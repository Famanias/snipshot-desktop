"""
SnipShot Desktop - Dashboard Window

Main dashboard with folder/image management (Google Drive-style).
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QScrollArea, QGridLayout, QMenu, QAction,
    QInputDialog, QMessageBox, QSizePolicy, QListWidget,
    QListWidgetItem, QStackedWidget, QProgressBar, QDialog,
    QLineEdit, QTextEdit, QDialogButtonBox, QApplication, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QFont
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtCore import QUrl

from api import api_client
from config import TRANSLATION_TARGET_LANG
from utils import format_file_size, format_date


class ImageLoaderWorker(QThread):
    """Background worker for loading images from URL"""

    finished = pyqtSignal(bytes)
    error = pyqtSignal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        try:
            import httpx
            # Use httpx for better async HTTP handling
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
        """Open image URL in browser"""
        import webbrowser
        url = self.image_data.get("public_url")
        if url:
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
        
        menu.addSeparator()
        
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(lambda: self.delete_requested.emit(self.image_data["id"]))
        
        menu.exec_(pos)


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
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SnipShot - Dashboard")
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)
        
        self.current_folder_id = None
        self.current_folder_name = None
        self.active_nav = "all"
        self.target_language = TRANSLATION_TARGET_LANG
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
                folder_grid = QFrame()
                folder_grid_layout = QGridLayout(folder_grid)
                folder_grid_layout.setSpacing(16)
                folder_grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

                for i, folder in enumerate(folders):
                    card = FolderCard(folder)
                    card.clicked.connect(self._on_folder_clicked)
                    card.delete_requested.connect(self._on_delete_folder)
                    card.rename_requested.connect(self._on_rename_folder)

                    row = i // 5
                    col = i % 5
                    folder_grid_layout.addWidget(card, row, col)

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
        """Add a grid of image cards"""
        image_grid = QFrame()
        image_grid_layout = QGridLayout(image_grid)
        image_grid_layout.setSpacing(16)
        image_grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        # Limit initial display to 20 images
        display_images = images[:20]
        self.all_images = images  # Store all images for load more functionality

        for i, image in enumerate(display_images):
            card = ImageCard(image)
            card.clicked.connect(self._on_image_clicked)
            card.delete_requested.connect(self._on_delete_image)

            row = i // 5
            col = i % 5
            image_grid_layout.addWidget(card, row, col)

        self.content_layout.addWidget(image_grid)

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
        if hasattr(self, 'all_images') and hasattr(self, 'load_more_btn'):
            # Remove load more button
            self.content_layout.removeWidget(self.load_more_btn)
            self.load_more_btn.deleteLater()

            # Add remaining images
            remaining_images = self.all_images[20:]
            if remaining_images:
                # Find existing image grid
                for i in range(self.content_layout.count()):
                    item = self.content_layout.itemAt(i)
                    if item and item.widget():
                        widget = item.widget()
                        if hasattr(widget, 'layout'):  # It's the image grid
                            layout = widget.layout()
                            if layout:
                                # Add remaining images to existing grid
                                start_index = 20
                                for j, image in enumerate(remaining_images):
                                    card = ImageCard(image)
                                    card.clicked.connect(self._on_image_clicked)
                                    card.delete_requested.connect(self._on_delete_image)

                                    row = (start_index + j) // 5
                                    col = (start_index + j) % 5
                                    layout.addWidget(card, row, col)
                                break
    
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

        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(20, 20, 20, 20)
        settings_layout.setSpacing(12)

        title = QLabel("Translation Settings")
        title.setStyleSheet("font-size: 18px; font-weight: 600; color: #202124;")
        settings_layout.addWidget(title)

        subtitle = QLabel("Select the default target language used for each new snip.")
        subtitle.setStyleSheet("color: #5F6368; font-size: 13px;")
        settings_layout.addWidget(subtitle)

        lang_label = QLabel("Target Language")
        lang_label.setStyleSheet("font-weight: 500; color: #202124; margin-top: 8px;")
        settings_layout.addWidget(lang_label)

        self.language_combo = QComboBox()
        self.language_combo.setStyleSheet("""
            QComboBox {
                padding: 10px;
                border: 1px solid #DADCE0;
                border-radius: 4px;
                font-size: 14px;
                min-width: 280px;
            }
        """)
        for label, code in self.language_options:
            self.language_combo.addItem(f"{label} ({code})", code)

        current_index = self.language_combo.findData(self.target_language)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)

        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        settings_layout.addWidget(self.language_combo)

        self.language_hint_label = QLabel(f"Current target language: {self.target_language}")
        self.language_hint_label.setStyleSheet("color: #5F6368; font-size: 12px;")
        settings_layout.addWidget(self.language_hint_label)

        self.content_layout.addWidget(settings_card)

    def _on_language_changed(self):
        """Handle settings language selection change."""
        if not hasattr(self, "language_combo"):
            return

        selected = self.language_combo.currentData()
        if selected:
            self.target_language = selected
            if hasattr(self, "language_hint_label"):
                self.language_hint_label.setText(f"Current target language: {self.target_language}")

    def get_target_language(self) -> str:
        """Return currently selected target language for new translations."""
        return self.target_language
    
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
        reply = QMessageBox.question(
            self, "Delete Folder",
            f"Delete folder '{folder_name}'?\n\nImages will be moved to Unfiled.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            result = api_client.delete_folder(folder_id)
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
    
    def _on_logout(self):
        """Handle logout"""
        api_client.logout()
        self.logout_requested.emit()
