from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QDateEdit, QTextEdit, QTabWidget, QCheckBox
)
from PySide6.QtCore import Qt, QDate, Signal
from database.connection import get_session
from database.models import Student, Parent, Class
from utils.pdf_generator import generate_student_id_card, generate_admission_form
import datetime

class StudentsPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        
        # 1. Directory Tab
        self.dir_tab = QWidget()
        self.init_dir_tab()
        self.tabs.addTab(self.dir_tab, "Student Directory")
        
        # 2. Bulk Promotions Tab
        self.promo_tab = QWidget()
        self.init_promo_tab()
        self.tabs.addTab(self.promo_tab, "Bulk Promotions & Alumni")
        
        main_layout.addWidget(self.tabs)
        
        self.load_filters()
        self.load_students()
        
    def init_dir_tab(self):
        layout = QVBoxLayout(self.dir_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Search & Actions Top Bar
        top_bar = QFrame()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search students by name or ID...")
        self.search_input.textChanged.connect(self.load_students)
        top_bar_layout.addWidget(self.search_input, stretch=3)
        
        self.class_filter = QComboBox()
        self.class_filter.addItem("All Classes")
        self.class_filter.currentIndexChanged.connect(self.load_students)
        top_bar_layout.addWidget(self.class_filter, stretch=1)
        
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Active", "Promoted", "Transferred", "Withdrawn", "Alumnus"])
        self.status_filter.currentIndexChanged.connect(self.load_students)
        top_bar_layout.addWidget(self.status_filter, stretch=1)
        
        add_student_btn = QPushButton("Admit Student")
        add_student_btn.setObjectName("primary_btn")
        add_student_btn.clicked.connect(self.open_admit_dialog)
        top_bar_layout.addWidget(add_student_btn)
        
        layout.addWidget(top_bar)
        
        # Table list of students
        self.table = QTableWidget()
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Class", "Parent Phone", "Status", "Actions"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(5, 120)
        self.table.cellDoubleClicked.connect(self.view_student_details)
        
        layout.addWidget(self.table)
        
    def init_promo_tab(self):
        layout = QVBoxLayout(self.promo_tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Promotions Top Bar
        top_bar = QFrame()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        top_bar_layout.addWidget(QLabel("Promote From Class:"))
        self.promo_class_filter = QComboBox()
        self.promo_class_filter.currentIndexChanged.connect(self.load_promo_students)
        top_bar_layout.addWidget(self.promo_class_filter, stretch=2)
        
        self.select_all_cb = QCheckBox("Select All")
        self.select_all_cb.stateChanged.connect(self.toggle_select_all_promo)
        top_bar_layout.addWidget(self.select_all_cb)
        
        top_bar_layout.addStretch()
        layout.addWidget(top_bar)
        
        # Promotions Table
        self.promo_table = QTableWidget()
        self.promo_table.setColumnCount(5)
        self.promo_table.setHorizontalHeaderLabels(["Select", "Student ID", "Student Name", "Current Class", "Next Class Target"])
        self.promo_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.promo_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.promo_table)
        
        # Promotion Actions Bar
        actions_bar = QHBoxLayout()
        
        promote_btn = QPushButton("Execute Bulk Promotion")
        promote_btn.setObjectName("primary_btn")
        promote_btn.clicked.connect(self.bulk_promote)
        actions_bar.addWidget(promote_btn)
        
        withdraw_btn = QPushButton("Mark Withdrawn")
        withdraw_btn.setObjectName("secondary_btn")
        withdraw_btn.clicked.connect(lambda: self.bulk_status_change("Withdrawn"))
        actions_bar.addWidget(withdraw_btn)
        
        transfer_btn = QPushButton("Mark Transferred")
        transfer_btn.setObjectName("secondary_btn")
        transfer_btn.clicked.connect(lambda: self.bulk_status_change("Transferred"))
        actions_bar.addWidget(transfer_btn)
        
        actions_bar.addStretch()
        layout.addLayout(actions_bar)
        
    def load_filters(self):
        session = get_session()
        try:
            classes = session.query(Class).all()
            for c in classes:
                self.class_filter.addItem(c.name, c.id)
                self.promo_class_filter.addItem(c.name, c.id)
        except Exception as e:
            print(f"Error loading filters: {e}")
        finally:
            session.close()

    def load_students(self):
        self.table.setRowCount(0)
        session = get_session()
        try:
            query = session.query(Student)
            
            search_text = self.search_input.text().strip()
            if search_text:
                query = query.filter(
                    (Student.first_name.ilike(f"%{search_text}%")) | 
                    (Student.last_name.ilike(f"%{search_text}%")) |
                    (Student.id.ilike(f"%{search_text}%"))
                )
                
            if self.class_filter.currentIndex() > 0:
                class_id = self.class_filter.currentData()
                query = query.filter(Student.class_id == class_id)
                
            status_val = self.status_filter.currentText()
            query = query.filter(Student.status == status_val)
            
            students = query.order_by(Student.last_name.asc()).all()
            self.table.setRowCount(len(students))
            
            for row_idx, student in enumerate(students):
                self.table.setItem(row_idx, 0, QTableWidgetItem(student.id))
                
                full_name = f"{student.last_name}, {student.first_name} {student.other_names or ''}"
                self.table.setItem(row_idx, 1, QTableWidgetItem(full_name))
                
                class_name = student.class_assigned.name if student.class_assigned else "Unassigned"
                self.table.setItem(row_idx, 2, QTableWidgetItem(class_name))
                
                parent_phone = student.parent.phone if student.parent else "N/A"
                self.table.setItem(row_idx, 3, QTableWidgetItem(parent_phone))
                
                self.table.setItem(row_idx, 4, QTableWidgetItem(student.status))
                
                action_widget = QWidget()
                action_layout = QHBoxLayout(action_widget)
                action_layout.setContentsMargins(2, 2, 2, 2)
                action_layout.setSpacing(5)
                
                view_btn = QPushButton("View")
                view_btn.setObjectName("secondary_btn")
                view_btn.clicked.connect(lambda checked=False, s_id=student.id: self.view_student_id(s_id))
                
                id_btn = QPushButton("ID")
                id_btn.setObjectName("secondary_btn")
                id_btn.clicked.connect(lambda checked=False, s_id=student.id: self.print_student_id(s_id))
                
                action_layout.addWidget(view_btn)
                action_layout.addWidget(id_btn)
                
                self.table.setCellWidget(row_idx, 5, action_widget)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load students:\n{str(e)}")
        finally:
            session.close()

    def get_next_class_level(self, current_name: str) -> str | None:
        mapping = {
            "Kindergarten 1": "Kindergarten 2",
            "Kindergarten 2": "Primary 1",
            "Primary 1": "Primary 2",
            "Primary 2": "Primary 3",
            "Primary 3": "Primary 4",
            "Primary 4": "Primary 5",
            "Primary 5": "Primary 6",
            "Primary 6": "JHS 1",
            "JHS 1": "JHS 2",
            "JHS 2": "JHS 3",
            "JHS 3": None  # Graduating level
        }
        for key, val in mapping.items():
            if current_name.startswith(key):
                return val
        return None

    def load_promo_students(self):
        self.promo_table.setRowCount(0)
        class_id = self.promo_class_filter.currentData()
        if not class_id:
            return
            
        session = get_session()
        try:
            students = session.query(Student).filter(
                Student.class_id == class_id,
                Student.status == "Active"
            ).order_by(Student.last_name.asc()).all()
            
            self.promo_table.setRowCount(len(students))
            self.promo_checkboxes = {} # row_idx -> QCheckBox
            
            for idx, student in enumerate(students):
                cb = QCheckBox()
                cb.setStyleSheet("margin-left: 10px;")
                self.promo_table.setCellWidget(idx, 0, cb)
                self.promo_checkboxes[idx] = cb
                
                self.promo_table.setItem(idx, 1, QTableWidgetItem(student.id))
                self.promo_table.setItem(idx, 2, QTableWidgetItem(f"{student.last_name}, {student.first_name}"))
                self.promo_table.setItem(idx, 3, QTableWidgetItem(student.class_assigned.name))
                
                next_class = self.get_next_class_level(student.class_assigned.name)
                next_str = f"{next_class} (Promoted)" if next_class else "Alumnus (Graduate)"
                self.promo_table.setItem(idx, 4, QTableWidgetItem(next_str))
        except Exception as e:
            print(f"Error loading promotions: {e}")
        finally:
            session.close()
            
    def toggle_select_all_promo(self, state):
        checked = state == Qt.CheckState.Checked.value
        for cb in self.promo_checkboxes.values():
            cb.setChecked(checked)
            
    def bulk_promote(self):
        selected_rows = [r for r, cb in self.promo_checkboxes.items() if cb.isChecked()]
        if not selected_rows:
            QMessageBox.warning(self, "No Selections", "Please check the students you wish to promote.")
            return
            
        confirm = QMessageBox.question(
            self, "Confirm Promotion", f"Are you sure you want to promote the {len(selected_rows)} selected students?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.No:
            return
            
        session = get_session()
        try:
            promoted_count = 0
            alumni_count = 0
            
            for row in selected_rows:
                s_id = self.promo_table.item(row, 1).text()
                student = session.query(Student).filter(Student.id == s_id).first()
                if student and student.class_assigned:
                    current_class = student.class_assigned
                    next_level = self.get_next_class_level(current_class.name)
                    
                    if next_level is None:
                        # Graduating student
                        student.status = "Alumnus"
                        student.class_id = None
                        alumni_count += 1
                    else:
                        # Promote matching same stream
                        target_class = session.query(Class).filter(
                            Class.name == next_level,
                            Class.stream == current_class.stream
                        ).first()
                        
                        if not target_class:
                            QMessageBox.critical(
                                self, "Class Stream Missing",
                                f"Unable to promote {student.first_name} {student.last_name}.\n"
                                f"The target class stream '{next_level} (Stream {current_class.stream or 'None'})' does not exist.\n"
                                f"Please build this class stream in the Academics tab first."
                            )
                            session.rollback()
                            return
                            
                        student.class_id = target_class.id
                        student.status = "Active"
                        promoted_count += 1
                        
            session.commit()
            QMessageBox.information(
                self, "Promotion Complete",
                f"Bulk promotion execute success.\n"
                f"- Promoted to next class: {promoted_count} students.\n"
                f"- Marked as Alumni: {alumni_count} graduates."
            )
            self.load_students()
            self.load_promo_students()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to promote students: {e}")
        finally:
            session.close()
            
    def bulk_status_change(self, status):
        selected_rows = [r for r, cb in self.promo_checkboxes.items() if cb.isChecked()]
        if not selected_rows:
            QMessageBox.warning(self, "No Selections", "Please select students first.")
            return
            
        confirm = QMessageBox.question(
            self, "Confirm Action", f"Are you sure you want to mark the {len(selected_rows)} selected students as {status}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.No:
            return
            
        session = get_session()
        try:
            for row in selected_rows:
                s_id = self.promo_table.item(row, 1).text()
                student = session.query(Student).filter(Student.id == s_id).first()
                if student:
                    student.status = status
                    student.class_id = None # Clear class assignment
            session.commit()
            QMessageBox.information(self, "Status Saved", f"Students status updated to {status}.")
            self.load_students()
            self.load_promo_students()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to update status: {e}")
        finally:
            session.close()

    def view_student_details(self, row, col):
        student_id = self.table.item(row, 0).text()
        self.view_student_id(student_id)
        
    def view_student_id(self, student_id):
        dialog = StudentProfileDialog(student_id, self)
        dialog.data_changed.connect(self.load_students)
        dialog.exec()
        
    def print_student_id(self, student_id):
        success, filepath = generate_student_id_card(student_id)
        if success:
            QMessageBox.information(self, "Success", f"ID Card PDF generated at:\n{filepath}")
        else:
            QMessageBox.warning(self, "Failed", f"Failed to generate ID card:\n{filepath}")

    def open_admit_dialog(self):
        dialog = AdmitStudentDialog(self)
        dialog.data_changed.connect(self.load_students)
        dialog.exec()

class StudentProfileDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, student_id, parent_widget=None):
        super().__init__(parent_widget)
        self.student_id = student_id
        self.setWindowTitle(f"Student Profile - {student_id}")
        self.setMinimumWidth(500)
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.fname_input = QLineEdit()
        self.lname_input = QLineEdit()
        self.onames_input = QLineEdit()
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        
        self.gender_input = QComboBox()
        self.gender_input.addItems(["Male", "Female"])
        
        self.class_input = QComboBox()
        self.parent_input = QComboBox()
        
        self.status_input = QComboBox()
        self.status_input.addItems(["Active", "Promoted", "Transferred", "Withdrawn", "Alumnus"])
        
        self.med_input = QTextEdit()
        self.med_input.setMaximumHeight(80)
        
        self.e_name_input = QLineEdit()
        self.e_phone_input = QLineEdit()
        
        form_layout.addRow("First Name:", self.fname_input)
        form_layout.addRow("Last Name:", self.lname_input)
        form_layout.addRow("Other Names:", self.onames_input)
        form_layout.addRow("Date of Birth:", self.dob_input)
        form_layout.addRow("Gender:", self.gender_input)
        form_layout.addRow("Class Stream:", self.class_input)
        form_layout.addRow("Parent / Guardian:", self.parent_input)
        form_layout.addRow("Status:", self.status_input)
        form_layout.addRow("Medical Details:", self.med_input)
        form_layout.addRow("Emergency Contact:", self.e_name_input)
        form_layout.addRow("Emergency Phone:", self.e_phone_input)
        
        layout.addLayout(form_layout)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        admission_pdf_btn = QPushButton("Admission Slip")
        admission_pdf_btn.setObjectName("secondary_btn")
        admission_pdf_btn.clicked.connect(self.generate_admission_pdf)
        btn_layout.addWidget(admission_pdf_btn)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_data)
        btn_box.rejected.connect(self.reject)
        
        btn_layout.addWidget(btn_box)
        layout.addLayout(btn_layout)
        
    def load_data(self):
        session = get_session()
        try:
            # Classes
            classes = session.query(Class).all()
            for c in classes:
                self.class_input.addItem(c.name, c.id)
                
            # Parents
            parents = session.query(Parent).all()
            for p in parents:
                self.parent_input.addItem(f"{p.last_name}, {p.first_name} ({p.phone})", p.id)
                
            # Student
            student = session.query(Student).filter(Student.id == self.student_id).first()
            if student:
                self.fname_input.setText(student.first_name)
                self.lname_input.setText(student.last_name)
                self.onames_input.setText(student.other_names or "")
                self.dob_input.setDate(QDate(student.date_of_birth.year, student.date_of_birth.month, student.date_of_birth.day))
                self.gender_input.setCurrentText(student.gender)
                self.status_input.setCurrentText(student.status)
                self.med_input.setPlainText(student.medical_info or "")
                self.e_name_input.setText(student.emergency_contact_name or "")
                self.e_phone_input.setText(student.emergency_contact_phone or "")
                
                if student.class_id:
                    idx = self.class_input.findData(student.class_id)
                    self.class_input.setCurrentIndex(idx)
                    
                if student.parent_id:
                    idx = self.parent_input.findData(student.parent_id)
                    self.parent_input.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load profile details:\n{e}")
        finally:
            session.close()

    def save_data(self):
        fname = self.fname_input.text().strip()
        lname = self.lname_input.text().strip()
        
        if not fname or not lname:
            QMessageBox.warning(self, "Validation Error", "First and Last Name are required.")
            return
            
        session = get_session()
        try:
            student = session.query(Student).filter(Student.id == self.student_id).first()
            if student:
                student.first_name = fname
                student.last_name = lname
                student.other_names = self.onames_input.text().strip() or None
                
                dob_qdate = self.dob_input.date()
                student.date_of_birth = datetime.date(dob_qdate.year(), dob_qdate.month(), dob_qdate.day())
                
                student.gender = self.gender_input.currentText()
                student.status = self.status_input.currentText()
                student.class_id = self.class_input.currentData()
                student.parent_id = self.parent_input.currentData()
                
                student.medical_info = self.med_input.toPlainText().strip() or None
                student.emergency_contact_name = self.e_name_input.text().strip() or None
                student.emergency_contact_phone = self.e_phone_input.text().strip() or None
                
                session.commit()
                QMessageBox.information(self, "Success", "Student profile updated successfully.")
                self.data_changed.emit()
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save student profile:\n{e}")
        finally:
            session.close()
            
    def generate_admission_pdf(self):
        success, filepath = generate_admission_form(self.student_id)
        if success:
            QMessageBox.information(self, "Success", f"Admission Slip PDF generated at:\n{filepath}")
        else:
            QMessageBox.warning(self, "Failed", f"Failed to generate admission slip:\n{filepath}")

class AdmitStudentDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Admit New Student")
        self.setMinimumWidth(450)
        self.init_ui()
        self.load_combos()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.fname_input = QLineEdit()
        self.lname_input = QLineEdit()
        self.onames_input = QLineEdit()
        self.dob_input = QDateEdit()
        self.dob_input.setCalendarPopup(True)
        self.dob_input.setDate(QDate.currentDate().addYears(-6)) # Default KG age
        
        self.gender_input = QComboBox()
        self.gender_input.addItems(["Male", "Female"])
        
        self.class_input = QComboBox()
        self.parent_input = QComboBox()
        
        form_layout.addRow("First Name:", self.fname_input)
        form_layout.addRow("Last Name:", self.lname_input)
        form_layout.addRow("Other Names:", self.onames_input)
        form_layout.addRow("Date of Birth:", self.dob_input)
        form_layout.addRow("Gender:", self.gender_input)
        form_layout.addRow("Class Stream:", self.class_input)
        form_layout.addRow("Parent / Guardian:", self.parent_input)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_data)
        btn_box.rejected.connect(self.reject)
        
        layout.addWidget(btn_box)
        
    def load_combos(self):
        session = get_session()
        try:
            # Classes
            classes = session.query(Class).all()
            for c in classes:
                self.class_input.addItem(c.name, c.id)
                
            # Parents
            parents = session.query(Parent).all()
            for p in parents:
                self.parent_input.addItem(f"{p.last_name}, {p.first_name} ({p.phone})", p.id)
        except Exception as e:
            print(f"Error loading combos: {e}")
        finally:
            session.close()
            
    def save_data(self):
        fname = self.fname_input.text().strip()
        lname = self.lname_input.text().strip()
        
        if not fname or not lname:
            QMessageBox.warning(self, "Validation Error", "First and Last Name are required.")
            return
            
        session = get_session()
        try:
            # Autogenerate Unique student ID: SMS-{YEAR}-{NEXT_INDEX:04d}
            year = datetime.datetime.now().year
            count = session.query(Student).count()
            student_id = f"SMS-{year}-{(count + 1):04d}"
            
            dob_qdate = self.dob_input.date()
            dob_date = datetime.date(dob_qdate.year(), dob_qdate.month(), dob_qdate.day())
            
            new_student = Student(
                id=student_id,
                first_name=fname,
                last_name=lname,
                other_names=self.onames_input.text().strip() or None,
                date_of_birth=dob_date,
                gender=self.gender_input.currentText(),
                class_id=self.class_input.currentData(),
                parent_id=self.parent_input.currentData(),
                admission_date=datetime.date.today(),
                status="Active"
            )
            
            session.add(new_student)
            session.commit()
            
            QMessageBox.information(self, "Success", f"Student admitted successfully.\nAssigned ID: {student_id}")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to admit student:\n{e}")
        finally:
            session.close()
