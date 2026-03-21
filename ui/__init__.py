"""
SnipShot Desktop - UI Module
"""

from .theme import theme
from .styles import get_main_stylesheet, CAPTURE_STYLESHEET
from .components import StyledButton, SnipShotSpinner, FolderSelector
from .login import LoginWindow
from .register import RegisterWindow
from .dashboard import DashboardWindow
from .capture import CaptureWidget
from .translation import TranslationWindow

__all__ = [
    "theme",
    "get_main_stylesheet",
    "CAPTURE_STYLESHEET",
    "StyledButton",
    "SnipShotSpinner",
    "FolderSelector",
    "LoginWindow",
    "RegisterWindow",
    "DashboardWindow",
    "CaptureWidget",
    "TranslationWindow",
]
