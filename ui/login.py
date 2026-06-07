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
    QDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon

from api import api_client
from utils import resource_path
from .theme import theme
from . import styles
from .styles import SPACE, FONT, apply_card_shadow
from .components import StyledButton


class ForgotPasswordDialog(QDialog):
    """Dialog prompting user for email to reset password."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reset Password")
        self.setMinimumWidth(400)
        self._status_is_error = True
        self._setup_ui()
        theme.theme_changed.connect(self._apply_styles)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE["md"])
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])

        # Title
        self.title_label = QLabel("Reset Password")
        layout.addWidget(self.title_label)

        # Description hint
        self.hint_label = QLabel("Enter your email address and we'll send you a link to reset your password.")
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        # Email field layout
        self.email_label = QLabel("Email Address")
        layout.addWidget(self.email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("name@example.com")
        self.email_input.setMinimumHeight(44)
        self.email_input.returnPressed.connect(self._on_submit)
        layout.addWidget(self.email_input)

        # Status/error banner (hidden by default)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        # Buttons layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = StyledButton("Cancel", variant="secondary")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.submit_btn = StyledButton("Send Reset Link", variant="primary")
        self.submit_btn.clicked.connect(self._on_submit)
        button_layout.addWidget(self.submit_btn)

        layout.addLayout(button_layout)
        self._apply_styles()

    def _apply_styles(self, _mode=None):
        c = theme.c
        self.setStyleSheet(f"background-color: {c['bg']};")
        self.title_label.setStyleSheet(
            f"font-size: {FONT['heading']['size']}px; font-weight: {FONT['heading']['weight']}; "
            f"color: {c['text']}; background-color: transparent;"
        )
        self.hint_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: {FONT['body']['size']}px; "
            f"background-color: transparent;"
        )
        self.email_label.setStyleSheet(
            f"font-weight: {FONT['label']['weight']}; font-size: {FONT['label']['size']}px; "
            f"color: {c['text']}; margin-bottom: {SPACE['xs']}px; background-color: transparent;"
        )
        self.email_input.setStyleSheet(styles.dialog_input())
        if self.status_label.isVisible():
            self._update_status_style()

    def _on_submit(self):
        email = self.email_input.text().strip()
        if not email:
            self._show_status("Please enter your email address", is_error=True)
            return

        # Simple email pattern validation
        if "@" not in email or "." not in email:
            self._show_status("Please enter a valid email address", is_error=True)
            return

        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Sending...")
        self.email_input.setEnabled(False)
        self.status_label.setVisible(False)

        try:
            res = api_client.reset_password_for_email(email)
            if res.get("success"):
                self._show_status("Password reset email sent. Check your inbox.", is_error=False)
                self.submit_btn.setText("Sent")
                self.cancel_btn.setText("Close")
            else:
                error_msg = res.get("error", "An error occurred.")
                self._show_status(f"Error: {error_msg}", is_error=True)
                self.submit_btn.setEnabled(True)
                self.submit_btn.setText("Send Reset Link")
                self.email_input.setEnabled(True)
        except Exception as e:
            self._show_status(f"Connection error: {str(e)}", is_error=True)
            self.submit_btn.setEnabled(True)
            self.submit_btn.setText("Send Reset Link")
            self.email_input.setEnabled(True)

    def _show_status(self, message: str, is_error: bool = True):
        self._status_is_error = is_error
        self.status_label.setText(message)
        self._update_status_style()
        self.status_label.setVisible(True)

    def _update_status_style(self):
        c = theme.c
        if self._status_is_error:
            self.status_label.setStyleSheet(
                f"color: {c['error']}; font-size: {FONT['caption']['size']}px; "
                f"background-color: {c['error_bg']}; "
                f"border-left: 3px solid {c['error']}; "
                f"border-radius: 6px; padding: {SPACE['sm']}px {SPACE['md']}px;"
            )
        else:
            success_color = c.get('success', '#10B981')
            success_bg = c.get('success_bg', '#ECFDF5')
            self.status_label.setStyleSheet(
                f"color: {success_color}; font-size: {FONT['caption']['size']}px; "
                f"background-color: {success_bg}; "
                f"border-left: 3px solid {success_color}; "
                f"border-radius: 6px; padding: {SPACE['sm']}px {SPACE['md']}px;"
            )


class LoginWindow(QWidget):
    """
    Login screen with email/password authentication.

    Signals:
        login_success: Emitted when login is successful
        show_register: Emitted when user wants to create account
        offline_mode_requested: Emitted when user wants offline-only mode
    """

    login_success = pyqtSignal()
    show_register = pyqtSignal()
    offline_mode_requested = pyqtSignal()

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
        cl.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])
        cl.setSpacing(SPACE["sm"])

        # Logo / Title
        self.title_label = QLabel("SnipShot")
        self.title_label.setObjectName("appTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.title_label)

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
        pw_header_layout = QHBoxLayout()
        pw_header_layout.setContentsMargins(0, 0, 0, 0)
        self.password_label = QLabel("Password")
        self.forgot_password_btn = QPushButton("Forgot password?")
        self.forgot_password_btn.setCursor(Qt.PointingHandCursor)
        self.forgot_password_btn.setFocusPolicy(Qt.NoFocus)
        self.forgot_password_btn.clicked.connect(self._on_forgot_password)
        pw_header_layout.addWidget(self.password_label)
        pw_header_layout.addStretch()
        pw_header_layout.addWidget(self.forgot_password_btn)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.returnPressed.connect(self._on_login)

        # Password visibility toggle button
        self.toggle_password_btn = QPushButton(self.password_input)
        self.toggle_password_btn.setCursor(Qt.PointingHandCursor)
        self.toggle_password_btn.setFixedSize(24, 24)
        self.toggle_password_btn.setFocusPolicy(Qt.NoFocus)
        self.toggle_password_btn.setStyleSheet(
            "background: transparent; border: none; padding: 0; min-height: 0; min-width: 0;"
        )

        self.visible_icon_path = resource_path("ui/icons/visibility_24dp_999999_FILL0_wght400_GRAD0_opsz24.svg")
        self.hidden_icon_path = resource_path("ui/icons/visibility_off_24dp_999999_FILL0_wght400_GRAD0_opsz24.svg")
        self.toggle_password_btn.setIcon(QIcon(self.hidden_icon_path))
        self.toggle_password_btn.clicked.connect(self._toggle_password_visibility)

        # Place button inside password input (aligned to right)
        pw_layout = QHBoxLayout(self.password_input)
        pw_layout.setContentsMargins(0, 0, SPACE["sm"], 0)
        pw_layout.addStretch()
        pw_layout.addWidget(self.toggle_password_btn)
        self.password_input.setLayout(pw_layout)
        cl.addWidget(self.password_input)

        # Error label — pre-allocated, hidden via setVisible
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        cl.addWidget(self.error_label)

        cl.addLayout(pw_header_layout)

        cl.addSpacing(SPACE["md"])

        # Sign In button
        self.login_btn = StyledButton("Sign In", variant="primary")
        self.login_btn.setMinimumHeight(44)
        self.login_btn.clicked.connect(self._on_login)
        cl.addWidget(self.login_btn)

        cl.addSpacing(SPACE["md"])

        cl.addSpacing(SPACE["sm"])

        # Create account — ghost button, own row
        self.register_btn = StyledButton("Create account", variant="ghost")
        self.register_btn.clicked.connect(self._on_show_register)
        cl.addWidget(self.register_btn)

        cl.addSpacing(SPACE["md"])

        # Offline mode button — secondary, no emoji
        self.offline_mode_btn = StyledButton("Use Offline Mode", variant="secondary")
        self.offline_mode_btn.setMinimumHeight(44)
        self.offline_mode_btn.clicked.connect(self._on_offline_mode)
        cl.addWidget(self.offline_mode_btn)

        cl.addSpacing(SPACE["xs"])

        self.local_hint_label = QLabel("use the app locally (dev mode)")
        self.local_hint_label.setAlignment(Qt.AlignCenter)
        self.local_hint_label.setWordWrap(True)
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
        self.forgot_password_btn.setStyleSheet(
            f"""
            QPushButton {{
                background: transparent;
                border: none;
                padding: 0;
                min-height: 0;
                min-width: 0;
                color: {c['primary']};
                font-size: {FONT['caption']['size']}px;
                font-weight: 500;
                margin-bottom: {SPACE['xs']}px;
            }}
            QPushButton:hover {{
                text-decoration: underline;
                color: {c['primary_dark']};
            }}
            """
        )
        
        # Override padding-right to avoid password text overlapping the toggle button
        pw_padding_right = SPACE["xl"] + SPACE["xs"]  # 32 + 4 = 36px
        pw_padding_right_focus = pw_padding_right - 1  # 35px
        self.password_input.setStyleSheet(
            styles.input_field() + f"""
            QLineEdit {{
                padding-right: {pw_padding_right}px;
            }}
            QLineEdit:focus {{
                padding-right: {pw_padding_right_focus}px;
            }}
            """
        )
        self.error_label.setStyleSheet(
            f"color: {c['error']}; font-size: {FONT['caption']['size']}px; "
            f"background-color: {c['error_bg']}; "
            f"border-left: 3px solid {c['error']}; "
            f"border-radius: 6px; padding: {SPACE['sm']}px {SPACE['md']}px;"
        )
        # self.line1.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        # self.line2.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
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

    def _on_offline_mode(self):
        self.offline_mode_requested.emit()

    def _toggle_password_visibility(self):
        if self.password_input.echoMode() == QLineEdit.Password:
            self.password_input.setEchoMode(QLineEdit.Normal)
            self.toggle_password_btn.setIcon(QIcon(self.visible_icon_path))
        else:
            self.password_input.setEchoMode(QLineEdit.Password)
            self.toggle_password_btn.setIcon(QIcon(self.hidden_icon_path))

    def _on_forgot_password(self):
        dialog = ForgotPasswordDialog(self)
        dialog.exec_()

    def clear_fields(self):
        self.email_input.clear()
        self.password_input.clear()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.toggle_password_btn.setIcon(QIcon(self.hidden_icon_path))
        self.error_label.setVisible(False)
