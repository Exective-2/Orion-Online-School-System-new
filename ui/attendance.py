from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDateEdit, QTabWidget, QRadioButton,
    QButtonGroup, QLineEdit
)
from PySide6.QtCore import Qt, QDate, Signal
from database.connection import get_session
from database.models import Student, Staff, Attendance, SMSLog
from config import config
import datetime

class AttendancePanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QTabWidget()
        
        # 1. Student Attendance
        self.student_tab = QWidget()
        self.init_student_tab()
        self.tabs.addTab(self.student_tab, "Student Register")
        
        # 2. Staff Attendance (Only head teacher and admin can take staff attendance)
        is_admin_or_head = False
        if self.user.role:
            is_admin_or_head = self.user.role.name in ["Super Admin", "Admin/Headteacher"]
            
        if is_admin_or_head:
            self.staff_tab = QWidget()
            self.init_staff_tab()
            self.tabs.addTab(self.staff_tab, "Staff Register")
        
        layout.addWidget(self.tabs)
        
    def init_student_tab(self):
        tab_layout = QVBoxLayout(self.student_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        # Controls Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout.addWidget(QLabel("Date:"))
        self.stud_date_edit = QDateEdit()
        self.stud_date_edit.setCalendarPopup(True)
        self.stud_date_edit.setDate(QDate.currentDate())
        self.stud_date_edit.dateChanged.connect(self.load_student_roll)
        header_layout.addWidget(self.stud_date_edit)
        
        header_layout.addWidget(QLabel("Class Stream:"))
        self.stud_class_combo = QComboBox()
        self.stud_class_combo.currentIndexChanged.connect(self.load_student_roll)
        header_layout.addWidget(self.stud_class_combo)
        
        header_layout.addStretch()
        tab_layout.addWidget(header)
        
        # Student Roll Table
        self.stud_table = QTableWidget()
        self.stud_table.verticalHeader().setDefaultSectionSize(40)
        self.stud_table.setColumnCount(5)
        self.stud_table.setHorizontalHeaderLabels(["Student ID", "Student Name", "Status", "Remarks / Reason", "Saved Status"])
        self.stud_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.stud_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.stud_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        tab_layout.addWidget(self.stud_table)
        
        # Save Button
        save_btn = QPushButton("Save Student Attendance")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self.save_student_attendance)
        tab_layout.addWidget(save_btn)
        
        self.load_classes_combo()
        
    def load_classes_combo(self):
        from database.models import Class, ClassTeacher
        session = get_session()
        try:
            is_admin_or_head = False
            if self.user.role:
                is_admin_or_head = self.user.role.name in ["Super Admin", "Admin/Headteacher"]
                
            if is_admin_or_head:
                classes = session.query(Class).all()
            else:
                classes = []
                if self.user.staff_profile:
                    ct_records = session.query(ClassTeacher).filter(
                        ClassTeacher.staff_id == self.user.staff_profile.id
                    ).all()
                    classes = [record.class_obj for record in ct_records if record.class_obj]
            
            self.stud_class_combo.clear()
            for c in classes:
                self.stud_class_combo.addItem(c.name, c.id)
                
            if not classes:
                self.stud_class_combo.addItem("No classes assigned to you", None)
        except Exception as e:
            print(f"Error loading classes: {e}")
        finally:
            session.close()

    def load_student_roll(self):
        self.stud_table.setRowCount(0)
        class_id = self.stud_class_combo.currentData()
        if not class_id:
            return
            
        stud_date = self.stud_date_edit.date()
        target_date = datetime.date(stud_date.year(), stud_date.month(), stud_date.day())
        
        session = get_session()
        try:
            students = session.query(Student).filter(
                Student.class_id == class_id, 
                Student.status == "Active"
            ).order_by(Student.last_name.asc()).all()
            
            self.stud_table.setRowCount(len(students))
            self.stud_button_groups = {} # student_id -> QButtonGroup
            self.stud_remarks_inputs = {} # student_id -> QLineEdit
            
            for i, s in enumerate(students):
                self.stud_table.setItem(i, 0, QTableWidgetItem(s.id))
                self.stud_table.setItem(i, 1, QTableWidgetItem(f"{s.last_name}, {s.first_name} {s.other_names or ''}"))
                
                # Check for existing log
                att_log = session.query(Attendance).filter(
                    Attendance.student_id == s.id,
                    Attendance.date == target_date
                ).first()
                
                # Present / Absent / Late options
                widget = QWidget()
                w_layout = QHBoxLayout(widget)
                w_layout.setContentsMargins(5, 2, 5, 2)
                
                btn_p = QRadioButton("P")
                btn_a = QRadioButton("A")
                btn_l = QRadioButton("L")
                
                grp = QButtonGroup(self)
                grp.addButton(btn_p, 1)
                grp.addButton(btn_a, 2)
                grp.addButton(btn_l, 3)
                self.stud_button_groups[s.id] = grp
                
                w_layout.addWidget(btn_p)
                w_layout.addWidget(btn_a)
                w_layout.addWidget(btn_l)
                
                self.stud_table.setCellWidget(i, 2, widget)
                
                # Remarks edit
                remarks_edit = QLineEdit()
                remarks_edit.setPlaceholderText("Late reason, sick note etc.")
                if att_log:
                    remarks_edit.setText(att_log.remarks or "")
                self.stud_remarks_inputs[s.id] = remarks_edit
                self.stud_table.setCellWidget(i, 3, remarks_edit)
                
                # Set toggled status
                saved_status = "Not Saved"
                if att_log:
                    saved_status = att_log.status
                    if att_log.status == "Present":
                        btn_p.setChecked(True)
                    elif att_log.status == "Absent":
                        btn_a.setChecked(True)
                    elif att_log.status == "Late":
                        btn_l.setChecked(True)
                else:
                    # default to present
                    btn_p.setChecked(True)
                    
                self.stud_table.setItem(i, 4, QTableWidgetItem(saved_status))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load roll call:\n{e}")
        finally:
            session.close()

    def save_student_attendance(self):
        class_id = self.stud_class_combo.currentData()
        if not class_id:
            return
            
        stud_date = self.stud_date_edit.date()
        target_date = datetime.date(stud_date.year(), stud_date.month(), stud_date.day())
        
        session = get_session()
        try:
            # Active term ids from config
            ay_id = config.get("active_academic_year_id", 1)
            term_id = config.get("active_term_id", 1)
            
            for s_id, grp in self.stud_button_groups.items():
                checked_id = grp.checkedId()
                status_str = "Present"
                if checked_id == 2:
                    status_str = "Absent"
                elif checked_id == 3:
                    status_str = "Late"
                    
                remarks_str = self.stud_remarks_inputs[s_id].text().strip() or None
                
                # Query existing attendance record
                att = session.query(Attendance).filter(
                    Attendance.student_id == s_id,
                    Attendance.date == target_date
                ).first()
                
                if att:
                    att.status = status_str
                    att.remarks = remarks_str
                else:
                    att = Attendance(
                        date=target_date,
                        student_id=s_id,
                        status=status_str,
                        remarks=remarks_str,
                        academic_year_id=ay_id,
                        term_id=term_id
                    )
                    session.add(att)
                    
                # If student is absent, dispatch SMS to parent
                if status_str == "Absent":
                    student = session.query(Student).filter(Student.id == s_id).first()
                    if student and student.parent and student.parent.phone:
                        sms_msg = f"Orion Notice: Dear Parent, your ward {student.first_name} {student.last_name} was marked ABSENT today ({target_date.strftime('%Y-%m-%d')})."
                        sms_log = SMSLog(
                            recipient_phone=student.parent.phone,
                            message_content=sms_msg,
                            status="Sent",
                            trigger_type="Attendance"
                        )
                        session.add(sms_log)
                    
            session.commit()
            QMessageBox.information(self, "Success", "Student attendance saved successfully.")
            self.load_student_roll()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save student attendance:\n{e}")
        finally:
            session.close()

    # --- Staff Attendance ---
    def init_staff_tab(self):
        tab_layout = QVBoxLayout(self.staff_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        # Controls Header
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout.addWidget(QLabel("Date:"))
        self.staff_date_edit = QDateEdit()
        self.staff_date_edit.setCalendarPopup(True)
        self.staff_date_edit.setDate(QDate.currentDate())
        self.staff_date_edit.dateChanged.connect(self.load_staff_roll)
        header_layout.addWidget(self.staff_date_edit)
        header_layout.addStretch()
        tab_layout.addWidget(header)
        
        # Staff table
        self.staff_table = QTableWidget()
        self.staff_table.verticalHeader().setDefaultSectionSize(40)
        self.staff_table.setColumnCount(5)
        self.staff_table.setHorizontalHeaderLabels(["Staff ID", "Staff Name", "Role", "Status", "Remarks"])
        self.staff_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.staff_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.staff_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tab_layout.addWidget(self.staff_table)
        
        # Save Button
        save_btn = QPushButton("Save Staff Attendance")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self.save_staff_attendance)
        tab_layout.addWidget(save_btn)
        
        self.load_staff_roll()
        
    def load_staff_roll(self):
        self.staff_table.setRowCount(0)
        staff_date = self.staff_date_edit.date()
        target_date = datetime.date(staff_date.year(), staff_date.month(), staff_date.day())
        
        session = get_session()
        try:
            staff_list = session.query(Staff).filter(Staff.status == "Active").all()
            self.staff_table.setRowCount(len(staff_list))
            
            self.staff_button_groups = {}
            self.staff_remarks_inputs = {}
            
            for i, st in enumerate(staff_list):
                self.staff_table.setItem(i, 0, QTableWidgetItem(str(st.id)))
                self.staff_table.setItem(i, 1, QTableWidgetItem(f"{st.last_name}, {st.first_name}"))
                self.staff_table.setItem(i, 2, QTableWidgetItem(st.role_title))
                
                # Check for existing log
                att_log = session.query(Attendance).filter(
                    Attendance.staff_id == st.id,
                    Attendance.date == target_date
                ).first()
                
                # Radio buttons
                widget = QWidget()
                w_layout = QHBoxLayout(widget)
                w_layout.setContentsMargins(5, 2, 5, 2)
                
                btn_p = QRadioButton("P")
                btn_a = QRadioButton("A")
                btn_l = QRadioButton("L")
                
                grp = QButtonGroup(self)
                grp.addButton(btn_p, 1)
                grp.addButton(btn_a, 2)
                grp.addButton(btn_l, 3)
                self.staff_button_groups[st.id] = grp
                
                w_layout.addWidget(btn_p)
                w_layout.addWidget(btn_a)
                w_layout.addWidget(btn_l)
                
                self.staff_table.setCellWidget(i, 3, widget)
                
                # Remarks edit
                remarks_edit = QLineEdit()
                remarks_edit.setPlaceholderText("Absent reason etc.")
                if att_log:
                    remarks_edit.setText(att_log.remarks or "")
                self.staff_remarks_inputs[st.id] = remarks_edit
                self.staff_table.setCellWidget(i, 4, remarks_edit)
                
                # Toggle status
                if att_log:
                    if att_log.status == "Present":
                        btn_p.setChecked(True)
                    elif att_log.status == "Absent":
                        btn_a.setChecked(True)
                    elif att_log.status == "Late":
                        btn_l.setChecked(True)
                else:
                    btn_p.setChecked(True)
        except Exception as e:
            print(f"Error loading staff attendance: {e}")
        finally:
            session.close()

    def save_staff_attendance(self):
        staff_date = self.staff_date_edit.date()
        target_date = datetime.date(staff_date.year(), staff_date.month(), staff_date.day())
        
        session = get_session()
        try:
            # Active term ids from config
            ay_id = config.get("active_academic_year_id", 1)
            term_id = config.get("active_term_id", 1)
            
            for st_id, grp in self.staff_button_groups.items():
                checked_id = grp.checkedId()
                status_str = "Present"
                if checked_id == 2:
                    status_str = "Absent"
                elif checked_id == 3:
                    status_str = "Late"
                    
                remarks_str = self.staff_remarks_inputs[st_id].text().strip() or None
                
                # Query existing attendance record
                att = session.query(Attendance).filter(
                    Attendance.staff_id == st_id,
                    Attendance.date == target_date
                ).first()
                
                if att:
                    att.status = status_str
                    att.remarks = remarks_str
                else:
                    att = Attendance(
                        date=target_date,
                        staff_id=st_id,
                        status=status_str,
                        remarks=remarks_str,
                        academic_year_id=ay_id,
                        term_id=term_id
                    )
                    session.add(att)
                    
            session.commit()
            QMessageBox.information(self, "Success", "Staff attendance saved successfully.")
            self.load_staff_roll()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save staff attendance:\n{e}")
        finally:
            session.close()
            
    def refresh(self):
        self.load_classes_combo()
        self.load_student_roll()
        if hasattr(self, 'staff_table'):
            self.load_staff_roll()
