"""
SnipShot Desktop - Centralized Settings Metadata
Cleanly separates validation and domain logic from presentation/UI logic.
"""

SECTION_DETECTION = "detection"
SECTION_INPAINTING = "inpainting"
SECTION_OCR = "ocr"
SECTION_RENDERING = "rendering"
SECTION_GENERAL = "general"

SECTION_LABELS = {
    SECTION_DETECTION: "Detection Configuration",
    SECTION_INPAINTING: "Inpainting Configuration",
    SECTION_OCR: "OCR & Extraction",
    SECTION_RENDERING: "Rendering & Layout",
    SECTION_GENERAL: "General Preferences",
}

SETTINGS_METADATA = {
    # --- BASIC SETTINGS (tier: basic) ---
    "target_language": {
        "default": "ENG",
        "type": "string",
        "tier": "basic",
        "section": SECTION_GENERAL,
        "validation": {
            "constraint": "enum",
            "options": ["ENG", "JPN", "KOR", "CHS", "CHT"]
        },
        "ui": {
            "label": "Default Target Language",
            "control": "combo",
            "options": [
                ("English", "ENG"),
                ("Japanese", "JPN"),
                ("Korean", "KOR"),
                ("Chinese (Simplified)", "CHS"),
                ("Chinese (Traditional)", "CHT")
            ],
            "tooltip": "UI and output translation language"
        }
    },
    "theme": {
        "default": "light",
        "type": "string",
        "tier": "basic",
        "section": SECTION_GENERAL,
        "validation": {
            "constraint": "enum",
            "options": ["light", "dark"]
        },
        "ui": {
            "label": "Theme",
            "control": "segmented_theme",
            "tooltip": "Application interface style"
        }
    },
    "snip_shortcut_key": {
        "default": 16777225, # Qt.Key_Print Screen (0x01000009)
        "type": "int",
        "tier": "basic",
        "section": SECTION_GENERAL,
        "validation": {
            "constraint": "positive"
        },
        "ui": {
            "label": "Single Snip Shortcut",
            "control": "shortcut_key",
            "tooltip": "Press this key to initiate a single screenshot capture"
        }
    },
    "continuous_shortcut_key": {
        "default": 16777272, # Qt.Key_F9 (0x01000038)
        "type": "int",
        "tier": "basic",
        "section": SECTION_GENERAL,
        "validation": {
            "constraint": "positive"
        },
        "ui": {
            "label": "Continuous Snip Shortcut",
            "control": "shortcut_key",
            "tooltip": "Press this key to initiate continuous screen capturing"
        }
    },
    "continuous_snip_interval": {
        "default": 500,
        "type": "int",
        "tier": "basic",
        "section": SECTION_GENERAL,
        "validation": {
            "constraint": "range",
            "min": 100,
            "max": 10000
        },
        "ui": {
            "label": "Snip Interval (ms)",
            "control": "number_input",
            "tooltip": "Time to wait (in milliseconds) before starting the next capture"
        }
    },
    "inpainter": {
        "default": "lama_large",
        "type": "string",
        "tier": "basic",
        "section": SECTION_INPAINTING,
        "validation": {
            "constraint": "enum",
            "options": ["lama_large", "none"]
        },
        "ui": {
            "label": "Inpainter Model",
            "control": "combo",
            "options": [
                ("LAMA Large (recommended)", "lama_large"),
                ("None (skip inpainting)", "none")
            ],
            "tooltip": "Select the AI model for filling in backgrounds"
        }
    },
    "font_size": {
        "default": 24,
        "type": "int",
        "tier": "basic",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "positive",
            "min": 8,
            "max": 128
        },
        "ui": {
            "label": "Font Size",
            "control": "slider_spinbox_optional",
            "tooltip": "Default font size for rendering. Enable custom override or check Auto."
        }
    },
    "use_font_size": {
        "default": False,
        "type": "bool",
        "tier": "basic",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Use Custom Font Size",
            "control": "checkbox",
            "tooltip": "Override automatically calculated font size"
        }
    },
    "line_spacing": {
        "default": 1.0,
        "type": "float",
        "tier": "basic",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "positive",
            "min": 0.5,
            "max": 2.0
        },
        "ui": {
            "label": "Line Spacing",
            "control": "slider_spinbox_optional",
            "tooltip": "Multiplier for line spacing. Enable custom override or check Auto."
        }
    },
    "use_line_spacing": {
        "default": False,
        "type": "bool",
        "tier": "basic",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Use Custom Line Spacing",
            "control": "checkbox",
            "tooltip": "Override automatically calculated line spacing"
        }
    },
    "alignment": {
        "default": "auto",
        "type": "string",
        "tier": "basic",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "enum",
            "options": ["auto", "left", "center", "right"]
        },
        "ui": {
            "label": "Alignment",
            "control": "combo",
            "options": [
                ("Auto Detect", "auto"),
                ("Left", "left"),
                ("Center", "center"),
                ("Right", "right")
            ],
            "tooltip": "Text alignment strategy"
        }
    },
    "text_case": {
        "default": "normal",
        "type": "string",
        "tier": "basic",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "enum",
            "options": ["normal", "uppercase", "lowercase"]
        },
        "ui": {
            "label": "Text Case",
            "control": "radio_group",
            "options": [
                ("Normal", "normal"),
                ("UPPERCASE", "uppercase"),
                ("lowercase", "lowercase")
            ],
            "tooltip": "Apply case transformation to translation text"
        }
    },

    # --- ADVANCED DETECTOR SETTINGS (tier: advanced, section: detection) ---
    "detector": {
        "default": "default",
        "type": "string",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "enum",
            "options": ["default"]
        },
        "ui": {
            "label": "Detector Model",
            "control": "combo",
            "options": [
                ("Default Detector", "default")
            ],
            "tooltip": "Select the text detection engine"
        }
    },
    "detection_size": {
        "default": 1536,
        "type": "int",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "range",
            "min": 512,
            "max": 3072,
            "step": 64
        },
        "ui": {
            "label": "Detection Size",
            "control": "slider_spinbox",
            "tooltip": "Maximum resolution size for OCR detector input. Higher size yields better small-text OCR but slower speed."
        }
    },
    "box_threshold": {
        "default": 0.7,
        "type": "float",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "range",
            "min": 0.1,
            "max": 1.0,
            "step": 0.05
        },
        "ui": {
            "label": "Box Threshold",
            "control": "slider_spinbox",
            "tooltip": "Minimum text bounding box confidence threshold"
        }
    },
    "text_threshold": {
        "default": 0.5,
        "type": "float",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "range",
            "min": 0.1,
            "max": 1.0,
            "step": 0.05
        },
        "ui": {
            "label": "Text Threshold",
            "control": "slider_spinbox",
            "tooltip": "Confidence threshold for character recognition validation"
        }
    },
    "unclip_ratio": {
        "default": 2.3,
        "type": "float",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "range",
            "min": 1.0,
            "max": 5.0,
            "step": 0.1
        },
        "ui": {
            "label": "Unclip Ratio",
            "control": "slider_spinbox",
            "tooltip": "Expands detected text boundaries for OCR padding"
        }
    },
    "det_rotate": {
        "default": False,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Detect Rotation",
            "control": "checkbox",
            "tooltip": "Enable detection of rotated or skewed text blocks"
        }
    },
    "det_auto_rotate": {
        "default": False,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Auto Rotation",
            "control": "checkbox",
            "tooltip": "Automatically deskew rotated text fields"
        }
    },
    "det_invert": {
        "default": False,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Invert Image",
            "control": "checkbox",
            "tooltip": "Invert input image pixel colors for dark-background text optimization"
        }
    },
    "det_gamma_correct": {
        "default": False,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Gamma Correction",
            "control": "checkbox",
            "tooltip": "Apply automatic gamma/contrast adjustments to enhance readability"
        }
    },

    # --- ADVANCED INPAINTING SETTINGS (tier: advanced, section: inpainting) ---
    "inpainting_size": {
        "default": 2048,
        "type": "int",
        "tier": "advanced",
        "section": SECTION_INPAINTING,
        "validation": {
            "constraint": "range",
            "min": 512,
            "max": 4096,
            "step": 256
        },
        "ui": {
            "label": "Inpainting Size",
            "control": "slider_spinbox",
            "tooltip": "Background clean/inpaint processing bounds size"
        }
    },
    "inpainting_precision": {
        "default": "bf16",
        "type": "string",
        "tier": "advanced",
        "section": SECTION_INPAINTING,
        "validation": {
            "constraint": "enum",
            "options": ["bf16", "fp16", "fp32"]
        },
        "ui": {
            "label": "Inpainting Precision",
            "control": "combo",
            "options": [
                ("BFloat16 (Fastest)", "bf16"),
                ("Float16 (Balanced)", "fp16"),
                ("Float32 (High Precision)", "fp32")
            ],
            "tooltip": "Floating-point precision for neural inpaint server"
        }
    },
    "kernel_size": {
        "default": 3,
        "type": "int",
        "tier": "advanced",
        "section": SECTION_INPAINTING,
        "validation": {
            "constraint": "odd_only",
            "min": 1,
            "max": 31,
            "step": 2
        },
        "ui": {
            "label": "Kernel Size",
            "control": "slider_spinbox",
            "tooltip": "Size of morphological processing kernel (must be odd)"
        }
    },
    "mask_dilation_offset": {
        "default": 30,
        "type": "int",
        "tier": "advanced",
        "section": SECTION_INPAINTING,
        "validation": {
            "constraint": "non_negative",
            "min": 0,
            "max": 100,
            "step": 1
        },
        "ui": {
            "label": "Mask Dilation Offset",
            "control": "slider_spinbox",
            "tooltip": "Expansion padding pixels for the inpainting clean mask"
        }
    },

    # --- ADVANCED OCR SETTINGS (tier: advanced, section: ocr) ---
    "ocr": {
        "default": "48px",
        "type": "string",
        "tier": "advanced",
        "section": SECTION_OCR,
        "validation": {
            "constraint": "enum",
            "options": ["48px"]
        },
        "ui": {
            "label": "OCR Model Size",
            "control": "combo",
            "options": [
                ("48px Model", "48px")
            ],
            "tooltip": "Internal target pixel size for characters during OCR extraction"
        }
    },
    "min_text_length": {
        "default": 0,
        "type": "int",
        "tier": "advanced",
        "section": SECTION_OCR,
        "validation": {
            "constraint": "non_negative",
            "min": 0,
            "max": 100,
            "step": 1
        },
        "ui": {
            "label": "Minimum Text Length",
            "control": "slider_spinbox",
            "tooltip": "Filter out and ignore extracted texts shorter than this length"
        }
    },
    "ignore_bubble": {
        "default": 0,
        "type": "int",
        "tier": "advanced",
        "section": SECTION_OCR,
        "validation": {
            "constraint": "non_negative",
            "min": 0,
            "max": 50,
            "step": 1
        },
        "ui": {
            "label": "Ignore Bubble Size",
            "control": "slider_spinbox",
            "tooltip": "Ignore speech bubbles/bounding boxes smaller than this pixel area"
        }
    },
    "use_prob": {
        "default": False,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_OCR,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Use Probability Threshold",
            "control": "checkbox",
            "tooltip": "Enable character probability filtering"
        }
    },
    "prob": {
        "default": 0.5,
        "type": "float",
        "tier": "advanced",
        "section": SECTION_OCR,
        "validation": {
            "constraint": "range",
            "min": 0.0,
            "max": 1.0,
            "step": 0.05
        },
        "ui": {
            "label": "Probability Cutoff",
            "control": "slider_spinbox_optional",
            "tooltip": "Confidence threshold to filter out low-probability character detections"
        }
    },
    "no_text_lang_skip": {
        "default": False,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_OCR,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "No Text Language Skip",
            "control": "checkbox",
            "tooltip": "Force translation even if target and source language match"
        }
    },

    # --- ADVANCED RENDERING SETTINGS (tier: advanced, section: rendering) ---
    "renderer": {
        "default": "default",
        "type": "string",
        "tier": "advanced",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "enum",
            "options": ["default", "manga2eng", "none"]
        },
        "ui": {
            "label": "Renderer Mode",
            "control": "combo",
            "options": [
                ("Default Renderer", "default"),
                ("Manga2Eng Model", "manga2eng"),
                ("No Rendering (Inpaint only)", "none")
            ],
            "tooltip": "Select text rendering layout engine"
        }
    },
    "font_size_minimum": {
        "default": -1,
        "type": "int",
        "tier": "advanced",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "lte_font_size",
            "min": -1,
            "max": 100,
            "step": 1
        },
        "ui": {
            "label": "Minimum Font Size",
            "control": "slider_spinbox",
            "tooltip": "Enforce minimum font size. -1 disables constraint; otherwise must be <= Font Size."
        }
    },
    "font_size_offset": {
        "default": 0,
        "type": "int",
        "tier": "advanced",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "range",
            "min": -50,
            "max": 50,
            "step": 1
        },
        "ui": {
            "label": "Font Size Offset",
            "control": "slider_spinbox",
            "tooltip": "Add or subtract value offset from automatically calculated font size"
        }
    },
    "disable_font_border": {
        "default": False,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Disable Font Border",
            "control": "checkbox",
            "tooltip": "Hide stroke/outline around translated text font"
        }
    },
    "direction": {
        "default": "auto",
        "type": "string",
        "tier": "advanced",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "enum",
            "options": ["auto", "horizontal", "vertical"]
        },
        "ui": {
            "label": "Direction Override",
            "control": "combo",
            "options": [
                ("Auto Detect", "auto"),
                ("Horizontal", "horizontal"),
                ("Vertical", "vertical")
            ],
            "tooltip": "Override direction of the rendered text"
        }
    },
    "no_hyphenation": {
        "default": False,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Disable Hyphenation",
            "control": "checkbox",
            "tooltip": "Avoid wrapping text using word division hyphens"
        }
    },
    "rtl": {
        "default": True,
        "type": "bool",
        "tier": "advanced",
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "boolean"
        },
        "ui": {
            "label": "Right-to-Left (RTL)",
            "control": "checkbox",
            "tooltip": "Enable Right-to-Left writing layout alignment"
        }
    },
}

DEFAULT_SETTINGS = {
    key: meta["default"]
    for key, meta in SETTINGS_METADATA.items()
}
