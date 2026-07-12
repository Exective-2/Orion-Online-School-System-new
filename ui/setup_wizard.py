import os
import shutil
import hashlib
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QPushButton, QStackedWidget, 
    QFileDialog, QMessageBox, QFormLayout, QFrame, QApplication
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon

from config import config, save_config
from ui.theme import get_theme_stylesheet
from database.connection import init_db, get_session
from database.seed import seed_database, hash_password
from database.models import User, Staff

class SetupWizardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Orion SMS - Installation Setup Wizard")
        self.setFixedSize(580, 520)
        self.setStyleSheet(get_theme_stylesheet("dark"))
        
        self.selected_logo_path = ""
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Header block
        self.header_label = QLabel("System Setup Wizard")
        self.header_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #3b82f6;")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.header_label)
        
        # Stacked Pages
        self.stacked_widget = QStackedWidget()
        
        self.page_db = self.create_db_page()
        self.page_school = self.create_school_page()
        self.page_admin = self.create_admin_page()
        
        self.stacked_widget.addWidget(self.page_db)
        self.stacked_widget.addWidget(self.page_school)
        self.stacked_widget.addWidget(self.page_admin)
        
        main_layout.addWidget(self.stacked_widget)
        
        # Bottom Navigation buttons
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("Back")
        self.back_btn.setObjectName("secondary_btn")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        nav_layout.addWidget(self.back_btn)
        
        nav_layout.addStretch()
        
        self.next_btn = QPushButton("Next")
        self.next_btn.setObjectName("primary_btn")
        self.next_btn.clicked.connect(self.go_next)
        nav_layout.addWidget(self.next_btn)
        
        main_layout.addLayout(nav_layout)
        
    def create_db_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        desc = QLabel("Step 1: Configure Database Connection\nChoose SQLite for single-computer deployments, or network engines for LAN setups.")
        desc.setStyleSheet("color: #94a3b8; margin-bottom: 10px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)
        
        self.db_type_combo = QComboBox()
        self.db_type_combo.addItems(["SQLite (Local Installation)", "PostgreSQL (Network Server)", "MySQL (Network Server)"])
        self.db_type_combo.currentIndexChanged.connect(self.toggle_db_inputs)
        form_layout.addRow("Database System:", self.db_type_combo)
        
        # Network database inputs (hidden by default)
        self.network_widget = QWidget()
        net_layout = QFormLayout(self.network_widget)
        net_layout.setContentsMargins(0, 0, 0, 0)
        net_layout.setSpacing(10)
        
        self.db_host_input = QLineEdit("localhost")
        self.db_port_input = QLineEdit("5432")
        self.db_name_input = QLineEdit("school_management")
        self.db_user_input = QLineEdit("postgres")
        self.db_pass_input = QLineEdit()
        self.db_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        net_layout.addRow("Host / Server IP:", self.db_host_input)
        net_layout.addRow("Port:", self.db_port_input)
        net_layout.addRow("Database Name:", self.db_name_input)
        net_layout.addRow("Username:", self.db_user_input)
        net_layout.addRow("Password:", self.db_pass_input)
        
        form_layout.addRow(self.network_widget)
        self.network_widget.setVisible(False)
        
        layout.addWidget(form_frame)
        layout.addStretch()
        return widget
        
    def create_school_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        desc = QLabel("Step 2: Enter School Profile details and upload your official School Logo.")
        desc.setStyleSheet("color: #94a3b8; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)
        
        self.school_name_input = QLineEdit("Orion School System")
        self.school_motto_input = QLineEdit("Knowledge, Integrity, Excellence")
        self.school_email_input = QLineEdit("info@orionschool.edu.gh")
        self.school_phone_input = QLineEdit("+233 24 123 4567")
        self.school_address_input = QLineEdit("P.O. Box 45, Accra, Ghana")
        
        form_layout.addRow("School Name *:", self.school_name_input)
        form_layout.addRow("School Motto:", self.school_motto_input)
        form_layout.addRow("Official Email:", self.school_email_input)
        form_layout.addRow("Contact Phone:", self.school_phone_input)
        form_layout.addRow("Address Info:", self.school_address_input)
        
        # Logo picker row
        logo_picker_layout = QHBoxLayout()
        self.logo_path_lbl = QLabel("No logo selected")
        self.logo_path_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
        
        logo_btn = QPushButton("Browse Logo...")
        logo_btn.setObjectName("secondary_btn")
        logo_btn.clicked.connect(self.browse_logo)
        
        logo_picker_layout.addWidget(logo_btn)
        logo_picker_layout.addWidget(self.logo_path_lbl, stretch=1)
        form_layout.addRow("School Logo:", logo_picker_layout)
        
        # Thumbnail logo preview
        self.logo_preview = QLabel("Logo Preview")
        self.logo_preview.setFixedSize(80, 80)
        self.logo_preview.setStyleSheet("border: 1px dashed #475569; border-radius: 6px; color: #64748b; background-color: #0f172a;")
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_layout.addRow("Logo Preview:", self.logo_preview)
        
        layout.addWidget(form_frame)
        layout.addStretch()
        return widget
        
    def create_admin_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        desc = QLabel("Step 3: Create Super Administrator credentials.\nThese credentials will be used to log in for the first time.")
        desc.setStyleSheet("color: #94a3b8; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)
        
        self.admin_user_input = QLineEdit("admin")
        self.admin_email_input = QLineEdit("admin@orionschool.edu.gh")
        self.admin_pass_input = QLineEdit()
        self.admin_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.admin_confirm_input = QLineEdit()
        self.admin_confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        form_layout.addRow("Admin Username *:", self.admin_user_input)
        form_layout.addRow("Admin Email *:", self.admin_email_input)
        form_layout.addRow("Password *:", self.admin_pass_input)
        form_layout.addRow("Confirm Password *:", self.admin_confirm_input)
        
        layout.addWidget(form_frame)
        layout.addStretch()
        return widget
        
    def toggle_db_inputs(self):
        index = self.db_type_combo.currentIndex()
        if index == 0:  # SQLite
            self.network_widget.setVisible(False)
        else:  # Postgres or MySQL
            self.network_widget.setVisible(True)
            if index == 1:  # Postgres
                self.db_port_input.setText("5432")
                self.db_user_input.setText("postgres")
            else:  # MySQL
                self.db_port_input.setText("3306")
                self.db_user_input.setText("root")
                
    def browse_logo(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select School Logo", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if filepath:
            self.selected_logo_path = filepath
            self.logo_path_lbl.setText(os.path.basename(filepath))
            
            # Load thumbnail preview
            pixmap = QPixmap(filepath)
            scaled = pixmap.scaled(
                self.logo_preview.size(), 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.logo_preview.setPixmap(scaled)
            
    def go_back(self):
        curr_idx = self.stacked_widget.currentIndex()
        if curr_idx > 0:
            self.stacked_widget.setCurrentIndex(curr_idx - 1)
            self.update_nav_buttons()
            
    def go_next(self):
        curr_idx = self.stacked_widget.currentIndex()
        if curr_idx == 0:
            # Validate database config if needed
            self.stacked_widget.setCurrentIndex(1)
            self.update_nav_buttons()
        elif curr_idx == 1:
            # Validate school page
            if not self.school_name_input.text().strip():
                QMessageBox.warning(self, "Validation Error", "School Name is a required field.")
                return
            self.stacked_widget.setCurrentIndex(2)
            self.update_nav_buttons()
        elif curr_idx == 2:
            # Validate admin account credentials & complete
            if self.validate_admin_form():
                self.complete_installation()
                
    def update_nav_buttons(self):
        curr_idx = self.stacked_widget.currentIndex()
        self.back_btn.setEnabled(curr_idx > 0)
        if curr_idx == 2:
            self.next_btn.setText("Complete Setup")
            self.next_btn.setObjectName("danger_btn")
        else:
            self.next_btn.setText("Next")
            self.next_btn.setObjectName("primary_btn")
        # Force stylesheet update for buttons
        self.next_btn.style().unpolish(self.next_btn)
        self.next_btn.style().polish(self.next_btn)
        
    def validate_admin_form(self) -> bool:
        username = self.admin_user_input.text().strip()
        email = self.admin_email_input.text().strip()
        pwd = self.admin_pass_input.text()
        confirm = self.admin_confirm_input.text()
        
        if not username or not email or not pwd:
            QMessageBox.warning(self, "Validation Error", "All fields marked with an asterisk (*) are required.")
            return False
            
        if "@" not in email:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
            return False
            
        if len(pwd) < 6:
            QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
            return False
            
        if pwd != confirm:
            QMessageBox.warning(self, "Validation Error", "Passwords do not match. Please re-enter passwords.")
            return False
            
        return True
        
    def complete_installation(self):
        self.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        
        try:
            # 1. Process Logo Image copy
            logo_path = ""
            if self.selected_logo_path:
                from config import DATA_DIR
                ext = Path(self.selected_logo_path).suffix
                dest_file = DATA_DIR / f"school_logo{ext}"
                try:
                    shutil.copy2(self.selected_logo_path, dest_file)
                    logo_path = str(dest_file)
                except Exception as e:
                    print(f"Error copying school logo: {e}")
            
            # 2. Save configurations to config.json
            db_idx = self.db_type_combo.currentIndex()
            db_type = "sqlite"
            if db_idx == 1:
                db_type = "postgresql"
            elif db_idx == 2:
                db_type = "mysql"
                
            config["db_type"] = db_type
            if db_type != "sqlite":
                config["db_host"] = self.db_host_input.text().strip()
                try:
                    config["db_port"] = int(self.db_port_input.text().strip())
                except ValueError:
                    config["db_port"] = 5432 if db_type == "postgresql" else 3306
                config["db_name"] = self.db_name_input.text().strip()
                config["db_user"] = self.db_user_input.text().strip()
                config["db_password"] = self.db_pass_input.text()
                
            config["school_name"] = self.school_name_input.text().strip()
            config["school_motto"] = self.school_motto_input.text().strip()
            config["school_email"] = self.school_email_input.text().strip()
            config["school_phone"] = self.school_phone_input.text().strip()
            config["school_address"] = self.school_address_input.text().strip()
            config["school_logo"] = logo_path
            config["setup_completed"] = True
            
            save_config(config)
            
            # 3. Create tables & Seed Default Data
            init_db()
            seed_database()
            
            # 4. Modify Seeded Admin Credentials to custom input
            session = get_session()
            admin_user = session.query(User).filter(User.username == "admin").first()
            if admin_user:
                # Update username, email, and password
                admin_user.username = self.admin_user_input.text().strip()
                admin_user.password_hash = hash_password(self.admin_pass_input.text())
                admin_user.email = self.admin_email_input.text().strip()
                
                # Update Staff profile linked to admin user
                staff = session.query(Staff).filter(Staff.user_id == admin_user.id).first()
                if staff:
                    staff.email = admin_user.email
                    staff.first_name = "System"
                    staff.last_name = "Administrator"
                
                session.commit()
            session.close()
            
            QMessageBox.information(
                self, "Setup Completed", 
                "System installation is complete!\nAll configurations are saved and standard databases are seeded."
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(
                self, "Setup Failed", 
                f"Failed to complete system setup:\n{str(e)}"
            )
        finally:
            QApplication.restoreOverrideCursor()
            self.setEnabled(True)
