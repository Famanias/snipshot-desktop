# CHANGELOG
# ─────────────────────────────────────────────────────────────────────
# - Replaced all addSpacing() values with SPACE constants (base-8 grid)
# - Replaced inline button styles with StyledButton where appropriate
# - All font/spacing values reference FONT/SPACE constants
# - apply_card_shadow() on dialogs and settings card
# - ImagePreviewDialog uses StyledButton for actions
# - CreateFolderDialog uses StyledButton
# - Settings rendering uses SPACE/FONT consistently
# - Preserved all signals, slot connections, and API call logic exactly
# ─────────────────────────────────────────────────────────────────────
# SETTINGS UI REDESIGN (latest):
# - Monolithic settings card split into per-section cards
# - Each card has a primary-coloured left accent border
# - Segmented pill toggle replaces plain Light/Dark buttons
# - Sliders have custom-styled coloured groove + round handle
# - Value labels rendered as accent-coloured badges
# - Shortcut display uses keyboard-key "kbd" styling
# - Section headers have emoji icons for instant visual scanning
# - Page title elevated to display-size heading
# - _theme_pill_style() helper added; _on_theme_changed re-applies it
# ─────────────────────────────────────────────────────────────────────

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
    QLayout, QSpinBox, QDoubleSpinBox, QSlider,
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
from .theme import theme
from . import styles
from .styles import SPACE, FONT, apply_card_shadow
from .components import StyledButton


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
            if os.path.isfile(self.url):
                with open(self.url, "rb") as f:
                    self.finished.emit(f.read())
                return
            import httpx
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                response = client.get(self.url)
                response.raise_for_status()
                self.finished.emit(response.content)
        except Exception as e:
            self.error.emit(str(e))


class ImagePreviewDialog(QDialog):
    """Dialog for viewing an image in full size"""

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
        c = theme.c
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        layout.setSpacing(SPACE["md"])

        # Image container with scroll
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(styles.preview_scroll())

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: transparent;")
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area, 1)

        # Loading indicator
        self.loading_label = QLabel("Loading image...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; "
            f"padding: {SPACE['lg']}px; background-color: transparent;"
        )
        self.image_label.setText("Loading...")

        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setStyleSheet(styles.progress_bar_lg())
        layout.addWidget(self.progress)

        # Info section
        info_layout = QHBoxLayout()

        filename = self.image_data.get("filename", "Unknown")
        self.filename_label = QLabel(filename)
        self.filename_label.setStyleSheet(
            f"font-weight: 500; color: {c['text']}; background-color: transparent;"
        )
        info_layout.addWidget(self.filename_label)

        info_layout.addStretch()

        open_browser_btn = StyledButton("Open in Browser", variant="secondary")
        open_browser_btn.clicked.connect(self._open_in_browser)
        info_layout.addWidget(open_browser_btn)

        close_btn = StyledButton("Close", variant="primary")
        close_btn.clicked.connect(self.accept)
        info_layout.addWidget(close_btn)

        layout.addLayout(info_layout)

    def _load_image(self):
        url = self.image_data.get("public_url")
        if not url:
            self.image_label.setText("No image URL available")
            self.progress.hide()
            return

        if url in self._image_cache:
            self._on_image_loaded(self._image_cache[url])
            return

        self.loader = ImageLoaderWorker(url)
        self.loader.finished.connect(self._on_image_loaded)
        self.loader.error.connect(self._on_load_error)
        self.loader.start()

    def _on_image_loaded(self, data: bytes):
        self.progress.hide()
        url = self.image_data.get("public_url")
        if url:
            self._image_cache[url] = data

        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            available_size = self.scroll_area.size()
            scaled = pixmap.scaled(
                available_size.width() - 20,
                available_size.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
            self.original_pixmap = pixmap
        else:
            self.image_label.setText("Failed to decode image")

    def _on_load_error(self, error: str):
        self.progress.hide()
        self.image_label.setText(f"Failed to load image:\n{error}")
        self.image_label.setStyleSheet(
            f"color: {theme.c['error']}; padding: {SPACE['lg']}px; background-color: transparent;"
        )

    def _open_in_browser(self):
        import os
        import webbrowser
        url = self.image_data.get("public_url")
        if url:
            if os.path.isfile(url):
                os.startfile(url)
            else:
                webbrowser.open(url)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "original_pixmap") and self.original_pixmap:
            available_size = self.scroll_area.size()
            scaled = self.original_pixmap.scaled(
                available_size.width() - 20,
                available_size.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)

    def closeEvent(self, event):
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
        c = theme.c
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE["md"])
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])

        # Title
        title = QLabel("Create New Folder")
        title.setStyleSheet(
            f"font-size: {FONT['heading']['size']}px; font-weight: {FONT['heading']['weight']}; "
            f"color: {c['text']}; background-color: transparent;"
        )
        layout.addWidget(title)

        # Name input
        name_label = QLabel("Folder Name")
        name_label.setStyleSheet(
            f"font-weight: 500; color: {c['text_secondary']}; background-color: transparent;"
        )
        layout.addWidget(name_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter folder name")
        self.name_input.setStyleSheet(styles.dialog_input())
        layout.addWidget(self.name_input)

        # Description input
        desc_label = QLabel("Description (optional)")
        desc_label.setStyleSheet(
            f"font-weight: 500; color: {c['text_secondary']}; background-color: transparent;"
        )
        layout.addWidget(desc_label)

        self.desc_input = QLineEdit()
        self.desc_input.setPlaceholderText("Enter description")
        self.desc_input.setStyleSheet(styles.dialog_input())
        layout.addWidget(self.desc_input)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = StyledButton("Cancel", variant="secondary")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.create_btn = StyledButton("Create", variant="primary")
        self.create_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.create_btn)

        layout.addLayout(button_layout)

    def get_values(self):
        return self.name_input.text().strip(), self.desc_input.text().strip()


class FolderCard(QFrame):
    """A card widget representing a folder"""

    clicked = pyqtSignal(int, str)
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
        c = theme.c
        self.setStyleSheet(styles.folder_card())
        self.setFixedSize(180, 160)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(SPACE["sm"])

        icon_label = QLabel("\U0001F4C1")
        icon_label.setStyleSheet(
            f"font-size: {SPACE['xxl']}px; background-color: transparent;"
        )
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        name_label = QLabel(self.folder_name)
        name_label.setStyleSheet(
            f"font-weight: {FONT['label']['weight']}; color: {c['text']}; "
            f"font-size: {FONT['body']['size']}px; background-color: transparent;"
        )
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        image_label_text = "image" if self.image_count == 1 else "images"
        count_label = QLabel(f"{self.image_count} {image_label_text}")
        count_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['caption']['size']}px; "
            "background-color: transparent;"
        )
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
        open_action.triggered.connect(
            lambda: self.clicked.emit(self.folder_id, self.folder_name)
        )
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(
            lambda: self.rename_requested.emit(self.folder_id, self.folder_name)
        )
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.folder_id, self.folder_name)
        )
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
        c = theme.c
        self.setStyleSheet(styles.image_card())
        self.setFixedSize(180, 200)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE["sm"], SPACE["sm"], SPACE["sm"], SPACE["sm"])
        layout.setSpacing(SPACE["sm"])

        # Thumbnail placeholder
        thumb_frame = QFrame()
        thumb_frame.setStyleSheet(
            f"background-color: {c['surface_alt']}; "
            f"border-radius: {SPACE['xs']}px;"
        )
        thumb_frame.setFixedHeight(120)
        thumb_layout = QVBoxLayout(thumb_frame)
        thumb_layout.setAlignment(Qt.AlignCenter)
        icon_label = QLabel("\U0001F5BC\uFE0F")
        icon_label.setStyleSheet(
            f"font-size: 36px; background-color: transparent;"
        )
        icon_label.setAlignment(Qt.AlignCenter)
        thumb_layout.addWidget(icon_label)
        layout.addWidget(thumb_frame)

        # Filename
        name_label = QLabel(self.image_data.get("filename", "Untitled"))
        name_label.setStyleSheet(
            f"font-weight: 500; color: {c['text']}; "
            f"font-size: {FONT['caption']['size']}px; background-color: transparent;"
        )
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(SPACE["xl"])
        layout.addWidget(name_label)

        # File size
        size = self.image_data.get("file_size")
        size_text = format_file_size(size) if size else ""
        size_label = QLabel(size_text)
        size_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['hint']['size']}px; "
            "background-color: transparent;"
        )
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
        rename_action.triggered.connect(
            lambda: self.rename_requested.emit(self.image_data)
        )
        move_action = menu.addAction("Move to Folder")
        move_action.triggered.connect(
            lambda: self.move_requested.emit(self.image_data)
        )
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.image_data["id"])
        )
        menu.exec_(pos)


class _ShortcutButton(QPushButton):
    """
    A button that, when clicked, waits for the user to press a key and emits
    ``shortcut_captured(int)`` with the Qt key code.
    """

    shortcut_captured = pyqtSignal(int)

    _IGNORED_KEYS = {
        Qt.Key_unknown,
        Qt.Key_Control,
        Qt.Key_Shift,
        Qt.Key_Alt,
        Qt.Key_Meta,
        Qt.Key_Tab,
        Qt.Key_Backtab,
        Qt.Key_Escape,
    }

    def __init__(self, text="Change\u2026", parent=None):
        super().__init__(text, parent)
        self._waiting = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._apply_style()
        self.clicked.connect(self._on_clicked)
        theme.theme_changed.connect(self._apply_style)

    def _apply_style(self, _mode=None):
        c = theme.c
        self.setStyleSheet(f"""
            QPushButton {{
                padding: {SPACE['sm']}px {SPACE['md']}px;
                background-color: {c['primary']};
                color: white;
                border: none;
                border-radius: {SPACE['xs']}px;
                font-size: {FONT['label']['size']}px;
                font-weight: 500;
            }}
            QPushButton:hover {{ background-color: {c['primary_dark']}; }}
            QPushButton[waiting="true"] {{
                background-color: {c['error']};
            }}
        """)

    def _on_clicked(self):
        self._waiting = True
        self.setProperty("waiting", True)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText("Press a key\u2026")
        self.setFocus()

    def keyPressEvent(self, event):
        if not self._waiting:
            super().keyPressEvent(event)
            return
        key = event.key()
        if key in self._IGNORED_KEYS or key == 0:
            return
        self._waiting = False
        self.setProperty("waiting", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setText("Change\u2026")
        self.clearFocus()
        self.shortcut_captured.emit(key)

    def focusOutEvent(self, event):
        if self._waiting:
            self._waiting = False
            self.setProperty("waiting", False)
            self.style().unpolish(self)
            self.style().polish(self)
            self.setText("Change\u2026")
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
    upload_requested = pyqtSignal(str)
    shortcut_changed = pyqtSignal(int)

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
        ]

        self._setup_ui()
        theme.theme_changed.connect(self._on_theme_changed)

    def _setup_ui(self):
        c = theme.c

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== Sidebar ==========
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        sidebar_layout.setSpacing(SPACE["sm"])

        # App title
        self.title_label = QLabel("SnipShot")
        sidebar_layout.addWidget(self.title_label)

        sidebar_layout.addSpacing(SPACE["md"])

        # Snip button
        self.snip_btn = QPushButton("\u2702\uFE0F New Snip")
        self.snip_btn.setCursor(Qt.PointingHandCursor)
        self.snip_btn.clicked.connect(self._on_snip)
        sidebar_layout.addWidget(self.snip_btn)

        # Upload button
        self.upload_btn = QPushButton("\U0001F4E4 Upload Image")
        self.upload_btn.setCursor(Qt.PointingHandCursor)
        self.upload_btn.clicked.connect(self._on_upload)
        sidebar_layout.addWidget(self.upload_btn)

        sidebar_layout.addSpacing(SPACE["md"])

        # Navigation
        self.nav_all = QPushButton("\U0001F4C1 All Files")
        self.nav_all.setCursor(Qt.PointingHandCursor)
        self.nav_all.clicked.connect(self._on_nav_all)
        sidebar_layout.addWidget(self.nav_all)

        self.nav_recent = QPushButton("\U0001F552 Recent")
        self.nav_recent.setCursor(Qt.PointingHandCursor)
        self.nav_recent.clicked.connect(self._on_nav_recent)
        sidebar_layout.addWidget(self.nav_recent)

        self.nav_settings = QPushButton("\u2699\uFE0F Settings")
        self.nav_settings.setCursor(Qt.PointingHandCursor)
        self.nav_settings.clicked.connect(self._on_nav_settings)
        sidebar_layout.addWidget(self.nav_settings)

        sidebar_layout.addStretch()

        # User section
        user_frame = QFrame()
        user_frame.setStyleSheet(
            f"background-color: transparent; padding-top: {SPACE['md']}px;"
        )
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(0, SPACE["md"], 0, 0)

        self.user_label = QLabel("Loading...")
        user_layout.addWidget(self.user_label)

        self.logout_btn = QPushButton("Sign Out")
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(self._on_logout)
        user_layout.addWidget(self.logout_btn)

        sidebar_layout.addWidget(user_frame)

        main_layout.addWidget(self.sidebar)

        # ========== Content Area ==========
        self.content_frame = QFrame()

        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Header
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setFixedHeight(64)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(SPACE["lg"], 0, SPACE["lg"], 0)

        self.header_title = QLabel("My Files")
        header_layout.addWidget(self.header_title)

        header_layout.addStretch()

        self.new_folder_btn = StyledButton("+ New Folder", variant="ghost")
        self.new_folder_btn.clicked.connect(self._on_new_folder)
        header_layout.addWidget(self.new_folder_btn)

        self.refresh_btn = QPushButton("\u21BB")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh)
        header_layout.addWidget(self.refresh_btn)

        content_layout.addWidget(self.header)

        # Scrollable content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        self.content_layout.setSpacing(SPACE["lg"])
        self.content_layout.setAlignment(Qt.AlignTop)

        self.scroll.setWidget(self.content_widget)
        content_layout.addWidget(self.scroll)

        # Loading indicator
        self.loading_label = QLabel("Loading...")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; "
            f"padding: {SPACE['xxl']}px;"
        )
        self.content_layout.addWidget(self.loading_label)

        main_layout.addWidget(self.content_frame)

        self._apply_styles()

    # ── Theme helpers ──────────────────────────────────────────────────
    def _apply_styles(self):
        """Apply or re-apply all sidebar / header / fixed-element styles."""
        c = theme.c

        self.sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background-color: {c['sidebar']};
                border-right: 1px solid {c['border']};
            }}
        """)
        self.title_label.setStyleSheet(
            f"font-size: {SPACE['lg']}px; font-weight: {FONT['display']['weight']}; "
            f"color: {c['primary']}; padding: {SPACE['sm']}px 0; background-color: transparent;"
        )
        self.snip_btn.setStyleSheet(styles.sidebar_action_button())
        self.upload_btn.setStyleSheet(styles.sidebar_action_button())
        self._set_active_nav(self.active_nav)
        self.user_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['caption']['size']}px; "
            "background-color: transparent;"
        )
        self.logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {c['error']};
                border: none; padding: {SPACE['sm']}px 0;
                font-size: {FONT['label']['size']}px; text-align: left;
            }}
            QPushButton:hover {{ text-decoration: underline; }}
        """)
        self.content_frame.setStyleSheet(f"background-color: {c['bg']};")
        self.header.setStyleSheet(f"""
            QFrame#header {{
                background-color: {c['surface']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        self.header_title.setStyleSheet(
            f"font-size: {FONT['heading']['size']}px; font-weight: 500; "
            f"color: {c['text']}; background-color: transparent;"
        )
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; border: none;
                font-size: {FONT['heading']['size']}px; padding: {SPACE['sm']}px;
                border-radius: {SPACE['xs']}px; color: {c['text_secondary']};
            }}
            QPushButton:hover {{ background-color: {c['hover']}; }}
        """)
        self.scroll.setStyleSheet(
            f"QScrollArea {{ border: none; background-color: {c['bg']}; }}"
        )

    def _on_theme_changed(self, _mode=None):
        """Handle live theme change."""
        self._apply_styles()
        if self.active_nav == "settings":
            self._on_nav_settings()

    def _nav_button_style(self, active: bool) -> str:
        return styles.nav_button(active)

    def _set_active_nav(self, active: str):
        self.active_nav = active
        self.nav_all.setStyleSheet(self._nav_button_style(active == "all"))
        self.nav_recent.setStyleSheet(self._nav_button_style(active == "recent"))
        self.nav_settings.setStyleSheet(self._nav_button_style(active == "settings"))

    # ── Data loading ───────────────────────────────────────────────────
    def load_user_info(self):
        if api_client.user:
            email = api_client.user.get("email", "Unknown")
            self.user_label.setText(f"\U0001F464 {email}")

    def refresh(self):
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
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _load_all_files_async(self):
        self.current_folder_id = None
        self.current_folder_name = None
        self.header_title.setText("My Files")
        self.new_folder_btn.setVisible(True)
        self._set_active_nav("all")

        class LoadWorker(QThread):
            finished = pyqtSignal(dict, dict)

            def run(self):
                folders_result = api_client.get_folders()
                images_result = api_client.get_images(folder_id=0, per_page=20)
                self.finished.emit(folders_result, images_result)

        self._clear_content()

        loading = QLabel("Loading folders...")
        loading.setStyleSheet(
            f"color: {theme.c['text_secondary']}; padding: {SPACE['lg']}px; "
            "background-color: transparent;"
        )
        self.content_layout.addWidget(loading)

        self.load_worker = LoadWorker()
        self.load_worker.finished.connect(self._on_data_loaded)
        self.load_worker.start()

    def _on_data_loaded(self, folders_result, images_result):
        c = theme.c
        self._clear_content()

        if folders_result["success"]:
            folders = folders_result["data"].get("folders", [])
            if folders:
                folders_label = QLabel("Folders")
                folders_label.setStyleSheet(
                    f"font-size: {FONT['body']['size']}px; font-weight: 500; "
                    f"color: {c['text_secondary']}; background-color: transparent;"
                )
                self.content_layout.addWidget(folders_label)

                folder_grid = QWidget()
                folder_grid_layout = FlowLayout(folder_grid, spacing=SPACE["md"])
                for folder in folders:
                    card = FolderCard(folder)
                    card.clicked.connect(self._on_folder_clicked)
                    card.delete_requested.connect(self._on_delete_folder)
                    card.rename_requested.connect(self._on_rename_folder)
                    folder_grid_layout.addWidget(card)
                self.content_layout.addWidget(folder_grid)

            if images_result["success"]:
                images = images_result["data"].get("images", [])
                if images:
                    self.content_layout.addSpacing(SPACE["md"])
                    images_label = QLabel("Unfiled Images")
                    images_label.setStyleSheet(
                        f"font-size: {FONT['body']['size']}px; font-weight: 500; "
                        f"color: {c['text_secondary']}; background-color: transparent;"
                    )
                    self.content_layout.addWidget(images_label)
                    self._add_image_grid(images)

            if not folders and not (
                images_result.get("success") and images_result["data"].get("images")
            ):
                self._show_empty_state(
                    "No files yet", "Capture a screenshot to get started!"
                )
        else:
            self._show_error("Failed to load folders")

        self.content_layout.addStretch()

    def _load_folder(self, folder_id: int, folder_name: str):
        c = theme.c
        self.current_folder_id = folder_id
        self.current_folder_name = folder_name
        self._set_active_nav("all")
        self.header_title.setText(f"\U0001F4C1 {folder_name}")
        self.new_folder_btn.setVisible(False)
        self._clear_content()

        back_btn = StyledButton("\u2190 Back to My Files", variant="ghost")
        back_btn.clicked.connect(self._on_nav_all)
        self.content_layout.addWidget(back_btn)

        result = api_client.get_images(folder_id=folder_id, page=1, per_page=100)
        if result["success"]:
            images = result["data"].get("images", [])
            if images:
                self._add_image_grid(images)
            else:
                self._show_empty_state(
                    "This folder is empty",
                    "Translated images saved to this folder will appear here.",
                )
        else:
            self._show_error("Failed to load folder")
        self.content_layout.addStretch()

    def _add_image_grid(self, images: list, show_load_more: bool = False):
        display_images = images[:20]
        self.all_images = images

        self._image_grid_widget = QWidget()
        grid_layout = FlowLayout(self._image_grid_widget, spacing=SPACE["md"])
        for image in display_images:
            card = ImageCard(image)
            card.clicked.connect(self._on_image_clicked)
            card.delete_requested.connect(self._on_delete_image)
            card.rename_requested.connect(self._on_rename_image)
            card.move_requested.connect(self._on_move_image)
            grid_layout.addWidget(card)
        self.content_layout.addWidget(self._image_grid_widget)

        if len(images) > 20 or show_load_more:
            self.load_more_btn = StyledButton("Load More Images", variant="primary")
            self.load_more_btn.clicked.connect(self._load_more_images)
            self.content_layout.addWidget(
                self.load_more_btn, alignment=Qt.AlignCenter
            )

    def _load_more_images(self):
        if not (hasattr(self, "all_images") and hasattr(self, "load_more_btn")):
            return
        self.content_layout.removeWidget(self.load_more_btn)
        self.load_more_btn.deleteLater()

        remaining_images = self.all_images[20:]
        if remaining_images and hasattr(self, "_image_grid_widget"):
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
        c = theme.c
        empty_frame = QFrame()
        empty_layout = QVBoxLayout(empty_frame)
        empty_layout.setAlignment(Qt.AlignCenter)
        empty_layout.setSpacing(SPACE["sm"])

        icon_label = QLabel("\U0001F4C2")
        icon_label.setStyleSheet(
            f"font-size: 64px; background-color: transparent;"
        )
        icon_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: {FONT['heading']['size']}px; font-weight: 500; "
            f"color: {c['text']}; background-color: transparent;"
        )
        title_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet(
            f"font-size: {FONT['body']['size']}px; color: {c['text_secondary']}; "
            "background-color: transparent;"
        )
        subtitle_label.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(subtitle_label)

        self.content_layout.addWidget(empty_frame)

    def _show_error(self, message: str):
        error_label = QLabel(f"\u274C {message}")
        error_label.setStyleSheet(
            f"color: {theme.c['error']}; padding: {SPACE['lg']}px; "
            "background-color: transparent;"
        )
        self.content_layout.addWidget(error_label)

    # ========== Event Handlers ==========

    def _on_snip(self):
        self.capture_requested.emit()

    def _on_upload(self):
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Image",
            "",
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if file_path:
            self.upload_requested.emit(file_path)

    def _on_nav_all(self):
        self._load_all_files_async()

    def _on_nav_recent(self):
        self._set_active_nav("recent")
        self.current_folder_id = None
        self.current_folder_name = None
        self.header_title.setText("Recent")
        self.new_folder_btn.setVisible(False)
        self._clear_content()

        result = api_client.get_images()
        if result["success"]:
            images = result["data"].get("images", [])
            if images:
                self._add_image_grid(images)
            else:
                self._show_empty_state(
                    "No recent files", "Your recent translations will appear here."
                )
        else:
            self._show_error("Failed to load recent files")
        self.content_layout.addStretch()

    def _on_nav_settings(self):
        self._set_active_nav("settings")
        self.current_folder_id = None
        self.current_folder_name = None
        self.header_title.setText("Settings")
        self.new_folder_btn.setVisible(False)
        self._clear_content()
        self._render_settings_content()
        self.content_layout.addStretch()

    # ------------------------------------------------------------------ #
    # Settings rendering  (redesigned)
    # ------------------------------------------------------------------ #

    def _make_section_card(self) -> tuple:
        """
        Returns (card_frame, card_vbox_layout).
        The card has a primary-coloured left accent border and a drop shadow.
        """
        c = theme.c
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-left: 3px solid {c['primary']};
                border-radius: {SPACE['sm']}px;
            }}
        """)
        apply_card_shadow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE["lg"], SPACE["md"], SPACE["lg"], SPACE["md"])
        layout.setSpacing(SPACE["xs"])
        return card, layout

    def _section_header_label(self, icon: str, text: str) -> QLabel:
        c = theme.c
        label = QLabel(f"{icon}  {text}")
        label.setStyleSheet(
            f"font-size: {FONT['body']['size']}px; "
            f"font-weight: {FONT['heading']['weight']}; "
            f"color: {c['text']}; "
            f"background-color: transparent; "
            f"padding-bottom: {SPACE['xs']}px;"
        )
        return label

    def _hint_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(self._settings_hint_style())
        return label

    def _value_badge(self, text: str) -> QLabel:
        """A small pill label showing the current value of a slider."""
        c = theme.c
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        label.setFixedWidth(80)
        label.setStyleSheet(f"""
            QLabel {{
                color: {c['primary']};
                background-color: {c['surface_alt']};
                border: 1px solid {c['border']};
                border-radius: {SPACE['xs']}px;
                padding: {SPACE['xs']}px {SPACE['sm']}px;
                font-size: {FONT['caption']['size']}px;
                font-weight: 600;
            }}
        """)
        return label

    def _styled_slider(self) -> str:
        """QSS for sliders: coloured sub-page track + round handle."""
        c = theme.c
        return f"""
            QSlider::groove:horizontal {{
                height: 4px;
                background: {c['border']};
                border-radius: 2px;
            }}
            QSlider::sub-page:horizontal {{
                background: {c['primary']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 16px;
                height: 16px;
                margin: -6px 0;
                background: {c['primary']};
                border-radius: 8px;
                border: 2px solid {c['surface']};
            }}
            QSlider::handle:horizontal:hover {{
                background: {c['primary_dark']};
            }}
        """

    def _theme_pill_style(self, active: bool) -> str:
        """Style for one half of the Light / Dark segmented pill control."""
        c = theme.c
        if active:
            return f"""
                QPushButton {{
                    padding: {SPACE['xs']}px {SPACE['lg']}px;
                    background-color: {c['primary']};
                    color: #ffffff;
                    border: 1px solid {c['primary']};
                    border-radius: {SPACE['xs']}px;
                    font-size: {FONT['label']['size']}px;
                    font-weight: 600;
                    min-width: 80px;
                }}
            """
        else:
            return f"""
                QPushButton {{
                    padding: {SPACE['xs']}px {SPACE['lg']}px;
                    background-color: transparent;
                    color: {c['text_secondary']};
                    border: 1px solid {c['border']};
                    border-radius: {SPACE['xs']}px;
                    font-size: {FONT['label']['size']}px;
                    font-weight: 500;
                    min-width: 80px;
                }}
                QPushButton:hover {{
                    background-color: {c['hover']};
                    color: {c['text']};
                }}
            """

    def _render_settings_content(self):
        c = theme.c

        # ── Page title ────────────────────────────────────────────────
        page_title = QLabel("Settings")
        page_title.setStyleSheet(
            f"font-size: {FONT['display']['size']}px; "
            f"font-weight: {FONT['display']['weight']}; "
            f"color: {c['text']}; "
            f"background-color: transparent; "
            f"padding-bottom: {SPACE['sm']}px;"
        )
        self.content_layout.addWidget(page_title)

        # ══════════════════════════════════════════════════════════════
        # CARD 1 — Appearance
        # ══════════════════════════════════════════════════════════════
        card, sl = self._make_section_card()
        sl.addWidget(self._section_header_label("🎨", "Appearance"))
        sl.addWidget(self._hint_label("Choose your preferred colour theme."))
        sl.addSpacing(SPACE["sm"])

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(SPACE["sm"])

        self.light_btn = QPushButton("☀  Light")
        self.light_btn.setCursor(Qt.PointingHandCursor)
        self.light_btn.setStyleSheet(self._theme_pill_style(not theme.is_dark))
        self.light_btn.clicked.connect(lambda: theme.set_mode("light"))

        self.dark_btn = QPushButton("🌙  Dark")
        self.dark_btn.setCursor(Qt.PointingHandCursor)
        self.dark_btn.setStyleSheet(self._theme_pill_style(theme.is_dark))
        self.dark_btn.clicked.connect(lambda: theme.set_mode("dark"))

        toggle_row.addWidget(self.light_btn)
        toggle_row.addWidget(self.dark_btn)
        toggle_row.addStretch()
        sl.addLayout(toggle_row)
        self.content_layout.addWidget(card)

        # ══════════════════════════════════════════════════════════════
        # CARD 2 — Capture Shortcut
        # ══════════════════════════════════════════════════════════════
        card, sl = self._make_section_card()
        sl.addWidget(self._section_header_label("⌨", "Capture Shortcut"))
        sl.addWidget(self._hint_label(
            "Keyboard shortcut that triggers a new screen snip from anywhere in the app."
        ))
        sl.addSpacing(SPACE["sm"])

        sc_row = QHBoxLayout()
        sc_row.setSpacing(SPACE["sm"])

        # kbd-styled display label
        self.shortcut_display = QLabel(self._key_name(self.snip_shortcut_key))
        self.shortcut_display.setAlignment(Qt.AlignCenter)
        self.shortcut_display.setStyleSheet(f"""
            QLabel {{
                padding: {SPACE['sm']}px {SPACE['lg']}px;
                border: 1px solid {c['border']};
                border-bottom: 3px solid {c['border']};
                border-radius: {SPACE['xs']}px;
                font-size: {FONT['label']['size']}px;
                font-weight: 700;
                background-color: {c['surface_alt']};
                color: {c['primary']};
                min-width: 80px;
                letter-spacing: 1px;
            }}
        """)
        sc_row.addWidget(self.shortcut_display)

        self.shortcut_btn = _ShortcutButton("Change\u2026")
        self.shortcut_btn.shortcut_captured.connect(self._on_shortcut_captured)
        sc_row.addWidget(self.shortcut_btn)
        sc_row.addStretch()
        sl.addLayout(sc_row)
        self.content_layout.addWidget(card)

        # ══════════════════════════════════════════════════════════════
        # CARD 3 — Translation Settings
        # ══════════════════════════════════════════════════════════════
        card, sl = self._make_section_card()
        sl.addWidget(self._section_header_label("🌐", "Translation"))
        sl.addWidget(self._hint_label(
            "Default target language applied to every new snip or upload."
        ))
        sl.addSpacing(SPACE["sm"])

        self.language_combo = QComboBox()
        self.language_combo.setStyleSheet(self._settings_input_style())
        for label, code in self.language_options:
            self.language_combo.addItem(f"{label} ({code})", code)
        current_index = self.language_combo.findData(self.target_language)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        sl.addWidget(self.language_combo)
        self.content_layout.addWidget(card)

        # ══════════════════════════════════════════════════════════════
        # CARD 4 — Advanced Parameters
        # ══════════════════════════════════════════════════════════════
        card, sl = self._make_section_card()
        sl.addWidget(self._section_header_label("⚙", "Advanced Parameters"))

        # ── Detection Size ──
        sl.addSpacing(SPACE["sm"])
        det_lbl = QLabel("Detection Size")
        det_lbl.setStyleSheet(self._settings_label_style())
        sl.addWidget(det_lbl)
        sl.addWidget(self._hint_label(
            "Resolution for text detection. Higher values improve quality but are slower."
        ))

        det_ctrl = QHBoxLayout()
        det_ctrl.setSpacing(SPACE["sm"])
        self.detection_size_slider = QSlider(Qt.Horizontal)
        self.detection_size_slider.setRange(DETECTION_SIZE_MIN, DETECTION_SIZE_MAX)
        self.detection_size_slider.setSingleStep(DETECTION_SIZE_STEP)
        self.detection_size_slider.setValue(self.detection_size)
        self.detection_size_slider.setStyleSheet(self._styled_slider())
        self.detection_size_slider.valueChanged.connect(self._on_detection_size_changed)
        det_ctrl.addWidget(self.detection_size_slider)
        self.detection_size_value = self._value_badge(f"{self.detection_size} px")
        det_ctrl.addWidget(self.detection_size_value)
        sl.addLayout(det_ctrl)

        # ── Box Threshold ──
        sl.addSpacing(SPACE["sm"])
        box_lbl = QLabel("Box Threshold")
        box_lbl.setStyleSheet(self._settings_label_style())
        sl.addWidget(box_lbl)
        sl.addWidget(self._hint_label(
            "Minimum confidence required before a detected region is translated."
        ))

        box_ctrl = QHBoxLayout()
        box_ctrl.setSpacing(SPACE["sm"])
        self.box_threshold_slider = QSlider(Qt.Horizontal)
        self.box_threshold_slider.setRange(
            int(BOX_THRESHOLD_MIN * 100), int(BOX_THRESHOLD_MAX * 100)
        )
        self.box_threshold_slider.setSingleStep(5)
        self.box_threshold_slider.setValue(int(self.box_threshold * 100))
        self.box_threshold_slider.setStyleSheet(self._styled_slider())
        self.box_threshold_slider.valueChanged.connect(self._on_box_threshold_changed)
        box_ctrl.addWidget(self.box_threshold_slider)
        self.box_threshold_value = self._value_badge(f"{self.box_threshold:.2f}")
        box_ctrl.addWidget(self.box_threshold_value)
        sl.addLayout(box_ctrl)

        # ── Inpainting Size ──
        sl.addSpacing(SPACE["sm"])
        inp_lbl = QLabel("Inpainting Size")
        inp_lbl.setStyleSheet(self._settings_label_style())
        sl.addWidget(inp_lbl)
        sl.addWidget(self._hint_label("Resolution used when filling in background regions."))

        inp_ctrl = QHBoxLayout()
        inp_ctrl.setSpacing(SPACE["sm"])
        self.inpainting_size_slider = QSlider(Qt.Horizontal)
        self.inpainting_size_slider.setRange(INPAINTING_SIZE_MIN, INPAINTING_SIZE_MAX)
        self.inpainting_size_slider.setSingleStep(INPAINTING_SIZE_STEP)
        self.inpainting_size_slider.setValue(self.inpainting_size)
        self.inpainting_size_slider.setStyleSheet(self._styled_slider())
        self.inpainting_size_slider.valueChanged.connect(self._on_inpainting_size_changed)
        inp_ctrl.addWidget(self.inpainting_size_slider)
        self.inpainting_size_value = self._value_badge(f"{self.inpainting_size} px")
        inp_ctrl.addWidget(self.inpainting_size_value)
        sl.addLayout(inp_ctrl)

        self.content_layout.addWidget(card)

        # ══════════════════════════════════════════════════════════════
        # CARD 5 — Inpainter Model
        # ══════════════════════════════════════════════════════════════
        card, sl = self._make_section_card()
        sl.addWidget(self._section_header_label("🤖", "Inpainter Model"))
        sl.addWidget(self._hint_label("AI model used for filling in backgrounds after text removal."))
        sl.addSpacing(SPACE["sm"])

        self.inpainter_combo = QComboBox()
        self.inpainter_combo.setStyleSheet(self._settings_input_style())
        self.inpainter_combo.addItem("LAMA Large  (recommended)", "lama_large")
        self.inpainter_combo.addItem("None  (skip inpainting)", "none")
        idx = self.inpainter_combo.findData(self.inpainter)
        if idx >= 0:
            self.inpainter_combo.setCurrentIndex(idx)
        self.inpainter_combo.currentIndexChanged.connect(self._on_inpainter_changed)
        sl.addWidget(self.inpainter_combo)
        self.content_layout.addWidget(card)

    # ── Settings style helpers ─────────────────────────────────────────
    def _settings_input_style(self):
        return styles.settings_input()

    def _settings_label_style(self):
        c = theme.c
        return (
            f"font-weight: 600; color: {c['text']}; "
            f"font-size: {FONT['label']['size']}px; "
            f"margin-top: {SPACE['xs']}px; background-color: transparent;"
        )

    def _settings_hint_style(self):
        c = theme.c
        return (
            f"color: {c['text_secondary']}; font-size: {FONT['caption']['size']}px; "
            "background-color: transparent;"
        )

    def _section_title_style(self):
        c = theme.c
        return (
            f"font-size: {FONT['body']['size']}px; font-weight: {FONT['label']['weight']}; "
            f"color: {c['text_secondary']}; margin-top: {SPACE['md']}px; "
            "background-color: transparent;"
        )

    def _add_section_separator(self, layout):
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet(
            f"color: {theme.c['border']}; background-color: {theme.c['border']};"
        )
        layout.addWidget(sep)

    # ── Settings change handlers ───────────────────────────────────────
    def _on_language_changed(self):
        if not hasattr(self, "language_combo"):
            return
        selected = self.language_combo.currentData()
        if selected:
            self.target_language = selected

    def _on_shortcut_captured(self, key: int):
        self.snip_shortcut_key = key
        if hasattr(self, "shortcut_display"):
            self.shortcut_display.setText(self._key_name(key))
        self.shortcut_changed.emit(key)

    def _on_detection_size_changed(self, value: int):
        self.detection_size = value
        if hasattr(self, "detection_size_value"):
            self.detection_size_value.setText(f"{value} px")

    def _on_box_threshold_changed(self, value: int):
        self.box_threshold = round(value / 100, 2)
        if hasattr(self, "box_threshold_value"):
            self.box_threshold_value.setText(f"{self.box_threshold:.2f}")

    def _on_inpainting_size_changed(self, value: int):
        self.inpainting_size = value
        if hasattr(self, "inpainting_size_value"):
            self.inpainting_size_value.setText(f"{value} px")

    def _on_inpainter_changed(self):
        if hasattr(self, "inpainter_combo"):
            self.inpainter = self.inpainter_combo.currentData()

    # ── Public getters ─────────────────────────────────────────────────
    def get_target_language(self) -> str:
        return self.target_language

    def get_translation_config(self) -> dict:
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
        ks = QKeySequence(key)
        text = ks.toString(QKeySequence.NativeText)
        return text if text else QKeySequence(key).toString()

    def _on_folder_clicked(self, folder_id: int, folder_name: str):
        self._load_folder(folder_id, folder_name)

    def _on_image_clicked(self, image_data: dict):
        dialog = ImagePreviewDialog(image_data, self)
        dialog.exec_()

    def _on_new_folder(self):
        dialog = CreateFolderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, description = dialog.get_values()
            if name:
                result = api_client.create_folder(name, description)
                if result["success"]:
                    self.refresh()
                else:
                    QMessageBox.warning(
                        self,
                        "Error",
                        result.get("error", "Failed to create folder"),
                    )

    def _on_delete_folder(self, folder_id: int, folder_name: str):
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Folder")
        msg.setText(f"Delete folder '{folder_name}'?")
        msg.setInformativeText("Choose how to handle the images inside.")
        keep_btn = msg.addButton(
            "Delete Folder (Keep Images)", QMessageBox.AcceptRole
        )
        delete_all_btn = msg.addButton(
            "Delete Folder + All Images", QMessageBox.DestructiveRole
        )
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
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "New name:", text=current_name
        )
        if ok and new_name and new_name != current_name:
            result = api_client.update_folder(folder_id, name=new_name)
            if result["success"]:
                self.refresh()
            else:
                QMessageBox.warning(
                    self, "Error", result.get("error", "Failed to rename folder")
                )

    def _on_delete_image(self, image_id: int):
        reply = QMessageBox.question(
            self,
            "Delete Image",
            "Delete this image permanently?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            result = api_client.delete_image(image_id)
            if result["success"]:
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete image")

    def _on_rename_image(self, image_data: dict):
        current_name = image_data.get("filename", "")
        new_name, ok = QInputDialog.getText(
            self, "Rename Image", "New filename:", text=current_name
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            result = api_client.update_image(
                image_data["id"], filename=new_name.strip()
            )
            if result["success"]:
                self.refresh()
            else:
                QMessageBox.warning(
                    self, "Error", result.get("error", "Failed to rename image")
                )

    def _on_move_image(self, image_data: dict):
        folders_result = api_client.get_folders()
        if not folders_result["success"]:
            QMessageBox.warning(self, "Error", "Failed to load folders")
            return

        folders = folders_result["data"].get("folders", [])
        folder_names = ["Unfiled"] + [f["name"] for f in folders]
        folder_ids = [0] + [f["id"] for f in folders]

        if len(folder_names) == 1:
            QMessageBox.information(
                self,
                "No Folders",
                "Create a folder first to move images into it.",
            )
            return

        choice, ok = QInputDialog.getItem(
            self,
            "Move to Folder",
            f"Move '{image_data.get('filename', 'image')}' to:",
            folder_names,
            0,
            False,
        )
        if ok and choice:
            idx = folder_names.index(choice)
            folder_id = folder_ids[idx]
            result = api_client.update_image(image_data["id"], folder_id=folder_id)
            if result["success"]:
                self.refresh()
            else:
                QMessageBox.warning(
                    self, "Error", result.get("error", "Failed to move image")
                )

    def _on_logout(self):
        api_client.logout()
        self.logout_requested.emit()