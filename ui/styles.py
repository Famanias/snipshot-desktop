# CHANGELOG
# ─────────────────────────────────────────────────────────────────────
# - Added SPACE dict (base-8 grid: xs=4, sm=8, md=16, lg=24, xl=32, xxl=48)
# - Added FONT dict (display/heading/body/label/caption/hint scale)
# - Removed primary_button(), text_button(), local_mode_button(),
#   dialog_primary(), dialog_cancel() — replaced by StyledButton
# - Removed outline_button(), close_button(), shortcut_button(),
#   load_more_button(), back_button(), new_folder_button() — use StyledButton
# - Kept auth_container(), input_field(), progress_bar_success(),
#   progress_bar_lg(), folder_card(), image_card(), settings_input(),
#   nav_button(), sidebar_action_button(), theme_toggle_button(),
#   folder_combo(), preview_scroll(), dialog_input()
# - Updated all style helpers to use SPACE / FONT constants
# - Added card() — generic elevated surface card style
# - Added get_tooltip_stylesheet() — for QApplication-level QToolTip
# - Added apply_card_shadow() — QGraphicsDropShadowEffect helper
# - Removed CSS box-shadow from auth_container() (handled by apply_card_shadow)
# - Added password_strength_bar() for register page
# ─────────────────────────────────────────────────────────────────────

from PyQt5.QtWidgets import QWidget, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor, QIcon
import os

from .theme import theme


# ═════════════════════════════════════════════════════════════════════════
# Design-system constants
# ═════════════════════════════════════════════════════════════════════════

SPACE = {"xs": 4, "sm": 8, "md": 16, "lg": 24, "xl": 32, "xxl": 48}

FONT = {
    "display":  {"size": 28, "weight": 700},
    "heading":  {"size": 18, "weight": 600},
    "body":     {"size": 14, "weight": 400},
    "label":    {"size": 13, "weight": 600},
    "caption":  {"size": 12, "weight": 400},
    "hint":     {"size": 12, "weight": 400},
}


def _c():
    """Shortcut to the current colour dict."""
    return theme.c


# ═════════════════════════════════════════════════════════════════════════
# Elevation helper
# ═════════════════════════════════════════════════════════════════════════

def apply_card_shadow(widget: QWidget):
    """Apply a subtle drop shadow to a card / dialog frame."""
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(24)
    shadow.setOffset(0, 4)
    alpha = 82 if theme.is_dark else 20  # 0.32*255≈82, 0.08*255≈20
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


# ═════════════════════════════════════════════════════════════════════════
# Global application stylesheet
# ═════════════════════════════════════════════════════════════════════════

def get_main_stylesheet() -> str:
    c = _c()
    f_body = FONT["body"]
    f_caption = FONT["caption"]
    return f"""
    /* ============== Global ============== */
    QMainWindow, QDialog {{
        background-color: {c['bg']};
    }}

    QWidget {{
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        font-size: {f_body['size']}px;
        color: {c['text']};
    }}

    /* ============== Buttons ============== */
    QPushButton {{
        background-color: {c['primary']};
        color: white;
        border: none;
        border-radius: {SPACE['sm']}px;
        padding: {SPACE['md']}px {SPACE['lg']}px;
        font-weight: 600;
        font-size: {f_body['size']}px;
        min-height: {SPACE['lg']}px;
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

    QPushButton[class="secondary"] {{
        background-color: transparent;
        color: {c['primary']};
        border: 1px solid {c['border']};
    }}

    QPushButton[class="secondary"]:hover {{
        background-color: {c['primary_light']};
        border-color: {c['primary']};
    }}

    QPushButton[class="danger"] {{
        background-color: {c['error']};
    }}

    QPushButton[class="danger"]:hover {{
        background-color: #DC2626;
    }}

    QPushButton[class="icon"] {{
        background-color: transparent;
        border: none;
        padding: {SPACE['sm']}px;
        border-radius: 20px;
    }}

    QPushButton[class="icon"]:hover {{
        background-color: {c['hover']};
    }}

    /* ============== Input Fields ============== */
    QLineEdit {{
        background-color: {c['input_bg']};
        border: 1px solid {c['input_border']};
        border-radius: {SPACE['sm']}px;
        padding: {SPACE['md']}px {SPACE['md']}px;
        font-size: {f_body['size']}px;
        min-height: 20px;
        color: {c['text']};
    }}

    QLineEdit:focus {{
        border: 2px solid {c['primary']};
        padding: {SPACE['md'] - 1}px {SPACE['md'] - 1}px;
    }}

    QLineEdit:disabled {{
        background-color: {c['surface_alt']};
        color: {c['disabled_text']};
    }}

    QLineEdit[class="error"] {{
        border: 2px solid {c['error']};
    }}

    /* ============== Labels ============== */
    QLabel {{
        color: {c['text']};
        background-color: transparent;
    }}

    QLabel[class="title"] {{
        font-size: {FONT['display']['size']}px;
        font-weight: {FONT['display']['weight']};
    }}

    QLabel[class="subtitle"] {{
        font-size: {f_body['size']}px;
        color: {c['text_secondary']};
    }}

    QLabel[class="error"] {{
        color: {c['error']};
        font-size: {f_caption['size']}px;
    }}

    QLabel[class="link"] {{
        color: {c['primary']};
    }}

    /* ============== Frames ============== */
    QFrame {{
        background-color: {c['surface']};
        border: none;
    }}

    QFrame[class="card"] {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: {SPACE['sm']}px;
    }}

    QFrame[class="sidebar"] {{
        background-color: {c['sidebar']};
        border-right: 1px solid {c['border']};
    }}

    /* ============== Scroll Area ============== */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}

    QScrollBar:vertical {{
        background-color: {c['scrollbar_bg']};
        width: {SPACE['sm']}px;
        border-radius: {SPACE['xs']}px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar']};
        border-radius: {SPACE['xs']}px;
        min-height: 40px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {c['scrollbar_hover']};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        background-color: {c['scrollbar_bg']};
        height: {SPACE['sm']}px;
        border-radius: {SPACE['xs']}px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c['scrollbar']};
        border-radius: {SPACE['xs']}px;
        min-width: 40px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background-color: {c['scrollbar_hover']};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ============== List Widget ============== */
    QListWidget {{
        background-color: transparent;
        border: none;
        outline: none;
    }}

    QListWidget::item {{
        padding: {SPACE['md']}px {SPACE['md']}px;
        border-radius: 0px;
        border-left: 3px solid transparent;
    }}

    QListWidget::item:hover {{
        background-color: {c['hover']};
    }}

    QListWidget::item:selected {{
        background-color: {c['primary_light']};
        border-left: 3px solid {c['primary']};
        color: {c['text']};
    }}

    /* ============== Menu ============== */
    QMenu {{
        background-color: {c['surface']};
        color: {c['text']};
        border: 1px solid {c['border']};
        padding: 4px 0px;
    }}

    QMenu::item {{
        background-color: transparent;
        padding: {SPACE['sm']}px {SPACE['xl']}px;
        color: {c['text']};
    }}

    QMenu::item:selected {{
        background-color: {c['hover']};
        color: {c['text']};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {c['border']};
        margin: 4px 0px;
    }}

    /* ============== Progress Bar ============== */
    QProgressBar {{
        background-color: {c['primary_light']};
        border: none;
        border-radius: {SPACE['xs']}px;
        height: {SPACE['xs']}px;
        text-align: center;
    }}

    QProgressBar::chunk {{
        background-color: {c['primary']};
        border-radius: {SPACE['xs']}px;
    }}

    /* ============== Message Box ============== */
    QMessageBox {{
        background-color: {c['surface']};
    }}

    QMessageBox QLabel {{
        color: {c['text']};
        font-size: {f_body['size']}px;
    }}

    /* ============== Tool Tip ============== */
    QToolTip {{
        background-color: {c['tooltip_bg']};
        color: {c['tooltip_text']};
        border: none;
        padding: {SPACE['sm']}px {SPACE['md']}px;
        border-radius: 6px;
        font-size: {f_caption['size']}px;
    }}

    /* ============== Tab Widget ============== */
    QTabWidget::pane {{
        border: none;
        background-color: {c['surface']};
    }}

    QTabBar::tab {{
        background-color: transparent;
        padding: {SPACE['md']}px {SPACE['lg']}px;
        border-bottom: 2px solid transparent;
        color: {c['text_secondary']};
    }}

    QTabBar::tab:selected {{
        color: {c['primary']};
        border-bottom: 2px solid {c['primary']};
    }}

    QTabBar::tab:hover:!selected {{
        color: {c['text']};
    }}

    /* ============== Combo Box ============== */
    QComboBox {{
        background-color: {c['input_bg']};
        border: 1px solid {c['input_border']};
        border-radius: {SPACE['sm']}px;
        padding: {SPACE['sm']}px {SPACE['md']}px;
        color: {c['text']};
    }}

    QComboBox:focus {{
        border-color: {c['primary']};
    }}

    QComboBox::drop-down {{
        border: none;
    }}

    QComboBox QAbstractItemView {{
        background-color: {c['surface']};
        border: 1px solid {c['border']};
        color: {c['text']};
        selection-background-color: {c['primary_light']};
        selection-color: {c['text']};
    }}

    /* ============== Spin Box ============== */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c['input_bg']};
        border: 1px solid {c['input_border']};
        border-radius: {SPACE['sm']}px;
        padding: {SPACE['sm']}px {SPACE['md']}px;
        color: {c['text']};
    }}

    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {c['primary']};
    }}

    /* ============== Input Dialog ============== */
    QInputDialog {{
        background-color: {c['surface']};
    }}
    """


def get_tooltip_stylesheet() -> str:
    """Standalone QToolTip stylesheet for QApplication level."""
    c = _c()
    return f"""
    QToolTip {{
        background-color: {c['tooltip_bg']};
        color: {c['tooltip_text']};
        border: none;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: {FONT['caption']['size']}px;
    }}
    """


# ═════════════════════════════════════════════════════════════════════════
# Reusable inline-style helpers
# ═════════════════════════════════════════════════════════════════════════

# ── Auth screens ───────────────────────────────────────────────────────

def auth_container():
    c = _c()
    return f"""
        QFrame#authContainer {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: {SPACE['md']}px;
        }}
    """


def input_field():
    c = _c()
    return f"""
        QLineEdit {{
            padding: {SPACE['md']}px {SPACE['md']}px;
            border: 1px solid {c['input_border']};
            border-radius: {SPACE['sm']}px;
            font-size: {FONT['body']['size']}px;
            background-color: {c['input_bg']};
            color: {c['text']};
        }}
        QLineEdit:focus {{
            border: 2px solid {c['primary']};
            padding: {SPACE['md'] - 1}px {SPACE['md'] - 1}px;
        }}
    """


# ── Cards ──────────────────────────────────────────────────────────────

def card():
    """Generic elevated surface card style."""
    c = _c()
    return f"""
        QFrame {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: {SPACE['sm']}px;
        }}
    """


def folder_card():
    c = _c()
    return f"""
        FolderCard {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 12px;
        }}
        FolderCard:hover {{
            background-color: {c['hover']};
            border-color: {c['primary']};
        }}
        FolderCard[dragOver="true"] {{
            background-color: {c['primary_light']};
            border: 2px dashed {c['primary']};
        }}
    """


def image_card():
    c = _c()
    return f"""
        ImageCard {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 12px;
        }}
        ImageCard:hover {{
            background-color: {c['hover']};
            border-color: {c['primary']};
        }}
        ImageCard[selected="true"] {{
            background-color: {c['primary_light']};
            border: 2px solid {c['primary']};
            border-radius: 12px;
        }}
        ImageCard QFrame#preview_box {{
            background-color: {c['bg']};
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        }}
        ImageCard QFrame#info_section {{
            background-color: {c['surface_alt']};
            border-bottom-left-radius: 12px;
            border-bottom-right-radius: 12px;
            border-top-left-radius: 0px;
            border-top-right-radius: 0px;
        }}
        ImageCard[selected="true"] QFrame#preview_box {{
            background-color: transparent;
        }}
        ImageCard[selected="true"] QFrame#info_section {{
            background-color: transparent;
        }}
    """


# ── Dashboard ──────────────────────────────────────────────────────────

def sidebar_action_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: {c['surface']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: {SPACE['lg']}px;
            padding: {SPACE['md']}px {SPACE['lg']}px;
            font-size: {FONT['body']['size']}px;
            font-weight: 500;
            text-align: left;
        }}
        QPushButton:hover {{
            border-color: {c['primary']};
        }}
    """


def nav_button(active: bool):
    c = _c()
    if active:
        return f"""
            QPushButton {{
                background-color: {c['nav_active_bg']};
                color: {c['nav_active_text']};
                border: none;
                border-radius: {SPACE['lg']}px;
                padding: {SPACE['sm']}px {SPACE['md']}px;
                font-size: {FONT['body']['size']}px;
                text-align: left;
                font-weight: 500;
            }}
        """
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['text_secondary']};
            border: none;
            border-radius: {SPACE['lg']}px;
            padding: {SPACE['sm']}px {SPACE['md']}px;
            font-size: {FONT['body']['size']}px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: {c['hover']};
        }}
    """


# ── Dialogs ────────────────────────────────────────────────────────────

def dialog_input():
    c = _c()
    return f"""
        QLineEdit {{
            padding: {SPACE['sm']}px {SPACE['md']}px;
            border: 1px solid {c['input_border']};
            border-radius: {SPACE['sm']}px;
            font-size: {FONT['body']['size']}px;
            background-color: {c['input_bg']};
            color: {c['text']};
        }}
        QLineEdit:focus {{
            border: 2px solid {c['primary']};
        }}
    """


# ── Preview dialog ─────────────────────────────────────────────────────

def preview_scroll():
    c = _c()
    return f"""
        QScrollArea {{
            border: 1px solid {c['border']};
            border-radius: {SPACE['sm']}px;
            background-color: {c['surface_alt']};
        }}
    """


def progress_bar_lg():
    c = _c()
    return f"""
        QProgressBar {{
            background-color: {c['primary_light']};
            border: none;
            border-radius: {SPACE['xs']}px;
            height: {SPACE['sm']}px;
        }}
        QProgressBar::chunk {{
            background-color: {c['primary']};
            border-radius: {SPACE['xs']}px;
        }}
    """


def progress_bar_success():
    c = _c()
    return f"""
        QProgressBar {{
            background-color: {c['success_bg']};
            border: none;
            border-radius: {SPACE['xs']}px;
            height: {SPACE['sm']}px;
        }}
        QProgressBar::chunk {{
            background-color: {c['success']};
            border-radius: {SPACE['xs']}px;
        }}
    """


# ── Settings ───────────────────────────────────────────────────────────

def settings_input():
    c = _c()
    return f"""
        QSpinBox, QDoubleSpinBox, QComboBox {{
            padding: {SPACE['sm']}px {SPACE['sm']}px;
            border: 1px solid {c['input_border']};
            border-radius: {SPACE['sm']}px;
            font-size: {FONT['label']['size']}px;
            min-width: 240px;
            background: {c['input_bg']};
            color: {c['text']};
        }}
        QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {{
            border-color: {c['primary']};
        }}
        QComboBox QAbstractItemView {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            color: {c['text']};
            selection-background-color: {c['primary_light']};
        }}
    """


def folder_combo():
    c = _c()
    return f"""
        QComboBox {{
            padding: {SPACE['sm']}px {SPACE['md']}px;
            border: 1px solid {c['input_border']};
            border-radius: {SPACE['sm']}px;
            font-size: {FONT['body']['size']}px;
            background-color: {c['input_bg']};
            color: {c['text']};
        }}
        QComboBox QAbstractItemView {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            color: {c['text']};
        }}
    """


# ── Theme toggle ───────────────────────────────────────────────────────

def theme_toggle_button(active: bool):
    c = _c()
    if active:
        return f"""
            QPushButton {{
                background-color: {c['primary']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: {SPACE['sm']}px {SPACE['lg']}px;
                font-weight: {FONT['label']['weight']};
                font-size: {FONT['label']['size']}px;
            }}
        """
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['text_secondary']};
            border: none;
            border-radius: 6px;
            padding: {SPACE['sm']}px {SPACE['lg']}px;
            font-size: {FONT['label']['size']}px;
        }}
        QPushButton:hover {{
            background-color: {c['hover']};
        }}
    """


# ── Password-strength bar ─────────────────────────────────────────────

def password_strength_bar(level: int):
    """Return stylesheet for the password strength QProgressBar (0-4)."""
    colors = {
        0: _c()["disabled_bg"],
        1: _c()["error"],
        2: "#F59E0B",
        3: _c()["primary"],
        4: _c()["success"],
    }
    colour = colors.get(level, colors[0])
    return f"""
        QProgressBar {{
            background-color: {_c()['surface_alt']};
            border: none;
            border-radius: 2px;
            height: {SPACE['xs']}px;
        }}
        QProgressBar::chunk {{
            background-color: {colour};
            border-radius: 2px;
        }}
    """


# ── Icon helper ────────────────────────────────────────────────────────

def load_icon(icon_name: str) -> QIcon:
    """
    Load an SVG icon from the ui/icons folder.
    Automatically adjusts icon color based on current theme:
    - Dark mode: uses light/grey icons (E3E3E3)
    - Light mode: uses dark icons (212121)
    
    Args:
        icon_name: The icon filename (can have E3E3E3 or 212121, will be normalized)
    
    Returns:
        A QIcon object, or empty QIcon if file not found
    """
    from .theme import theme
    from utils.helpers import resource_path
    
    # Normalize the icon name based on current theme
    if theme.is_dark:
        # Dark mode: use light-colored icons (E3E3E3)
        if "212121" in icon_name:
            icon_name = icon_name.replace("212121", "E3E3E3")
    else:
        # Light mode: use dark-colored icons (212121)
        if "E3E3E3" in icon_name:
            icon_name = icon_name.replace("E3E3E3", "212121")
    
    icon_path = resource_path(os.path.join("ui", "icons", icon_name))
    
    if os.path.exists(icon_path):
        return QIcon(icon_path)
    else:
        print(f"Warning: Icon not found at {icon_path}")
        return QIcon()


CAPTURE_STYLESHEET = """
QWidget#captureOverlay {
    background-color: rgba(0, 0, 0, 0.3);
}
"""
