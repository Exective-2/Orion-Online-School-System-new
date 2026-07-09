import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, 
    QLabel, QPushButton, QStackedWidget, QSizePolicy, QMessageBox,
    QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QAction, QPixmap
from config import config, save_config
from ui.theme import get_theme_stylesheet

# Import UI panels (they will be implemented next)
from ui.dashboard import DashboardPanel
from ui.students import StudentsPanel
from ui.staff import StaffPanel
from ui.academics import AcademicsPanel
from ui.attendance import AttendancePanel
from ui.exams import ExamsPanel
from ui.fees import FeesPanel
from ui.library import LibraryPanel
from ui.inventory import InventoryPanel
from ui.communication import CommunicationPanel
from ui.settings import SettingsPanel

class MainWindow(QMainWindow):
    logout_requested = Signal()
    
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.active_theme = config.get("theme", "dark")
        
        self.setWindowTitle("Orion School Management System")
        self.resize(1200, 800)
        
        # Apply stylesheet
        self.apply_theme()
        
        self.init_ui()
        
    def apply_theme(self):
        self.setStyleSheet(get_theme_stylesheet(self.active_theme))
        
    def toggle_theme(self):
        self.active_theme = "light" if self.active_theme == "dark" else "dark"
        config["theme"] = self.active_theme
        save_config(config)
        self.apply_theme()
        
    def init_ui(self):
        # Central widget and horizontal layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 1. Sidebar Container
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setMinimumWidth(220)
        self.sidebar.setMaximumWidth(220)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 20, 10, 20)
        sidebar_layout.setSpacing(8)
        
        # School logo/motto header
        school_logo = QLabel()
        school_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = config.get("school_logo", "")
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            school_logo.setPixmap(scaled)
        else:
            school_logo.setText("ORION")
            school_logo.setStyleSheet("font-size: 24px; font-weight: bold; color: #3b82f6; padding: 10px;")
            
        motto = QLabel(config.get("school_motto", ""))
        motto.setStyleSheet("font-size: 10px; color: #64748b; font-style: italic; margin-bottom: 20px;")
        motto.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motto.setWordWrap(True)
        
        sidebar_layout.addWidget(school_logo)
        sidebar_layout.addWidget(motto)
        
        # 2. Main Content Frame (Header + Stacked Content)
        content_frame = QFrame()
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Header bar
        header = QFrame()
        header.setObjectName("header")
        header.setMinimumHeight(60)
        header.setMaximumHeight(60)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        self.header_title = QLabel("Dashboard")
        self.header_title.setObjectName("header_title")
        header_layout.addWidget(self.header_title)
        
        header_layout.addStretch()
        
        # Term Status Label
        term_label = QLabel(f"{config.get('school_name', '')} | Term 1")
        term_label.setStyleSheet("color: #64748b; font-weight: bold; margin-right: 15px;")
        header_layout.addWidget(term_label)
        
        # Theme toggle button
        theme_btn = QPushButton("Toggle Theme")
        theme_btn.setObjectName("secondary_btn")
        theme_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        theme_btn.clicked.connect(self.toggle_theme)
        header_layout.addWidget(theme_btn)
        
        # User menu button
        staff_name = "Super Admin"
        if self.user.staff_profile:
            staff_name = f"{self.user.staff_profile.first_name} {self.user.staff_profile.last_name}"
            
        user_btn = QPushButton(f"{staff_name} ({self.user.role.name}) ▾")
        user_btn.setObjectName("secondary_btn")
        user_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # User dropdown menu
        user_menu = QMenu(self)
        logout_action = QAction("Logout", self)
        logout_action.triggered.connect(self.handle_logout)
        user_menu.addAction(logout_action)
        user_btn.setMenu(user_menu)
        
        header_layout.addWidget(user_btn)
        
        content_layout.addWidget(header)
        
        # Stacked Widget for pages
        self.stacked_widget = QStackedWidget()
        content_layout.addWidget(self.stacked_widget)
        
        # Register and configure view panels
        self.panels = []
        self.sidebar_buttons = []
        
        # Definitions of panels (Name, Icon, Class, Permissions required)
        panel_definitions = [
            ("Dashboard", DashboardPanel, ["view_dashboard"]),
            ("Students", StudentsPanel, ["manage_students"]),
            ("Staff", StaffPanel, ["manage_staff"]),
            ("Academics", AcademicsPanel, ["manage_academics"]),
            ("Attendance", AttendancePanel, ["manage_attendance"]),
            ("Examinations", ExamsPanel, ["manage_exams"]),
            ("Fees & Finance", FeesPanel, ["manage_fees"]),
            ("Library", LibraryPanel, ["manage_library"]),
            ("Inventory", InventoryPanel, ["manage_inventory"]),
            ("Announcements", CommunicationPanel, ["manage_communication"]),
            ("System Settings", SettingsPanel, [])
        ]
        
        # Retrieve user permissions list
        user_perms = [p.name for p in self.user.role.permissions] if self.user.role else []
        
        for name, cls, required_perms in panel_definitions:
            # Check permission
            has_permission = False
            if not required_perms:
                has_permission = True
            elif self.user.role.name == "Super Admin":
                has_permission = True
            else:
                for rp in required_perms:
                    if rp in user_perms:
                        has_permission = True
                        break
            
            if not has_permission:
                continue
                
            # Dynamic naming for settings
            button_label = name
            if name == "System Settings" and not any(p == "manage_settings" for p in user_perms) and self.user.role.name != "Super Admin":
                button_label = "My Account"
                
            # Instantiate panel and add to stacked widget
            panel = cls(self.user)
            self.stacked_widget.addWidget(panel)
            self.panels.append(panel)
            
            # Create sidebar button
            btn = QPushButton(button_label)
            btn.setObjectName("sidebar_btn")
            btn.setProperty("active", "false")
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            
            # Map index
            index = len(self.panels) - 1
            btn.clicked.connect(lambda checked=False, idx=index, n=name: self.switch_panel(idx, n))
            
            sidebar_layout.addWidget(btn)
            self.sidebar_buttons.append(btn)
            
        sidebar_layout.addStretch()
        
        # Logout button at bottom of sidebar
        logout_btn = QPushButton("Logout")
        logout_btn.setObjectName("danger_btn")
        logout_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        logout_btn.clicked.connect(self.handle_logout)
        sidebar_layout.addWidget(logout_btn)
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(content_frame)
        
        # Select first panel by default
        if self.panels:
            self.switch_panel(0, panel_definitions[0][0])
            
    def switch_panel(self, index, panel_name):
        self.stacked_widget.setCurrentIndex(index)
        self.header_title.setText(panel_name)
        
        # Refresh current panel content if refresh method exists
        active_panel = self.panels[index]
        if hasattr(active_panel, "refresh"):
            active_panel.refresh()
            
        # Update sidebar button states
        for i, btn in enumerate(self.sidebar_buttons):
            if i == index:
                btn.setProperty("active", "true")
            else:
                btn.setProperty("active", "false")
            # Refresh QSS style representation
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            
    def handle_logout(self):
        confirm = QMessageBox.question(
            self, "Logout", "Are you sure you want to log out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.logout_requested.emit()
