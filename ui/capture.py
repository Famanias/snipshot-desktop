"""
SnipShot Desktop - Screen Capture Widget

Allows users to select a region of the screen to capture.
Based on the original Capturer.py implementation.
"""

import time
import os
import tempfile
from PyQt5.QtWidgets import QWidget, QApplication, QRubberBand
from PyQt5.QtGui import QMouseEvent, QPixmap
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

    def __init__(self, parent=None):
        super().__init__(None)  # No parent - independent window
        self.parent_window = parent
        
        # Hide parent window during capture
        if self.parent_window:
            self.parent_window.hide()
        
        self.setMouseTracking(True)
        
        # Full screen overlay
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        self.setGeometry(screen_geometry)
        
        # Window flags for overlay
        self.setWindowFlags(
            Qt.FramelessWindowHint | 
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setWindowOpacity(0.15)
        
        # Rubber band for selection
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        self.origin = QPoint()
        self.imgmap = None
        
        # Set cross cursor
        QApplication.setOverrideCursor(Qt.CrossCursor)
        
        # Capture screenshot (after small delay for window to hide)
        time.sleep(0.31)
        self.screenshot = screen.grabWindow(0)  # Grab entire screen

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.origin = event.pos()
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())
            self.rubber_band.show()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self.origin.isNull():
            self.rubber_band.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self.rubber_band.hide()
            
            rect = self.rubber_band.geometry()
            
            # Check if selection is valid (not too small)
            if rect.width() < 10 or rect.height() < 10:
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
            
            # IMPORTANT: Hide and close the overlay BEFORE emitting signal
            # This ensures the snipping UI is removed before translation starts
            self.hide()
            QApplication.processEvents()  # Process hide event immediately
            
            # Show parent window
            if self.parent_window:
                self.parent_window.show()
                QApplication.processEvents()  # Ensure parent is shown
            
            # Emit signal with captured image (overlay is now hidden)
            self.captured.emit(self.imgmap, temp_path)
            
            self.close()

    def keyPressEvent(self, event) -> None:
        # Cancel on Escape
        if event.key() == Qt.Key_Escape:
            self._cancel()
    
    def _cancel(self):
        """Cancel the capture"""
        QApplication.restoreOverrideCursor()
        
        # Hide the overlay BEFORE emitting signal
        self.hide()
        QApplication.processEvents()
        
        if self.parent_window:
            self.parent_window.show()
            QApplication.processEvents()
        
        self.cancelled.emit()
        self.close()
