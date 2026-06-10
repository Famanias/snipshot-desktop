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

import os
import json

SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QMenu, QAction,
    QInputDialog, QMessageBox, QSizePolicy, QListWidget,
    QListWidgetItem, QStackedWidget, QProgressBar, QDialog,
    QLineEdit, QTextEdit, QDialogButtonBox, QApplication, QComboBox,
    QLayout, QSplitter, QSpinBox, QDoubleSpinBox, QSlider, QToolButton,
    QCheckBox, QRadioButton, QGroupBox,
)
from config_metadata import (
    SETTINGS_METADATA, DEFAULT_SETTINGS, SECTION_LABELS,
    SECTION_DETECTION, SECTION_INPAINTING, SECTION_OCR, SECTION_RENDERING
)
from PyQt5.QtGui import QKeySequence
from typing import Optional, Any, Tuple, Dict
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread, QRect, QPoint
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QFont, QKeySequence, QCloseEvent
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt5.QtCore import QUrl

from api import api_client
from config import (
    TRANSLATION_TARGET_LANG, TRANSLATION_INPAINTER,
    DEFAULT_SHORTCUT_KEY, DEFAULT_CONTINUOUS_SHORTCUT_KEY,
    DEFAULT_CONTINUOUS_SNIP_INTERVAL,
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

    def insertWidget(self, index: int, widget: QWidget):
        self.addChildWidget(widget)
        from PyQt5.QtWidgets import QWidgetItem
        self._items.insert(index, QWidgetItem(widget))
        self.invalidate()

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

    def __init__(self, images: list, current_image: dict, parent=None):
        super().__init__(parent)
        self.images = images
        self.image_data = current_image
        self.setWindowTitle(current_image.get("filename", "Image Preview"))
        self.setMinimumSize(600, 500)
        self.resize(800, 600)
        self.loader = None
        self.request_id = 0
        self.prefetch_workers = {}

        self.current_index = next(
            (i for i, img in enumerate(self.images) if img["id"] == current_image["id"]),
            -1
        )

        self._setup_ui()
        self._update_navigation()
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

        # Navigation controls
        self.nav_layout = QHBoxLayout()
        self.nav_layout.setContentsMargins(0, 0, 0, 0)
        self.nav_layout.setSpacing(SPACE["md"])

        self.prev_btn = StyledButton("< Previous", variant="secondary")
        self.prev_btn.clicked.connect(self._on_prev_clicked)
        self.nav_layout.addWidget(self.prev_btn)

        self.nav_layout.addStretch()

        self.counter_label = QLabel()
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; font-weight: 500; background-color: transparent;"
        )
        self.nav_layout.addWidget(self.counter_label)

        self.nav_layout.addStretch()

        self.next_btn = StyledButton("Next >", variant="secondary")
        self.next_btn.clicked.connect(self._on_next_clicked)
        self.nav_layout.addWidget(self.next_btn)

        layout.addLayout(self.nav_layout)

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
        self.request_id += 1
        req_id = self.request_id

        self.original_pixmap = None

        url = self.image_data.get("public_url")
        if not url:
            self.image_label.setText("No image URL available")
            self.progress.hide()
            return

        if url in self._image_cache:
            self._on_image_loaded(self._image_cache[url], req_id)
            return

        self.progress.show()
        self.image_label.setText("Loading...")

        self.loader = ImageLoaderWorker(url)
        self.loader.finished.connect(lambda data, r_id=req_id: self._on_image_loaded(data, r_id))
        self.loader.error.connect(lambda err, r_id=req_id: self._on_load_error(err, r_id))
        self.loader.start()

    def _on_image_loaded(self, data: bytes, req_id: int):
        if req_id != self.request_id:
            return

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

            # Start prefetching adjacent images on successful load
            self._prefetch_adjacent_images()
        else:
            self.image_label.setText("Failed to decode image")

    def _on_load_error(self, error: str, req_id: int):
        if req_id != self.request_id:
            return

        self.progress.hide()
        self.image_label.setText(f"Failed to load image:\n{error}")
        self.image_label.setStyleSheet(
            f"color: {theme.c['error']}; padding: {SPACE['lg']}px; background-color: transparent;"
        )

    def _on_prev_clicked(self):
        if self.current_index > 0:
            self._navigate_to_image(self.current_index - 1)

    def _on_next_clicked(self):
        if self.current_index < len(self.images) - 1:
            self._navigate_to_image(self.current_index + 1)

    def _navigate_to_image(self, index: int):
        self.current_index = index
        self.image_data = self.images[index]
        self.setWindowTitle(self.image_data.get("filename", "Image Preview"))
        self.filename_label.setText(self.image_data.get("filename", "Unknown"))

        self._refresh_signed_url_if_needed()
        self._update_navigation()
        self._load_image()

    def _update_navigation(self):
        if self.current_index == -1 or not self.images:
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            self.counter_label.setText("")
            return

        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.images) - 1)
        self.counter_label.setText(f"Image {self.current_index + 1} of {len(self.images)}")

    def _refresh_signed_url_if_needed(self):
        import time
        current_time = time.time()
        # If the signed URL was generated more than 50 minutes (3000 seconds) ago,
        # or if there is no signed URL, refresh it.
        if current_time - self.image_data.get("_signed_at", 0) > 3000 or not self.image_data.get("public_url"):
            try:
                parent = self.parent()
                if parent and hasattr(parent, "api_client"):
                    res = parent.api_client.get_image(self.image_data["id"])
                    if res.get("success") and res.get("data"):
                        self.image_data.update(res.get("data"))
                        self.image_data["_signed_at"] = current_time

                        # Also update the parent's image cache in-place
                        if hasattr(parent, "_get_cached_image"):
                            cached_img = parent._get_cached_image(self.image_data["id"])
                            if cached_img:
                                cached_img.update(res.get("data"))
                                cached_img["_signed_at"] = current_time
                    else:
                        print(f"Warning: Failed to refresh signed URL: {res.get('error')}")
            except Exception as e:
                print(f"Error: Exception while retrieving signed URL: {e}")

    def _prefetch_adjacent_images(self):
        for offset in (1, -1):
            target_idx = self.current_index + offset
            if 0 <= target_idx < len(self.images):
                target_img = self.images[target_idx]
                target_url = target_img.get("public_url")
                if target_url and target_url not in self._image_cache and target_url not in self.prefetch_workers:
                    worker = ImageLoaderWorker(target_url)
                    def on_prefetched(data, url=target_url):
                        self._image_cache[url] = data
                        if url in self.prefetch_workers:
                            del self.prefetch_workers[url]

                    def on_prefetch_error(err, url=target_url):
                        if url in self.prefetch_workers:
                            del self.prefetch_workers[url]

                    worker.finished.connect(on_prefetched)
                    worker.error.connect(on_prefetch_error)
                    self.prefetch_workers[target_url] = worker
                    worker.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Left:
            self._on_prev_clicked()
        elif event.key() == Qt.Key_Right:
            self._on_next_clicked()
        elif event.key() == Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)

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
        # Clean up prefetch workers
        for worker in list(self.prefetch_workers.values()):
            if worker.isRunning():
                worker.terminate()
                worker.wait()
        self.prefetch_workers.clear()

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
    move_requested = pyqtSignal(int, str)
    image_dropped = pyqtSignal(int, list)
    folder_dropped = pyqtSignal(int, int)

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
        if event.mimeData().hasFormat("application/x-snipshot-image-ids") or event.mimeData().hasFormat("application/x-snipshot-folder-id"):
            event.acceptProposedAction()
            self.setProperty("dragOver", True)
            self.style().unpolish(self)
            self.style().polish(self)
            self.update()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-snipshot-image-ids") or event.mimeData().hasFormat("application/x-snipshot-folder-id"):
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
        if mime_data.hasFormat("application/x-snipshot-image-ids"):
            json_bytes = mime_data.data("application/x-snipshot-image-ids").data().decode('utf-8')
            try:
                image_ids = json.loads(json_bytes)
                self.image_dropped.emit(self.folder_id, image_ids)
                event.acceptProposedAction()
            except (ValueError, json.JSONDecodeError):
                event.ignore()
        elif mime_data.hasFormat("application/x-snipshot-folder-id"):
            folder_id_str = mime_data.data("application/x-snipshot-folder-id").data().decode('utf-8')
            try:
                source_folder_id = int(folder_id_str)
                if source_folder_id != self.folder_id:
                    self.folder_dropped.emit(self.folder_id, source_folder_id)
                    event.acceptProposedAction()
                else:
                    event.ignore()
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
        from ui.styles import get_main_stylesheet
        menu.setStyleSheet(get_main_stylesheet())
        open_action = menu.addAction("Open")
        open_action.triggered.connect(
            lambda: self.clicked.emit(self.folder_id, self.folder_name)
        )
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(
            lambda: self.rename_requested.emit(self.folder_id, self.folder_name)
        )
        move_action = menu.addAction("Move to...")
        move_action.triggered.connect(
            lambda: self.move_requested.emit(self.folder_id, self.folder_name)
        )
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.folder_id, self.folder_name)
        )
        menu.exec_(pos)


class ImageCard(QFrame):
    """A card widget representing an image"""

    clicked = pyqtSignal(int)
    double_clicked = pyqtSignal(int)
    right_clicked = pyqtSignal(int, QPoint)
    delete_requested = pyqtSignal(int)
    rename_requested = pyqtSignal(int)
    move_requested = pyqtSignal(int)

    def __init__(self, image_data: dict, parent=None):
        super().__init__(parent)
        self.image_data = image_data
        self.image_id = image_data["id"]
        self._selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)
        self._setup_ui()
        theme.theme_changed.connect(self._on_theme_changed)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.setProperty("selected", "true" if selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _setup_ui(self):
        self.setFixedSize(220, 180)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Image preview container
        self.preview_box = QFrame()
        self.preview_box.setObjectName("preview_box")
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
        self.info_section.setObjectName("info_section")
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
        # preview_box and info_section background/border-radius are handled by QSS selectors
        # in image_card() via ImageCard QFrame#preview_box / ImageCard QFrame#info_section
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
            self.clicked.emit(self.image_id)
        elif event.button() == Qt.RightButton:
            self.right_clicked.emit(self.image_id, event.globalPos())

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self.image_id)
        super().mouseDoubleClickEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.double_clicked.emit(self.image_id)
        else:
            super().keyPressEvent(event)

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

        if not hasattr(self, "drag_start_position"):
            return
        if (event.pos() - self.drag_start_position).manhattanLength() < QApplication.startDragDistance():
            return

        mime_data = QMimeData()
        image_ids = [self.image_id]
        mime_data.setData(
            "application/x-snipshot-image-ids",
            QByteArray(json.dumps(image_ids).encode('utf-8'))
        )

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        pixmap = self.grab()
        drag.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        drag.setHotSpot(self.drag_start_position)

        drag.exec_(Qt.MoveAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if hasattr(self, "drag_start_position"):
                del self.drag_start_position
        super().mouseReleaseEvent(event)

    def _on_menu_clicked(self):
        self._show_context_menu(QCursor.pos())

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        from ui.styles import get_main_stylesheet
        menu.setStyleSheet(get_main_stylesheet())
        open_action = menu.addAction("View")
        open_action.triggered.connect(lambda: self.double_clicked.emit(self.image_id))
        rename_action = menu.addAction("Rename")
        rename_action.triggered.connect(
            lambda: self.rename_requested.emit(self.image_id)
        )
        move_action = menu.addAction("Move to Folder")
        move_action.triggered.connect(
            lambda: self.move_requested.emit(self.image_id)
        )
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        delete_action.triggered.connect(
            lambda: self.delete_requested.emit(self.image_id)
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
        if hasattr(self.parent(), "_reposition_floating_widgets"):
            self.parent()._reposition_floating_widgets()

    def _on_theme_changed(self, _mode=None):
        self._apply_style()

    def dragEnterEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasFormat("application/x-snipshot-image-ids") or mime_data.hasFormat("application/x-snipshot-folder-id"):
            event.acceptProposedAction()
            self._is_drag_over = True
            self._apply_style()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        mime_data = event.mimeData()
        if mime_data.hasFormat("application/x-snipshot-image-ids") or mime_data.hasFormat("application/x-snipshot-folder-id"):
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
        if mime_data.hasFormat("application/x-snipshot-image-ids"):
            json_bytes = mime_data.data("application/x-snipshot-image-ids").data().decode('utf-8')
            try:
                image_ids = json.loads(json_bytes)
                if hasattr(self.parent(), "_delete_images_dropped"):
                    self.parent()._delete_images_dropped(image_ids)
                event.acceptProposedAction()
            except (ValueError, json.JSONDecodeError):
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


class DragDropOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.hide()
        self._setup_ui()
        theme.theme_changed.connect(self._apply_style)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 0, 0, 0)

        # Inner frame for dashed border
        self.inner_frame = QFrame()
        inner_layout = QVBoxLayout(self.inner_frame)
        inner_layout.setAlignment(Qt.AlignCenter)
        inner_layout.setSpacing(SPACE["sm"])

        self.icon_lbl = QLabel()
        self.icon_lbl.setAlignment(Qt.AlignCenter)
        inner_layout.addWidget(self.icon_lbl)

        self.text_lbl = QLabel("Drop images here to translate")
        self.text_lbl.setAlignment(Qt.AlignCenter)
        inner_layout.addWidget(self.text_lbl)

        layout.addWidget(self.inner_frame)
        self._apply_style()

    def _apply_style(self):
        c = theme.c
        self.inner_frame.setFixedSize(320, 200)
        self.inner_frame.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {c['primary']};
                border-radius: 16px;
                background-color: {c['surface']};
            }}
        """)
        icon_pixmap = load_icon("translate_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg").pixmap(48, 48)
        self.icon_lbl.setPixmap(icon_pixmap)
        self.text_lbl.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: 600;
                color: {c['text']};
                background: transparent;
            }}
        """)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(0, 0, 0, 0.4);
            }}
        """)

    def set_drag_state(self, has_valid, has_folders, has_unsupported):
        c = theme.c
        if has_folders:
            self.inner_frame.setStyleSheet(f"""
                QFrame {{
                    border: 2px dashed {c['error']};
                    border-radius: 16px;
                    background-color: {c['surface']};
                }}
            """)
            self.text_lbl.setText("Folders are not supported")
            self.text_lbl.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['error']}; background: transparent;")
        elif has_unsupported and not has_valid:
            self.inner_frame.setStyleSheet(f"""
                QFrame {{
                    border: 2px dashed {c['error']};
                    border-radius: 16px;
                    background-color: {c['surface']};
                }}
            """)
            self.text_lbl.setText("Unsupported file type(s)")
            self.text_lbl.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['error']}; background: transparent;")
        else:
            self.inner_frame.setStyleSheet(f"""
                QFrame {{
                    border: 2px dashed {c['primary']};
                    border-radius: 16px;
                    background-color: {c['surface']};
                }}
            """)
            self.text_lbl.setText("Drop images here to translate")
            self.text_lbl.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {c['primary']}; background: transparent;")

    def dragEnterEvent(self, event):
        has_valid, has_folders, has_unsupported = self.parent()._check_drag_data(event.mimeData())
        self.set_drag_state(has_valid, has_folders, has_unsupported)
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.hide()
        event.accept()

    def dropEvent(self, event):
        self.hide()
        self.parent()._handle_file_drop(event.mimeData())
        event.acceptProposedAction()


class SectionHeader(QWidget):
    toggled = pyqtSignal(bool)  # Emits True if expanded, False if collapsed

    def __init__(self, text: str, is_expanded: bool = True, parent=None):
        super().__init__(parent)
        self.text = text
        self.is_expanded = is_expanded
        self._setup_ui()
        theme.theme_changed.connect(self._apply_style)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["xs"])
        layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Arrow toggle button
        self.arrow_btn = QToolButton()
        self.arrow_btn.setCursor(Qt.PointingHandCursor)
        self.arrow_btn.clicked.connect(self.toggle)

        # Flat button for the text label
        self.text_btn = QPushButton(self.text)
        self.text_btn.setCursor(Qt.PointingHandCursor)
        self.text_btn.clicked.connect(self.toggle)

        layout.addWidget(self.arrow_btn)
        layout.addWidget(self.text_btn)

        self._apply_style()

    def _apply_style(self):
        c = theme.c
        arrow_char = "▼" if self.is_expanded else "▶"
        self.arrow_btn.setText(arrow_char)
        
        self.arrow_btn.setStyleSheet(f"""
            QToolButton {{
                color: {c['text_secondary']};
                font-size: 11px;
                font-weight: bold;
                background-color: transparent;
                border: none;
                padding: 0;
            }}
            QToolButton:hover {{
                color: {c['primary']};
            }}
        """)
        self.text_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 12px;
                font-weight: 700;
                color: {c['text_secondary']};
                background-color: transparent;
                text-transform: uppercase;
                border: none;
                padding: 0;
            }}
            QPushButton:hover {{
                color: {c['primary']};
            }}
        """)

    def toggle(self):
        self.is_expanded = not self.is_expanded
        self._apply_style()
        self.toggled.emit(self.is_expanded)


class ToastNotification(QWidget):
    def __init__(self, parent, message, type="info"):
        super().__init__(parent)
        self.type = type
        self.message = message
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.close_toast)
        self.timer.start(4000) # 4 seconds
        self._setup_ui()
        theme.theme_changed.connect(self._apply_style)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(SPACE["sm"])

        self.emoji_lbl = QLabel()
        self.emoji_lbl.setStyleSheet("font-size: 16px; background: transparent; border: none;")
        layout.addWidget(self.emoji_lbl)

        self.text_lbl = QLabel(self.message)
        self.text_lbl.setWordWrap(True)
        layout.addWidget(self.text_lbl, 1)

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setIcon(load_icon("close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.close_btn.setIconSize(QSize(10, 10))
        self.close_btn.clicked.connect(self.close_toast)
        layout.addWidget(self.close_btn)

        self._apply_style()
        self.adjustSize()
        self.reposition()

    def _apply_style(self):
        c = theme.c
        border_color = c['border']
        if self.type == "success":
            self.emoji_lbl.setText("✅")
            border_color = c['primary']
        elif self.type == "error":
            self.emoji_lbl.setText("❌")
            border_color = c['error']
        else:
            self.emoji_lbl.setText("ℹ️")
            border_color = c['text_secondary']

        self.text_lbl.setStyleSheet(f"""
            QLabel {{
                color: {c['text']};
                font-size: 13px;
                font-weight: 500;
                background: transparent;
                border: none;
            }}
        """)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {c['surface_alt']};
                border: 1px solid {border_color};
                border-radius: 8px;
            }}
        """)

    def reposition(self):
        if not self.parent():
            return
        p_width = self.parent().width()
        x = (p_width - self.width()) // 2
        y = 70
        self.move(x, y)
        self.raise_()

    def close_toast(self):
        self.hide()
        self.deleteLater()


class ElidedLabel(QLabel):
    """A QLabel that automatically elides text to fit its width, with a tooltip of the full text."""
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self._full_text = text
        self.setToolTip(text)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(30)

    def setText(self, text):
        self._full_text = text
        self.setToolTip(text)
        self._elide_text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide_text()

    def _elide_text(self):
        fm = self.fontMetrics()
        elided = fm.elidedText(self._full_text, Qt.ElideMiddle, self.width())
        if elided != super().text():
            super().setText(elided)

    def minimumSizeHint(self):
        return QSize(30, self.fontMetrics().height())


class QueueItemWidget(QFrame):
    cancel_requested = pyqtSignal(str)

    def __init__(self, item_id: str, name: str, lang: str, thumbnail: QPixmap = None, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        self.status = "pending"
        self.setObjectName("QueueItemWidget")
        
        self._setup_ui(name, lang, thumbnail)
        self._apply_style()
        theme.theme_changed.connect(self._apply_style)

    def _setup_ui(self, name: str, lang: str, thumbnail: QPixmap):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACE["sm"], SPACE["sm"], SPACE["sm"], SPACE["sm"])
        layout.setSpacing(SPACE["sm"])
        
        # Thumbnail
        self.thumb_label = QLabel()
        self.thumb_label.setFixedSize(36, 36)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        if thumbnail:
            scaled = thumbnail.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumb_label.setPixmap(scaled)
        else:
            self.thumb_label.setText("\U0001F5BC") # fallback emoji
            self.thumb_label.setStyleSheet("font-size: 18px;")
            
        layout.addWidget(self.thumb_label)
        
        # Details layout
        details = QVBoxLayout()
        details.setSpacing(2)
        details.setContentsMargins(0, 0, 0, 0)
        
        # Name and Lang
        name_lang = QHBoxLayout()
        name_lang.setSpacing(4)
        
        self.name_lbl = ElidedLabel(name)
        self.name_lbl.setStyleSheet("font-weight: 600; font-size: 12px; background: transparent;")
        
        self.lang_badge = QLabel(lang)
        
        name_lang.addWidget(self.name_lbl, 1)
        name_lang.addWidget(self.lang_badge, 0)
        details.addLayout(name_lang)
        
        # Progress Bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFixedHeight(4)
        self.progress.setTextVisible(False)
        details.addWidget(self.progress)
        
        # Status
        self.status_lbl = QLabel("Pending...")
        self.status_lbl.setStyleSheet("font-size: 11px;")
        self.status_lbl.setWordWrap(True)
        details.addWidget(self.status_lbl)
        
        layout.addLayout(details, 1)

        # Cancel Button
        self.cancel_btn = QPushButton("×")
        self.cancel_btn.setFixedSize(20, 20)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._on_cancel_clicked)
        layout.addWidget(self.cancel_btn)

    def _on_cancel_clicked(self):
        self.cancel_requested.emit(self.item_id)

    def _apply_style(self):
        c = theme.c
        self.setStyleSheet(f"""
            QFrame#QueueItemWidget {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
        """)
        self.name_lbl.setStyleSheet(f"font-weight: 600; font-size: 12px; color: {c['text']}; background: transparent;")
        self.lang_badge.setStyleSheet(f"""
            QLabel {{
                background-color: {c['primary_light']};
                color: {c['primary_dark'] if theme.is_dark else c['primary']};
                font-size: 10px;
                font-weight: 700;
                padding: 1px 4px;
                border-radius: 3px;
            }}
        """)
        self.progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {c['border']};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {c['primary']};
                border-radius: 2px;
            }}
        """)
        self.status_lbl.setStyleSheet(f"font-size: 11px; color: {c['text_secondary']}; background: transparent;")
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text_secondary']};
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                padding: 0px;
                margin: 0px;
            }}
            QPushButton:hover {{
                background-color: {c['error_bg']};
                color: {c['error']};
            }}
        """)

    def update_status(self, status: str, progress: int = 0, error_msg: str = ""):
        c = theme.c
        self.status = status
        self.progress.setValue(progress)
        
        if status in ("pending", "translating", "saving"):
            self.cancel_btn.show()
        else:
            self.cancel_btn.hide()
            
        if status == "pending":
            self.status_lbl.setText("Pending...")
            self.status_lbl.setStyleSheet(f"font-size: 11px; color: {c['text_secondary']}; background: transparent;")
            self.progress.show()
        elif status == "translating":
            self.status_lbl.setText(f"Translating ({progress}%)")
            self.status_lbl.setStyleSheet(f"font-size: 11px; color: {c['primary']}; background: transparent;")
            self.progress.show()
        elif status == "saving":
            self.status_lbl.setText("Saving to account...")
            self.status_lbl.setStyleSheet(f"font-size: 11px; color: {c['primary']}; background: transparent;")
            self.progress.setValue(90)
            self.progress.show()
        elif status == "completed":
            self.status_lbl.setText("Completed")
            self.status_lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {c['success']}; background: transparent;")
            self.progress.hide()
        elif status == "failed":
            self.status_lbl.setText(f"Failed: {error_msg}")
            self.status_lbl.setStyleSheet(f"font-size: 11px; color: {c['error']}; background: transparent;")
            self.progress.hide()
        elif status == "cancelled":
            self.status_lbl.setText("Cancelled")
            self.status_lbl.setStyleSheet(f"font-size: 11px; color: {c['text_tertiary']}; background: transparent;")
            self.progress.hide()


class SettingControlWrapper:
    """Wrapper to interact with compound UI settings controls uniformly."""
    def __init__(self, key: str, main_layout_widget: QWidget):
        self.key = key
        self.main_layout_widget = main_layout_widget
        self.slider = None
        self.spinbox = None
        self.checkbox = None
        self.radio_buttons = []
        self.combo = None
        self.shortcut_display = None
        self.shortcut_btn = None
        self.badge = None

    def block_signals(self, block: bool):
        for widget in [self.slider, self.spinbox, self.checkbox, self.combo] + self.radio_buttons:
            if widget:
                widget.blockSignals(block)

    def set_value(self, value: Any):
        self.block_signals(True)
        
        # Handle checkbox values
        if self.checkbox:
            if self.spinbox:
                # Compound control (checkbox represents override/not None)
                self.checkbox.setChecked(value is not None)
                if value is None:
                    self.spinbox.setEnabled(False)
            else:
                # Standard boolean checkbox
                self.checkbox.setChecked(bool(value))
        
        # Update numeric controls
        if value is not None:
            if self.spinbox:
                self.spinbox.setEnabled(True)
                self.spinbox.setValue(value)
            if self.slider:
                self.slider.setEnabled(True)
                if isinstance(value, float):
                    self.slider.setValue(int(value * 100))
                else:
                    self.slider.setValue(value)
            if self.badge:
                if isinstance(value, float):
                    self.badge.setText(f"{value:.2f}")
                else:
                    self.badge.setText(f"{value}")
                    
        # Update choice controls
        if self.combo:
            idx = self.combo.findData(value)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
        for radio in self.radio_buttons:
            if radio.property("val") == value:
                radio.setChecked(True)
                
        # Update shortcut key representation if applicable
        if self.shortcut_display and isinstance(value, int) and not isinstance(value, bool):
            self.shortcut_display.setText(QKeySequence(value).toString())
                
        self.block_signals(False)

    def get_ui_value(self) -> Any:
        """Read live value from the UI inputs."""
        if self.checkbox:
            if self.spinbox:
                if not self.checkbox.isChecked():
                    return None
            else:
                return self.checkbox.isChecked()
        if self.spinbox:
            return self.spinbox.value()
        if self.combo:
            return self.combo.currentData()
        for radio in self.radio_buttons:
            if radio.isChecked():
                return radio.property("val")
        return None

    def show_error(self, error_message: str):
        """Applies error styling to the control's inputs."""
        border_style = "border: 1.5px solid red; border-radius: 4px;"
        if self.spinbox:
            self.spinbox.setStyleSheet(border_style)
            self.spinbox.setToolTip(error_message)
        elif self.combo:
            self.combo.setStyleSheet(border_style)
            self.combo.setToolTip(error_message)

    def clear_error(self):
        """Clears validation highlights."""
        if self.spinbox:
            self.spinbox.setStyleSheet("")
            self.spinbox.setToolTip("")
        elif self.combo:
            self.combo.setStyleSheet("")
            self.combo.setToolTip("")


class _ContentWidget(QWidget):
    """Content area widget that detects clicks on empty space for selection clearing."""
    empty_clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.childAt(event.pos()) is None:
                self.empty_clicked.emit()
        super().mousePressEvent(event)


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
    upload_requested = pyqtSignal(list)
    shortcut_changed = pyqtSignal(int)
    continuous_mode_changed = pyqtSignal(bool)
    continuous_shortcut_changed = pyqtSignal(int)
    snip_interval_changed = pyqtSignal(int)
    cancel_queue_item_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SnipShot - Dashboard")
        self.setMinimumSize(1200, 800)
        self.resize(1200, 800)

        self.current_folder_id = None
        self.current_folder_name = None
        self.active_nav = "all"
        self.selected_image_ids = set()
        
        from utils.settings_manager import settings_manager
        self.settings_manager = settings_manager
        self._setting_widgets = {}
        self.advanced_settings_visible = self.settings_manager.get_setting("ui_advanced_expanded", False)
        self.continuous_mode_enabled = False
        
        settings_manager.profile_changed.connect(self._on_settings_profile_changed)
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
        self._folder_cards = {}
        self._image_cards = {}
        self._current_view = "root"        # "root" | "folder" | "recent"
        self._current_folder_id = None
        self._current_folder_name = ""
        self._folder_nav_history = []      # list of (folder_id, folder_name)
        self.search_worker = None
        self.cache_loader_worker = None
        self.cache_update_worker = None
        self.folder_grid = None
        self.folder_grid_layout = None
        self._image_grid_widget = None
        self._queue_widgets = {}

        self._folders_expanded = True
        self._images_expanded = True
        self._folders_container = None
        self._images_container = None

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
        self.setAcceptDrops(True)
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
        
        # Queue toggle button in top bar
        self.queue_toggle_btn = QPushButton()
        self.queue_toggle_btn.setFixedSize(28, 28)
        self.queue_toggle_btn.setIcon(load_icon("translate_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.queue_toggle_btn.setIconSize(QSize(20, 20))
        self.queue_toggle_btn.setCursor(Qt.PointingHandCursor)
        self.queue_toggle_btn.setToolTip("Translation Queue")
        self.queue_toggle_btn.clicked.connect(self._toggle_queue_drawer)
        
        top_layout.addWidget(self.queue_toggle_btn, alignment=Qt.AlignVCenter)
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

        self.content_widget = _ContentWidget()
        self.content_widget.setStyleSheet(f"background-color: {c['bg']};")
        self.content_widget.empty_clicked.connect(self.clear_image_selection)
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

        # ========== Queue Sidebar Drawer (Right) ==========
        self.queue_sidebar = QFrame()
        self.queue_sidebar.setObjectName("queue_sidebar")
        self.queue_sidebar.setMinimumWidth(320)
        self.queue_sidebar.setMaximumWidth(600)
        self.queue_sidebar.setHidden(True)

        queue_layout = QVBoxLayout(self.queue_sidebar)
        queue_layout.setContentsMargins(SPACE["md"], SPACE["md"], SPACE["md"], SPACE["md"])
        queue_layout.setSpacing(SPACE["sm"])

        # Header of Queue Sidebar
        q_header = QHBoxLayout()
        self.q_title = QLabel("Translation Queue")
        self.q_title.setStyleSheet(f"font-size: {FONT['heading']['size']}px; font-weight: {FONT['heading']['weight']}; color: {c['text']};")
        
        self.q_close_btn = QPushButton()
        self.q_close_btn.setFixedSize(24, 24)
        self.q_close_btn.setCursor(Qt.PointingHandCursor)
        self.q_close_btn.setIcon(load_icon("close_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self.q_close_btn.setIconSize(QSize(16, 16))
        self.q_close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 12px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
            }
        """)
        self.q_close_btn.clicked.connect(lambda: self.queue_sidebar.setHidden(True))
        
        q_header.addWidget(self.q_title)
        q_header.addStretch()
        q_header.addWidget(self.q_close_btn)
        queue_layout.addLayout(q_header)

        # Scroll area for queue items
        self.q_scroll = QScrollArea()
        self.q_scroll.setWidgetResizable(True)
        self.q_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.q_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.q_list_widget = QWidget()
        self.q_list_widget.setObjectName("q_list_widget")
        self.q_list_widget.setStyleSheet("background: transparent;")
        self.q_list_layout = QVBoxLayout(self.q_list_widget)
        self.q_list_layout.setContentsMargins(0, 0, 0, 0)
        self.q_list_layout.setSpacing(SPACE["sm"])
        self.q_list_layout.setAlignment(Qt.AlignTop)
        
        self.q_scroll.setWidget(self.q_list_widget)
        queue_layout.addWidget(self.q_scroll)

        # Empty Queue placeholder
        self.q_empty_label = QLabel("No active translations.\nSnip to begin!")
        self.q_empty_label.setAlignment(Qt.AlignCenter)
        self.q_empty_label.setStyleSheet(f"color: {c['text_secondary']}; font-size: {FONT['caption']['size']}px; padding: {SPACE['lg']}px;")
        queue_layout.addWidget(self.q_empty_label)

        split_layout.addWidget(self.sidebar)
        
        # Create a splitter for main content and queue sidebar
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        self.main_splitter.addWidget(self.content_frame)
        self.main_splitter.addWidget(self.queue_sidebar)
        self.main_splitter.setSizes([800, 350])
        
        split_layout.addWidget(self.main_splitter)
        outer_layout.addWidget(split_widget)

        # Keep dummy controls for compatibility
        self.new_folder_btn = QPushButton()
        self.new_folder_btn.hide()
        self.refresh_btn = QPushButton()
        self.refresh_btn.hide()

        # Create floating Trash Drop Zone
        self.trash_drop_zone = TrashDropZone(self)
        self.trash_drop_zone.show()

        # Create Back to Top button
        self.back_to_top_btn = QPushButton("↑", self)
        self.back_to_top_btn.setFixedSize(36, 36)
        self.back_to_top_btn.setCursor(Qt.PointingHandCursor)
        self.back_to_top_btn.hide()
        self.back_to_top_btn.clicked.connect(self._scroll_to_top)

        # Create Drag & Drop Overlay
        self.drag_drop_overlay = DragDropOverlay(self)

        # Connect scroll listener for infinite scroll and Back to Top display
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)

        self._apply_styles()

    # ── Theme helpers ──────────────────────────────────────────────────
    def _apply_styles(self):
        """Apply or re-apply all sidebar / header / fixed-element styles."""
        c = theme.c
        self.scroll.setStyleSheet(f"QScrollArea {{ border: none; background-color: {c['bg']}; }}")
        self.content_widget.setStyleSheet(f"background-color: {c['bg']};")

        if hasattr(self, "main_splitter"):
            self.main_splitter.setStyleSheet(f"""
                QSplitter::handle {{
                    background-color: {c['border']};
                }}
                QSplitter::handle:horizontal {{
                    width: 2px;
                }}
                QSplitter::handle:horizontal:hover {{
                    background-color: {c['primary']};
                }}
            """)

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

        # Queue Drawer styles
        self.queue_sidebar.setStyleSheet(f"""
            QFrame#queue_sidebar {{
                background-color: {c['sidebar']};
                border-left: 1px solid {c['border']};
            }}
        """)
        self.q_title.setStyleSheet(f"""
            QLabel {{
                font-size: {FONT['heading']['size']}px;
                font-weight: {FONT['heading']['weight']};
                color: {c['text']};
                background: transparent;
            }}
        """)
        self.q_empty_label.setStyleSheet(f"""
            QLabel {{
                color: {c['text_secondary']};
                font-size: {FONT['caption']['size']}px;
                padding: {SPACE['lg']}px;
                background: transparent;
            }}
        """)
        self._update_queue_badge()
        self._apply_back_to_top_style()

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
        self.queue_toggle_btn.setIcon(load_icon("translate_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        self._update_queue_badge()
        
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
        """Recompute folder image counts from the local image cache and update visible card labels."""
        counts = {}
        for img in self._cached_images:
            fid = img.get("folder_id")
            if fid is not None:
                counts[fid] = counts.get(fid, 0) + 1
        for folder in self._cached_folders:
            new_count = counts.get(folder["id"], 0)
            folder["image_count"] = new_count
            
            # Update the visible widget count label directly
            card = self._folder_cards.get(folder["id"])
            if card:
                card.image_count = new_count
                image_label_text = "image" if new_count == 1 else "images"
                card.count_label.setText(f"{new_count} {image_label_text}")

    def _get_cached_image(self, image_id: int) -> Optional[dict]:
        """Resolve a dictionary reference from the images cache by ID."""
        for img in self._cached_images:
            if img.get("id") == image_id:
                return img
        return None

    def _add_folder_card_widget(self, folder: dict):
        """Create and prepend a FolderCard widget directly to the grid layout."""
        if self._current_view != "root" or not getattr(self, "folder_grid_layout", None):
            self._restore_current_view()
            return

        card = FolderCard(folder)
        card.clicked.connect(self._on_folder_clicked)
        card.delete_requested.connect(self._on_delete_folder)
        card.rename_requested.connect(self._on_rename_folder)
        card.image_dropped.connect(self._on_images_dropped)
        
        self.folder_grid_layout.insertWidget(0, card)
        self._folder_cards[folder["id"]] = card

    def _remove_folder_card_widget(self, folder_id: int):
        """Safely remove a folder card widget from the UI and delete it."""
        card = self._folder_cards.pop(folder_id, None)
        if card:
            try:
                card.clicked.disconnect()
                card.delete_requested.disconnect()
                card.rename_requested.disconnect()
                card.image_dropped.disconnect()
            except Exception:
                pass
            if getattr(self, "folder_grid_layout", None) is not None:
                self.folder_grid_layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
            
        # If no folders left in the root view, restore view to trigger empty state properly
        if self._current_view == "root" and not self._folder_cards and not any(img.get("folder_id") is None for img in self._cached_images):
            self._restore_current_view()

    def _add_image_card_widget(self, image: dict):
        """Create and prepend an ImageCard widget directly to the grid layout."""
        grid_widget = getattr(self, "_image_grid_widget", None)
        if not grid_widget or grid_widget.layout() is None:
            self._restore_current_view()
            return

        card = ImageCard(image)
        card.clicked.connect(self._on_image_clicked)
        card.double_clicked.connect(self._on_image_double_clicked)
        card.right_clicked.connect(self.show_image_context_menu)
        card.delete_requested.connect(self._on_delete_image)
        card.rename_requested.connect(self._on_rename_image)
        card.move_requested.connect(self._on_move_image)

        grid_widget.layout().insertWidget(0, card)
        self._image_cards[image["id"]] = card

    def _remove_image_card_widget(self, image_id: int):
        """Safely remove an image card widget from the UI and delete it."""
        card = self._image_cards.pop(image_id, None)
        if card:
            try:
                card.clicked.disconnect()
                card.double_clicked.disconnect()
                card.right_clicked.disconnect()
                card.delete_requested.disconnect()
                card.rename_requested.disconnect()
                card.move_requested.disconnect()
            except Exception:
                pass
            grid_widget = getattr(self, "_image_grid_widget", None)
            if grid_widget and grid_widget.layout() is not None:
                grid_widget.layout().removeWidget(card)
            card.setParent(None)
            card.deleteLater()
            
        # If no images left in the grid, restore view to trigger empty state properly
        grid_widget = getattr(self, "_image_grid_widget", None)
        if grid_widget and grid_widget.layout() is not None and grid_widget.layout().count() == 0:
            self._restore_current_view()

    def add_saved_image(self, image_data: dict):
        """Prepend a newly saved image to the cache and patch the UI in-place."""
        if not image_data or not isinstance(image_data, dict):
            return
        
        # Avoid duplicate entries in cache
        if any(img.get("id") == image_data.get("id") for img in self._cached_images):
            return

        # Prepend to the cache list
        self._cached_images.insert(0, image_data)

        # Apply active view matrix rules to show/hide the widget
        if self._current_view == "root":
            # root view displays unfiled images (folder_id is None) at the bottom
            if image_data.get("folder_id") is None:
                self._add_image_card_widget(image_data)
        elif self._current_view == "folder":
            # Display if it belongs to the current folder
            if self._current_folder_id == image_data.get("folder_id"):
                self._add_image_card_widget(image_data)
        elif self._current_view == "recent":
            # Always show in recent view
            self._add_image_card_widget(image_data)

        # Reconcile counts
        self._reconcile_folder_counts()

    def _move_image_locally(self, image_id: int, new_folder_id: int):
        """Update an image's folder in the cache and patch the UI in-place."""
        image_data = self._get_cached_image(image_id)
        if not image_data:
            return

        old_folder_id = image_data.get("folder_id")
        target_folder_id = new_folder_id if new_folder_id != 0 else None

        # Update cache
        image_data["folder_id"] = target_folder_id

        # Apply active view matrix rules to show/hide the widget
        if self._current_view == "root":
            # Case 1: Moved from unfiled to a folder -> remove widget
            if old_folder_id is None and target_folder_id is not None:
                self._remove_image_card_widget(image_id)
            # Case 2: Moved from folder to unfiled -> add widget
            elif old_folder_id is not None and target_folder_id is None:
                self._add_image_card_widget(image_data)
        elif self._current_view == "folder":
            # Case 1: Moved out of the current folder -> remove widget
            if old_folder_id == self._current_folder_id and target_folder_id != self._current_folder_id:
                self._remove_image_card_widget(image_id)
            # Case 2: Moved into the current folder -> add widget
            elif old_folder_id != self._current_folder_id and target_folder_id == self._current_folder_id:
                self._add_image_card_widget(image_data)

        # Reconcile counts
        self._reconcile_folder_counts()

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

        # Clear mappings and instance variables
        self._folder_cards = {}
        self._image_cards = {}
        self.folder_grid = None
        self.folder_grid_layout = None
        self._image_grid_widget = None
        self._folders_expanded = True
        self._images_expanded = True
        self._folders_container = None
        self._images_container = None
        self.selected_image_ids.clear()

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
        self._folder_nav_history = []
        self.header_title.setText("My Files")
        if len(self._cached_images) >= CacheLoaderWorker.SOFT_CAP:
            self.header_subtitle.setText("Root / All Files (Notice: Showing first 10,000 items. Use search to find others.)")
        else:
            self.header_subtitle.setText("Root / All Files")
        self._set_active_nav("all")
        self._clear_content()

        c = theme.c
        folders = [f for f in self._cached_folders if f.get("parent_folder_id") is None]
        images = self._cached_images
        unfiled_images = [img for img in images if img.get("folder_id") is None]

        if folders:
            header = SectionHeader("Folders", self._folders_expanded, self)
            header.toggled.connect(self._toggle_folders)
            self.content_layout.addWidget(header)

            self._folders_container = QWidget()
            self._folders_container.setStyleSheet("background-color: transparent;")
            folders_container_layout = QVBoxLayout(self._folders_container)
            folders_container_layout.setContentsMargins(0, 0, 0, 0)
            folders_container_layout.setSpacing(0)

            self.folder_grid = QWidget()
            self.folder_grid.setStyleSheet("background-color: transparent;")
            self.folder_grid_layout = FlowLayout(self.folder_grid, spacing=SPACE["md"])

            self._folder_cards = {}
            for folder in folders:
                card = FolderCard(folder)
                card.clicked.connect(self._on_folder_clicked)
                card.delete_requested.connect(self._on_delete_folder)
                card.rename_requested.connect(self._on_rename_folder)
                card.move_requested.connect(self._on_move_folder)
                card.image_dropped.connect(self._on_images_dropped)
                card.folder_dropped.connect(self._move_folder_to_folder)
                self.folder_grid_layout.addWidget(card)
                self._folder_cards[folder["id"]] = card

            folders_container_layout.addWidget(self.folder_grid)
            self.content_layout.addWidget(self._folders_container)
            self._folders_container.setVisible(self._folders_expanded)

        if unfiled_images:
            self.content_layout.addSpacing(SPACE["md"])

            header = SectionHeader("Unfiled Images", self._images_expanded, self)
            header.toggled.connect(self._toggle_images)
            self.content_layout.addWidget(header)

            self._images_container = QWidget()
            self._images_container.setStyleSheet("background-color: transparent;")
            images_container_layout = QVBoxLayout(self._images_container)
            images_container_layout.setContentsMargins(0, 0, 0, 0)
            images_container_layout.setSpacing(0)

            self._add_image_grid(unfiled_images)
            self.content_layout.addWidget(self._images_container)
            self._images_container.setVisible(self._images_expanded)

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
        
        # Build breadcrumbs path dynamically
        breadcrumbs = self._get_breadcrumbs(folder_id)
        breadcrumb_str = "Root / Folders / " + " / ".join(f["name"] for f in breadcrumbs)
        self.header_subtitle.setText(breadcrumb_str)
        self._clear_content()

        back_btn = StyledButton("", variant="ghost")
        back_btn.setIcon(load_icon("keyboard_backspace_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        back_btn.setIconSize(QSize(24, 24))
        back_btn.setToolTip("Back")
        back_btn.setMaximumWidth(50)
        back_btn.clicked.connect(self._on_nav_back)
        self.content_layout.addWidget(back_btn, alignment=Qt.AlignLeft)

        c = theme.c
        subfolders = [f for f in self._cached_folders if f.get("parent_folder_id") == folder_id]
        folder_images = [img for img in self._cached_images if img.get("folder_id") == folder_id]

        if subfolders:
            header = SectionHeader("Subfolders", self._folders_expanded, self)
            header.toggled.connect(self._toggle_folders)
            self.content_layout.addWidget(header)

            self._folders_container = QWidget()
            self._folders_container.setStyleSheet("background-color: transparent;")
            folders_container_layout = QVBoxLayout(self._folders_container)
            folders_container_layout.setContentsMargins(0, 0, 0, 0)
            folders_container_layout.setSpacing(0)

            self.folder_grid = QWidget()
            self.folder_grid.setStyleSheet("background-color: transparent;")
            self.folder_grid_layout = FlowLayout(self.folder_grid, spacing=SPACE["md"])

            self._folder_cards = {}
            for folder in subfolders:
                card = FolderCard(folder)
                card.clicked.connect(self._on_folder_clicked)
                card.delete_requested.connect(self._on_delete_folder)
                card.rename_requested.connect(self._on_rename_folder)
                card.move_requested.connect(self._on_move_folder)
                card.image_dropped.connect(self._on_images_dropped)
                card.folder_dropped.connect(self._move_folder_to_folder)
                self.folder_grid_layout.addWidget(card)
                self._folder_cards[folder["id"]] = card

            folders_container_layout.addWidget(self.folder_grid)
            self.content_layout.addWidget(self._folders_container)
            self._folders_container.setVisible(self._folders_expanded)
            self.content_layout.addSpacing(SPACE["md"])

        if folder_images:
            if subfolders:
                header = SectionHeader("Images", self._images_expanded, self)
                header.toggled.connect(self._toggle_images)
                self.content_layout.addWidget(header)

                self._images_container = QWidget()
                self._images_container.setStyleSheet("background-color: transparent;")
                images_container_layout = QVBoxLayout(self._images_container)
                images_container_layout.setContentsMargins(0, 0, 0, 0)
                images_container_layout.setSpacing(0)

            self._add_image_grid(folder_images)
            
            if subfolders:
                self.content_layout.addWidget(self._images_container)
                self._images_container.setVisible(self._images_expanded)
        elif not subfolders:
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
        self._loaded_images_count = len(display_images)
        self._scroll_loading = False

        self._image_grid_widget = QWidget()
        self._image_grid_widget.setStyleSheet("background-color: transparent;")
        grid_layout = FlowLayout(self._image_grid_widget, spacing=SPACE["md"])
        
        self._image_cards = {}
        for image in display_images:
            card = ImageCard(image)
            card.clicked.connect(self._on_image_clicked)
            card.double_clicked.connect(self._on_image_double_clicked)
            card.right_clicked.connect(self.show_image_context_menu)
            card.delete_requested.connect(self._on_delete_image)
            card.rename_requested.connect(self._on_rename_image)
            card.move_requested.connect(self._on_move_image)
            grid_layout.addWidget(card)
            self._image_cards[image["id"]] = card

        # Determine target layout (uses images container if defined, otherwise defaults to content layout)
        target_layout = self.content_layout
        if hasattr(self, "_images_container") and self._images_container is not None and self._images_container.layout() is not None:
            target_layout = self._images_container.layout()

        target_layout.addWidget(self._image_grid_widget)

        # Create loading progress bar for infinite scroll prefetching
        self._scroll_loading_widget = QProgressBar()
        self._scroll_loading_widget.setRange(0, 0)
        self._scroll_loading_widget.setTextVisible(False)
        self._scroll_loading_widget.setFixedHeight(4)
        c = theme.c
        self._scroll_loading_widget.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: transparent;
                margin-top: {SPACE['md']}px;
                margin-bottom: {SPACE['md']}px;
            }}
            QProgressBar::chunk {{
                background-color: {c['primary']};
                border-radius: 2px;
            }}
        """)
        self._scroll_loading_widget.hide()
        target_layout.addWidget(self._scroll_loading_widget)

        # Trigger viewport check to load more images automatically if screen height permits
        self._check_and_fill_viewport()

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

        extensions_filter = " ".join("*" + ext for ext in SUPPORTED_IMAGE_EXTENSIONS)
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            "",
            f"Images ({extensions_filter})",
        )
        if file_paths:
            self.upload_requested.emit(file_paths)

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
            header = SectionHeader(f"Folders Matching \"{query}\"", self._folders_expanded, self)
            header.toggled.connect(self._toggle_folders)
            self.content_layout.addWidget(header)

            self._folders_container = QWidget()
            self._folders_container.setStyleSheet("background-color: transparent;")
            folders_container_layout = QVBoxLayout(self._folders_container)
            folders_container_layout.setContentsMargins(0, 0, 0, 0)
            folders_container_layout.setSpacing(0)

            self.folder_grid = QWidget()
            self.folder_grid.setStyleSheet("background-color: transparent;")
            self.folder_grid_layout = FlowLayout(self.folder_grid, spacing=SPACE["md"])
            for folder in folders:
                card = FolderCard(folder)
                card.clicked.connect(self._on_folder_clicked)
                card.delete_requested.connect(self._on_delete_folder)
                card.rename_requested.connect(self._on_rename_folder)
                card.image_dropped.connect(self._on_images_dropped)
                self.folder_grid_layout.addWidget(card)

            folders_container_layout.addWidget(self.folder_grid)
            self.content_layout.addWidget(self._folders_container)
            self._folders_container.setVisible(self._folders_expanded)

        if images:
            if folders:
                self.content_layout.addSpacing(SPACE["lg"])
                
                header = SectionHeader(f"Images Matching \"{query}\"", self._images_expanded, self)
                header.toggled.connect(self._toggle_images)
                self.content_layout.addWidget(header)

                self._images_container = QWidget()
                self._images_container.setStyleSheet("background-color: transparent;")
                images_container_layout = QVBoxLayout(self._images_container)
                images_container_layout.setContentsMargins(0, 0, 0, 0)
                images_container_layout.setSpacing(0)

            self._add_image_grid(images)
            
            if folders:
                self.content_layout.addWidget(self._images_container)
                self._images_container.setVisible(self._images_expanded)

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

    def _continuous_pill_style(self, active: bool) -> str:
        """Style for continuous mode segmented control button."""
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
                    min-width: 140px;
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
                    min-width: 140px;
                }}
                QPushButton:hover {{
                    background-color: {c['hover']};
                    color: {c['text']};
                }}
            """

    def _render_settings_content(self):
        """Orchestrates layout generation for Settings tab."""
        c = theme.c

        # Clear existing wrappers
        self._setting_widgets.clear()

        # 1. Page title / header
        # The page headers are already updated by _on_nav_settings()
        
        # 2. Render Basic Settings QWidget
        basic_panel = self._render_basic_settings()
        self.content_layout.addWidget(basic_panel)
        self.content_layout.addSpacing(SPACE["lg"])

        # 3. Add Advanced settings toggle button
        toggle_layout = QHBoxLayout()
        toggle_layout.setContentsMargins(0, 0, 0, 0)
        
        self.advanced_toggle_btn = StyledButton(
            "Show Advanced Settings" if not self.advanced_settings_visible else "Hide Advanced Settings",
            variant="secondary"
        )
        self.advanced_toggle_btn.clicked.connect(self._toggle_advanced_panel)
        toggle_layout.addWidget(self.advanced_toggle_btn)
        toggle_layout.addStretch()
        self.content_layout.addLayout(toggle_layout)
        self.content_layout.addSpacing(SPACE["md"])

        # 4. Render Advanced Settings container
        self.advanced_container = self._render_advanced_settings()
        self.content_layout.addWidget(self.advanced_container)
        self._update_advanced_visibility()
        self.content_layout.addSpacing(SPACE["xl"])

        # 5. Global Reset Button
        reset_row = QHBoxLayout()
        reset_row.setContentsMargins(0, 0, 0, 0)
        
        global_reset_btn = StyledButton("Reset All Settings to Defaults", variant="secondary")
        global_reset_btn.setIcon(load_icon("refresh_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        global_reset_btn.clicked.connect(self._on_reset_all_settings)
        reset_row.addWidget(global_reset_btn)
        reset_row.addStretch()
        self.content_layout.addLayout(reset_row)

    def _render_basic_settings(self) -> QWidget:
        """Constructs and returns a styled container widget with all basic settings."""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["md"])

        layout.addWidget(self._section_header_label("", "General Preferences"))
        layout.addSpacing(SPACE["xs"])

        # Render basic settings dynamically using metadata
        for key, meta in SETTINGS_METADATA.items():
            if meta.get("tier") == "basic":
                # Ensure we skip dependent boolean keys to let the parent control handle them
                if key in ("use_font_size", "use_line_spacing"):
                    continue
                wrapper = self._build_control(key, meta)
                layout.addWidget(wrapper.main_layout_widget)
                self._setting_widgets[key] = wrapper

        return container

    def _render_advanced_settings(self) -> QWidget:
        """Constructs and returns a styled container widget with all advanced sections."""
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACE["lg"])

        # Dynamically find sections for advanced settings in ordered fashion
        advanced_sections = []
        for key, meta in SETTINGS_METADATA.items():
            if meta.get("tier") == "advanced":
                sec = meta.get("section")
                if sec and sec not in advanced_sections:
                    advanced_sections.append(sec)

        # Render sections
        for sec in advanced_sections:
            section_card = self._render_section(sec)
            layout.addWidget(section_card)

        return container

    def _render_section(self, section_id: str) -> QWidget:
        """Constructs a styled frame representing one advanced collapsible section card."""
        c = theme.c
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-left: 4px solid {c['primary']};
                border-radius: {SPACE['sm']}px;
            }}
        """)
        apply_card_shadow(card)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        layout.setSpacing(SPACE["sm"])

        # Header Row: Title on the left, Reset Button on the right
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_text = SECTION_LABELS.get(section_id, section_id.title())
        header_layout.addWidget(self._section_header_label("", title_text))
        header_layout.addStretch()

        reset_btn = QToolButton()
        reset_btn.setText(" Reset ")
        reset_btn.setIcon(load_icon("refresh_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
        reset_btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        reset_btn.setCursor(Qt.PointingHandCursor)
        reset_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {c['surface_alt']};
                border: 1px solid {c['border']};
                border-radius: 4px;
                padding: 4px 8px;
                color: {c['text_secondary']};
                font-weight: 500;
            }}
            QToolButton:hover {{
                background-color: {c['hover']};
                color: {c['text']};
            }}
        """)
        reset_btn.clicked.connect(lambda _, s=section_id: self._on_reset_section(s))
        header_layout.addWidget(reset_btn)
        
        layout.addLayout(header_layout)
        layout.addSpacing(SPACE["xs"])

        # Populate controls for this section dynamically
        for key, meta in SETTINGS_METADATA.items():
            if meta.get("tier") == "advanced" and meta.get("section") == section_id:
                if key in ("use_prob",):
                    continue
                wrapper = self._build_control(key, meta)
                layout.addWidget(wrapper.main_layout_widget)
                self._setting_widgets[key] = wrapper

        return card

    def _toggle_advanced_panel(self):
        """Toggle advanced settings and persist expanded state locally."""
        self.advanced_settings_visible = not self.advanced_settings_visible
        self.settings_manager.set_setting("ui_advanced_expanded", self.advanced_settings_visible)
        self._update_advanced_visibility()

    def _update_advanced_visibility(self):
        """Syncs the advanced settings container visibility with current toggle state."""
        if hasattr(self, "advanced_container") and self.advanced_container:
            self.advanced_container.setVisible(self.advanced_settings_visible)
        if hasattr(self, "advanced_toggle_btn") and self.advanced_toggle_btn:
            self.advanced_toggle_btn.setText(
                "Hide Advanced Settings" if self.advanced_settings_visible else "Show Advanced Settings"
            )

    def _build_control(self, key: str, meta: dict) -> SettingControlWrapper:
        """Dynamically generates QWidget layout and binds inputs into a SettingControlWrapper."""
        c = theme.c
        control_type = meta["ui"]["control"]
        label_text = meta["ui"]["label"]
        tooltip_text = meta["ui"].get("tooltip", "")
        default_val = meta.get("default")
        current_val = self.settings_manager.get_setting(key)
        
        container = QWidget()
        container.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, SPACE["xs"] // 2, 0, SPACE["xs"] // 2)
        layout.setSpacing(SPACE["xs"])
        
        wrapper = SettingControlWrapper(key, container)
        
        # Header layout for labels/combos/etc.
        lbl_layout = QHBoxLayout()
        lbl_layout.setContentsMargins(0, 0, 0, 0)
        lbl_layout.setSpacing(SPACE["sm"])
        
        label = QLabel(label_text)
        label.setStyleSheet(self._settings_label_style())
        label.setToolTip(tooltip_text)
        lbl_layout.addWidget(label)
        lbl_layout.addStretch()
        
        if control_type == "combo":
            combo = QComboBox()
            combo.setStyleSheet(self._settings_input_style())
            combo.setCursor(Qt.PointingHandCursor)
            for display_label, data_val in meta["ui"].get("options", []):
                combo.addItem(display_label, data_val)
            idx = combo.findData(current_val)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.currentIndexChanged.connect(lambda _, k=key: self._on_control_modified(k))
            
            combo.setFixedWidth(240)
            lbl_layout.addWidget(combo)
            wrapper.combo = combo
            layout.addLayout(lbl_layout)
            
        elif control_type == "checkbox":
            chk = QCheckBox()
            chk.setCursor(Qt.PointingHandCursor)
            chk.setChecked(bool(current_val))
            chk.stateChanged.connect(lambda _, k=key: self._on_control_modified(k))
            
            lbl_layout.addWidget(chk)
            wrapper.checkbox = chk
            layout.addLayout(lbl_layout)
            
        elif control_type == "radio_group":
            group = QGroupBox()
            group.setStyleSheet("QGroupBox { border: none; margin: 0px; padding: 0px; background-color: transparent; }")
            g_layout = QHBoxLayout(group)
            g_layout.setContentsMargins(0, 0, 0, 0)
            g_layout.setSpacing(SPACE["md"])
            
            for display_label, data_val in meta["ui"].get("options", []):
                radio = QRadioButton(display_label)
                radio.setCursor(Qt.PointingHandCursor)
                radio.setProperty("val", data_val)
                radio.setStyleSheet(f"color: {c['text']}; font-size: {FONT['body']['size']}px;")
                radio.setChecked(current_val == data_val)
                radio.toggled.connect(lambda checked, k=key: checked and self._on_control_modified(k))
                g_layout.addWidget(radio)
                wrapper.radio_buttons.append(radio)
            
            lbl_layout.addWidget(group)
            layout.addLayout(lbl_layout)
            
        elif control_type == "segmented_theme":
            pill_widget = QWidget()
            pill_layout = QHBoxLayout(pill_widget)
            pill_layout.setContentsMargins(0, 0, 0, 0)
            pill_layout.setSpacing(SPACE["xs"])
            
            light_btn = QPushButton("Light")
            light_btn.setIcon(load_icon("light_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
            light_btn.setIconSize(QSize(20, 20))
            light_btn.setCursor(Qt.PointingHandCursor)
            
            dark_btn = QPushButton("Dark")
            dark_btn.setIcon(load_icon("dark_mode_24dp_E3E3E3_FILL0_wght400_GRAD0_opsz24.svg"))
            dark_btn.setIconSize(QSize(20, 20))
            dark_btn.setCursor(Qt.PointingHandCursor)
            
            def set_theme_ui(val):
                light_btn.setStyleSheet(self._theme_pill_style(val == "light"))
                dark_btn.setStyleSheet(self._theme_pill_style(val == "dark"))
                
            set_theme_ui(current_val)
            
            def on_theme_click(val):
                set_theme_ui(val)
                theme.set_mode(val)
                self._on_control_modified(key)
                
            light_btn.clicked.connect(lambda: on_theme_click("light"))
            dark_btn.clicked.connect(lambda: on_theme_click("dark"))
            
            pill_layout.addWidget(light_btn)
            pill_layout.addWidget(dark_btn)
            lbl_layout.addWidget(pill_widget)
            
            wrapper.combo = QComboBox()
            wrapper.combo.addItem("light", "light")
            wrapper.combo.addItem("dark", "dark")
            wrapper.combo.setCurrentIndex(wrapper.combo.findData(current_val))
            
            layout.addLayout(lbl_layout)
            
        elif control_type == "shortcut_key":
            display = QLabel(self._key_name(current_val))
            display.setAlignment(Qt.AlignCenter)
            display.setStyleSheet(f"""
                QLabel {{
                    padding: {SPACE['sm']}px {SPACE['lg']}px;
                    border: 1px solid {c['border']};
                    border-bottom: 3px solid {c['border']};
                    border-radius: {SPACE['xs']}px;
                    font-size: {FONT['label']['size']}px;
                    font-weight: 700;
                    background-color: {c['surface_alt']};
                    color: {c['text']};
                    min-width: 100px;
                    letter-spacing: 1px;
                }}
            """)
            
            btn = _ShortcutButton("Change Shortcut")
            
            def on_shortcut_captured(new_key, k=key, disp=display):
                disp.setText(self._key_name(new_key))
                self.settings_manager.set_setting(k, new_key)
                self._on_control_modified(k)
                if k == "snip_shortcut_key":
                    self.shortcut_changed.emit(new_key)
                elif k == "continuous_shortcut_key":
                    self.continuous_shortcut_changed.emit(new_key)
                    
            btn.shortcut_captured.connect(on_shortcut_captured)
            lbl_layout.addWidget(display)
            lbl_layout.addWidget(btn)
            wrapper.shortcut_display = display
            wrapper.shortcut_btn = btn
            layout.addLayout(lbl_layout)
            
        elif control_type == "number_input":
            spin = QSpinBox()
            spin.setStyleSheet(self._settings_input_style())
            v_meta = meta.get("validation", {})
            spin.setRange(v_meta.get("min", 0), v_meta.get("max", 999999))
            spin.setValue(int(current_val))
            spin.editingFinished.connect(lambda k=key: self._on_control_modified(k))
            spin.setFixedWidth(120)
            
            lbl_layout.addWidget(spin)
            wrapper.spinbox = spin
            layout.addLayout(lbl_layout)
            
        elif control_type in ("slider_spinbox", "slider_spinbox_optional"):
            v_meta = meta.get("validation", {})
            min_val = v_meta.get("min", 0)
            max_val = v_meta.get("max", 100)
            step = v_meta.get("step", 1)
            is_float = meta["type"] == "float"
            
            use_key = f"use_{key}"
            has_use_key = use_key in SETTINGS_METADATA
            
            if has_use_key:
                use_label = SETTINGS_METADATA[use_key]["ui"]["label"]
                use_chk = QCheckBox(use_label)
                use_chk.setCursor(Qt.PointingHandCursor)
                use_chk.setChecked(self.settings_manager.get_setting(use_key, False))
                
                lbl_layout.addWidget(use_chk)
                wrapper.checkbox = use_chk
                
            badge = self._value_badge("")
            lbl_layout.addWidget(badge)
            wrapper.badge = badge
            layout.addLayout(lbl_layout)
            
            slider_row = QHBoxLayout()
            slider_row.setSpacing(SPACE["sm"])
            
            slider = QSlider(Qt.Horizontal)
            slider.setStyleSheet(self._styled_slider())
            slider.setCursor(Qt.PointingHandCursor)
            
            if is_float:
                slider.setRange(int(min_val * 100), int(max_val * 100))
                slider.setSingleStep(int(step * 100))
                val_to_set = current_val if current_val is not None else default_val
                slider.setValue(int(val_to_set * 100))
            else:
                slider.setRange(int(min_val), int(max_val))
                slider.setSingleStep(int(step))
                val_to_set = current_val if current_val is not None else default_val
                slider.setValue(int(val_to_set))
                
            slider_row.addWidget(slider)
            wrapper.slider = slider
            
            if is_float:
                spin = QDoubleSpinBox()
                spin.setDecimals(2)
                spin.setSingleStep(step)
            else:
                spin = QSpinBox()
                spin.setSingleStep(int(step))
                
            spin.setStyleSheet(self._settings_input_style())
            spin.setRange(min_val, max_val)
            val_to_set = current_val if current_val is not None else default_val
            spin.setValue(val_to_set)
            spin.setFixedWidth(100)
            slider_row.addWidget(spin)
            wrapper.spinbox = spin
            
            layout.addLayout(slider_row)
            
            def sync_slider_to_spinbox(slider_val, k=key, sp=spin, bd=badge, fl=is_float):
                actual_val = slider_val / 100.0 if fl else slider_val
                sp.blockSignals(True)
                sp.setValue(actual_val)
                sp.blockSignals(False)
                if fl:
                    bd.setText(f"{actual_val:.2f}")
                else:
                    bd.setText(f"{actual_val}")
                self._on_control_modified(k)
                
            def sync_spinbox_to_slider(k=key, sl=slider, sp=spin, bd=badge, fl=is_float):
                spin_val = sp.value()
                sl.blockSignals(True)
                sl.setValue(int(spin_val * 100) if fl else int(spin_val))
                sl.blockSignals(False)
                if fl:
                    bd.setText(f"{spin_val:.2f}")
                else:
                    bd.setText(f"{spin_val}")
                self._on_control_modified(k)
                
            slider.valueChanged.connect(lambda val: sync_slider_to_spinbox(val))
            spin.valueChanged.connect(lambda _: sync_spinbox_to_slider())
            
            badge_val = current_val if current_val is not None else default_val
            if is_float:
                badge.setText(f"{badge_val:.2f}")
            else:
                badge.setText(f"{badge_val}")
                
            if has_use_key:
                is_enabled = self.settings_manager.get_setting(use_key, False)
                slider.setEnabled(is_enabled)
                spin.setEnabled(is_enabled)
                
                def on_use_toggled(state, k=key, uk=use_key, sl=slider, sp=spin):
                    enabled = state == Qt.Checked
                    sl.setEnabled(enabled)
                    sp.setEnabled(enabled)
                    self.settings_manager.set_setting(uk, enabled)
                    self._on_control_modified(k)
                    
                use_chk.stateChanged.connect(lambda state: on_use_toggled(state))
       
       # Add hint label below control
        layout.addWidget(self._hint_label(tooltip_text))
       
        return wrapper

    def _refresh_setting_control(self, key: str):
        """Refreshes a control's UI value in-place without rebuilding the widget layout."""
        wrapper = self._setting_widgets.get(key)
        if not wrapper:
            return
        
        val = self.settings_manager.get_setting(key)
        wrapper.set_value(val)
        wrapper.clear_error()

        use_key = f"use_{key}"
        if use_key in SETTINGS_METADATA and use_key in self._setting_widgets:
            use_val = self.settings_manager.get_setting(use_key, False)
            use_wrapper = self._setting_widgets[use_key]
            use_wrapper.set_value(use_val)

    def _on_control_modified(self, key: str):
        """Fires when any setting control input is modified. Validates and saves changes."""
        wrapper = self._setting_widgets.get(key)
        if not wrapper:
            return
            
        new_val = wrapper.get_ui_value()
        
        # Build active context from other UI inputs to avoid order-dependency errors
        context = {}
        if key == "font_size_minimum":
            font_size_wrapper = self._setting_widgets.get("font_size")
            if font_size_wrapper:
                context["font_size"] = font_size_wrapper.get_ui_value()
                
        is_valid, error_msg = self.settings_manager.validate_setting(key, new_val, current_ui_context=context)
        
        if not is_valid:
            wrapper.show_error(error_msg)
        else:
            wrapper.clear_error()
            self.settings_manager.set_validated(key, new_val)
            
        # Cascade validations (e.g. if Font Size changed, re-validate Minimum Font Size)
        if key == "font_size":
            self._on_control_modified("font_size_minimum")

    def _on_reset_all_settings(self):
        """Resets all configuration preferences to defaults in-place."""
        reply = QMessageBox.question(
            self, "Reset All Settings?",
            "Reset all settings to defaults? This cannot be undone.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_all_settings()
            
            # Update all widgets in-place
            for key in self._setting_widgets:
                self._refresh_setting_control(key)
                
            self.show_toast("Settings reset successfully", "success")

    def _on_reset_section(self, section_name: str):
        """Resets dynamic section configuration preferences in-place."""
        reply = QMessageBox.question(
            self, f"Reset Section?",
            f"Reset all '{SECTION_LABELS.get(section_name, section_name)}' settings to defaults?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.settings_manager.reset_section(section_name)
            
            keys_to_reset = self.settings_manager.get_keys_in_section(section_name)
            for key in keys_to_reset:
                self._refresh_setting_control(key)
                
            self.show_toast(f"'{SECTION_LABELS.get(section_name, section_name)}' reset successfully", "success")

    def _on_settings_profile_changed(self):
        """Update settings UI components in-place on profile changes (e.g. login/logout)."""
        self.shortcut_changed.emit(self.snip_shortcut_key)
        self.continuous_shortcut_changed.emit(self.continuous_shortcut_key)
        self.snip_interval_changed.emit(self.continuous_snip_interval)

        for key in list(self._setting_widgets.keys()):
            self._refresh_setting_control(key)

    # ── Settings Properties (single source of truth in settings_manager) ──
    @property
    def target_language(self):
        return self.settings_manager.get_setting("target_language")

    @target_language.setter
    def target_language(self, value):
        self.settings_manager.set_setting("target_language", value)

    @property
    def snip_shortcut_key(self):
        return self.settings_manager.get_setting("snip_shortcut_key")

    @snip_shortcut_key.setter
    def snip_shortcut_key(self, value):
        self.settings_manager.set_setting("snip_shortcut_key", value)

    @property
    def continuous_shortcut_key(self):
        return self.settings_manager.get_setting("continuous_shortcut_key")

    @continuous_shortcut_key.setter
    def continuous_shortcut_key(self, value):
        self.settings_manager.set_setting("continuous_shortcut_key", value)

    @property
    def continuous_snip_interval(self):
        return self.settings_manager.get_setting("continuous_snip_interval")

    @continuous_snip_interval.setter
    def continuous_snip_interval(self, value):
        self.settings_manager.set_setting("continuous_snip_interval", value)

    @property
    def detection_size(self):
        return self.settings_manager.get_setting("detection_size")

    @detection_size.setter
    def detection_size(self, value):
        self.settings_manager.set_setting("detection_size", value)

    @property
    def box_threshold(self):
        return self.settings_manager.get_setting("box_threshold")

    @box_threshold.setter
    def box_threshold(self, value):
        self.settings_manager.set_setting("box_threshold", value)

    @property
    def inpainting_size(self):
        return self.settings_manager.get_setting("inpainting_size")

    @inpainting_size.setter
    def inpainting_size(self, value):
        self.settings_manager.set_setting("inpainting_size", value)

    @property
    def inpainter(self):
        return self.settings_manager.get_setting("inpainter")

    @inpainter.setter
    def inpainter(self, value):
        self.settings_manager.set_setting("inpainter", value)

    def get_target_language(self) -> str:
        return self.target_language

    def get_translation_config(self) -> dict:
        """Reads validated values on-demand to serialize the backend parameters payload."""
        config = {
            "detector": {
                "detector": self.settings_manager.get_setting("detector"),
                "detection_size": self.settings_manager.get_setting("detection_size"),
                "box_threshold": self.settings_manager.get_setting("box_threshold"),
                "text_threshold": self.settings_manager.get_setting("text_threshold"),
                "unclip_ratio": self.settings_manager.get_setting("unclip_ratio"),
                "det_rotate": self.settings_manager.get_setting("det_rotate"),
                "det_auto_rotate": self.settings_manager.get_setting("det_auto_rotate"),
                "det_invert": self.settings_manager.get_setting("det_invert"),
                "det_gamma_correct": self.settings_manager.get_setting("det_gamma_correct"),
            },
            "translator": {
                "target_lang": self.settings_manager.get_setting("target_language"),
                "no_text_lang_skip": self.settings_manager.get_setting("no_text_lang_skip"),
            },
            "inpainter": {
                "inpainter": self.settings_manager.get_setting("inpainter"),
                "inpainting_size": self.settings_manager.get_setting("inpainting_size"),
                "inpainting_precision": self.settings_manager.get_setting("inpainting_precision"),
            },
            "ocr": {
                "ocr": self.settings_manager.get_setting("ocr"),
                "min_text_length": self.settings_manager.get_setting("min_text_length"),
                "ignore_bubble": self.settings_manager.get_setting("ignore_bubble"),
                "prob": self.settings_manager.get_setting("prob") if self.settings_manager.get_setting("use_prob") else None,
            },
            "render": {
                "renderer": self.settings_manager.get_setting("renderer"),
                "font_size": self.settings_manager.get_setting("font_size") if self.settings_manager.get_setting("use_font_size") else None,
                "font_size_minimum": self.settings_manager.get_setting("font_size_minimum"),
                "font_size_offset": self.settings_manager.get_setting("font_size_offset"),
                "line_spacing": self.settings_manager.get_setting("line_spacing") if self.settings_manager.get_setting("use_line_spacing") else None,
                "disable_font_border": self.settings_manager.get_setting("disable_font_border"),
                "alignment": self.settings_manager.get_setting("alignment"),
                "direction": self.settings_manager.get_setting("direction"),
                "no_hyphenation": self.settings_manager.get_setting("no_hyphenation"),
                "rtl": self.settings_manager.get_setting("rtl"),
            },
            "kernel_size": self.settings_manager.get_setting("kernel_size"),
            "mask_dilation_offset": self.settings_manager.get_setting("mask_dilation_offset"),
        }

        # Expand text_case radio selection to boolean pair (uppercase/lowercase)
        text_case = self.settings_manager.get_setting("text_case")
        if text_case == "uppercase":
            config["render"]["uppercase"] = True
            config["render"]["lowercase"] = False
        elif text_case == "lowercase":
            config["render"]["uppercase"] = False
            config["render"]["lowercase"] = True
        else:  # "normal"
            config["render"]["uppercase"] = False
            config["render"]["lowercase"] = False

        return config

    @staticmethod
    def _settings_label_style() -> str:
        c = theme.c
        return f"font-size: {FONT['label']['size']}px; font-weight: {FONT['label']['weight']}; color: {c['text']}; margin-top: 4px; background-color: transparent;"

    @staticmethod
    def _settings_input_style() -> str:
        return styles.settings_input()

    @staticmethod
    def _key_name(key: int) -> str:
        ks = QKeySequence(key)
        text = ks.toString(QKeySequence.NativeText)
        return text if text else QKeySequence(key).toString()

    def _on_folder_clicked(self, folder_id: int, folder_name: str):
        if self._current_view == "root":
            self._folder_nav_history = []
        elif self._current_view == "folder" and self._current_folder_id is not None:
            if not self._folder_nav_history or self._folder_nav_history[-1][0] != self._current_folder_id:
                self._folder_nav_history.append((self._current_folder_id, self._current_folder_name))
        self._load_folder(folder_id, folder_name)

    def _on_nav_back(self):
        if self._folder_nav_history:
            prev_id, prev_name = self._folder_nav_history.pop()
            self._load_folder(prev_id, prev_name)
        else:
            self._render_root_view()

    def _get_breadcrumbs(self, folder_id: int) -> list:
        path = []
        curr_id = folder_id
        folder_map = {f["id"]: f for f in self._cached_folders}
        visited = set()
        while curr_id and curr_id not in visited:
            visited.add(curr_id)
            f = folder_map.get(curr_id)
            if not f:
                break
            path.append(f)
            curr_id = f.get("parent_folder_id")
        path.reverse()
        return path

    def _is_descendant(self, parent_id: int, child_id: int) -> bool:
        """Check if child_id is a descendant of parent_id."""
        if parent_id == child_id:
            return True
        
        folder_map = {f["id"]: f for f in self._cached_folders}
        curr_id = child_id
        visited = set()
        while curr_id and curr_id not in visited:
            visited.add(curr_id)
            f = folder_map.get(curr_id)
            if not f:
                break
            parent = f.get("parent_folder_id")
            if parent == parent_id:
                return True
            curr_id = parent
        return False

    def _move_folder_to_folder(self, target_folder_id: int, source_folder_id: int):
        """Move source_folder_id inside target_folder_id after checking for circular references."""
        if self._is_descendant(source_folder_id, target_folder_id):
            QMessageBox.warning(
                self,
                "Invalid Move",
                "Cannot move a folder into its own subfolder."
            )
            return

        result = api_client.update_folder(source_folder_id, parent_folder_id=target_folder_id)
        if result.get("success"):
            updated_folder = result.get("data")
            if updated_folder:
                for f in self._cached_folders:
                    if f["id"] == source_folder_id:
                        f["parent_folder_id"] = target_folder_id
                        break
            self._restore_current_view()
        else:
            QMessageBox.warning(
                self,
                "Error",
                result.get("error", "Failed to move folder")
            )

    def _on_move_folder(self, folder_id: int, current_name: str):
        """Show dialog allowing user to move folder_id inside another folder or to Root."""
        folders = self._cached_folders
        # Exclude the folder itself and its descendants to prevent circular loops
        valid_folders = [f for f in folders if f["id"] != folder_id and not self._is_descendant(folder_id, f["id"])]
        
        folder_names = ["Root"] + [f["name"] for f in valid_folders]
        folder_ids = [None] + [f["id"] for f in valid_folders]
        
        curr_folder = next((f for f in folders if f["id"] == folder_id), None)
        curr_parent_id = curr_folder.get("parent_folder_id") if curr_folder else None
        
        current_idx = 0
        if curr_parent_id is not None:
            try:
                current_idx = folder_ids.index(curr_parent_id)
            except ValueError:
                current_idx = 0
                
        choice, ok = QInputDialog.getItem(
            self,
            "Move Folder",
            f"Move folder '{current_name}' to:",
            folder_names,
            current_idx,
            False,
        )
        if ok and choice:
            idx = folder_names.index(choice)
            target_parent_id = folder_ids[idx]
            result = api_client.update_folder(folder_id, parent_folder_id=target_parent_id)
            if result.get("success"):
                for f in self._cached_folders:
                    if f["id"] == folder_id:
                        f["parent_folder_id"] = target_parent_id
                        break
                self._restore_current_view()
            else:
                QMessageBox.warning(
                    self, "Error", result.get("error", "Failed to move folder")
                )

    def _on_image_clicked(self, image_id: int):
        card = self._image_cards.get(image_id)
        if not card:
            return
        ctrl_held = bool(QApplication.keyboardModifiers() & Qt.ControlModifier)
        if ctrl_held:
            # Ctrl+click: toggle this card without affecting others
            if image_id in self.selected_image_ids:
                self.selected_image_ids.discard(image_id)
                card.set_selected(False)
            else:
                self.selected_image_ids.add(image_id)
                card.set_selected(True)
        else:
            # Normal click: clear all, select only this one
            self.clear_image_selection()
            self.selected_image_ids.add(image_id)
            card.set_selected(True)

    def _on_image_double_clicked(self, image_id: int):
        image_data = self._get_cached_image(image_id)
        if not image_data:
            return

        import time
        current_time = time.time()
        # If the signed URL was generated more than 50 minutes (3000 seconds) ago,
        # or if there is no signed URL, refresh it.
        if current_time - image_data.get("_signed_at", 0) > 3000 or not image_data.get("public_url"):
            try:
                res = self.api_client.get_image(image_id)
                if res.get("success") and res.get("data"):
                    image_data.update(res.get("data"))
                    image_data["_signed_at"] = current_time
                else:
                    print(f"Warning: Failed to refresh signed URL for image {image_id}: {res.get('error')}")
            except Exception as e:
                print(f"Error: Exception while retrieving signed URL for image {image_id}: {e}")

        images_snapshot = list(self.all_images) if hasattr(self, "all_images") and self.all_images else [image_data]
        dialog = ImagePreviewDialog(images_snapshot, image_data, self)
        dialog.exec_()

    def clear_image_selection(self):
        for image_id in list(self.selected_image_ids):
            card = self._image_cards.get(image_id)
            if card:
                card.set_selected(False)
        self.selected_image_ids.clear()

    def show_image_context_menu(self, image_id: int, pos: QPoint):
        is_selected = image_id in self.selected_image_ids
        is_multi = is_selected and len(self.selected_image_ids) > 1

        if not is_selected:
            self.clear_image_selection()
            self._on_image_clicked(image_id)

        menu = QMenu(self)
        from ui.styles import get_main_stylesheet
        menu.setStyleSheet(get_main_stylesheet())

        if is_multi:
            count = len(self.selected_image_ids)
            move_action = menu.addAction(f"Move {count} images to Folder")
            move_action.triggered.connect(self._on_bulk_move_images)
            menu.addSeparator()
            delete_action = menu.addAction(f"Delete {count} images")
            delete_action.triggered.connect(self._on_bulk_delete_images)
        else:
            view_action = menu.addAction("View")
            view_action.triggered.connect(lambda: self._on_image_double_clicked(image_id))
            rename_action = menu.addAction("Rename")
            rename_action.triggered.connect(lambda: self._on_rename_image(image_id))
            move_action = menu.addAction("Move to Folder")
            move_action.triggered.connect(lambda: self._on_move_image(image_id))
            menu.addSeparator()
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self._on_delete_image(image_id))

        menu.exec_(pos)

    def _on_bulk_move_images(self):
        if not self.selected_image_ids:
            return

        folders = self._cached_folders
        if not folders:
            QMessageBox.information(self, "No Folders", "Create a folder first to move images into it.")
            return

        folder_names = ["Unfiled"] + [f["name"] for f in folders]
        folder_ids = [0] + [f["id"] for f in folders]

        choice, ok = QInputDialog.getItem(
            self, "Move to Folder",
            f"Move {len(self.selected_image_ids)} image(s) to:",
            folder_names, 0, False
        )
        if ok and choice:
            idx = folder_names.index(choice)
            target_folder_id = folder_ids[idx]
            for image_id in list(self.selected_image_ids):
                result = api_client.move_image_to_folder(image_id, folder_id=target_folder_id)
                if result.get("success"):
                    self._move_image_locally(image_id, target_folder_id)
            self.selected_image_ids.clear()

    def _on_bulk_delete_images(self):
        if not self.selected_image_ids:
            return

        count = len(self.selected_image_ids)
        reply = QMessageBox.question(
            self, "Delete Images",
            f"Delete {count} image(s) permanently?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            for image_id in list(self.selected_image_ids):
                result = api_client.delete_image(image_id)
                if result.get("success"):
                    self._cached_images = [img for img in self._cached_images if img["id"] != image_id]
                    self._remove_image_card_widget(image_id)
            self.selected_image_ids.clear()
            self._reconcile_folder_counts()

    def _on_new_folder(self):
        dialog = CreateFolderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            name, description = dialog.get_values()
            if name:
                parent_id = self._current_folder_id if self._current_view == "folder" else None
                result = api_client.create_folder(name, description, parent_folder_id=parent_id)
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
        # Find parent_folder_id of the deleted folder
        target_folder = next((f for f in self._cached_folders if f["id"] == folder_id), None)
        parent_id = target_folder.get("parent_folder_id") if target_folder else None

        msg = QMessageBox(self)
        msg.setWindowTitle("Delete Folder")
        msg.setText(f"Delete folder '{folder_name}'?")
        msg.setInformativeText("Choose how to handle any subfolders and images inside:")
        
        promote_btn = msg.addButton(
            "Promote Contents (Move to Parent/Root)", QMessageBox.AcceptRole
        )
        delete_all_btn = msg.addButton(
            "Delete Folder + All Contents Recursively", QMessageBox.DestructiveRole
        )
        msg.addButton("Cancel", QMessageBox.RejectRole)
        msg.exec_()

        clicked = msg.clickedButton()
        if clicked == promote_btn:
            action = "promote"
        elif clicked == delete_all_btn:
            action = "delete_all"
        else:
            return

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            if action == "promote":
                # 1. Promote subfolders to parent_id
                subfolders = [f for f in self._cached_folders if f.get("parent_folder_id") == folder_id]
                failed_folders = []
                for sf in subfolders:
                    res = api_client.update_folder(sf["id"], parent_folder_id=parent_id)
                    if res.get("success"):
                        sf["parent_folder_id"] = parent_id
                    else:
                        failed_folders.append(sf["name"])

                # 2. Promote images in this folder to parent_id
                images = [img for img in self._cached_images if img.get("folder_id") == folder_id]
                failed_images = []
                for img in images:
                    res = api_client.move_image_to_folder(img["id"], folder_id=parent_id)
                    if res.get("success"):
                        img["folder_id"] = parent_id
                    else:
                        failed_images.append(img.get("filename") or f"Image ID {img['id']}")

                # Report promote partial failures if any
                if failed_folders or failed_images:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.warning(
                        self,
                        "Partial Failures",
                        f"Failed to promote some items:\n"
                        f"Folders: {', '.join(failed_folders) if failed_folders else 'None'}\n"
                        f"Images: {', '.join(failed_images) if failed_images else 'None'}"
                    )
                    QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))

                # 3. Delete the folder row
                res = api_client.delete_folder(folder_id, delete_images=False)
                if res.get("success"):
                    self._cached_folders = [f for f in self._cached_folders if f["id"] != folder_id]
                    # If currently viewing this folder, go back
                    if self._current_view == "folder" and self._current_folder_id == folder_id:
                        self._on_nav_back()
                    else:
                        self._restore_current_view()
                else:
                    QApplication.restoreOverrideCursor()
                    QMessageBox.warning(
                        self,
                        "Error",
                        res.get("error", "Failed to delete the folder itself.")
                    )

            elif action == "delete_all":
                # 1. Collect all subfolder IDs and images recursively
                folder_ids = [folder_id]
                image_ids = []
                
                # Stack for DFS
                subfolder_map = {}
                for f in self._cached_folders:
                    p_id = f.get("parent_folder_id")
                    if p_id is not None:
                        subfolder_map.setdefault(p_id, []).append(f["id"])
                        
                stack = [folder_id]
                visited = set()
                while stack:
                    curr = stack.pop()
                    if curr in visited:
                        continue
                    visited.add(curr)
                    if curr != folder_id:
                        folder_ids.append(curr)
                    children = subfolder_map.get(curr, [])
                    for child in children:
                        if child not in visited:
                            stack.append(child)

                # Collect all images inside any of these folders
                for img in self._cached_images:
                    if img.get("folder_id") in folder_ids:
                        image_ids.append(img)

                failed_images = []
                # Handle storage deletion before DB deletion (built into delete_image API method)
                for img in image_ids:
                    res = api_client.delete_image(img["id"])
                    if res.get("success"):
                        self._cached_images = [i for i in self._cached_images if i["id"] != img["id"]]
                    else:
                        failed_images.append(img.get("filename") or f"Image ID {img['id']}")

                failed_folders = []
                # Delete folders bottom-up (reverse order of DFS traversal is perfect since parents are pushed first)
                for fid in reversed(folder_ids):
                    res = api_client.delete_folder(fid, delete_images=False)
                    if res.get("success"):
                        self._cached_folders = [f for f in self._cached_folders if f["id"] != fid]
                    else:
                        fname = next((f["name"] for f in self._cached_folders if f["id"] == fid), f"Folder ID {fid}")
                        failed_folders.append(fname)

                # Report recursive delete partial failures if any
                QApplication.restoreOverrideCursor()
                if failed_folders or failed_images:
                    QMessageBox.warning(
                        self,
                        "Partial Failures During Deletion",
                        f"Failed to delete some items:\n"
                        f"Folders: {', '.join(failed_folders) if failed_folders else 'None'}\n"
                        f"Images: {', '.join(failed_images) if failed_images else 'None'}"
                    )

                # Navigate back if current folder was deleted
                if self._current_view == "folder" and self._current_folder_id in folder_ids:
                    self._folder_nav_history = [(fid, name) for fid, name in self._folder_nav_history if fid not in folder_ids]
                    self._on_nav_back()
                else:
                    self._restore_current_view()
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Exception Occurred", f"An error occurred during folder deletion: {str(e)}")
        finally:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

    def _on_rename_folder(self, folder_id: int, current_name: str):
        new_name, ok = QInputDialog.getText(
            self, "Rename Folder", "New name:", text=current_name
        )
        if ok and new_name and new_name.strip() and new_name.strip() != current_name:
            new_name = new_name.strip()
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
                    self.header_title.setText(new_name)
                    self.header_subtitle.setText(f"Root / Folders / {new_name}")
                
                # Update folder card label directly
                card = self._folder_cards.get(folder_id)
                if card:
                    card.folder_name = new_name
                    card.name_label.setText(new_name)
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
                # Remove from cache
                self._cached_images = [img for img in self._cached_images if img["id"] != image_id]
                # Remove widget
                self._remove_image_card_widget(image_id)
                # Reconcile counts
                self._reconcile_folder_counts()
            else:
                QMessageBox.warning(self, "Error", "Failed to delete image")

    def _on_rename_image(self, image_id: int):
        image_data = self._get_cached_image(image_id)
        if not image_data:
            return

        current_name = image_data.get("filename", "")
        new_name, ok = QInputDialog.getText(
            self, "Rename Image", "New filename:", text=current_name
        )
        if ok and new_name.strip() and new_name.strip() != current_name:
            new_name = new_name.strip()
            result = api_client.update_image(image_id, filename=new_name)
            if result.get("success"):
                # Update local cache
                image_data["filename"] = new_name
                
                # Update visible card directly
                card = self._image_cards.get(image_id)
                if card:
                    card.image_data["filename"] = new_name
                    card.name_label.setText(new_name)
                    size = card.image_data.get("file_size")
                    size_text = format_file_size(size) if size else "0 KB"
                    ext = new_name.split(".")[-1].upper() if "." in new_name else "PNG"
                    card.meta_label.setText(f"{size_text} • {ext}")
            else:
                QMessageBox.warning(self, "Error", result.get("error", "Failed to rename image"))


    def _on_move_image(self, image_id: int):
        image_data = self._get_cached_image(image_id)
        if not image_data:
            return

        folders = self._cached_folders
        folder_names = ["Unfiled"] + [f["name"] for f in folders]
        folder_ids = [0] + [f["id"] for f in folders]

        if len(folder_names) == 1:
            QMessageBox.information(
                self,
                "No Folders",
                "Create a folder first to move images into it.",
            )
            return

        # Find current folder index to set as default in prompt
        curr_folder_id = image_data.get("folder_id")
        current_idx = 0
        if curr_folder_id is not None:
            try:
                current_idx = folder_ids.index(curr_folder_id)
            except ValueError:
                current_idx = 0

        choice, ok = QInputDialog.getItem(
            self,
            "Move to Folder",
            f"Move '{image_data.get('filename', 'image')}' to:",
            folder_names,
            current_idx,
            False,
        )
        if ok and choice:
            idx = folder_names.index(choice)
            folder_id = folder_ids[idx]
            result = api_client.move_image_to_folder(image_id, folder_id=folder_id)
            if result.get("success"):
                self._move_image_locally(image_id, folder_id)
            else:
                QMessageBox.warning(
                    self, "Error", result.get("error", "Failed to move image")
                )

    def _on_images_dropped(self, folder_id: int, image_ids: list):
        if getattr(self, "_is_moving_image", False):
            return
        self._is_moving_image = True

        # If a single selected image was dragged, expand to the full selection
        if len(image_ids) == 1 and image_ids[0] in self.selected_image_ids:
            effective_ids = list(self.selected_image_ids)
        else:
            effective_ids = image_ids

        # Validate that the drop target is a valid folder
        valid_folder = any(f["id"] == folder_id for f in self._cached_folders)
        if not valid_folder:
            self._is_moving_image = False
            return

        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        try:
            for image_id in effective_ids:
                result = self.api_client.move_image_to_folder(image_id, folder_id=folder_id)
                if result.get("success"):
                    self._move_image_locally(image_id, folder_id)
                else:
                    QMessageBox.warning(
                        self,
                        "Move Failed",
                        result.get("error", "Failed to move the image to the folder.")
                    )
                    break
            self.selected_image_ids.clear()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred while moving the image: {str(e)}")
        finally:
            QApplication.restoreOverrideCursor()
            self._is_moving_image = False

    def _delete_images_dropped(self, image_ids: list):
        if getattr(self, "_is_deleting_item", False):
            return
        self._is_deleting_item = True
        try:
            # If a single selected image was dragged, expand to the full selection
            if len(image_ids) == 1 and image_ids[0] in self.selected_image_ids:
                effective_ids = list(self.selected_image_ids)
            else:
                effective_ids = image_ids

            if len(effective_ids) == 1:
                self._on_delete_image(effective_ids[0])
            else:
                reply = QMessageBox.question(
                    self, "Delete Images",
                    f"Delete {len(effective_ids)} image(s) permanently?",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if reply == QMessageBox.Yes:
                    for image_id in effective_ids:
                        result = api_client.delete_image(image_id)
                        if result.get("success"):
                            self._cached_images = [img for img in self._cached_images if img["id"] != image_id]
                            self._remove_image_card_widget(image_id)
                    self.selected_image_ids.clear()
                    self._reconcile_folder_counts()
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
        self._reposition_floating_widgets()
        if hasattr(self, "drag_drop_overlay") and self.drag_drop_overlay:
            self.drag_drop_overlay.setGeometry(self.rect())
        if hasattr(self, "_current_toast") and self._current_toast:
            self._current_toast.reposition()

    def _check_drag_data(self, mime_data) -> tuple:
        has_valid_images = False
        has_folders = False
        has_unsupported = False
        
        if mime_data.hasUrls():
            for url in mime_data.urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    has_folders = True
                elif path.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                    has_valid_images = True
                else:
                    has_unsupported = True
        return has_valid_images, has_folders, has_unsupported

    def dragEnterEvent(self, event):
        has_valid, has_folders, has_unsupported = self._check_drag_data(event.mimeData())
        if has_valid or has_folders or has_unsupported:
            event.acceptProposedAction()
            if hasattr(self, "drag_drop_overlay") and self.drag_drop_overlay:
                self.drag_drop_overlay.setGeometry(self.rect())
                self.drag_drop_overlay.set_drag_state(has_valid, has_folders, has_unsupported)
                self.drag_drop_overlay.show()
                self.drag_drop_overlay.raise_()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def _handle_file_drop(self, mime_data):
        valid_files = []
        folder_count = 0
        unsupported_count = 0
        
        if mime_data.hasUrls():
            for url in mime_data.urls():
                path = url.toLocalFile()
                if os.path.isdir(path):
                    folder_count += 1
                elif path.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS):
                    if os.path.isfile(path):
                        valid_files.append(path)
                else:
                    unsupported_count += 1
                    
        if valid_files:
            self.upload_requested.emit(valid_files)
            
        if folder_count > 0 or unsupported_count > 0:
            msg_parts = []
            if len(valid_files) > 0:
                msg_parts.append(f"{len(valid_files)} image(s) were added to the queue.")
            if folder_count > 0:
                msg_parts.append(f"{folder_count} folder(s) were ignored (folders are not supported).")
            if unsupported_count > 0:
                msg_parts.append(f"{unsupported_count} unsupported file(s) were ignored.")
                
            QMessageBox.warning(
                self,
                "Upload Warning",
                "\n".join(msg_parts)
            )

    def showEvent(self, event):
        super().showEvent(event)
        self._reposition_floating_widgets()

    def _reposition_floating_widgets(self):
        margin_right = 24
        margin_bottom = 24
        
        # Trash Drop Zone dimensions for math (decoupled layout)
        trash_w = 64
        trash_h = 64
        trash_x = self.width() - trash_w - margin_right
        trash_y = self.height() - trash_h - margin_bottom
        
        if hasattr(self, "trash_drop_zone") and self.trash_drop_zone is not None:
            self.trash_drop_zone.move(trash_x, trash_y)
            
        # Back to Top Button placed horizontally to the left of the trash zone
        btn_w = 36
        btn_h = 36
        btn_x = trash_x - btn_w - 10
        btn_y = trash_y + (trash_h - btn_h) // 6 + 2
        
        if hasattr(self, "back_to_top_btn") and self.back_to_top_btn is not None:
            self.back_to_top_btn.move(btn_x, btn_y)

    def _apply_back_to_top_style(self):
        if not hasattr(self, "back_to_top_btn") or self.back_to_top_btn is None:
            return
        c = theme.c
        self.back_to_top_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['surface_alt']};
                color: {c['text']};
                border: 1px solid {c['border']};
                border-radius: 18px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {c['primary_subtle']};
                color: {c['primary_dark'] if theme.is_dark else c['primary']};
                border-color: {c['primary']};
            }}
        """)

    def _scroll_to_top(self):
        from PyQt5.QtCore import QVariantAnimation
        scrollbar = self.scroll.verticalScrollBar()
        self._scroll_animation = QVariantAnimation(self)
        self._scroll_animation.setStartValue(scrollbar.value())
        self._scroll_animation.setEndValue(0)
        self._scroll_animation.setDuration(400) # 400ms smooth scroll
        self._scroll_animation.valueChanged.connect(scrollbar.setValue)
        self._scroll_animation.start()

    def _toggle_folders(self, expanded):
        self._folders_expanded = expanded
        if hasattr(self, "_folders_container") and self._folders_container:
            self._folders_container.setVisible(expanded)

    def _toggle_images(self, expanded):
        self._images_expanded = expanded
        if hasattr(self, "_images_container") and self._images_container:
            self._images_container.setVisible(expanded)
        if expanded:
            self._check_and_fill_viewport()

    def _on_scroll_value_changed(self, value):
        # 1. Toggle Back to Top button based on scroll depth
        if hasattr(self, "back_to_top_btn") and self.back_to_top_btn is not None:
            if value > 600:
                if self.back_to_top_btn.isHidden():
                    self.back_to_top_btn.show()
                    self.back_to_top_btn.raise_()
            else:
                if not self.back_to_top_btn.isHidden():
                    self.back_to_top_btn.hide()

        # 2. Check prefetching condition for infinite scroll
        if not getattr(self, "_images_expanded", True):
            return
        if not hasattr(self, "all_images") or not hasattr(self, "_loaded_images_count"):
            return
        if getattr(self, "_scroll_loading", False):
            return
        if self._loaded_images_count >= len(self.all_images):
            return
        if getattr(self, "_image_grid_widget", None) is None:
            return

        scrollbar = self.scroll.verticalScrollBar()
        remaining = scrollbar.maximum() - value
        if remaining < 400: # Prefetch threshold (400px remaining scroll)
            self._load_next_page_batch()

    def _check_and_fill_viewport(self):
        if not getattr(self, "_images_expanded", True):
            return
        if not hasattr(self, "all_images") or not hasattr(self, "_loaded_images_count"):
            return
        if getattr(self, "_scroll_loading", False):
            return
        if self._loaded_images_count >= len(self.all_images):
            return
        if getattr(self, "_image_grid_widget", None) is None:
            return

        scrollbar = self.scroll.verticalScrollBar()
        if scrollbar.maximum() == 0:
            # Viewport not filled, trigger next load immediately
            self._load_next_page_batch()

    def _load_next_page_batch(self):
        # 1. Set loading flag immediately to prevent duplicate triggers
        self._scroll_loading = True
        
        # 2. Show the progress bar loader
        if hasattr(self, "_scroll_loading_widget") and self._scroll_loading_widget:
            self._scroll_loading_widget.show()
            
        # 3. Defer the heavy rendering work to allow Qt to paint the loader
        QTimer.singleShot(0, self._render_next_page_batch)

    def _render_next_page_batch(self):
        # Double check sanity conditions
        if not hasattr(self, "all_images") or not hasattr(self, "_loaded_images_count") or getattr(self, "_image_grid_widget", None) is None:
            self._scroll_loading = False
            if hasattr(self, "_scroll_loading_widget") and self._scroll_loading_widget:
                self._scroll_loading_widget.hide()
            return

        next_batch = self.all_images[self._loaded_images_count : self._loaded_images_count + 20]
        if next_batch:
            layout = self._image_grid_widget.layout()
            if layout:
                for image in next_batch:
                    card = ImageCard(image)
                    card.clicked.connect(self._on_image_clicked)
                    card.double_clicked.connect(self._on_image_double_clicked)
                    card.right_clicked.connect(self.show_image_context_menu)
                    card.delete_requested.connect(self._on_delete_image)
                    card.rename_requested.connect(self._on_rename_image)
                    card.move_requested.connect(self._on_move_image)
                    layout.addWidget(card)
                    self._image_cards[image["id"]] = card

        self._loaded_images_count += len(next_batch)
        self._scroll_loading = False
        
        if hasattr(self, "_scroll_loading_widget") and self._scroll_loading_widget:
            self._scroll_loading_widget.hide()

        # Check if another batch is needed to fill the viewport recursively (using 50ms single-shot timer for layout calculations)
        QTimer.singleShot(50, self._check_and_fill_viewport)

    def _toggle_queue_drawer(self):
        """Toggle queue sidebar visibility."""
        if hasattr(self, "queue_sidebar"):
            self.queue_sidebar.setHidden(not self.queue_sidebar.isHidden())

    def add_queue_item_ui(self, item_id: str, name: str, lang: str, thumbnail: QPixmap = None):
        """Create and add a new QueueItemWidget to the queue sidebar drawer."""
        if not hasattr(self, "_queue_widgets"):
            self._queue_widgets = {}

        # Hide empty label
        if hasattr(self, "q_empty_label"):
            self.q_empty_label.hide()

        # Instantiate item widget
        widget = QueueItemWidget(item_id, name, lang, thumbnail, self)
        widget.cancel_requested.connect(self.cancel_queue_item_requested.emit)
        self._queue_widgets[item_id] = widget
        
        # Add to list layout
        if hasattr(self, "q_list_layout"):
            self.q_list_layout.addWidget(widget)
            
        # Update badge count
        self._update_queue_badge()

    def show_toast(self, message: str, type: str = "info"):
        if hasattr(self, "_current_toast") and self._current_toast:
            try:
                self._current_toast.deleteLater()
            except (RuntimeError, TypeError):
                pass
        self._current_toast = ToastNotification(self, message, type)
        self._current_toast.show()

    def update_queue_item_ui(self, item_id: str, status: str, progress: int = 0, error_msg: str = ""):
        """Update the status of an existing item in the queue drawer."""
        if not hasattr(self, "_queue_widgets") or item_id not in self._queue_widgets:
            return
            
        widget = self._queue_widgets[item_id]
        widget.update_status(status, progress, error_msg)
        
        # Update badge count
        self._update_queue_badge()

        # If terminal state, schedule removal after a short delay (1.5 seconds)
        if status in ("completed", "failed", "cancelled"):
            filename = widget.name_lbl._full_text if hasattr(widget, "name_lbl") else "Image"
            if status == "completed":
                self.show_toast(f"Translation completed for {filename}!", type="success")
            elif status == "failed":
                self.show_toast(f"Translation failed for {filename}: {error_msg}", type="error")
            elif status == "cancelled":
                self.show_toast(f"Translation cancelled for {filename}.", type="info")

            # Schedule removal
            QTimer.singleShot(1500, lambda: self._remove_queue_item(item_id))

    def _remove_queue_item(self, item_id: str):
        """Remove a queue item widget from the UI and safely clean it up."""
        if not hasattr(self, "_queue_widgets") or item_id not in self._queue_widgets:
            return
        widget = self._queue_widgets.pop(item_id)
        if hasattr(self, "q_list_layout") and self.q_list_layout:
            self.q_list_layout.removeWidget(widget)
        widget.deleteLater()
        
        # Show empty label if list is empty
        if not self._queue_widgets and hasattr(self, "q_empty_label"):
            self.q_empty_label.show()
            
        self._update_queue_badge()

    def _update_queue_badge(self):
        """Update the toggle button badge count with active/pending tasks."""
        if not hasattr(self, "_queue_widgets") or not hasattr(self, "queue_toggle_btn"):
            return
            
        active_count = 0
        for widget in self._queue_widgets.values():
            if widget.status in ("pending", "translating", "saving"):
                active_count += 1
                
        if active_count > 0:
            self.queue_toggle_btn.setFixedSize(65, 28)
            self.queue_toggle_btn.setText(f" ({active_count})")
            c = theme.c
            self.queue_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['primary_subtle']};
                    color: {c['primary_dark'] if theme.is_dark else c['primary']};
                    border: 1px solid {c['primary']};
                    font-size: 13px;
                    font-weight: 700;
                    border-radius: 14px;
                }}
                QPushButton:hover {{
                    background-color: {c['primary_light']};
                }}
            """)
        else:
            self.queue_toggle_btn.setFixedSize(28, 28)
            self.queue_toggle_btn.setText("")
            c = theme.c
            self.queue_toggle_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    padding: 0px;
                    border-radius: 14px;
                    color: {c['text_secondary']};
                }}
                QPushButton:hover {{
                    background-color: {c['hover']};
                }}
            """)

    def _on_logout(self):
        api_client.logout()
        self.logout_requested.emit()

    def closeEvent(self, event: QCloseEvent):
        self.search_timer.stop()
        self._cancel_worker("search_worker")
        self._cancel_worker("cache_loader_worker")
        self._cancel_worker("cache_update_worker")
        event.accept()
