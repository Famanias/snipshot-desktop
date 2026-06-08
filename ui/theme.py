"""
SnipShot Desktop - Theme Manager

Centralized light/dark mode management with persistent preferences.
Colors derived from the SnipShot website branding.
"""

import json
import os
from PyQt5.QtCore import QObject, pyqtSignal


class ThemeManager(QObject):
    """Singleton that holds the current color palette and persists the preference."""

    theme_changed = pyqtSignal(str)  # "light" or "dark"

    _instance = None
    _is_initialized = False

    # ── Light palette (improved web-app feel) ──────────────────────────
    LIGHT = {
        "bg":              "#F5F5F5",
        "surface":         "#FFFFFF",
        "surface_alt":     "#F8F8F8",
        "sidebar":         "#F8F8F8",
        "border":          "#E0E0E0",
        "border_light":    "#F0F0F0",
        "primary":         "#0EA5E9",
        "primary_dark":    "#0284C7",
        "primary_light":   "#E0F2FE",
        "primary_subtle":  "#F0F9FF",
        "text":            "#1A1A1A",
        "text_secondary":  "#4A4A4A",
        "text_tertiary":   "#7A7A7A",
        "hover":           "#F0F0F0",
        "input_bg":        "#FFFFFF",
        "input_border":    "#D0D0D0",
        "error":           "#EF4444",
        "error_bg":        "#FEF2F2",
        "success":         "#10B981",
        "success_bg":      "#ECFDF5",
        "nav_active_bg":   "#E0F2FE",
        "nav_active_text": "#0EA5E9",
        "scrollbar_bg":    "#F8F8F8",
        "scrollbar":       "#D0D0D0",
        "scrollbar_hover": "#A0A0A0",
        "tooltip_bg":      "#1F2937",
        "tooltip_text":    "#FFFFFF",
        "disabled_bg":     "#E8E8E8",
        "disabled_text":   "#A0A0A0",
    }

    # ── Dark palette (from SnipShot website) ───────────────────────────
    DARK = {
        "bg":              "#121314",
        "surface":         "#121314",
        "surface_alt":     "#1f2021",
        "sidebar":         "#1f2021",
        "border":          "#3d484e",
        "border_light":    "#3d484e",
        "primary":         "#7cdaff",
        "primary_dark":    "#006781",
        "primary_light":   "#47494c",
        "primary_subtle":  "#1b1c1d",
        "text":            "#e3e2e3",
        "text_secondary":  "#bcc8cf",
        "text_tertiary":   "#869399",
        "hover":           "#0d0e0f",
        "input_bg":        "#1f2021",
        "input_border":    "#3d484e",
        "error":           "#ffb4ab",
        "error_bg":        "#93000a",
        "success":         "#10B981",
        "success_bg":      "#0D2818",
        "nav_active_bg":   "#47494c",
        "nav_active_text": "#e3e2e3",
        "scrollbar_bg":    "#121314",
        "scrollbar":       "#343536",
        "scrollbar_hover": "#47494c",
        "tooltip_bg":      "#e3e2e3",
        "tooltip_text":    "#121314",
        "disabled_bg":     "#1b1c1d",
        "disabled_text":   "#869399",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        pass

    def ensure_initialized(self):
        if getattr(self, "_is_initialized", False):
            return
        super().__init__()
        self._is_initialized = True
        from utils.settings_manager import settings_manager
        settings_manager.setting_changed.connect(self._on_setting_changed)
        settings_manager.profile_changed.connect(self._on_profile_changed)

    @property
    def mode(self) -> str:
        self.ensure_initialized()
        from utils.settings_manager import settings_manager
        return settings_manager.get_setting("theme", "light")

    @property
    def c(self) -> dict:
        """Current colour palette."""
        return self.DARK if self.mode == "dark" else self.LIGHT

    @property
    def is_dark(self) -> bool:
        return self.mode == "dark"

    def set_mode(self, mode: str):
        if mode not in ("light", "dark") or mode == self.mode:
            return
        from utils.settings_manager import settings_manager
        settings_manager.set_setting("theme", mode)

    def toggle(self):
        self.set_mode("dark" if self.mode == "light" else "light")

    def rgba(self, key: str, alpha: float) -> str:
        """Convert a hex palette colour to an rgba() CSS string."""
        hex_color = self.c[key].lstrip("#")
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    def _on_setting_changed(self, key: str, val: Any):
        if key == "theme":
            self.theme_changed.emit(val)

    def _on_profile_changed(self):
        self.theme_changed.emit(self.mode)


# Module-level singleton
theme = ThemeManager()
