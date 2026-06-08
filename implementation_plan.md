# Implementation Plan - Expose Advanced Configuration Parameters in Settings UI (Revised)

We will expand the Settings UI panel of the SnipShot Desktop application to expose configuration parameters through a **two-tier system**: Basic Settings (always visible) and Advanced Settings (collapsible). We will introduce a centralized settings metadata system, input validation, and reset functionality.

## Architecture Principles

### 1. Single Source of Truth: `SETTINGS_METADATA`
- **`SETTINGS_METADATA`** is authoritative for all setting definitions (ranges, constraints, labels, tooltips, defaults)
- **`DEFAULT_SETTINGS`** is derived from metadata to prevent drift
- No duplication of default values
- Metadata drives all UI creation and validation

### 2. Scalable Settings Storage
- Dashboard does **not** load individual setting attributes (`self.text_threshold`, `self.kernel_size`, etc.)
- Instead, use `self.settings_manager.get(key)` on-demand
- Adding new settings requires only metadata entry, not attribute initialization
- Cleaner, more maintainable codebase as setting count grows

### 3. Validation Before Storage
- Invalid values are **prevented** at the UI control level (spinbox constraints, enum dropdowns, odd-only steps)
- Validation on save ensures invalid values never enter QSettings
- By translation time, all settings are guaranteed valid
- No surprise validation failures during translation

### 4. Section Constants
- Section names (e.g., `"Detection Configuration"`) are defined as module-level constants
- Prevents brittle string duplication and copy-paste errors
- Refactoring is safe and traceable

---

## Architecture Overview

### Two-Tier Settings System

#### Basic Settings (Always Visible)
~10 essential controls for everyday users:
- **Language** (dropdown)
- **Theme** (segmented toggle)
- **Capture Shortcuts** (hotkey buttons)
- **Continuous Snipping** (toggle + interval control)
- **Inpainter Model** (dropdown)
- **Font Size** (slider/spinbox with "Auto" toggle)
- **Line Spacing** (slider/spinbox with "Auto" toggle)
- **Alignment** (dropdown)
- **Text Case** (radio buttons: Normal / UPPERCASE / lowercase)

#### Advanced Settings (Collapsible)
Behind **[ Show Advanced Settings ]** button for power users:
- **Detection Configuration:** Detector Model, Detection Size, Box Threshold, Text Threshold, Unclip Ratio, Detect Rotation, Auto Rotation, Invert Image, No Text Language Skip, Gamma Correction
- **Inpainting Configuration:** Inpainting Precision, Kernel Size, Mask Dilation Offset
- **OCR & Extraction:** OCR Model, Minimum Text Length, Ignore Bubble, Probability Threshold (with toggle), No Text Language Skip
- **Rendering & Layout:** Renderer, Font Size Minimum, Font Size Offset, Disable Font Border, Direction, No Hyphenation, RTL Rendering

---

## Phase 1: Settings Metadata & Validation Infrastructure

### [CREATE] `config_metadata.py` (or add to `config.py`)

Define centralized metadata for all settings. This is the **single source of truth** for all setting definitions.

**Key Principle:** `SETTINGS_METADATA` is authoritative. `DEFAULT_SETTINGS` is derived from it:

```python
SETTINGS_METADATA = {
    "language": { ... },
    "theme": { ... },
    # ... all settings ...
}

# Derive defaults automatically to prevent drift
DEFAULT_SETTINGS = {
    key: metadata["default"]
    for key, metadata in SETTINGS_METADATA.items()
}
```

**Structure:** Each setting has:

```python
SETTINGS_METADATA = {
    # Basic Settings
    "language": {
        "label": "Language",
        "type": "string",
        "default": "English",
        "options": ["English", "Spanish", "French", "..."],
        "tooltip": "UI and output language"
    },
    "theme": {
        "label": "Theme",
        "type": "string",
        "default": "light",
        "options": ["light", "dark"],
        "tooltip": "Application theme"
    },
    
    # Advanced Settings - Numeric with Ranges
    "text_threshold": {
        "label": "Text Threshold",
        "type": "float",
        "default": 0.5,
        "min": 0.0,
        "max": 1.0,
        "step": 0.01,
        "constraint": "range",
        "tooltip": "Confidence threshold for text detection"
    },
    "unclip_ratio": {
        "label": "Unclip Ratio",
        "type": "float",
        "default": 2.3,
        "min": 1.0,
        "max": 4.0,
        "step": 0.1,
        "constraint": "range",
        "tooltip": "Expands detected text boundaries"
    },
    "kernel_size": {
        "label": "Kernel Size",
        "type": "int",
        "default": 3,
        "min": 1,
        "max": 7,
        "step": 1,
        "constraint": "odd_only",
        "tooltip": "Morphological kernel (must be odd: 1, 3, 5, 7)"
    },
    "line_spacing": {
        "label": "Line Spacing",
        "type": "float",
        "default": 1.0,
        "min": 0.5,
        "max": 2.0,
        "step": 0.1,
        "constraint": "positive",
        "tooltip": "Multiplier for line spacing"
    },
    "font_size": {
        "label": "Font Size",
        "type": "int",
        "default": 24,
        "min": 8,
        "max": 128,
        "step": 1,
        "constraint": "positive",
        "tooltip": "Default font size for rendering"
    },
    "font_size_minimum": {
        "label": "Minimum Font Size",
        "type": "int",
        "default": -1,
        "min": -1,
        "max": 128,
        "step": 1,
        "constraint": "lte_font_size",
        "tooltip": "-1 = no minimum; otherwise must be ≤ Font Size"
    },
    "font_size_offset": {
        "label": "Font Size Offset",
        "type": "int",
        "default": 0,
        "min": -50,
        "max": 50,
        "step": 1,
        "constraint": "range",
        "tooltip": "Adjustment to calculated font size"
    },
    "mask_dilation_offset": {
        "label": "Mask Dilation Offset",
        "type": "int",
        "default": 30,
        "min": 0,
        "max": 100,
        "step": 5,
        "constraint": "non_negative",
        "tooltip": "Pixels to dilate inpainting mask"
    },
    "min_text_length": {
        "label": "Minimum Text Length",
        "type": "int",
        "default": 0,
        "min": 0,
        "max": 1000,
        "step": 1,
        "constraint": "non_negative",
        "tooltip": "Ignore text shorter than this length"
    },
    "ignore_bubble": {
        "label": "Ignore Bubble Threshold",
        "type": "int",
        "default": 0,
        "min": 0,
        "max": 1000,
        "step": 10,
        "constraint": "non_negative",
        "tooltip": "Ignore small regions (pixels²)"
    },
    "prob": {
        "label": "Probability Threshold",
        "type": "float",
        "default": 0.5,
        "min": 0.0,
        "max": 1.0,
        "step": 0.05,
        "constraint": "range",
        "tooltip": "Probability cutoff (requires 'use_prob' enabled)"
    },
    
    # Dropdown/Options Settings
    "detector": {
        "label": "Detector Model",
        "type": "string",
        "default": "default",
        "options": ["default", "craft", "ctpn"],
        "constraint": "enum",
        "tooltip": "Text detection model"
    },
    "inpainting_precision": {
        "label": "Inpainting Precision",
        "type": "string",
        "default": "bf16",
        "options": ["fp32", "fp16", "bf16"],
        "constraint": "enum",
        "tooltip": "Floating point precision for inpainting"
    },
    "ocr": {
        "label": "OCR Model Size",
        "type": "string",
        "default": "48px",
        "options": ["32px", "48px", "64px"],
        "constraint": "enum",
        "tooltip": "OCR model resolution"
    },
    "renderer": {
        "label": "Renderer",
        "type": "string",
        "default": "default",
        "options": ["default", "advanced"],
        "constraint": "enum",
        "tooltip": "Text rendering engine"
    },
    "alignment": {
        "label": "Alignment",
        "type": "string",
        "default": "auto",
        "options": ["auto", "left", "center", "right", "justify"],
        "constraint": "enum",
        "tooltip": "Text alignment strategy"
    },
    "direction": {
        "label": "Text Direction",
        "type": "string",
        "default": "auto",
        "options": ["auto", "ltr", "rtl"],
        "constraint": "enum",
        "tooltip": "Text direction (left-to-right, right-to-left)"
    },
    
    # Text Case (Mutually Exclusive)
    "text_case": {
        "label": "Text Case",
        "type": "string",
        "default": "normal",
        "options": ["normal", "uppercase", "lowercase"],
        "constraint": "enum_exclusive",
        "tooltip": "Apply case transformation to output text"
    },
    
    # Boolean Settings
    "det_rotate": {
        "label": "Detect Rotation",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Enable text rotation detection"
    },
    "det_auto_rotate": {
        "label": "Auto Rotation",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Automatically rotate detected regions"
    },
    "det_invert": {
        "label": "Invert Image",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Invert image colors for detection"
    },
    "det_gamma_correct": {
        "label": "Gamma Correction",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Apply gamma correction to image"
    },
    "no_text_lang_skip": {
        "label": "No Text Language Skip",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Skip language-specific text filtering"
    },
    "use_prob": {
        "label": "Use Probability Threshold",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Enable probability-based filtering"
    },
    "use_font_size": {
        "label": "Use Custom Font Size",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Override default font size calculation"
    },
    "use_line_spacing": {
        "label": "Use Custom Line Spacing",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Override default line spacing"
    },
    "disable_font_border": {
        "label": "Disable Font Border",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Remove border from rendered text"
    },
    "no_hyphenation": {
        "label": "No Hyphenation",
        "type": "bool",
        "default": False,
        "constraint": "boolean",
        "tooltip": "Disable word hyphenation"
    },
    "rtl": {
        "label": "RTL Rendering",
        "type": "bool",
        "default": True,
        "constraint": "boolean",
        "tooltip": "Enable right-to-left text rendering"
    },
}
```

### [MODIFY] `settings_manager.py`

Add validation and reset methods:

#### Section Name Constants (NEW)
```python
# Prevent string literal brittleness
SECTION_DETECTION = "Detection Configuration"
SECTION_INPAINTING = "Inpainting Configuration"
SECTION_OCR = "OCR & Extraction"
SECTION_RENDERING = "Rendering & Layout"

SECTION_SETTINGS_MAP = {
    SECTION_DETECTION: ["detector", "text_threshold", "unclip_ratio", "det_rotate", ...],
    SECTION_INPAINTING: ["inpainting_precision", "kernel_size", "mask_dilation_offset", ...],
    SECTION_OCR: ["ocr", "min_text_length", "ignore_bubble", "use_prob", "prob", ...],
    SECTION_RENDERING: ["renderer", "font_size_minimum", "font_size_offset", ...],
}
```

#### New Methods:
- `validate_setting(key: str, value: Any) -> Tuple[bool, Optional[str]]`
  - Checks type, range, and constraints defined in `SETTINGS_METADATA`
  - Returns `(is_valid, error_message)` tuple
  - Handles constraints: `range`, `odd_only`, `positive`, `non_negative`, `lte_font_size`, `enum`, `boolean`

- `set_validated(key: str, value: Any) -> Tuple[bool, Optional[str]]`
  - **NEW:** Validates before saving
  - Only persists if valid
  - Returns success/error tuple
  - Prevents invalid values from entering QSettings

- `reset_all_settings() -> None`
  - Resets all settings to defaults (from `DEFAULT_SETTINGS`, which derives from metadata)
  - Syncs to Supabase if online

- `reset_section(section_name: str) -> None`
  - Resets only settings within a section (using `SECTION_SETTINGS_MAP`)
  - Maps section name to setting key groups
  - Safer than string literals

#### Validation Example:
```python
def validate_setting(self, key: str, value) -> tuple:
    metadata = SETTINGS_METADATA.get(key)
    if not metadata:
        return True, None  # Unknown key: allow (backward compat)
    
    constraint = metadata.get("constraint")
    
    if constraint == "range":
        min_val, max_val = metadata.get("min"), metadata.get("max")
        if not (min_val <= value <= max_val):
            return False, f"Must be between {min_val} and {max_val}"
    
    if constraint == "odd_only":
        if int(value) % 2 == 0:
            return False, f"Must be odd (1, 3, 5, 7)"
    
    if constraint == "lte_font_size":
        font_size = self.get("font_size")
        if value > font_size and value != -1:
            return False, f"Must be ≤ Font Size ({font_size}) or -1"
    
    if constraint == "positive":
        if value <= 0:
            return False, "Must be positive (> 0)"
    
    if constraint == "non_negative":
        if value < 0:
            return False, "Must be non-negative (≥ 0)"
    
    if constraint == "enum":
        options = metadata.get("options", [])
        if value not in options:
            return False, f"Must be one of: {', '.join(options)}"
    
    return True, None

def set_validated(self, key: str, value) -> tuple:
    """Save setting only if validation passes."""
    is_valid, error_msg = self.validate_setting(key, value)
    if not is_valid:
        return False, error_msg
    
    # Safe to persist
    self.set(key, value)
    return True, None
```

---

## Phase 2: Settings UI Restructuring (dashboard.py)

### [MODIFY] `dashboard.py`

#### Part A: Initialization & Properties

**Design Decision:** Instead of loading each setting into individual attributes (which creates maintenance overhead with 30+ settings), use `settings_manager.get(key)` on-demand.

```python
def __init__(self, ...):
    # ... existing code ...
    
    self.settings_manager = settings_manager  # Store reference
    self.advanced_settings_visible = False     # Only track UI state
```

**Benefits:**
- New settings require no attribute initialization
- Serialization/reset logic stays metadata-driven
- Single source of truth in `settings_manager`

When you need a setting value, call:
```python
value = self.settings_manager.get("kernel_size")
```

or bind directly from metadata:
```python
metadata = SETTINGS_METADATA.get("kernel_size")
current_value = self.settings_manager.get("kernel_size")
```

#### Part B: New UI Creation Methods

- `_create_numeric_control(key: str) -> QWidget`
  - Reads metadata (min, max, step, label, tooltip)
  - Creates paired QSlider + QDoubleSpinBox/QSpinBox
  - Bidirectional sync: slider ↔ spinbox
  - Floating-point scaling for slider (multiply by 100)
  - Optional "Auto" checkbox (handled via `use_*` settings)

- `_create_boolean_control(key: str) -> QCheckBox`
  - Reads metadata label, tooltip
  - Returns styled checkbox with signal connection

- `_create_options_control(key: str) -> QComboBox`
  - Reads metadata options, label, tooltip
  - Returns populated dropdown

- `_create_radio_control(key: str, options: List[str]) -> QGroupBox`
  - **NEW:** For mutually exclusive options (e.g., text_case)
  - Returns QGroupBox with QRadioButton children
  - Only one option selectable at a time

#### Part C: Settings Content Rendering

Rewrite `_render_settings_content(self)` to split into two sections:

**Section 1: BASIC SETTINGS** (Always Visible)
```
┌─ Language [dropdown] ─────────────────────────────┐
├─ Theme [Light][Dark] ─────────────────────────────┤
├─ Capture Shortcuts [Btn] [Btn] [Btn] ─────────────┤
├─ Continuous Snipping [Toggle] Interval: [input] ──┤
├─ Detection Size [Slider ──●────] [SpinBox] ───────┤
├─ Inpainter Model [dropdown] ──────────────────────┤
├─ Font Size [Slider ──●────] [SpinBox] with [Auto]─┤
├─ Line Spacing [Slider ──●────] [SpinBox] [Auto] ──┤
├─ Alignment [dropdown] ────────────────────────────┤
└─────────────────────────────────────────────────────┘
```

**Section 2: ADVANCED SETTINGS** (Collapsible)
```
┌─────────────────────────────────────────────────────┐
│ [▼ Show Advanced Settings] or [▶ Hide Advanced] ─────│
└─────────────────────────────────────────────────────┘
(visible only when toggled on)

┌─ Detection Configuration 🔍 [Reset 🔄] ──────────┐
├─ Detector Model [dropdown] ───────────────────────┤
├─ Detection Size [Slider] [SpinBox] ──────────────┤
├─ Box Threshold [Slider] [SpinBox] ───────────────┤
├─ Text Threshold [Slider] [SpinBox] ──────────────┤
├─ Unclip Ratio [Slider] [SpinBox] ────────────────┤
├─ Detect Rotation [✓] Auto Rotation [✓] ─────────┤
├─ Invert Image [✓] Gamma Correction [✓] ─────────┤
└───────────────────────────────────────────────────┘

┌─ Inpainting Configuration 🎨 [Reset 🔄] ────────┐
├─ Inpainter Model [dropdown] ──────────────────────┤
├─ Inpainting Size [Slider] [SpinBox] ──────────────┤
├─ Inpainting Precision [dropdown] ─────────────────┤
├─ Mask Dilation Offset [Slider] [SpinBox] ────────┤
├─ Kernel Size [Slider] [SpinBox] ──────────────────┤
└───────────────────────────────────────────────────┘

┌─ OCR & Extraction 📝 [Reset 🔄] ────────────────┐
├─ OCR Model [dropdown] ────────────────────────────┤
├─ Minimum Text Length [Slider] [SpinBox] ─────────┤
├─ Ignore Bubble [Slider] [SpinBox] ────────────────┤
├─ Probability Threshold [Slider] [SpinBox] ──────┤
│  └─ [✓ Use Probability] ──────────────────────────┤
├─ No Text Language Skip [✓] ──────────────────────┤
└───────────────────────────────────────────────────┘

┌─ Rendering & Layout 🖋️ [Reset 🔄] ─────────────┐
├─ Renderer [dropdown] ─────────────────────────────┤
├─ Font Size Minimum [Slider] [SpinBox] ────────────┤
├─ Font Size Offset [Slider] [SpinBox] ─────────────┤
├─ Disable Font Border [✓] ────────────────────────┤
├─ Direction [dropdown] ────────────────────────────┤
├─ Text Case: ○ Normal ○ UPPERCASE ○ lowercase ───┤
├─ No Hyphenation [✓] RTL Rendering [✓] ──────────┤
└───────────────────────────────────────────────────┘
```

**Bottom: Global Reset**
```
┌──────────────────────────────────────────────────────┐
│      [Reset All Settings to Defaults] 🔄             │
└──────────────────────────────────────────────────────┘
```

#### Part D: Validation & Constraint Enforcement

**Design Philosophy:** Prevent invalid input at the UI control level rather than validating after the fact.

**Primary Defense (Prevent Invalid Input):**
- **Enum/Dropdown:** Use `QComboBox` with predefined options (e.g., Renderer: ["default", "advanced"])
- **Odd-Only (kernel_size):** Use `QSpinBox` with `setSingleStep(2)` and `setMinimum(1)` → user can only select 1, 3, 5, 7
- **Range-Constrained:** Use `QSlider` or `QSpinBox` with enforced `setMinimum()` / `setMaximum()`
- **Radio Buttons:** For mutually exclusive options (text_case) — only one can be selected

**Secondary Defense (Validation on Save):**
```python
# When user clicks save/apply:
is_valid, error_msg = self.settings_manager.validate_setting(key, new_value)
if not is_valid:
    control.setStyleSheet("border: 2px solid red;")
    control.setToolTip(error_msg)
    # Disable save button — prevent storage of invalid value
else:
    is_saved, save_error = self.settings_manager.set_validated(key, new_value)
    if is_saved:
        control.setStyleSheet("")  # Clear red border
        self._show_toast(f"{key} updated")
    else:
        control.setToolTip(save_error)
```

**Benefits:**
- Invalid values never reach QSettings
- User gets immediate feedback (red border + tooltip)
- No surprise failures during translation
- Controls constrain input proactively (spinbox with odd-only step)

#### Part E: Text Case Handling

Replace two separate boolean controls (`uppercase`, `lowercase`) with mutually exclusive radio buttons:

```python
# Old (conflicting):
# "uppercase": False
# "lowercase": False

# New (single setting):
# "text_case": "normal"  # or "uppercase" or "lowercase"
```

When serializing to backend (`get_translation_config()`), expand back to boolean pair:
```python
def get_translation_config(self):
    # ... build config ...
    
    # Text case expansion
    if self.text_case == "uppercase":
        config["uppercase"] = True
        config["lowercase"] = False
    elif self.text_case == "lowercase":
        config["uppercase"] = False
        config["lowercase"] = True
    else:  # "normal"
        config["uppercase"] = False
        config["lowercase"] = False
    
    return config
```

#### Part F: Reset Button Handlers

Use section constants to prevent brittle string duplication:

```python
from settings_manager import SECTION_DETECTION, SECTION_INPAINTING, SECTION_OCR, SECTION_RENDERING

def _on_reset_all_settings(self):
    reply = QMessageBox.question(
        self, "Reset All Settings?",
        "Reset all settings to defaults? This cannot be undone.",
        QMessageBox.Yes | QMessageBox.No
    )
    if reply == QMessageBox.Yes:
        self.settings_manager.reset_all_settings()
        self._render_settings_content()  # Reload UI
        self._show_toast("Settings reset successfully")

def _on_reset_section(self, section_name: str):
    """section_name should be SECTION_DETECTION, SECTION_INPAINTING, etc."""
    reply = QMessageBox.question(
        self, f"Reset {section_name}?",
        f"Reset all {section_name.lower()} to defaults?",
        QMessageBox.Yes | QMessageBox.No
    )
    if reply == QMessageBox.Yes:
        self.settings_manager.reset_section(section_name)
        self._render_settings_content()
        self._show_toast(f"{section_name} reset successfully")

# Wire up buttons:
self.reset_detection_btn.clicked.connect(
    lambda: self._on_reset_section(SECTION_DETECTION)
)
self.reset_inpainting_btn.clicked.connect(
    lambda: self._on_reset_section(SECTION_INPAINTING)
)
# ... etc
```

---

## Phase 3: Serialization & Backend Integration

### [MODIFY] `get_translation_config(self)` in dashboard.py

**Key Design:** All validation happens during settings UI interaction (Part D above). By the time translation occurs, all stored settings are guaranteed valid.

1. **Read stored settings (no validation needed here):**
   ```python
   config = {
       "detection": {
           "detector": self.settings_manager.get("detector"),
           "text_threshold": self.settings_manager.get("text_threshold"),
           "unclip_ratio": self.settings_manager.get("unclip_ratio"),
           # ... etc
       },
       "inpainting": { ... },
       "rendering": { ... }
   }
   ```

2. **Expand text_case radio to boolean pair:**
   ```python
   text_case = self.settings_manager.get("text_case")
   if text_case == "uppercase":
       config["uppercase"] = True
       config["lowercase"] = False
   elif text_case == "lowercase":
       config["uppercase"] = False
       config["lowercase"] = True
   else:  # "normal"
       config["uppercase"] = False
       config["lowercase"] = False
   ```

3. **Handle conditional settings (use_* flags):**
   ```python
   # Only include font_size in payload if use_font_size is True
   if self.settings_manager.get("use_font_size"):
       config["font_size"] = self.settings_manager.get("font_size")
   # else: backend uses default calculation
   
   # Same for line_spacing, probability, etc.
   ```

**Benefits:**
- No validation failures during translation (they're caught earlier)
- Translation workflow is clean and reliable
- No surprise "Invalid kernel_size" errors mid-workflow
- Settings are validated at input time, not at use time

---

## Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| `config_metadata.py` | **CREATE** | Centralized settings metadata (single source of truth for ranges, constraints, labels, tooltips) |
| `utils/settings_manager.py` | **MODIFY** | Add section constants, `validate_setting()`, `set_validated()`, `reset_all_settings()`, `reset_section()` |
| `ui/dashboard.py` | **MODIFY** | Restructure settings layout, implement control-level constraint enforcement, use `settings_manager.get(key)` on-demand, handle resets using section constants |

---

## Implementation Checklist

### Phase 1: Metadata & Validation
- [ ] Create `config_metadata.py` with complete `SETTINGS_METADATA`
- [ ] Add `validate_setting()` to `settings_manager.py`
- [ ] Add `reset_all_settings()` and `reset_section()` to `settings_manager.py`
- [ ] Test validation logic for edge cases (kernel_size = 4, line_spacing = -1, etc.)

### Phase 2: Settings UI
- [ ] Add `self.advanced_settings_visible` flag to dashboard
- [ ] Implement `_create_numeric_control()`, `_create_boolean_control()`, `_create_options_control()`, `_create_radio_control()`
- [ ] Rewrite `_render_settings_content()` with two-tier layout
- [ ] Add "Show Advanced Settings" toggle button
- [ ] Add section reset buttons (🔄 icon per section)
- [ ] Add global reset button at bottom
- [ ] Implement validation UI feedback (red borders, error tooltips)

### Phase 3: Integration
- [ ] Update `get_translation_config()` with full validation
- [ ] Implement text_case expansion (radio selection → boolean pair)
- [ ] Test settings persistence across app restarts
- [ ] Test section resets (only affect target section)
- [ ] Test global reset (all settings → defaults)

---

## Verification Plan

### Phase 1: Metadata & Validation
1. Verify `SETTINGS_METADATA` loads without errors
2. Test: `validate_setting("kernel_size", 4)` → returns `(False, "must be odd")`
3. Test: `validate_setting("kernel_size", 5)` → returns `(True, None)`
4. Test: `validate_setting("line_spacing", -1)` → returns `(False, "must be positive")`
5. Test: `validate_setting("font_size_minimum", 25)` with `font_size=24` → returns `(False, "must be ≤ Font Size")`

### Phase 2: Settings UI
6. Launch app, navigate to Settings
7. Verify **Basic Settings** section visible (9 controls)
8. Verify **Advanced Settings** section hidden
9. Click **"Show Advanced Settings"** → section expands with ~25 additional controls
10. Click again → section collapses
11. Verify text case appears as **radio buttons** (Normal / UPPERCASE / lowercase), not checkboxes
12. Try selecting multiple radio options → only one remains selected
13. Enter invalid value (e.g., kernel_size = 4):
    - Control shows red border
    - Tooltip displays: "Must be odd (1, 3, 5, 7)"
    - Save button disabled
14. Correct the value → red border clears, save enabled
15. Test "Auto" checkboxes:
    - Check "Font Size Auto" → slider/spinbox disabled
    - Uncheck → re-enabled

### Phase 3: Reset & Persistence
16. Click **"Reset Detection Settings"** → only detection controls revert
17. Verify other settings unchanged
18. Click **"Reset All Settings to Defaults"**:
    - Confirmation dialog appears
    - After confirming, all controls show defaults
19. Change several settings, close app, restart:
    - All settings persist
20. Trigger a translation:
    - Inspect API payload (or logs)
    - Verify text_case radio correctly expands to `uppercase=T/F, lowercase=T/F`
    - Verify all numeric/enum settings present and validated

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Two-tier settings** | Basic tier for casual users; Advanced behind toggle keeps UI clean and non-intimidating |
| **Centralized metadata** | Single source of truth for ranges, constraints, labels; eliminates hardcoded UI values |
| **Text case as radio buttons** | Mutually exclusive option cleaner than two conflicting booleans; prevents invalid state |
| **Section-level resets** | Power users can reset specific categories without losing all preferences |
| **Validation on change** | Red borders + tooltips make constraints discoverable without docs |
| **Metadata constraints** | Centralizes rules; easier to maintain, test, and update validation logic |

---

## Known Questions & Decisions Made

| Question | Decision |
|----------|----------|
| Text Case default: "normal" or user's last choice? | Default to "normal"; respects fresh install UX |
| font_size_minimum = -1 (no minimum): always allow reverting? | Yes, always allow -1 for "no minimum" state |
| Confirm section resets? | Global reset: Yes (confirmation dialog). Section resets: Optional (brief toast). |

---

## Future Enhancements

### High-Value Features (Prioritize These)

- **Preset Profiles** ⭐ (Recommended next phase)
  - Predefined profiles: "Manga", "Light Novel", "Comic", "General"
  - Each profile auto-configures Detection Size, Thresholds, Rendering, OCR, etc.
  - Single-click switch instead of manual adjustment
  - Most users benefit more from presets than from tuning individual parameters
  - Lower learning curve, higher conversion

### Lower-Priority Features

- Import/export settings as JSON
- Comparison view (current vs. default)
- Setting change history/undo
- Per-language configuration overrides
