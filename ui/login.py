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
        layout.setContentsMargins(24, 24, 24, 24)

        # Container card
        self.container = QFrame()
        self.container.setObjectName("authContainer")
        self.container.setMaximumWidth(450)
        self.container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        cl = QVBoxLayout(self.container)
        cl.setContentsMargins(32, 32, 32, 32)
        cl.setSpacing(12)

        # Logo / Title
        self.title_label = QLabel("SnipShot")
        self.title_label.setObjectName("appTitle")
        self.title_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel("Sign in to your account")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.subtitle_label)

        cl.addSpacing(20)

        # Email field
        self.email_label = QLabel("Email")
        cl.addWidget(self.email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setMinimumHeight(44)
        cl.addWidget(self.email_input)

        cl.addSpacing(8)

        # Password field
        self.password_label = QLabel("Password")
        cl.addWidget(self.password_label)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.returnPressed.connect(self._on_login)
        cl.addWidget(self.password_input)

        # Error label
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        cl.addWidget(self.error_label)

        cl.addSpacing(10)

        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setMinimumHeight(48)
        self.login_btn.clicked.connect(self._on_login)
        cl.addWidget(self.login_btn)

        cl.addSpacing(20)

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

        cl.addSpacing(10)

        # Register link
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignCenter)
        self.register_text_label = QLabel("Don't have an account?")
        register_layout.addWidget(self.register_text_label)
        self.register_btn = QPushButton("Create account")
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.clicked.connect(self._on_show_register)
        register_layout.addWidget(self.register_btn)
        cl.addLayout(register_layout)

        cl.addSpacing(12)

        # Local mode button
        self.local_mode_btn = QPushButton("\U0001F4BB  Use Local Mode")
        self.local_mode_btn.setCursor(Qt.PointingHandCursor)
        self.local_mode_btn.setMinimumHeight(44)
        self.local_mode_btn.clicked.connect(self._on_local_mode)
        cl.addWidget(self.local_mode_btn)

        self.local_hint_label = QLabel("Save files locally without an account")
        self.local_hint_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.local_hint_label)

        layout.addWidget(self.container)

        self._apply_styles()

    # ── Theme-aware styling ────────────────────────────────────────────
    def _apply_styles(self, _mode=None):
        c = theme.c
        self.setStyleSheet(f"background-color: {c['bg']};")
        self.container.setStyleSheet(styles.auth_container())
        self.title_label.setStyleSheet(
            f"font-size: 32px; font-weight: 700; color: {c['primary']}; "
            "background-color: transparent; padding: 4px 0 8px 0; min-height: 52px;"
        )
        self.subtitle_label.setStyleSheet(
            f"color: {c['text_secondary']}; font-size: 14px; background-color: transparent;"
        )
        self.email_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {c['text']}; margin-bottom: 4px; background-color: transparent;"
        )
        self.email_input.setStyleSheet(styles.input_field())
        self.password_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {c['text']}; margin-bottom: 4px; background-color: transparent;"
        )
        self.password_input.setStyleSheet(styles.input_field())
        self.error_label.setStyleSheet(f"color: {c['error']}; font-size: 12px; background-color: transparent;")
        self.login_btn.setStyleSheet(styles.primary_button())
        self.line1.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        self.line2.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        self.or_label.setStyleSheet(f"color: {c['text_secondary']}; padding: 0 10px; background-color: transparent;")
        self.register_text_label.setStyleSheet(f"color: {c['text_secondary']}; background-color: transparent;")
        self.register_btn.setStyleSheet(styles.text_button())
        self.local_mode_btn.setStyleSheet(styles.local_mode_button())
        self.local_hint_label.setStyleSheet(
            f"color: {c['text_tertiary']}; font-size: 11px; background-color: transparent;"
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
        self.error_label.hide()

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
        self.error_label.show()

    def _on_show_register(self):
        self.show_register.emit()

    def _on_local_mode(self):
        self.local_mode_requested.emit()

    def clear_fields(self):
        self.email_input.clear()
        self.password_input.clear()
        self.error_label.hide()
