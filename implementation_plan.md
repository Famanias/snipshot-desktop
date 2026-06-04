# Implementation Plan - Local Cache and Optimistic UI Updates

This plan details the implementation of an in-memory local cache state manager and targeted UI updates in the PyQt5 dashboard. This removes unnecessary full library reloads (displaying blocking "Loading..." screens) after basic CRUD operations, making the application feel instantaneous and responsive.

## User Review Required

> [!NOTE]
> All basic CRUD operations (Create Folder, Rename Folder, Delete Folder, Rename Image, Delete Image, Move Image) will now modify the in-memory lists `self._cached_folders` and `self._cached_images` directly and update the visible UI widgets in-place (patching).
> 
> A full library reload (with the loading screen) will be reserved only for:
> 1. Initial application startup / Login.
> 2. Swapping client implementations (Local Mode toggle).
> 3. Manual refresh operations (if triggered).

## Key Design Principles & Safety Measures

### 1. Targeted Widget Patching (No "Performance Trap")
Instead of clearing and rebuilding the entire dashboard via `self._restore_current_view()` for minor changes, we will:
- Track active widgets in dictionaries: `self._folder_cards = {}` (folder_id -> Card) and `self._image_cards = {}` (image_id -> Card).
- Update widget labels directly on rename.
- Remove widgets directly from their layout on delete.
- Insert folder widgets directly into the layout on create.
- Fall back to `_restore_current_view()` only for layout-level reflows (e.g. transitioning to or from empty states).

### 2. PyQt Layout & Memory Safety
To prevent spacing glitches and memory leaks from orphaned widgets in PyQt layouts:
- When removing a card widget, we will explicitly disconnect its signals, call `widget.setParent(None)`, and call `widget.deleteLater()`.
- Card deletion/removal will strictly follow this order:
  1. API operation success check.
  2. Mutate cache (`self._cached_images` / `self._cached_folders`).
  3. Remove widget from the layout.
  4. Dispose of the widget (`setParent(None)` and `deleteLater()`).
  5. Remove reference from the mapping dictionary (`self._image_cards` / `self._folder_cards`).

### 3. Transaction Safety (Sync API First)
To avoid UI desynchronization on API failures, all operations will run synchronously on the client:
1. Trigger API operation.
2. Await API success.
3. If successful, modify the local caches (`self._cached_folders`, `self._cached_images`) and update/patch the PyQt UI widgets.
4. If failed, display the error dialog and leave both the cache and UI completely untouched (precluding the need for complex state rollback).

### 4. Folder Count Reconciliation
Instead of fragile incremental math (`+1` / `-1`), we will implement a centralized `_reconcile_folder_counts(self)` method. Whenever images are added, removed, or moved, this helper will:
- Recompute the counts of all folders directly from the `self._cached_images` list.
- Update the `image_count` property of folders in `self._cached_folders` and update the count label of active folder cards directly.

### 5. Cache Resolution by ID
To prevent widget-level reference copies from becoming stale:
- `ImageCard` signals (`clicked`, `delete_requested`, `rename_requested`, `move_requested`) will be updated to emit `image_id: int` instead of full dictionaries.
- `DashboardWindow` will retrieve the active dictionary from the cache by ID using a helper: `_get_cached_image(self, image_id: int) -> Optional[dict]`.

---

## Architectural UI Patch Primitives

To keep PyQt view layout manipulation modular, standardized, and clean, we will implement the following UI patch primitives:

- `_add_folder_card_widget(self, folder: dict)`:
  - Instantiates `FolderCard(folder)`, connects event handlers, adds it to `self.folder_grid_layout` (inserted at index 0), and registers it in `self._folder_cards`.
- `_remove_folder_card_widget(self, folder_id: int)`:
  - Resolves widget from `self._folder_cards`. If found, removes it from the layout, calls `widget.setParent(None)`, `widget.deleteLater()`, and deletes the reference in `self._folder_cards`.
- `_add_image_card_widget(self, image: dict)`:
  - Instantiates `ImageCard(image)`, connects event handlers, inserts it at index 0 of `self._image_grid_widget.layout()`, and registers it in `self._image_cards`.
- `_remove_image_card_widget(self, image_id: int)`:
  - Resolves widget from `self._image_cards`. If found, removes it from `self._image_grid_widget.layout()`, calls `widget.setParent(None)`, `widget.deleteLater()`, and deletes the reference in `self._image_cards`.

---

## Architectural & Integration Contracts

### Contract 1: Strict Event Pipeline Ordering
All CRUD operations (moves, renames, deletes) must strictly adhere to the following sequence of execution:
```
1. Trigger API Operation (Wait for Response)
       ↓
2. Validate Success Status
       ↓
3. Mutate Local Cache (self._cached_images / self._cached_folders)
       ↓
4. Patch PyQt Widgets (using UI Patch Primitives)
       ↓
5. Reconcile Folder Counts (trigger _reconcile_folder_counts)
```

### Contract 2: Signal Migration Safety
To prevent "half-migrated UI" bugs and PyQt signature mismatch crashes:
- When changing `ImageCard` signals to emit `image_id: int`, all corresponding connect statements in `DashboardWindow` (`_on_image_clicked`, `_on_delete_image`, `_on_rename_image`, `_on_move_image`) must be updated to accept the `image_id (int)` parameter and resolve the image dictionary from the cache via `self._get_cached_image(image_id)`.

### Future Architectural Evolution Notes
- **Supabase Latency**: If network latency spikes, the synchronous API block may freeze the UI. If this becomes a problem, we will upgrade to asynchronous background threads with immediate optimistic UI updates and revert-on-failure rollback handlers.
- **Scale Optimization**: If the user's library grows large (e.g. 10k+ images), running `O(N)` reconciliation on every operation may cause lag. In that case, we will transition to deferred reconciliation (e.g., using a short QTimer debounce) or maintain incremental counters.
- **View Abstraction**: To prevent view matrix rules from expanding uncontrollably, we will eventually abstract views into filter classes (e.g., `view.filter(image) -> bool`).
- **Framework Separation**: If logic becomes scattered, we will refactor to separate the UI layer from the state store (e.g., `DashboardStore`, `DashboardActions`, and `DashboardRenderer`).

---

## Active View Patching Matrix

The UI update actions for image cards depend on the currently active view:

| Action / Operation | Active View is: **All Files (Root)** | Active View is: **Folder View (Folder A)** | Active View is: **Recent View** |
| :--- | :--- | :--- | :--- |
| **New Image Created** | Call `_add_image_card_widget` if `folder_id` is None. | Call `_add_image_card_widget` if image `folder_id == Folder A`. | Call `_add_image_card_widget`. |
| **Delete Image** | Call `_remove_image_card_widget` (if it was unfiled). | Call `_remove_image_card_widget`. | Call `_remove_image_card_widget`. |
| **Move to Folder B** | Call `_remove_image_card_widget` (if moving from unfiled). Update counts on Folder B card. | Call `_remove_image_card_widget` (since it left Folder A). | Update counts on Folder B card. |
| **Move from Folder B** | Call `_add_image_card_widget` (if moving to unfiled). Update counts on Folder B card. | Call `_add_image_card_widget` if moving to Folder A. Update counts on Folder B card. | Update counts on Folder B card. |

---

## Proposed Changes

### UI Components

We will update the PyQt5 UI dashboard and translation window to support optimistic updates and local caching.

#### [MODIFY] [translation.py](file:///c:/Users/neilc/OneDrive/Documents/GitHub/snipshot-desktop/ui/translation.py)
- Change the `saved` signal to emit the newly created image dictionary:
  `saved = pyqtSignal(dict)`
- In `_on_save_complete(self, data: dict)`, emit the new image data dict with the signal:
  `self.saved.emit(data)`

#### [MODIFY] [main.py](file:///c:/Users/neilc/OneDrive/Documents/GitHub/snipshot-desktop/main.py)
- Connect the `saved` signal of the `TranslationWindow` to `self.dashboard.add_saved_image` instead of `self.dashboard.refresh`.

#### [MODIFY] [dashboard.py](file:///c:/Users/neilc/OneDrive/Documents/GitHub/snipshot-desktop/ui/dashboard.py)

- Keep references to layout and widget groups:
  - Add `self._folder_cards = {}` and `self._image_cards = {}` mappings.
  - Store `self.folder_grid` and `self.folder_grid_layout` as instance variables in `_render_root_view`.
- Update `_add_image_grid` to populate `self._image_cards`.
- Update `ImageCard` signals to emit `image_id (int)` instead of `image_data (dict)`.
- Implement state helpers:
  - `_get_cached_image(self, image_id: int) -> Optional[dict]`
  - `_reconcile_folder_counts(self)`: Recomputes folder image counts and updates visible folder card labels.
- Implement UI patch helpers & primitives:
  - `_add_folder_card_widget(self, folder: dict)`
  - `_remove_folder_card_widget(self, folder_id: int)`
  - `_add_image_card_widget(self, image: dict)`
  - `_remove_image_card_widget(self, image_id: int)`
  - `add_saved_image(self, image_data: dict)`: Inserts new image into cache, calls `_add_image_card_widget` if current view criteria is matched, and reconcile counts.
  - `_move_image_locally(self, image_id: int, new_folder_id: int)`: Updates `folder_id` in image cache, calls `_remove_image_card_widget` or `_add_image_card_widget` according to the active view matrix, and reconciles counts.
- Update CRUD event handlers to apply mutations to cache + patch visible widgets:
  - `_on_image_clicked(self, image_id: int)`
  - `_on_new_folder(self)`
  - `_on_delete_folder(self, folder_id: int, folder_name: str)`
  - `_on_rename_folder(self, folder_id: int, current_name: str)`
  - `_on_delete_image(self, image_id: int)`
  - `_on_rename_image(self, image_id: int)`
  - `_on_move_image(self, image_id: int)`
  - `_on_image_dropped(self, folder_id: int, image_id: int)`

---

## Verification Plan

### Automated Tests
- Run Python compilation check to verify no syntax errors:
  ```powershell
  .venv\Scripts\python -m py_compile ui/translation.py ui/dashboard.py main.py
  ```

### Manual Verification
- Start the application:
  ```powershell
  .venv\Scripts\python main.py
  ```
- **Folder CRUD Test**: Create a folder, rename it, and delete it. Verify all transitions are instant, with no "Loading your library..." screens shown.
- **Image CRUD Test**: Rename an image, delete an image, and move an image to a folder. Verify these updates happen instantly.
- **Image Drop Test**: Drag and drop an image into a folder. Verify the thumbnail grid and folder counts update immediately with no full reload.
- **Save Capture Test**: Trigger a screenshot snip, translate it, and save it to a folder. Verify the dashboard updates immediately when the dialog closes, displaying the new screenshot card.
