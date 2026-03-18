"""
SnipShot Desktop - Dashboard Window

Main dashboard with folder/image management (Google Drive-style).
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QMenu, QAction,
    QInputDialog, QMessageBox, QSizePolicy, QListWidget,
    QListWidgetItem, QStackedWidget, QProgressBar, QDialog,
    QLineEdit, QTextEdit, QDialogButtonBox, QApplication, QComboBox,
    QLayout, QSpinBox, QDoubleSpinBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread, QRect, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QFont, QKeySequence
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtCore import QUrl

from api import api_client
from config import (
    TRANSLATION_TARGET_LANG, TRANSLATION_INPAINTER,
    DEFAULT_SHORTCUT_KEY,
    DETECTION_SIZE_MIN, DETECTION_SIZE_MAX, DETECTION_SIZE_STEP,
    BOX_THRESHOLD_MIN, BOX_THRESHOLD_MAX,
    INPAINTING_SIZE_MIN, INPAINTING_SIZE_MAX, INPAINTING_SIZE_STEP,
)
from utils import format_file_size, format_date


class FlowLayout(QLayout):
    """A layout that wraps child widgets to the next row when available space runs out."""

    def __init__(self, parent=None, spacing=16):
        super().__init__(parent)
        self._spacing = spacing
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        x = rect.x() + m.left()
        y = rect.y() + m.top()
        line_height = 0
        right_edge = rect.right() - m.right()

        for item in self._items:
            w = item.sizeHint().width()
            h = item.sizeHint().height()
            if x + w > right_edge and line_height > 0:
                x = rect.x() + m.left()
                y += line_height + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            x += w + self._spacing
            line_height = max(line_height, h)

        return y + line_height - rect.y() + m.bottom()


class ImageLoaderWorker(QThread):
    """Background worker for loading images from URL or local file"""

    finished = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            import os
            # Local file path — read directly from disk
            if os.path.isfile(self.url):
                with open(self.url, "rb") as f:
                    self.finished.emit(f.read())
                return
            # Remote URL — fetch over HTTP
            import httpx
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                response = client.get(self.url)
                response.raise_for_status()
                self.finished.emit(response.content)
        except Exception as e:
            self.error.emit(str(e))


class ImagePreviewDialog(QDialog):
    """Dialog for viewing an image in full size"""

    # Simple in-memory cache for loaded images
    _image_cache = {}

    def __init__(self, image_data: dict, parent=None):
        super().__init__(parent)
        self.image_data = image_data
        self.setWindowTitle(image_data.get("filename", "Image Preview"))
        self.setMinimumSize(600, 500)
        self.resize(800, 600)
        self.loader = None
        self._setup_ui()
        self._load_image()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Image container with scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #DADCE0;
                border-radius: 8px;
                background-color: #F8F9FA;
            }
        """)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: transparent;")
        self.scroll_area.setWidget(self.image_label)
        
        layout.addWidget(self.scroll_area, 1)
        
        # Loading indicator
        self.loading_label = QLabel("Loading image...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #5F6368; font-size: 14px; padding: 20px;")
        self.image_label.setText("Loading...")
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setStyleSheet("""
            QProgressBar {
                background-color: #E8F0FE;
                border: none;
                border-radius: 4px;
                height: 4px;
            }
            QProgressBar::chunk {
                background-color: #4285F4;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.progress)
        
        # Info section
        info_layout = QHBoxLayout()
        
        filename = self.image_data.get("filename", "Unknown")
        self.filename_label = QLabel(filename)
        self.filename_label.setStyleSheet("font-weight: 500; color: #202124;")
        info_layout.addWidget(self.filename_label)
        
        info_layout.addStretch()
        
        # Open in browser button
        open_browser_btn = QPushButton("Open in Browser")
        open_browser_btn.setCursor(Qt.PointingHandCursor)
        open_browser_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4285F4;
                border: 1px solid #4285F4;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
            }
        """)
        open_browser_btn.clicked.connect(self._open_in_browser)
        info_layout.addWidget(open_browser_btn)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 24px;
                font-weight: 500;
            }
        """)
        close_btn.clicked.connect(self.accept)
        info_layout.addWidget(close_btn)
        
        layout.addLayout(info_layout)
    
    def _load_image(self):
        """Load image from URL"""
        url = self.image_data.get("public_url")
        if not url:
            self.image_label.setText("No image URL available")
            self.progress.hide()
            return

        # Check cache first
        if url in self._image_cache:
            self._on_image_loaded(self._image_cache[url])
            return

        self.loader = ImageLoaderWorker(url)
        self.loader.finished.connect(self._on_image_loaded)
        self.loader.error.connect(self._on_load_error)
        self.loader.start()
    
    def _on_image_loaded(self, data: bytes):
        """Handle loaded image data"""
        self.progress.hide()

        # Cache the image data
        url = self.image_data.get("public_url")
        if url:
            self._image_cache[url] = data

        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            # Scale to fit dialog while maintaining aspect ratio
            available_size = self.scroll_area.size()
            scaled = pixmap.scaled(
                available_size.width() - 20,
                available_size.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)

            # Store original for potential zoom
            self.original_pixmap = pixmap
        else:
            self.image_label.setText("Failed to decode image")
    
    def _on_load_error(self, error: str):
        """Handle load error"""
        self.progress.hide()
        self.image_label.setText(f"Failed to load image:\n{error}")
        self.image_label.setStyleSheet("color: #EA4335; padding: 20px;")
    
    def _open_in_browser(self):
        """Open image URL in browser or local file viewer"""
        import os
        import webbrowser
        url = self.image_data.get("public_url")
        if url:
            if os.path.isfile(url):
                os.startfile(url)
            else:
                webbrowser.open(url)
    
    def resizeEvent(self, event):
        """Re-scale image when dialog is resized"""
        super().resizeEvent(event)
        if hasattr(self, 'original_pixmap') and self.original_pixmap:
            available_size = self.scroll_area.size()
            scaled = self.original_pixmap.scaled(
                available_size.width() - 20,
                available_size.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled)
    
    def closeEvent(self, event):
        """Clean up worker thread"""
        if self.loader and self.loader.isRunning():
            self.loader.terminate()
            self.loader.wait()
        super().closeEvent(event)


class CreateFolderDialog(QDialog):
    """Dialog for creating a new folder"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Folder")
        self.setMinimumWidth(350)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("Create New Folder")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #202124;")
        layout.addWidget(title)
        
        # Name input
        name_label = QLabel("Folder Name")
        name_label.setStyleSheet("font-weight: 500; color: #5F6368;")
        layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter folder name")
        self.name_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #DADCE0;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #4285F4;
            }
        """)
        layout.addWidget(self.name_input)
        
        # Description input
        desc_label = QLabel("Description (optional)")
        desc_label.setStyleSheet("font-weight: 500; color: #5F6368;")
        layout.addWidget(desc_label)
        
        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Enter description")
        self.desc_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                border: 1px solid #DADCE0;
                border-radius: 4px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #4285F4;
            }
        """)
        layout.addWidget(self.desc_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #5F6368;
                border: 1px solid #DADCE0;
                border-radius: 4px;
                padding: 10px 24px;
                font-weight: 500;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        self.create_btn = QPushButton("Create")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 10px 24px;
                font-weight: 600;
            }
        """)
        self.create_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.create_btn)
        
        layout.addLayout(button_layout)
    
    def get_values(self):
        return self.name_input.text().strip(), self.desc_input.text().strip()


class FolderCard(QFrame):
    """A card widget representing a folder"""
    
    clicked = pyqtSignal(int, str)  # folder_id, folder_name
    delete_requested = pyqtSignal(int, str)
    rename_requested = pyqtSignal(int, str)
    
    def __init__(self, folder_data: dict, parent=None):
        super().__init__(parent)
        self.folder_id = folder_data["id"]
        self.folder_name = folder_data["name"]
        self.image_count = folder_data.get("image_count", 0)
        self._setup_ui()
        self.setCursor(Qt.PointingHandCursor)
    
    def _setup_ui(self):
        self.setStyleSheet("""
            FolderCard {
                background-color: #FFFFFF;
                border: 1px solid #DADCE0;
                border-radius: 8px;
            }
            FolderCard:hover {
                border-color: #4285F4;
            }
        """)
        self.setFixedSize(180, 160)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)
        
        # Folder icon
        icon_label = QLabel("📁")
        icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)
        
        # Folder name
        name_label = QLabel(self.folder_name)
        name_label.setStyleSheet("font-weight: 600; color: #202124; font-size: 14px;")
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        # Image count
        image_label = "image" if self.image_count == 1 else "images"
        count_label = QLabel(f"{self.image_count} {image_label}")
        count_label.setStyleSheet("color: #5F6368; font-size: 12px;")
        count_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(count_label)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.folder_id, self.folder_name)
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
    
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        
        open_action = menu.addAction("Open")
        open_action.triggered.connect(lambda: self.clicked.emit(self.folder_id, self.folder_name))
        
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda: self.rename_requested.emit(self.folder_id, self.folder_name))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.folder_id, self.folder_name))
        
        menu.exec_(pos)


class ImageCard(QFrame):
    """A card widget representing an image"""
    
    clicked = pyqtSignal(dict)
    delete_requested = pyqtSignal(int)
    rename_requested = pyqtSignal(dict)
    move_requested = pyqtSignal(dict)
    
    def __init__(self, image_data: dict, parent=None):
        super().__init__(parent)
        self.image_data = image_data
        self._setup_ui()
        self.setCursor(Qt.PointingHandCursor)
    
    def _setup_ui(self):
        self.setStyleSheet("""
            ImageCard {
                background-color: #FFFFFF;
                border: 1px solid #DADCE0;
                border-radius: 8px;
            }
            ImageCard:hover {
                border-color: #4285F4;
            }
        """)
        self.setFixedSize(180, 200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Thumbnail placeholder
        thumb_frame = QFrame()
        thumb_frame.setStyleSheet("""
            background-color: #F1F3F4;
            border-radius: 4px;
        """)
        thumb_frame.setFixedHeight(120)
        
        thumb_layout = QVBoxLayout(thumb_frame)
        thumb_layout.setAlignment(Qt.AlignCenter)
        
        # Image icon
        icon_label = QLabel("🖼️")
        icon_label.setStyleSheet("font-size: 36px;")
        icon_label.setAlignment(Qt.AlignCenter)
        thumb_layout.addWidget(icon_label)
        
        layout.addWidget(thumb_frame)
        
        # Filename
        name_label = QLabel(self.image_data.get("filename", "Untitled"))
        name_label.setStyleSheet("font-weight: 500; color: #202124; font-size: 12px;")
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(32)
        layout.addWidget(name_label)
        
        # File size
        size = self.image_data.get("file_size")
        size_text = format_file_size(size) if size else ""
        size_label = QLabel(size_text)
        size_label.setStyleSheet("color: #5F6368; font-size: 11px;")
        layout.addWidget(size_label)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.image_data)
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())
    
    def _show_context_menu(self, pos):
        menu = QMenu(self)
        
        open_action = menu.addAction("View")
        open_action.triggered.connect(lambda: self.clicked.emit(self.image_data))

        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(lambda: self.rename_requested.emit(self.image_data))

        move_action = menu.addAction("Move to Folder")
        move_action.triggered.connect(lambda: self.move_requested.emit(self.image_data))
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.image_data["id"]))
        
        menu.exec_(pos)


class _ShortcutButton(QPushButton):
    """
    A button that, when clicked, waits for the user to press a key and emits
    ``shortcut_captured(int)`` with the Qt key code.
    """

    shortcut_captured = pyqtSignal(int)

    # Keys that should not be accepted as shortcuts
    _IGNORED_KEYS = {
        Qt.Key_unknown,
        Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta,
        Qt.Key_Tab, Qt.Key_Backtab,
        Qt.Key_Escape,
    }

    def __init__(self, text="Change…", parent=None):
        super().__init__(text, parent)
        self._waiting = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #3367D6; }
            QPushButton[waiting="true"] {
                background-color: #EA4335;
            }
        """)
        self.clicked.connect(self._on_clicked)

    def _on_clicked(self):
        self._waiting = True
        self.setProperty("waiting", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText("Press a key…")
        self.setFocus()

    def keyPressEvent(self, event):
        if not self._waiting:
            super().keyPressEvent(event)
            return

        key = event.key()
        if key in self._IGNORED_KEYS or key == 0:
            # Keep waiting — modifiers / unknown keys are not valid shortcuts
            return

        self._waiting = False
        self.setProperty("waiting", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText("Change…")
        self.clearFocus()
        self.shortcut_captured.emit(key)

    def focusOutEvent(self, event):
        """Cancel capture if focus is lost."""
        if self._waiting:
            self._waiting = False
            self.setProperty("waiting", False)
            self.style().unpolish(self)
            self.style().polish(self)
            self.setText("Change…")
        super().focusOutEvent(event)


class DashboardWindow(QWidget):
    """
    Main dashboard with folder and image management.
    Similar to Google Drive interface.
    
    Signals:
        logout_requested: Emitted when user wants to logout
        capture_requested: Emitted when user wants to capture screen
    """
    
    logout_requested = pyqtSignal()
    capture_requested = pyqtSignal()
    upload_requested = pyqtSignal(str)  # emits file path
    shortcut_changed = pyqtSignal(int)  # emits new Qt key code
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SnipShot - Dashboard")
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)
        
        self.current_folder_id = None
        self.current_folder_name = None
        self.active_nav = "all"
        self.target_language = TRANSLATION_TARGET_LANG
        self.snip_shortcut_key = DEFAULT_SHORTCUT_KEY
        self.detection_size = 1536
        self.box_threshold = 0.7
        self.inpainting_size = 2048
        self.inpainter = TRANSLATION_INPAINTER
        self.language_options = [
            ("English", "ENG"),
            ("Japanese", "JPN"),
            ("Korean", "KOR"),
            ("Chinese (Simplified)", "CHS"),
            ("Chinese (Traditional)", "CHT"),
            # ("Spanish", "ESP"),
            # ("French", "FRA"),
            # ("German", "DEU"),
            # ("Italian", "ITA"),
            # ("Portuguese", "POR"),
            # ("Russian", "RUS"),
        ]
        
        self._setup_ui()
        
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== Sidebar ==========
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: #F8F9FA;
                border-right: 1px solid #DADCE0;
            }
        """)
        
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 16, 16, 16)
        sidebar_layout.setSpacing(8)
        
        # App title
        title_label = QLabel("SnipShot")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: 700;
            color: #4285F4;
            padding: 8px 0;
            background-color: transparent;
        """)
        sidebar_layout.addWidget(title_label)
        
        sidebar_layout.addSpacing(16)
        
        # Snip button
        self.snip_btn = QPushButton("✂️  New Snip")
        self.snip_btn.setCursor(Qt.PointingHandCursor)
        self.snip_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #202124;
                border: 1px solid #DADCE0;
                border-radius: 24px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
        """)
        self.snip_btn.clicked.connect(self._on_snip)
        sidebar_layout.addWidget(self.snip_btn)

        # Upload image button
        self.upload_btn = QPushButton("📂  Upload Image")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #202124;
                border: 1px solid #DADCE0;
                border-radius: 24px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
        """)
        self.upload_btn.clicked.connect(self._on_upload)
        sidebar_layout.addWidget(self.upload_btn)
        
        sidebar_layout.addSpacing(16)
        
        # Navigation items
        self.nav_all = QPushButton("📁  All Files")
        self.nav_all.setCursor(Qt.PointingHandCursor)
        self.nav_all.setStyleSheet(self._nav_button_style(True))
        self.nav_all.clicked.connect(self._on_nav_all)
        sidebar_layout.addWidget(self.nav_all)
        
        self.nav_recent = QPushButton("🕐  Recent")
        self.nav_recent.setCursor(Qt.PointingHandCursor)
        self.nav_recent.setStyleSheet(self._nav_button_style(False))
        self.nav_recent.clicked.connect(self._on_nav_recent)
        sidebar_layout.addWidget(self.nav_recent)

        self.nav_settings = QPushButton("⚙️  Settings")
        self.nav_settings.setCursor(Qt.PointingHandCursor)
        self.nav_settings.setStyleSheet(self._nav_button_style(False))
        self.nav_settings.clicked.connect(self._on_nav_settings)
        sidebar_layout.addWidget(self.nav_settings)
        
        sidebar_layout.addStretch()
        
        # User section
        user_frame = QFrame()
        user_frame.setStyleSheet("""
            background-color: transparent;
            padding-top: 16px;
        """)
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(0, 16, 0, 0)
        
        self.user_label = QLabel("Loading...")
        self.user_label.setStyleSheet("color: #5F6368; font-size: 12px;")
        user_layout.addWidget(self.user_label)
        
        logout_btn = QPushButton("Sign Out")
        logout_btn.setCursor(Qt.PointingHandCursor)
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #EA4335;
                border: none;
                padding: 8px 0;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        logout_btn.clicked.connect(self._on_logout)
        user_layout.addWidget(logout_btn)
        
        sidebar_layout.addWidget(user_frame)
        
        main_layout.addWidget(sidebar)
        
        # ========== Content Area ==========
        content = QFrame()
        content.setStyleSheet("background-color: #FFFFFF;")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setObjectName("header")
        header.setStyleSheet("""
            QFrame#header {
                background-color: #FFFFFF;
                border-bottom: 1px solid #DADCE0;
            }
        """)
        header.setFixedHeight(64)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        
        # Breadcrumb / Title
        self.header_title = QLabel("My Files")
        self.header_title.setStyleSheet("font-size: 18px; font-weight: 500; color: #202124;")
        header_layout.addWidget(self.header_title)
        
        header_layout.addStretch()
        
        # New folder button
        self.new_folder_btn = QPushButton("+ New Folder")
        self.new_folder_btn.setCursor(Qt.PointingHandCursor)
        self.new_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                color: #4285F4;
                border: 1px solid #4285F4;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: 500;
            }
        """)
        self.new_folder_btn.clicked.connect(self._on_new_folder)
        header_layout.addWidget(self.new_folder_btn)
        
        # Refresh button
        refresh_btn = QPushButton("↻")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 18px;
                padding: 8px;
                border-radius: 4px;
            }
        """)
        refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(refresh_btn)
        
        content_layout.addWidget(header)
        
        # Main content area (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #FFFFFF;
            }
        """)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(24)
        self.content_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.content_widget)
        content_layout.addWidget(scroll)
        
        # Loading indicator
        self.loading_label = QLabel("Loading...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet("color: #5F6368; font-size: 14px; padding: 40px;")
        self.content_layout.addWidget(self.loading_label)
        
        main_layout.addWidget(content)
    
    def _nav_button_style(self, active: bool) -> str:
        if active:
            return """
                QPushButton {
                    background-color: #E8F0FE;
                    color: #4285F4;
                    border: none;
                    border-radius: 24px;
                    padding: 10px 16px;
                    font-size: 14px;
                    text-align: left;
                    font-weight: 500;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: transparent;
                    color: #5F6368;
                    border: none;
                    border-radius: 24px;
                    padding: 10px 16px;
                    font-size: 14px;
                    text-align: left;
                }
            """

    def _set_active_nav(self, active: str):
        """Update sidebar active state styling."""
        self.active_nav = active
        self.nav_all.setStyleSheet(self._nav_button_style(active == "all"))
        self.nav_recent.setStyleSheet(self._nav_button_style(active == "recent"))
        self.nav_settings.setStyleSheet(self._nav_button_style(active == "settings"))
    
    def load_user_info(self):
        """Load and display user info"""
        if api_client.user:
            email = api_client.user.get("email", "Unknown")
            self.user_label.setText(f"👤 {email}")
    
    def refresh(self):
        """Refresh current view"""
        if self.active_nav == "settings":
            self._on_nav_settings()
            return

        if self.active_nav == "recent":
            self._on_nav_recent()
            return

        if self.current_folder_id:
            self._load_folder(self.current_folder_id, self.current_folder_name)
        else:
            self._load_all_files_async()
    
    def _clear_content(self):
        """Clear the content area"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def _load_all_files_async(self):
        """Load folders and unfiled images asynchronously"""
        self.current_folder_id = None
        self.current_folder_name = None
        self.header_title.setText("My Files")
        self.new_folder_btn.setVisible(True)
        self._set_active_nav("all")

        from PyQt5.QtCore import QThread, pyqtSignal

        class LoadWorker(QThread):
            finished = pyqtSignal(dict, dict)  # folders_result, images_result

            def run(self):
                folders_result = api_client.get_folders()
                images_result = api_client.get_images(folder_id=0, per_page=20)  # Load fewer images initially
                self.finished.emit(folders_result, images_result)

        self._clear_content()

        # Show loading
        loading = QLabel("Loading folders...")
        loading.setStyleSheet("color: #5F6368; padding: 20px;")
        self.content_layout.addWidget(loading)

        # Start async loading
        self.load_worker = LoadWorker()
        self.load_worker.finished.connect(self._on_data_loaded)
        self.load_worker.start()

    def _on_data_loaded(self, folders_result, images_result):
        """Handle loaded data"""
        self._clear_content()

        if folders_result["success"]:
            folders = folders_result["data"].get("folders", [])

            if folders:
                # Folders section
                folders_label = QLabel("Folders")
                folders_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #5F6368;")
                self.content_layout.addWidget(folders_label)

                # Folder grid
                folder_grid = QWidget()
                folder_grid_layout = FlowLayout(folder_grid, spacing=16)

                for folder in folders:
                    card = FolderCard(folder)
                    card.clicked.connect(self._on_folder_clicked)
                    card.delete_requested.connect(self._on_delete_folder)
                    card.rename_requested.connect(self._on_rename_folder)
                    folder_grid_layout.addWidget(card)

                self.content_layout.addWidget(folder_grid)

            # Load unfiled images
            if images_result["success"]:
                images = images_result["data"].get("images", [])

                if images:
                    # Images section
                    self.content_layout.addSpacing(16)

                    images_label = QLabel("Unfiled Images")
                    images_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #5F6368;")
                    self.content_layout.addWidget(images_label)

                    self._add_image_grid(images)

            # Empty state
            if not folders and not (images_result.get("success") and images_result["data"].get("images")):
                self._show_empty_state("No files yet", "Capture a screenshot to get started!")
        else:
            self._show_error("Failed to load folders")

        self.content_layout.addStretch()
    
    def _load_folder(self, folder_id: int, folder_name: str):
        """Load images in a specific folder"""
        self.current_folder_id = folder_id
        self.current_folder_name = folder_name
        self._set_active_nav("all")
        
        # Update header with back button
        self.header_title.setText(f"📁 {folder_name}")
        self.new_folder_btn.setVisible(False)
        
        self._clear_content()
        
        # Back button
        back_btn = QPushButton("← Back to My Files")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4285F4;
                border: none;
                padding: 8px 0;
                font-size: 13px;
                text-align: left;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        back_btn.clicked.connect(self._on_nav_all)
        self.content_layout.addWidget(back_btn)
        
        # Load folder contents via images endpoint filtered by folder_id
        result = api_client.get_images(folder_id=folder_id, page=1, per_page=100)
        
        if result["success"]:
            images = result["data"].get("images", [])
            
            if images:
                self._add_image_grid(images)
            else:
                self._show_empty_state(
                    "This folder is empty", 
                    "Translated images saved to this folder will appear here."
                )
        else:
            self._show_error("Failed to load folder")
        
        self.content_layout.addStretch()
    
    def _add_image_grid(self, images: list, show_load_more: bool = False):
        """Add a responsive flow grid of image cards"""
        display_images = images[:20]
        self.all_images = images

        self._image_grid_widget = QWidget()
        grid_layout = FlowLayout(self._image_grid_widget, spacing=16)

        for image in display_images:
            card = ImageCard(image)
            card.clicked.connect(self._on_image_clicked)
            card.delete_requested.connect(self._on_delete_image)
            card.rename_requested.connect(self._on_rename_image)
            card.move_requested.connect(self._on_move_image)
            grid_layout.addWidget(card)

        self.content_layout.addWidget(self._image_grid_widget)

        # Add "Load More" button if there are more images
        if len(images) > 20 or show_load_more:
            self.load_more_btn = QPushButton("Load More Images")
            self.load_more_btn.setCursor(Qt.PointingHandCursor)
            self.load_more_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4285F4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 10px 20px;
                    font-weight: 500;
                    margin: 16px 0;
                }
                QPushButton:hover {
                    background-color: #3367D6;
                }
            """)
            self.load_more_btn.clicked.connect(self._load_more_images)
            self.content_layout.addWidget(self.load_more_btn, alignment=Qt.AlignCenter)

    def _load_more_images(self):
        """Load additional images"""
        if not (hasattr(self, 'all_images') and hasattr(self, 'load_more_btn')):
            return
        self.content_layout.removeWidget(self.load_more_btn)
        self.load_more_btn.deleteLater()

        remaining_images = self.all_images[20:]
        if remaining_images and hasattr(self, '_image_grid_widget'):
            layout = self._image_grid_widget.layout()
            if layout:
                for image in remaining_images:
                    card = ImageCard(image)
                    card.clicked.connect(self._on_image_clicked)
                    card.delete_requested.connect(self._on_delete_image)
                    card.rename_requested.connect(self._on_rename_image)
                    card.move_requested.connect(self._on_move_image)
                    layout.addWidget(card)
    
    def _show_empty_state(self, title: str, subtitle: str):
        """Show empty state message"""
        empty_frame = QFrame()
        empty_layout = QVBoxLayout(empty_frame)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(8)
        
        icon_label = QLabel("📂")
        icon_label.setStyleSheet("font-size: 64px;")
        icon_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 18px; font-weight: 500; color: #202124;")
        title_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_label)
        
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 14px; color: #5F6368;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(subtitle_label)
        
        self.content_layout.addWidget(empty_frame)
    
    def _show_error(self, message: str):
        """Show error message"""
        error_label = QLabel(f"❌ {message}")
        error_label.setStyleSheet("color: #EA4335; padding: 20px;")
        self.content_layout.addWidget(error_label)
    
    # ========== Event Handlers ==========
    
    def _on_snip(self):
        """Handle snip button click"""
        self.capture_requested.emit()

    def _on_upload(self):
        """Handle upload button click — open a file picker"""
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
        )
        if file_path:
            self.upload_requested.emit(file_path)
    
    def _on_nav_all(self):
        """Navigate to all files"""
        self._load_all_files_async()
    
    def _on_nav_recent(self):
        """Navigate to recent files"""
        self._set_active_nav("recent")
        self.current_folder_id = None
        self.current_folder_name = None
        self.header_title.setText("Recent")
        self.new_folder_btn.setVisible(False)
        
        self._clear_content()
        
        # Load all images sorted by date
        result = api_client.get_images()
        
        if result["success"]:
            images = result["data"].get("images", [])
            if images:
                self._add_image_grid(images)
            else:
                self._show_empty_state("No recent files", "Your recent translations will appear here.")
        else:
            self._show_error("Failed to load recent files")
        
        self.content_layout.addStretch()

    def _on_nav_settings(self):
        """Navigate to settings view."""
        self._set_active_nav("settings")
        self.current_folder_id = None
        self.current_folder_name = None
        self.header_title.setText("Settings")
        self.new_folder_btn.setVisible(False)

        self._clear_content()
        self._render_settings_content()
        self.content_layout.addStretch()

    # ------------------------------------------------------------------ #
    # Settings helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _settings_input_style():
        return """
            QSpinBox, QDoubleSpinBox, QComboBox {
                padding: 8px 10px;
                border: 1px solid #DADCE0;
                border-radius: 4px;
                font-size: 13px;
                min-width: 240px;
                background: #FFFFFF;
            }
            QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
                border-color: #4285F4;
            }
        """

    @staticmethod
    def _settings_label_style():
        return "font-weight: 500; color: #202124; margin-top: 4px;"

    @staticmethod
    def _settings_hint_style():
        return "color: #5F6368; font-size: 12px;"

    @staticmethod
    def _section_title_style():
        return "font-size: 14px; font-weight: 600; color: #3C4043; margin-top: 12px;"

    def _add_section_separator(self, layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #DADCE0;")
        layout.addWidget(sep)

    # ------------------------------------------------------------------ #
    # Settings rendering
    # ------------------------------------------------------------------ #

    def _render_settings_content(self):
        """Render settings controls in content area."""
        settings_card = QFrame()
        settings_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #DADCE0;
                border-radius: 8px;
            }
        """)

        sl = QVBoxLayout(settings_card)
        sl.setContentsMargins(24, 24, 24, 24)
        sl.setSpacing(10)

        # ── Page title ──────────────────────────────────────────────────
        page_title = QLabel("Settings")
        page_title.setStyleSheet("font-size: 18px; font-weight: 600; color: #202124;")
        sl.addWidget(page_title)

        # ================================================================
        # SECTION: Capture Shortcut
        # ================================================================
        sec_capture = QLabel("Capture Shortcut")
        sec_capture.setStyleSheet(self._section_title_style())
        sl.addWidget(sec_capture)

        self._add_section_separator(sl)

        sc_desc = QLabel(
            "Keyboard shortcut that triggers a new screen snip from anywhere in the app."
        )
        sc_desc.setWordWrap(True)
        sc_desc.setStyleSheet(self._settings_hint_style())
        sl.addWidget(sc_desc)

        # Current shortcut display + change button
        sc_row = QHBoxLayout()
        sc_row.setSpacing(12)

        self.shortcut_display = QLabel(self._key_name(self.snip_shortcut_key))
        self.shortcut_display.setStyleSheet("""
            QLabel {
                padding: 8px 14px;
                border: 1px solid #DADCE0;
                border-radius: 4px;
                font-size: 13px;
                font-weight: 500;
                background: #F1F3F4;
                color: #202124;
                min-width: 160px;
            }
        """)
        sc_row.addWidget(self.shortcut_display)

        self.shortcut_btn = _ShortcutButton("Change…")
        self.shortcut_btn.shortcut_captured.connect(self._on_shortcut_captured)
        sc_row.addWidget(self.shortcut_btn)
        sc_row.addStretch()

        sl.addLayout(sc_row)

        # ================================================================
        # SECTION: Translation Language
        # ================================================================
        sl.addSpacing(8)
        sec_lang = QLabel("Translation Language")
        sec_lang.setStyleSheet(self._section_title_style())
        sl.addWidget(sec_lang)

        self._add_section_separator(sl)

        lang_desc = QLabel("Default target language applied to every new snip or upload.")
        lang_desc.setWordWrap(True)
        lang_desc.setStyleSheet(self._settings_hint_style())
        sl.addWidget(lang_desc)

        self.language_combo = QComboBox()
        self.language_combo.setStyleSheet(self._settings_input_style())
        for label, code in self.language_options:
            self.language_combo.addItem(f"{label} ({code})", code)

        current_index = self.language_combo.findData(self.target_language)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)

        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        sl.addWidget(self.language_combo)

        self.language_hint_label = QLabel(f"Current: {self.target_language}")
        self.language_hint_label.setStyleSheet(self._settings_hint_style())
        sl.addWidget(self.language_hint_label)

        # ================================================================
        # SECTION: Translation Parameters
        # ================================================================
        sl.addSpacing(8)
        sec_trans = QLabel("Translation Parameters")
        sec_trans.setStyleSheet(self._section_title_style())
        sl.addWidget(sec_trans)

        self._add_section_separator(sl)

        params_desc = QLabel(
            "Fine-tune the translation engine. Higher detection/inpainting sizes improve quality "
            "at the cost of speed. Box threshold controls how confidently a region must be detected "
            "before being translated (higher = fewer false positives)."
        )
        params_desc.setWordWrap(True)
        params_desc.setStyleSheet(self._settings_hint_style())
        sl.addWidget(params_desc)

        # Detection size
        det_label = QLabel("Detection Size")
        det_label.setStyleSheet(self._settings_label_style())
        sl.addWidget(det_label)

        self.detection_size_spin = QSpinBox()
        self.detection_size_spin.setRange(DETECTION_SIZE_MIN, DETECTION_SIZE_MAX)
        self.detection_size_spin.setSingleStep(DETECTION_SIZE_STEP)
        self.detection_size_spin.setValue(self.detection_size)
        self.detection_size_spin.setStyleSheet(self._settings_input_style())
        self.detection_size_spin.valueChanged.connect(self._on_detection_size_changed)
        sl.addWidget(self.detection_size_spin)

        sl.addWidget(QLabel(
            "Resolution used for text detection  (512 – 3072 px, step 64).",
            styleSheet=self._settings_hint_style()
        ))

        # Box threshold
        box_label = QLabel("Box Threshold")
        box_label.setStyleSheet(self._settings_label_style())
        sl.addWidget(box_label)

        self.box_threshold_spin = QDoubleSpinBox()
        self.box_threshold_spin.setRange(BOX_THRESHOLD_MIN, BOX_THRESHOLD_MAX)
        self.box_threshold_spin.setSingleStep(0.05)
        self.box_threshold_spin.setDecimals(2)
        self.box_threshold_spin.setValue(self.box_threshold)
        self.box_threshold_spin.setStyleSheet(self._settings_input_style())
        self.box_threshold_spin.valueChanged.connect(self._on_box_threshold_changed)
        sl.addWidget(self.box_threshold_spin)

        sl.addWidget(QLabel(
            "Minimum confidence for a detected region to be translated  (0.10 – 1.00).",
            styleSheet=self._settings_hint_style()
        ))

        # Inpainting size
        inp_label = QLabel("Inpainting Size")
        inp_label.setStyleSheet(self._settings_label_style())
        sl.addWidget(inp_label)

        self.inpainting_size_spin = QSpinBox()
        self.inpainting_size_spin.setRange(INPAINTING_SIZE_MIN, INPAINTING_SIZE_MAX)
        self.inpainting_size_spin.setSingleStep(INPAINTING_SIZE_STEP)
        self.inpainting_size_spin.setValue(self.inpainting_size)
        self.inpainting_size_spin.setStyleSheet(self._settings_input_style())
        self.inpainting_size_spin.valueChanged.connect(self._on_inpainting_size_changed)
        sl.addWidget(self.inpainting_size_spin)

        sl.addWidget(QLabel(
            "Resolution used for background inpainting  (512 – 4096 px, step 256).",
            styleSheet=self._settings_hint_style()
        ))

        # Inpainter backend
        inp_type_label = QLabel("Inpainter")
        inp_type_label.setStyleSheet(self._settings_label_style())
        sl.addWidget(inp_type_label)

        self.inpainter_combo = QComboBox()
        self.inpainter_combo.setStyleSheet(self._settings_input_style())
        self.inpainter_combo.addItem("LAMA Large (recommended)", "lama_large")
        self.inpainter_combo.addItem("None (skip inpainting)", "none")
        idx = self.inpainter_combo.findData(self.inpainter)
        if idx >= 0:
            self.inpainter_combo.setCurrentIndex(idx)
        self.inpainter_combo.currentIndexChanged.connect(self._on_inpainter_changed)
        sl.addWidget(self.inpainter_combo)

        self.content_layout.addWidget(settings_card)

    # ------------------------------------------------------------------ #
    # Settings change handlers
    # ------------------------------------------------------------------ #

    def _on_language_changed(self):
        if not hasattr(self, "language_combo"):
            return
        selected = self.language_combo.currentData()
        if selected:
            self.target_language = selected
            if hasattr(self, "language_hint_label"):
                self.language_hint_label.setText(f"Current: {self.target_language}")

    def _on_shortcut_captured(self, key: int):
        self.snip_shortcut_key = key
        if hasattr(self, "shortcut_display"):
            self.shortcut_display.setText(self._key_name(key))
        self.shortcut_changed.emit(key)

    def _on_detection_size_changed(self, value: int):
        self.detection_size = value

    def _on_box_threshold_changed(self, value: float):
        self.box_threshold = round(value, 2)

    def _on_inpainting_size_changed(self, value: int):
        self.inpainting_size = value

    def _on_inpainter_changed(self):
        if hasattr(self, "inpainter_combo"):
            self.inpainter = self.inpainter_combo.currentData()

    # ------------------------------------------------------------------ #
    # Public getters
    # ------------------------------------------------------------------ #

    def get_target_language(self) -> str:
        """Return currently selected target language for new translations."""
        return self.target_language

    def get_translation_config(self) -> dict:
        """Return a translation config dict reflecting current settings."""
        return {
            "detector": {
                "detection_size": self.detection_size,
                "box_threshold": self.box_threshold,
            },
            "translator": {"target_lang": self.target_language},
            "inpainter": {
                "inpainter": self.inpainter,
                "inpainting_size": self.inpainting_size,
            },
        }

    @staticmethod
    def _key_name(key: int) -> str:
        """Return a human-readable name for a Qt key code."""
        ks = QKeySequence(key)
        text = ks.toString(QKeySequence.NativeText)
        return text if text else QKeySequence(key).toString()
    
    def _on_folder_clicked(self, folder_id: int, folder_name: str):
        """Handle folder click"""
        self._load_folder(folder_id, folder_name)
    
    def _on_image_clicked(self, image_data: dict):
        """Handle image click - show preview dialog"""
        dialog = ImagePreviewDialog(image_data, self)
        dialog.exec_()
    
    def _on_new_folder(self):
        """Create new folder"""
        dialog = CreateFolderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, description = dialog.get_values()
            if name:
                result = api_client.create_folder(name, description)
                if result["success"]:
                    self.refresh()
                else:
                    QMessageBox.warning(self, "Error", result.get("error", "Failed to create folder"))
    
    def _on_delete_folder(self, folder_id: int, folder_name: str):
        """Delete folder"""
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Folder")
        msg.setText(f"Delete folder '{folder_name}'?")
        msg.setInformativeText("Choose how to handle the images inside.")
        keep_btn = msg.addButton("Delete Folder (Keep Images)", QMessageBox.AcceptRole)
        delete_all_btn = msg.addButton("Delete Folder + All Images", QMessageBox.DestructiveRole)
        msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == keep_btn:
            result = api_client.delete_folder(folder_id, delete_images=False)
        elif clicked == delete_all_btn:
            result = api_client.delete_folder(folder_id, delete_images=True)
        else:
            return

        if result["success"]:
            self.refresh()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete folder")
    
    def _on_rename_folder(self, folder_id: int, current_name: str):
        """Rename folder"""
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "New name:", text=current_name
        )
        
        if ok and new_name and new_name != current_name:
            result = api_client.update_folder(folder_id, name=new_name)
            if result["success"]:
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", result.get("error", "Failed to rename folder"))
    
    def _on_delete_image(self, image_id: int):
        """Delete image"""
        reply = QMessageBox.question(
            self, "Delete Image",
            "Delete this image permanently?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result = api_client.delete_image(image_id)
            if result["success"]:
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete image")

    def _on_rename_image(self, image_data: dict):
        """Rename image"""
        current_name = image_data.get("filename", "")
        new_name, ok = QInputDialog.getText(
            self, "Rename Image", "New filename:", text=current_name
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            result = api_client.update_image(image_data["id"], filename=new_name.strip())
            if result["success"]:
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", result.get("error", "Failed to rename image"))

    def _on_move_image(self, image_data: dict):
        """Move image to a different folder"""
        folders_result = api_client.get_folders()
        if not folders_result["success"]:
            QMessageBox.warning(self, "Error", "Failed to load folders")
            return

        folders = folders_result["data"].get("folders", [])
        folder_names = ["Unfiled"] + [f["name"] for f in folders]
        folder_ids = [0] + [f["id"] for f in folders]

        if len(folder_names) == 1:
            QMessageBox.information(
                self, "No Folders",
                "Create a folder first to move images into it."
            )
            return

        choice, ok = QInputDialog.getItem(
            self, "Move to Folder",
            f"Move '{image_data.get('filename', 'image')}' to:",
            folder_names, 0, False
        )
        if ok and choice:
            idx = folder_names.index(choice)
            folder_id = folder_ids[idx]
            result = api_client.update_image(image_data["id"], folder_id=folder_id)
            if result["success"]:
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", result.get("error", "Failed to move image"))
    
    def _on_logout(self):
        """Handle logout"""
        api_client.logout()
        self.logout_requested.emit()
