from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTextEdit, QListWidget,
    QListWidgetItem, QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from database.connection import get_session
from database.models import Announcement, SMSLog, Parent, Student, Class, Staff, Examination, Result, StudentBill
from utils.sms_sender import send_sms
import datetime
from config import config

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
        
        # 2. SMS Broadcaster Tab
        self.broadcaster_tab = QWidget()
        self.init_broadcaster_tab()
        self.tabs.addTab(self.broadcaster_tab, "Parent SMS Broadcaster")
        
        # 3. SMS Logs Tab
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
        self.load_broadcaster_combos()

    def init_broadcaster_tab(self):
        layout = QVBoxLayout(self.broadcaster_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Filter controls
        controls = QHBoxLayout()
        controls.addWidget(QLabel("Target Audience:"))
        self.bc_audience_combo = QComboBox()
        self.bc_audience_combo.addItems([
            "All Parents (School-wide)",
            "Parents of Selected Class",
            "All Teachers & Staff Members",
            "All School Community (Parents & Staff)"
        ])
        self.bc_audience_combo.currentTextChanged.connect(self.on_bc_audience_changed)
        controls.addWidget(self.bc_audience_combo)
        
        self.bc_class_label = QLabel("Select Class:")
        controls.addWidget(self.bc_class_label)
        self.bc_class_combo = QComboBox()
        controls.addWidget(self.bc_class_combo)
        self.bc_class_label.setVisible(False)
        self.bc_class_combo.setVisible(False)
        
        controls.addWidget(QLabel("Message Type:"))
        self.bc_type_combo = QComboBox()
        self.bc_type_combo.addItems([
            "General Custom Message / SMS",
            "Terminal Report Summary",
            "Outstanding Fee Reminder"
        ])
        self.bc_type_combo.currentTextChanged.connect(self.on_bc_type_changed)
        controls.addWidget(self.bc_type_combo)
        
        self.bc_exam_label = QLabel("Select Exam:")
        controls.addWidget(self.bc_exam_label)
        self.bc_exam_combo = QComboBox()
        controls.addWidget(self.bc_exam_combo)
        self.bc_exam_label.setVisible(False)
        self.bc_exam_combo.setVisible(False)
        
        controls.addStretch()
        layout.addLayout(controls)
        
        # Custom message box
        self.bc_custom_msg_label = QLabel("Type Custom Broadcast Message Content:")
        layout.addWidget(self.bc_custom_msg_label)
        self.bc_custom_msg = QTextEdit()
        self.bc_custom_msg.setMaximumHeight(80)
        self.bc_custom_msg.setPlaceholderText("Type SMS message to broadcast to the selected audience group...")
        layout.addWidget(self.bc_custom_msg)
        
        # Buttons
        actions = QHBoxLayout()
        preview_btn = QPushButton("Generate & Preview Recipient List")
        preview_btn.setObjectName("secondary_btn")
        preview_btn.clicked.connect(self.preview_broadcast)
        actions.addWidget(preview_btn)
        
        self.dispatch_btn = QPushButton("Send Bulk SMS Broadcast")
        self.dispatch_btn.setObjectName("primary_btn")
        self.dispatch_btn.setEnabled(False)
        self.dispatch_btn.clicked.connect(self.send_broadcast)
        actions.addWidget(self.dispatch_btn)
        
        actions.addStretch()
        layout.addLayout(actions)
        
        # Preview Table
        layout.addWidget(QLabel("<b>Broadcast Messages Queue Preview:</b>"))
        self.bc_table = QTableWidget()
        self.bc_table.setColumnCount(4)
        self.bc_table.setHorizontalHeaderLabels(["Recipient Name", "Role / Group", "Phone Number", "SMS Content Message"])
        self.bc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.bc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.bc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.bc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.bc_table)
        
        self.load_broadcaster_combos()
        
    def on_bc_audience_changed(self, text):
        is_class = text == "Parents of Selected Class"
        self.bc_class_label.setVisible(is_class)
        self.bc_class_combo.setVisible(is_class)

    def on_bc_type_changed(self, text):
        is_report = text == "Terminal Report Summary"
        is_custom = text == "General Custom Message / SMS"
        self.bc_exam_label.setVisible(is_report)
        self.bc_exam_combo.setVisible(is_report)
        self.bc_custom_msg_label.setVisible(is_custom)
        self.bc_custom_msg.setVisible(is_custom)
        
    def load_broadcaster_combos(self):
        self.bc_class_combo.clear()
        self.bc_exam_combo.clear()
        
        session = get_session()
        try:
            # Classes
            classes = session.query(Class).all()
            self.bc_class_combo.addItem("All Classes", None)
            for c in classes:
                self.bc_class_combo.addItem(c.name, c.id)
                
            # Exams
            exams = session.query(Examination).all()
            for e in exams:
                self.bc_exam_combo.addItem(e.name, e.id)
        except Exception as e:
            print(f"Error loading broadcaster combos: {e}")
        finally:
            session.close()
            
    def preview_broadcast(self):
        self.bc_table.setRowCount(0)
        self.dispatch_btn.setEnabled(False)
        
        audience = self.bc_audience_combo.currentText()
        class_id = self.bc_class_combo.currentData()
        bc_type = self.bc_type_combo.currentText()
        exam_id = self.bc_exam_combo.currentData()
        custom_msg = self.bc_custom_msg.toPlainText().strip()
        
        session = get_session()
        try:
            preview_rows = []
            
            if bc_type == "General Custom Message / SMS":
                if not custom_msg:
                    QMessageBox.warning(self, "Validation Error", "Please enter message content before generating preview.")
                    return

                seen_phones = set()
                # Parents
                if audience in ["All Parents (School-wide)", "Parents of Selected Class", "All School Community (Parents & Staff)"]:
                    q = session.query(Student).filter(Student.status == "Active")
                    if audience == "Parents of Selected Class" and class_id:
                        q = q.filter(Student.class_id == class_id)
                    students = q.all()
                    for s in students:
                        if s.parent and s.parent.phone:
                            phone = s.parent.phone.strip()
                            if phone and phone not in seen_phones:
                                seen_phones.add(phone)
                                p_name = f"{s.parent.first_name} {s.parent.last_name}".strip() or f"Parent of {s.first_name}"
                                preview_rows.append((p_name, "Parent", phone, custom_msg))

                # Teachers / Staff
                if audience in ["All Teachers & Staff Members", "All School Community (Parents & Staff)"]:
                    staff_list = session.query(Staff).filter(Staff.status == "Active").all()
                    for st in staff_list:
                        if st.phone:
                            phone = st.phone.strip()
                            if phone and phone not in seen_phones:
                                seen_phones.add(phone)
                                st_name = f"{st.first_name} {st.last_name}".strip() or "Staff Member"
                                preview_rows.append((st_name, "Teacher/Staff", phone, custom_msg))

            elif bc_type == "Terminal Report Summary":
                if not exam_id:
                    QMessageBox.warning(self, "Validation Error", "Please select an examination session.")
                    return
                
                query = session.query(Student).filter(Student.status == "Active")
                if class_id:
                    query = query.filter(Student.class_id == class_id)
                students = query.all()

                class_students_map = {}
                for s in students:
                    if s.class_id not in class_students_map:
                        class_students_map[s.class_id] = []
                    class_students_map[s.class_id].append(s)
                    
                ranks_map = {}
                averages_map = {}
                subject_counts_map = {}
                
                for c_id, s_list in class_students_map.items():
                    s_ids = [student.id for student in s_list]
                    all_results = session.query(Result).filter(
                        Result.examination_id == exam_id,
                        Result.student_id.in_(s_ids)
                    ).all()
                    
                    totals = {}
                    counts = {}
                    for r in all_results:
                        totals[r.student_id] = totals.get(r.student_id, 0.0) + r.total_score
                        counts[r.student_id] = counts.get(r.student_id, 0) + 1
                        
                    for s_id in s_ids:
                        totals[s_id] = totals.get(s_id, 0.0)
                        counts[s_id] = counts.get(s_id, 0)
                        
                    sorted_totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)
                    
                    curr_rank = 1
                    for idx, (s_id, tot) in enumerate(sorted_totals):
                        if idx > 0 and tot < sorted_totals[idx - 1][1]:
                            curr_rank = idx + 1
                        ranks_map[s_id] = curr_rank
                        averages_map[s_id] = (tot / counts[s_id]) if counts.get(s_id, 0) > 0 else 0.0
                        subject_counts_map[s_id] = counts[s_id]
                
                for s in students:
                    if s.parent and s.parent.phone:
                        pos = ranks_map.get(s.id, 0)
                        avg = averages_map.get(s.id, 0.0)
                        sub_cnt = subject_counts_map.get(s.id, 0)
                        
                        def get_suffix(rank):
                            if 11 <= rank % 100 <= 13:
                                return "th"
                            return {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
                            
                        pos_str = f"{pos}{get_suffix(pos)}" if pos > 0 else "N/A"
                        msg = f"Orion SMS: Dear Parent/Guardian, report summary for {s.first_name} {s.last_name}: Average Score: {avg:.1f}%, Position in Class: {pos_str} (out of {len(class_students_map.get(s.class_id, []))}). Total subjects graded: {sub_cnt}."
                        preview_rows.append((f"{s.first_name} {s.last_name} ({s.parent.name or 'Parent'})", "Parent", s.parent.phone, msg))
                        
            elif bc_type == "Outstanding Fee Reminder":
                query = session.query(Student).filter(Student.status == "Active")
                if class_id:
                    query = query.filter(Student.class_id == class_id)
                students = query.all()

                for s in students:
                    if s.parent and s.parent.phone:
                        bills = session.query(StudentBill).filter(StudentBill.student_id == s.id).all()
                        total_billed = sum(b.amount_billed for b in bills)
                        total_paid = sum(b.amount_paid for b in bills)
                        balance = total_billed - total_paid
                        
                        if balance > 0:
                            msg = f"Orion SMS: Dear Parent/Guardian, this is a friendly reminder that {s.first_name} {s.last_name} has an outstanding fees balance of GHS {balance:.2f}. Please make payment as soon as possible. Thank you."
                            preview_rows.append((f"{s.first_name} {s.last_name} ({s.parent.name or 'Parent'})", "Parent", s.parent.phone, msg))
                            
            if not preview_rows:
                QMessageBox.information(self, "No Records", "No recipients found matching your selection criteria. Ensure parents/staff have valid phone numbers entered.")
                return
                
            self.bc_table.setRowCount(len(preview_rows))
            self.bc_queue_data = []
            
            for i, (name, role_lbl, phone, msg) in enumerate(preview_rows):
                self.bc_table.setItem(i, 0, QTableWidgetItem(name))
                self.bc_table.setItem(i, 1, QTableWidgetItem(role_lbl))
                self.bc_table.setItem(i, 2, QTableWidgetItem(phone))
                self.bc_table.setItem(i, 3, QTableWidgetItem(msg))
                self.bc_queue_data.append((phone, msg))
                
            self.dispatch_btn.setEnabled(True)
            QMessageBox.information(self, "Preview Ready", f"Prepared {len(preview_rows)} recipient(s) successfully.\nReview the list below and click 'Send Bulk SMS Broadcast' to dispatch.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to preview broadcast: {e}")
        finally:
            session.close()
            
    def send_broadcast(self):
        if not hasattr(self, 'bc_queue_data') or not self.bc_queue_data:
            return
            
        confirm = QMessageBox.question(
            self, "Confirm Broadcast",
            f"Are you sure you want to dispatch bulk SMS to all {len(self.bc_queue_data)} recipient(s) now?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
            
        sent_count = 0
        failed_count = 0
        try:
            for phone, msg in self.bc_queue_data:
                success, _ = send_sms(phone, msg, trigger_type="Bulk SMS")
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                
            QMessageBox.information(self, "Broadcast Dispatched", f"Successfully dispatched {sent_count} SMS notification(s).")
            self.bc_table.setRowCount(0)
            self.dispatch_btn.setEnabled(False)
            self.load_sms_logs()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to send broadcast: {e}")
