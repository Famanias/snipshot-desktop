# CHANGELOG
# ─────────────────────────────────────────────────────────────────────
# - NEW file: reusable widget components
# - StyledButton(QPushButton) — primary/secondary/ghost/danger variants
# - SnipShotSpinner(QWidget)  — animated 8-arc spinner
# - FolderSelector(QWidget)   — custom themed folder dropdown
# ─────────────────────────────────────────────────────────────────────

import time

from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QSizePolicy, QGraphicsOpacityEffect, QListWidget,
    QListWidgetItem, QApplication,
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
                    padding: {SPACE['sm']}px {SPACE['lg']}px;
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
                    padding: {SPACE['sm']}px {SPACE['lg']}px;
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
                    padding: {SPACE['sm']}px {SPACE['lg']}px;
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

# Dropdown configuration constants for FolderSelector
ITEM_HEIGHT = 40             # Height of each list item in logical pixels
MAX_VISIBLE_ITEMS = 5        # Max items visible before scrolling is enabled
MAX_HEIGHT = ITEM_HEIGHT * MAX_VISIBLE_ITEMS  # Capped dropdown height (200px)
REOPEN_DEBOUNCE_S = 0.15     # Debounce time (150ms) to avoid click-to-close bounce
VERTICAL_PADDING = 8         # Total top/bottom padding (SPACE['xs'] * 2)
BORDER_HEIGHT = 2            # Total top/bottom border thickness (1px each)
PADDING_BORDER_OFFSET = VERTICAL_PADDING + BORDER_HEIGHT # 10px offset for layout height


class FolderDropdownList(QListWidget):
    """
    Styled dropdown list that overlays using Qt.Popup.
    Handles keyboard selection and avoids boundary clipping.
    """

    closed = pyqtSignal()
    item_chosen = pyqtSignal(object, str)  # emits (data, text)

    def __init__(self, parent=None):
        super().__init__(parent)
        # Ensure the list behaves as a popup window by adding the Qt.Popup flag to existing flags
        self.setWindowFlags(self.windowFlags() | Qt.Popup)
        self.setObjectName("FolderDropdownList")
        self.setFocusPolicy(Qt.StrongFocus)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.itemClicked.connect(self._on_item_activated)
        self.itemActivated.connect(self._on_item_activated)
        self._is_closing = False
        self._apply_style()

    def _apply_style(self):
        c = theme.c
        self.setStyleSheet(f"""
            QListWidget#FolderDropdownList {{
                background-color: {c['surface']};
                border: 1px solid {c['border']};
                border-radius: {SPACE['sm']}px;
                outline: none;
                padding: {SPACE['xs']}px;
            }}
            QListWidget#FolderDropdownList::item {{
                color: {c['text']};
                border: none;
                border-radius: {SPACE['xs']}px;
                padding: 0px {SPACE['md']}px;
                font-size: {FONT['body']['size']}px;
            }}
            QListWidget#FolderDropdownList::item:hover {{
                background-color: {c['hover']};
            }}
            QListWidget#FolderDropdownList::item:selected {{
                background-color: {c['primary_light']};
                color: {c['text']};
            }}
        """)

    def _on_item_activated(self, item):
        if not item:
            return
        data = item.data(Qt.UserRole)
        text = item.text()
        self.item_chosen.emit(data, text)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            current = self.currentItem()
            if current:
                self._on_item_activated(current)
            event.accept()
        elif event.key() == Qt.Key_Escape:
            self.close()
            event.accept()
        else:
            super().keyPressEvent(event)

    def hideEvent(self, event):
        if not self._is_closing:
            self._is_closing = True
            self.closed.emit()
        super().hideEvent(event)


class FolderSelector(QWidget):
    """
    Custom themed folder dropdown to replace QComboBox.
    Shows a styled button; on click opens a FolderDropdownList.
    """

    selection_changed = pyqtSignal(object)  # emits the data value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[tuple[str, object]] = []
        self._current_data = None
        self._current_text = "Select folder..."
        self._last_close_time = 0.0

        self._btn = QPushButton(self._current_text)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.setFixedHeight(44)
        self._btn.clicked.connect(self._toggle_dropdown)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._btn)

        self._dropdown: FolderDropdownList | None = None
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
        if time.time() - self._last_close_time < REOPEN_DEBOUNCE_S:
            return
        if self._dropdown and self._dropdown.isVisible():
            self._close_dropdown()
            return
        self._open_dropdown()

    def _open_dropdown(self):
        self._close_dropdown()

        # Create a popup list without a parent so it receives mouse events.
        self._dropdown = FolderDropdownList()
        self._dropdown.item_chosen.connect(self._on_item_selected)
        self._dropdown.closed.connect(self._close_dropdown)

        # Populate items
        # Ensure the popup appears above other widgets
        self._dropdown.raise_()
        for text, data in self._items:
            item = QListWidgetItem(text, self._dropdown)
            item.setData(Qt.UserRole, data)
            item.setSizeHint(QSize(0, ITEM_HEIGHT))
            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self._dropdown.addItem(item)

        # Calculate height dynamically with capping & scaling safety
        num_items = len(self._items)
        total_height = num_items * ITEM_HEIGHT + PADDING_BORDER_OFFSET
        max_height = MAX_HEIGHT + PADDING_BORDER_OFFSET
        dropdown_height = min(total_height, max_height)

        self._dropdown.setFixedWidth(self._btn.width())
        self._dropdown.setFixedHeight(dropdown_height)

        # Viewport protection (flip upward if dropdown would overflow the screen bottom)
        global_pos = self._btn.mapToGlobal(QPoint(0, self._btn.height()))
        screen = QApplication.desktop().screenGeometry(global_pos)

        if global_pos.y() + dropdown_height > screen.bottom():
            # Open above the button
            global_pos = self._btn.mapToGlobal(QPoint(0, -dropdown_height))

        self._dropdown.move(global_pos)
        self._dropdown.show()

        # Pre-select the item matches self._current_data using Row indices
        for i in range(self._dropdown.count()):
            item = self._dropdown.item(i)
            if item.data(Qt.UserRole) == self._current_data:
                self._dropdown.setCurrentRow(i)
                break

        self._dropdown.setFocus()

    def _close_dropdown(self):
        if self._dropdown:
            self._last_close_time = time.time()
            try:
                self._dropdown.closed.disconnect(self._close_dropdown)
            except TypeError:
                pass
            self._dropdown.close()
            self._dropdown.deleteLater()
            self._dropdown = None

    def _on_item_selected(self, data, text):
        self._current_data = data
        self._current_text = text
        self._btn.setText(text)
        self._close_dropdown()
        self.selection_changed.emit(data)
