"""
SnipShot Desktop - Settings Manager

Centralized management of application configurations with support for
profile isolation (offline vs. online), optimistic UI updates, debounced
cloud syncing, and background retry loops for failed synchronization.
"""

import os
import json
import logging
from typing import Any

from PyQt5.QtCore import QObject, QTimer, QThread, pyqtSignal, QSettings

# Setup logging
logger = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "theme": "light",
    "snip_shortcut_key": 16777225,            # Qt.Key_Print Screen (0x01000009)
    "continuous_shortcut_key": 16777240,     # Qt.Key_F9 (0x01000038)
    "continuous_snip_interval": 500,
    "target_language": "ENG",
    "detection_size": 1536,
    "box_threshold": 0.7,
    "inpainting_size": 2048,
    "inpainter": "lama_large"
}


class SettingsSyncWorker(QThread):
    """Background worker to save settings to Supabase without blocking the GUI thread."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, updates: dict):
        super().__init__()
        self.updates = updates

    def run(self):
        try:
            from api import api_client
            # Supabase API client handles access tokens automatically
            res = api_client.update_user_settings(self.updates)
            if res.get("success"):
                self.finished.emit(res.get("data") or {})
            else:
                self.error.emit(res.get("error", "Failed to update settings on server"))
        except Exception as e:
            self.error.emit(str(e))


class SettingsFetchWorker(QThread):
    """Background worker to fetch settings from Supabase without blocking the GUI thread."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            from api import api_client
            res = api_client.get_user_settings()
            if res.get("success"):
                self.finished.emit(res.get("data") or {})
            else:
                self.error.emit(res.get("error", "Failed to retrieve settings from server"))
        except Exception as e:
            self.error.emit(str(e))


class SettingsManager(QObject):
    """Manages SnipShot configurations for online/offline modes, caching, and cloud sync."""

    setting_changed = pyqtSignal(str, object)  # Emitted when a setting changes: (key, new_value)
    profile_changed = pyqtSignal()             # Emitted when switching setting profiles (e.g. login/logout)

    def __init__(self):
        super().__init__()
        self.qsettings = QSettings("SnipShot", "SnipShot")
        self.user_id = None
        
        # Debounce timer for saving to cloud (500ms)
        self.debounce_timer = QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(500)
        self.debounce_timer.timeout.connect(self.save_to_supabase)
        
        # Retry timer for failed syncs (5 minutes / 300,000ms)
        self.retry_timer = QTimer(self)
        self.retry_timer.setInterval(300000)
        self.retry_timer.timeout.connect(self.retry_pending_sync)

        self.sync_worker = None
        self.fetch_worker = None

        # Clean up any legacy settings files/keys from older versions
        self.migrate_legacy_settings()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value, scoped to the current profile (user cache or offline)."""
        if default is None:
            default = DEFAULT_SETTINGS.get(key)
        
        group = f"user_{self.user_id}" if self.user_id else "offline"
        val = self.qsettings.value(f"{group}/{key}")
        
        if val is None:
            return default
            
        # Cast value based on default type
        if default is not None:
            try:
                if isinstance(default, bool):
                    if isinstance(val, str):
                        return val.lower() in ("true", "1")
                    return bool(val)
                elif isinstance(default, int):
                    return int(val)
                elif isinstance(default, float):
                    return float(val)
            except (ValueError, TypeError):
                pass
        return val

    def set_setting(self, key: str, val: Any):
        """Set a setting value, scoped to the active profile, and trigger synchronization if online."""
        group = f"user_{self.user_id}" if self.user_id else "offline"
        current_val = self.get_setting(key)
        
        # Avoid redundant saves/updates
        if current_val == val:
            return
            
        self.qsettings.setValue(f"{group}/{key}", val)
        self.setting_changed.emit(key, val)
        
        # If in online mode, mark dirty and start/reset the debounce sync timer
        if self.user_id:
            self.mark_dirty(True)
            self.debounce_timer.start()

    def load_offline_profile(self):
        """Revert settings to the local offline profile."""
        self.user_id = None
        self.retry_timer.stop()
        self.profile_changed.emit()
        logger.info("Loaded offline settings profile.")

    def load_user_profile(self, user_id: str):
        """Load settings for the given user ID (Cache-First)."""
        self.user_id = user_id
        
        # Trigger immediate UI refresh using local cache
        self.profile_changed.emit()
        logger.info(f"Loaded user settings cache for user: {user_id}")
        
        # If there are unsynced changes from a previous session, push them to Supabase
        if self.is_dirty():
            logger.info("Pending local changes found. Scheduling sync.")
            self.save_to_supabase()
        else:
            # Otherwise, fetch the latest from the server in the background
            self._fetch_from_supabase()

        # Start periodic checks for dirty sync status
        self.retry_timer.start()

    def is_dirty(self) -> bool:
        """Check if there are local user changes that haven't reached Supabase yet."""
        if not self.user_id:
            return False
        return self.qsettings.value(f"user_{self.user_id}/sync_dirty", False, type=bool)

    def mark_dirty(self, dirty: bool = True):
        """Write the sync dirty flag to QSettings to persist across restarts."""
        if self.user_id:
            self.qsettings.setValue(f"user_{self.user_id}/sync_dirty", dirty)

    def save_to_supabase(self):
        """Upsert the active user's settings profile to Supabase in a background thread."""
        if not self.user_id:
            return

        if self.sync_worker is not None and self.sync_worker.isRunning():
            # Let the active run finish; the retry/debounce will fire again if needed
            return

        updates = {}
        for key in DEFAULT_SETTINGS:
            updates[key] = self.get_setting(key)

        logger.info(f"Saving settings to Supabase for user {self.user_id}...")
        self.sync_worker = SettingsSyncWorker(updates)
        self.sync_worker.finished.connect(self._on_sync_finished)
        self.sync_worker.error.connect(self._on_sync_error)
        self.sync_worker.start()

    def _on_sync_finished(self, data: dict):
        logger.info("Successfully synced settings to Supabase.")
        self.mark_dirty(False)
        self.sync_worker = None

    def _on_sync_error(self, error_msg: str):
        logger.error(f"Failed to sync settings to Supabase: {error_msg}")
        self.mark_dirty(True)
        self.sync_worker = None

    def _fetch_from_supabase(self):
        """Retrieve the user settings row from Supabase in the background."""
        if not self.user_id:
            return

        if self.fetch_worker is not None and self.fetch_worker.isRunning():
            return

        logger.info(f"Fetching settings from Supabase for user {self.user_id}...")
        self.fetch_worker = SettingsFetchWorker()
        self.fetch_worker.finished.connect(self._on_fetch_finished)
        self.fetch_worker.error.connect(self._on_fetch_error)
        self.fetch_worker.start()

    def _on_fetch_finished(self, data: dict):
        self.fetch_worker = None
        if not self.user_id:
            return

        if not data:
            # First-time user: no settings stored on the server yet.
            # Populate the server with values from the offline profile as the starting point.
            logger.info("No server settings found. Initializing server settings with current offline preferences...")
            for key in DEFAULT_SETTINGS:
                offline_val = self.get_setting(key)
                self.qsettings.setValue(f"user_{self.user_id}/{key}", offline_val)
            self.save_to_supabase()
            return

        # Check if the server configuration differs from local cache
        cache_differs = False
        for key in DEFAULT_SETTINGS:
            server_val = data.get(key)
            if server_val is not None:
                # Handle numeric differences or casting issues
                local_val = self.get_setting(key)
                if local_val != server_val:
                    self.qsettings.setValue(f"user_{self.user_id}/{key}", server_val)
                    cache_differs = True
        
        if cache_differs:
            logger.info("Local settings cache updated from server.")
            self.profile_changed.emit()

    def _on_fetch_error(self, error_msg: str):
        logger.error(f"Could not load settings from Supabase: {error_msg}")
        self.fetch_worker = None

    def retry_pending_sync(self):
        """Invoked by retry_timer to sync dirty settings when internet connection returns."""
        if self.user_id and self.is_dirty():
            logger.info("Retrying pending settings sync...")
            self.save_to_supabase()

    def migrate_legacy_settings(self):
        """Migrate older SnipShot settings configurations into new scoped QSettings groups."""
        # 1. Migrate legacy `%APPDATA%/SnipShot/theme.json`
        appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
        legacy_theme_path = os.path.join(appdata, "SnipShot", "theme.json")
        if os.path.exists(legacy_theme_path):
            try:
                with open(legacy_theme_path) as f:
                    data = json.load(f)
                    theme_val = data.get("mode", "light")
                    if self.qsettings.value("offline/theme") is None:
                        self.qsettings.setValue("offline/theme", theme_val)
                os.remove(legacy_theme_path)
                logger.info("Migrated legacy theme.json file to QSettings.")
            except Exception as e:
                logger.warning(f"Failed to migrate legacy theme.json: {e}")

        # 2. Migrate legacy root keys in QSettings
        legacy_interval = self.qsettings.value("continuous_snip_interval")
        if legacy_interval is not None:
            if self.qsettings.value("offline/continuous_snip_interval") is None:
                self.qsettings.setValue("offline/continuous_snip_interval", legacy_interval)
            self.qsettings.remove("continuous_snip_interval")
            logger.info("Migrated legacy continuous_snip_interval key in QSettings.")


# Instantiate the settings manager singleton class
settings_manager = SettingsManager()
