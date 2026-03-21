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
        "bg":              "#F0F2F5",
        "surface":         "#FFFFFF",
        "surface_alt":     "#F0F1F3",
        "sidebar":         "#F0F1F3",
        "border":          "#D1D5DB",
        "border_light":    "#ECEEF1",
        "primary":         "#0EA5E9",
        "primary_dark":    "#0284C7",
        "primary_light":   "#E0F2FE",
        "primary_subtle":  "#F0F9FF",
        "text":            "#111827",
        "text_secondary":  "#6B7280",
        "text_tertiary":   "#9CA3AF",
        "hover":           "#ECEEF1",
        "input_bg":        "#FFFFFF",
        "input_border":    "#D1D5DB",
        "error":           "#EF4444",
        "error_bg":        "#FEF2F2",
        "success":         "#10B981",
        "success_bg":      "#ECFDF5",
        "nav_active_bg":   "#E0F2FE",
        "nav_active_text": "#0EA5E9",
        "scrollbar_bg":    "#F0F1F3",
        "scrollbar":       "#D1D5DB",
        "scrollbar_hover": "#9CA3AF",
        "tooltip_bg":      "#1F2937",
        "tooltip_text":    "#FFFFFF",
        "disabled_bg":     "#E5E7EB",
        "disabled_text":   "#9CA3AF",
    }

    # ── Dark palette (from SnipShot website) ───────────────────────────
    DARK = {
        "bg":              "#0A0A0B",
        "surface":         "#141416",
        "surface_alt":     "#1E1E24",
        "sidebar":         "#0F0F11",
        "border":          "#2A2A2E",
        "border_light":    "#2A2A2E",
        "primary":         "#0EA5E9",
        "primary_dark":    "#0284C7",
        "primary_light":   "#0C2D4A",
        "primary_subtle":  "#0A1929",
        "text":            "#F9FAFB",
        "text_secondary":  "#9CA3AF",
        "text_tertiary":   "#9CA3AF",
        "hover":           "#1F1F23",
        "input_bg":        "#141416",
        "input_border":    "#2A2A2E",
        "error":           "#EF4444",
        "error_bg":        "#2D1515",
        "success":         "#10B981",
        "success_bg":      "#0D2818",
        "nav_active_bg":   "#0C2D4A",
        "nav_active_text": "#0EA5E9",
        "scrollbar_bg":    "#141416",
        "scrollbar":       "#2A2A2E",
        "scrollbar_hover": "#3A3A3E",
        "tooltip_bg":      "#F9FAFB",
        "tooltip_text":    "#111827",
        "disabled_bg":     "#1E1E22",
        "disabled_text":   "#4B5563",
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if ThemeManager._is_initialized:
            return
        super().__init__()
        ThemeManager._is_initialized = True
        self._mode = self._load_preference()

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def c(self) -> dict:
        """Current colour palette."""
        return self.DARK if self._mode == "dark" else self.LIGHT

    @property
    def is_dark(self) -> bool:
        return self._mode == "dark"

    def set_mode(self, mode: str):
        if mode not in ("light", "dark") or mode == self._mode:
            return
        self._mode = mode
        self._save_preference()
        self.theme_changed.emit(mode)

    def toggle(self):
        self.set_mode("dark" if self._mode == "light" else "light")

    def rgba(self, key: str, alpha: float) -> str:
        """Convert a hex palette colour to an rgba() CSS string."""
        hex_color = self.c[key].lstrip("#")
        r, g, b = int(hex_color[:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"

    # ── Persistence ────────────────────────────────────────────────────
    def _config_path(self):
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        d = os.path.join(appdata, "SnipShot")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "theme.json")

    def _load_preference(self) -> str:
        try:
            with open(self._config_path()) as f:
                return json.load(f).get("mode", "light")
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return "light"

    def _save_preference(self):
        try:
            with open(self._config_path(), "w") as f:
                json.dump({"mode": self._mode}, f)
        except OSError:
            pass


# Module-level singleton
theme = ThemeManager()
