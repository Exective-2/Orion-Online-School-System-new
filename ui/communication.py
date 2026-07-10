from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTextEdit, QListWidget,
    QListWidgetItem, QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from database.connection import get_session
from database.models import Announcement, SMSLog, Parent
import datetime
from config import config

def send_sms(recipient_phone: str, message: str, trigger_type: str) -> bool:
    """
    Simulates sending an SMS message by logging it directly into the database.
    """
    session = get_session()
    try:
        log = SMSLog(
            recipient_phone=recipient_phone,
            message_content=message,
            status="Sent",
            trigger_type=trigger_type
        )
        session.add(log)
        session.commit()
        return True
    except Exception as e:
        print(f"SMS Log error: {e}")
        return False
    finally:
        session.close()

class CommunicationPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        
        # 1. Notice Board Tab
        self.notice_tab = QWidget()
        self.init_notice_tab()
        self.tabs.addTab(self.notice_tab, "Notice Board")
        
        # 2. SMS Logs Tab
        self.sms_tab = QWidget()
        self.init_sms_tab()
        self.tabs.addTab(self.sms_tab, "SMS Dispatch Logs")
        
        main_layout.addWidget(self.tabs)
        
    def init_notice_tab(self):
        layout = QHBoxLayout(self.notice_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Left Panel: Broadcast Form
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(20, 20, 20, 20)
        form_layout.setSpacing(15)
        
        form_title = QLabel("Broadcast New Notice")
        form_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        form_layout.addWidget(form_title)
        
        form_layout.addWidget(QLabel("Announcement Title:"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. End of Term Examination Schedule")
        form_layout.addWidget(self.title_input)
        
        form_layout.addWidget(QLabel("Target Audience Group:"))
        self.audience_combo = QComboBox()
        self.audience_combo.addItems(["All", "Teachers", "Parents", "Students"])
        form_layout.addWidget(self.audience_combo)
        
        form_layout.addWidget(QLabel("Notice Content Message:"))
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("Type the full detail message to broadcast here...")
        form_layout.addWidget(self.content_input)
        
        # Duplicate SMS option
        self.sms_cb = QCheckBox("Send duplicate SMS alerts to Parents")
        form_layout.addWidget(self.sms_cb)
        
        send_btn = QPushButton("Publish Announcement")
        send_btn.setObjectName("primary_btn")
        send_btn.clicked.connect(self.publish_announcement)
        form_layout.addWidget(send_btn)
        
        layout.addWidget(form_frame, stretch=2)
        
        # Right Panel: Active Announcements Board
        board_frame = QFrame()
        board_frame.setObjectName("card")
        board_layout = QVBoxLayout(board_frame)
        board_layout.setContentsMargins(20, 20, 20, 20)
        board_layout.setSpacing(10)
        
        board_title = QLabel("Published Board Notices")
        board_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6;")
        board_layout.addWidget(board_title)
        
        self.board_list = QListWidget()
        self.board_list.setStyleSheet("background-color: transparent; border: none;")
        self.board_list.setWordWrap(True)
        board_layout.addWidget(self.board_list)
        
        layout.addWidget(board_frame, stretch=3)
        
        self.load_board()
        
    def load_board(self):
        self.board_list.clear()
        session = get_session()
        try:
            announcements = session.query(Announcement).order_by(Announcement.created_at.desc()).all()
            for ann in announcements:
                item = QListWidgetItem()
                widget = QWidget()
                w_layout = QVBoxLayout(widget)
                w_layout.setContentsMargins(10, 10, 10, 10)
                w_layout.setSpacing(5)
                
                # Add background styling using theme card component
                card_frame = QFrame()
                card_frame.setObjectName("card")
                card_frame.setStyleSheet("padding: 10px;")
                cf_layout = QVBoxLayout(card_frame)
                
                active_theme = config.get("theme", "dark").lower()
                is_light = active_theme == "light"
                
                title_lbl = QLabel(ann.title)
                title_lbl.setStyleSheet("font-weight: bold; font-size: 14px; color: #0f172a;" if is_light else "font-weight: bold; font-size: 14px; color: #ffffff;")
                
                body_lbl = QLabel(ann.content)
                body_lbl.setWordWrap(True)
                body_lbl.setStyleSheet("color: #334155; font-size: 12px; margin-top: 5px;" if is_light else "color: #94a3b8; font-size: 12px; margin-top: 5px;")
                
                info_lbl = QLabel(f"Target Group: {ann.target_audience} | Published: {ann.created_at.strftime('%Y-%m-%d %H:%M')}")
                info_lbl.setStyleSheet("color: #64748b; font-size: 10px;")
                
                cf_layout.addWidget(title_lbl)
                cf_layout.addWidget(body_lbl)
                cf_layout.addWidget(info_lbl)
                
                w_layout.addWidget(card_frame)
                
                item.setSizeHint(widget.sizeHint())
                self.board_list.addItem(item)
                self.board_list.setItemWidget(item, widget)
        except Exception as e:
            print(f"Error loading notices: {e}")
        finally:
            session.close()
            
    def publish_announcement(self):
        title = self.title_input.text().strip()
        content = self.content_input.toPlainText().strip()
        audience = self.audience_combo.currentText()
        
        if not title or not content:
            QMessageBox.warning(self, "Validation Error", "Notice title and content are required.")
            return
            
        session = get_session()
        try:
            staff_id = self.user.staff_profile.id if self.user.staff_profile else None
            ann = Announcement(
                title=title,
                content=content,
                target_audience=audience,
                created_by=staff_id
            )
            session.add(ann)
            session.flush()
            
            # Send duplicate SMS triggers if checked
            sms_count = 0
            if self.sms_cb.isChecked():
                parents = session.query(Parent).all()
                sms_message = f"Orion Notice: {title} - {content[:100]}"
                if len(content) > 100:
                    sms_message += "..."
                for p in parents:
                    if p.phone:
                        # Log mock SMS
                        sms_log = SMSLog(
                            recipient_phone=p.phone,
                            message_content=sms_message,
                            status="Sent",
                            trigger_type="Notice"
                        )
                        session.add(sms_log)
                        sms_count += 1
            
            session.commit()
            msg = "Notice published successfully."
            if sms_count > 0:
                msg += f"\nSent SMS notifications to {sms_count} parents."
            QMessageBox.information(self, "Success", msg)
            
            self.title_input.clear()
            self.content_input.clear()
            self.sms_cb.setChecked(False)
            self.load_board()
            self.load_sms_logs()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to publish announcement: {e}")
        finally:
            session.close()
            
    def init_sms_tab(self):
        tab_layout = QVBoxLayout(self.sms_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        actions = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Logs")
        refresh_btn.setObjectName("secondary_btn")
        refresh_btn.clicked.connect(self.load_sms_logs)
        actions.addWidget(refresh_btn)
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        self.sms_table = QTableWidget()
        self.sms_table.setColumnCount(5)
        self.sms_table.setHorizontalHeaderLabels(["ID", "Recipient Phone", "Message Content", "Time Logged", "Status"])
        self.sms_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sms_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.sms_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        tab_layout.addWidget(self.sms_table)
        self.load_sms_logs()
        
    def load_sms_logs(self):
        self.sms_table.setRowCount(0)
        session = get_session()
        try:
            logs = session.query(SMSLog).order_by(SMSLog.sent_at.desc()).all()
            self.sms_table.setRowCount(len(logs))
            for i, l in enumerate(logs):
                self.sms_table.setItem(i, 0, QTableWidgetItem(str(l.id)))
                self.sms_table.setItem(i, 1, QTableWidgetItem(l.recipient_phone))
                self.sms_table.setItem(i, 2, QTableWidgetItem(l.message_content))
                self.sms_table.setItem(i, 3, QTableWidgetItem(l.sent_at.strftime("%Y-%m-%d %H:%M:%S")))
                self.sms_table.setItem(i, 4, QTableWidgetItem(l.status))
        except Exception as e:
            print(f"Error loading SMS logs: {e}")
        finally:
            session.close()
            
    def refresh(self):
        self.load_board()
        self.load_sms_logs()
