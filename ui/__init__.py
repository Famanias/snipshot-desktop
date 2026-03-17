"""
SnipShot Desktop - UI Module
"""

from .styles import MAIN_STYLESHEET, AUTH_STYLESHEET, DASHBOARD_STYLESHEET
from .login import LoginWindow
from .register import RegisterWindow
from .dashboard import DashboardWindow
from .capture import CaptureWidget
from .translation import TranslationWindow

__all__ = [
    "MAIN_STYLESHEET",
    "AUTH_STYLESHEET", 
    "DASHBOARD_STYLESHEET",
    "LoginWindow",
    "RegisterWindow",
    "DashboardWindow",
    "CaptureWidget",
    "TranslationWindow"
]
