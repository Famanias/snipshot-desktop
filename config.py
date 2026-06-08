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
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")
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
APP_VERSION = "2.0.6"

# Default translation config — mirrors test.py test_local_translate defaults
DEFAULT_TRANSLATION_CONFIG = {
    "detector": {
        "detector": "default",
        "detection_size": 1536,
        "box_threshold": 0.7,
        "text_threshold": 0.5,
        "unclip_ratio": 2.3,
        "det_rotate": False,
        "det_auto_rotate": False,
        "det_invert": False,
        "det_gamma_correct": False,
    },
    "translator": {
        # "translator": "groq",
        "target_lang": TRANSLATION_TARGET_LANG,
        "no_text_lang_skip": False,
    },
    "inpainter": {
        "inpainter": TRANSLATION_INPAINTER,
        "inpainting_size": 2048,
        "inpainting_precision": "bf16",
    },
    "ocr": {
        "ocr": "48px",
        "min_text_length": 0,
        "ignore_bubble": 0,
        "prob": None,
    },
    "render": {
        "renderer": "default",
        "font_size": None,
        "font_size_minimum": -1,
        "font_size_offset": 0,
        "line_spacing": None,
        "disable_font_border": False,
        "alignment": "auto",
        "direction": "auto",
        "uppercase": False,
        "lowercase": False,
        "no_hyphenation": False,
        "font_color": None,
        "rtl": True,
    },
    "kernel_size": 3,
    "mask_dilation_offset": 30,
}

# Translation parameter bounds / options (used by Settings UI)
DETECTION_SIZE_MIN = 512
DETECTION_SIZE_MAX = 3072
DETECTION_SIZE_STEP = 64

BOX_THRESHOLD_MIN = 0.1
BOX_THRESHOLD_MAX = 1.0
BOX_THRESHOLD_STEP = 0.05

TEXT_THRESHOLD_MIN = 0.1
TEXT_THRESHOLD_MAX = 1.0
TEXT_THRESHOLD_STEP = 0.05

UNCLIP_RATIO_MIN = 1.0
UNCLIP_RATIO_MAX = 5.0
UNCLIP_RATIO_STEP = 0.1

INPAINTING_SIZE_MIN = 512
INPAINTING_SIZE_MAX = 4096
INPAINTING_SIZE_STEP = 256

MASK_DILATION_OFFSET_MIN = 0
MASK_DILATION_OFFSET_MAX = 100
MASK_DILATION_OFFSET_STEP = 1

KERNEL_SIZE_MIN = 1
KERNEL_SIZE_MAX = 31
KERNEL_SIZE_STEP = 2  # Must be odd

MIN_TEXT_LENGTH_MIN = 0
MIN_TEXT_LENGTH_MAX = 100
MIN_TEXT_LENGTH_STEP = 1

IGNORE_BUBBLE_MIN = 0
IGNORE_BUBBLE_MAX = 50
IGNORE_BUBBLE_STEP = 1

PROB_MIN = 0.0
PROB_MAX = 1.0
PROB_STEP = 0.05

FONT_SIZE_MIN = 1
FONT_SIZE_MAX = 200
FONT_SIZE_STEP = 1

FONT_SIZE_MINIMUM_MIN = -1
FONT_SIZE_MINIMUM_MAX = 100
FONT_SIZE_MINIMUM_STEP = 1

FONT_SIZE_OFFSET_MIN = -50
FONT_SIZE_OFFSET_MAX = 50
FONT_SIZE_OFFSET_STEP = 1

LINE_SPACING_MIN = 0.0
LINE_SPACING_MAX = 2.0
LINE_SPACING_STEP = 0.05

DETECTOR_OPTIONS = ["default"]
# TRANSLATOR_OPTIONS = ["groq"]
INPAINTER_OPTIONS = ["lama_large", "none"]
OCR_OPTIONS = ["48px"]
RENDERER_OPTIONS = ["default", "manga2eng", "none"]
INPAINTING_PRECISION_OPTIONS = ["bf16", "fp16", "fp32"]
ALIGNMENT_OPTIONS = ["auto", "left", "center", "right"]
DIRECTION_OPTIONS = ["auto", "horizontal", "vertical"]

# Shortcut key (default: Print Screen)
DEFAULT_SHORTCUT_KEY = 0x01000009  # Qt.Key_Print (Print Screen)
DEFAULT_CONTINUOUS_SHORTCUT_KEY = 0x01000038  # Qt.Key_F9
DEFAULT_CONTINUOUS_SNIP_INTERVAL = 500  # Default delay of 500ms between continuous snips