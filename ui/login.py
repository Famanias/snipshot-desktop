"""
SnipShot Desktop - Login Window

User authentication screen.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QSpacerItem, 
    QSizePolicy, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap

from api import api_client


class LoginWindow(QWidget):
    """
    Login screen with email/password authentication.
    
    Signals:
        login_success: Emitted when login is successful
        show_register: Emitted when user wants to create account
    """
    
    login_success = pyqtSignal()
    show_register = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SnipShot - Login")
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
        container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(32, 32, 32, 32)
        container_layout.setSpacing(12)
        
        # Logo/Title
        title = QLabel("SnipShot")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size: 32px;
            font-weight: 700;
            color: #4285F4;
            margin-bottom: 10px;
        """)
        container_layout.addWidget(title)
        
        # Subtitle
        subtitle = QLabel("Sign in to your account")
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
        
        container_layout.addSpacing(8)
        
        # Password field
        password_label = QLabel("Password")
        password_label.setStyleSheet("font-weight: 600; font-size: 13px; color: #202124; margin-bottom: 4px;")
        container_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
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
        self.password_input.returnPressed.connect(self._on_login)
        container_layout.addWidget(self.password_input)
        
        # Error label (hidden by default)
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #EA4335; font-size: 12px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)
        
        container_layout.addSpacing(10)
        
        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.PointingHandCursor)
        self.login_btn.setMinimumHeight(48)
        self.login_btn.setStyleSheet("""
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
        self.login_btn.clicked.connect(self._on_login)
        container_layout.addWidget(self.login_btn)
        
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
        
        # Create account link
        register_layout = QHBoxLayout()
        register_layout.setAlignment(Qt.AlignCenter)
        
        register_text = QLabel("Don't have an account?")
        register_text.setStyleSheet("color: #5F6368;")
        register_layout.addWidget(register_text)
        
        self.register_btn = QPushButton("Create account")
        self.register_btn.setCursor(Qt.PointingHandCursor)
        self.register_btn.setStyleSheet("""
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
        self.register_btn.clicked.connect(self._on_show_register)
        register_layout.addWidget(self.register_btn)
        
        container_layout.addLayout(register_layout)
        
        layout.addWidget(container)
    
    def _on_login(self):
        """Handle login button click"""
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
        """Show error message"""
        self.error_label.setText(message)
        self.error_label.show()
    
    def _on_show_register(self):
        """Switch to register screen"""
        self.show_register.emit()
    
    def clear_fields(self):
        """Clear all input fields"""
        self.email_input.clear()
        self.password_input.clear()
        self.error_label.hide()
