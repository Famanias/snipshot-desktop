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
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QSystemTrayIcon, QMenu, QAction
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon, QPixmap

from config import APP_NAME, APP_VERSION
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
    
    def _on_logout(self):
        """Handle logout"""
        self._show_login()
    
    def _start_capture(self):
        """Start screen capture"""
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
            target_language=self.dashboard.get_target_language()
        )
        self.translation_window.saved.connect(self.dashboard.refresh)
        self.translation_window.exec_()
    
    def _on_capture_cancelled(self):
        """Handle cancelled capture"""
        # Note: Parent window is already shown by CaptureWidget
        pass


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
