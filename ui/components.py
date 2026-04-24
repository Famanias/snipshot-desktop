# CHANGELOG
# ─────────────────────────────────────────────────────────────────────
# - NEW file: reusable widget components
# - StyledButton(QPushButton) — primary/secondary/ghost/danger variants
# - SnipShotSpinner(QWidget)  — animated 8-arc spinner
# - FolderSelector(QWidget)   — custom themed folder dropdown
# ─────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy, QGraphicsOpacityEffect,
)
from PyQt5.QtCore import Qt, QTimer, QSize, QRectF, pyqtSignal, QEvent, QPoint
from PyQt5.QtGui import QPainter, QPen, QColor, QFont

from .theme import theme
from .styles import SPACE, FONT


# ═════════════════════════════════════════════════════════════════════════
# StyledButton
# ═════════════════════════════════════════════════════════════════════════

class StyledButton(QPushButton):
    """
    A QPushButton with built-in variant styling.

    Variants: "primary", "secondary", "ghost", "danger"
    """

    VARIANTS = ["primary", "secondary", "ghost", "danger"]

    def __init__(self, label: str, variant: str = "primary", parent=None):
        super().__init__(label, parent)
        if variant not in self.VARIANTS:
            variant = "primary"
        self._variant = variant
        self.setCursor(Qt.PointingHandCursor)
        self._apply_variant_style()
        theme.theme_changed.connect(self._apply_variant_style)

    @property
    def variant(self) -> str:
        return self._variant

    @variant.setter
    def variant(self, v: str):
        if v in self.VARIANTS:
            self._variant = v
            self._apply_variant_style()

    def _apply_variant_style(self, _mode=None):
        c = theme.c
        if self._variant == "primary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['primary']};
                    color: white;
                    border: none;
                    border-radius: {SPACE['sm']}px;
                    padding: {SPACE['md']}px {SPACE['lg']}px;
                    font-size: {FONT['body']['size']}px;
                    font-weight: 600;
                    min-height: 44px;
                }}
                QPushButton:hover {{
                    background-color: {c['primary_dark']};
                }}
                QPushButton:pressed {{
                    background-color: {c['primary_dark']};
                }}
                QPushButton:disabled {{
                    background-color: {c['disabled_bg']};
                    color: {c['disabled_text']};
                }}
            """)
        elif self._variant == "secondary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['surface_alt']};
                    color: {c['text']};
                    border: 1px solid {c['border']};
                    border-radius: {SPACE['sm']}px;
                    padding: {SPACE['md']}px {SPACE['lg']}px;
                    font-size: {FONT['body']['size']}px;
                    font-weight: 500;
                    min-height: 44px;
                }}
                QPushButton:hover {{
                    background-color: {c['hover']};
                    border-color: {c['input_border']};
                }}
                QPushButton:pressed {{
                    background-color: {c['border']};
                }}
                QPushButton:disabled {{
                    background-color: {c['disabled_bg']};
                    color: {c['disabled_text']};
                }}
            """)
        elif self._variant == "ghost":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {c['primary']};
                    border: none;
                    border-radius: {SPACE['sm']}px;
                    padding: {SPACE['sm']}px {SPACE['md']}px;
                    font-size: {FONT['body']['size']}px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {c['primary_subtle']};
                }}
                QPushButton:pressed {{
                    background-color: {c['primary_light']};
                }}
                QPushButton:disabled {{
                    background-color: transparent;
                    color: {c['disabled_text']};
                }}
            """)
        elif self._variant == "danger":
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {c['error']};
                    color: white;
                    border: none;
                    border-radius: {SPACE['sm']}px;
                    padding: {SPACE['md']}px {SPACE['lg']}px;
                    font-size: {FONT['body']['size']}px;
                    font-weight: 600;
                    min-height: 44px;
                }}
                QPushButton:hover {{
                    background-color: #DC2626;
                }}
                QPushButton:pressed {{
                    background-color: #B91C1C;
                }}
                QPushButton:disabled {{
                    background-color: {c['disabled_bg']};
                    color: {c['disabled_text']};
                }}
            """)


# ═════════════════════════════════════════════════════════════════════════
# SnipShotSpinner
# ═════════════════════════════════════════════════════════════════════════

class SnipShotSpinner(QWidget):
    """Animated 8-arc segment spinner."""

    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._size = size
        self._angle = 0
        self._num_segments = 8
        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(80)

    def _rotate(self):
        self._angle = (self._angle + 1) % self._num_segments
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        c = theme.c
        primary = QColor(c["primary"])
        border_c = QColor(c["border"])

        margin = 4
        rect = QRectF(margin, margin, self._size - 2 * margin, self._size - 2 * margin)
        span = 360 // self._num_segments
        gap = 8  # degrees gap between arcs

        for i in range(self._num_segments):
            if i == self._angle:
                pen = QPen(primary, 3)
            else:
                pen = QPen(border_c, 2)
            painter.setPen(pen)
            start_angle = i * span + gap // 2
            arc_span = span - gap
            painter.drawArc(rect, start_angle * 16, arc_span * 16)

        painter.end()

    def start(self):
        if not self._timer.isActive():
            self._timer.start(80)

    def stop(self):
        self._timer.stop()


# ═════════════════════════════════════════════════════════════════════════
# FolderSelector
# ═════════════════════════════════════════════════════════════════════════

class _FolderDropdownItem(QPushButton):
    """Single item inside the FolderSelector dropdown."""

    item_clicked = pyqtSignal(object, str)  # data, display_text

    def __init__(self, display_text: str, data, parent=None):
        super().__init__(display_text, parent)
        self._data = data
        self._display = display_text
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self._apply_style()
        self.clicked.connect(lambda: self.item_clicked.emit(self._data, self._display))

    def _apply_style(self):
        c = theme.c
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {c['text']};
                border: none;
                border-radius: {SPACE['xs']}px;
                padding: {SPACE['sm']}px {SPACE['md']}px;
                font-size: {FONT['body']['size']}px;
                text-align: left;
            }}
            QPushButton:hover {{
                background-color: {c['hover']};
            }}
        """)


class FolderSelector(QWidget):
    """
    Custom themed folder dropdown to replace QComboBox.
    Shows a styled button; on click opens a QFrame dropdown.
    """

    selection_changed = pyqtSignal(object)  # emits the data value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[str, object]] = []
        self._current_data = None
        self._current_text = "Select folder..."

        self._btn = QPushButton(self._current_text)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setFixedHeight(44)
        self._btn.clicked.connect(self._toggle_dropdown)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._btn)

        self._dropdown: QFrame | None = None
        self._apply_style()
        theme.theme_changed.connect(self._apply_style)

    def _apply_style(self, _mode=None):
        c = theme.c
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c['input_bg']};
                color: {c['text']};
                border: 1px solid {c['input_border']};
                border-radius: {SPACE['sm']}px;
                padding: {SPACE['sm']}px {SPACE['md']}px;
                font-size: {FONT['body']['size']}px;
                text-align: left;
            }}
            QPushButton:hover {{
                border-color: {c['primary']};
            }}
        """)

    def addItem(self, text: str, data=None):
        self._items.append((text, data))
        if len(self._items) == 1:
            self._current_text = text
            self._current_data = data
            self._btn.setText(text)

    def currentData(self):
        return self._current_data

    def clear(self):
        self._items.clear()
        self._current_data = None
        self._current_text = "Select folder..."
        self._btn.setText(self._current_text)

    def _toggle_dropdown(self):
        if self._dropdown and self._dropdown.isVisible():
            self._close_dropdown()
            return
        self._open_dropdown()

    def _open_dropdown(self):
        self._close_dropdown()

        c = theme.c
        self._dropdown = QFrame(self.window())
        self._dropdown.setStyleSheet(f"""
            QFrame {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-radius: {SPACE['sm']}px;
            }}
        """)

        dl = QVBoxLayout(self._dropdown)
        dl.setContentsMargins(SPACE['xs'], SPACE['xs'], SPACE['xs'], SPACE['xs'])
        dl.setSpacing(0)

        for text, data in self._items:
            item = _FolderDropdownItem(text, data, self._dropdown)
            item.item_clicked.connect(self._on_item_selected)
            dl.addWidget(item)

        self._dropdown.adjustSize()

        # Position below the button
        global_pos = self._btn.mapToGlobal(QPoint(0, self._btn.height()))
        parent_pos = self.window().mapFromGlobal(global_pos)
        self._dropdown.move(parent_pos)
        self._dropdown.setFixedWidth(self._btn.width())
        self._dropdown.raise_()
        self._dropdown.show()

        # Install event filter to close on outside click
        self.window().installEventFilter(self)

    def _close_dropdown(self):
        if self._dropdown:
            self.window().removeEventFilter(self)
            self._dropdown.hide()
            self._dropdown.deleteLater()
            self._dropdown = None

    def _on_item_selected(self, data, text):
        self._current_data = data
        self._current_text = text
        self._btn.setText(text)
        self._close_dropdown()
        self.selection_changed.emit(data)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and self._dropdown:
            # Close if the click is outside the dropdown
            global_pos = event.globalPos() if hasattr(event, 'globalPos') else event.globalPosition().toPoint()
            dropdown_rect = self._dropdown.geometry()
            dropdown_global = self._dropdown.mapToGlobal(QPoint(0, 0))
            from PyQt5.QtCore import QRect
            actual_rect = QRect(dropdown_global, self._dropdown.size())
            if not actual_rect.contains(global_pos):
                self._close_dropdown()
        return False
