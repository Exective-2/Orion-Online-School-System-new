from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QDateEdit, QTextEdit, QTabWidget, QCheckBox, QFileDialog
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
        
        bulk_upload_btn = QPushButton("Bulk Upload")
        bulk_upload_btn.setObjectName("secondary_btn")
        bulk_upload_btn.clicked.connect(self.bulk_upload_students)
        top_bar_layout.addWidget(bulk_upload_btn)
        
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
        self.table.setSortingEnabled(False)
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
            self.table.setSortingEnabled(True)
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
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Student ID Card", f"id_card_{student_id}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        success, filepath = generate_student_id_card(student_id, file_path)
        if success:
            QMessageBox.information(self, "Success", f"ID Card PDF generated at:\n{filepath}")
        else:
            QMessageBox.warning(self, "Failed", f"Failed to generate ID card:\n{filepath}")

    def open_admit_dialog(self):
        dialog = AdmitStudentDialog(self)
        dialog.data_changed.connect(self.load_students)
        dialog.exec()

    def bulk_upload_students(self):
        dialog = BulkUploadStudentsDialog(self)
        if dialog.exec() != QDialog.Accepted:
            return
            
        file_path = dialog.selected_file_path
        if not file_path:
            return
            
        import pandas as pd
        try:
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
                
            # Verify columns
            required_cols = {'first_name', 'last_name', 'gender', 'date_of_birth'}
            missing = required_cols - set(df.columns)
            if missing:
                QMessageBox.warning(
                    self, "Invalid File Structure",
                    f"The file is missing the following required columns: {', '.join(missing)}\n\n"
                    "Supported optional columns: other_names, class_name, parent_name, parent_phone, parent_email, emergency_contact_name, emergency_contact_phone"
                )
                return
                
            session = get_session()
            imported_count = 0
            
            # Preload classes and parents
            from database.models import Class, Parent
            classes = {c.name.lower(): c.id for c in session.query(Class).all()}
            parents_by_phone = {p.phone: p.id for p in session.query(Parent).filter(Parent.phone != None).all()}
            
            year = datetime.datetime.now().year
            current_count = session.query(Student).count()
            
            for _, row in df.iterrows():
                fname = str(row['first_name']).strip()
                lname = str(row['last_name']).strip()
                if not fname or not lname or fname == 'nan' or lname == 'nan':
                    continue
                    
                gender = str(row['gender']).strip()
                dob_str = str(row['date_of_birth']).strip()
                try:
                    dob_date = pd.to_datetime(dob_str).date()
                except Exception:
                    dob_date = datetime.date(2010, 1, 1)
                
                # Check class
                class_id = None
                if 'class_name' in row and not pd.isna(row['class_name']):
                    cls_name = str(row['class_name']).strip().lower()
                    if cls_name in classes:
                        class_id = classes[cls_name]
                    else:
                        new_cls = Class(name=str(row['class_name']).strip())
                        session.add(new_cls)
                        session.flush()
                        classes[cls_name] = new_cls.id
                        class_id = new_cls.id
                        
                # Check parent
                parent_id = None
                if 'parent_phone' in row and not pd.isna(row['parent_phone']):
                    p_phone = str(row['parent_phone']).strip()
                    if p_phone in parents_by_phone:
                        parent_id = parents_by_phone[p_phone]
                    else:
                        p_name = str(row.get('parent_name', 'Parent Name')).strip()
                        parts = p_name.split(None, 1)
                        p_fname = parts[0] if parts else "Parent"
                        p_lname = parts[1] if len(parts) > 1 else "Name"
                        new_parent = Parent(
                            first_name=p_fname,
                            last_name=p_lname,
                            phone=p_phone,
                            email=str(row.get('parent_email', '')).strip() or None
                        )
                        session.add(new_parent)
                        session.flush()
                        parents_by_phone[p_phone] = new_parent.id
                        parent_id = new_parent.id
                
                other_names = str(row['other_names']).strip() if ('other_names' in row and not pd.isna(row['other_names'])) else None
                if other_names == 'nan':
                    other_names = None
                    
                student_id = f"SMS-{year}-{(current_count + imported_count + 1):04d}"
                
                new_student = Student(
                    id=student_id,
                    first_name=fname,
                    last_name=lname,
                    other_names=other_names,
                    date_of_birth=dob_date,
                    gender=gender,
                    class_id=class_id,
                    parent_id=parent_id,
                    admission_date=datetime.date.today(),
                    status="Active",
                    emergency_contact_name=str(row.get('emergency_contact_name', '')).strip() or None,
                    emergency_contact_phone=str(row.get('emergency_contact_phone', '')).strip() or None
                )
                session.add(new_student)
                imported_count += 1
                
            session.commit()
            session.close()
            
            QMessageBox.information(
                self, "Import Complete",
                f"Successfully imported {imported_count} student(s) from the file."
            )
            self.load_students()
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import students:\n{e}")

class StudentProfileDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, student_id, parent_widget=None):
        super().__init__(parent_widget)
        self.student_id = student_id
        self.user = parent_widget.user if parent_widget else None
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
        
        is_admin_or_head = False
        if self.user and self.user.role:
            is_admin_or_head = self.user.role.name in ["Super Admin", "Admin/Headteacher"]
            
        if is_admin_or_head:
            delete_btn = QPushButton("Delete Student")
            delete_btn.setObjectName("danger_btn")
            delete_btn.setStyleSheet("background-color: #ef4444; color: white;")
            delete_btn.clicked.connect(self.delete_student)
            btn_layout.addWidget(delete_btn)
            
        admission_pdf_btn = QPushButton("Admission Slip")
        admission_pdf_btn.setObjectName("secondary_btn")
        admission_pdf_btn.clicked.connect(self.generate_admission_pdf)
        btn_layout.addWidget(admission_pdf_btn)
        
        btn_layout.addStretch()
        
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
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Admission Slip", f"admission_slip_{self.student_id}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
        success, filepath = generate_admission_form(self.student_id, file_path)
        if success:
            QMessageBox.information(self, "Success", f"Admission Slip PDF generated at:\n{filepath}")
        else:
            QMessageBox.warning(self, "Failed", f"Failed to generate admission slip:\n{filepath}")
            
    def delete_student(self):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to permanently delete student {self.student_id}?\n"
            "This will delete all their attendance records, exam results, and fee bills. This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.No:
            return
            
        session = get_session()
        try:
            student = session.query(Student).filter(Student.id == self.student_id).first()
            if student:
                session.delete(student)
                session.commit()
                QMessageBox.information(self, "Success", "Student record deleted successfully.")
                self.data_changed.emit()
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Student record not found.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete student: {e}")
        finally:
            session.close()

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


class BulkUploadStudentsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Upload Students")
        self.setMinimumWidth(400)
        self.init_ui()
        self.selected_file_path = None
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        info_label = QLabel(
            "<b>Instructions:</b><br/>"
            "1. Download the template below to see the required format.<br/>"
            "2. Fill in student records. Required fields: <i>first_name, last_name, gender, date_of_birth</i>.<br/>"
            "3. Click 'Upload & Import File' to import the data into the system."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Download button
        download_btn = QPushButton("Download Template (CSV)")
        download_btn.setObjectName("secondary_btn")
        download_btn.clicked.connect(self.download_template)
        layout.addWidget(download_btn)
        
        # Import button
        import_btn = QPushButton("Upload & Import File")
        import_btn.setObjectName("primary_btn")
        import_btn.clicked.connect(self.import_file)
        layout.addWidget(import_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
    def download_template(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Student Template", "student_upload_template.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            import csv
            headers = [
                'first_name', 'last_name', 'other_names', 'gender', 'date_of_birth',
                'class_name', 'parent_name', 'parent_phone', 'parent_email',
                'emergency_contact_name', 'emergency_contact_phone'
            ]
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerow([
                    'John', 'Doe', 'Kofi', 'Male', '2015-06-15',
                    'Class 1A', 'Robert Doe', '+233240000000', 'robert.doe@example.com',
                    'Mary Doe', '+233241111111'
                ])
            QMessageBox.information(self, "Success", f"Student upload template saved successfully at:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template:\n{e}")
            
    def import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Student Import File", "", "Data Files (*.csv *.xlsx *.xls)"
        )
        if not file_path:
            return
            
        self.selected_file_path = file_path
        self.accept()
