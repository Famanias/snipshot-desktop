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
import logging
import traceback
from pathlib import Path
import platformdirs
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QStackedWidget, QSystemTrayIcon, QMenu, QAction,
    QWidget, QHBoxLayout, QFrame, QLabel, QPushButton, QShortcut
)
from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QThread, QBuffer, QIODevice
from PyQt5.QtGui import QIcon, QPixmap, QKeySequence

# Setup crash logging
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


from config import APP_NAME, APP_VERSION, DEFAULT_SHORTCUT_KEY, DEFAULT_CONTINUOUS_SHORTCUT_KEY, DEFAULT_CONTINUOUS_SNIP_INTERVAL
from ui import (
    theme,
    get_main_stylesheet,
    LoginWindow,
    RegisterWindow, 
    DashboardWindow,
    CaptureWidget,
    TranslationWindow
)
from api import api_client
from utils import resource_path

_AUTH_WINDOW_SIZE = (1200, 800)
_DASHBOARD_WINDOW_SIZE = (1200, 800)

# ── Win32 global hotkey support ────────────────────────────────────────────
_WM_HOTKEY = 0x0312       # Windows WM_HOTKEY message
_MOD_NOREPEAT = 0x4000    # Suppress repeated triggers while key is held
_SNIP_HOTKEY_ID = 1       # Arbitrary ID for our registered hotkey
_CONTINUOUS_HOTKEY_ID = 2  # Arbitrary ID for our continuous registered hotkey

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


class ContinuousModeHUD(QWidget):
    """
    A floating, stays-on-top, draggable HUD overlay that shows
    the state of Continuous Snipping Mode.
    """
    def __init__(self, main_window):
        super().__init__(None) # No parent so it can float freely
        self.main_window = main_window
        
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.SubWindow |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(180, 48)
        
        self.drag_position = QPoint()
        self._setup_ui()
        self.set_state("ready")

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Background frame for styling
        self.container = QFrame(self)
        self.container.setObjectName("Container")
        self.container.setFixedSize(180, 48)
        
        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(16, 0, 16, 0)
        container_layout.setSpacing(12)
        
        # Status Dot
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        
        # Status Label
        self.label = QLabel("Continuous: Ready")
        
        container_layout.addWidget(self.dot)
        container_layout.addWidget(self.label)
        container_layout.addStretch()
        
        layout.addWidget(self.container)
        
        self._apply_style()
        theme.theme_changed.connect(self._apply_style)

    def _apply_style(self):
        c = theme.c
        # Beautiful glassmorphism style
        self.container.setStyleSheet(f"""
            QFrame#Container {{
                background-color: {theme.rgba('surface', 0.85)};
                border: 1px solid {c['border']};
                border-radius: 24px;
            }}
        """)
        self.label.setStyleSheet(f"""
            QLabel {{
                color: {c['text']};
                font-size: 12px;
                font-weight: 600;
                background-color: transparent;
                border: none;
            }}
        """)

    def set_state(self, state: str):
        """
        Set status indicator state:
        - "ready": waiting for user to press hotkey (Green dot)
        - "capturing": capture overlay is active (Blue dot)
        - "translating": translating the image (Orange/Yellow dot)
        """
        if state == "ready":
            self.dot.setStyleSheet("border-radius: 5px; background-color: #10B981;") # Green
            self.label.setText("Continuous: Ready")
        elif state == "capturing":
            self.dot.setStyleSheet("border-radius: 5px; background-color: #0EA5E9;") # Blue
            self.label.setText("Continuous: Snipping")
        elif state == "translating":
            self.dot.setStyleSheet("border-radius: 5px; background-color: #F59E0B;") # Yellow/Orange
            self.label.setText("Continuous: Translating")

    # Draggable functionality
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.drag_position)
            event.accept()


class QueuedTranslationWorker(QThread):
    """
    Background worker that handles translation AND saving sequentially.
    """
    progress = pyqtSignal(str, int)  # status text, progress percentage
    finished = pyqtSignal(dict)      # final saved image database record
    error = pyqtSignal(str)          # error message

    def __init__(
        self,
        image_bytes: bytes,
        filename: str,
        folder_id: int = None,
        target_language: str = "ENG",
        translation_config: dict = None,
    ):
        super().__init__()
        self.image_bytes = image_bytes
        self.filename = filename
        self.folder_id = folder_id
        self.target_language = target_language
        self.translation_config = translation_config

    def run(self):
        try:
            import copy
            from config import DEFAULT_TRANSLATION_CONFIG
            
            # Step 1: Translate
            self.progress.emit("translating", 10)
            
            config = copy.deepcopy(
                self.translation_config if self.translation_config is not None
                else DEFAULT_TRANSLATION_CONFIG
            )
            config.setdefault("translator", {})
            config["translator"]["target_lang"] = self.target_language
            
            self.progress.emit("translating", 30)
            res = api_client.translate_image(self.image_bytes, config=config)
            
            if not res.get("success"):
                self.error.emit(res.get("error", "Translation failed"))
                return
                
            translated_bytes = res["data"].get("image_bytes")
            if not translated_bytes:
                self.error.emit("Translated image bytes are empty")
                return

            self.progress.emit("translating", 70)
            
            # Step 2: Save to Account
            self.progress.emit("saving", 85)
            save_res = api_client.save_image_from_bytes(
                translated_bytes,
                self.filename,
                self.folder_id,
                source_language="JPN",
                target_language=self.target_language,
            )
            
            if not save_res.get("success"):
                self.error.emit(save_res.get("error", "Save failed"))
                return
                
            self.progress.emit("completed", 100)
            self.finished.emit(save_res["data"])
            
        except Exception as e:
            self.error.emit(str(e))


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
        self.setMinimumSize(*_AUTH_WINDOW_SIZE)
        self.resize(*_AUTH_WINDOW_SIZE)
        
        # Stacked widget for screen navigation
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        
        # Create screens
        self._create_screens()
        
        # Start at login with the same auth-screen sizing used after sign out
        self._show_login()
        
        # Capture widget (created on demand)
        self.capture_widget = None

        # System-wide hotkey (Win32 RegisterHotKey)
        self._current_hotkey_vk = None
        self._current_continuous_hotkey_vk = None
        self._translation_in_progress = False
        self.continuous_hud = None
        self.translation_queue = []
        self.active_worker = None
        self._queue_snip_counter = 0
        
        from PyQt5.QtCore import QSettings
        settings = QSettings("SnipShot", "SnipShot")
        self._snip_interval_ms = settings.value("continuous_snip_interval", DEFAULT_CONTINUOUS_SNIP_INTERVAL, type=int)

        self._snip_local_shortcut = None
        self._continuous_local_shortcut = None
        self._install_snip_shortcut(DEFAULT_SHORTCUT_KEY)
        self._install_continuous_snip_shortcut(DEFAULT_CONTINUOUS_SHORTCUT_KEY)
    
    def _create_screens(self):
        """Create all application screens"""
        
        # Login screen
        self.login_screen = LoginWindow()
        self.login_screen.login_success.connect(self._on_login_success)
        self.login_screen.show_register.connect(self._show_register)
        self.login_screen.offline_mode_requested.connect(self._on_offline_mode)
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
        self.dashboard.continuous_mode_changed.connect(self._on_continuous_mode_changed)
        self.dashboard.continuous_shortcut_changed.connect(self._install_continuous_snip_shortcut)
        self.dashboard.snip_interval_changed.connect(self._on_snip_interval_changed)
        self.dashboard.cancel_queue_item_requested.connect(self._on_cancel_queue_item)
        self.stack.addWidget(self.dashboard)
    
    def _show_login(self):
        """Show login screen"""
        self.register_screen.clear_fields()
        self.stack.setCurrentWidget(self.login_screen)
        self.setMinimumSize(*_AUTH_WINDOW_SIZE)
        self.resize(*_AUTH_WINDOW_SIZE)
    
    def _show_register(self):
        """Show register screen"""
        self.login_screen.clear_fields()
        self.stack.setCurrentWidget(self.register_screen)
        self.setMinimumSize(*_AUTH_WINDOW_SIZE)
        self.resize(*_AUTH_WINDOW_SIZE)
    
    def _show_dashboard(self):
        """Show main dashboard"""
        self.stack.setCurrentWidget(self.dashboard)
        self.setMinimumSize(*_DASHBOARD_WINDOW_SIZE)
        self.resize(*_DASHBOARD_WINDOW_SIZE)
        
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

    def _on_offline_mode(self):
        """Switch to offline mode — use local SQLite + filesystem storage."""
        from PyQt5.QtWidgets import QMessageBox
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QCursor
        import httpx
        from config import LOCAL_TRANSLATOR_URL

        # Set wait cursor during check
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        backend_active = False
        error_msg = ""
        try:
            with httpx.Client(timeout=2.0) as client:
                # Perform a request to verify the server is running and reachable
                client.get(LOCAL_TRANSLATOR_URL)
                backend_active = True
        except Exception as e:
            error_msg = str(e)
        finally:
            QApplication.restoreOverrideCursor()

        if not backend_active:
            QMessageBox.critical(
                self,
                "Local Backend Offline",
                f"Could not connect to the local translator backend at {LOCAL_TRANSLATOR_URL}.\n\n"
                "Please make sure your local backend repository is running before using Offline Mode.\n\n"
                "To launch it, open a terminal and run:\n"
                "  cd C:\\Users\\your-username\\snipshot-backend\n"
                "  python main.py\n\n"
                f"Details: {error_msg}"
            )
            return

        from local_api import LocalAPIClient
        self._local_client = LocalAPIClient(translator_url=LOCAL_TRANSLATOR_URL)
        api_client.set_impl(self._local_client)
        self.login_screen.clear_fields()
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

        # Re-create active window local fallback shortcut
        if hasattr(self, "_snip_local_shortcut") and self._snip_local_shortcut is not None:
            self._snip_local_shortcut.setEnabled(False)
            self._snip_local_shortcut.deleteLater()
            self._snip_local_shortcut = None

        self._snip_local_shortcut = QShortcut(QKeySequence(key), self)
        self._snip_local_shortcut.setContext(Qt.WindowShortcut)
        self._snip_local_shortcut.activated.connect(lambda: self._start_capture(continuous=False))

        vk = _qt_key_to_vk(key)
        if vk is None:
            return  # Key not mappable to a Win32 Virtual Key

        # Try first with MOD_NOREPEAT (Win8+), fall back without it
        success = user32.RegisterHotKey(hwnd, _SNIP_HOTKEY_ID, _MOD_NOREPEAT, vk)
        if not success:
            success = user32.RegisterHotKey(hwnd, _SNIP_HOTKEY_ID, 0, vk)

        if success:
            self._current_hotkey_vk = vk

    def _install_continuous_snip_shortcut(self, key: int = None):
        """
        Register (or re-register) a system-wide hotkey via Win32 RegisterHotKey for continuous snip.
        """
        if key is None:
            key = DEFAULT_CONTINUOUS_SHORTCUT_KEY

        user32 = ctypes.windll.user32
        hwnd = int(self.winId())

        if self._current_continuous_hotkey_vk is not None:
            user32.UnregisterHotKey(hwnd, _CONTINUOUS_HOTKEY_ID)
            self._current_continuous_hotkey_vk = None

        # Re-create active window local fallback shortcut
        if hasattr(self, "_continuous_local_shortcut") and self._continuous_local_shortcut is not None:
            self._continuous_local_shortcut.setEnabled(False)
            self._continuous_local_shortcut.deleteLater()
            self._continuous_local_shortcut = None

        self._continuous_local_shortcut = QShortcut(QKeySequence(key), self)
        self._continuous_local_shortcut.setContext(Qt.WindowShortcut)
        self._continuous_local_shortcut.activated.connect(lambda: self._start_capture(continuous=True))

        vk = _qt_key_to_vk(key)
        if vk is None:
            return

        success = user32.RegisterHotKey(hwnd, _CONTINUOUS_HOTKEY_ID, _MOD_NOREPEAT, vk)
        if not success:
            success = user32.RegisterHotKey(hwnd, _CONTINUOUS_HOTKEY_ID, 0, vk)

        if success:
            self._current_continuous_hotkey_vk = vk

    def nativeEvent(self, eventType, message):
        """Intercept WM_HOTKEY to trigger the snip shortcuts globally."""
        if eventType == b"windows_generic_MSG":
            msg = ctypes.cast(
                int(message),
                ctypes.POINTER(ctypes.wintypes.MSG)
            ).contents
            if msg.message == _WM_HOTKEY:
                if msg.wParam == _SNIP_HOTKEY_ID:
                    self._start_capture(continuous=False)
                    return True, 0
                elif msg.wParam == _CONTINUOUS_HOTKEY_ID:
                    self._start_capture(continuous=True)
                    return True, 0
        return super().nativeEvent(eventType, message)

    def closeEvent(self, event):
        """Unregister hotkeys and close HUD when the window closes."""
        user32 = ctypes.windll.user32
        hwnd = int(self.winId())
        if self._current_hotkey_vk is not None:
            user32.UnregisterHotKey(hwnd, _SNIP_HOTKEY_ID)
        if self._current_continuous_hotkey_vk is not None:
            user32.UnregisterHotKey(hwnd, _CONTINUOUS_HOTKEY_ID)
        if hasattr(self, "continuous_hud") and self.continuous_hud is not None:
            self.continuous_hud.close()
        super().closeEvent(event)

    def _on_logout(self):
        """Handle logout"""
        api_client.reset()
        self._show_login()
        if hasattr(self, "continuous_hud") and self.continuous_hud is not None:
            self.continuous_hud.hide()
        if hasattr(self, "translation_queue") and self.translation_queue:
            for item in list(self.translation_queue):
                self.dashboard.update_queue_item_ui(item["item_id"], "cancelled")
            self.translation_queue.clear()
        self._clear_active_worker()

    def _on_continuous_mode_changed(self, enabled: bool):
        self._update_indicator()
        if enabled:
            self._start_capture()
        else:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

    def _on_snip_interval_changed(self, interval: int):
        self._snip_interval_ms = interval

    def _update_indicator(self):
        if (hasattr(self, "dashboard") and 
            self.dashboard.continuous_mode_enabled and 
            api_client.is_authenticated and 
            self.stack.currentWidget() == self.dashboard):
            
            if self.continuous_hud is None:
                self.continuous_hud = ContinuousModeHUD(self)
            
            # Position at the bottom-right corner of screen (respecting taskbar)
            available_rect = QApplication.primaryScreen().availableGeometry()
            self.continuous_hud.move(
                available_rect.right() - self.continuous_hud.width() - 20,
                available_rect.bottom() - self.continuous_hud.height() - 20
            )
            self.continuous_hud.show()
            self.continuous_hud.raise_()
            
            if self.capture_widget is not None and self.capture_widget.isVisible():
                self.continuous_hud.set_state("capturing")
            elif self._translation_in_progress:
                self.continuous_hud.set_state("translating")
            else:
                self.continuous_hud.set_state("ready")
        else:
            if hasattr(self, "continuous_hud") and self.continuous_hud is not None:
                self.continuous_hud.hide()

    def _start_capture(self, continuous: bool | None = None):
        """Start screen capture"""
        # Ignore if not logged in, not on the dashboard
        if self.stack.currentWidget() != self.dashboard:
            return
        if not api_client.is_authenticated:
            return
            
        if continuous is not None:
            self.dashboard._set_continuous_mode(continuous)

        # Ignore if a capture is already in progress
        if self.capture_widget is not None and self.capture_widget.isVisible():
            return

        self._update_indicator()
        self.hide()

        # Small delay to ensure window is hidden
        QTimer.singleShot(100, self._do_capture)

    def _do_capture(self):
        """Actually perform the capture"""
        self.capture_widget = CaptureWidget(self)
        if self.dashboard.continuous_mode_enabled:
            self.capture_widget.show_parent_on_close = False
        self.capture_widget.captured.connect(self._on_capture_complete)
        self.capture_widget.cancelled.connect(self._on_capture_cancelled)
        self.capture_widget.show()
        self.capture_widget.activateWindow()
        self.capture_widget.setFocus()
        self._update_indicator()
    
    def _on_capture_complete(self, pixmap: QPixmap, temp_path: str):
        """Handle completed capture"""
        # Note: Parent window is already shown by CaptureWidget (unless show_parent_on_close is False)
        
        # Check if user is authenticated
        if not api_client.is_authenticated:
            return

        if self.dashboard.continuous_mode_enabled:
            # Bypass modal and add directly to queue
            self._add_to_queue(pixmap)
            
            # Immediately trigger next capture if continuous is still enabled
            if self.dashboard.continuous_mode_enabled:
                QTimer.singleShot(self._snip_interval_ms, self._start_capture)
        else:
            self._add_to_queue(pixmap, is_single=True)

    def _on_capture_cancelled(self):
        """Handle cancelled capture"""
        # Force restore override cursors to prevent lingering crosshairs
        while QApplication.overrideCursor() is not None:
            QApplication.restoreOverrideCursor()

        # Note: Parent window is already shown by CaptureWidget (unless show_parent_on_close is False)
        if self.dashboard.continuous_mode_enabled:
            self.dashboard._set_continuous_mode(False)
            
        self.show()
        self.activateWindow()
        self.setFocus()

    def _on_upload_image(self, file_paths: list):
        """Handle multiple image uploads — queue them for background translation"""
        if not api_client.is_authenticated:
            return

        from PyQt5.QtWidgets import QMessageBox
        
        queued_any = False
        
        for file_path in file_paths:
            pixmap = QPixmap(file_path)
            if pixmap.isNull():
                QMessageBox.warning(self, "Upload Error", f"Could not load image:\n{file_path}")
                continue

            self._queue_snip_counter += 1
            item_id = f"upload_{self._queue_snip_counter}"
            filename = os.path.basename(file_path)
            
            folder_id = self.dashboard.current_folder_id
            target_language = self.dashboard.get_target_language()
            
            # Convert QPixmap to bytes (PNG format)
            buffer = QBuffer()
            buffer.open(QIODevice.WriteOnly)
            pixmap.save(buffer, "PNG")
            image_bytes = buffer.data().data()
            
            item = {
                "item_id": item_id,
                "image_bytes": image_bytes,
                "filename": filename,
                "folder_id": folder_id,
                "target_language": target_language,
                "thumbnail": pixmap
            }
            
            self.translation_queue.append(item)
            self.dashboard.add_queue_item_ui(item_id, filename, target_language, pixmap)
            queued_any = True

        if queued_any:
            if hasattr(self.dashboard, "queue_sidebar") and self.dashboard.queue_sidebar.isHidden():
                self.dashboard.queue_sidebar.show()
                
            self._process_next_queue_item()

    def _add_to_queue(self, pixmap: QPixmap, is_single: bool = False):
        self._queue_snip_counter += 1
        item_id = f"snip_{self._queue_snip_counter}"
        if is_single:
            filename = f"Snip #{self._queue_snip_counter}.png"
        else:
            filename = f"Continuous Snip #{self._queue_snip_counter}.png"
        
        folder_id = self.dashboard.current_folder_id
        target_language = self.dashboard.get_target_language()
        
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        pixmap.save(buffer, "PNG")
        image_bytes = buffer.data().data()
        
        item = {
            "item_id": item_id,
            "image_bytes": image_bytes,
            "filename": filename,
            "folder_id": folder_id,
            "target_language": target_language,
            "thumbnail": pixmap
        }
        
        self.translation_queue.append(item)
        self.dashboard.add_queue_item_ui(item_id, filename, target_language, pixmap)
        
        if hasattr(self.dashboard, "queue_sidebar") and self.dashboard.queue_sidebar.isHidden():
            self.dashboard.queue_sidebar.show()
            
        self._process_next_queue_item()

    def _on_cancel_queue_item(self, item_id: str):
        """Cancel a pending or translating queue item."""
        if getattr(self, "active_worker_item_id", None) == item_id:
            self._clear_active_worker()
            self.dashboard.update_queue_item_ui(item_id, "cancelled")
            self._process_next_queue_item()
            return

        for i, item in enumerate(self.translation_queue):
            if item["item_id"] == item_id:
                self.translation_queue.pop(i)
                self.dashboard.update_queue_item_ui(item_id, "cancelled")
                return

    def _process_next_queue_item(self):
        if self.active_worker is not None or not self.translation_queue:
            return
            
        item = self.translation_queue.pop(0)
        
        self.active_worker = QueuedTranslationWorker(
            image_bytes=item["image_bytes"],
            filename=item["filename"],
            folder_id=item["folder_id"],
            target_language=item["target_language"],
            translation_config=self.dashboard.get_translation_config()
        )
        
        self.active_worker_item_id = item["item_id"]
        
        self.active_worker.progress.connect(self._on_queue_worker_progress)
        self.active_worker.finished.connect(self._on_queue_worker_finished)
        self.active_worker.error.connect(self._on_queue_worker_error)
        
        self._translation_in_progress = True
        self._update_indicator()
        
        self.active_worker.start()

    def _on_queue_worker_progress(self, status: str, progress: int):
        item_id = getattr(self, "active_worker_item_id", None)
        if item_id:
            self.dashboard.update_queue_item_ui(item_id, status, progress)

    def _on_queue_worker_finished(self, saved_image_data: dict):
        item_id = getattr(self, "active_worker_item_id", None)
        if item_id:
            self.dashboard.update_queue_item_ui(item_id, "completed", 100)
            
        self.dashboard.add_saved_image(saved_image_data)
        
        self._clear_active_worker()
        self._process_next_queue_item()

    def _on_queue_worker_error(self, error_msg: str):
        item_id = getattr(self, "active_worker_item_id", None)
        if item_id:
            self.dashboard.update_queue_item_ui(item_id, "failed", error_msg=error_msg)
            
        self._clear_active_worker()
        self._process_next_queue_item()

    def _clear_active_worker(self):
        if self.active_worker:
            self.active_worker.quit()
            self.active_worker.wait()
            self.active_worker = None
        self.active_worker_item_id = None
        self._translation_in_progress = False
        self._update_indicator()


def main():
    """Application entry point"""
    # Enable high DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    
    # Set application style
    app.setStyleSheet(get_main_stylesheet())

    # Re-apply global stylesheet on theme change
    theme.theme_changed.connect(lambda _: app.setStyleSheet(get_main_stylesheet()))
    
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
