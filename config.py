"""
SnipShot Desktop - Configuration
"""

import os

# ---------------------------------------------------------------------------
# Supabase credentials (direct connection)
# Get these from Supabase dashboard → Project Settings → API
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://lsccpfjohkqfkrcxyybf.supabase.co/")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxzY2NwZmpvaGtxZmtyY3h5eWJmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjgyNzIxMTksImV4cCI6MjA4Mzg0ODExOX0.SKgsQ_tJyhqtlXjeE6WRyTr2Pv37Vi_KT3pA-78ne8c")

#   NEVER add SUPABASE_SERVICE_KEY to a desktop app.

# API Endpoints
TRANSLATOR_URL = os.getenv("TRANSLATOR_URL", "https://snipshot-snipshot-backend.hf.space")
LOCAL_TRANSLATOR_URL = "http://localhost:8001"

# Translation settings (must match snipshot-backend config enums)
TRANSLATION_TARGET_LANG = os.getenv("TRANSLATION_TARGET_LANG", "ENG").upper()
TRANSLATION_INPAINTER = os.getenv("TRANSLATION_INPAINTER", "lama_large").lower()
if TRANSLATION_INPAINTER not in {"lama_large", "none"}:
    TRANSLATION_INPAINTER = "lama_large"

# Local mode storage
LOCAL_STORAGE_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "SnipShot")

# App Settings
APP_NAME = "SnipShot"
APP_VERSION = "2.0.3"

# Default translation config — mirrors test.py test_local_translate defaults
DEFAULT_TRANSLATION_CONFIG = {
    "detector": {
        "detection_size": 1536,
        "box_threshold": 0.7,
    },
    "translator": {"target_lang": TRANSLATION_TARGET_LANG},
    "inpainter": {"inpainter": TRANSLATION_INPAINTER, "inpainting_size": 2048},
}

# Translation parameter bounds (used by Settings UI)
DETECTION_SIZE_MIN = 512
DETECTION_SIZE_MAX = 3072
DETECTION_SIZE_STEP = 64
BOX_THRESHOLD_MIN = 0.1
BOX_THRESHOLD_MAX = 1.0
INPAINTING_SIZE_MIN = 512
INPAINTING_SIZE_MAX = 4096
INPAINTING_SIZE_STEP = 256

# Shortcut key (default: Print Screen)
DEFAULT_SHORTCUT_KEY = 0x01000009  # Qt.Key_Print (Print Screen)
DEFAULT_CONTINUOUS_SHORTCUT_KEY = 0x01000038  # Qt.Key_F9
DEFAULT_CONTINUOUS_SNIP_INTERVAL = 500  # Default delay of 500ms between continuous snips

