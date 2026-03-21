"""
SnipShot Desktop - Translation Window

Shows translation progress and result, allows saving to folder.
"""

import copy

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QFrame, QProgressBar, QComboBox, QMessageBox, QDialog
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QBuffer, QIODevice
from PyQt5.QtGui import QPixmap

from api import api_client
from config import DEFAULT_TRANSLATION_CONFIG
from .theme import theme
from . import styles


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
        image_url: str,
        filename: str,
        folder_id: int = None,
        target_language: str = "ENG"
    ):
        super().__init__()
        self.image_url = image_url
        self.filename = filename
        self.folder_id = folder_id
        self.target_language = target_language
    
    def run(self):
        try:
            result = api_client.save_image_from_url(
                self.image_url, 
                self.filename, 
                self.folder_id,
                source_language="JPN",
                target_language=self.target_language
            )
            if result["success"]:
                self.finished.emit(result["data"])
            else:
                self.error.emit(result.get("error", "Save failed"))
        except Exception as e:
            self.error.emit(str(e))


class TranslationWindow(QDialog):
    """
    Window shown during/after translation.
    Displays progress, result, and save options.
    """
    
    saved = pyqtSignal()
    
    def __init__(self, captured_pixmap: QPixmap, parent=None, target_language: str = "ENG", translation_config: dict = None):
        super().__init__(parent)
        self.setWindowTitle("SnipShot - Translate")
        self.setMinimumSize(500, 400)
        self.setModal(True)
        
        self.captured_pixmap = captured_pixmap
        self.target_language = target_language
        self.translation_config = translation_config
        self.translated_url = None
        self.folders = []
        
        self._setup_ui()
        self._load_folders()
        self._start_translation()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("Translating Image...")
        title.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {theme.c['text']};")
        layout.addWidget(title)
        self.title_label = title
        
        # Preview
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"background-color: {theme.c['surface_alt']}; border-radius: 8px;")
        preview_frame.setFixedHeight(200)
        
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setAlignment(Qt.AlignCenter)
        
        # Show scaled preview
        self.preview_label = QLabel()
        scaled = self.captured_pixmap.scaled(
            300, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        layout.addWidget(preview_frame)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setStyleSheet(styles.progress_bar_lg())
        layout.addWidget(self.progress)
        
        # Status label
        self.status_label = QLabel(
            f"Sending to translator ({self.target_language})... This may take 1-2 minutes."
        )
        self.status_label.setStyleSheet(f"color: {theme.c['text_secondary']}; font-size: 13px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Save options (hidden initially)
        self.save_frame = QFrame()
        self.save_frame.setVisible(False)
        save_layout = QVBoxLayout(self.save_frame)
        save_layout.setContentsMargins(0, 16, 0, 0)
        save_layout.setSpacing(12)
        
        # Folder selector
        folder_label = QLabel("Save to folder:")
        folder_label.setStyleSheet(f"font-weight: 500; color: {theme.c['text']};")
        save_layout.addWidget(folder_label)
        
        self.folder_combo = QComboBox()
        self.folder_combo.setStyleSheet(styles.folder_combo())
        self.folder_combo.addItem("Unfiled", 0)
        save_layout.addWidget(self.folder_combo)
        
        layout.addWidget(self.save_frame)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(styles.dialog_cancel())
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save to Account")
        self.save_btn.setStyleSheet(styles.dialog_primary())
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def _load_folders(self):
        """Load user's folders"""
        try:
            result = api_client.get_folders()
            if result["success"]:
                self.folders = result["data"].get("folders", [])
                for folder in self.folders:
                    self.folder_combo.addItem(f"📁 {folder['name']}", folder["id"])
        except:
            pass
    
    def _start_translation(self):
        """Start the translation process"""
        # Convert pixmap to bytes
        buffer = QBuffer()
        buffer.open(QIODevice.WriteOnly)
        self.captured_pixmap.save(buffer, "PNG")
        image_bytes = bytes(buffer.data())
        
        # Start worker thread
        self.worker = TranslationWorker(image_bytes, self.target_language, self.translation_config)
        self.worker.finished.connect(self._on_translation_complete)
        self.worker.error.connect(self._on_translation_error)
        self.worker.start()
    
    def _on_translation_complete(self, data: dict):
        """Handle translation completion"""
        self.translated_url = data.get("image_url")
        
        self.title_label.setText("✓ Translation Complete!")
        self.title_label.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {theme.c['success']};")
        
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.progress.setStyleSheet(styles.progress_bar_success())
        
        self.status_label.setText(
            f"Translation successful ({self.target_language})! Choose a folder to save."
        )
        
        self.save_frame.setVisible(True)
        self.save_btn.setEnabled(True)
        self.cancel_btn.setText("Close")
    
    def _on_translation_error(self, error: str):
        """Handle translation error"""
        self.title_label.setText("✗ Translation Failed")
        self.title_label.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {theme.c['error']};")
        
        self.progress.setVisible(False)
        self.status_label.setText(f"Error: {error}")
        self.status_label.setStyleSheet(f"color: {theme.c['error']}; font-size: 13px;")
        
        self.cancel_btn.setText("Close")
    
    def _on_save(self):
        """Save translated image to account"""
        if not self.translated_url:
            return
        
        folder_id = self.folder_combo.currentData()
        if folder_id == 0:
            folder_id = None
        
        # Generate filename
        import time
        filename = f"translated_{int(time.time())}.png"
        
        self.save_btn.setEnabled(False)
        self.save_btn.setText("Saving...")
        
        self.save_worker = SaveWorker(
            self.translated_url,
            filename,
            folder_id,
            target_language=self.target_language
        )
        self.save_worker.finished.connect(self._on_save_complete)
        self.save_worker.error.connect(self._on_save_error)
        self.save_worker.start()
    
    def _on_save_complete(self, data: dict):
        """Handle save completion"""
        self.status_label.setText("✓ Saved to your account!")
        self.status_label.setStyleSheet(f"color: {theme.c['success']}; font-size: 13px; font-weight: 500;")
        
        self.save_btn.setText("Saved!")
        self.saved.emit()
        
        # Close after short delay
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1500, self.accept)
    
    def _on_save_error(self, error: str):
        """Handle save error"""
        QMessageBox.warning(self, "Error", f"Failed to save: {error}")
        self.save_btn.setEnabled(True)
        self.save_btn.setText("Save to Account")
