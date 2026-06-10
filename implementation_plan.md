Implementation Plan - Multi-Selection and Bulk Actions
User Review Required

[!IMPORTANT]

Click Behavior Change: Single-click on images will now toggle selection/deselection. Double-click (or pressing Enter) will open the image preview. This is consistent with Windows Explorer behavior.
Visual Style Update: Image cards will get a highlighted border and background when selected to clearly show their selected state.
Phase Scope: This plan covers all three phases. Phase 1 is the core implementation. Phases 2 and 3 build on top of it incrementally — each phase assumes the previous is complete and merged.



Proposed Changes

UI Styles
[MODIFY] ui/styles.py

Update image_card() to support selection state (ImageCard[selected="true"]).
Style child components of ImageCard (QFrame#preview_box and QFrame#info_section) to have transparent backgrounds when selected, inheriting the container's highlight color.
(Phase 2) Add a style for the rubber-band marquee rectangle (QRubberBand) to give it a visible, themed border and translucent fill.


Dashboard Components
[MODIFY] ui/dashboard.py

1. Imports

(Phase 2) Add QRubberBand to imports from PyQt5.QtWidgets.


2. ImageCard Update
Phase 1

Add double_clicked = pyqtSignal(int) and right_clicked = pyqtSignal(int, QPoint) signals.
Add selected state variable and set_selected(self, selected: bool) method.
Set self.setFocusPolicy(Qt.StrongFocus) so the card can receive keyboard focus, required for Enter key handling. Note: full keyboard navigation is deferred to Phase 3, but focus must be enabled now.
Update _setup_ui to assign object names preview_box and info_section to the respective frames, aligning with QSS selectors.
Update _apply_style to remove inline background-color styling on preview_box and info_section so they correctly inherit selection styles from QSS.
Update mousePressEvent:

Left-click: delegate to dashboard via the existing clicked signal; the dashboard owns all selection logic.
Right-click: emit right_clicked with the image ID and global cursor position.


Update mouseDoubleClickEvent to emit double_clicked.
Update keyPressEvent to emit double_clicked when Enter or Return is pressed, reusing the same signal since both actions open the preview.
Update _start_drag:

Guard with QApplication.startDragDistance() check before initiating a drag, to prevent accidental drags during single-click selection.
Encode dragged image IDs as JSON bytes under MIME type application/x-snipshot-image-ids (e.g., [1, 2, 3]).



Phase 3

Update keyPressEvent to also emit a new key_pressed = pyqtSignal(int, QKeyEvent) signal for arrow keys (Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right), Qt.Key_Delete, and Qt.Key_F2, forwarding them to the dashboard for handling.


3. FolderCard Update
Phase 1

Change images_dropped = pyqtSignal(int, str) to images_dropped = pyqtSignal(int, list).
Update dropEvent to decode the application/x-snipshot-image-ids MIME payload via json.loads() and emit the resulting list of integer IDs.


4. SelectionContainer (Phase 2)

Create SelectionContainer(QWidget) to serve as the content area background.
Implement mousePressEvent:

Record drag origin as self._drag_origin.
If Ctrl is not held, call clear_image_selection() on the dashboard immediately.
Capture current selection into self._drag_start_selection for additive marquee support with Ctrl.
Instantiate and show a QRubberBand at the origin point.


Implement mouseMoveEvent:

Expand the QRubberBand to cover the rectangle between the drag origin and current cursor position.
Call update_selection_from_rect(rect, drag_start_selection) on the dashboard on each move to update selection in real time.


Implement mouseReleaseEvent:

Hide and delete the QRubberBand.
Perform a final update_selection_from_rect call to commit the completed selection.


Empty-space click (no drag): if mousePressEvent fires and mouseReleaseEvent fires without meaningful movement (within QApplication.startDragDistance()), treat it as an empty-area click and call clear_image_selection().


5. DashboardWindow Core Implementation
Phase 1

Initialize self.selected_image_ids = set() to track the current selection.
Implement selection helpers:

clear_image_selection(self): Deselects all cards and clears self.selected_image_ids.
_on_image_clicked(self, image_id): Toggles selection state of the clicked card.
_on_image_double_clicked(self, image_id): Opens the preview dialog.


Handle empty-space clicks: override mousePressEvent on the content widget so a click landing on no ImageCard calls clear_image_selection(). Superseded by SelectionContainer in Phase 2 but required for Phase 1.
Implement context menu with Explorer-convention right-click behavior:

show_image_context_menu(self, image_id, pos):

If the right-clicked image is not in the current selection: clear selection, select that image only, show single-image menu (View / Rename / Move / Delete).
If the right-clicked image is already selected and multiple are selected: keep current selection, show bulk menu (Move / Delete).
If the right-clicked image is selected but it is the only selected image: show single-image menu.




Implement bulk actions:

_on_bulk_move_images(self): Prompts user for a target folder and moves all images in self.selected_image_ids.
_on_bulk_delete_images(self): Confirms and deletes all images in self.selected_image_ids.


Update drag-and-drop handlers:

_on_images_dropped(self, folder_id, image_ids): Accepts a list of integer IDs; handles single and bulk move onto a folder.
_delete_images_dropped(self, image_ids): Accepts a list of integer IDs; handles single and bulk drop onto the Trash Drop Zone with confirmation.


Clear selection in _clear_content and _restore_current_view when shifting views.

Phase 2

Replace self.content_widget = QWidget() with self.content_widget = SelectionContainer(self).
Remove the Phase 1 mousePressEvent override on the content widget; SelectionContainer now owns empty-space click and marquee behavior.
Implement update_selection_from_rect(self, rect, drag_start_selection): iterates over all visible ImageCard instances, checks if their geometry intersects rect (mapped to the content widget's coordinate space), and selects or deselects accordingly. With Ctrl held, starts from drag_start_selection and toggles intersecting cards rather than replacing selection.
Implement select_all_images(self): selects all ImageCard instances in the current view and updates self.selected_image_ids.
Add Ctrl+A keypress handler on DashboardWindow to call select_all_images().
Update _on_image_clicked to support Ctrl-click: if Ctrl is held when the clicked signal fires, add the image to the selection rather than toggling it exclusively. This requires forwarding the modifier state from ImageCard.mousePressEvent — either by emitting a separate ctrl_clicked = pyqtSignal(int) signal or by including a modifiers parameter in the existing clicked signal.

Phase 3

Implement _on_image_shift_clicked(self, image_id): selects a contiguous range from the last-clicked card to the current one, based on visual order in the layout. Track self._last_clicked_image_id in _on_image_clicked to serve as the range anchor.
Update _on_image_clicked to check for Shift modifier (via the forwarded modifier state) and delegate to _on_image_shift_clicked if held.
Implement keyboard navigation handler _on_image_key_pressed(self, image_id, event):

Arrow keys: move focus to the adjacent card in the grid (up/down/left/right based on layout position). Combine with Shift to extend the selection range.
Delete: call _on_bulk_delete_images() if any images are selected.
F2: open the rename dialog for the currently focused image (single selection only).


Connect each ImageCard.key_pressed signal to _on_image_key_pressed.


Verification Plan
Automated Tests
UI interaction is primarily manual. Run the main application and verify it compiles and imports without errors before manual testing.

Manual Verification (to be done by the user, not an automated test)
Phase 1

Individual toggle: Single-click an image. The card should highlight; clicking it again should deselect it.
Double-click preview: Double-click an image card. The preview dialog should open.
Enter to open: Select a card and press Enter. The preview dialog should open.
Empty-space click: Select several images, then click an empty area of the dashboard. All cards should deselect.
Bulk move: Select multiple images, right-click, choose Move to Folder, and pick a target. All selected images should move.
Bulk delete: Select multiple images, right-click, choose Delete, and confirm. All selected images should be deleted.
Bulk drag to folder: Select multiple images and drag one onto a FolderCard. All selected images should move to that folder.
Bulk trash drop: Drag a multi-selection onto the Trash zone. A confirmation prompt should appear, and all selected images should be deleted on confirm.
Right-click unselected: With images 1–3 selected, right-click image 4. The selection should clear, image 4 should become selected, and a single-image context menu should appear.
Right-click selected: With images 1–3 selected, right-click image 2. The selection should be preserved and a bulk context menu should appear.
Accidental drag guard: Click an image with a slight mouse drift. The selection should toggle and a drag should not start.

Phase 2

Marquee selection: Click and drag over empty space across several cards. A rubber-band box should be drawn and all intersected cards should be selected.
Ctrl+marquee additive: Hold Ctrl and drag a marquee over new cards. The previous selection should be preserved and the intersected cards should be added to it.
Marquee ignores non-cards: Drag the marquee over folder cards, the trash zone, and labels. Only ImageCard instances should be selected.
Ctrl+A: Press Ctrl+A. All images in the current view should be selected.
Ctrl+click additive: Hold Ctrl and click individual images. Each click should add or remove that card without clearing the rest of the selection.

Phase 3

Shift-click range: Click image 1, then Shift-click image 8. Images 1 through 8 should be selected in visual order.
Shift+arrow extend: Select a card, then hold Shift and press an arrow key. The selection should extend in the arrow direction.
Delete key: Select images and press Delete. A confirmation prompt should appear and all selected images should be deleted on confirm.
F2 rename: Focus a single card and press F2. The rename dialog should open for that image.
Arrow navigation: Press arrow keys while a card is focused. Focus should move to the adjacent card in the grid.