import hashlib
import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, 
    QHBoxLayout, QFrame, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from database.connection import get_session
from database.models import User, Staff, Role, Permission
from sqlalchemy.orm import joinedload
from config import config
from ui.theme import get_theme_stylesheet

def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        salt_hex, hash_hex = stored_password.split(":")
        salt = bytes.fromhex(salt_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return pwd_hash.hex() == hash_hex
    except Exception:
        return False

class LoginWindow(QWidget):
    login_success = Signal(object)  # Emits User model object on success
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orion SMS - Sign In")
        self.setFixedSize(400, 500)
        self.setStyleSheet(get_theme_stylesheet(config.get("theme", "dark")))
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # Container Card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(20)
        card_layout.setContentsMargins(30, 40, 30, 40)
        
        # Logo placeholder or Title text
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = config.get("school_logo", "")
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled)
        else:
            self.logo_label.setText("ORION")
            self.logo_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #3b82f6; letter-spacing: 2px;")
            
        self.subtitle_label = QLabel(config.get("school_name", "School Management System"))
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #94a3b8; margin-bottom: 20px;")
        
        # Inputs
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setObjectName("username")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setObjectName("password")
        
        # Sign In Button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setMinimumHeight(40)
        
        # Help label
        self.help_label = QLabel("Contact admin if you forgot your credentials.")
        self.help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_label.setStyleSheet("font-size: 11px; color: #64748b; margin-top: 10px;")
        
        card_layout.addWidget(self.logo_label)
        card_layout.addWidget(self.subtitle_label)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.login_btn)
        card_layout.addWidget(self.help_label)
        
        main_layout.addWidget(card)
        
    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Please fill in all fields.")
            return
            
        session = get_session()
        try:
            # Query user with eager loading of all relationships needed by the app
            user = (
                session.query(User)
                .options(
                    joinedload(User.role).joinedload(Role.permissions),
                    joinedload(User.staff_profile)
                )
                .filter(User.username == username)
                .first()
            )
            if not user or not user.is_active:
                QMessageBox.critical(self, "Login Failed", "Invalid username or inactive account.")
                return
                
            if verify_password(user.password_hash, password):
                # Successful login
                # Load profile details to verify
                staff_name = "System Administrator"
                if user.staff_profile:
                    staff_name = f"{user.staff_profile.first_name} {user.staff_profile.last_name}"
                
                # Detach user from session so it can be safely used after session closes
                from sqlalchemy.orm import make_transient
                session.expunge(user)
                make_transient(user)
                
                # Show greeting message
                QMessageBox.information(self, "Welcome", f"Access Granted. Welcome, {staff_name} ({user.role.name})!")
                self.login_success.emit(user)
            else:
                QMessageBox.critical(self, "Login Failed", "Invalid password. Please try again.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"An error occurred during authentication:\n{str(e)}")
        finally:
            session.close()

    def keyPressEvent(self, event):
        # Enter key triggers login
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.handle_login()
        else:
            super().keyPressEvent(event)
