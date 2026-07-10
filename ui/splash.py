import os
from PySide6.QtWidgets import QSplashScreen, QProgressBar, QLabel, QVBoxLayout, QFrame
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QFont
from config import config

class OrionSplashScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Dimensions
        self.setFixedSize(500, 320)
        
        # Outer Frame
        self.frame = QFrame(self)
        self.frame.setObjectName("splash_frame")
        self.frame.setGeometry(0, 0, 500, 320)
        
        # Theme-aware stylesheet
        active_theme = config.get("theme", "dark").lower()
        is_dark = active_theme != "light"
        if active_theme == "emerald":
            bg_color = "rgba(5, 20, 15, 0.95)"
            border_color = "rgba(20, 64, 46, 0.5)"
            text_color = "#f8fafc"
            accent_color = "#10b981"
        elif active_theme == "sapphire":
            bg_color = "rgba(6, 11, 19, 0.95)"
            border_color = "rgba(30, 46, 79, 0.5)"
            text_color = "#f8fafc"
            accent_color = "#3b82f6"
        elif active_theme == "amber":
            bg_color = "rgba(21, 15, 7, 0.95)"
            border_color = "rgba(74, 51, 26, 0.5)"
            text_color = "#f8fafc"
            accent_color = "#f59e0b"
        elif is_dark:
            bg_color = "rgba(15, 23, 42, 0.95)"
            border_color = "rgba(51, 65, 85, 0.5)"
            text_color = "#f8fafc"
            accent_color = "#3b82f6"
        else:
            bg_color = "rgba(255, 255, 255, 0.98)"
            border_color = "rgba(226, 232, 240, 0.8)"
            text_color = "#0f172a"
            accent_color = "#2563eb"
            
        self.frame.setStyleSheet(f"""
            QFrame#splash_frame {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self.frame)
        layout.setContentsMargins(30, 40, 30, 30)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # School Logo
        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_path = config.get("school_logo", "")
        logo_loaded = False
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                self.logo_label.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                logo_loaded = True
                
        if not logo_loaded:
            # Fallback to a default styled icon
            self.logo_label.setText("🏫")
            self.logo_label.setFont(QFont("Segoe UI Emoji", 48))
            self.logo_label.setStyleSheet(f"color: {accent_color}; background: transparent; border: none;")
            
        layout.addWidget(self.logo_label)
        layout.addSpacing(10)
        
        # School Name
        self.title_label = QLabel(config.get("school_name", "Orion School System"))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont("Helvetica Neue", 20, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none;")
        layout.addWidget(self.title_label)
        
        # Motto
        self.motto_label = QLabel(config.get("school_motto", ""))
        self.motto_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        motto_font = QFont("Helvetica Neue", 11)
        motto_font.setItalic(True)
        self.motto_label.setFont(motto_font)
        self.motto_label.setStyleSheet("color: #64748b; background: transparent; border: none;")
        layout.addWidget(self.motto_label)
        
        layout.addStretch()
        
        # Status Label
        self.status_label = QLabel("Initializing systems...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self.status_label.setFont(QFont("Helvetica Neue", 10))
        self.status_label.setStyleSheet("color: #64748b; background: transparent; border: none;")
        layout.addWidget(self.status_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(148, 163, 184, 0.2);
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {accent_color};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # Animation / Timer settings
        self.counter = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        
    def start_loading(self):
        self.show()
        self.timer.start(20) # 20ms * 100 = 2 seconds loading
        
    def update_progress(self):
        self.counter += 1
        self.progress_bar.setValue(self.counter)
        
        if self.counter == 10:
            self.status_label.setText("Loading components...")
        elif self.counter == 30:
            self.status_label.setText("Connecting to database...")
        elif self.counter == 50:
            self.status_label.setText("Applying theme presets...")
        elif self.counter == 70:
            self.status_label.setText("Checking user credentials...")
        elif self.counter == 90:
            self.status_label.setText("Starting services...")
            
        if self.counter >= 100:
            self.timer.stop()
            self.close()
