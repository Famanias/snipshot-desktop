# CHANGELOG
# ─────────────────────────────────────────────────────────────────────
# - Added instructional overlay ("Click and drag … / Press Esc to cancel")
# - Replaced QRubberBand with custom paintEvent selection rect:
#     · primary-at-15% fill, 2px primary border, 8×8 corner handles
# - Increased overlay opacity from 0.15 → 0.25
# - Added floating HUD label showing "W × H px" during drag
# - Instruction label hides on first mouse press
# ─────────────────────────────────────────────────────────────────────

"""
SnipShot Desktop - Screen Capture Widget

Allows users to select a region of the screen to capture.
"""

import time
import os
import tempfile
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt5.QtGui import QMouseEvent, QPixmap, QPainter, QPen, QBrush, QColor
from PyQt5.QtCore import Qt, QPoint, QRect, pyqtSignal


class CaptureWidget(QWidget):
    """
    Full-screen overlay for screen region capture.

    Signals:
        captured: Emitted when capture is complete with (QPixmap, temp_path)
        cancelled: Emitted when capture is cancelled
    """

    captured = pyqtSignal(QPixmap, str)
    cancelled = pyqtSignal()

    _PRIMARY = QColor(14, 165, 233)        # #0EA5E9
    _FILL = QColor(14, 165, 233, 38)       # primary at ~15 %
    _HANDLE_SIZE = 8

    def __init__(self, parent=None):
        super().__init__(None)  # No parent — independent window
        self.parent_window = parent

        # Hide parent window during capture
        if self.parent_window:
            self.parent_window.hide()

        self.setMouseTracking(True)

        # Full-screen overlay
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.setGeometry(screen_geometry)

        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setWindowOpacity(0.25)

        # Selection state
        self.origin = QPoint()
        self.selection_rect: QRect | None = None
        self.imgmap = None
        self._dragging = False
        self._instruction_visible = True

        # Instruction overlay
        self._instruction = QLabel(self)
        self._instruction.setAlignment(Qt.AlignCenter)
        self._instruction.setText(
            "Click and drag to select a region\nPress Esc to cancel"
        )
        self._instruction.setStyleSheet(
            "QLabel {"
            "  color: white;"
            "  background-color: rgba(0, 0, 0, 153);"
            "  border-radius: 12px;"
            "  padding: 12px 20px;"
            "  font-size: 15px;"
            "}"
        )
        self._instruction.adjustSize()
        # Centre on screen
        ix = (screen_geometry.width() - self._instruction.width()) // 2
        iy = (screen_geometry.height() - self._instruction.height()) // 2
        self._instruction.move(ix, iy)

        # Dimension HUD
        self._hud = QLabel(self)
        self._hud.setStyleSheet(
            "QLabel {"
            "  color: white;"
            "  background-color: rgba(0, 0, 0, 153);"
            "  border-radius: 8px;"
            "  padding: 4px 10px;"
            "  font-size: 13px;"
            "}"
        )
        self._hud.hide()

        # Cross cursor
        QApplication.setOverrideCursor(Qt.CrossCursor)

        # Capture screenshot after a short delay for window hiding
        time.sleep(0.31)
        self.screenshot = screen.grabWindow(0)

    # ── Paint ──────────────────────────────────────────────────────────

    def paintEvent(self, event):
        if self.selection_rect and not self.selection_rect.isNull():
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            rect = self.selection_rect.normalized()

            # Fill
            painter.setBrush(QBrush(self._FILL))
            painter.setPen(Qt.NoPen)
            painter.drawRect(rect)

            # Border
            pen = QPen(self._PRIMARY, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)

            # Corner handles
            hs = self._HANDLE_SIZE
            painter.setBrush(QBrush(self._PRIMARY))
            painter.setPen(Qt.NoPen)
            corners = [
                QRect(rect.left() - hs // 2, rect.top() - hs // 2, hs, hs),
                QRect(rect.right() - hs // 2, rect.top() - hs // 2, hs, hs),
                QRect(rect.left() - hs // 2, rect.bottom() - hs // 2, hs, hs),
                QRect(rect.right() - hs // 2, rect.bottom() - hs // 2, hs, hs),
            ]
            for cr in corners:
                painter.drawRect(cr)

            painter.end()

    # ── Mouse events ───────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            # Hide instruction on first press
            if self._instruction_visible:
                self._instruction.hide()
                self._instruction_visible = False

            self.origin = event.pos()
            self.selection_rect = QRect(self.origin, self.origin)
            self._dragging = True

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self.selection_rect = QRect(self.origin, event.pos()).normalized()
            self.update()
            self._update_hud()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self._hud.hide()

            rect = self.selection_rect
            if rect is None or rect.width() < 10 or rect.height() < 10:
                self._cancel()
                return

            # Crop screenshot to selection
            self.imgmap = self.screenshot.copy(rect)
            QApplication.restoreOverrideCursor()

            # Copy to clipboard
            clipboard = QApplication.clipboard()
            clipboard.setPixmap(self.imgmap)

            # Save to temp folder
            temp_dir = tempfile.gettempdir()
            temp_path = os.path.join(temp_dir, "snipshot_capture.png")
            self.imgmap.save(temp_path)

            # Hide and close overlay BEFORE emitting signal
            self.hide()
            QApplication.processEvents()

            if self.parent_window:
                self.parent_window.show()
                QApplication.processEvents()

            self.captured.emit(self.imgmap, temp_path)
            self.close()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape:
            self._cancel()

    # ── Helpers ────────────────────────────────────────────────────────

    def _update_hud(self):
        if self.selection_rect is None:
            return
        r = self.selection_rect.normalized()
        self._hud.setText(f"{r.width()} \u00d7 {r.height()} px")
        self._hud.adjustSize()
        hx = r.left() + (r.width() - self._hud.width()) // 2
        hy = r.top() - self._hud.height() - 8
        if hy < 0:
            hy = r.bottom() + 8
        self._hud.move(hx, hy)
        self._hud.show()

    def _cancel(self):
        """Cancel the capture."""
        QApplication.restoreOverrideCursor()
        self.hide()
        QApplication.processEvents()

        if self.parent_window:
            self.parent_window.show()
            QApplication.processEvents()

        self.cancelled.emit()
        self.close()
