"""
system_admin_portal.py
-----------------------
System Administrator portal — shown exclusively when the ``sysadmin`` account
(or any other SystemAdmin) logs in.

Tabs:
  1. System Overview  — cross-branch statistics cards + per-branch summary table
  2. Branch Management — create, edit, deactivate / reactivate school branches
  3. Admin Accounts   — assign Admin/Headteacher users to branches; reset passwords
"""

from __future__ import annotations

import os
import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QLineEdit, QComboBox,
    QMessageBox, QSizePolicy, QScrollArea, QGridLayout, QCheckBox,
    QMenu, QApplication,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QAction, QCursor, QColor, QFont

from config import config, DATA_DIR
from ui.theme import get_theme_stylesheet


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Helper: coloured status badge
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _status_item(text: str, active: bool) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    item.setForeground(QColor("#22c55e") if active else QColor("#ef4444"))
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    return item


def _ro_item(text: str, align=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setTextAlignment(align)
    item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
    return item


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Branch Creation Dialog
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CreateBranchDialog(QDialog):
    def __init__(self, parent=None, branch=None):
        super().__init__(parent)
        self.branch = branch          # None → create mode; Branch object → edit mode
        self.setWindowTitle("Edit Branch" if branch else "Create New Branch")
        self.setMinimumWidth(440)
        self.setStyleSheet(get_theme_stylesheet(config.get("theme", "dark")))
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Edit Branch Details" if self.branch else "➕  New School Branch")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6; margin-bottom: 6px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.name_input = QLineEdit(self.branch.name if self.branch else "")
        self.name_input.setPlaceholderText("e.g. North Annexe Campus")
        self.name_input.setMinimumHeight(34)

        self.code_input = QLineEdit(self.branch.code if self.branch else "")
        self.code_input.setPlaceholderText("e.g. NORTH  (short, unique, no spaces)")
        self.code_input.setMaxLength(20)
        self.code_input.setMinimumHeight(34)
        if self.branch:             # code is immutable once set (used in filename)
            self.code_input.setReadOnly(True)
            self.code_input.setStyleSheet("opacity: 0.6;")

        self.address_input = QLineEdit(self.branch.address or "" if self.branch else "")
        self.address_input.setPlaceholderText("Street / town address")
        self.address_input.setMinimumHeight(34)

        self.phone_input = QLineEdit(self.branch.phone or "" if self.branch else "")
        self.phone_input.setPlaceholderText("+233 24 000 0000")
        self.phone_input.setMinimumHeight(34)

        self.email_input = QLineEdit(self.branch.email or "" if self.branch else "")
        self.email_input.setPlaceholderText("branch@school.edu.gh")
        self.email_input.setMinimumHeight(34)

        self.notes_input = QLineEdit(self.branch.notes or "" if self.branch else "")
        self.notes_input.setPlaceholderText("Optional internal notes")
        self.notes_input.setMinimumHeight(34)

        form.addRow("Branch Name *", self.name_input)
        form.addRow("Branch Code *", self.code_input)
        form.addRow("Address", self.address_input)
        form.addRow("Phone", self.phone_input)
        form.addRow("Email", self.email_input)
        form.addRow("Notes", self.notes_input)
        layout.addLayout(form)

        if not self.branch:
            info = QLabel(
                "ℹ️  A new database file will be created for this branch.\n"
                "Default academic year, classes, and subjects will be seeded automatically."
            )
            info.setWordWrap(True)
            info.setStyleSheet("color: #64748b; font-size: 11px; margin-top: 6px;")
            layout.addWidget(info)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary_btn")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Branch" if self.branch else "Create Branch")
        save_btn.clicked.connect(self.accept)
        save_btn.setMinimumHeight(38)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "code": self.code_input.text().strip().upper().replace(" ", "_"),
            "address": self.address_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "email": self.email_input.text().strip(),
            "notes": self.notes_input.text().strip(),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Add / Edit Branch Admin Dialog
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AddAdminDialog(QDialog):
    def __init__(self, parent=None, branches: list = None, admin_record=None):
        """
        branches: list of (branch_id, branch_name, db_filename)
        admin_record: existing BranchAdmin ORM object for editing; None → create
        """
        super().__init__(parent)
        self.branches = branches or []
        self.admin_record = admin_record
        self.setWindowTitle("Edit Admin Account" if admin_record else "Add Branch Admin Account")
        self.setMinimumWidth(460)
        self.setStyleSheet(get_theme_stylesheet(config.get("theme", "dark")))
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("👤  Add Admin / Headteacher Account")
        if self.admin_record:
            title.setText("✏️  Edit Admin Account")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6; margin-bottom: 6px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        # Branch selector
        self.branch_combo = QComboBox()
        self.branch_combo.setMinimumHeight(34)
        for bid, bname, _ in self.branches:
            self.branch_combo.addItem(bname, bid)
        if self.admin_record:
            idx = self.branch_combo.findData(self.admin_record.branch_id)
            if idx >= 0:
                self.branch_combo.setCurrentIndex(idx)
            self.branch_combo.setEnabled(False)   # can't move admin between branches

        # Role selector
        self.role_combo = QComboBox()
        self.role_combo.setMinimumHeight(34)
        for role in ["Admin/Headteacher", "Accountant", "Teacher", "Librarian", "Storekeeper"]:
            self.role_combo.addItem(role)

        self.fullname_input = QLineEdit(self.admin_record.full_name if self.admin_record else "")
        self.fullname_input.setPlaceholderText("Full Name")
        self.fullname_input.setMinimumHeight(34)

        self.username_input = QLineEdit(self.admin_record.username if self.admin_record else "")
        self.username_input.setPlaceholderText("Login username (no spaces)")
        self.username_input.setMinimumHeight(34)
        if self.admin_record:
            self.username_input.setReadOnly(True)

        self.email_input = QLineEdit(self.admin_record.email or "" if self.admin_record else "")
        self.email_input.setPlaceholderText("user@school.edu.gh")
        self.email_input.setMinimumHeight(34)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(
            "Leave blank to keep existing password" if self.admin_record else "Temporary password"
        )
        self.password_input.setMinimumHeight(34)

        self.confirm_input = QLineEdit()
        self.confirm_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_input.setPlaceholderText("Confirm password")
        self.confirm_input.setMinimumHeight(34)

        form.addRow("Branch *", self.branch_combo)
        form.addRow("Role *", self.role_combo)
        form.addRow("Full Name *", self.fullname_input)
        form.addRow("Username *", self.username_input)
        form.addRow("Email", self.email_input)
        form.addRow("Password *", self.password_input)
        form.addRow("Confirm Password", self.confirm_input)
        layout.addLayout(form)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondary_btn")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Account" if self.admin_record else "Create Account")
        save_btn.clicked.connect(self._validate_and_accept)
        save_btn.setMinimumHeight(38)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _validate_and_accept(self):
        data = self.get_data()
        if not data["full_name"] or not data["username"]:
            QMessageBox.warning(self, "Validation", "Full name and username are required.")
            return
        if not self.admin_record and not data["password"]:
            QMessageBox.warning(self, "Validation", "Password is required for new accounts.")
            return
        if data["password"] and data["password"] != data["confirm"]:
            QMessageBox.warning(self, "Validation", "Passwords do not match.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "branch_id": self.branch_combo.currentData(),
            "branch_name": self.branch_combo.currentText(),
            "role": self.role_combo.currentText(),
            "full_name": self.fullname_input.text().strip(),
            "username": self.username_input.text().strip().lower().replace(" ", "_"),
            "email": self.email_input.text().strip(),
            "password": self.password_input.text(),
            "confirm": self.confirm_input.text(),
        }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Stat card widget
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class StatCard(QFrame):
    def __init__(self, title: str, value: str, icon: str, accent: str, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            f"QFrame#card {{ border-left: 4px solid {accent}; border-radius: 8px; padding: 12px; }}"
        )
        lay = QVBoxLayout(self)
        lay.setSpacing(4)
        header = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"font-size: 24px; color: {accent};")
        header.addWidget(icon_lbl)
        header.addStretch()
        lay.addLayout(header)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"font-size: 28px; font-weight: bold; color: {accent};")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-size: 12px; color: #94a3b8;")
        lay.addWidget(val_lbl)
        lay.addWidget(title_lbl)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  System Admin Portal (Main Window)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class SystemAdminPortal(QMainWindow):
    logout_requested = Signal()

    def __init__(self, sysadmin):
        super().__init__()
        self.sysadmin = sysadmin
        self.setWindowTitle("Orion SMS — System Administrator Portal")
        self.resize(1100, 720)
        self.setStyleSheet(get_theme_stylesheet(config.get("theme", "dark")))
        self._build_ui()
        self.refresh_all()

    # ─────────────────────────────────────────────────────────────────────
    # UI Layout
    # ─────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setObjectName("header")
        header.setFixedHeight(60)
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)

        logo_lbl = QLabel("⚙  ORION  |  System Administrator")
        logo_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6; letter-spacing: 1px;")
        h_lay.addWidget(logo_lbl)
        h_lay.addStretch()

        # Theme menu
        theme_btn = QPushButton("Theme ▾")
        theme_btn.setObjectName("secondary_btn")
        theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        theme_menu = QMenu(self)
        for label, key in [("Dark Mode", "dark"), ("Light Mode", "light"),
                            ("Forest Emerald", "emerald"), ("Midnight Sapphire", "sapphire"),
                            ("Sunset Amber", "amber")]:
            act = QAction(label, self)
            act.triggered.connect(lambda _=False, k=key: self._change_theme(k))
            theme_menu.addAction(act)
        theme_btn.setMenu(theme_menu)
        h_lay.addWidget(theme_btn)

        # User menu
        user_btn = QPushButton(f"{self.sysadmin.full_name}  ▾")
        user_btn.setObjectName("secondary_btn")
        user_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        user_menu = QMenu(self)
        logout_act = QAction("Logout", self)
        logout_act.triggered.connect(self._handle_logout)
        user_menu.addAction(logout_act)
        user_btn.setMenu(user_menu)
        h_lay.addWidget(user_btn)
        root.addWidget(header)

        # ── Tab widget ──
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setStyleSheet("QTabBar::tab { min-width: 160px; padding: 10px 20px; font-size: 13px; }")

        self.overview_tab = QWidget()
        self.branches_tab = QWidget()
        self.admins_tab = QWidget()

        self.tabs.addTab(self.overview_tab, "📊  System Overview")
        self.tabs.addTab(self.branches_tab, "🏫  Branch Management")
        self.tabs.addTab(self.admins_tab, "👤  Admin Accounts")

        self._build_overview_tab()
        self._build_branches_tab()
        self._build_admins_tab()

        root.addWidget(self.tabs)

    # ─────────────────────────────────────────────────────────────────────
    # TAB 1 — System Overview
    # ─────────────────────────────────────────────────────────────────────

    def _build_overview_tab(self):
        lay = QVBoxLayout(self.overview_tab)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        sub = QLabel("Live statistics fetched from every active branch database.")
        sub.setStyleSheet("color: #64748b; font-size: 12px;")
        lay.addWidget(sub)

        # Summary cards row
        self.cards_row = QHBoxLayout()
        self.cards_row.setSpacing(14)
        lay.addLayout(self.cards_row)

        # Per-branch breakdown table
        tbl_label = QLabel("Per-Branch Breakdown")
        tbl_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #e2e8f0; margin-top: 8px;")
        lay.addWidget(tbl_label)

        self.overview_table = QTableWidget()
        self.overview_table.setColumnCount(7)
        self.overview_table.setHorizontalHeaderLabels([
            "Branch", "Code", "Students", "Staff", "Active Year", "Fees Collected (GHS)", "Status"
        ])
        self.overview_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.overview_table.setAlternatingRowColors(True)
        self.overview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.overview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.overview_table.verticalHeader().setVisible(False)
        lay.addWidget(self.overview_table)

        refresh_btn = QPushButton("🔄  Refresh Statistics")
        refresh_btn.setObjectName("secondary_btn")
        refresh_btn.clicked.connect(self.refresh_all)
        lay.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignRight)

    # ─────────────────────────────────────────────────────────────────────
    # TAB 2 — Branch Management
    # ─────────────────────────────────────────────────────────────────────

    def _build_branches_tab(self):
        lay = QVBoxLayout(self.branches_tab)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        create_btn = QPushButton("➕  Create New Branch")
        create_btn.clicked.connect(self._create_branch)
        create_btn.setMinimumHeight(36)
        toolbar.addWidget(create_btn)
        toolbar.addStretch()
        refresh_b = QPushButton("🔄  Refresh")
        refresh_b.setObjectName("secondary_btn")
        refresh_b.clicked.connect(self.load_branches_table)
        toolbar.addWidget(refresh_b)
        lay.addLayout(toolbar)

        # Table
        self.branches_table = QTableWidget()
        self.branches_table.setColumnCount(7)
        self.branches_table.setHorizontalHeaderLabels([
            "ID", "Branch Name", "Code", "Phone", "Address", "DB File", "Status"
        ])
        self.branches_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.branches_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.branches_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.branches_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.branches_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.branches_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.branches_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.branches_table.setAlternatingRowColors(True)
        self.branches_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.branches_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.branches_table.verticalHeader().setVisible(False)
        lay.addWidget(self.branches_table)

        # Action buttons
        action_row = QHBoxLayout()
        self.edit_branch_btn = QPushButton("✏️  Edit Selected")
        self.edit_branch_btn.setObjectName("secondary_btn")
        self.edit_branch_btn.clicked.connect(self._edit_branch)
        self.toggle_branch_btn = QPushButton("🔴  Deactivate Selected")
        self.toggle_branch_btn.setObjectName("danger_btn")
        self.toggle_branch_btn.clicked.connect(self._toggle_branch)
        action_row.addWidget(self.edit_branch_btn)
        action_row.addWidget(self.toggle_branch_btn)
        action_row.addStretch()
        lay.addLayout(action_row)

    # ─────────────────────────────────────────────────────────────────────
    # TAB 3 — Admin Accounts
    # ─────────────────────────────────────────────────────────────────────

    def _build_admins_tab(self):
        lay = QVBoxLayout(self.admins_tab)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        # Toolbar
        toolbar = QHBoxLayout()
        add_btn = QPushButton("➕  Add Admin Account")
        add_btn.clicked.connect(self._add_admin)
        add_btn.setMinimumHeight(36)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        refresh_a = QPushButton("🔄  Refresh")
        refresh_a.setObjectName("secondary_btn")
        refresh_a.clicked.connect(self.load_admins_table)
        toolbar.addWidget(refresh_a)
        lay.addLayout(toolbar)

        # Table
        self.admins_table = QTableWidget()
        self.admins_table.setColumnCount(6)
        self.admins_table.setHorizontalHeaderLabels([
            "ID", "Full Name", "Username", "Branch", "Email", "Status"
        ])
        self.admins_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.admins_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.admins_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.admins_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.admins_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.admins_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.admins_table.setAlternatingRowColors(True)
        self.admins_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.admins_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.admins_table.verticalHeader().setVisible(False)
        lay.addWidget(self.admins_table)

        action_row = QHBoxLayout()
        self.edit_admin_btn = QPushButton("✏️  Edit / Reset Password")
        self.edit_admin_btn.setObjectName("secondary_btn")
        self.edit_admin_btn.clicked.connect(self._edit_admin)
        self.toggle_admin_btn = QPushButton("🔴  Deactivate Selected")
        self.toggle_admin_btn.setObjectName("danger_btn")
        self.toggle_admin_btn.clicked.connect(self._toggle_admin)
        action_row.addWidget(self.edit_admin_btn)
        action_row.addWidget(self.toggle_admin_btn)
        action_row.addStretch()
        lay.addLayout(action_row)

    # ─────────────────────────────────────────────────────────────────────
    # Data Loading
    # ─────────────────────────────────────────────────────────────────────

    def refresh_all(self):
        self.load_overview()
        self.load_branches_table()
        self.load_admins_table()

    def _get_branches(self):
        from database.master_connection import get_master_session
        from database.master_models import Branch
        session = get_master_session()
        branches = session.query(Branch).order_by(Branch.name).all()
        result = [(b.id, b.name, b.code, b.phone or "", b.address or "",
                   b.db_filename, b.is_active) for b in branches]
        session.close()
        return result

    def _get_branch_stats(self, db_filename: str) -> dict:
        """Fetch stats from a single branch DB — safe, returns zeros on error."""
        stats = {"students": 0, "staff": 0, "year": "—", "fees": 0.0}
        db_path = DATA_DIR / db_filename
        if not db_path.exists():
            return stats
        try:
            from database.master_connection import get_branch_session
            from database.models import Student, Staff, AcademicYear, Payment
            session = get_branch_session(db_filename)
            stats["students"] = session.query(Student).filter(Student.status == "Active").count()
            stats["staff"] = session.query(Staff).filter(Staff.status == "Active").count()
            yr = session.query(AcademicYear).filter(AcademicYear.is_current == True).first()
            if yr:
                stats["year"] = yr.name
            total_paid = session.query(Payment).all()
            stats["fees"] = sum(p.amount for p in total_paid)
            session.close()
        except Exception as e:
            print(f"[portal] stats error for {db_filename}: {e}")
        return stats

    def load_overview(self):
        # Clear old stat cards
        while self.cards_row.count():
            item = self.cards_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        branches = self._get_branches()
        total_students = 0
        total_staff = 0
        total_fees = 0.0
        active_branches = sum(1 for b in branches if b[6])

        # Table
        self.overview_table.setRowCount(0)
        for bid, bname, code, phone, addr, dbf, is_active in branches:
            stats = self._get_branch_stats(dbf)
            total_students += stats["students"]
            total_staff += stats["staff"]
            total_fees += stats["fees"]
            row = self.overview_table.rowCount()
            self.overview_table.insertRow(row)
            self.overview_table.setItem(row, 0, _ro_item(bname))
            self.overview_table.setItem(row, 1, _ro_item(code))
            self.overview_table.setItem(row, 2, _ro_item(stats["students"],
                                                          Qt.AlignmentFlag.AlignCenter))
            self.overview_table.setItem(row, 3, _ro_item(stats["staff"],
                                                          Qt.AlignmentFlag.AlignCenter))
            self.overview_table.setItem(row, 4, _ro_item(stats["year"],
                                                          Qt.AlignmentFlag.AlignCenter))
            self.overview_table.setItem(row, 5, _ro_item(f"GHS {stats['fees']:,.2f}",
                                                          Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter))
            self.overview_table.setItem(row, 6, _status_item("Active" if is_active else "Inactive", is_active))

        # Summary cards
        card_data = [
            ("Total Branches", str(len(branches)), "🏫", "#3b82f6"),
            ("Active Branches", str(active_branches), "✅", "#22c55e"),
            ("Total Students", str(total_students), "👧", "#8b5cf6"),
            ("Total Staff", str(total_staff), "👨‍🏫", "#f59e0b"),
            ("Total Fees Collected", f"GHS {total_fees:,.0f}", "💰", "#06b6d4"),
        ]
        for title, val, icon, accent in card_data:
            card = StatCard(title, val, icon, accent)
            self.cards_row.addWidget(card)

    def load_branches_table(self):
        branches = self._get_branches()
        self.branches_table.setRowCount(0)
        for bid, bname, code, phone, addr, dbf, is_active in branches:
            row = self.branches_table.rowCount()
            self.branches_table.insertRow(row)
            self.branches_table.setItem(row, 0, _ro_item(str(bid), Qt.AlignmentFlag.AlignCenter))
            self.branches_table.setItem(row, 1, _ro_item(bname))
            self.branches_table.setItem(row, 2, _ro_item(code, Qt.AlignmentFlag.AlignCenter))
            self.branches_table.setItem(row, 3, _ro_item(phone))
            self.branches_table.setItem(row, 4, _ro_item(addr))
            self.branches_table.setItem(row, 5, _ro_item(dbf, Qt.AlignmentFlag.AlignCenter))
            self.branches_table.setItem(row, 6, _status_item("Active" if is_active else "Inactive", is_active))
            self.branches_table.setRowHeight(row, 32)

    def load_admins_table(self):
        from database.master_connection import get_master_session
        from database.master_models import BranchAdmin, Branch
        session = get_master_session()
        admins = (
            session.query(BranchAdmin, Branch.name)
            .join(Branch, BranchAdmin.branch_id == Branch.id)
            .order_by(Branch.name, BranchAdmin.full_name)
            .all()
        )
        self.admins_table.setRowCount(0)
        for admin, branch_name in admins:
            row = self.admins_table.rowCount()
            self.admins_table.insertRow(row)
            self.admins_table.setItem(row, 0, _ro_item(str(admin.id), Qt.AlignmentFlag.AlignCenter))
            self.admins_table.setItem(row, 1, _ro_item(admin.full_name))
            self.admins_table.setItem(row, 2, _ro_item(admin.username))
            self.admins_table.setItem(row, 3, _ro_item(branch_name))
            self.admins_table.setItem(row, 4, _ro_item(admin.email or "—"))
            self.admins_table.setItem(row, 5, _status_item("Active" if admin.is_active else "Inactive",
                                                             admin.is_active))
            self.admins_table.setRowHeight(row, 32)
        session.close()

    # ─────────────────────────────────────────────────────────────────────
    # Branch CRUD Actions
    # ─────────────────────────────────────────────────────────────────────

    def _create_branch(self):
        dlg = CreateBranchDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()
        if not data["name"] or not data["code"]:
            QMessageBox.warning(self, "Validation", "Branch Name and Code are required.")
            return

        from database.master_connection import get_master_session
        from database.master_models import Branch
        session = get_master_session()
        try:
            # Unique code check
            if session.query(Branch).filter(Branch.code == data["code"]).first():
                QMessageBox.warning(self, "Duplicate Code",
                                    f"A branch with code '{data['code']}' already exists.")
                session.close()
                return

            # Generate unique DB filename
            count = session.query(Branch).count()
            db_filename = f"branch_{count + 1}_{data['code'].lower()}.db"
            db_path = DATA_DIR / db_filename

            branch = Branch(
                name=data["name"],
                code=data["code"],
                address=data["address"],
                phone=data["phone"],
                email=data["email"],
                notes=data.get("notes", ""),
                db_filename=db_filename,
                is_active=True,
            )
            session.add(branch)
            session.commit()
            branch_id = branch.id
            session.close()

            # Seed the new branch DB
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            from database.seed import seed_fresh_branch
            success = seed_fresh_branch(db_path, data["name"])
            QApplication.restoreOverrideCursor()

            if success:
                QMessageBox.information(
                    self, "Branch Created",
                    f"✅  Branch '{data['name']}' created successfully!\n\n"
                    f"Database file: {db_filename}\n\n"
                    "You can now add admin accounts for this branch."
                )
            else:
                QMessageBox.warning(self, "Partial Success",
                                    "Branch registered but database seeding failed.\n"
                                    "Please check logs and try again.")
            self.refresh_all()

        except Exception as e:
            session.rollback()
            session.close()
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"Failed to create branch:\n{e}")

    def _edit_branch(self):
        row = self.branches_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a branch to edit.")
            return
        branch_id = int(self.branches_table.item(row, 0).text())

        from database.master_connection import get_master_session
        from database.master_models import Branch
        session = get_master_session()
        branch = session.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            session.close()
            return

        dlg = CreateBranchDialog(self, branch=branch)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            session.close()
            return
        data = dlg.get_data()
        try:
            branch.name = data["name"]
            branch.address = data["address"]
            branch.phone = data["phone"]
            branch.email = data["email"]
            branch.notes = data.get("notes", "")
            session.commit()
            session.close()
            QMessageBox.information(self, "Updated", f"Branch '{data['name']}' updated.")
            self.load_branches_table()
            self.load_overview()
        except Exception as e:
            session.rollback()
            session.close()
            QMessageBox.critical(self, "Error", f"Failed to update branch:\n{e}")

    def _toggle_branch(self):
        row = self.branches_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select a branch.")
            return
        branch_id = int(self.branches_table.item(row, 0).text())
        branch_name = self.branches_table.item(row, 1).text()
        current_status = self.branches_table.item(row, 6).text()
        is_active = current_status == "Active"

        action = "deactivate" if is_active else "reactivate"
        confirm = QMessageBox.question(
            self, f"Confirm {action.capitalize()}",
            f"Are you sure you want to {action} the branch:\n\n'{branch_name}'?\n\n"
            + ("Deactivated branches will not appear in the login branch selector "
               "and their admins will not be able to log in." if is_active else
               "Reactivated branches will become accessible again."),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        from database.master_connection import get_master_session
        from database.master_models import Branch
        session = get_master_session()
        try:
            branch = session.query(Branch).filter(Branch.id == branch_id).first()
            if branch:
                branch.is_active = not is_active
                session.commit()
            session.close()
            self.refresh_all()
        except Exception as e:
            session.rollback()
            session.close()
            QMessageBox.critical(self, "Error", f"Failed to update branch status:\n{e}")

    # ─────────────────────────────────────────────────────────────────────
    # Admin Account CRUD Actions
    # ─────────────────────────────────────────────────────────────────────

    def _add_admin(self):
        branches_raw = self._get_branches()
        active_branches = [(bid, bname, dbf) for bid, bname, *_, dbf, is_active in branches_raw if is_active]
        if not active_branches:
            QMessageBox.warning(self, "No Branches",
                                "Please create at least one active branch before adding admins.")
            return

        dlg = AddAdminDialog(self, branches=active_branches)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        data = dlg.get_data()

        # Find the branch DB filename
        target = next((b for b in active_branches if b[0] == data["branch_id"]), None)
        if not target:
            QMessageBox.critical(self, "Error", "Selected branch not found.")
            return
        _, branch_name, db_filename = target

        from database.master_connection import get_master_session
        from database.master_models import BranchAdmin
        from database.seed import hash_password

        master_session = get_master_session()
        try:
            # Check for duplicate username in master
            if master_session.query(BranchAdmin).filter(
                    BranchAdmin.username == data["username"]).first():
                QMessageBox.warning(self, "Duplicate Username",
                                    f"Username '{data['username']}' is already assigned to another branch.")
                master_session.close()
                return

            # Create User in the branch DB
            branch_user_id = self._create_user_in_branch_db(
                db_filename=db_filename,
                username=data["username"],
                password=data["password"],
                full_name=data["full_name"],
                email=data["email"],
                role_name=data["role"],
            )
            if branch_user_id is None:
                master_session.close()
                return   # error already shown

            # Register in master for login routing
            admin = BranchAdmin(
                branch_id=data["branch_id"],
                username=data["username"],
                full_name=data["full_name"],
                email=data["email"],
                is_active=True,
            )
            master_session.add(admin)
            master_session.commit()
            master_session.close()

            QMessageBox.information(
                self, "Account Created",
                f"✅  Admin account created successfully!\n\n"
                f"Name: {data['full_name']}\n"
                f"Username: {data['username']}\n"
                f"Role: {data['role']}\n"
                f"Branch: {branch_name}\n\n"
                "The user can now log in and will see only this branch's data."
            )
            self.load_admins_table()

        except Exception as e:
            master_session.rollback()
            master_session.close()
            QMessageBox.critical(self, "Error", f"Failed to create admin account:\n{e}")

    def _create_user_in_branch_db(self, db_filename: str, username: str,
                                   password: str, full_name: str,
                                   email: str, role_name: str) -> int | None:
        """
        Insert a User + Staff record into the specified branch DB.
        Returns the new User.id on success, None on failure.
        """
        from database.master_connection import get_branch_session
        from database.models import User, Staff, Role
        from database.seed import hash_password

        db_path = DATA_DIR / db_filename
        if not db_path.exists():
            QMessageBox.critical(self, "Error",
                                 f"Branch database file not found:\n{db_path}\n\n"
                                 "Please ensure the branch was created successfully.")
            return None

        session = get_branch_session(db_filename)
        try:
            # Check duplicate username in branch DB
            if session.query(User).filter(User.username == username).first():
                QMessageBox.warning(self, "Duplicate Username",
                                    f"Username '{username}' already exists in this branch.")
                session.close()
                return None

            # Find the role
            role = session.query(Role).filter(Role.name == role_name).first()
            if not role:
                QMessageBox.critical(self, "Error",
                                     f"Role '{role_name}' not found in branch database.\n"
                                     "The branch may not have been seeded correctly.")
                session.close()
                return None

            # Determine email for user
            user_email = email if email else None

            user = User(
                username=username,
                password_hash=hash_password(password),
                email=user_email,
                role_id=role.id,
                is_active=True,
            )
            session.add(user)
            session.flush()

            # Staff profile
            names = full_name.split(" ", 1)
            fname = names[0]
            lname = names[1] if len(names) > 1 else ""
            staff = Staff(
                user_id=user.id,
                first_name=fname,
                last_name=lname,
                email=user_email,
                phone="",
                role_title=role_name,
                department="Administration",
                hire_date=datetime.date.today(),
                status="Active",
            )
            session.add(staff)
            session.commit()
            uid = user.id
            session.close()
            return uid

        except Exception as e:
            session.rollback()
            session.close()
            QMessageBox.critical(self, "Database Error",
                                 f"Failed to create user in branch database:\n{e}")
            return None

    def _edit_admin(self):
        row = self.admins_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select an admin to edit.")
            return
        admin_id = int(self.admins_table.item(row, 0).text())

        from database.master_connection import get_master_session
        from database.master_models import BranchAdmin, Branch
        session = get_master_session()
        admin = session.query(BranchAdmin).filter(BranchAdmin.id == admin_id).first()
        if not admin:
            session.close()
            return

        branches_raw = self._get_branches()
        active_branches = [(bid, bname, dbf) for bid, bname, *_, dbf, is_active in branches_raw]

        dlg = AddAdminDialog(self, branches=active_branches, admin_record=admin)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            session.close()
            return

        data = dlg.get_data()
        # Find branch db
        target = next((b for b in active_branches if b[0] == admin.branch_id), None)

        try:
            admin.full_name = data["full_name"]
            admin.email = data["email"]
            session.commit()

            # Update User record in branch DB
            if target and data["password"]:
                self._update_branch_user_password(
                    db_filename=target[2],
                    username=admin.username,
                    new_password=data["password"],
                    new_email=data["email"],
                    full_name=data["full_name"],
                )

            session.close()
            QMessageBox.information(self, "Updated", "Admin account updated successfully.")
            self.load_admins_table()

        except Exception as e:
            session.rollback()
            session.close()
            QMessageBox.critical(self, "Error", f"Update failed:\n{e}")

    def _update_branch_user_password(self, db_filename: str, username: str,
                                      new_password: str, new_email: str, full_name: str):
        from database.master_connection import get_branch_session
        from database.models import User, Staff
        from database.seed import hash_password
        session = get_branch_session(db_filename)
        try:
            user = session.query(User).filter(User.username == username).first()
            if user:
                if new_password:
                    user.password_hash = hash_password(new_password)
                if new_email:
                    user.email = new_email
                # Update staff name too
                if user.staff_profile:
                    names = full_name.split(" ", 1)
                    user.staff_profile.first_name = names[0]
                    user.staff_profile.last_name = names[1] if len(names) > 1 else ""
                    user.staff_profile.email = new_email
                session.commit()
        except Exception as e:
            session.rollback()
            print(f"[portal] update_branch_user error: {e}")
        finally:
            session.close()

    def _toggle_admin(self):
        row = self.admins_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "No Selection", "Please select an admin account.")
            return
        admin_id = int(self.admins_table.item(row, 0).text())
        admin_name = self.admins_table.item(row, 1).text()
        current_status = self.admins_table.item(row, 5).text()
        is_active = current_status == "Active"

        action = "deactivate" if is_active else "reactivate"
        confirm = QMessageBox.question(
            self, f"Confirm {action.capitalize()}",
            f"Are you sure you want to {action} the account for:\n\n'{admin_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        from database.master_connection import get_master_session
        from database.master_models import BranchAdmin
        session = get_master_session()
        try:
            admin = session.query(BranchAdmin).filter(BranchAdmin.id == admin_id).first()
            if admin:
                admin.is_active = not is_active
                # Also toggle in branch DB
                branches_raw = self._get_branches()
                target = next((b for b in branches_raw if b[0] == admin.branch_id), None)
                if target:
                    self._toggle_branch_user_status(target[6], admin.username, not is_active)
                session.commit()
            session.close()
            self.load_admins_table()
        except Exception as e:
            session.rollback()
            session.close()
            QMessageBox.critical(self, "Error", f"Failed to update account status:\n{e}")

    def _toggle_branch_user_status(self, db_filename: str, username: str, new_status: bool):
        """Enable or disable a user account in the branch DB."""
        from database.master_connection import get_branch_session
        from database.models import User
        session = get_branch_session(db_filename)
        try:
            user = session.query(User).filter(User.username == username).first()
            if user:
                user.is_active = new_status
                session.commit()
        except Exception as e:
            session.rollback()
            print(f"[portal] toggle_branch_user error: {e}")
        finally:
            session.close()

    # ─────────────────────────────────────────────────────────────────────
    # Theme & Logout
    # ─────────────────────────────────────────────────────────────────────

    def _change_theme(self, theme_key: str):
        config["theme"] = theme_key
        from config import save_config
        save_config(config)
        self.setStyleSheet(get_theme_stylesheet(theme_key))

    def _handle_logout(self):
        confirm = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()
