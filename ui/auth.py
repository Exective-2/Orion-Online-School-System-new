import hashlib
import os
from PySide6.QtWidgets import (
    QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QHBoxLayout, QFrame, QMessageBox, QApplication, QDialog, QComboBox
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
    """
    Login window that supports three user types:
    1. System Administrator (credentials in master DB → opens System Admin Portal)
    2. Branch Admin / Headteacher  (credentials in branch DB)
    3. Regular branch staff       (credentials in branch DB)

    Two signals are emitted on success so the application can route correctly.
    """
    login_success = Signal(object)        # Emits User model on successful branch login
    sysadmin_login = Signal(object)       # Emits SystemAdmin model on sysadmin login

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orion SMS - Sign In")
        self.setFixedSize(420, 560)
        self.setStyleSheet(get_theme_stylesheet(config.get("theme", "dark")))
        self._branches = []       # populated in init_ui from master DB
        self.init_ui()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(40, 40, 40, 40)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(18)
        card_layout.setContentsMargins(30, 40, 30, 40)

        # Logo / title
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = config.get("school_logo", "")
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled)
        else:
            self.logo_label.setText("ORION")
            self.logo_label.setStyleSheet(
                "font-size: 32px; font-weight: bold; color: #3b82f6; letter-spacing: 2px;"
            )

        self.subtitle_label = QLabel(config.get("school_name", "School Management System"))
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #94a3b8; margin-bottom: 10px;")

        # Branch selector (shown only when multiple branches are registered)
        self.branch_selector = QComboBox()
        self.branch_selector.setObjectName("branch_selector")
        self.branch_selector.setMinimumHeight(36)
        self._load_branches()
        if len(self._branches) <= 1:
            self.branch_selector.hide()

        # Credentials
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Username")
        self.username_input.setObjectName("username")

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setObjectName("password")

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self.handle_login)
        self.login_btn.setMinimumHeight(42)

        self.help_label = QLabel("Contact admin if you forgot your credentials.")
        self.help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_label.setStyleSheet("font-size: 11px; color: #64748b; margin-top: 8px;")

        self.setup_wizard_btn = QPushButton("System Setup Wizard (First-time installation)")
        self.setup_wizard_btn.setObjectName("link_btn")
        self.setup_wizard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_wizard_btn.clicked.connect(self.run_setup_wizard)
        self.setup_wizard_btn.setStyleSheet(
            "color: #3b82f6; background: transparent; border: none; "
            "font-size: 11px; text-decoration: underline; margin-top: 4px;"
        )

        card_layout.addWidget(self.logo_label)
        card_layout.addWidget(self.subtitle_label)
        card_layout.addWidget(self.branch_selector)
        card_layout.addWidget(self.username_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.login_btn)
        card_layout.addWidget(self.help_label)
        card_layout.addWidget(self.setup_wizard_btn)

        main_layout.addWidget(card)

    # ------------------------------------------------------------------
    # Branch loader
    # ------------------------------------------------------------------

    def _load_branches(self):
        """Populate the branch selector from the master database."""
        try:
            from database.master_connection import get_master_session
            from database.master_models import Branch
            session = get_master_session()
            branches = session.query(Branch).filter(Branch.is_active == True).order_by(Branch.name).all()
            self._branches = [(b.id, b.name, b.db_filename) for b in branches]
            session.close()
        except Exception:
            self._branches = []

        self.branch_selector.clear()
        if len(self._branches) > 1:
            self.branch_selector.addItem("— Select your branch —", None)
        for bid, bname, _ in self._branches:
            self.branch_selector.addItem(bname, bid)

    # ------------------------------------------------------------------
    # Login handler
    # ------------------------------------------------------------------

    def handle_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Validation Error", "Please fill in all fields.")
            return

        # ── Step 1: Check master DB for System Administrator ──────────
        if self._try_sysadmin_login(username, password):
            return

        # ── Step 2: Check branch DB(s) ────────────────────────────────
        # If branch selector is visible and a specific branch is selected,
        # only search that branch — otherwise iterate all active branches.
        selected_branch_id = self.branch_selector.currentData() if self.branch_selector.isVisible() else None

        if selected_branch_id is not None:
            # Search only the selected branch
            target = next((b for b in self._branches if b[0] == selected_branch_id), None)
            if target:
                if self._try_branch_login(username, password, *target):
                    return
        else:
            # Search all active branches in order
            for branch_tuple in self._branches:
                if self._try_branch_login(username, password, *branch_tuple):
                    return

        QMessageBox.critical(self, "Login Failed",
                             "Invalid username or password, or your account is inactive.")

    # ------------------------------------------------------------------
    # Internal login helpers
    # ------------------------------------------------------------------

    def _try_sysadmin_login(self, username: str, password: str) -> bool:
        """Return True and emit sysadmin_login if credentials match the master system_admins table."""
        try:
            from database.master_connection import get_master_session
            from database.master_models import SystemAdmin
            session = get_master_session()
            admin = session.query(SystemAdmin).filter(
                SystemAdmin.username == username,
                SystemAdmin.is_active == True
            ).first()
            if admin and verify_password(admin.password_hash, password):
                from sqlalchemy.orm import make_transient
                session.expunge(admin)
                make_transient(admin)
                session.close()
                QMessageBox.information(
                    self, "Welcome",
                    f"Access Granted.\nWelcome, {admin.full_name} (System Administrator)!"
                )
                self.sysadmin_login.emit(admin)
                return True
            session.close()
        except Exception as e:
            print(f"[auth] sysadmin check error: {e}")
        return False

    def _try_branch_login(self, username: str, password: str,
                          branch_id: int, branch_name: str, db_filename: str) -> bool:
        """
        Return True and emit login_success if credentials match a user record
        inside the specified branch database.
        """
        try:
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker, make_transient
            from sqlalchemy.pool import NullPool
            from config import DATA_DIR
            from database.models import User, Role

            db_path = DATA_DIR / db_filename
            if not db_path.exists():
                return False

            tmp_engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False},
                poolclass=NullPool,
                echo=False,
            )
            TmpSession = sessionmaker(autocommit=False, autoflush=False, bind=tmp_engine)
            session = TmpSession()

            user = (
                session.query(User)
                .options(
                    joinedload(User.role).joinedload(Role.permissions),
                    joinedload(User.staff_profile),
                )
                .filter(User.username == username, User.is_active == True)
                .first()
            )

            if user and verify_password(user.password_hash, password):
                # Detach fully so we can close the temp session
                session.expunge_all()
                make_transient(user)
                if user.role:
                    make_transient(user.role)
                    for perm in user.role.permissions:
                        make_transient(perm)
                if user.staff_profile:
                    make_transient(user.staff_profile)

                session.close()
                tmp_engine.dispose()

                # Activate this branch globally
                from database.branch_context import set_active_branch
                from database.connection import set_active_branch_db
                set_active_branch(branch_id, branch_name, db_filename)
                set_active_branch_db(db_path)

                staff_name = "Administrator"
                if user.staff_profile:
                    staff_name = f"{user.staff_profile.first_name} {user.staff_profile.last_name}"

                QMessageBox.information(
                    self, "Welcome",
                    f"Access Granted.\nWelcome, {staff_name} ({user.role.name if user.role else 'User'})!\n"
                    f"Branch: {branch_name}"
                )
                self.login_success.emit(user)
                return True

            session.close()
            tmp_engine.dispose()
        except Exception as e:
            print(f"[auth] branch login error ({branch_name}): {e}")
        return False

    # ------------------------------------------------------------------
    # Setup Wizard
    # ------------------------------------------------------------------

    def run_setup_wizard(self):
        from ui.setup_wizard import SetupWizardDialog
        wizard = SetupWizardDialog(self)
        if wizard.exec() == QDialog.DialogCode.Accepted:
            from config import load_config
            new_config = load_config()
            self.subtitle_label.setText(new_config.get("school_name", "School Management System"))
            logo_path = new_config.get("school_logo", "")
            if logo_path and os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                scaled = pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                self.logo_label.setPixmap(scaled)
            else:
                self.logo_label.setText("ORION")
            # Reload branches after wizard completes
            self._load_branches()
            if len(self._branches) > 1:
                self.branch_selector.show()
            else:
                self.branch_selector.hide()

    # ------------------------------------------------------------------
    # Key events
    # ------------------------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.handle_login()
        else:
            super().keyPressEvent(event)
