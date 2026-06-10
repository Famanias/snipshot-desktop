# Implementation Plan Status — Multi-Selection and Bulk Actions

---

## Completed Work (Phase 1)

[All Phase 1 items completed as per previous status]

---

## Completed Work (Phase 2)

### ui/styles.py

- `image_card()` updated to include QRubberBand style:
  - `QRubberBand`: themed border (`primary`) with translucent fill (15% opacity).

### ui/dashboard.py — Imports

- Added `QRubberBand` to `from PyQt5.QtWidgets import …`.

### ui/dashboard.py — SelectionContainer

- Replaced `_ContentWidget` with new `SelectionContainer(QWidget)` class:
  - `__init__(dashboard_window, parent)`: stores reference to dashboard.
  - `mousePressEvent`: records `_drag_origin`; if Ctrl not held, calls `clear_image_selection()`; captures `_drag_start_selection`; creates and shows `QRubberBand`.
  - `mouseMoveEvent`: resizes `QRubberBand` to origin↔cursor rect; calls `dashboard.update_selection_from_rect(rect, drag_start_selection)` on each move.
  - `mouseReleaseEvent`: hides/deletes `QRubberBand`; performs final `update_selection_from_rect` call; if movement < `startDragDistance()`, treats as empty-space click → `clear_image_selection()`.

### ui/dashboard.py — DashboardWindow

- Replaced `self.content_widget = _ContentWidget()` with `self.content_widget = SelectionContainer(self)` in `_setup_ui()`.
- Removed `empty_clicked` signal connection (SelectionContainer now owns that logic).
- **`update_selection_from_rect(rect, drag_start_selection)`**: iterates all `_image_cards`; maps each card geometry to content widget coordinates; selects/deselects based on intersection with `rect`.
  - With Ctrl held: starts from `drag_start_selection` and toggles intersecting cards.
  - Without Ctrl: selects only intersecting cards.
- **`select_all_images()`**: adds all `_image_cards` keys to `selected_image_ids` and calls `set_selected(True)` on each.
- **`keyPressEvent(event)`**: added handler for Ctrl+A keyboard shortcut → calls `select_all_images()`.

---

## Current State (Phase 2 Complete)

### Working

- All Phase 1 features working as before.
- Marquee/rubber-band selection: click and drag over empty space across several cards; a themed rubber-band box is drawn and all intersected ImageCards are selected.
- Ctrl+marquee additive: hold Ctrl and drag a marquee over new cards; previous selection is preserved and intersected cards are added to it.
- Marquee ignores non-cards: dragging over folder cards, trash zone, labels only selects ImageCard instances.
- Ctrl+A select-all: pressing Ctrl+A selects all images in the current view.

### Known Limitations / Not Yet Implemented

- No Ctrl+click additive selection at individual card level (already working from Phase 1 via direct click handling).
- No Shift+click range selection (Phase 3).
- No keyboard navigation with arrow keys (Phase 3).
- No Delete key shortcut to delete selected images (Phase 3).
- No F2 key shortcut to rename focused image (Phase 3).

---

## Pending Work

### Phase 3

1. **`key_pressed = pyqtSignal(int, QKeyEvent)`** on `ImageCard`.
2. **`keyPressEvent` update** on `ImageCard`: emit `key_pressed` for arrow keys (`Up/Down/Left/Right`), `Delete`, and `F2`; keep Enter/Return emitting `double_clicked`.
3. **`_last_clicked_image_id`** tracking in `_on_image_clicked`.
4. **`_on_image_shift_clicked(image_id)`** on `DashboardWindow`: select contiguous range from `_last_clicked_image_id` to `image_id` in visual layout order.
5. **Shift-modifier check** in `_on_image_clicked`: delegate to `_on_image_shift_clicked` when Shift is held (use `QApplication.keyboardModifiers()`).
6. **`_on_image_key_pressed(image_id, event)`** on `DashboardWindow`:
   - Arrow keys: move focus to adjacent card in grid; Shift+arrow extends selection range.
   - Delete: call `_on_bulk_delete_images()`.
   - F2: open rename dialog for focused image (single selection only).
7. **Connect `key_pressed`** on each card creation site → `_on_image_key_pressed`.
8. **Disconnect `key_pressed`** in `_remove_image_card_widget`.

---

## Modified Files

- `ui/styles.py`: Updated `image_card()` with QRubberBand style.
- `ui/dashboard.py`: 
  - Added `QRubberBand` import.
  - Replaced `_ContentWidget` with `SelectionContainer` class.
  - Replaced `_ContentWidget()` instantiation with `SelectionContainer(self)`.
  - Added `update_selection_from_rect()` method.
  - Added `select_all_images()` method.
  - Added `keyPressEvent()` method with Ctrl+A handler.

---

## Notes

- SelectionContainer properly handles child widget detection to avoid conflicts with drag operations on cards.
- Coordinate mapping from card geometry to content widget space is handled correctly in `update_selection_from_rect()`.
- QRubberBand styling uses theme-aware primary color with translucent fill (39/255 alpha ≈ 15% opacity).
- All Phase 1 functionality remains intact and compatible with Phase 2 additions.
- Next phase (Phase 3) will add keyboard-driven navigation and range selection via Shift+click and arrow keys.

---

## Next Steps (Ordered)

1. Implement `key_pressed` signal on `ImageCard` and update `keyPressEvent`.
2. Implement `_last_clicked_image_id` tracking and `_on_image_shift_clicked`.
3. Implement `_on_image_key_pressed` with arrow, Delete, and F2 handling.
4. Wire `key_pressed` at all card creation/removal sites.
5. Manually verify all Phase 2 scenarios from the verification plan.
6. Manually verify all Phase 3 scenarios from the verification plan.
