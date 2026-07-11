from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QFormLayout, QMessageBox,
    QFileDialog, QTabWidget, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal
from config import config, save_config
from utils.backup import create_backup, restore_backup
from pathlib import Path

from database.connection import get_session
from database.models import User, Staff
from ui.auth import verify_password
from database.seed import hash_password

class SettingsPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QTabWidget()
        
        # Check permissions
        has_admin_rights = False
        if self.user.role:
            if self.user.role.name == "Super Admin":
                has_admin_rights = True
            elif self.user.role.permissions:
                has_admin_rights = any(p.name == "manage_settings" for p in self.user.role.permissions)
        
        if has_admin_rights:
            # 1. School Branding Profile Tab
            self.profile_tab = QWidget()
            self.init_profile_tab()
            self.tabs.addTab(self.profile_tab, "School Profile")
            
            # 2. Database Backup & Restore Tab
            self.backup_tab = QWidget()
            self.init_backup_tab()
            self.tabs.addTab(self.backup_tab, "Backup & Recovery")
            
            # 3. Grading Scale Tab
            self.grading_tab = QWidget()
            self.init_grading_tab()
            self.tabs.addTab(self.grading_tab, "Grading Scale")
        
        # 3. User Account Tab
        self.account_tab = QWidget()
        self.init_account_tab()
        self.tabs.addTab(self.account_tab, "My Account")
        
        layout.addWidget(self.tabs)
        
    def init_profile_tab(self):
        tab_layout = QVBoxLayout(self.profile_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        form_frame = QFrame()
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(10)
        
        self.name_input = QLineEdit()
        self.motto_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.address_input = QLineEdit()
        
        form_layout.addRow("School Name:", self.name_input)
        form_layout.addRow("School Motto / Slogan:", self.motto_input)
        form_layout.addRow("School Email Address:", self.email_input)
        form_layout.addRow("School Contact Phone:", self.phone_input)
        form_layout.addRow("School Physical Address:", self.address_input)
        
        tab_layout.addWidget(form_frame)
        
        save_btn = QPushButton("Save School Details")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self.save_branding)
        tab_layout.addWidget(save_btn)
        tab_layout.addStretch()
        
        self.load_branding_data()
        
    def load_branding_data(self):
        self.name_input.setText(config.get("school_name", ""))
        self.motto_input.setText(config.get("school_motto", ""))
        self.email_input.setText(config.get("school_email", ""))
        self.phone_input.setText(config.get("school_phone", ""))
        self.address_input.setText(config.get("school_address", ""))
        
    def save_branding(self):
        config["school_name"] = self.name_input.text().strip()
        config["school_motto"] = self.motto_input.text().strip()
        config["school_email"] = self.email_input.text().strip()
        config["school_phone"] = self.phone_input.text().strip()
        config["school_address"] = self.address_input.text().strip()
        
        if save_config(config):
            QMessageBox.information(self, "Success", "School profile details updated successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save configuration updates.")

    # --- Database Backups ---
    def init_backup_tab(self):
        tab_layout = QVBoxLayout(self.backup_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(20)
        
        # Backup section
        backup_frame = QFrame()
        backup_frame.setObjectName("card")
        b_layout = QVBoxLayout(backup_frame)
        b_layout.setSpacing(10)
        
        b_title = QLabel("Create Database Backup Archive")
        b_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #3b82f6;")
        b_layout.addWidget(b_title)
        
        b_desc = QLabel("Export a compressed ZIP backup copy of the local SQLite database archive. Useful for preventing data loss.")
        b_desc.setWordWrap(True)
        b_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        b_layout.addWidget(b_desc)
        
        self.backup_path_input = QLineEdit()
        self.backup_path_input.setPlaceholderText("Select folder path to save backup archive...")
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.backup_path_input)
        
        browse_btn = QPushButton("Select Folder")
        browse_btn.setObjectName("secondary_btn")
        browse_btn.clicked.connect(self.browse_backup_folder)
        path_layout.addWidget(browse_btn)
        b_layout.addLayout(path_layout)
        
        run_backup_btn = QPushButton("Generate Backup Now")
        run_backup_btn.setObjectName("primary_btn")
        run_backup_btn.clicked.connect(self.run_backup)
        b_layout.addWidget(run_backup_btn)
        
        tab_layout.addWidget(backup_frame)
        
        # Restore section
        restore_frame = QFrame()
        restore_frame.setObjectName("card")
        r_layout = QVBoxLayout(restore_frame)
        r_layout.setSpacing(10)
        
        r_title = QLabel("Restore Database from Archive")
        r_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #ef4444;")
        r_layout.addWidget(r_title)
        
        r_desc = QLabel("Restore database tables state from an existing backup ZIP file. WARNING: This will overwrite the current database details and cannot be undone!")
        r_desc.setWordWrap(True)
        r_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        r_layout.addWidget(r_desc)
        
        self.restore_path_input = QLineEdit()
        self.restore_path_input.setPlaceholderText("Select database backup ZIP file...")
        
        restore_path_layout = QHBoxLayout()
        restore_path_layout.addWidget(self.restore_path_input)
        
        browse_zip_btn = QPushButton("Select ZIP File")
        browse_zip_btn.setObjectName("secondary_btn")
        browse_zip_btn.clicked.connect(self.browse_restore_file)
        restore_path_layout.addWidget(browse_zip_btn)
        r_layout.addLayout(restore_path_layout)
        
        run_restore_btn = QPushButton("Execute Restore")
        run_restore_btn.setObjectName("danger_btn")
        run_restore_btn.clicked.connect(self.run_restore)
        r_layout.addWidget(run_restore_btn)
        
        tab_layout.addWidget(restore_frame)
        
        # Auto Backup Settings
        auto_backup_frame = QFrame()
        auto_backup_frame.setObjectName("card")
        ab_layout = QVBoxLayout(auto_backup_frame)
        ab_layout.setSpacing(10)
        
        ab_title = QLabel("Auto Backup Settings")
        ab_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #3b82f6;")
        ab_layout.addWidget(ab_title)
        
        ab_desc = QLabel("Configure automatic backups to prevent data loss. Auto backups are stored as compressed zip archives.")
        ab_desc.setWordWrap(True)
        ab_desc.setStyleSheet("color: #94a3b8; font-size: 12px;")
        ab_layout.addWidget(ab_desc)
        
        self.auto_backup_dir_input = QLineEdit()
        self.auto_backup_dir_input.setPlaceholderText("Select folder path to save auto backups...")
        
        ab_path_layout = QHBoxLayout()
        ab_path_layout.addWidget(self.auto_backup_dir_input)
        
        ab_browse_btn = QPushButton("Select Folder")
        ab_browse_btn.setObjectName("secondary_btn")
        ab_browse_btn.clicked.connect(self.browse_auto_backup_folder)
        ab_path_layout.addWidget(ab_browse_btn)
        ab_layout.addLayout(ab_path_layout)
        
        self.chk_backup_open = QCheckBox("Backup on system startup (open)")
        self.chk_backup_close = QCheckBox("Backup on system exit (close)")
        self.chk_backup_monthly = QCheckBox("Schedule monthly periodic auto backup")
        
        ab_layout.addWidget(self.chk_backup_open)
        ab_layout.addWidget(self.chk_backup_close)
        ab_layout.addWidget(self.chk_backup_monthly)
        
        save_auto_btn = QPushButton("Save Auto Backup Settings")
        save_auto_btn.setObjectName("primary_btn")
        save_auto_btn.clicked.connect(self.save_auto_backup_settings)
        ab_layout.addWidget(save_auto_btn)
        
        tab_layout.addWidget(auto_backup_frame)
        tab_layout.addStretch()
        
        # Load active auto backup settings
        self.load_auto_backup_settings()
        
    def browse_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Backup Folder")
        if folder:
            self.backup_path_input.setText(folder)
            
    def browse_restore_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Backup ZIP File", "", "ZIP Files (*.zip)")
        if file_path:
            self.restore_path_input.setText(file_path)
            
    def run_backup(self):
        dest_folder = self.backup_path_input.text().strip()
        if not dest_folder:
            QMessageBox.warning(self, "Path Required", "Please select a target folder to save the backup.")
            return
            
        success, msg = create_backup(dest_folder)
        if success:
            QMessageBox.information(self, "Backup Complete", msg)
        else:
            QMessageBox.critical(self, "Backup Failed", msg)
            
    def run_restore(self):
        zip_path = self.restore_path_input.text().strip()
        if not zip_path:
            QMessageBox.warning(self, "File Required", "Please select a database backup ZIP file to restore from.")
            return
            
        confirm = QMessageBox.question(
            self, "Confirm Dangerous Operation",
            "This will completely overwrite current database states with backup data.\nAre you absolutely sure you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            success, msg = restore_backup(zip_path)
            if success:
                QMessageBox.information(self, "Restore Complete", "Database restored successfully. Please restart the application to reload changes.")
            else:
                QMessageBox.critical(self, "Restore Failed", msg)
                 
    def browse_auto_backup_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Auto Backup Folder")
        if folder:
            self.auto_backup_dir_input.setText(folder)

    def load_auto_backup_settings(self):
        self.auto_backup_dir_input.setText(config.get("backup_directory", ""))
        self.chk_backup_open.setChecked(config.get("auto_backup_on_open", False))
        self.chk_backup_close.setChecked(config.get("auto_backup_on_close", False))
        self.chk_backup_monthly.setChecked(config.get("auto_backup_monthly", False))

    def save_auto_backup_settings(self):
        dir_path = self.auto_backup_dir_input.text().strip()
        if not dir_path:
            QMessageBox.warning(self, "Path Required", "Please select a target folder to save the auto backups.")
            return
            
        config["backup_directory"] = dir_path
        config["auto_backup_on_open"] = self.chk_backup_open.isChecked()
        config["auto_backup_on_close"] = self.chk_backup_close.isChecked()
        config["auto_backup_monthly"] = self.chk_backup_monthly.isChecked()
        
        if save_config(config):
            QMessageBox.information(self, "Success", "Auto backup settings updated successfully.")
        else:
            QMessageBox.critical(self, "Error", "Failed to save auto backup configuration.")
            
    def init_account_tab(self):
        tab_layout = QVBoxLayout(self.account_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        forms_layout = QHBoxLayout()
        forms_layout.setSpacing(20)
        
        # Form 1: Personal Profile
        profile_frame = QFrame()
        profile_frame.setObjectName("card")
        p_layout = QVBoxLayout(profile_frame)
        p_layout.setSpacing(10)
        
        p_title = QLabel("Edit Personal Profile Info")
        p_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #3b82f6;")
        p_layout.addWidget(p_title)
        
        p_form = QFormLayout()
        p_form.setSpacing(8)
        
        self.usr_username_input = QLineEdit()
        self.usr_username_input.setEnabled(False)  # Read-only username
        self.usr_fname_input = QLineEdit()
        self.usr_lname_input = QLineEdit()
        self.usr_email_input = QLineEdit()
        self.usr_phone_input = QLineEdit()
        
        p_form.addRow("Username:", self.usr_username_input)
        p_form.addRow("First Name:", self.usr_fname_input)
        p_form.addRow("Last Name:", self.usr_lname_input)
        p_form.addRow("Email Address:", self.usr_email_input)
        p_form.addRow("Contact Phone:", self.usr_phone_input)
        p_layout.addLayout(p_form)
        
        save_profile_btn = QPushButton("Save Profile Details")
        save_profile_btn.setObjectName("primary_btn")
        save_profile_btn.clicked.connect(self.save_profile_data)
        p_layout.addWidget(save_profile_btn)
        p_layout.addStretch()
        
        forms_layout.addWidget(profile_frame)
        
        # Form 2: Change Password
        pass_frame = QFrame()
        pass_frame.setObjectName("card")
        pass_layout = QVBoxLayout(pass_frame)
        pass_layout.setSpacing(10)
        
        pass_title = QLabel("Change Account Password")
        pass_title.setStyleSheet("font-weight: bold; font-size: 14px; color: #3b82f6;")
        pass_layout.addWidget(pass_title)
        
        pass_form = QFormLayout()
        pass_form.setSpacing(8)
        
        self.old_pass_input = QLineEdit()
        self.old_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_pass_input = QLineEdit()
        self.new_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pass_input = QLineEdit()
        self.confirm_pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        pass_form.addRow("Current Password:", self.old_pass_input)
        pass_form.addRow("New Password:", self.new_pass_input)
        pass_form.addRow("Confirm Password:", self.confirm_pass_input)
        pass_layout.addLayout(pass_form)
        
        change_pass_btn = QPushButton("Change Password")
        change_pass_btn.setObjectName("danger_btn")
        change_pass_btn.clicked.connect(self.change_user_password)
        pass_layout.addWidget(change_pass_btn)
        pass_layout.addStretch()
        
        forms_layout.addWidget(pass_frame)
        
        tab_layout.addLayout(forms_layout)
        
        self.load_account_data()

    def load_account_data(self):
        self.usr_username_input.setText(self.user.username)
        self.usr_email_input.setText(self.user.email or "")
        
        if self.user.staff_profile:
            self.usr_fname_input.setText(self.user.staff_profile.first_name or "")
            self.usr_lname_input.setText(self.user.staff_profile.last_name or "")
            self.usr_phone_input.setText(self.user.staff_profile.phone or "")
        else:
            self.usr_fname_input.setEnabled(False)
            self.usr_lname_input.setEnabled(False)
            self.usr_phone_input.setEnabled(False)

    def save_profile_data(self):
        session = get_session()
        try:
            # Re-fetch objects within thread session to prevent DetachedInstanceError
            db_user = session.query(User).filter(User.id == self.user.id).first()
            if not db_user:
                QMessageBox.critical(self, "Error", "User session account not found in database.")
                return
                
            email_val = self.usr_email_input.text().strip()
            if not email_val or "@" not in email_val:
                QMessageBox.warning(self, "Validation Error", "Please enter a valid email address.")
                return
                
            db_user.email = email_val
            # Update user session object email in memory
            self.user.email = email_val
            
            if db_user.staff_profile:
                fname = self.usr_fname_input.text().strip()
                lname = self.usr_lname_input.text().strip()
                phone = self.usr_phone_input.text().strip()
                
                if not fname or not lname:
                    QMessageBox.warning(self, "Validation Error", "First Name and Last Name cannot be empty.")
                    return
                    
                db_user.staff_profile.first_name = fname
                db_user.staff_profile.last_name = lname
                db_user.staff_profile.phone = phone
                db_user.staff_profile.email = email_val
                
                # Update user session object staff_profile details in memory
                self.user.staff_profile.first_name = fname
                self.user.staff_profile.last_name = lname
                self.user.staff_profile.phone = phone
                self.user.staff_profile.email = email_val
                
            session.commit()
            QMessageBox.information(self, "Success", "Profile details updated successfully.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save profile updates: {e}")
        finally:
            session.close()

    def change_user_password(self):
        old_pwd = self.old_pass_input.text()
        new_pwd = self.new_pass_input.text()
        confirm_pwd = self.confirm_pass_input.text()
        
        if not old_pwd or not new_pwd or not confirm_pwd:
            QMessageBox.warning(self, "Validation Error", "All password fields are required.")
            return
            
        if len(new_pwd) < 6:
            QMessageBox.warning(self, "Validation Error", "New password must be at least 6 characters.")
            return
            
        if new_pwd != confirm_pwd:
            QMessageBox.warning(self, "Validation Error", "New passwords do not match confirmation.")
            return
            
        session = get_session()
        try:
            db_user = session.query(User).filter(User.id == self.user.id).first()
            if not db_user:
                QMessageBox.critical(self, "Error", "User session account not found in database.")
                return
                
            if not verify_password(db_user.password_hash, old_pwd):
                QMessageBox.critical(self, "Error", "Current password entered is incorrect.")
                return
                
            db_user.password_hash = hash_password(new_pwd)
            session.commit()
            
            # Clear input fields
            self.old_pass_input.clear()
            self.new_pass_input.clear()
            self.confirm_pass_input.clear()
            
            QMessageBox.information(self, "Success", "Account password updated successfully.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update password: {e}")
        finally:
            session.close()

    def refresh(self):
        if hasattr(self, 'name_input'):
            self.load_branding_data()
        if hasattr(self, 'auto_backup_dir_input'):
            self.load_auto_backup_settings()
        if hasattr(self, 'grading_table'):
            self.load_grading_scale_table()
        self.load_account_data()

    def init_grading_tab(self):
        tab_layout = QVBoxLayout(self.grading_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        info_lbl = QLabel(
            "Define the school's grading system. The system maps the calculated total score (Class + Exam) "
            "to a grade based on the Minimum Score Threshold. Set rules in descending order for correct calculation."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #64748b; font-size: 12px;")
        tab_layout.addWidget(info_lbl)
        
        # Grading Table
        from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        self.grading_table = QTableWidget()
        self.grading_table.setColumnCount(3)
        self.grading_table.setHorizontalHeaderLabels(["Grade (e.g. 1 or A)", "Min Score Threshold (0 - 100)", "Official Remark (e.g. Excellent)"])
        self.grading_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.grading_table)
        
        # Load existing data
        self.load_grading_scale_table()
        
        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add New Rule")
        add_btn.setObjectName("secondary_btn")
        add_btn.clicked.connect(self.add_grading_rule)
        btn_layout.addWidget(add_btn)
        
        delete_btn = QPushButton("Delete Selected Rule")
        delete_btn.setObjectName("secondary_btn")
        delete_btn.clicked.connect(self.delete_grading_rule)
        btn_layout.addWidget(delete_btn)
        
        save_btn = QPushButton("Save Grading Scale")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self.save_grading_scale)
        btn_layout.addWidget(save_btn)
        
        btn_layout.addStretch()
        tab_layout.addLayout(btn_layout)
        
    def load_grading_scale_table(self):
        scale = config.get("grading_scale", [])
        # Sort by min_score descending
        sorted_scale = sorted(scale, key=lambda x: x.get("min_score", 0.0), reverse=True)
        
        self.grading_table.setRowCount(len(sorted_scale))
        for r, item in enumerate(sorted_scale):
            self.grading_table.setItem(r, 0, QTableWidgetItem(str(item.get("grade", ""))))
            self.grading_table.setItem(r, 1, QTableWidgetItem(f"{item.get('min_score', 0.0):.1f}"))
            self.grading_table.setItem(r, 2, QTableWidgetItem(str(item.get("remark", ""))))
            
    def add_grading_rule(self):
        row = self.grading_table.rowCount()
        self.grading_table.insertRow(row)
        from PySide6.QtWidgets import QTableWidgetItem
        self.grading_table.setItem(row, 0, QTableWidgetItem(""))
        self.grading_table.setItem(row, 1, QTableWidgetItem("0.0"))
        self.grading_table.setItem(row, 2, QTableWidgetItem(""))
        
    def delete_grading_rule(self):
        selected = self.grading_table.selectedRanges()
        if not selected:
            QMessageBox.warning(self, "Selection Required", "Please select the row you want to delete.")
            return
        row = selected[0].topRow()
        self.grading_table.removeRow(row)
        
    def save_grading_scale(self):
        scale = []
        for r in range(self.grading_table.rowCount()):
            grade_item = self.grading_table.item(r, 0)
            score_item = self.grading_table.item(r, 1)
            remark_item = self.grading_table.item(r, 2)
            
            grade_str = grade_item.text().strip() if grade_item else ""
            score_str = score_item.text().strip() if score_item else "0.0"
            remark_str = remark_item.text().strip() if remark_item else ""
            
            if not grade_str:
                QMessageBox.warning(self, "Validation Error", f"Row {r+1}: Grade field cannot be empty.")
                return
                
            try:
                min_score = float(score_str)
                if min_score < 0 or min_score > 100:
                    raise ValueError()
            except ValueError:
                QMessageBox.warning(self, "Validation Error", f"Row {r+1}: Minimum score must be a number between 0 and 100.")
                return
                
            scale.append({
                "grade": grade_str,
                "min_score": min_score,
                "remark": remark_str
            })
            
        # Update config and save
        config["grading_scale"] = scale
        if save_config(config):
            QMessageBox.information(self, "Success", "School grading system configuration saved successfully!")
            self.load_grading_scale_table()
        else:
            QMessageBox.critical(self, "Error", "Failed to write grading scale configurations to file.")
