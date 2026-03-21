"""
SnipShot Desktop - Register Window

User registration screen.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal

from api import api_client
from .theme import theme
from . import styles


class RegisterWindow(QWidget):
    """
    Registration screen for new users.

    Signals:
        register_success: Emitted when registration is successful
        show_login: Emitted when user wants to go back to login
    """

    register_success = pyqtSignal()
    show_login = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SnipShot - Create Account")
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
        cl = QVBoxLayout(self.container)
        cl.setContentsMargins(32, 32, 32, 32)
        cl.setSpacing(10)

        # Logo / Title
        self.title_label = QLabel("SnipShot")
        self.title_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel("Create your account")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.subtitle_label)

        cl.addSpacing(20)

        # Email
        self.email_label = QLabel("Email")
        cl.addWidget(self.email_label)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setMinimumHeight(44)
        cl.addWidget(self.email_input)

        cl.addSpacing(6)

        # Password
        self.password_label = QLabel("Password")
        cl.addWidget(self.password_label)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Create a password (min 6 characters)")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(44)
        cl.addWidget(self.password_input)

        cl.addSpacing(6)

        # Confirm password
        self.confirm_label = QLabel("Confirm Password")
        cl.addWidget(self.confirm_label)
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setMinimumHeight(44)
        self.confirm_input.returnPressed.connect(self._on_register)
        cl.addWidget(self.confirm_input)

        # Error / success labels
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        cl.addWidget(self.error_label)

        self.success_label = QLabel("")
        self.success_label.setWordWrap(True)
        self.success_label.hide()
        cl.addWidget(self.success_label)

        cl.addSpacing(10)

        # Register button
        self.register_btn = QPushButton("Create Account")
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.setMinimumHeight(48)
        self.register_btn.clicked.connect(self._on_register)
        cl.addWidget(self.register_btn)

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

        # Login link
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignCenter)
        self.login_text_label = QLabel("Already have an account?")
        login_layout.addWidget(self.login_text_label)
        self.login_btn = QPushButton("Sign in")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.clicked.connect(self._on_show_login)
        login_layout.addWidget(self.login_btn)
        cl.addLayout(login_layout)

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
        for lbl in (self.email_label, self.password_label, self.confirm_label):
            lbl.setStyleSheet(
                f"font-weight: 600; font-size: 13px; color: {c['text']}; margin-bottom: 4px; background-color: transparent;"
            )
        for inp in (self.email_input, self.password_input, self.confirm_input):
            inp.setStyleSheet(styles.input_field())
        self.error_label.setStyleSheet(f"color: {c['error']}; font-size: 12px; background-color: transparent;")
        self.success_label.setStyleSheet(f"color: {c['success']}; font-size: 12px; background-color: transparent;")
        self.register_btn.setStyleSheet(styles.primary_button())
        self.line1.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        self.line2.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        self.or_label.setStyleSheet(f"color: {c['text_secondary']}; padding: 0 10px; background-color: transparent;")
        self.login_text_label.setStyleSheet(f"color: {c['text_secondary']}; background-color: transparent;")
        self.login_btn.setStyleSheet(styles.text_button())

    # ── Actions ────────────────────────────────────────────────────────
    def _on_register(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if not email or not password or not confirm:
            self._show_error("Please fill in all fields")
            return
        if len(password) < 6:
            self._show_error("Password must be at least 6 characters")
            return
        if password != confirm:
            self._show_error("Passwords do not match")
            return

        self.register_btn.setEnabled(False)
        self.register_btn.setText("Creating account...")
        self.error_label.hide()
        self.success_label.hide()

        try:
            result = api_client.register(email, password)
            if result["success"]:
                data = result.get("data", {})
                if data.get("access_token"):
                    self.register_success.emit()
                else:
                    self._show_success("Account created! Please check your email to confirm.")
            else:
                self._show_error(result.get("error", "Registration failed"))
        except Exception as e:
            self._show_error(f"Connection error: {str(e)}")
        finally:
            self.register_btn.setEnabled(True)
            self.register_btn.setText("Create Account")

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
        self.success_label.hide()

    def _show_success(self, message: str):
        self.success_label.setText(message)
        self.success_label.show()
        self.error_label.hide()

    def _on_show_login(self):
        self.show_login.emit()

    def clear_fields(self):
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.error_label.hide()
        self.success_label.hide()
