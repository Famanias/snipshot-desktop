# Implementation Plan Status — Multi-Selection and Bulk Actions

---

## Completed Work (Phase 1)

[All Phase 1 items completed as per previous status]

---

## Completed Work (Phase 2)

[All Phase 2 items completed as per previous status]

---

## Completed Work (Phase 3)

[All Phase 3 items completed as per previous status]

---

## Completed Work (Post-Plan: Multi-Item Drag & Drop)

### Problem

`ImageCard._start_drag` always encoded only `[self.image_id]` regardless of the current selection. The drop handlers worked around this with expansion logic: "if 1 ID received and that ID is in the selection, expand to the full set." This was fragile — it only worked when exactly one card was dragged, not when the payload was already multi-item, and it put selection logic in the wrong layer.

### Changes Made

#### `ui/dashboard.py` — `ImageCard.__init__`

- Added `dashboard=None` parameter, stored as `self._dashboard`.

#### `ui/dashboard.py` — `ImageCard._start_drag`

- Replaced the hardcoded `image_ids = [self.image_id]` with selection-aware logic:
  - **Dragged card is in the selection**: payload = `list(dashboard.selected_image_ids)` — all selected IDs.
  - **Dragged card is NOT in the selection**: call `dashboard.clear_image_selection()`, select only the dragged card, payload = `[self.image_id]`.
- Drag payload is now correct before it reaches any drop target.

#### `ui/dashboard.py` — Card creation sites (3 locations)

- `_add_image_card_widget`: `ImageCard(image)` → `ImageCard(image, dashboard=self)`
- `_add_image_grid`: same
- `_render_next_page_batch`: same

#### `ui/dashboard.py` — `_on_images_dropped`

- Removed the expansion block (`if len == 1 and in selection → expand`). Payload is already correct; `effective_ids = image_ids` directly.

#### `ui/dashboard.py` — `_delete_images_dropped`

- Removed the same expansion block.
- Replaced all remaining `effective_ids` references with `image_ids` to match.

---

## Current State

### Working

- All Phase 1, 2, and 3 features working as before.
- **Multi-item drag to folder**: select N images, drag any one of them onto a FolderCard → all N images move to that folder.
- **Multi-item drag to trash**: select N images, drag any one onto the trash zone → single confirmation dialog for all N → deleted together.
- **Unselected card drag**: dragging a card that is not part of the current selection clears the old selection, selects only the dragged card, and moves only that card.
- **Single-image drag**: unchanged behavior — payload is `[image_id]`, drop handlers behave identically to before.

### Known Limitations

- None outstanding.

---

## Edge Cases Handled

| Scenario | Behavior |
|---|---|
| Drag a card that is already selected (with others also selected) | Payload includes all selected IDs |
| Drag a card that is NOT selected | Selection cleared, dragged card selected, payload = `[dragged_id]` |
| Single-image drag (no multi-selection active) | Payload = `[image_id]`, drop handlers treat it as single-image move/delete |
| `_dashboard` is `None` (card created without dashboard ref) | Falls back to `[self.image_id]`, safe no-op |

---

## Deviations from Plan

- None. The implementation matches the requirements exactly.
- The expansion logic that was removed from `_on_images_dropped` and `_delete_images_dropped` was a workaround, not a plan requirement — removing it is a cleanup, not a deviation.

---

## Modified Files

- `ui/dashboard.py`
  - `ImageCard.__init__`: added `dashboard=None` parameter.
  - `ImageCard._start_drag`: selection-aware payload construction.
  - `_add_image_card_widget`, `_add_image_grid`, `_render_next_page_batch`: pass `dashboard=self` at card creation.
  - `_on_images_dropped`: removed expansion logic.
  - `_delete_images_dropped`: removed expansion logic, replaced `effective_ids` refs with `image_ids`.

---

## Next Steps

Manual verification:

1. **Multi-drag to folder**: select 3+ images, drag one onto a folder → all selected images move.
2. **Multi-drag to trash**: select 3+ images, drag one onto the trash zone → single confirmation for all → all deleted.
3. **Unselected drag**: with images A, B, C selected, drag image D (unselected) → A, B, C deselected; D selected and moved alone.
4. **Single drag**: with no multi-selection, drag a single card → behaves as before.
5. **Drag payload integrity**: confirm that drag of a selected card in a 5-image selection moves all 5, not just the dragged one.
