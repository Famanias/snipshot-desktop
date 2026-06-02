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
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QFont, QKeySequence, QCloseEvent
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
from .styles import SPACE, FONT, apply_card_shadow, load_icon
from .components import StyledButton

class ThumbnailLabel(QLabel):
    """A QLabel that asynchronously loads an image from a URL or local file path."""

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.setText("\U0001F5BC\uFE0F")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("font-size: 36px; background-color: transparent;")

        if url:
            import os
            from urllib.parse import unquote
            clean_url = unquote(url)
            if clean_url.startswith("file:///"):
                clean_url = clean_url[8:]
            elif clean_url.startswith("file://"):
                clean_url = clean_url[7:]
            clean_url = os.path.normpath(clean_url)

            if os.path.exists(clean_url) and os.path.isfile(clean_url):
                self.set_pixmap_from_file(clean_url)
            elif url.startswith("http"):
                self.load_from_url(url)

    def set_pixmap_from_file(self, path):
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            self.set_scaled_pixmap(pixmap)

    def load_from_url(self, url):
        self.nam = QNetworkAccessManager(self)
        self.nam.finished.connect(self._on_finished)
        self.nam.get(QNetworkRequest(QUrl(url)))

    def _on_finished(self, reply):
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self.set_scaled_pixmap(pixmap)
        reply.deleteLater()

    def set_scaled_pixmap(self, pixmap):
        scaled = pixmap.scaled(
            200, 110,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.setPixmap(scaled)
        self.setStyleSheet("background-color: transparent; border: none;")


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


class CacheLoaderWorker(QThread):
    finished = pyqtSignal(list, list)   # folders, images
    error = pyqtSignal(str)
    progress = pyqtSignal(int)          # items loaded so far

    SOFT_CAP = 10_000
    PAGE_SIZE = 100

    def __init__(self, api_client):
        super().__init__()
        self._api_client = api_client
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            folders_res = self._api_client.get_folders()
            if self._cancelled:
                return
            folders = folders_res.get("data", []) if folders_res.get("success") else []

            images = []
            page = 1
            while True:
                if self._cancelled:
                    return
                batch_res = self._api_client.get_images(page=page, per_page=self.PAGE_SIZE)
                if self._cancelled:
                    return
                if not batch_res.get("success"):
                    raise Exception(batch_res.get("error", "Failed to fetch images"))
                
                batch_data = batch_res.get("data", {})
                batch = batch_data.get("images", []) if isinstance(batch_data, dict) else batch_data
                if not batch:
                    break
                images.extend(batch)
                self.progress.emit(len(images))
                if len(images) >= self.SOFT_CAP:
                    break
                page += 1

            self.finished.emit(folders, images)

        except Exception as e:
            self.error.emit(str(e))


def filter_items(
    query: str,
    folders: list,
    images: list,
    cancelled_flag=None
) -> tuple[list, list]:
    """Pure filtering function. Decoupled from UI and workers."""
    q = query.lower().strip()

    matched_folders = []
    for folder in folders:
        if cancelled_flag and cancelled_flag():
            return [], []
        if q in (folder.get("name") or "").lower() \
           or q in (folder.get("description") or "").lower():
            matched_folders.append(folder)

    matched_images = []
    for image in images:
        if cancelled_flag and cancelled_flag():
            return [], []
        if q in (image.get("filename") or "").lower() \
           or q in (image.get("original_filename") or "").lower() \
           or q in (image.get("source_language") or "").lower() \
           or q in (image.get("target_language") or "").lower():
            matched_images.append(image)

    return matched_folders, matched_images


class InMemorySearchWorker(QThread):
    finished = pyqtSignal(list, list)   # matched_folders, matched_images
    error = pyqtSignal(str)

    def __init__(self, query, folders, images):
        super().__init__()
        self._query = query
        self._folders = folders
        self._images = images
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            matched_folders, matched_images = filter_items(
                self._query, self._folders, self._images,
                cancelled_flag=lambda: self._cancelled
            )
            if not self._cancelled:
                self.finished.emit(matched_folders, matched_images)
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
    image_dropped = pyqtSignal(int, int)

    def __init__(self, folder_data: dict, parent=None):
        super().__init__(parent)
        self.folder_id = folder_data["id"]
        self.folder_name = folder_data["name"]
        self.image_count = folder_data.get("image_count", 0)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)
        self._setup_ui()
        theme.theme_changed.connect(self._on_theme_changed)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-snipshot-image-id"):
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-snipshot-image-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def dropEvent(self, event):
        self.setProperty("dragOver", False)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()
        
        mime_data = event.mimeData()
        if mime_data.hasFormat("application/x-snipshot-image-id"):
            image_id_str = mime_data.data("application/x-snipshot-image-id").data().decode('utf-8')
            try:
                image_id = int(image_id_str)
                self.image_dropped.emit(self.folder_id, image_id)
                event.acceptProposedAction()
            except ValueError:
                event.ignore()
        else:
            event.ignore()

    def _setup_ui(self):
        self.setFixedSize(200, 140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        layout.setSpacing(SPACE["sm"])

        # Top row: icon + menu button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)

        # Icon box
        self.icon_box = QFrame()
        self.icon_box.setFixedSize(36, 36)
        box_layout = QVBoxLayout(self.icon_box)
        box_layout.setContentsMargins(0, 0, 0, 0)
        box_layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setStyleSheet("background-color: transparent;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        box_layout.addWidget(self.icon_label)
        top_row.addWidget(self.icon_box)

        top_row.addStretch()

        # Menu button
        self.menu_btn = QPushButton()
        self.menu_btn.setFixedSize(24, 24)
        self.menu_btn.setIconSize(QSize(24, 24))
        self.menu_btn.clicked.connect(self._on_menu_clicked)
        top_row.addWidget(self.menu_btn)

        layout.addLayout(top_row)
        layout.addSpacing(SPACE["xs"])

        # Folder Name
        self.name_label = QLabel(self.folder_name)
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.name_label.setWordWrap(False)
        layout.addWidget(self.name_label)

        # Count
        image_label_text = "image" if self.image_count == 1 else "images"
        self.count_label = QLabel(f"{self.image_count} {image_label_text}")
        self.count_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.count_label)

        self._apply_style()

    def _apply_style(self):
        c = theme.c
        self.setStyleSheet(styles.folder_card())
        self.icon_box.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg']};
                border-radius: 8px;
            }}
        """)
        icon_pixmap = load_icon("folder_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg").pixmap(18, 18)
        self.icon_label.setPixmap(icon_pixmap)
        self.menu_btn.setIcon(load_icon("more_vert_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_secondary']};
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                color: {c['primary']};
            }}
        """)
        self.name_label.setStyleSheet(
            f"font-weight: 600; color: {c['text']}; "
            f"font-size: {FONT['body']['size']}px; background-color: transparent;"
        )
        self.count_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['caption']['size']}px; "
            "background-color: transparent;"
        )

    def _on_theme_changed(self, _mode=None):
        """Reload styles when theme changes."""
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.menu_btn.rect().contains(self.menu_btn.mapFrom(self, event.pos())):
                return
            self.drag_start_position = event.pos()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, "drag_start_position"):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        self._start_drag(event)

    def _start_drag(self, event):
        from PyQt5.QtGui import QDrag
        from PyQt5.QtCore import QMimeData, QByteArray

        mime_data = QMimeData()
        folder_id_str = str(self.folder_id)
        mime_data.setText(folder_id_str)
        mime_data.setData("application/x-snipshot-folder-id", QByteArray(folder_id_str.encode('utf-8')))

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        # Grab a scaled visual preview of the folder card for the drag icon
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.setHotSpot(self.drag_start_position)

        drag.exec_(Qt.MoveAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if hasattr(self, "drag_start_position"):
                # If released without dragging, trigger open folder (click)
                if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                    self.clicked.emit(self.folder_id, self.folder_name)
                del self.drag_start_position
        super().mouseReleaseEvent(event)

    def _on_menu_clicked(self):
        self._show_context_menu(QCursor.pos())

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
        self.setCursor(Qt.PointingHandCursor)
        self._setup_ui()
        theme.theme_changed.connect(self._on_theme_changed)

    def _setup_ui(self):
        self.setFixedSize(220, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image preview container
        self.preview_box = QFrame()
        self.preview_box.setFixedHeight(120)

        preview_layout = QVBoxLayout(self.preview_box)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(0)
        preview_layout.setAlignment(Qt.AlignCenter)

        self.thumbnail = ThumbnailLabel(self.image_data.get("public_url", ""))
        preview_layout.addWidget(self.thumbnail)

        layout.addWidget(self.preview_box)

        # Bottom info section
        self.info_section = QFrame()
        info_layout = QHBoxLayout(self.info_section)
        info_layout.setContentsMargins(SPACE["sm"], SPACE["sm"], SPACE["sm"], SPACE["sm"])
        info_layout.setSpacing(SPACE["xs"])

        labels_layout = QVBoxLayout()
        labels_layout.setSpacing(2)
        labels_layout.setContentsMargins(0, 0, 0, 0)

        filename = self.image_data.get("filename", "Untitled.png")
        self.name_label = QLabel(filename)
        self.name_label.setWordWrap(False)
        labels_layout.addWidget(self.name_label)

        size = self.image_data.get("file_size")
        size_text = format_file_size(size) if size else "0 KB"
        ext = filename.split(".")[-1].upper() if "." in filename else "PNG"
        self.meta_label = QLabel(f"{size_text} • {ext}")
        labels_layout.addWidget(self.meta_label)
        info_layout.addLayout(labels_layout, 1)

        # Menu button
        self.menu_btn = QPushButton()
        self.menu_btn.setFixedSize(24, 24)
        self.menu_btn.setIconSize(QSize(24, 24))
        self.menu_btn.clicked.connect(self._on_menu_clicked)
        info_layout.addWidget(self.menu_btn)

        layout.addWidget(self.info_section)

        self._apply_style()

    def _apply_style(self):
        c = theme.c
        self.setStyleSheet(styles.image_card())
        self.preview_box.setStyleSheet(f"""
            QFrame {{
                background-color: {c['bg']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }}
        """)
        self.info_section.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface_alt']};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
            }}
        """)
        self.name_label.setStyleSheet(
            f"font-weight: 600; color: {c['text']}; "
            f"font-size: 11px; background-color: transparent;"
        )
        self.meta_label.setStyleSheet(
            f"color: {c['text_tertiary']}; font-size: 9px; "
            "background-color: transparent;"
        )
        self.menu_btn.setIcon(load_icon("more_vert_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.menu_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_secondary']};
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                color: {c['primary']};
            }}
        """)

    def _on_theme_changed(self, _mode=None):
        """Reload styles when theme changes."""
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.menu_btn.rect().contains(self.menu_btn.mapFrom(self, event.pos())):
                return
            self.drag_start_position = event.pos()
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            return
        if not hasattr(self, "drag_start_position"):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        # Limit drag and drop to unfiled images
        if self.image_data.get("folder_id") is None:
            self._start_drag(event)

    def _start_drag(self, event):
        from PyQt5.QtGui import QDrag
        from PyQt5.QtCore import QMimeData, QByteArray

        mime_data = QMimeData()
        image_id_str = str(self.image_data["id"])
        mime_data.setText(image_id_str)
        mime_data.setData("application/x-snipshot-image-id", QByteArray(image_id_str.encode('utf-8')))

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        # Create a visually pleasing thumbnail of the image card for the drag action
        pixmap = self.grab()
        drag.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.setHotSpot(self.drag_start_position)

        drag.exec_(Qt.MoveAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if hasattr(self, "drag_start_position"):
                # If released without crossing the drag threshold, trigger click (view preview)
                if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
                    self.clicked.emit(self.image_data)
                del self.drag_start_position
        super().mouseReleaseEvent(event)

    def _on_menu_clicked(self):
        self._show_context_menu(QCursor.pos())

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


class TrashDropZone(QFrame):
    """
    A persistent floating trash/delete drop zone widget anchored to the bottom-right.
    Accepts drop events for both folders and images and handles deletion.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._is_drag_over = False
        self._setup_ui()
        theme.theme_changed.connect(self._on_theme_changed)

    def _setup_ui(self):
        self.setFixedSize(64, 64)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setStyleSheet("background-color: transparent;")
        layout.addWidget(self.icon_label)

        self.setToolTip("Drag here to delete permanently")
        self._apply_style()

    def _apply_style(self):
        c = theme.c
        icon_color_suffix = "E3E3E3" if theme.is_dark else "212121"
        icon_name = f"delete_24dp_{icon_color_suffix}_FILL0_wght400_GRAD0_opsz24.svg"

        if self._is_drag_over:
            bg_color = "#3B1C1C" if theme.is_dark else "#FEF2F2"
            icon_pixmap = load_icon(icon_name).pixmap(32, 32)
            self.setFixedSize(72, 72)
        else:
            bg_color = c["surface_alt"]
            icon_pixmap = load_icon(icon_name).pixmap(24, 24)
            self.setFixedSize(64, 64)

        self.icon_label.setPixmap(icon_pixmap)

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: none;
                border-radius: {self.width() // 2}px;
            }}
        """)
        apply_card_shadow(self)

        # Reposition parent if parent is DashboardWindow
        if hasattr(self.parent(), "_reposition_trash_drop_zone"):
            self.parent()._reposition_trash_drop_zone()

    def _on_theme_changed(self, _mode=None):
        self._apply_style()

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasFormat("application/x-snipshot-image-id") or mime_data.hasFormat("application/x-snipshot-folder-id"):
            event.acceptProposedAction()
            self._is_drag_over = True
            self._apply_style()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasFormat("application/x-snipshot-image-id") or mime_data.hasFormat("application/x-snipshot-folder-id"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._is_drag_over = False
        self._apply_style()

    def dropEvent(self, event):
        self._is_drag_over = False
        self._apply_style()

        mime_data = event.mimeData()
        if mime_data.hasFormat("application/x-snipshot-image-id"):
            image_id_str = mime_data.data("application/x-snipshot-image-id").data().decode('utf-8')
            try:
                image_id = int(image_id_str)
                if hasattr(self.parent(), "_delete_image_dropped"):
                    self.parent()._delete_image_dropped(image_id)
                event.acceptProposedAction()
            except ValueError:
                event.ignore()
        elif mime_data.hasFormat("application/x-snipshot-folder-id"):
            folder_id_str = mime_data.data("application/x-snipshot-folder-id").data().decode('utf-8')
            try:
                folder_id = int(folder_id_str)
                if hasattr(self.parent(), "_delete_folder_dropped"):
                    self.parent()._delete_folder_dropped(folder_id)
                event.acceptProposedAction()
            except ValueError:
                event.ignore()
        else:
            event.ignore()


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

        # Global Search Feature Cache & Thread Management
        self.api_client = api_client
        self._cached_folders = []
        self._cached_images = []
        self._current_view = "root"        # "root" | "folder" | "recent"
        self._current_folder_id = None
        self._current_folder_name = ""
        self.search_worker = None
        self.cache_loader_worker = None
        self.cache_update_worker = None

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.search_timer.timeout.connect(self._trigger_search)

        self._setup_ui()
        theme.theme_changed.connect(self._on_theme_changed)

    def _cancel_worker(self, attr: str):
        worker = getattr(self, attr, None)
        if worker is not None and worker.isRunning():
            try:
                worker.cancel()          # sets _cancelled = True
                worker.finished.disconnect()
                worker.error.disconnect()
            except (TypeError, RuntimeError):
                pass
            worker.wait(2000)            # wait up to 2s for clean exit
        setattr(self, attr, None)

    def _setup_ui(self):
        c = theme.c

        # Outer layout that holds TopAppBar and Split Area
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        # ========== TopAppBar Header ==========
        self.top_bar = QFrame()
        self.top_bar.setObjectName("topBar")
        self.top_bar.setFixedHeight(56)
        self.top_bar.setStyleSheet(f"""
            QFrame#topBar {{
                background-color: {c['surface_alt']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        top_layout = QHBoxLayout(self.top_bar)
        top_layout.setContentsMargins(SPACE["md"], 0, SPACE["md"], 0)
        top_layout.setSpacing(SPACE["sm"])

        # Left: Refresh button + Title
        title_box = QHBoxLayout()
        title_box.setSpacing(SPACE["sm"])

        self.top_refresh_btn = QPushButton()
        self.top_refresh_btn.setFixedSize(28, 28)
        self.top_refresh_btn.setIcon(load_icon("refresh_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.top_refresh_btn.setIconSize(QSize(24, 24))
        self.top_refresh_btn.setCursor(Qt.PointingHandCursor)
        self.top_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 14px;
                border-radius: 14px;
                color: {c['primary']};
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        self.top_refresh_btn.clicked.connect(self.refresh)
        title_box.addWidget(self.top_refresh_btn, alignment=Qt.AlignVCenter)

        self.app_title_label = QLabel("SnipShot")
        self.app_title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: 700;
                color: {c['primary']};
                background-color: transparent;
            }}
        """)
        title_box.addWidget(self.app_title_label, alignment=Qt.AlignVCenter)
        top_layout.addLayout(title_box)

        top_layout.addStretch()

        # Right: Theme toggle button
        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(28, 28)
        self.theme_btn.setIcon(load_icon(theme.is_dark and "dark_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg" or "light_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.theme_btn.setIconSize(QSize(24, 24))
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 14px;
                border-radius: 14px;
                color: {c['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        self.theme_btn.clicked.connect(self._on_theme_toggle_clicked)
        top_layout.addWidget(self.theme_btn, alignment=Qt.AlignVCenter)

        outer_layout.addWidget(self.top_bar)

        # ========== Split Layout for Sidebar and Content ==========
        split_widget = QWidget()
        split_layout = QHBoxLayout(split_widget)
        split_layout.setContentsMargins(0, 0, 0, 0)
        split_layout.setSpacing(0)

        # ========== Sidebar Navigation Drawer ==========
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)

        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        sidebar_layout.setSpacing(SPACE["sm"])

        self.nav_title = QLabel("NAVIGATION")
        sidebar_layout.addWidget(self.nav_title)

        self.nav_new_folder = QPushButton("New Folder")
        self.nav_new_folder.setIcon(load_icon("add_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_new_folder.setIconSize(QSize(24, 24))
        self.nav_new_folder.setCursor(Qt.PointingHandCursor)
        self.nav_new_folder.clicked.connect(self._on_new_folder)
        sidebar_layout.addWidget(self.nav_new_folder)

        self.nav_new_snip = QPushButton("Snip Translate")
        self.nav_new_snip.setIcon(load_icon("content_cut_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_new_snip.setIconSize(QSize(24, 24))
        self.nav_new_snip.setCursor(Qt.PointingHandCursor)
        self.nav_new_snip.clicked.connect(self._on_snip)
        sidebar_layout.addWidget(self.nav_new_snip)

        self.nav_translate = QPushButton("Translate via Upload")
        self.nav_translate.setIcon(load_icon("translate_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_translate.setIconSize(QSize(24, 24))
        self.nav_translate.setCursor(Qt.PointingHandCursor)
        self.nav_translate.clicked.connect(self._on_upload)
        sidebar_layout.addWidget(self.nav_translate)

        self.nav_all = QPushButton("All Files")
        self.nav_all.setIcon(load_icon("allfiles_copy_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_all.setIconSize(QSize(24, 24))
        self.nav_all.setCursor(Qt.PointingHandCursor)
        self.nav_all.clicked.connect(self._on_nav_all)
        sidebar_layout.addWidget(self.nav_all)

        self.nav_recent = QPushButton("Recent")
        self.nav_recent.setIcon(load_icon("recents_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_recent.setIconSize(QSize(24, 24))
        self.nav_recent.setCursor(Qt.PointingHandCursor)
        self.nav_recent.clicked.connect(self._on_nav_recent)
        sidebar_layout.addWidget(self.nav_recent)

        sidebar_layout.addStretch()

        # Settings
        self.nav_settings = QPushButton("Settings")
        self.nav_settings.setIcon(load_icon("settings_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_settings.setIconSize(QSize(24, 24))
        self.nav_settings.setCursor(Qt.PointingHandCursor)
        self.nav_settings.clicked.connect(self._on_nav_settings)
        sidebar_layout.addWidget(self.nav_settings)

        # User Info + Logout
        self.user_frame = QFrame()
        user_layout = QVBoxLayout(self.user_frame)
        user_layout.setContentsMargins(0, SPACE["sm"], 0, 0)
        user_layout.setSpacing(SPACE["xs"])

        self.user_label = QLabel("Loading...")
        user_layout.addWidget(self.user_label)

        self.logout_btn = QPushButton("Sign Out")
        self.logout_btn.setIcon(load_icon("logout_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.logout_btn.setIconSize(QSize(24, 24))
        self.logout_btn.setCursor(Qt.PointingHandCursor)
        self.logout_btn.clicked.connect(self._on_logout)
        user_layout.addWidget(self.logout_btn)
        sidebar_layout.addWidget(self.user_frame)

        split_layout.addWidget(self.sidebar)

        # ========== Content Area ==========
        self.content_frame = QFrame()
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Page Header
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setFixedHeight(64)
        self.header.setStyleSheet(f"""
            QFrame#header {{
                background-color: {c['bg']};
                border-bottom: 1px solid {c['border']};
            }}
        """)

        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(SPACE["lg"], SPACE["sm"], SPACE["lg"], SPACE["sm"])

        title_layout = QVBoxLayout()
        title_layout.setSpacing(2)
        title_layout.setContentsMargins(0, 0, 0, 0)

        self.header_title = QLabel("My Files")
        title_layout.addWidget(self.header_title)

        self.header_subtitle = QLabel("Root / All Files")
        title_layout.addWidget(self.header_subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Search box in the header
        self.search_container = QFrame()
        self.search_container.setFixedWidth(220)
        search_layout = QHBoxLayout(self.search_container)
        search_layout.setContentsMargins(SPACE["sm"], 0, SPACE["sm"], 0)
        search_layout.setSpacing(SPACE["xs"])

        self.search_icon = QLabel()
        self.search_icon.setStyleSheet("background-color: transparent;")
        search_layout.addWidget(self.search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search files...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                padding: 4px 0;
                font-size: 12px;
            }
        """)
        self.search_input.textChanged.connect(self._on_search_changed)
        search_layout.addWidget(self.search_input)

        header_layout.addWidget(self.search_container)

        content_layout.addWidget(self.header)

        # Scrollable content
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {c['bg']}; }}")

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

        split_layout.addWidget(self.content_frame)
        outer_layout.addWidget(split_widget)

        # Keep dummy controls for compatibility
        self.new_folder_btn = QPushButton()
        self.new_folder_btn.hide()
        self.refresh_btn = QPushButton()
        self.refresh_btn.hide()

        # Create floating Trash Drop Zone
        self.trash_drop_zone = TrashDropZone(self)
        self.trash_drop_zone.show()

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
        self._set_active_nav(self.active_nav)
        self.user_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['caption']['size']}px; "
            "background-color: transparent; padding-left: 8px;"
        )
        self.content_frame.setStyleSheet(f"background-color: {c['bg']};")
        self.header.setStyleSheet(f"""
            QFrame#header {{
                background-color: {c['bg']};
                border-bottom: 1px solid {c['border']};
            }}
        """)

        self.nav_title.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                font-weight: 700;
                color: {c['text_tertiary']};
                letter-spacing: 2px;
                background-color: transparent;
                padding-left: {SPACE['sm']}px;
                margin-top: {SPACE['sm']}px;
                margin-bottom: {SPACE['sm']}px;
            }}
        """)

        self.user_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-top: 1px solid {c['border']};
                padding-top: 8px;
            }}
        """)

        self.logout_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['error']};
                border: none;
                padding: {SPACE['sm']}px {SPACE['sm']}px;
                font-size: 12px;
                text-align: left;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                border-radius: 8px;
            }}
        """)

        self.header_title.setStyleSheet(f"""
            QLabel {{
                font-size: 20px;
                font-weight: 700;
                color: {c['text']};
                background-color: transparent;
            }}
        """)

        self.header_subtitle.setStyleSheet(f"""
            QLabel {{
                font-size: 11px;
                color: {c['text_tertiary']};
                letter-spacing: 0.5px;
                background-color: transparent;
            }}
        """)

        self.top_refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 14px;
                border-radius: 14px;
                color: {c['primary']};
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)

        self.search_container.setStyleSheet(f"""
            QFrame {{
                background-color: {c['hover']};
                border: none;
                border-radius: 8px;
            }}
        """)
        search_pixmap = load_icon("search_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg").pixmap(16, 16)
        self.search_icon.setPixmap(search_pixmap)

    def _on_theme_toggle_clicked(self):
        theme.toggle()
        self.theme_btn.setIcon(load_icon(theme.is_dark and "dark_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg" or "light_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))

    def _on_theme_changed(self, _mode=None):
        """Handle live theme change."""
        self._apply_styles()
        c = theme.c
        self.top_bar.setStyleSheet(f"""
            QFrame#topBar {{
                background-color: {c['surface_alt']};
                border-bottom: 1px solid {c['border']};
            }}
        """)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                font-size: 14px;
                border-radius: 14px;
                color: {c['text_secondary']};
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        self.theme_btn.setText("")
        self.theme_btn.setIcon(load_icon(theme.is_dark and "dark_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg" or "light_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.app_title_label.setStyleSheet(f"""
            QLabel {{
                font-size: 18px;
                font-weight: 700;
                color: {c['primary']};
                background-color: transparent;
            }}
        """)
        # Reload all navigation icons for theme change
        self.top_refresh_btn.setIcon(load_icon("refresh_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_new_folder.setIcon(load_icon("add_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_new_snip.setIcon(load_icon("content_cut_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_translate.setIcon(load_icon("translate_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_all.setIcon(load_icon("allfiles_copy_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_recent.setIcon(load_icon("recents_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.nav_settings.setIcon(load_icon("settings_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.logout_btn.setIcon(load_icon("logout_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        
        # Re-render active view to recreate/style all dynamic controls with the new theme
        self._restore_current_view()

    def _nav_button_style(self, active: bool) -> str:
        c = theme.c
        if active:
            return f"""
                QPushButton {{
                    background-color: {c['primary_light']};
                    color: {c['text']};
                    border: none;
                    border-left: 4px solid {c['primary']};
                    border-radius: 8px;
                    padding: 8px 12px;
                    font-size: {FONT['body']['size']}px;
                    font-weight: 600;
                    text-align: left;
                }}
            """
        return f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_secondary']};
                border: none;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: {FONT['body']['size']}px;
                text-align: left;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
                color: {c['text']};
            }}
        """

    def _set_active_nav(self, active: str):
        self.active_nav = active
        self.nav_new_folder.setStyleSheet(self._nav_button_style(False))
        self.nav_new_snip.setStyleSheet(self._nav_button_style(False))
        self.nav_translate.setStyleSheet(self._nav_button_style(False))
        self.nav_all.setStyleSheet(self._nav_button_style(active == "all"))
        self.nav_recent.setStyleSheet(self._nav_button_style(active == "recent"))
        self.nav_settings.setStyleSheet(self._nav_button_style(active == "settings"))

    # ── Data loading ───────────────────────────────────────────────────
    def load_user_info(self):
        if api_client.user:
            email = getattr(api_client.user, "email", "Unknown")
            profile_icon = load_icon("account_circle_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg").pixmap(12, 12)
            if profile_icon.isNull():
                self.user_label.setText(f"{email}")
            else:
                # Use text-only since QLabel with icon is complex; just show email
                self.user_label.setText(f"{email}")

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

    def _reconcile_folder_counts(self):
        """Recompute folder image counts from the local image cache."""
        counts = {}
        for img in self._cached_images:
            fid = img.get("folder_id")
            if fid is not None:
                counts[fid] = counts.get(fid, 0) + 1
        for folder in self._cached_folders:
            folder["image_count"] = counts.get(folder["id"], 0)

    def _clear_content(self):
        def clear_layout(layout):
            if layout is None:
                return
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                elif item.layout():
                    clear_layout(item.layout())
            layout.deleteLater()

        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                clear_layout(item.layout())

    def _load_all_files_async(self):
        self._start_cache_load()

    def _start_cache_load(self):
        self._cancel_worker("cache_loader_worker")
        self._show_loading_indicator("Loading your library...")
        
        worker = CacheLoaderWorker(self.api_client)
        worker.finished.connect(self._on_data_loaded)
        worker.error.connect(self._on_cache_error)
        worker.progress.connect(self._on_cache_progress)
        self.cache_loader_worker = worker
        worker.start()

    def _show_loading_indicator(self, text: str):
        self._clear_content()
        self.loading_label = QLabel(text)
        self.loading_label.setAlignment(Qt.AlignCenter)
        c = theme.c
        self.loading_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; "
            f"padding: {SPACE['xxl']}px; background-color: transparent;"
        )
        self.content_layout.addWidget(self.loading_label)

    def _on_cache_progress(self, count: int):
        if hasattr(self, "loading_label") and self.loading_label:
            if count >= CacheLoaderWorker.SOFT_CAP:
                self.loading_label.setText(f"Loading… {count} items (Limit reached. Use search to find others.)")
            else:
                self.loading_label.setText(f"Loading… {count} items")

    def _on_cache_error(self, msg: str):
        self._clear_content()
        error_container = QWidget()
        err_layout = QVBoxLayout(error_container)
        err_layout.setAlignment(Qt.AlignCenter)
        err_layout.setSpacing(SPACE["sm"])

        error_label = QLabel(f"❌ Could not load library: {msg}")
        error_label.setStyleSheet(
            f"color: {theme.c['error']}; font-size: {FONT['body']['size']}px; "
            "background-color: transparent;"
        )
        error_label.setAlignment(Qt.AlignCenter)
        err_layout.addWidget(error_label)

        retry_btn = StyledButton("Retry", variant="primary")
        retry_btn.clicked.connect(self._start_cache_load)
        err_layout.addWidget(retry_btn, alignment=Qt.AlignCenter)

        self.content_layout.addWidget(error_container)

    def _on_data_loaded(self, folders, images):
        self._cached_folders = folders
        self._cached_images = images
        self._render_root_view()

    def _render_root_view(self):
        self._current_view = "root"
        self.current_folder_id = None
        self.current_folder_name = None
        self._current_folder_id = None
        self._current_folder_name = ""
        self.header_title.setText("My Files")
        if len(self._cached_images) >= CacheLoaderWorker.SOFT_CAP:
            self.header_subtitle.setText("Root / All Files (Notice: Showing first 10,000 items. Use search to find others.)")
        else:
            self.header_subtitle.setText("Root / All Files")
        self._set_active_nav("all")
        self._clear_content()

        c = theme.c
        folders = self._cached_folders
        images = self._cached_images
        unfiled_images = [img for img in images if img.get("folder_id") is None]

        if folders:
            header_row = QHBoxLayout()
            header_row.setSpacing(SPACE["xs"])
            dot = QLabel("•")
            dot.setStyleSheet(f"color: {c['primary']}; font-size: 20px; font-weight: bold; background-color: transparent;")
            lbl = QLabel("Folders")
            lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {c['text_secondary']}; background-color: transparent; text-transform: uppercase;")
            header_row.addWidget(dot)
            header_row.addWidget(lbl)
            header_row.addStretch()
            self.content_layout.addLayout(header_row)

            folder_grid = QWidget()
            folder_grid_layout = FlowLayout(folder_grid, spacing=SPACE["md"])

            for folder in folders:
                card = FolderCard(folder)
                card.clicked.connect(self._on_folder_clicked)
                card.delete_requested.connect(self._on_delete_folder)
                card.rename_requested.connect(self._on_rename_folder)
                card.image_dropped.connect(self._on_image_dropped)
                folder_grid_layout.addWidget(card)

            self.content_layout.addWidget(folder_grid)

        if unfiled_images:
            self.content_layout.addSpacing(SPACE["md"])

            header_row = QHBoxLayout()
            header_row.setSpacing(SPACE["xs"])
            dot = QLabel("•")
            dot.setStyleSheet(f"color: {c['text_secondary']}; font-size: 20px; font-weight: bold; background-color: transparent;")
            lbl = QLabel("Unfiled Images")
            lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {c['text_secondary']}; background-color: transparent; text-transform: uppercase;")
            header_row.addWidget(dot)
            header_row.addWidget(lbl)
            header_row.addStretch()
            self.content_layout.addLayout(header_row)

            self._add_image_grid(unfiled_images)

        if not folders and not unfiled_images:
            self._show_empty_state(
                "No files yet", "Capture a screenshot to get started!"
            )
        self.content_layout.addStretch()

    def _render_folder_view(self, folder_id: int, folder_name: str):
        self._current_view = "folder"
        self.current_folder_id = folder_id
        self.current_folder_name = folder_name
        self._current_folder_id = folder_id
        self._current_folder_name = folder_name
        self._set_active_nav("all")
        self.header_title.setText(folder_name)
        self.header_subtitle.setText(f"Root / Folders / {folder_name}")
        self._clear_content()

        back_btn = StyledButton("", variant="ghost")
        back_btn.setIcon(load_icon("keyboard_backspace_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        back_btn.setIconSize(QSize(24, 24))
        back_btn.setToolTip("Back to My Files")
        back_btn.setMaximumWidth(50)
        back_btn.clicked.connect(self._on_nav_all)
        self.content_layout.addWidget(back_btn, alignment=Qt.AlignLeft)

        folder_images = [img for img in self._cached_images if img.get("folder_id") == folder_id]

        if folder_images:
            self._add_image_grid(folder_images)
        else:
            self._show_empty_state(
                "This folder is empty",
                "Translated images saved to this folder will appear here.",
            )
        self.content_layout.addStretch()

    def _render_recent_view(self):
        self._current_view = "recent"
        self.current_folder_id = None
        self.current_folder_name = None
        self._current_folder_id = None
        self._current_folder_name = ""
        self._set_active_nav("recent")
        self.header_title.setText("Recent")
        self.header_subtitle.setText("Root / Recent Translations")
        self._clear_content()

        def get_date(img):
            return img.get("created_at") or ""
        
        sorted_images = sorted(self._cached_images, key=get_date, reverse=True)
        recent_images = sorted_images[:20]

        if recent_images:
            self._add_image_grid(recent_images)
        else:
            self._show_empty_state(
                "No recent files", "Your recent translations will appear here."
            )
        self.content_layout.addStretch()

    def _restore_current_view(self):
        if self._current_view == "root":
            self._render_root_view()
        elif self._current_view == "folder":
            self._render_folder_view(self._current_folder_id, self._current_folder_name)
        elif self._current_view == "recent":
            self._render_recent_view()
        elif self._current_view == "settings":
            self._on_nav_settings()

    def _load_folder(self, folder_id: int, folder_name: str):
        self._current_view = "folder"
        self._current_folder_id = folder_id
        self._current_folder_name = folder_name
        self.current_folder_id = folder_id
        self.current_folder_name = folder_name
        
        # Render immediately from cache
        self._render_folder_view(folder_id, folder_name)

        # Cancel any active update worker
        self._cancel_worker("cache_update_worker")

        # Start silent background update to sync cache
        worker = CacheLoaderWorker(self.api_client)
        def on_update_finished(folders, images):
            self._cached_folders = folders
            self._cached_images = images
            if self._current_view == "folder" and self._current_folder_id == folder_id:
                self._render_folder_view(folder_id, folder_name)
        
        worker.finished.connect(on_update_finished)
        self.cache_update_worker = worker
        worker.start()


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

        icon_label = QLabel()
        icon_pixmap = load_icon("folder_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg").pixmap(64, 64)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setStyleSheet(
            f"background-color: transparent;"
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
        error_label = QLabel(f"❌ {message}")
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
        self._current_view = "recent"
        self.current_folder_id = None
        self.current_folder_name = None
        self._current_folder_id = None
        self._current_folder_name = ""
        
        # Render immediately from cache
        self._render_recent_view()

        # Cancel active update
        self._cancel_worker("cache_update_worker")

        # Start background sync
        worker = CacheLoaderWorker(self.api_client)
        def on_update_finished(folders, images):
            self._cached_folders = folders
            self._cached_images = images
            if self._current_view == "recent":
                self._render_recent_view()
        worker.finished.connect(on_update_finished)
        self.cache_update_worker = worker
        worker.start()

    def _on_nav_settings(self):
        self._set_active_nav("settings")
        self._current_view = "settings"
        self.current_folder_id = None
        self.current_folder_name = None
        self.header_title.setText("Settings")
        self.header_subtitle.setText("Application Preferences")
        self._clear_content()
        self._render_settings_content()
        self.content_layout.addStretch()

    def _on_search_changed(self, text: str):
        self.search_timer.stop()
        self._cancel_worker("search_worker")
        if not text.strip():
            self._restore_current_view()   # warm cache, zero network
        else:
            self.search_timer.start()

    def _trigger_search(self):
        query = self.search_input.text().strip()
        if not query:
            return
        self._cancel_worker("search_worker")
        
        # Show searching indicator
        self._clear_content()
        c = theme.c
        searching_label = QLabel("Searching...")
        searching_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; "
            f"padding: {SPACE['xxl']}px; background-color: transparent;"
        )
        searching_label.setAlignment(Qt.AlignCenter)
        self.content_layout.addWidget(searching_label)

        # Start search worker
        worker = InMemorySearchWorker(query, self._cached_folders, self._cached_images)
        worker.finished.connect(self._on_search_results)
        worker.error.connect(self._on_search_error)
        self.search_worker = worker
        worker.start()

    def _on_search_results(self, folders, images):
        self._clear_content()
        c = theme.c
        query = self.search_input.text()

        if folders:
            header_row = QHBoxLayout()
            header_row.setSpacing(SPACE["xs"])
            dot = QLabel("•")
            dot.setStyleSheet(f"color: {c['primary']}; font-size: 20px; font-weight: bold; background-color: transparent;")
            lbl = QLabel(f"Folders Matching \"{query}\"")
            lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {c['text_secondary']}; background-color: transparent;")
            header_row.addWidget(dot)
            header_row.addWidget(lbl)
            header_row.addStretch()
            self.content_layout.addLayout(header_row)

            folder_grid = QWidget()
            folder_grid_layout = FlowLayout(folder_grid, spacing=SPACE["md"])
            for folder in folders:
                card = FolderCard(folder)
                card.clicked.connect(self._on_folder_clicked)
                card.delete_requested.connect(self._on_delete_folder)
                card.rename_requested.connect(self._on_rename_folder)
                card.image_dropped.connect(self._on_image_dropped)
                folder_grid_layout.addWidget(card)
            self.content_layout.addWidget(folder_grid)

        if images:
            if folders:
                self.content_layout.addSpacing(SPACE["lg"])
            header_row = QHBoxLayout()
            header_row.setSpacing(SPACE["xs"])
            dot = QLabel("•")
            dot.setStyleSheet(f"color: {c['primary']}; font-size: 20px; font-weight: bold; background-color: transparent;")
            lbl = QLabel(f"Images Matching \"{query}\"")
            lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {c['text_secondary']}; background-color: transparent;")
            header_row.addWidget(dot)
            header_row.addWidget(lbl)
            header_row.addStretch()
            self.content_layout.addLayout(header_row)

            self._add_image_grid(images)

        if not folders and not images:
            self._show_empty_state(
                "No search results", f"No folders or images matched '{query}'."
            )
        self.content_layout.addStretch()

    def _on_search_error(self, msg: str):
        self._show_error(f"Search error: {msg}")
        self._restore_current_view()


    # ------------------------------------------------------------------ #
    # Settings rendering  (redesigned)
    # ------------------------------------------------------------------ #

    def _make_section_card(self) -> tuple:
        """
        Returns a transparent spacer frame + its VBoxLayout (flat, no border).
        """
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: transparent; border: none; }")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["xs"])
        return card, layout

    def _section_header_label(self, icon: str, text: str) -> QLabel:
        """Plain bold section title – no border, no background."""
        c = theme.c
        label = QLabel(text)
        label.setStyleSheet(
            f"font-size: {FONT['heading']['size']}px; "
            f"font-weight: {FONT['heading']['weight']}; "
            f"color: {c['text']}; "
            "background-color: transparent; "
            "border: none;"
        )
        return label

    def _hint_label(self, text: str) -> QLabel:
        """Secondary hint text – no border, no background."""
        label = QLabel(text)
        label.setWordWrap(True)
        c = theme.c
        label.setStyleSheet(
            f"color: {c['text_secondary']}; "
            f"font-size: {FONT['caption']['size']}px; "
            "background-color: transparent; "
            "border: none;"
        )
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
        # page_title = QLabel("Settings")
        # page_title.setStyleSheet(
        #     f"font-size: {FONT['display']['size']}px; "
        #     f"font-weight: {FONT['display']['weight']}; "
        #     f"color: {c['text']}; "
        #     "background-color: transparent; "
        #     "border: none;"
        # )
        # self.content_layout.addWidget(page_title)
        # self.content_layout.addSpacing(SPACE["md"])

        # ── Appearance ────────────────────────────────────────────────
        self.content_layout.addWidget(self._section_header_label("", "Appearance"))
        self.content_layout.addSpacing(SPACE["sm"])

        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(SPACE["sm"])

        self.light_btn = QPushButton("Light")
        self.light_btn.setIcon(load_icon("light_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.light_btn.setIconSize(QSize(24, 24))
        self.light_btn.setCursor(Qt.PointingHandCursor)
        self.light_btn.setStyleSheet(self._theme_pill_style(not theme.is_dark))
        self.light_btn.clicked.connect(lambda: theme.set_mode("light"))

        self.dark_btn = QPushButton("Dark")
        self.dark_btn.setIcon(load_icon("dark_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.dark_btn.setIconSize(QSize(24, 24))
        self.dark_btn.setCursor(Qt.PointingHandCursor)
        self.dark_btn.setStyleSheet(self._theme_pill_style(theme.is_dark))
        self.dark_btn.clicked.connect(lambda: theme.set_mode("dark"))

        toggle_row.addWidget(self.light_btn)
        toggle_row.addWidget(self.dark_btn)
        toggle_row.addStretch()
        self.content_layout.addLayout(toggle_row)
        self.content_layout.addSpacing(SPACE["lg"])

        # ── Capture Shortcut ──────────────────────────────────────────
        self.content_layout.addWidget(self._section_header_label("", "Capture Shortcut"))
        self.content_layout.addSpacing(SPACE["xs"])

        sc_label = QLabel("Keyboard Shortcut")
        sc_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; "
            "background-color: transparent; border: none;"
        )
        self.content_layout.addWidget(sc_label)
        self.content_layout.addSpacing(SPACE["sm"])

        sc_row = QHBoxLayout()
        sc_row.setSpacing(SPACE["sm"])

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
                color: {c['text']};
                min-width: 80px;
                letter-spacing: 1px;
            }}
        """)
        sc_row.addWidget(self.shortcut_display)

        self.shortcut_btn = _ShortcutButton("Change Shortcut")
        self.shortcut_btn.shortcut_captured.connect(self._on_shortcut_captured)
        sc_row.addWidget(self.shortcut_btn)
        sc_row.addStretch()
        self.content_layout.addLayout(sc_row)
        self.content_layout.addSpacing(SPACE["lg"])

        # ── Translation Settings ───────────────────────────────────────
        self.content_layout.addWidget(self._section_header_label("", "Translation Settings"))
        self.content_layout.addSpacing(SPACE["sm"])

        lang_label = QLabel("Default Target Language")
        lang_label.setStyleSheet(
            f"font-weight: 600; color: {c['text']}; "
            f"font-size: {FONT['label']['size']}px; "
            "background-color: transparent; border: none;"
        )
        self.content_layout.addWidget(lang_label)
        self.content_layout.addSpacing(SPACE["xs"])

        self.language_combo = QComboBox()
        self.language_combo.setStyleSheet(self._settings_input_style())
        for label, code in self.language_options:
            self.language_combo.addItem(f"{label} ({code})", code)
        current_index = self.language_combo.findData(self.target_language)
        if current_index >= 0:
            self.language_combo.setCurrentIndex(current_index)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        self.content_layout.addWidget(self.language_combo)
        self.content_layout.addSpacing(SPACE["lg"])

        # ── Advanced Parameters ───────────────────────────────────────
        self.content_layout.addWidget(self._section_header_label("", "Advanced Parameters"))

        # ── Detection Size ──
        self.content_layout.addSpacing(SPACE["sm"])
        det_row = QHBoxLayout()
        det_lbl = QLabel("Detection Size")
        det_lbl.setStyleSheet(
            f"font-weight: 600; color: {c['text']}; "
            f"font-size: {FONT['label']['size']}px; "
            "background-color: transparent; border: none;"
        )
        det_row.addWidget(det_lbl)
        det_row.addStretch()
        
        self.det_save_btn = StyledButton("✓", variant="primary")
        self.det_save_btn.clicked.connect(self._save_detection_size)
        self.det_save_btn.hide()
        det_row.addWidget(self.det_save_btn)
        
        self.det_cancel_btn = StyledButton("✕", variant="secondary")
        self.det_cancel_btn.clicked.connect(self._cancel_detection_size)
        self.det_cancel_btn.hide()
        det_row.addWidget(self.det_cancel_btn)
        
        self.detection_size_value = QLabel(f"{self.detection_size} px")
        self.detection_size_value.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['label']['size']}px; "
            "background-color: transparent; border: none;"
        )
        det_row.addWidget(self.detection_size_value)
        self.content_layout.addLayout(det_row)

        self.detection_size_slider = QSlider(Qt.Horizontal)
        self.detection_size_slider.setRange(DETECTION_SIZE_MIN, DETECTION_SIZE_MAX)
        self.detection_size_slider.setSingleStep(DETECTION_SIZE_STEP)
        self.detection_size_slider.setValue(self.detection_size)
        self.detection_size_slider.setStyleSheet(self._styled_slider())
        self.detection_size_slider.valueChanged.connect(self._on_detection_size_changed)
        self.content_layout.addWidget(self.detection_size_slider)
        self.content_layout.addWidget(self._hint_label(
            "Controls resolution for text detection. Higher values improve quality but are slower."
        ))

        # ── Box Threshold ──
        self.content_layout.addSpacing(SPACE["sm"])
        box_row = QHBoxLayout()
        box_lbl = QLabel("Box Threshold")
        box_lbl.setStyleSheet(
            f"font-weight: 600; color: {c['text']}; "
            f"font-size: {FONT['label']['size']}px; "
            "background-color: transparent; border: none;"
        )
        box_row.addWidget(box_lbl)
        box_row.addStretch()
        
        self.box_save_btn = StyledButton("✓", variant="primary")
        self.box_save_btn.clicked.connect(self._save_box_threshold)
        self.box_save_btn.hide()
        box_row.addWidget(self.box_save_btn)
        
        self.box_cancel_btn = StyledButton("✕", variant="secondary")
        self.box_cancel_btn.clicked.connect(self._cancel_box_threshold)
        self.box_cancel_btn.hide()
        box_row.addWidget(self.box_cancel_btn)
        
        self.box_threshold_value = QLabel(f"{self.box_threshold:.2f}")
        self.box_threshold_value.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['label']['size']}px; "
            "background-color: transparent; border: none;"
        )
        box_row.addWidget(self.box_threshold_value)
        self.content_layout.addLayout(box_row)

        self.box_threshold_slider = QSlider(Qt.Horizontal)
        self.box_threshold_slider.setRange(
            int(BOX_THRESHOLD_MIN * 100), int(BOX_THRESHOLD_MAX * 100)
        )
        self.box_threshold_slider.setSingleStep(5)
        self.box_threshold_slider.setValue(int(self.box_threshold * 100))
        self.box_threshold_slider.setStyleSheet(self._styled_slider())
        self.box_threshold_slider.valueChanged.connect(self._on_box_threshold_changed)
        self.content_layout.addWidget(self.box_threshold_slider)
        self.content_layout.addWidget(self._hint_label(
            "Minimum confidence for translating a detected region."
        ))

        # ── Inpainting Size ──
        self.content_layout.addSpacing(SPACE["sm"])
        inp_row = QHBoxLayout()
        inp_lbl = QLabel("Inpainting Size")
        inp_lbl.setStyleSheet(
            f"font-weight: 600; color: {c['text']}; "
            f"font-size: {FONT['label']['size']}px; "
            "background-color: transparent; border: none;"
        )
        inp_row.addWidget(inp_lbl)
        inp_row.addStretch()
        
        self.inp_save_btn = StyledButton("✓", variant="primary")
        self.inp_save_btn.clicked.connect(self._save_inpainting_size)
        self.inp_save_btn.hide()
        inp_row.addWidget(self.inp_save_btn)
        
        self.inp_cancel_btn = StyledButton("✕", variant="secondary")
        self.inp_cancel_btn.clicked.connect(self._cancel_inpainting_size)
        self.inp_cancel_btn.hide()
        inp_row.addWidget(self.inp_cancel_btn)
        
        self.inpainting_size_value = QLabel(f"{self.inpainting_size} px")
        self.inpainting_size_value.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['label']['size']}px; "
            "background-color: transparent; border: none;"
        )
        inp_row.addWidget(self.inpainting_size_value)
        self.content_layout.addLayout(inp_row)

        self.inpainting_size_slider = QSlider(Qt.Horizontal)
        self.inpainting_size_slider.setRange(INPAINTING_SIZE_MIN, INPAINTING_SIZE_MAX)
        self.inpainting_size_slider.setSingleStep(INPAINTING_SIZE_STEP)
        self.inpainting_size_slider.setValue(self.inpainting_size)
        self.inpainting_size_slider.setStyleSheet(self._styled_slider())
        self.inpainting_size_slider.valueChanged.connect(self._on_inpainting_size_changed)
        self.content_layout.addWidget(self.inpainting_size_slider)
        self.content_layout.addWidget(self._hint_label(
            "Resolution for background inpainting."
        ))
        self.content_layout.addSpacing(SPACE["lg"])

        # ── Inpainter Model ───────────────────────────────────────────
        inp_model_row = QHBoxLayout()
        inp_model_lbl = QLabel("Inpainter Model")
        inp_model_lbl.setStyleSheet(
            f"font-weight: 600; color: {c['text']}; "
            f"font-size: {FONT['label']['size']}px; "
            "background-color: transparent; border: none;"
        )
        inp_model_row.addWidget(inp_model_lbl)
        inp_model_row.addSpacing(SPACE["md"])
        self.inpainter_combo = QComboBox()
        self.inpainter_combo.setStyleSheet(self._settings_input_style())
        self.inpainter_combo.addItem("LAMA Large (recommended)", "lama_large")
        self.inpainter_combo.addItem("None (skip inpainting)", "none")
        idx = self.inpainter_combo.findData(self.inpainter)
        if idx >= 0:
            self.inpainter_combo.setCurrentIndex(idx)
        self.inpainter_combo.currentIndexChanged.connect(self._on_inpainter_changed)
        inp_model_row.addWidget(self.inpainter_combo)
        inp_model_row.addStretch()
        self.content_layout.addLayout(inp_model_row)
        self.content_layout.addWidget(self._hint_label(
            "Select the AI model for filling in backgrounds."
        ))

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
        if hasattr(self, "detection_size_value"):
            self.detection_size_value.setText(f"{value} px")
            if hasattr(self, "det_save_btn"):
                if value != self.detection_size:
                    self.det_save_btn.show()
                    self.det_cancel_btn.show()
                else:
                    self.det_save_btn.hide()
                    self.det_cancel_btn.hide()

    def _save_detection_size(self):
        self.detection_size = self.detection_size_slider.value()
        self.det_save_btn.hide()
        self.det_cancel_btn.hide()

    def _cancel_detection_size(self):
        self.detection_size_slider.setValue(self.detection_size)

    def _on_box_threshold_changed(self, value: int):
        if hasattr(self, "box_threshold_value"):
            self.box_threshold_value.setText(f"{value / 100:.2f}")
            if hasattr(self, "box_save_btn"):
                if round(value / 100, 2) != self.box_threshold:
                    self.box_save_btn.show()
                    self.box_cancel_btn.show()
                else:
                    self.box_save_btn.hide()
                    self.box_cancel_btn.hide()

    def _save_box_threshold(self):
        self.box_threshold = round(self.box_threshold_slider.value() / 100, 2)
        self.box_save_btn.hide()
        self.box_cancel_btn.hide()

    def _cancel_box_threshold(self):
        self.box_threshold_slider.setValue(int(self.box_threshold * 100))

    def _on_inpainting_size_changed(self, value: int):
        if hasattr(self, "inpainting_size_value"):
            self.inpainting_size_value.setText(f"{value} px")
            if hasattr(self, "inp_save_btn"):
                if value != self.inpainting_size:
                    self.inp_save_btn.show()
                    self.inp_cancel_btn.show()
                else:
                    self.inp_save_btn.hide()
                    self.inp_cancel_btn.hide()

    def _save_inpainting_size(self):
        self.inpainting_size = self.inpainting_size_slider.value()
        self.inp_save_btn.hide()
        self.inp_cancel_btn.hide()

    def _cancel_inpainting_size(self):
        self.inpainting_size_slider.setValue(self.inpainting_size)

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
        import time
        current_time = time.time()
        # If the signed URL was generated more than 50 minutes (3000 seconds) ago,
        # or if there is no signed URL, refresh it.
        if current_time - image_data.get("_signed_at", 0) > 3000 or not image_data.get("public_url"):
            res = self.api_client.get_image(image_data["id"])
            if res.get("success") and res.get("data"):
                image_data.update(res.get("data"))

        dialog = ImagePreviewDialog(image_data, self)
        dialog.exec_()

    def _on_new_folder(self):
        dialog = CreateFolderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, description = dialog.get_values()
            if name:
                result = api_client.create_folder(name, description)
                if result.get("success"):
                    new_folder = result.get("data")
                    if new_folder:
                        new_folder["image_count"] = 0
                        self._cached_folders.insert(0, new_folder)
                        self._restore_current_view()
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
        delete_images = False
        if clicked == keep_btn:
            delete_images = False
        elif clicked == delete_all_btn:
            delete_images = True
        else:
            return

        result = api_client.delete_folder(folder_id, delete_images=delete_images)

        if result.get("success"):
            # Update local cache
            self._cached_folders = [f for f in self._cached_folders if f["id"] != folder_id]
            if delete_images:
                # Remove all images inside this folder
                self._cached_images = [img for img in self._cached_images if img.get("folder_id") != folder_id]
            else:
                # Set folder_id to None for all images inside this folder
                for img in self._cached_images:
                    if img.get("folder_id") == folder_id:
                        img["folder_id"] = None
            
            # If current view was the deleted folder, navigate back to root/all
            if self._current_view == "folder" and self._current_folder_id == folder_id:
                self._on_nav_all()
            else:
                self._restore_current_view()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete folder")

    def _on_rename_folder(self, folder_id: int, current_name: str):
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "New name:", text=current_name
        )
        if ok and new_name and new_name != current_name:
            result = api_client.update_folder(folder_id, name=new_name)
            if result.get("success"):
                # Update local cache
                for f in self._cached_folders:
                    if f["id"] == folder_id:
                        f["name"] = new_name
                        break
                # If currently viewing this folder, update title
                if self._current_view == "folder" and self._current_folder_id == folder_id:
                    self._current_folder_name = new_name
                    self.current_folder_name = new_name
                self._restore_current_view()
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
            if result.get("success"):
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete image")

    def _on_rename_image(self, image_data: dict):
        current_name = image_data.get("filename", "")
        new_name, ok = QInputDialog.getText(
            self, "Rename Image", "New filename:", text=current_name
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            result = api_client.update_image(image_data["id"], filename=new_name.strip())
            if result.get("success"):
                self.refresh()
            else:
                QMessageBox.warning(self, "Error", result.get("error", "Failed to rename image"))


    def _on_move_image(self, image_data: dict):
        folders_result = api_client.get_folders()
        if not folders_result.get("success"):
            QMessageBox.warning(self, "Error", "Failed to load folders")
            return

        folders = folders_result.get("data", [])
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
            result = api_client.move_image_to_folder(image_data["id"], folder_id=folder_id)
            if result.get("success"):
                self.refresh()
            else:
                QMessageBox.warning(
                    self, "Error", result.get("error", "Failed to move image")
                )

    def _on_image_dropped(self, folder_id: int, image_id: int):
        if getattr(self, "_is_moving_image", False):
            return
        self._is_moving_image = True

        # Validate that the drop target is a valid folder
        valid_folder = any(f["id"] == folder_id for f in self._cached_folders)
        if not valid_folder:
            self._is_moving_image = False
            return

        # Show busy feedback
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

        try:
            result = self.api_client.move_image_to_folder(image_id, folder_id=folder_id)
            if result.get("success"):
                self.refresh()
            else:
                QMessageBox.warning(
                    self,
                    "Move Failed",
                    result.get("error", "Failed to move the image to the folder.")
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred while moving the image: {str(e)}"
            )
        finally:
            QApplication.restoreOverrideCursor()
            self._is_moving_image = False

    def _delete_image_dropped(self, image_id: int):
        if getattr(self, "_is_deleting_item", False):
            return
        self._is_deleting_item = True
        try:
            self._on_delete_image(image_id)
        finally:
            self._is_deleting_item = False

    def _delete_folder_dropped(self, folder_id: int):
        if getattr(self, "_is_deleting_item", False):
            return
        self._is_deleting_item = True
        try:
            folder_name = "Folder"
            for f in self._cached_folders:
                if f["id"] == folder_id:
                    folder_name = f["name"]
                    break
            self._on_delete_folder(folder_id, folder_name)
        finally:
            self._is_deleting_item = False

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reposition_trash_drop_zone()

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition_trash_drop_zone()

    def _reposition_trash_drop_zone(self):
        if hasattr(self, "trash_drop_zone") and self.trash_drop_zone is not None:
            margin_right = 24
            margin_bottom = 24
            trash_w = self.trash_drop_zone.width()
            trash_h = self.trash_drop_zone.height()
            new_x = self.width() - trash_w - margin_right
            new_y = self.height() - trash_h - margin_bottom
            self.trash_drop_zone.move(new_x, new_y)

    def _on_logout(self):
        api_client.logout()
        self.logout_requested.emit()

    def closeEvent(self, event: QCloseEvent):
        self.search_timer.stop()
        self._cancel_worker("search_worker")
        self._cancel_worker("cache_loader_worker")
        self._cancel_worker("cache_update_worker")
        event.accept()
