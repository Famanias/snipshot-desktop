"""
SnipShot Desktop - Register Window

User registration screen.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal

from api import api_client


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
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Container card - flexible sizing with max-width
        container = QFrame()
        container.setObjectName("authContainer")
        container.setStyleSheet("""
            QFrame#authContainer {
                background-color: #FFFFFF;
                border: 1px solid #DADCE0;
                border-radius: 12px;
            }
        """)
        container.setMaximumWidth(450)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(32, 32, 32, 32)
        container_layout.setSpacing(10)
        
        # Logo/Title
        title = QLabel("SnipShot")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 700;
            color: #4285F4;
            margin-bottom: 10px;
        """)
        container_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Create your account")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("color: #5F6368; font-size: 14px;")
        container_layout.addWidget(subtitle)
        
        container_layout.addSpacing(20)
        
        # Email field
        email_label = QLabel("Email")
        email_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #202124; margin-bottom: 4px;")
        container_layout.addWidget(email_label)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setMinimumHeight(44)
        self.email_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 1px solid #DADCE0;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #4285F4;
                padding: 11px 15px;
            }
        """)
        container_layout.addWidget(self.email_input)
        
        container_layout.addSpacing(6)
        
        # Password field
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #202124; margin-bottom: 4px;")
        container_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Create a password (min 6 characters)")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(44)
        self.password_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 1px solid #DADCE0;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #4285F4;
                padding: 11px 15px;
            }
        """)
        container_layout.addWidget(self.password_input)
        
        container_layout.addSpacing(6)
        
        # Confirm Password field
        confirm_label = QLabel("Confirm Password")
        confirm_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #202124; margin-bottom: 4px;")
        container_layout.addWidget(confirm_label)
        
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("Confirm your password")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setMinimumHeight(44)
        self.confirm_input.setStyleSheet("""
            QLineEdit {
                padding: 12px 16px;
                border: 1px solid #DADCE0;
                border-radius: 6px;
                font-size: 14px;
                background-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #4285F4;
                padding: 11px 15px;
            }
        """)
        self.confirm_input.returnPressed.connect(self._on_register)
        container_layout.addWidget(self.confirm_input)
        
        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #EA4335; font-size: 12px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)
        
        # Success label (hidden by default)
        self.success_label = QLabel("")
        self.success_label.setStyleSheet("color: #34A853; font-size: 12px;")
        self.success_label.setWordWrap(True)
        self.success_label.hide()
        container_layout.addWidget(self.success_label)
        
        container_layout.addSpacing(10)
        
        # Register button
        self.register_btn = QPushButton("Create Account")
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.setMinimumHeight(48)
        self.register_btn.setStyleSheet("""
            QPushButton {
                background-color: #4285F4;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 14px 24px;
                font-size: 15px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3367D6;
            }
            QPushButton:pressed {
                background-color: #2A56C6;
            }
            QPushButton:disabled {
                background-color: #DADCE0;
            }
        """)
        self.register_btn.clicked.connect(self._on_register)
        container_layout.addWidget(self.register_btn)
        
        container_layout.addSpacing(20)
        
        # Divider
        divider_layout = QHBoxLayout()
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setStyleSheet("background-color: #DADCE0;")
        divider_layout.addWidget(line1)
        
        divider_layout.addStretch()
        
        or_label = QLabel("or")
        or_label.setStyleSheet("color: #5F6368; padding: 0 10px;")
        divider_layout.addWidget(or_label)
        
        divider_layout.addStretch()
        
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setStyleSheet("background-color: #DADCE0;")
        divider_layout.addWidget(line2)
        
        container_layout.addLayout(divider_layout)
        
        container_layout.addSpacing(10)
        
        # Login link
        login_layout = QHBoxLayout()
        login_layout.setAlignment(Qt.AlignCenter)
        
        login_text = QLabel("Already have an account?")
        login_text.setStyleSheet("color: #5F6368;")
        login_layout.addWidget(login_text)
        
        self.login_btn = QPushButton("Sign in")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4285F4;
                border: none;
                font-weight: 600;
                padding: 0;
            }
            QPushButton:hover {
                text-decoration: underline;
            }
        """)
        self.login_btn.clicked.connect(self._on_show_login)
        login_layout.addWidget(self.login_btn)
        
        container_layout.addLayout(login_layout)
        
        layout.addWidget(container)
    
    def _on_register(self):
        """Handle register button click"""
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()
        
        # Validation
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
                # Check if email confirmation is required
                data = result.get("data", {})
                if data.get("access_token"):
                    # Logged in immediately
                    self.register_success.emit()
                else:
                    # Email confirmation required
                    self._show_success("Account created! Please check your email to confirm.")
            else:
                self._show_error(result.get("error", "Registration failed"))
        except Exception as e:
            self._show_error(f"Connection error: {str(e)}")
        finally:
            self.register_btn.setEnabled(True)
            self.register_btn.setText("Create Account")
    
    def _show_error(self, message: str):
        """Show error message"""
        self.error_label.setText(message)
        self.error_label.show()
        self.success_label.hide()
    
    def _show_success(self, message: str):
        """Show success message"""
        self.success_label.setText(message)
        self.success_label.show()
        self.error_label.hide()
    
    def _on_show_login(self):
        """Switch to login screen"""
        self.show_login.emit()
    
    def clear_fields(self):
        """Clear all input fields"""
        self.email_input.clear()
        self.password_input.clear()
        self.confirm_input.clear()
        self.error_label.hide()
        self.success_label.hide()
