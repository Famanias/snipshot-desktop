# CHANGELOG
# ─────────────────────────────────────────────────────────────────────
# - Replaced all addSpacing() values with SPACE constants (base-8 grid)
# - Replaced primary_button / text_button with StyledButton
# - Error label: left-border indicator + error_bg, pre-allocated with setVisible
# - Success label: same pattern with success colour
# - Added password strength indicator bar (QProgressBar, 0–4)
# - Added inline validation: ✓ / ✗ indicators on focusOut per field
# - apply_card_shadow() on auth container
# - All font/spacing reference FONT/SPACE constants
# ─────────────────────────────────────────────────────────────────────

"""
SnipShot Desktop - Register Window

User registration screen.
"""

import re

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QFrame, QProgressBar,
)
from PyQt5.QtCore import Qt, pyqtSignal

from api import api_client
from .theme import theme
from . import styles
from .styles import SPACE, FONT, apply_card_shadow
from .components import StyledButton


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

    # ── UI setup ───────────────────────────────────────────────────────

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(SPACE["lg"], SPACE["lg"], SPACE["lg"], SPACE["lg"])

        # Container card
        self.container = QFrame()
        self.container.setObjectName("authContainer")
        self.container.setMaximumWidth(450)

        cl = QVBoxLayout(self.container)
        cl.setContentsMargins(SPACE["xl"], SPACE["xl"], SPACE["xl"], SPACE["xl"])
        cl.setSpacing(SPACE["sm"])

        # Title
        self.title_label = QLabel("SnipShot")
        self.title_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.title_label)

        # Subtitle
        self.subtitle_label = QLabel("Create your account")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.subtitle_label)

        cl.addSpacing(SPACE["md"])

        # Email
        email_row = QHBoxLayout()
        self.email_label = QLabel("Email")
        email_row.addWidget(self.email_label)
        email_row.addStretch()
        self.email_check = QLabel("")
        self.email_check.setFixedWidth(24)
        email_row.addWidget(self.email_check)
        cl.addLayout(email_row)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setMinimumHeight(44)
        cl.addWidget(self.email_input)

        cl.addSpacing(SPACE["sm"])

        # Password
        pw_row = QHBoxLayout()
        self.password_label = QLabel("Password")
        pw_row.addWidget(self.password_label)
        pw_row.addStretch()
        self.password_check = QLabel("")
        self.password_check.setFixedWidth(24)
        pw_row.addWidget(self.password_check)
        cl.addLayout(pw_row)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Create a password (min 6 characters)")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.textChanged.connect(self._on_password_changed)
        cl.addWidget(self.password_input)

        # Password strength bar
        self.strength_bar = QProgressBar()
        self.strength_bar.setRange(0, 4)
        self.strength_bar.setValue(0)
        self.strength_bar.setTextVisible(False)
        self.strength_bar.setFixedHeight(SPACE["xs"])
        self.strength_bar.setStyleSheet(styles.password_strength_bar(0))
        cl.addWidget(self.strength_bar)

        cl.addSpacing(SPACE["sm"])

        # Confirm password
        conf_row = QHBoxLayout()
        self.confirm_label = QLabel("Confirm Password")
        conf_row.addWidget(self.confirm_label)
        conf_row.addStretch()
        self.confirm_check = QLabel("")
        self.confirm_check.setFixedWidth(24)
        conf_row.addWidget(self.confirm_check)
        cl.addLayout(conf_row)

        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setMinimumHeight(44)
        self.confirm_input.returnPressed.connect(self._on_register)
        cl.addWidget(self.confirm_input)

        # Error / success labels — pre-allocated
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        cl.addWidget(self.error_label)

        self.success_label = QLabel("")
        self.success_label.setWordWrap(True)
        self.success_label.setVisible(False)
        cl.addWidget(self.success_label)

        cl.addSpacing(SPACE["md"])

        # Register button
        self.register_btn = StyledButton("Create Account", variant="primary")
        self.register_btn.setMinimumHeight(48)
        self.register_btn.clicked.connect(self._on_register)
        cl.addWidget(self.register_btn)

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

        # Login link — ghost button, own row
        self.login_btn = StyledButton("Sign in", variant="ghost")
        self.login_btn.clicked.connect(self._on_show_login)
        cl.addWidget(self.login_btn)

        layout.addWidget(self.container)

        apply_card_shadow(self.container)

        # Wire up focus-out validation
        self.email_input.editingFinished.connect(self._validate_email)
        self.password_input.editingFinished.connect(self._validate_password)
        self.confirm_input.editingFinished.connect(self._validate_confirm)

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
        for lbl in (self.email_label, self.password_label, self.confirm_label):
            lbl.setStyleSheet(
                f"font-weight: {FONT['label']['weight']}; font-size: {FONT['label']['size']}px; "
                f"color: {c['text']}; margin-bottom: {SPACE['xs']}px; background-color: transparent;"
            )
        for inp in (self.email_input, self.password_input, self.confirm_input):
            inp.setStyleSheet(styles.input_field())
        self.error_label.setStyleSheet(
            f"color: {c['error']}; font-size: {FONT['caption']['size']}px; "
            f"background-color: {c['error_bg']}; "
            f"border-left: 3px solid {c['error']}; "
            f"border-radius: 6px; padding: {SPACE['sm']}px {SPACE['md']}px;"
        )
        self.success_label.setStyleSheet(
            f"color: {c['success']}; font-size: {FONT['caption']['size']}px; "
            f"background-color: {c['success_bg']}; "
            f"border-left: 3px solid {c['success']}; "
            f"border-radius: 6px; padding: {SPACE['sm']}px {SPACE['md']}px;"
        )
        self.line1.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        self.line2.setStyleSheet(f"background-color: {c['border']}; color: {c['border']};")
        self.or_label.setStyleSheet(
            f"color: {c['text_secondary']}; padding: 0 {SPACE['sm']}px; background-color: transparent;"
        )
        for chk in (self.email_check, self.password_check, self.confirm_check):
            chk.setStyleSheet("background-color: transparent;")

    # ── Inline validation ──────────────────────────────────────────────

    def _set_check(self, label: QLabel, valid: bool):
        c = theme.c
        if valid:
            label.setText("\u2713")
            label.setStyleSheet(
                f"color: {c['success']}; font-size: {FONT['body']['size']}px; "
                "font-weight: 700; background-color: transparent;"
            )
        else:
            label.setText("\u2717")
            label.setStyleSheet(
                f"color: {c['error']}; font-size: {FONT['body']['size']}px; "
                "font-weight: 700; background-color: transparent;"
            )

    def _validate_email(self):
        text = self.email_input.text().strip()
        if not text:
            self.email_check.setText("")
            return
        valid = bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text))
        self._set_check(self.email_check, valid)

    def _validate_password(self):
        text = self.password_input.text()
        if not text:
            self.password_check.setText("")
            return
        self._set_check(self.password_check, len(text) >= 6)

    def _validate_confirm(self):
        text = self.confirm_input.text()
        if not text:
            self.confirm_check.setText("")
            return
        self._set_check(self.confirm_check, text == self.password_input.text())

    # ── Password strength ──────────────────────────────────────────────

    @staticmethod
    def _calc_strength(password: str) -> int:
        if not password:
            return 0
        if len(password) < 6:
            return 1
        score = 0
        if len(password) >= 6:
            score += 1
        if len(password) >= 10:
            score += 1
        if re.search(r"[A-Z]", password) and re.search(r"[a-z]", password):
            score += 1
        if re.search(r"\d", password):
            score += 1
        if re.search(r"[^A-Za-z0-9]", password):
            score += 1
        return min(score, 4)

    def _on_password_changed(self, text: str):
        level = self._calc_strength(text)
        self.strength_bar.setValue(level)
        self.strength_bar.setStyleSheet(styles.password_strength_bar(level))

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
        self.error_label.setVisible(False)
        self.success_label.setVisible(False)

        try:
            result = api_client.register(email, password)
            if result["success"]:
                # Check if user is immediately authenticated (no email confirmation required)
                # data = result.get("data", {})
                # if data.get("access_token"):
                if api_client.access_token:
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
        self.error_label.setVisible(True)
        self.success_label.setVisible(False)

    def _show_success(self, message: str):
        self.success_label.setText(message)
        self.success_label.setVisible(True)
        self.error_label.setVisible(False)

    def _on_show_login(self):
        self.show_login.emit()

    def clear_fields(self):
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.error_label.setVisible(False)
        self.success_label.setVisible(False)
        self.strength_bar.setValue(0)
        self.strength_bar.setStyleSheet(styles.password_strength_bar(0))
        for chk in (self.email_check, self.password_check, self.confirm_check):
            chk.setText("")
