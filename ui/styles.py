"""
SnipShot Desktop - Qt Stylesheets

Modern, clean styling for the application.
"""

# Color palette
COLORS = {
    "primary": "#4285F4",       # Google Blue
    "primary_dark": "#3367D6",
    "primary_light": "#E8F0FE",
    "secondary": "#5F6368",     # Gray
    "success": "#34A853",       # Green
    "warning": "#FBBC04",       # Yellow
    "error": "#EA4335",         # Red
    "background": "#FFFFFF",
    "surface": "#F8F9FA",
    "border": "#DADCE0",
    "text_primary": "#202124",
    "text_secondary": "#5F6368",
}


MAIN_STYLESHEET = """
/* ============== Global ============== */
QMainWindow, QDialog {
    background-color: #FFFFFF;
}

QWidget {
    font-family: 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
    color: #202124;
}

/* ============== Buttons ============== */
QPushButton {
    background-color: #4285F4;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 12px 24px;
    font-weight: 600;
    font-size: 14px;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #3367D6;
}

QPushButton:pressed {
    background-color: #2A56C6;
}

QPushButton:disabled {
    background-color: #DADCE0;
    color: #80868B;
}

/* Secondary Button */
QPushButton[class="secondary"] {
    background-color: transparent;
    color: #4285F4;
    border: 1px solid #DADCE0;
}

QPushButton[class="secondary"]:hover {
    background-color: #E8F0FE;
    border-color: #4285F4;
}

/* Danger Button */
QPushButton[class="danger"] {
    background-color: #EA4335;
}

QPushButton[class="danger"]:hover {
    background-color: #D93025;
}

/* Icon Button (flat) */
QPushButton[class="icon"] {
    background-color: transparent;
    border: none;
    padding: 8px;
    border-radius: 20px;
}

QPushButton[class="icon"]:hover {
    background-color: #F1F3F4;
}

/* ============== Input Fields ============== */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #DADCE0;
    border-radius: 6px;
    padding: 12px 16px;
    font-size: 14px;
    min-height: 20px;
    color: #202124;
}

QLineEdit:focus {
    border: 2px solid #4285F4;
    padding: 11px 15px;
}

QLineEdit:disabled {
    background-color: #F1F3F4;
    color: #80868B;
}

QLineEdit[class="error"] {
    border: 2px solid #EA4335;
}

/* ============== Labels ============== */
QLabel {
    color: #202124;
}

QLabel[class="title"] {
    font-size: 24px;
    font-weight: 600;
    color: #202124;
}

QLabel[class="subtitle"] {
    font-size: 14px;
    color: #5F6368;
}

QLabel[class="error"] {
    color: #EA4335;
    font-size: 12px;
}

QLabel[class="link"] {
    color: #4285F4;
}

/* ============== Frames ============== */
QFrame {
    background-color: #FFFFFF;
    border: none;
}

QFrame[class="card"] {
    background-color: #FFFFFF;
    border: 1px solid #DADCE0;
    border-radius: 8px;
}

QFrame[class="sidebar"] {
    background-color: #F8F9FA;
    border-right: 1px solid #DADCE0;
}

/* ============== Scroll Area ============== */
QScrollArea {
    background-color: transparent;
    border: none;
}

QScrollBar:vertical {
    background-color: #F1F3F4;
    width: 8px;
    border-radius: 4px;
}

QScrollBar::handle:vertical {
    background-color: #DADCE0;
    border-radius: 4px;
    min-height: 40px;
}

QScrollBar::handle:vertical:hover {
    background-color: #BDC1C6;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* ============== List Widget ============== */
QListWidget {
    background-color: transparent;
    border: none;
    outline: none;
}

QListWidget::item {
    padding: 12px 16px;
    border-radius: 0px;
    border-left: 3px solid transparent;
}

QListWidget::item:hover {
    background-color: #F1F3F4;
}

QListWidget::item:selected {
    background-color: #E8F0FE;
    border-left: 3px solid #4285F4;
    color: #202124;
}

/* ============== Menu ============== */
QMenu {
    background-color: #FFFFFF;
    border: 1px solid #DADCE0;
    border-radius: 4px;
    padding: 8px 0;
}

QMenu::item {
    padding: 8px 32px;
}

QMenu::item:selected {
    background-color: #F1F3F4;
}

/* ============== Progress Bar ============== */
QProgressBar {
    background-color: #E8F0FE;
    border: none;
    border-radius: 4px;
    height: 4px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #4285F4;
    border-radius: 4px;
}

/* ============== Message Box ============== */
QMessageBox {
    background-color: #FFFFFF;
}

QMessageBox QLabel {
    color: #202124;
    font-size: 14px;
}

/* ============== Tool Tip ============== */
QToolTip {
    background-color: #202124;
    color: #FFFFFF;
    border: none;
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
}

/* ============== Tab Widget ============== */
QTabWidget::pane {
    border: none;
    background-color: #FFFFFF;
}

QTabBar::tab {
    background-color: transparent;
    padding: 12px 24px;
    border-bottom: 2px solid transparent;
    color: #5F6368;
}

QTabBar::tab:selected {
    color: #4285F4;
    border-bottom: 2px solid #4285F4;
}

QTabBar::tab:hover:!selected {
    color: #202124;
}
"""


# Login/Register specific styles
AUTH_STYLESHEET = """
QFrame#authContainer {
    background-color: #FFFFFF;
    border: 1px solid #DADCE0;
    border-radius: 8px;
}

QLabel#appTitle {
    font-size: 28px;
    font-weight: 700;
    color: #4285F4;
}

QLabel#authTitle {
    font-size: 24px;
    font-weight: 400;
    color: #202124;
}
"""


# Dashboard specific styles  
DASHBOARD_STYLESHEET = """
/* Sidebar */
QFrame#sidebar {
    background-color: #F8F9FA;
    border-right: 1px solid #DADCE0;
}

/* Folder Item */
QFrame.folderItem {
    background-color: #FFFFFF;
    border: 1px solid #DADCE0;
    border-radius: 8px;
    padding: 12px;
}

QFrame.folderItem:hover {
    border-color: #4285F4;
    background-color: #F8F9FA;
}

/* Image Grid Item */
QFrame.imageItem {
    background-color: #FFFFFF;
    border: 1px solid #DADCE0;
    border-radius: 8px;
}

QFrame.imageItem:hover {
    border-color: #4285F4;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}

/* Header */
QFrame#header {
    background-color: #FFFFFF;
    border-bottom: 1px solid #DADCE0;
}

/* Empty State */
QLabel#emptyState {
    color: #80868B;
    font-size: 16px;
}
"""


# Capture overlay styles
CAPTURE_STYLESHEET = """
QWidget#captureOverlay {
    background-color: rgba(0, 0, 0, 0.3);
}
"""
