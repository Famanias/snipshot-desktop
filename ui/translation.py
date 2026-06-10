# translation.py
# CHANGELOG
# ─────────────────────────────────────────────────────────────────────
# - Replaced QProgressBar indeterminate with SnipShotSpinner
# - save_frame pre-added with setFixedHeight(0), animated via
#   QPropertyAnimation on maximumHeight (0 → natural, 300 ms OutCubic)
# - Preview frame: rounded corners (border-radius 12px via pixmap mask),
#   subtle 1px inner border
# - Replaced QComboBox folder selector with FolderSelector widget
# - Replaced dialog_cancel / dialog_primary buttons with StyledButton
# - All spacing uses SPACE constants; all font sizes use FONT constants
# ─────────────────────────────────────────────────────────────────────

"""
SnipShot Desktop - Translation Window

Shows translation progress and result, allows saving to folder.
"""

import copy
import time

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QProgressBar, QComboBox, QMessageBox, QDialog,
)
from PyQt5.QtCore import (
    Qt, pyqtSignal, QThread, QBuffer, QIODevice,
    QPropertyAnimation, QEasingCurve, QTimer,
)
from PyQt5.QtGui import QPixmap, QPainterPath, QRegion, QBitmap, QPainter, QColor, QImage

from api import api_client
from config import DEFAULT_TRANSLATION_CONFIG
from .theme import theme
from . import styles
from .styles import SPACE, FONT, apply_card_shadow
from .components import StyledButton, SnipShotSpinner, FolderSelector


class TranslationWorker(QThread):
    """Background worker for translation"""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, image_bytes: bytes, target_language: str = "ENG", translation_config: dict = None):
        super().__init__()
        self.image_bytes = image_bytes
        self.target_language = target_language
        self.translation_config = translation_config

    def run(self):
        try:
            config = copy.deepcopy(
                self.translation_config if self.translation_config is not None
                else DEFAULT_TRANSLATION_CONFIG
            )
            config.setdefault("translator", {})
            config["translator"]["target_lang"] = self.target_language

            result = api_client.translate_image(self.image_bytes, config=config)
            if result["success"]:
                self.finished.emit(result["data"])
            else:
                self.error.emit(result.get("error", "Translation failed"))
        except Exception as e:
            self.error.emit(str(e))


class SaveWorker(QThread):
    """Background worker for saving to database"""

    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(
        self,
        image_bytes: bytes,
        filename: str,
        folder_id: int = None,
        target_language: str = "ENG",
    ):
        super().__init__()
        self.image_bytes = image_bytes
        self.filename = filename
        self.folder_id = folder_id
        self.target_language = target_language

    def run(self):
        try:
            
            result = api_client.save_image_from_bytes(
                self.image_bytes,
                self.filename,
                self.folder_id,
                source_language="JPN",
                target_language=self.target_language,
            )
            if result["success"]:
                self.finished.emit(result["data"])
            else:
                self.error.emit(result.get("error", "Save failed"))
        except Exception as e:
            self.error.emit(str(e))


def validate_qimage(image: QImage) -> tuple:
    """
    Returns (True, "", "") if image is acceptable, otherwise (False, title, message).
    Safe to call from background threads.
    """
    import numpy as np

    # ── 1. Resolution check ─────────────────────────────
    min_width, min_height = 300, 300
    if image.width() < min_width or image.height() < min_height:
        return (
            False,
            "Image Too Small",
            f"Image resolution too low ({image.width()}x{image.height()}).\n"
            f"Minimum required is {min_width}x{min_height}."
        )

    # Convert to standard format for analysis
    image = image.convertToFormat(4)  # Format_ARGB32

    width = image.width()
    height = image.height()

    ptr = image.bits()
    ptr.setsize(image.byteCount())
    arr = np.frombuffer(ptr, np.uint8).reshape(height, width, 4)

    # ── 2. Blank image detection ────────────────────────
    gray = arr[..., :3].mean(axis=2)

    brightness = gray.mean()
    contrast = gray.std()

    # If almost uniform or too dark/bright
    if brightness < 10 or brightness > 245 or contrast < 5:
        return (
            False,
            "Blank Image Detected",
            "The captured image appears to be blank or unreadable."
        )

    # ── 3. Blur detection (variance of Laplacian) ───────
    # Simple edge detection approximation (no OpenCV required)
    laplacian = (
        np.abs(gray[1:-1, 1:-1] - gray[:-2, 1:-1]) +
        np.abs(gray[1:-1, 1:-1] - gray[2:, 1:-1]) +
        np.abs(gray[1:-1, 1:-1] - gray[1:-1, :-2]) +
        np.abs(gray[1:-1, 1:-1] - gray[1:-1, 2:])
    )

    blur_score = laplacian.var()

    if blur_score < 15:  # tune this depending on device
        return (
            False,
            "Image Too Blurry",
            "The captured image is too blurry. Please retake the screenshot."
        )

    return True, "", ""


class TranslationWindow(QDialog):
    """
    Window shown during/after translation.
    Displays progress, result, and save options.
    """

    saved = pyqtSignal(dict)

    def __init__(
        self,
        captured_pixmap: QPixmap,
        parent=None,
        target_language: str = "ENG",
        translation_config: dict = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("SnipShot - Translate")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        self.captured_pixmap = captured_pixmap

        if not self._validate_image(self.captured_pixmap):
            QTimer.singleShot(0, self.reject)
            return

        self.target_language = target_language
        self.translation_config = translation_config
        self.translated_bytes = None
        self.folders = []
        self.translation_success = False

        self._setup_ui()
        self._load_folders()
        self._start_translation()

    def _setup_ui(self):
        c = theme.c

        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        layout.setSpacing(SPACE["md"])

        # Title
        self.title_label = QLabel("Translating Image...")
        self.title_label.setStyleSheet(
            f"font-size: {FONT['heading']['size']}px; font-weight: {FONT['heading']['weight']}; "
            f"color: {c['text']}; background-color: transparent;"
        )
        layout.addWidget(self.title_label)

        # Preview with rounded corners and inner border
        self.preview_frame = QFrame()
        self.preview_frame.setStyleSheet(
            f"background-color: {c['surface_alt']}; "
            f"border-radius: {SPACE['md']}px; "
            f"border: 1px solid {c['border']};"
        )
        self.preview_frame.setFixedHeight(200)

        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setAlignment(Qt.AlignCenter)

        self.preview_label = QLabel()
        scaled = self.captured_pixmap.scaled(
            300, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        # Create rounded pixmap
        rounded = self._round_pixmap(scaled, SPACE["md"])
        self.preview_label.setPixmap(rounded)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: transparent;")
        preview_layout.addWidget(self.preview_label)

        layout.addWidget(self.preview_frame)

        # Spinner (replaces indeterminate progress bar)
        spinner_row = QHBoxLayout()
        spinner_row.setAlignment(Qt.AlignCenter)
        self.spinner = SnipShotSpinner(40)
        spinner_row.addWidget(self.spinner)
        layout.addLayout(spinner_row)

        # Completion progress bar (hidden until done)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setStyleSheet(styles.progress_bar_lg())
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Status label
        self.status_label = QLabel(
            f"Sending to translator ({self.target_language})... This may take 1-2 minutes."
        )
        self.status_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['label']['size']}px; "
            "background-color: transparent;"
        )
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        # Save options — pre-added, height=0 (animated open later)
        self.save_frame = QFrame()
        self.save_frame.setMaximumHeight(0)
        self.save_frame.setStyleSheet("background-color: transparent; border: none;")

        save_layout = QVBoxLayout(self.save_frame)
        save_layout.setContentsMargins(0, SPACE["md"], 0, 0)
        save_layout.setSpacing(SPACE["sm"])

        folder_label = QLabel("Save to folder:")
        folder_label.setStyleSheet(
            f"font-weight: 500; color: {c['text']}; background-color: transparent;"
        )
        save_layout.addWidget(folder_label)

        self.folder_selector = FolderSelector()
        self.folder_selector.addItem("Unfiled", 0)
        save_layout.addWidget(self.folder_selector)

        layout.addWidget(self.save_frame)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = StyledButton("Cancel", variant="secondary")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.save_btn = StyledButton("Save to Account", variant="primary")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_btn)

        layout.addLayout(button_layout)

    # ── Helpers ────────────────────────────────────────────────────────

    def _validate_image(self, pixmap: QPixmap) -> bool:
        """
        Returns True if image is acceptable, otherwise shows error and returns False.
        """
        success, title, message = validate_qimage(pixmap.toImage())
        if not success:
            QMessageBox.warning(self, title, message)
            return False
        return True

    @staticmethod
    def _round_pixmap(pixmap: QPixmap, radius: int) -> QPixmap:
        """Return a copy of *pixmap* with rounded corners."""
        rounded = QPixmap(pixmap.size())
        rounded.fill(Qt.transparent)
        painter = QPainter(rounded)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        return rounded

    def _animate_save_frame(self):
        """Slide-open the save_frame from height 0 → natural height."""
        self.save_frame.adjustSize()
        target_h = self.save_frame.sizeHint().height()
        anim = QPropertyAnimation(self.save_frame, b"maximumHeight")
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(target_h + SPACE["md"])
        anim.setEasingCurve(QEasingCurve.OutCubic)
        self._save_anim = anim  # prevent GC
        anim.start()

    def _load_folders(self):
        """Load user's folders."""
        try:
            result = api_client.get_folders()
            if result["success"]:
                data = result["data"]
                self.folders = data if isinstance(data, list) else data.get("folders", [])
                for folder in self.folders:
                    self.folder_selector.addItem(
                        f"\U0001F4C1 {folder['name']}", folder["id"]
                    )
        except Exception:
            pass

    def _start_translation(self):
        """Start the translation process."""
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        self.captured_pixmap.save(buffer, "PNG")
        image_bytes = bytes(buffer.data())

        self.worker = TranslationWorker(
            image_bytes, self.target_language, self.translation_config
        )
        self.worker.finished.connect(self._on_translation_complete)
        self.worker.error.connect(self._on_translation_error)
        self.worker.start()

    def _on_translation_complete(self, data: dict):
        """Handle translation completion."""
        self.translation_success = True
        self.translated_bytes = data.get("image_bytes")
        c = theme.c

        self.title_label.setText("Translation Complete!")
        self.title_label.setStyleSheet(
            f"font-size: {FONT['heading']['size']}px; font-weight: {FONT['heading']['weight']}; "
            f"color: {c['success']}; background-color: transparent;"
        )

        self.spinner.stop()
        self.spinner.hide()

        self.progress.setVisible(True)
        self.progress.setValue(100)
        self.progress.setStyleSheet(styles.progress_bar_success())

        # Update preview with translated image
        if self.translated_bytes:
            translated_pixmap = QPixmap()
            translated_pixmap.loadFromData(self.translated_bytes)
            scaled = translated_pixmap.scaled(
                300, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            rounded = self._round_pixmap(scaled, SPACE["md"])
            self.preview_label.setPixmap(rounded)

        self.status_label.setText(
            f"Translation successful ({self.target_language})! Choose a folder to save."
        )

        self._animate_save_frame()
        self.save_btn.setEnabled(True)
        self.cancel_btn.setText("Close")

    def _on_translation_error(self, error: str):
        """Handle translation error."""
        c = theme.c
        self.title_label.setText("Translation Failed")
        self.title_label.setStyleSheet(
            f"font-size: {FONT['heading']['size']}px; font-weight: {FONT['heading']['weight']}; "
            f"color: {c['error']}; background-color: transparent;"
        )

        self.spinner.stop()
        self.spinner.hide()
        self.progress.setVisible(False)

        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet(
            f"color: {c['error']}; font-size: {FONT['label']['size']}px; "
            "background-color: transparent;"
        )

        self.cancel_btn.setText("Close")

    def _on_save(self):
        """Save translated image to account."""
        if not self.translated_bytes:
            return

        folder_id = self.folder_selector.currentData()
        if folder_id == 0:
            folder_id = None

        import time as _time

        filename = f"translated_{int(_time.time())}.png"

        self.save_btn.setEnabled(False)
        self.save_btn.setText("Saving...")

        self.save_worker = SaveWorker(
            self.translated_bytes,
            filename,
            folder_id,
            target_language=self.target_language,
        )
        self.save_worker.finished.connect(self._on_save_complete)
        self.save_worker.error.connect(self._on_save_error)
        self.save_worker.start()

    def _on_save_complete(self, data: dict):
        """Handle save completion."""
        c = theme.c
        self.status_label.setText("Saved to your account!")
        self.status_label.setStyleSheet(
            f"color: {c['success']}; font-size: {FONT['label']['size']}px; "
            f"font-weight: 500; background-color: transparent;"
        )

        self.save_btn.setText("Saved!")
        self.saved.emit(data)

        from PyQt5.QtCore import QTimer

        QTimer.singleShot(1500, self.accept)

    def _on_save_error(self, error: str):
        """Handle save error."""
        QMessageBox.warning(self, "Error", f"Failed to save: {error}")
        self.save_btn.setEnabled(True)
        self.save_btn.setText("Save to Account")
