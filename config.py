"""
SnipShot Desktop - Configuration
"""

import os
from dotenv import load_dotenv

load_dotenv()

# API Endpoints
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8002/api")
TRANSLATOR_URL = os.getenv("TRANSLATOR_URL", "http://localhost:8000")

# App Settings
APP_NAME = "SnipShot"
APP_VERSION = "1.0.0"

# Default translation config
DEFAULT_TRANSLATION_CONFIG = {
    "detector": {
        "detector": "default",
        "detection_size": 1536,
        "box_threshold": 0.7,
        "unclip_ratio": 2.3
    },
    "render": {"direction": "auto"},
    "translator": {"translator": "groq", "target_lang": "ENG"},
    "inpainter": {"inpainter": "default", "inpainting_size": 2048},
    "mask_dilation_offset": 30
}

# Shortcut key (default: F2)
DEFAULT_SHORTCUT_KEY = 0x01000071  # Qt.Key_F2
