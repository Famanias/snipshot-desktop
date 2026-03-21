"""
SnipShot Desktop - UI Module
"""

from .theme import theme
from .styles import get_main_stylesheet, CAPTURE_STYLESHEET
from .login import LoginWindow
from .register import RegisterWindow
from .dashboard import DashboardWindow
from .capture import CaptureWidget
from .translation import TranslationWindow

__all__ = [
    "theme",
    "get_main_stylesheet",
    "CAPTURE_STYLESHEET",
    "LoginWindow",
    "RegisterWindow",
    "DashboardWindow",
    "CaptureWidget",
    "TranslationWindow"
]
