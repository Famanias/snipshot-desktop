# Implementation Plan - Global Search Feature (Production-Ready)

Implement a front-end only, fast, responsive global search across the Snipshot Desktop application to filter folders and images in real time.

---

## User Review Required

> [!IMPORTANT]
> **Cooperative Thread Cancellation (No `terminate()`):** Workers use a shared `_cancelled` flag instead of `QThread.terminate()`. The worker checks this flag at safe checkpoints during its loop and exits cleanly. `terminate()` is a hard kill that can corrupt heap state on Windows — unsafe for a PyInstaller exe.

> [!IMPORTANT]
> **Sequential Paginated Cache Building:** The background cache worker fetches images page-by-page (100 items/page) until the API returns an empty page, retrieving the full dataset without a hardcoded ceiling. A soft cap of 10,000 items is applied with a visible user notice if exceeded.

> [!IMPORTANT]
> **Error Handling in Workers:** All API calls inside background workers are wrapped in try/except. On failure, workers emit an `error` signal. The UI displays a non-blocking error banner rather than silently leaving the cache partially populated.

> [!IMPORTANT]
> **Safe App Close (`closeEvent`):** `DashboardWindow.closeEvent` cancels and joins all active workers before accepting the close event, preventing crashes or hangs from dangling threads on exit.

> [!NOTE]
> **Zero-fetch Warm Cache Restores:** Clearing the search input re-renders the current view (All Files, Folder View, or Recent View) directly from the warm in-memory cache — no network request, no loading state.

> [!NOTE]
> **Cold Load Progress Feedback:** During the initial paginated cache build, a non-blocking progress indicator is shown in the content area so users know the app is working, not frozen.

> [!NOTE]
> **Crash Logging:** A global `sys.excepthook` writes unhandled exceptions to a log file in the platform-appropriate user data directory (`%APPDATA%` on Windows). This gives visibility into production crashes without requiring a crash reporting service.

---

## Proposed Changes

### Desktop UI

#### [MODIFY] `main.py` (or app entry point)

- **Crash Logger Setup:**
  - Before the `QApplication` is created, install a global exception hook:
    ```python
    import sys, logging, traceback
    from pathlib import Path
    import platformdirs

    log_dir = Path(platformdirs.user_data_dir("Snipshot", "Snipshot"))
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=log_dir / "snipshot.log",
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s %(message)s"
    )

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logging.critical(
            "Unhandled exception",
            exc_info=(exc_type, exc_value, exc_tb)
        )

    sys.excepthook = handle_exception
    ```
  - Add `platformdirs` to `requirements.txt`.

---

#### [MODIFY] `dashboard.py`

---

##### 1. In-Memory Cache

- Define in `DashboardWindow.__init__`:
  ```python
  self._cached_folders: list = []
  self._cached_images: list = []
  self._current_view: str = "root"        # "root" | "folder" | "recent"
  self._current_folder_id: int | None = None
  self._current_folder_name: str = ""
  self.search_worker = None
  self.cache_loader_worker = None
  self.cache_update_worker = None
  ```

---

##### 2. Debounce Layer

- Initialize in `__init__`:
  ```python
  self.search_timer = QTimer(self)
  self.search_timer.setSingleShot(True)
  self.search_timer.setInterval(250)
  self.search_timer.timeout.connect(self._trigger_search)
  ```

---

##### 3. Cooperative Worker Cancellation Helper

- Add `_cancel_worker(self, attr: str)`:
  ```python
  def _cancel_worker(self, attr: str):
      worker = getattr(self, attr, None)
      if worker is not None and worker.isRunning():
          try:
              worker.cancel()          # sets _cancelled = True
              worker.finished.disconnect()
              worker.error.disconnect()
          except (TypeError, RuntimeError):
              pass
          worker.wait(2000)            # wait up to 2s for clean exit
      setattr(self, attr, None)
  ```

---

##### 4. `CacheLoaderWorker(QThread)` — Paginated, Cancellable

```python
class CacheLoaderWorker(QThread):
    finished = pyqtSignal(list, list)   # folders, images
    error = pyqtSignal(str)
    progress = pyqtSignal(int)          # items loaded so far

    SOFT_CAP = 10_000
    PAGE_SIZE = 100

    def __init__(self, api_client):
        super().__init__()
        self._api_client = api_client
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            folders = self._api_client.get_folders()
            if self._cancelled:
                return

            images = []
            page = 1
            while True:
                if self._cancelled:
                    return
                batch = self._api_client.get_images(page=page, per_page=self.PAGE_SIZE)
                if not batch:
                    break
                images.extend(batch)
                self.progress.emit(len(images))
                if len(images) >= self.SOFT_CAP:
                    # Emit with a flag or log; UI will show a notice
                    break
                page += 1

            self.finished.emit(folders, images)

        except Exception as e:
            self.error.emit(str(e))
```

- **Note:** If `len(images) >= SOFT_CAP`, `_on_data_loaded` should display a non-blocking notice: *"Showing first 10,000 items. Use search to find others."*

---

##### 5. `InMemorySearchWorker(QThread)` — Cooperative Cancellation

```python
class InMemorySearchWorker(QThread):
    finished = pyqtSignal(list, list)   # matched_folders, matched_images
    error = pyqtSignal(str)

    def __init__(self, query, folders, images):
        super().__init__()
        self._query = query.lower().strip()
        self._folders = folders
        self._images = images
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            matched_folders, matched_images = filter_items(
                self._query, self._folders, self._images,
                cancelled_flag=lambda: self._cancelled
            )
            if not self._cancelled:
                self.finished.emit(matched_folders, matched_images)
        except Exception as e:
            self.error.emit(str(e))
```

---

##### 6. `filter_items` — Decoupled, Cancellable Search Function

```python
def filter_items(
    query: str,
    folders: list,
    images: list,
    cancelled_flag=None
) -> tuple[list, list]:
    """Pure filtering function. Decoupled from UI and workers."""
    q = query.lower().strip()

    matched_folders = []
    for folder in folders:
        if cancelled_flag and cancelled_flag():
            return [], []
        if q in (folder.get("name") or "").lower() \
           or q in (folder.get("description") or "").lower():
            matched_folders.append(folder)

    matched_images = []
    for image in images:
        if cancelled_flag and cancelled_flag():
            return [], []
        if q in (image.get("filename") or "").lower() \
           or q in (image.get("original_filename") or "").lower() \
           or q in (image.get("source_language") or "").lower() \
           or q in (image.get("target_language") or "").lower():
            matched_images.append(image)

    return matched_folders, matched_images
```

---

##### 7. Decoupled Render Methods

- `_render_root_view(self)` — renders folders + unfiled images (`folder_id is None`) from cache.
- `_render_folder_view(self, folder_id, folder_name)` — renders images matching `folder_id` from cache.
- `_render_recent_view(self)` — sorts `_cached_images` by `created_at` descending, renders top 20.
- Each method sets `self._current_view` and related state before rendering.

---

##### 8. Cache Loader Startup

- On `__init__` and on explicit refresh, call `_start_cache_load()`:
  ```python
  def _start_cache_load(self):
      self._cancel_worker("cache_loader_worker")
      self._show_loading_indicator("Loading your library...")
      worker = CacheLoaderWorker(self.api_client)
      worker.finished.connect(self._on_data_loaded)
      worker.error.connect(self._on_cache_error)
      worker.progress.connect(self._on_cache_progress)
      self.cache_loader_worker = worker
      worker.start()
  ```
- `_on_cache_progress(count)` — updates a progress label: *"Loading… {count} items"*.
- `_on_cache_error(msg)` — shows a non-blocking error banner: *"Could not load library: {msg}. Retry?"*

---

##### 9. Cache Synchronization During Navigation

- In `_load_folder`: call `_cancel_worker("cache_update_worker")` before starting a new background sync.
- In `_on_nav_recent`: same guard before any background sync.
- Cache update workers use the same `CacheLoaderWorker` pattern with `cancelled_flag`.

---

##### 10. Search Box Events

- `_on_search_changed(text)`:
  ```python
  def _on_search_changed(self, text: str):
      self.search_timer.stop()
      self._cancel_worker("search_worker")
      if not text.strip():
          self._restore_current_view()   # warm cache, zero network
      else:
          self.search_timer.start()
  ```
- `_restore_current_view()` dispatches to the appropriate render method based on `self._current_view`.

- `_trigger_search()` (debounce timeout):
  ```python
  def _trigger_search(self):
      query = self.search_input.text().strip()
      if not query:
          return
      self._cancel_worker("search_worker")
      self._show_searching_indicator()
      worker = InMemorySearchWorker(query, self._cached_folders, self._cached_images)
      worker.finished.connect(self._on_search_results)
      worker.error.connect(self._on_search_error)
      self.search_worker = worker
      worker.start()
  ```

---

##### 11. Search Results Rendering

- `_on_search_results(folders, images)`:
  - Clear layout.
  - If folders non-empty: render "Folders" header + `FolderCard` per folder.
  - If images non-empty: render "Images" header + `ImageCard` per image.
  - If both empty: render *"No results for '{query}'"* empty state.
- `_on_search_error(msg)`: show non-blocking error banner, restore previous view.

---

##### 12. Safe App Close

```python
def closeEvent(self, event: QCloseEvent):
    self.search_timer.stop()
    self._cancel_worker("search_worker")
    self._cancel_worker("cache_loader_worker")
    self._cancel_worker("cache_update_worker")
    event.accept()
```

---

## Verification Plan

### Automated Verification

```powershell
python main.py
```
Confirm app starts, cache loads, and no errors in `snipshot.log`.

### Manual Verification

| Test | Expected Result |
|---|---|
| **Cooperative cancellation** | Type quickly; confirm in logs that preceding workers call `cancel()` and exit — no `terminate()` calls, no crashes |
| **Rapid folder navigation** | Click between folders rapidly; no crashes, no stale results, no concurrent write errors |
| **Cold load progress** | On first launch, a loading indicator shows item count incrementing until complete |
| **Soft cap notice** | With 10,000+ items in test data, a notice appears; search still works across all loaded items |
| **API failure during load** | Kill backend mid-load; confirm error banner appears with retry option, app does not freeze |
| **Warm cache restore** | Type a query, then clear; view restores instantly with no network request (verify no backend log entries) |
| **Empty state** | Search `xyz123`; confirm custom empty state message renders |
| **Metadata matching** | Search `ENG`, `JPN`, or a folder description keyword; confirm correct items surface |
| **closeEvent safety** | Close app while cache is loading; confirm clean exit, no hang, no crash |
| **Crash log** | Trigger a deliberate unhandled exception; confirm it appears in `snipshot.log` with timestamp and traceback |

---

## Production Checklist (Before PyInstaller Build)

- [ ] `platformdirs` added to `requirements.txt`
- [ ] `sys.excepthook` installed before `QApplication` creation
- [ ] `closeEvent` implemented and tested
- [ ] All workers use `_cancelled` flag — zero `terminate()` calls
- [ ] All worker API calls wrapped in `try/except` with `error` signal
- [ ] Soft cap notice visible in UI when exceeded
- [ ] Cold load progress indicator functional
- [ ] `snipshot.log` written to `%APPDATA%\Snipshot\` on Windows
- [ ] PyInstaller spec includes `platformdirs` in hidden imports if needed