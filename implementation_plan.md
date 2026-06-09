# Implementation Plan - Expose Advanced Configuration Parameters in Settings UI (Revised)

We will expand the Settings UI panel of the SnipShot Desktop application to expose configuration parameters through a **two-tier system**: Basic Settings (always visible) and Advanced Settings (collapsible). We will introduce a centralized settings metadata system, input validation, and reset functionality.

## Architecture Principles

### 1. Single Source of Truth: `SETTINGS_METADATA`
- **`SETTINGS_METADATA`** is authoritative for all setting definitions (ranges, constraints, labels, tooltips, defaults).
- **`DEFAULT_SETTINGS`** is derived from metadata to prevent drift.
- No duplication of default values.
- Metadata drives all UI creation and validation.

### 2. Decoupled Metadata Model (UI vs. Domain concerns)
- Metadata is separated into:
  - **Domain concerns**: `default`, `type`, `validation`, `section`, and `tier`.
  - **UI concerns**: `ui` (nested dictionary containing labels, tooltips, and control layouts).
- Ensures that future systems (CLI, web backend, sync engines) can consume settings configuration without importing GUI-specific attributes.

### 3. Metadata-Driven Generation (Zero UI Hardcoding)
- Place settings in their respective panels dynamically using metadata keys:
  - `"tier": "basic"` vs. `"tier": "advanced"`
  - `"section": "detection"` vs. `"section": "inpainting"`
- Avoid hardcoded lists of setting keys inside `dashboard.py` layout code. Adding a setting requires editing only `config_metadata.py`.

### 4. Scalable Settings Storage
- Dashboard does **not** load individual setting attributes (`self.text_threshold`, `self.kernel_size`, etc.).
- Instead, use `self.settings_manager.get_setting(key)` on-demand.
- Cleaner, more maintainable codebase as setting count grows.

### 5. Validation Before Storage
- Invalid values are **prevented** at the UI control level (spinbox constraints, enum dropdowns, odd-only steps).
- Validation on save ensures invalid values never enter QSettings.
- Type enforcement checks occur early in the pipeline (preventing values like `"banana"`).
- By translation time, all settings are guaranteed valid.

### 6. Local-First Eventual Consistency
- Local settings database (QSettings) is the absolute authority for active operation.
- Resets/changes commit to local storage immediately and reflect instantly in the UI.
- Background sync tasks update Supabase asynchronously. If a network sync fails, changes are flagged as dirty and retried in the background until successfully persisted to the cloud.

---

## Architecture Overview

### Decoupled Sections & Labels

```python
# Unique identifiers for configuration groupings (never used as display text directly)
SECTION_DETECTION = "detection"
SECTION_INPAINTING = "inpainting"
SECTION_OCR = "ocr"
SECTION_RENDERING = "rendering"

SECTION_LABELS = {
    SECTION_DETECTION: "Detection Configuration",
    SECTION_INPAINTING: "Inpainting Configuration",
    SECTION_OCR: "OCR & Extraction",
    SECTION_RENDERING: "Rendering & Layout",
}
```

---

## Phase 1: Settings Metadata & Validation Infrastructure

### [NEW] [config_metadata.py](file:///d:/repos/snipshot-desktop/config_metadata.py)

Centralized configuration definitions, cleanly separating validation/domain keys from presentation details.

```python
SETTINGS_METADATA = {
    # --- BASIC SETTINGS ---
    "language": {
        "default": "English",
        "type": "string",
        "tier": "basic",
        "section": "general",
        "validation": {
            "constraint": "enum",
            "options": ["English", "Spanish", "French", "Chinese", "Japanese"]
        },
        "ui": {
            "label": "Language",
            "control": "combo",
            "tooltip": "UI and output translation language"
        }
    },
    "theme": {
        "default": "light",
        "type": "string",
        "tier": "basic",
        "section": "general",
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
    "text_case": {
        "default": "normal",
        "type": "string",
        "tier": "basic",
        "section": "rendering",
        "validation": {
            "constraint": "enum",
            "options": ["normal", "uppercase", "lowercase"]
        },
        "ui": {
            "label": "Text Case",
            "control": "radio_group",
            "tooltip": "Apply text transformation to output"
        }
    },

    # --- ADVANCED SETTINGS ---
    "text_threshold": {
        "default": 0.5,
        "type": "float",
        "tier": "advanced",
        "section": SECTION_DETECTION,
        "validation": {
            "constraint": "range",
            "min": 0.0,
            "max": 1.0,
            "step": 0.01
        },
        "ui": {
            "label": "Text Threshold",
            "control": "slider_spinbox",
            "tooltip": "Confidence threshold for text detection"
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
            "max": 4.0,
            "step": 0.1
        },
        "ui": {
            "label": "Unclip Ratio",
            "control": "slider_spinbox",
            "tooltip": "Expands detected text boundaries"
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
            "max": 7,
            "step": 2
        },
        "ui": {
            "label": "Kernel Size",
            "control": "slider_spinbox",
            "tooltip": "Morphological kernel size (must be odd)"
        }
    },
    "font_size": {
        "default": 24,
        "type": "int",
        "tier": "basic", # Exposed as basic with optional "Auto" checkbox toggle
        "section": SECTION_RENDERING,
        "validation": {
            "constraint": "positive",
            "min": 8,
            "max": 128
        },
        "ui": {
            "label": "Font Size",
            "control": "slider_spinbox_optional", # Paired with a "use_font_size" flag
            "tooltip": "Default font size for rendering"
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
            "max": 128
        },
        "ui": {
            "label": "Minimum Font Size",
            "control": "slider_spinbox",
            "tooltip": "-1 = no minimum; otherwise must be ≤ Font Size"
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
            "max": 100
        },
        "ui": {
            "label": "Mask Dilation Offset",
            "control": "slider_spinbox",
            "tooltip": "Pixels to expand inpainting mask boundary"
        }
    }
    # ... rest of parameters defined using the same nested structure ...
}

# Derive default configuration values automatically to guarantee zero drift
DEFAULT_SETTINGS = {
    key: metadata["default"]
    for key, metadata in SETTINGS_METADATA.items()
}
```

### [MODIFY] [settings_manager.py](file:///d:/repos/snipshot-desktop/utils/settings_manager.py)

#### Type Validation & Unknown Checking:
1. Validate type conversions early (e.g. converting `"banana"` to float should fail).
2. Set `allow_unknown=False` to ensure typos like `text_threshhold` raise immediate validation exceptions or warnings instead of silently saving.
3. Handle the `-1` sentinel for `font_size_minimum` as a clean validation bypass prior to applying logic checks.

```python
import logging
logger = logging.getLogger(__name__)

def validate_setting(self, key: str, value: Any, current_ui_context: dict = None, allow_unknown: bool = False) -> tuple:
    metadata = SETTINGS_METADATA.get(key)
    if not metadata:
        if allow_unknown:
            logger.warning(f"Allowing validation of unknown setting key: '{key}'")
            return True, None
        return False, f"Unknown setting key: '{key}'"

    expected_type = metadata.get("type")
    
    # 1. Type Coercion & Verification
    coerced_value = value
    try:
        if expected_type == "int":
            coerced_value = int(value)
        elif expected_type == "float":
            coerced_value = float(value)
        elif expected_type == "bool":
            if isinstance(value, str):
                coerced_value = value.lower() in ("true", "1", "yes")
            else:
                coerced_value = bool(value)
        elif expected_type == "string":
            coerced_value = str(value)
    except (ValueError, TypeError):
        return False, f"Value '{value}' is not of expected type: {expected_type}"

    # 2. Handle Sentinel Bypass (e.g., -1 allows bypassing positive/min constraints)
    if key == "font_size_minimum" and coerced_value == -1:
        return True, None

    validation_rules = metadata.get("validation", {})
    constraint = validation_rules.get("constraint")

    if constraint == "range":
        min_val, max_val = validation_rules.get("min"), validation_rules.get("max")
        if not (min_val <= coerced_value <= max_val):
            return False, f"Must be between {min_val} and {max_val}"

    elif constraint == "odd_only":
        if int(coerced_value) % 2 == 0:
            return False, "Must be odd (1, 3, 5, 7)"

    elif constraint == "lte_font_size":
        # Resolve comparison target from UI context, else fallback to storage
        font_size = None
        if current_ui_context and "font_size" in current_ui_context:
            font_size = current_ui_context["font_size"]
        else:
            font_size = self.get_setting("font_size")

        if font_size is not None and coerced_value > font_size:
            return False, f"Must be ≤ Font Size ({font_size}) or -1"

    elif constraint == "positive":
        if coerced_value <= 0:
            return False, "Must be positive (> 0)"

    elif constraint == "non_negative":
        if coerced_value < 0:
            return False, "Must be non-negative (≥ 0)"

    elif constraint == "enum":
        options = validation_rules.get("options", [])
        if coerced_value not in options:
            return False, f"Must be one of: {', '.join(options)}"

    return True, None
```

#### Synchronized Cloud Failure Strategy:
- **Local Database is Authoritative**: Settings are committed immediately to the local QSettings profile. UI updates are optimistic.
- **Failures are Non-Blocking**: If an online sync to Supabase fails, the local cache sets `sync_dirty = True`. The sync payload is queued.
- **Eventual Consistency**: The background retry loop (`retry_pending_sync`) wakes up every 5 minutes (or on reconnection) to clear the queue.
- **User Notification**: A non-blocking, transient status indicator (or toast) informs the user if synchronization fails, but operations continue locally.

```python
def reset_section(self, section_name: str) -> None:
    """Resets only keys associated with the given section in metadata."""
    # Find all keys under this section name
    keys_to_reset = [
        key for key, meta in SETTINGS_METADATA.items()
        if meta.get("section") == section_name
    ]
    
    group = f"user_{self.user_id}" if self.user_id else "offline"
    for key in keys_to_reset:
        default_val = DEFAULT_SETTINGS[key]
        self.qsettings.setValue(f"{group}/{key}", default_val)
        self.setting_changed.emit(key, default_val)
        
    if self.user_id:
        self.mark_dirty(True)
        self.debounce_timer.start() # Push to Supabase asynchronously
```

---

## Phase 2: Settings UI Restructuring (dashboard.py)

### [MODIFY] [dashboard.py](file:///d:/repos/snipshot-desktop/ui/dashboard.py)

#### Part A: Compound Control Wrappers (No Raw Widget Registry)
Using a raw widget mapping (`self._setting_widgets[key] = widget`) breaks when a setting comprises multiple UI elements (e.g. Slider + Spinbox + Override Checkbox). We will introduce a clean interface wrapper to encapsulate these:

```python
class SettingControlWrapper:
    """Wrapper to interact with compound UI settings controls uniformly."""
    def __init__(self, key: str, main_layout: QWidget):
        self.key = key
        self.main_layout = main_layout
        self.slider = None
        self.spinbox = None
        self.checkbox = None
        self.radio_buttons = []
        self.combo = None

    def block_signals(self, block: bool):
        for widget in [self.slider, self.spinbox, self.checkbox, self.combo] + self.radio_buttons:
            if widget:
                widget.blockSignals(block)

    def set_value(self, value: Any):
        self.block_signals(True)
        
        # Handle "Auto" check state dependency
        if self.checkbox:
            # e.g., use_font_size determines if font_size is enabled
            self.checkbox.setChecked(value is not None)
            if self.spinbox and value is None:
                self.spinbox.setEnabled(False)
        
        # Update numeric controls
        if value is not None:
            if self.spinbox:
                self.spinbox.setEnabled(True)
                self.spinbox.setValue(value)
            if self.slider:
                self.slider.setEnabled(True)
                # handle float representations in integer sliders
                if isinstance(value, float):
                    self.slider.setValue(int(value * 100))
                else:
                    self.slider.setValue(value)
                    
        # Update choice controls
        if self.combo:
            idx = self.combo.findData(value)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
        for radio in self.radio_buttons:
            if radio.property("val") == value:
                radio.setChecked(True)
                
        self.block_signals(False)

    def get_ui_value(self) -> Any:
        """Read live value from the UI inputs before saving."""
        if self.checkbox and not self.checkbox.isChecked():
            return None # e.g. "Auto" calculation selected
        if self.spinbox:
            return self.spinbox.value()
        if self.combo:
            return self.combo.currentData()
        for radio in self.radio_buttons:
            if radio.isChecked():
                return radio.property("val")
        return None

    def show_error(self, error_message: str):
        """Applies error styling to the control's inputs."""
        border_style = "border: 1.5px solid red; border-radius: 4px;"
        if self.spinbox:
            self.spinbox.setStyleSheet(border_style)
            self.spinbox.setToolTip(error_message)
        elif self.combo:
            self.combo.setStyleSheet(border_style)
            self.combo.setToolTip(error_message)

    def clear_error(self):
        """Clears validation highlights."""
        if self.spinbox:
            self.spinbox.setStyleSheet("")
            self.spinbox.setToolTip("")
        elif self.combo:
            self.combo.setStyleSheet("")
            self.combo.setToolTip("")
```

We map wrappers in the dashboard:
`self._setting_widgets: Dict[str, SettingControlWrapper] = {}`

#### Part B: Metadata-Driven Dynamic Generation
Instead of hardcoding layout bindings, the UI reads the metadata dictionary to assemble itself dynamically:

```python
def _render_settings_content(self):
    """Orchestrates layout generation."""
    # 1. Clear layout & recreate references dict
    self._setting_widgets.clear()
    
    # 2. Render Basic settings
    self.content_layout.addWidget(self._render_basic_settings())
    self.content_layout.addSpacing(SPACE["lg"])
    
    # 3. Add Advanced Toggle
    self.advanced_toggle_btn = QPushButton()
    self.advanced_toggle_btn.clicked.connect(self._toggle_advanced_panel)
    self.content_layout.addWidget(self.advanced_toggle_btn)
    
    # 4. Render Advanced settings container
    self.advanced_container = self._render_advanced_settings()
    self.content_layout.addWidget(self.advanced_container)
    
    # Apply initial expanded state from local storage persistence
    self._update_advanced_visibility()

    # 5. Add Global Reset
    reset_btn = QPushButton("Reset All Settings to Defaults")
    reset_btn.clicked.connect(self._on_reset_all)
    self.content_layout.addWidget(reset_btn)

def _render_basic_settings(self) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.addWidget(self._section_header_label("", "General Preferences"))
    
    # Generate all settings where tier == basic
    for key, meta in SETTINGS_METADATA.items():
        if meta.get("tier") == "basic":
            wrapper = self._build_control(key, meta)
            layout.addWidget(wrapper.main_layout)
            self._setting_widgets[key] = wrapper
            
    return container

def _render_advanced_settings(self) -> QWidget:
    container = QWidget()
    layout = QVBoxLayout(container)
    
    # Group advanced settings by section key dynamically
    sections_found = set(
        meta.get("section") for meta in SETTINGS_METADATA.values()
        if meta.get("tier") == "advanced"
    )
    
    for section_id in sorted(sections_found):
        section_card = self._render_section(section_id)
        layout.addWidget(section_card)
        
    return container

def _render_section(self, section_id: str) -> QWidget:
    card = QFrame()
    card.setProperty("class", "settings-card")
    layout = QVBoxLayout(card)
    
    # Header layout with Title and Section Reset
    header_layout = QHBoxLayout()
    header_title = SECTION_LABELS.get(section_id, section_id.title())
    header_layout.addWidget(self._section_header_label("", header_title))
    header_layout.addStretch()
    
    reset_btn = QToolButton()
    reset_btn.setText("Reset")
    reset_btn.clicked.connect(lambda _, s=section_id: self._on_reset_section(s))
    header_layout.addWidget(reset_btn)
    layout.addLayout(header_layout)
    
    # Populate section controls dynamically
    for key, meta in SETTINGS_METADATA.items():
        if meta.get("tier") == "advanced" and meta.get("section") == section_id:
            wrapper = self._build_control(key, meta)
            layout.addWidget(wrapper.main_layout)
            self._setting_widgets[key] = wrapper
            
    return card
```

#### Part C: Inter-field Validation Context
When modifying a field containing validation dependencies:
```python
def _on_control_modified(self, key: str):
    wrapper = self._setting_widgets[key]
    new_value = wrapper.get_ui_value()
    
    # Build active context from other UI inputs to avoid order-dependency errors
    context = {}
    if key == "font_size_minimum":
        font_size_wrapper = self._setting_widgets.get("font_size")
        if font_size_wrapper:
            context["font_size"] = font_size_wrapper.get_ui_value()
            
    is_valid, error_msg = self.settings_manager.validate_setting(key, new_value, current_ui_context=context)
    
    if not is_valid:
        wrapper.show_error(error_msg)
    else:
        wrapper.clear_error()
        self.settings_manager.set_validated(key, new_value)
        
    # Cascade validations (e.g. if Font Size changed, re-validate Minimum Font Size)
    if key == "font_size":
        self._on_control_modified("font_size_minimum")
```

---

## Phase 3: Serialization & Backend Integration

### [MODIFY] `get_translation_config(self)` in dashboard.py

Serialization remains identical to the previous version but benefits from absolute guarantees that validation occurred on change:

```python
def get_translation_config(self) -> dict:
    """Reads validated values on-demand to serialize the backend parameters payload."""
    config = {
        "detection": {
            "detector": self.settings_manager.get_setting("detector"),
            "text_threshold": self.settings_manager.get_setting("text_threshold"),
            "unclip_ratio": self.settings_manager.get_setting("unclip_ratio"),
            # ...
        },
        "inpainting": {
            "inpainting_precision": self.settings_manager.get_setting("inpainting_precision"),
            "kernel_size": self.settings_manager.get_setting("kernel_size"),
            # ...
        }
    }
    return config
```

---

## Files to Modify/Create

| File | Action | Purpose |
|------|--------|---------|
| [config_metadata.py](file:///d:/repos/snipshot-desktop/config_metadata.py) | **CREATE** | Declarative single-source-of-truth metadata model (isolates UI and Domain schemas). |
| [settings_manager.py](file:///d:/repos/snipshot-desktop/utils/settings_manager.py) | **MODIFY** | Type checking, validation with sentinel, dynamic key resets, and background retry loops. |
| [dashboard.py](file:///d:/repos/snipshot-desktop/ui/dashboard.py) | **MODIFY** | Metadata-driven UI layout construction, `SettingControlWrapper` management, dynamic resets. |

---

## Implementation Checklist

### Phase 1: Declarative Infrastructure
- [ ] Create `config_metadata.py` containing isolated UI and Validation blocks.
- [ ] Add strict key check (`allow_unknown=False`) and early type conversion constraints.
- [ ] Implement local-first cloud retry synchronization model.

### Phase 2: Metadata-Driven GUI Generation
- [ ] Implement `SettingControlWrapper` to encapsulate compound controls.
- [ ] Dynamic basic/advanced layouts by iterating over metadata tiers and sections.
- [ ] Add in-place refreshes via wrapper interfaces on resets.
- [ ] Set up cascading validation for cross-field dependencies (e.g. Font Size updates trigger Min Font Size check).

---

## Verification Plan

### Automated / Unit Verification
1. **Type Constraint Testing**:
   - `validate_setting("text_threshold", "banana")` -> returns `(False, "not of expected type")`
   - `validate_setting("kernel_size", 3)` -> returns `(True, None)`
2. **Sentinel Bypass Testing**:
   - `validate_setting("font_size_minimum", -1)` -> returns `(True, None)`
3. **Cross-Field Order Independence**:
   - `validate_setting("font_size_minimum", 20, {"font_size": 18})` -> returns `(False, "Must be ≤ Font Size")`
   - `validate_setting("font_size_minimum", 20, {"font_size": 25})` -> returns `(True, None)`

### Manual GUI & Sync Verification
1. **No-Flicker Card Resets**: Change several values in the **Detection Configuration** card. Trigger the section reset button. Verify only detection fields reset in-place, the cursor focus and scroll position do not jump, and no layout flickering occurs.
2. **Persistence of Toggle State**: Collapse the advanced panel, close the application, restart, and confirm it remains collapsed. Expand the panel, restart, and confirm it remains expanded.
3. **Cloud Connection Interruption Recovery**:
   - Disconnect the local network interface.
   - Click "Reset All Settings". Verify settings revert immediately in the UI.
   - Reconnect the network. Wait or trigger sync; check the Supabase backend DB to verify the settings row is updated.
