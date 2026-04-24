# CHANGELOG
# ─────────────────────────────────────────────────────────────────────
# - Replaced all addSpacing() values with SPACE constants (base-8 grid)
# - Replaced primary_button / text_button / local_mode_button with StyledButton
# - Added app description ("Translate manga …") beneath title
# - Restructured button hierarchy: Sign In (primary) → divider →
#   Create account (ghost, own row) → Use Local Mode (secondary, no emoji)
# - Error label now uses left-border indicator + error_bg background,
#   pre-allocated with setVisible(False) (no hide/show layout jump)
# - apply_card_shadow() on auth container
# - All font/spacing values reference FONT/SPACE constants
# ─────────────────────────────────────────────────────────────────────

"""
SnipShot Desktop - Login Window

User authentication screen.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal

from api import api_client
from .theme import theme
from . import styles
from .styles import SPACE, FONT, apply_card_shadow
from .components import StyledButton


class LoginWindow(QWidget):
    """
    Login screen with email/password authentication.

    Signals:
        login_success: Emitted when login is successful
        show_register: Emitted when user wants to create account
        local_mode_requested: Emitted when user wants local-only mode
    """

    login_success = pyqtSignal()
    show_register = pyqtSignal()
    local_mode_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SnipShot - Login")
        self.setMinimumSize(900, 600)
        self._setup_ui()
        theme.theme_changed.connect(self._apply_styles)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])

        # Container card
        self.container = QFrame()
        self.container.setObjectName("authContainer")
        self.container.setMaximumWidth(450)
        self.container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        cl = QVBoxLayout(self.container)
        cl.setContentsMargins(SPACE["xl"], SPACE["xl"], SPACE["xl"], SPACE["xl"])
        cl.setSpacing(SPACE["sm"])

        # Logo / Title
        self.title_label = QLabel("SnipShot")
        self.title_label.setObjectName("appTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.title_label)

        # App description
        self.desc_label = QLabel("Translate manga and text from screenshots instantly")
        self.desc_label.setAlignment(Qt.AlignCenter)
        self.desc_label.setWordWrap(True)
        self.desc_label.setMaximumWidth(320)
        cl.addWidget(self.desc_label, alignment=Qt.AlignCenter)

        # Subtitle
        self.subtitle_label = QLabel("Sign in to your account")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.subtitle_label)

        cl.addSpacing(SPACE["md"])

        # Email field
        self.email_label = QLabel("Email")
        cl.addWidget(self.email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setMinimumHeight(44)
        cl.addWidget(self.email_input)

        cl.addSpacing(SPACE["sm"])

        # Password field
        self.password_label = QLabel("Password")
        cl.addWidget(self.password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.returnPressed.connect(self._on_login)
        cl.addWidget(self.password_input)

        # Error label — pre-allocated, hidden via setVisible
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        cl.addWidget(self.error_label)

        cl.addSpacing(SPACE["md"])

        # Sign In button
        self.login_btn = StyledButton("Sign In", variant="primary")
        self.login_btn.setMinimumHeight(48)
        self.login_btn.clicked.connect(self._on_login)
        cl.addWidget(self.login_btn)

        cl.addSpacing(SPACE["md"])

        # Divider
        divider_layout = QHBoxLayout()
        self.line1 = QFrame()
        self.line1.setFrameShape(QFrame.HLine)
        divider_layout.addWidget(self.line1)
        divider_layout.addStretch()
        self.or_label = QLabel("or")
        divider_layout.addWidget(self.or_label)
        divider_layout.addStretch()
        self.line2 = QFrame()
        self.line2.setFrameShape(QFrame.HLine)
        divider_layout.addWidget(self.line2)
        cl.addLayout(divider_layout)

        cl.addSpacing(SPACE["sm"])

        # Create account — ghost button, own row
        self.register_btn = StyledButton("Create account", variant="ghost")
        self.register_btn.clicked.connect(self._on_show_register)
        cl.addWidget(self.register_btn)

        cl.addSpacing(SPACE["sm"])

        # Local mode button — secondary, no emoji
        self.local_mode_btn = StyledButton("Use Local Mode", variant="secondary")
        self.local_mode_btn.setMinimumHeight(44)
        self.local_mode_btn.clicked.connect(self._on_local_mode)
        cl.addWidget(self.local_mode_btn)

        self.local_hint_label = QLabel("Save files locally without an account")
        self.local_hint_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.local_hint_label)

        layout.addWidget(self.container)

        apply_card_shadow(self.container)
        self._apply_styles()

    # ── Theme-aware styling ────────────────────────────────────────────
    def _apply_styles(self, _mode=None):
        c = theme.c
        self.setStyleSheet(f"background-color: {c['bg']};")
        self.container.setStyleSheet(styles.auth_container())
        apply_card_shadow(self.container)
        self.title_label.setStyleSheet(
            f"font-size: {FONT['display']['size']}px; font-weight: {FONT['display']['weight']}; "
            f"color: {c['primary']}; background-color: transparent; "
            f"padding: {SPACE['xs']}px 0 {SPACE['sm']}px 0; min-height: 52px;"
        )
        self.desc_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; "
            "background-color: transparent;"
        )
        self.subtitle_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; "
            "background-color: transparent;"
        )
        for lbl in (self.email_label, self.password_label):
            lbl.setStyleSheet(
                f"font-weight: {FONT['label']['weight']}; font-size: {FONT['label']['size']}px; "
                f"color: {c['text']}; margin-bottom: {SPACE['xs']}px; background-color: transparent;"
            )
        self.email_input.setStyleSheet(styles.input_field())
        self.password_input.setStyleSheet(styles.input_field())
        self.error_label.setStyleSheet(
            f"color: {c['error']}; font-size: {FONT['caption']['size']}px; "
            f"background-color: {c['error_bg']}; "
            f"border-left: 3px solid {c['error']}; "
            f"border-radius: 6px; padding: {SPACE['sm']}px {SPACE['md']}px;"
        )
        self.line1.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        self.line2.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        self.or_label.setStyleSheet(
            f"color: {c['text_secondary']}; padding: 0 {SPACE['sm']}px; background-color: transparent;"
        )
        self.local_hint_label.setStyleSheet(
            f"color: {c['text_tertiary']}; font-size: {FONT['hint']['size']}px; "
            "background-color: transparent;"
        )

    # ── Actions ────────────────────────────────────────────────────────
    def _on_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not email or not password:
            self._show_error("Please enter email and password")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in...")
        self.error_label.setVisible(False)

        try:
            result = api_client.login(email, password)
            if result["success"]:
                self.login_success.emit()
            else:
                self._show_error(result.get("error", "Login failed"))
        except Exception as e:
            self._show_error(f"Connection error: {str(e)}")
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Sign In")

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _on_show_register(self):
        self.show_register.emit()

    def _on_local_mode(self):
        self.local_mode_requested.emit()

    def clear_fields(self):
        self.email_input.clear()
        self.password_input.clear()
        self.error_label.setVisible(False)
