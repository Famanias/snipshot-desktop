# Implementation Plan Status — Multi-Selection and Bulk Actions

---

## Completed Work (Phase 1)

### ui/styles.py

- `image_card()` fully updated with QSS-based selection styles:
  - `ImageCard[selected="true"]` — highlighted border (`primary`) and background (`primary_light`).
  - `ImageCard QFrame#preview_box` and `ImageCard QFrame#info_section` — background/border-radius moved from inline Python into QSS using descendant selectors.
  - `ImageCard[selected="true"] QFrame#preview_box` and `…#info_section` — set to `transparent` so the parent highlight shows through.

### ui/dashboard.py — ImageCard

- Added signals: `double_clicked = pyqtSignal(int)`, `right_clicked = pyqtSignal(int, QPoint)`.
- Added `_selected = False` state and `set_selected(bool)` method with `unpolish`/`polish` to force QSS re-evaluation.
- `setFocusPolicy(Qt.StrongFocus)` set in `__init__`.
- `_setup_ui`: `preview_box` and `info_section` assigned object names `"preview_box"` and `"info_section"`.
- `_apply_style`: inline `setStyleSheet` calls removed from `preview_box` and `info_section`; styles now come entirely from `image_card()` QSS.
- `mousePressEvent`: left-click emits `clicked`; right-click emits `right_clicked` with global position.
- `mouseDoubleClickEvent`: emits `double_clicked`.
- `keyPressEvent`: emits `double_clicked` on Enter/Return.
- `_start_drag`: guarded with `QApplication.startDragDistance()`; encodes `[image_id]` as JSON bytes under MIME type `application/x-snipshot-image-ids`.
- `_show_context_menu` "View" action: fixed to emit `double_clicked` (not `clicked`).

### ui/dashboard.py — FolderCard

- Signal changed from `pyqtSignal(int, str)` to `pyqtSignal(int, list)`.
- `dragEnterEvent`/`dragMoveEvent`: accept `application/x-snipshot-image-ids`.
- `dropEvent`: decodes JSON bytes via `json.loads()`, emits list of integer IDs.

### ui/dashboard.py — TrashDropZone

- Updated to accept `application/x-snipshot-image-ids` MIME type.
- Calls `_delete_images_dropped(image_ids: list)`.

### ui/dashboard.py — _ContentWidget

- New `_ContentWidget(QWidget)` class with `empty_clicked = pyqtSignal()`.
- `mousePressEvent`: emits `empty_clicked` when click lands on no child widget.
- Replaces bare `QWidget()` as `self.content_widget`; `empty_clicked` connected to `clear_image_selection`.

### ui/dashboard.py — DashboardWindow

- `self.selected_image_ids = set()` initialized in `__init__`.
- `_clear_content`: calls `self.selected_image_ids.clear()`.
- All card-creation sites: connect `double_clicked` → `_on_image_double_clicked`, `right_clicked` → `show_image_context_menu`.
- `_remove_image_card_widget`: disconnects `double_clicked` and `right_clicked` before removal.
- **`_on_image_clicked(image_id)`**: single-select on plain click (clears others first); Ctrl+click toggles without clearing. Uses `QApplication.keyboardModifiers()` at call time.
- **`_on_image_double_clicked(image_id)`**: opens `ImagePreviewDialog` (URL refresh + dialog).
- **`clear_image_selection()`**: deselects all cards in `selected_image_ids`, clears the set.
- **`show_image_context_menu(image_id, pos)`**: Windows Explorer convention — right-click unselected card clears and selects it (single menu); right-click already-selected card in a multi-selection keeps selection (bulk menu).
- **`_on_bulk_move_images()`**: `QInputDialog.getItem` folder picker; moves all selected images via `api_client.move_image_to_folder`.
- **`_on_bulk_delete_images()`**: `QMessageBox.question` confirm; deletes all selected images via `api_client.delete_image`, removes cards, reconciles folder counts.
- **`_on_images_dropped(folder_id, image_ids)`**: expands single dragged-selected card to full `selected_image_ids`; moves all; clears selection on success.
- **`_delete_images_dropped(image_ids)`**: same expansion logic; shows combined confirmation for multi-drop onto trash zone.

---

## Current State

### Working

- Single-click selects one image; clicking another deselects the first.
- Ctrl+click adds/removes individual images to/from selection without clearing others.
- Double-click opens the image preview dialog.
- Enter key on a focused card opens the preview dialog.
- Clicking empty dashboard space deselects all cards.
- Right-click on an unselected card: selects it, shows single-image context menu (View / Rename / Move to Folder / Delete).
- Right-click on a selected card with multiple selected: shows bulk context menu (Move N images / Delete N images).
- Bulk move via context menu prompts for folder and moves all selected images.
- Bulk delete via context menu confirms and deletes all selected images.
- Dragging one card from a multi-selection onto a FolderCard moves all selected images.
- Dragging one card from a multi-selection onto the Trash zone deletes all with confirmation.
- Accidental drag guard: drags below `QApplication.startDragDistance()` are suppressed.
- Card selection visual state (highlighted border + background) correctly reflects `selected_image_ids`.

### Known Limitations / Not Yet Implemented

- No rubber-band marquee selection (Phase 2).
- No Ctrl+A select-all (Phase 2).
- No Shift+click range selection (Phase 3).
- No keyboard navigation with arrow keys (Phase 3).
- No Delete key shortcut to delete selected images (Phase 3).
- No F2 key shortcut to rename focused image (Phase 3).

---

## Pending Work

### Phase 2

1. **QRubberBand import** — add `QRubberBand` to `from PyQt5.QtWidgets import …` in `dashboard.py`.
2. **Rubber-band style** — add `QRubberBand` QSS rule to `ui/styles.py` (`image_card()` or a separate helper): themed border, translucent fill.
3. **`SelectionContainer(QWidget)`** — new class to replace `_ContentWidget`:
   - `mousePressEvent`: record `_drag_origin`; if Ctrl not held call `clear_image_selection()`; capture `_drag_start_selection`; create and show `QRubberBand`.
   - `mouseMoveEvent`: resize `QRubberBand` to origin↔cursor rect; call `dashboard.update_selection_from_rect(rect, drag_start_selection)`.
   - `mouseReleaseEvent`: hide/delete `QRubberBand`; final `update_selection_from_rect` call; if movement < `startDragDistance()` treat as empty-space click → `clear_image_selection()`.
4. **Replace `_ContentWidget`** with `SelectionContainer(self)` in `DashboardWindow._setup_ui`; remove the Phase 1 `empty_clicked` connection (SelectionContainer owns that logic).
5. **`update_selection_from_rect(rect, drag_start_selection)`** on `DashboardWindow`:
   - Iterate all `_image_cards`; map each card geometry to content widget coordinates; select/deselect based on intersection with `rect`.
   - With Ctrl: start from `drag_start_selection` and toggle intersecting cards.
6. **`select_all_images()`** on `DashboardWindow`: add all `_image_cards` keys to `selected_image_ids` and call `set_selected(True)` on each.
7. **Ctrl+A handler** on `DashboardWindow.keyPressEvent`: call `select_all_images()`.
8. **`_on_image_clicked` Ctrl path** — already implemented via `QApplication.keyboardModifiers()`; verify it satisfies Phase 2 requirement (no signal-level change needed unless plan specifies forwarding modifiers explicitly).

### Phase 3

1. **`key_pressed = pyqtSignal(int, QKeyEvent)`** on `ImageCard`.
2. **`keyPressEvent` update** on `ImageCard`: emit `key_pressed` for arrow keys (`Up/Down/Left/Right`), `Delete`, and `F2`; keep Enter/Return emitting `double_clicked`.
3. **`_last_clicked_image_id`** tracking in `_on_image_clicked`.
4. **`_on_image_shift_clicked(image_id)`** on `DashboardWindow`: select contiguous range from `_last_clicked_image_id` to `image_id` in visual layout order.
5. **Shift-modifier check** in `_on_image_clicked`: delegate to `_on_image_shift_clicked` when Shift is held (requires forwarded modifier state or `QApplication.keyboardModifiers()`).
6. **`_on_image_key_pressed(image_id, event)`** on `DashboardWindow`:
   - Arrow keys: move focus to adjacent card in grid; Shift+arrow extends selection range.
   - Delete: call `_on_bulk_delete_images()`.
   - F2: open rename dialog for focused image (single selection only).
7. **Connect `key_pressed`** on each card creation site → `_on_image_key_pressed`.
8. **Disconnect `key_pressed`** in `_remove_image_card_widget`.

---

## Next Steps (Ordered)

1. Add `QRubberBand` to `PyQt5.QtWidgets` import in `dashboard.py`.
2. Add `QRubberBand` QSS rule to `ui/styles.py`.
3. Implement `SelectionContainer` class with rubber-band mouse events.
4. Replace `_ContentWidget` with `SelectionContainer` in `_setup_ui`.
5. Implement `update_selection_from_rect` on `DashboardWindow`.
6. Implement `select_all_images` on `DashboardWindow`.
7. Add Ctrl+A handler to `DashboardWindow.keyPressEvent`.
8. Manually verify all Phase 2 scenarios from the verification plan.
9. *(Phase 3)* Add `key_pressed` signal to `ImageCard` and update `keyPressEvent`.
10. *(Phase 3)* Implement `_last_clicked_image_id` tracking and `_on_image_shift_clicked`.
11. *(Phase 3)* Implement `_on_image_key_pressed` with arrow, Delete, and F2 handling.
12. *(Phase 3)* Wire `key_pressed` at all card creation/removal sites.
13. Manually verify all Phase 3 scenarios from the verification plan.
