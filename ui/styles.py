"""
SnipShot Desktop - Dynamic Stylesheets

Theme-aware stylesheet generation.  All colour values come from the
active ThemeManager palette so that a single toggle switches the
entire application between light and dark mode.
"""

from .theme import theme


def _c():
    """Shortcut to the current colour dict."""
    return theme.c


# ═════════════════════════════════════════════════════════════════════════
# Global application stylesheet
# ═════════════════════════════════════════════════════════════════════════

def get_main_stylesheet() -> str:
    c = _c()
    return f"""
    /* ============== Global ============== */
    QMainWindow, QDialog {{
        background-color: {c['bg']};
    }}

    QWidget {{
        font-family: 'Segoe UI', 'Roboto', sans-serif;
        font-size: 13px;
        color: {c['text']};
    }}

    /* ============== Buttons ============== */
    QPushButton {{
        background-color: {c['primary']};
        color: white;
        border: none;
        border-radius: 6px;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 14px;
        min-height: 24px;
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
        padding: 8px;
        border-radius: 20px;
    }}

    QPushButton[class="icon"]:hover {{
        background-color: {c['hover']};
    }}

    /* ============== Input Fields ============== */
    QLineEdit {{
        background-color: {c['input_bg']};
        border: 1px solid {c['input_border']};
        border-radius: 6px;
        padding: 12px 16px;
        font-size: 14px;
        min-height: 20px;
        color: {c['text']};
    }}

    QLineEdit:focus {{
        border: 2px solid {c['primary']};
        padding: 11px 15px;
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
        font-size: 24px;
        font-weight: 600;
    }}

    QLabel[class="subtitle"] {{
        font-size: 14px;
        color: {c['text_secondary']};
    }}

    QLabel[class="error"] {{
        color: {c['error']};
        font-size: 12px;
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
        border-radius: 8px;
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
        width: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:vertical {{
        background-color: {c['scrollbar']};
        border-radius: 4px;
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
        height: 8px;
        border-radius: 4px;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {c['scrollbar']};
        border-radius: 4px;
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
        padding: 12px 16px;
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
        border: 1px solid {c['border']};
        border-radius: 4px;
        padding: 8px 0;
    }}

    QMenu::item {{
        padding: 8px 32px;
        color: {c['text']};
    }}

    QMenu::item:selected {{
        background-color: {c['hover']};
    }}

    /* ============== Progress Bar ============== */
    QProgressBar {{
        background-color: {c['primary_light']};
        border: none;
        border-radius: 4px;
        height: 4px;
        text-align: center;
    }}

    QProgressBar::chunk {{
        background-color: {c['primary']};
        border-radius: 4px;
    }}

    /* ============== Message Box ============== */
    QMessageBox {{
        background-color: {c['surface']};
    }}

    QMessageBox QLabel {{
        color: {c['text']};
        font-size: 14px;
    }}

    /* ============== Tool Tip ============== */
    QToolTip {{
        background-color: {c['tooltip_bg']};
        color: {c['tooltip_text']};
        border: none;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 12px;
    }}

    /* ============== Tab Widget ============== */
    QTabWidget::pane {{
        border: none;
        background-color: {c['surface']};
    }}

    QTabBar::tab {{
        background-color: transparent;
        padding: 12px 24px;
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
        border-radius: 6px;
        padding: 8px 12px;
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
        border-radius: 6px;
        padding: 8px 12px;
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
            border-radius: 12px;
        }}
    """


def input_field():
    c = _c()
    return f"""
        QLineEdit {{
            padding: 12px 16px;
            border: 1px solid {c['input_border']};
            border-radius: 6px;
            font-size: 14px;
            background-color: {c['input_bg']};
            color: {c['text']};
        }}
        QLineEdit:focus {{
            border: 2px solid {c['primary']};
            padding: 11px 15px;
        }}
    """


def primary_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: {c['primary']};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 14px 24px;
            font-size: 15px;
            font-weight: 600;
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
    """


def text_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['primary']};
            border: none;
            font-weight: 600;
            padding: 0;
        }}
        QPushButton:hover {{
            text-decoration: underline;
        }}
    """


def local_mode_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: {c['surface_alt']};
            color: {c['text']};
            border: 1px solid {c['border']};
            border-radius: 6px;
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c['hover']};
            border-color: {c['input_border']};
        }}
        QPushButton:pressed {{
            background-color: {c['border']};
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
            border-radius: 24px;
            padding: 12px 20px;
            font-size: 14px;
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
                border-radius: 24px;
                padding: 10px 16px;
                font-size: 14px;
                text-align: left;
                font-weight: 500;
            }}
        """
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['text_secondary']};
            border: none;
            border-radius: 24px;
            padding: 10px 16px;
            font-size: 14px;
            text-align: left;
        }}
        QPushButton:hover {{
            background-color: {c['hover']};
        }}
    """


def new_folder_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: {c['surface']};
            color: {c['primary']};
            border: 1px solid {c['primary']};
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c['primary_light']};
        }}
    """


# ── Cards ──────────────────────────────────────────────────────────────

def folder_card():
    c = _c()
    return f"""
        FolderCard {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 8px;
        }}
        FolderCard:hover {{
            border-color: {c['primary']};
        }}
    """


def image_card():
    c = _c()
    return f"""
        ImageCard {{
            background-color: {c['surface']};
            border: 1px solid {c['border']};
            border-radius: 8px;
        }}
        ImageCard:hover {{
            border-color: {c['primary']};
        }}
    """


# ── Dialogs ────────────────────────────────────────────────────────────

def dialog_input():
    c = _c()
    return f"""
        QLineEdit {{
            padding: 10px;
            border: 1px solid {c['input_border']};
            border-radius: 4px;
            font-size: 14px;
            background-color: {c['input_bg']};
            color: {c['text']};
        }}
        QLineEdit:focus {{
            border: 2px solid {c['primary']};
        }}
    """


def dialog_cancel():
    c = _c()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['text_secondary']};
            border: 1px solid {c['border']};
            border-radius: 4px;
            padding: 10px 24px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c['hover']};
        }}
    """


def dialog_primary():
    c = _c()
    return f"""
        QPushButton {{
            background-color: {c['primary']};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 24px;
            font-weight: 600;
        }}
        QPushButton:hover {{
            background-color: {c['primary_dark']};
        }}
    """


def outline_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['primary']};
            border: 1px solid {c['primary']};
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c['primary_light']};
        }}
    """


def close_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: {c['primary']};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px 24px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c['primary_dark']};
        }}
    """


# ── Preview dialog ─────────────────────────────────────────────────────

def preview_scroll():
    c = _c()
    return f"""
        QScrollArea {{
            border: 1px solid {c['border']};
            border-radius: 8px;
            background-color: {c['surface_alt']};
        }}
    """


def progress_bar_lg():
    c = _c()
    return f"""
        QProgressBar {{
            background-color: {c['primary_light']};
            border: none;
            border-radius: 4px;
            height: 8px;
        }}
        QProgressBar::chunk {{
            background-color: {c['primary']};
            border-radius: 4px;
        }}
    """


def progress_bar_success():
    c = _c()
    return f"""
        QProgressBar {{
            background-color: {c['success_bg']};
            border: none;
            border-radius: 4px;
            height: 8px;
        }}
        QProgressBar::chunk {{
            background-color: {c['success']};
            border-radius: 4px;
        }}
    """


# ── Settings ───────────────────────────────────────────────────────────

def settings_input():
    c = _c()
    return f"""
        QSpinBox, QDoubleSpinBox, QComboBox {{
            padding: 8px 10px;
            border: 1px solid {c['input_border']};
            border-radius: 4px;
            font-size: 13px;
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


def shortcut_button():
    c = _c()
    return f"""
        QPushButton {{
            padding: 8px 16px;
            background-color: {c['primary']};
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton:hover {{ background-color: {c['primary_dark']}; }}
        QPushButton[waiting="true"] {{
            background-color: {c['error']};
        }}
    """


def load_more_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: {c['primary']};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px 20px;
            font-weight: 500;
            margin: 16px 0;
        }}
        QPushButton:hover {{
            background-color: {c['primary_dark']};
        }}
    """


def back_button():
    c = _c()
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['primary']};
            border: none;
            padding: 8px 0;
            font-size: 13px;
            text-align: left;
        }}
        QPushButton:hover {{
            text-decoration: underline;
        }}
    """


def folder_combo():
    c = _c()
    return f"""
        QComboBox {{
            padding: 10px;
            border: 1px solid {c['input_border']};
            border-radius: 4px;
            font-size: 14px;
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
                padding: 8px 20px;
                font-weight: 600;
                font-size: 13px;
            }}
        """
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c['text_secondary']};
            border: none;
            border-radius: 6px;
            padding: 8px 20px;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background-color: {c['hover']};
        }}
    """


# ═════════════════════════════════════════════════════════════════════════
# Legacy / Capture (not themed)
# ═════════════════════════════════════════════════════════════════════════

CAPTURE_STYLESHEET = """
QWidget#captureOverlay {
    background-color: rgba(0, 0, 0, 0.3);
}
"""
