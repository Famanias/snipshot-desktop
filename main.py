"""
SnipShot Desktop Application

A screen capture and manga translation tool with cloud storage.

Features:
- Snip/capture screen regions
- Translate manga/comics to English
- Save translations to cloud (Supabase)
- Organize in folders (Google Drive-style)

Usage:
    python main.py
"""

import sys
import os
import ctypes
import ctypes.wintypes
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap

from config import APP_NAME, APP_VERSION, DEFAULT_SHORTCUT_KEY
from ui import (
    MAIN_STYLESHEET,
    LoginWindow,
    RegisterWindow, 
    DashboardWindow,
    CaptureWidget,
    TranslationWindow
)
from api import api_client
from utils import resource_path

# ── Win32 global hotkey support ────────────────────────────────────────────
_WM_HOTKEY = 0x0312       # Windows WM_HOTKEY message
_MOD_NOREPEAT = 0x4000    # Suppress repeated triggers while key is held
_SNIP_HOTKEY_ID = 1       # Arbitrary ID for our registered hotkey

# Qt key code → Windows Virtual Key code.
# ASCII range 0x20–0x7E maps 1-to-1 and is handled at runtime.
_QT_TO_VK = {
    0x01000009: 0x2C,  # Key_Print  (Print Screen) → VK_SNAPSHOT
    0x01000030: 0x70,  # Key_F1  → VK_F1
    0x01000031: 0x71,  # Key_F2
    0x01000032: 0x72,  # Key_F3
    0x01000033: 0x73,  # Key_F4
    0x01000034: 0x74,  # Key_F5
    0x01000035: 0x75,  # Key_F6
    0x01000036: 0x76,  # Key_F7
    0x01000037: 0x77,  # Key_F8
    0x01000038: 0x78,  # Key_F9
    0x01000039: 0x79,  # Key_F10
    0x0100003A: 0x7A,  # Key_F11
    0x0100003B: 0x7B,  # Key_F12
    0x01000010: 0x24,  # Key_Home
    0x01000011: 0x23,  # Key_End
    0x01000016: 0x21,  # Key_PageUp
    0x01000017: 0x22,  # Key_PageDown
    0x01000012: 0x25,  # Key_Left
    0x01000013: 0x26,  # Key_Up
    0x01000014: 0x27,  # Key_Right
    0x01000015: 0x28,  # Key_Down
    0x01000006: 0x2D,  # Key_Insert
    0x01000007: 0x2E,  # Key_Delete
}


def _qt_key_to_vk(qt_key: int):
    """Return the Windows Virtual Key code for a Qt key, or None if not mappable."""
    if qt_key in _QT_TO_VK:
        return _QT_TO_VK[qt_key]
    # Printable ASCII: Qt code == Windows VK code
    if 0x20 <= qt_key <= 0x7E:
        return qt_key
    return None


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Manages navigation between:
    - Login screen
    - Register screen
    - Dashboard (main app)
    
    Also handles screen capture overlay.
    """
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)
        
        # Stacked widget for screen navigation
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Create screens
        self._create_screens()
        
        # Start at login
        self.stack.setCurrentWidget(self.login_screen)
        
        # Capture widget (created on demand)
        self.capture_widget = None

        # System-wide hotkey (Win32 RegisterHotKey)
        self._current_hotkey_vk = None
        self._install_snip_shortcut(DEFAULT_SHORTCUT_KEY)
    
    def _create_screens(self):
        """Create all application screens"""
        
        # Login screen
        self.login_screen = LoginWindow()
        self.login_screen.login_success.connect(self._on_login_success)
        self.login_screen.show_register.connect(self._show_register)
        self.stack.addWidget(self.login_screen)
        
        # Register screen
        self.register_screen = RegisterWindow()
        self.register_screen.register_success.connect(self._on_register_success)
        self.register_screen.show_login.connect(self._show_login)
        self.stack.addWidget(self.register_screen)
        
        # Dashboard
        self.dashboard = DashboardWindow()
        self.dashboard.logout_requested.connect(self._on_logout)
        self.dashboard.capture_requested.connect(self._start_capture)
        self.dashboard.upload_requested.connect(self._on_upload_image)
        self.dashboard.shortcut_changed.connect(self._install_snip_shortcut)
        self.stack.addWidget(self.dashboard)
    
    def _show_login(self):
        """Show login screen"""
        self.register_screen.clear_fields()
        self.stack.setCurrentWidget(self.login_screen)
        self.setMinimumSize(900, 600)
        self.resize(900, 600)
    
    def _show_register(self):
        """Show register screen"""
        self.login_screen.clear_fields()
        self.stack.setCurrentWidget(self.register_screen)
        self.setMinimumSize(900, 600)
        self.resize(900, 600)
    
    def _show_dashboard(self):
        """Show main dashboard"""
        self.stack.setCurrentWidget(self.dashboard)
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)
        
        # Load user info and files
        self.dashboard.load_user_info()
        self.dashboard.refresh()
    
    def _on_login_success(self):
        """Handle successful login"""
        self.login_screen.clear_fields()
        self._show_dashboard()
    
    def _on_register_success(self):
        """Handle successful registration (with auto-login)"""
        self.register_screen.clear_fields()
        self._show_dashboard()
    
    def _install_snip_shortcut(self, key: int = None):
        """
        Register (or re-register) a system-wide hotkey via Win32 RegisterHotKey.
        Works even when the application is in the background or minimised.
        """
        if key is None:
            key = DEFAULT_SHORTCUT_KEY

        user32 = ctypes.windll.user32
        hwnd = int(self.winId())

        # Unregister the previous hotkey before registering a new one
        if self._current_hotkey_vk is not None:
            user32.UnregisterHotKey(hwnd, _SNIP_HOTKEY_ID)
            self._current_hotkey_vk = None

        vk = _qt_key_to_vk(key)
        if vk is None:
            return  # Key not mappable to a Win32 Virtual Key

        # Try first with MOD_NOREPEAT (Win8+), fall back without it
        success = user32.RegisterHotKey(hwnd, _SNIP_HOTKEY_ID, _MOD_NOREPEAT, vk)
        if not success:
            success = user32.RegisterHotKey(hwnd, _SNIP_HOTKEY_ID, 0, vk)

        if success:
            self._current_hotkey_vk = vk

    def nativeEvent(self, eventType, message):
        """Intercept WM_HOTKEY to trigger the snip shortcut globally."""
        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(
                int(message),
                ctypes.POINTER(ctypes.wintypes.MSG)
            ).contents
            if msg.message == _WM_HOTKEY and msg.wParam == _SNIP_HOTKEY_ID:
                self._start_capture()
                return True, 0
        return super().nativeEvent(eventType, message)

    def closeEvent(self, event):
        """Unregister the hotkey when the window closes."""
        if self._current_hotkey_vk is not None:
            ctypes.windll.user32.UnregisterHotKey(int(self.winId()), _SNIP_HOTKEY_ID)
        super().closeEvent(event)

    def _on_logout(self):
        """Handle logout"""
        self._show_login()
    
    def _start_capture(self):
        """Start screen capture"""
        # Ignore if not logged in or a capture is already in progress
        if not api_client.is_authenticated:
            return
        if self.capture_widget is not None and self.capture_widget.isVisible():
            return

        self.hide()

        # Small delay to ensure window is hidden
        QTimer.singleShot(100, self._do_capture)
    
    def _do_capture(self):
        """Actually perform the capture"""
        self.capture_widget = CaptureWidget(self)
        self.capture_widget.captured.connect(self._on_capture_complete)
        self.capture_widget.cancelled.connect(self._on_capture_cancelled)
        self.capture_widget.show()
    
    def _on_capture_complete(self, pixmap: QPixmap, temp_path: str):
        """Handle completed capture"""
        # Note: Parent window is already shown by CaptureWidget
        
        # Check if user is authenticated
        if not api_client.is_authenticated:
            return
        
        # Open translation dialog
        self.translation_window = TranslationWindow(
            pixmap,
            self,
            target_language=self.dashboard.get_target_language(),
            translation_config=self.dashboard.get_translation_config(),
        )
        self.translation_window.saved.connect(self.dashboard.refresh)
        self.translation_window.exec_()

    def _on_capture_cancelled(self):
        """Handle cancelled capture"""
        # Note: Parent window is already shown by CaptureWidget
        pass

    def _on_upload_image(self, file_path: str):
        """Handle image upload — open TranslationWindow with the chosen file"""
        if not api_client.is_authenticated:
            return

        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Upload Error", f"Could not load image:\n{file_path}")
            return

        self.translation_window = TranslationWindow(
            pixmap,
            self,
            target_language=self.dashboard.get_target_language(),
            translation_config=self.dashboard.get_translation_config(),
        )
        self.translation_window.saved.connect(self.dashboard.refresh)
        self.translation_window.exec_()


def main():
    """Application entry point"""
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # Set application style
    app.setStyleSheet(MAIN_STYLESHEET)
    
    # Set window icon (if exists)
    icon_path = resource_path("resources/icon.ico")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
