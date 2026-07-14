from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QDateEdit, QTabWidget, QCheckBox, QFileDialog, QInputDialog,
    QDoubleSpinBox
)
from PySide6.QtCore import Qt, QDate, Signal
from database.connection import get_session
from database.models import Staff, User, Role
from database.seed import hash_password
import datetime

class StaffPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.handle_tab_change)
        
        # --- TAB 1: Staff Directory ---
        self.directory_tab = QWidget()
        layout = QVBoxLayout(self.directory_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Search & Actions top bar
        top_bar = QFrame()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search staff members by name...")
        self.search_input.textChanged.connect(self.load_staff)
        top_bar_layout.addWidget(self.search_input, stretch=3)
        
        self.role_filter = QComboBox()
        self.role_filter.addItems(["All Roles", "Teacher", "Accountant", "Librarian", "Storekeeper", "Admin Officer", "Headteacher"])
        self.role_filter.currentIndexChanged.connect(self.load_staff)
        top_bar_layout.addWidget(self.role_filter, stretch=1)
        
        add_staff_btn = QPushButton("Register Staff")
        add_staff_btn.setObjectName("primary_btn")
        add_staff_btn.clicked.connect(self.open_register_dialog)
        top_bar_layout.addWidget(add_staff_btn)
        
        bulk_upload_btn = QPushButton("Bulk Upload")
        bulk_upload_btn.setObjectName("secondary_btn")
        bulk_upload_btn.clicked.connect(self.bulk_upload_staff)
        top_bar_layout.addWidget(bulk_upload_btn)
        
        layout.addWidget(top_bar)
        
        # Table listing staff members
        self.table = QTableWidget()
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Role Title", "Department", "Phone", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self.view_staff_details)
        
        layout.addWidget(self.table)
        self.tabs.addTab(self.directory_tab, "Staff Directory")
        
        # --- TAB 2: Payroll Management ---
        self.payroll_tab = QWidget()
        self.init_payroll_ui()
        self.tabs.addTab(self.payroll_tab, "Payroll Management")
        
        main_layout.addWidget(self.tabs)
        
        self.load_staff()
        
    def load_staff(self):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        session = get_session()
        try:
            query = session.query(Staff)
            
            search_text = self.search_input.text().strip()
            if search_text:
                query = query.filter(
                    (Staff.first_name.ilike(f"%{search_text}%")) | 
                    (Staff.last_name.ilike(f"%{search_text}%"))
                )
                
            if self.role_filter.currentIndex() > 0:
                role_val = self.role_filter.currentText()
                query = query.filter(Staff.role_title == role_val)
                
            staff_list = query.order_by(Staff.last_name.asc()).all()
            self.table.setRowCount(len(staff_list))
            
            for row_idx, staff in enumerate(staff_list):
                self.table.setItem(row_idx, 0, QTableWidgetItem(str(staff.id)))
                
                full_name = f"{staff.last_name}, {staff.first_name} {staff.other_names or ''}"
                self.table.setItem(row_idx, 1, QTableWidgetItem(full_name))
                
                self.table.setItem(row_idx, 2, QTableWidgetItem(staff.role_title))
                self.table.setItem(row_idx, 3, QTableWidgetItem(staff.department or "Unassigned"))
                self.table.setItem(row_idx, 4, QTableWidgetItem(staff.phone))
                self.table.setItem(row_idx, 5, QTableWidgetItem(staff.status))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load staff:\n{str(e)}")
        finally:
            self.table.setSortingEnabled(True)
            session.close()

    def view_staff_details(self, row, col):
        staff_id = int(self.table.item(row, 0).text())
        dialog = StaffDetailsDialog(staff_id, self)
        dialog.data_changed.connect(self.load_staff)
        dialog.exec()
        
    def open_register_dialog(self):
        dialog = RegisterStaffDialog(self)
        dialog.data_changed.connect(self.load_staff)
        dialog.exec()

    def handle_tab_change(self, index):
        if index == 1:
            self.load_payroll_periods()

    def init_payroll_ui(self):
        p_layout = QVBoxLayout(self.payroll_tab)
        p_layout.setContentsMargins(15, 15, 15, 15)
        p_layout.setSpacing(15)
        
        # Payroll top bar: Month filter, process payroll button
        pay_bar = QFrame()
        pay_bar_layout = QHBoxLayout(pay_bar)
        pay_bar_layout.setContentsMargins(0, 0, 0, 0)
        pay_bar_layout.setSpacing(10)
        
        pay_bar_layout.addWidget(QLabel("Pay Period:"))
        self.period_combo = QComboBox()
        self.period_combo.currentIndexChanged.connect(self.load_payslips)
        pay_bar_layout.addWidget(self.period_combo, stretch=2)
        
        process_btn = QPushButton("Generate Period Payroll")
        process_btn.setObjectName("primary_btn")
        process_btn.clicked.connect(self.process_monthly_payroll)
        pay_bar_layout.addWidget(process_btn)
        
        pay_bar_layout.addStretch()
        p_layout.addWidget(pay_bar)
        
        # Payslips Table
        self.payslips_table = QTableWidget()
        self.payslips_table.verticalHeader().setDefaultSectionSize(40)
        self.payslips_table.setColumnCount(9)
        self.payslips_table.setHorizontalHeaderLabels([
            "Staff Name", "Role", "Base Salary", "Allowances", "Tax (PAYE)", "Pension (SSNIT)", "Net Pay", "PDF", "Edit"
        ])
        self.payslips_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.payslips_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.payslips_table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.payslips_table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        p_layout.addWidget(self.payslips_table)

    def load_payroll_periods(self):
        self.period_combo.blockSignals(True)
        self.period_combo.clear()
        
        import calendar
        today = datetime.date.today()
        months = []
        for i in range(12):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            m_name = calendar.month_name[m]
            months.append(f"{m_name} {y}")
            
        self.period_combo.addItems(months)
        self.period_combo.blockSignals(False)
        self.load_payslips()

    def process_monthly_payroll(self):
        period = self.period_combo.currentText()
        if not period:
            return
            
        session = get_session()
        try:
            from database.models import Payslip
            
            # Fetch all active staff
            active_staff = session.query(Staff).filter(Staff.status == "Active").all()
            if not active_staff:
                QMessageBox.warning(self, "Payroll Info", "No active staff members found to process.")
                return
                
            processed_count = 0
            for st in active_staff:
                # Check if payslip already exists for this period
                existing = session.query(Payslip).filter(
                    Payslip.staff_id == st.id,
                    Payslip.pay_period == period
                ).first()
                if existing:
                    continue
                    
                # Calculations
                base = st.base_salary if st.base_salary and st.base_salary > 0 else 1500.0
                
                # Allowances
                role_allowances = {
                    "Headteacher": 500.0,
                    "Admin Officer": 300.0,
                    "Accountant": 300.0,
                    "Teacher": 200.0,
                    "Librarian": 100.0,
                    "Storekeeper": 100.0
                }
                allowance = role_allowances.get(st.role_title, 100.0)
                
                gross = base + allowance
                tax = gross * 0.15      # 15% PAYE
                pension = base * 0.055  # 5.5% SSNIT
                net = gross - tax - pension
                
                payslip = Payslip(
                    staff_id=st.id,
                    pay_period=period,
                    base_salary=base,
                    allowances=allowance,
                    tax_deductions=tax,
                    pension_deductions=pension,
                    net_salary=net,
                    status="Paid", # Auto mark as paid for simplicity
                    payment_date=datetime.date.today()
                )
                session.add(payslip)
                processed_count += 1
                
            session.commit()
            if processed_count > 0:
                QMessageBox.information(self, "Success", f"Successfully generated {processed_count} payslips for {period}.")
            else:
                QMessageBox.information(self, "Payroll Info", f"Payroll for {period} was already processed for all staff.")
            self.load_payslips()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to process payroll:\n{e}")
        finally:
            session.close()

    def load_payslips(self):
        period = self.period_combo.currentText()
        if not period:
            return
            
        self.payslips_table.setRowCount(0)
        session = get_session()
        try:
            from database.models import Payslip
            slips = session.query(Payslip).filter(Payslip.pay_period == period).all()
            
            for i, sl in enumerate(slips):
                self.payslips_table.insertRow(i)
                
                name_item = QTableWidgetItem(f"{sl.staff.first_name} {sl.staff.last_name}")
                name_item.setFlags(name_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                
                role_item = QTableWidgetItem(sl.staff.role_title)
                role_item.setFlags(role_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                
                base_item = QTableWidgetItem(f"{sl.base_salary:.2f}")
                base_item.setFlags(base_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                
                allowance_item = QTableWidgetItem(f"{sl.allowances:.2f}")
                allowance_item.setFlags(allowance_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                
                tax_item = QTableWidgetItem(f"{sl.tax_deductions:.2f}")
                tax_item.setFlags(tax_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                
                pension_item = QTableWidgetItem(f"{sl.pension_deductions:.2f}")
                pension_item.setFlags(pension_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                
                net_item = QTableWidgetItem(f"{sl.net_salary:.2f}")
                net_item.setFlags(net_item.flags() ^ Qt.ItemFlag.ItemIsEditable)
                
                self.payslips_table.setItem(i, 0, name_item)
                self.payslips_table.setItem(i, 1, role_item)
                self.payslips_table.setItem(i, 2, base_item)
                self.payslips_table.setItem(i, 3, allowance_item)
                self.payslips_table.setItem(i, 4, tax_item)
                self.payslips_table.setItem(i, 5, pension_item)
                self.payslips_table.setItem(i, 6, net_item)
                
                # PDF Action Button
                print_btn = QPushButton("PDF")
                print_btn.setObjectName("secondary_btn")
                print_btn.clicked.connect(lambda checked=False, sid=sl.id: self.generate_payslip(sid))
                self.payslips_table.setCellWidget(i, 7, print_btn)
                
                # Edit Payslip Button (restricted to Admin/Bursar roles)
                can_edit = False
                if self.user and self.user.role:
                    can_edit = self.user.role.name in ["Super Admin", "Admin/Headteacher", "Accountant"]
                if can_edit:
                    edit_btn = QPushButton("Edit")
                    edit_btn.setObjectName("primary_btn")
                    edit_btn.clicked.connect(lambda checked=False, sid=sl.id: self.open_edit_payslip(sid))
                    self.payslips_table.setCellWidget(i, 8, edit_btn)
                
        except Exception as e:
            print(f"Error loading payslips: {e}")
        finally:
            session.close()

    def generate_payslip(self, payslip_id):
        session = get_session()
        try:
            from database.models import Payslip
            payslip = session.query(Payslip).filter(Payslip.id == payslip_id).first()
            if payslip:
                from utils.pdf_generator import generate_payslip_pdf
                default_filename = f"payslip_{payslip.staff_id}_{payslip.pay_period.replace(' ', '_')}.pdf"
                file_path, _ = QFileDialog.getSaveFileName(
                    self, "Save Payslip", default_filename, "PDF Files (*.pdf)"
                )
                if not file_path:
                    return
                pdf_path, error = generate_payslip_pdf(payslip, file_path)
                if pdf_path:
                    import os, subprocess
                    if os.path.exists(pdf_path):
                        if os.name == 'posix':
                            subprocess.run(["open", pdf_path])
                        else:
                            os.startfile(pdf_path)
                else:
                    QMessageBox.critical(self, "Error", f"Failed to generate payslip PDF: {error}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error generating payslip: {e}")
        finally:
            session.close()

    def open_edit_payslip(self, payslip_id):
        dialog = EditPayslipDialog(payslip_id, self.user, self)
        dialog.payslip_saved.connect(self.load_payslips)
        dialog.exec()

    def bulk_upload_staff(self):
        dialog = BulkUploadStaffDialog(self)
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
            required_cols = {'first_name', 'last_name', 'phone', 'role_title'}
            missing = required_cols - set(df.columns)
            if missing:
                QMessageBox.warning(
                    self, "Invalid File Structure",
                    f"The file is missing the following required columns: {', '.join(missing)}\n\n"
                    "Supported optional columns: other_names, email, department, qualification, address, base_salary"
                )
                return
                
            session = get_session()
            imported_count = 0
            
            # Roles for mapping
            from database.models import Role, User
            from database.seed import hash_password
            roles = {r.name.lower(): r.id for r in session.query(Role).all()}
            
            role_mapping = {
                "teacher": "teacher",
                "accountant": "accountant",
                "librarian": "librarian",
                "storekeeper": "storekeeper",
                "headteacher": "admin/headteacher",
                "admin officer": "admin/headteacher"
            }
            
            for _, row in df.iterrows():
                fname = str(row['first_name']).strip()
                lname = str(row['last_name']).strip()
                if not fname or not lname or fname == 'nan' or lname == 'nan':
                    continue
                    
                phone = str(row['phone']).strip()
                role_title = str(row['role_title']).strip()
                
                email = str(row.get('email', '')).strip() or None
                if email == 'nan':
                    email = None
                    
                dept = str(row.get('department', '')).strip() or None
                if dept == 'nan':
                    dept = None
                    
                qual = str(row.get('qualification', '')).strip() or None
                if qual == 'nan':
                    qual = None
                    
                addr = str(row.get('address', '')).strip() or None
                if addr == 'nan':
                    addr = None
                    
                salary_val = row.get('base_salary', 0.0)
                try:
                    salary = float(salary_val) if not pd.isna(salary_val) else 0.0
                except Exception:
                    salary = 0.0
                
                # Check if phone already registered to avoid duplicates
                existing_staff = session.query(Staff).filter(Staff.phone == phone).first()
                if existing_staff:
                    continue
                
                # Generate unique username
                base_username = f"{fname.lower()}.{lname.lower()}"
                username = base_username
                idx = 1
                while session.query(User).filter(User.username == username).first():
                    username = f"{base_username}{idx}"
                    idx += 1
                
                # Resolve role id
                mapped_role_name = role_mapping.get(role_title.lower(), "teacher")
                role_id = roles.get(mapped_role_name)
                if not role_id:
                    role_id = list(roles.values())[0] if roles else None
                
                # Create user
                new_user = User(
                    username=username,
                    password_hash=hash_password("Orion@123"), # default password
                    email=email,
                    role_id=role_id,
                    is_active=True
                )
                session.add(new_user)
                session.flush()
                
                new_staff = Staff(
                    user_id=new_user.id,
                    first_name=fname,
                    last_name=lname,
                    other_names=str(row.get('other_names', '')).strip() or None,
                    email=email,
                    phone=phone,
                    role_title=role_title,
                    department=dept,
                    hire_date=datetime.date.today(),
                    status="Active",
                    address=addr,
                    qualification=qual,
                    base_salary=salary
                )
                session.add(new_staff)
                imported_count += 1
                
            session.commit()
            session.close()
            
            QMessageBox.information(
                self, "Import Complete",
                f"Successfully imported {imported_count} staff member(s) from the file.\n"
                "Corresponding user accounts have been created with the default password: Orion@123"
            )
            self.load_staff()
            
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to import staff:\n{e}")

class StaffDetailsDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, staff_id, parent_widget=None):
        super().__init__(parent_widget)
        self.staff_id = staff_id
        self.parent_panel = parent_widget
        self.user = parent_widget.user if parent_widget else None
        self.setWindowTitle(f"Staff Profile Details")
        self.setMinimumWidth(500)
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Tabs for staff profile
        tabs = QTabWidget()
        
        # 1. Info Tab
        info_tab = QWidget()
        form_layout = QFormLayout(info_tab)
        
        self.fname_input = QLineEdit()
        self.lname_input = QLineEdit()
        self.onames_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        self.role_input = QComboBox()
        self.role_input.addItems(["Teacher", "Accountant", "Librarian", "Storekeeper", "Admin Officer", "Headteacher"])
        self.dept_input = QComboBox()
        self.dept_input.addItems(["Academics", "Administration", "Operations"])
        self.status_input = QComboBox()
        self.status_input.addItems(["Active", "Resigned", "Suspended"])
        
        form_layout.addRow("First Name:", self.fname_input)
        form_layout.addRow("Last Name:", self.lname_input)
        form_layout.addRow("Other Names:", self.onames_input)
        form_layout.addRow("Email:", self.email_input)
        form_layout.addRow("Phone Number:", self.phone_input)
        form_layout.addRow("Role Title:", self.role_input)
        form_layout.addRow("Department:", self.dept_input)
        form_layout.addRow("Status:", self.status_input)
        
        tabs.addTab(info_tab, "Personal Info")
        
        # 2. Employment Tab
        emp_tab = QWidget()
        emp_layout = QFormLayout(emp_tab)
        
        self.qualification_input = QLineEdit()
        self.hire_date_input = QDateEdit()
        self.hire_date_input.setCalendarPopup(True)
        self.address_input = QLineEdit()
        self.salary_input = QLineEdit()
        self.salary_input.setPlaceholderText("e.g. 2500.00")
        
        emp_layout.addRow("Qualifications:", self.qualification_input)
        emp_layout.addRow("Hire Date:", self.hire_date_input)
        emp_layout.addRow("Residential Address:", self.address_input)
        emp_layout.addRow("Base Salary (GHS):", self.salary_input)
        
        tabs.addTab(emp_tab, "Employment")
        
        layout.addWidget(tabs)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        is_admin_or_head = False
        if self.user and self.user.role:
            is_admin_or_head = self.user.role.name in ["Super Admin", "Admin/Headteacher"]
            
        if is_admin_or_head:
            delete_btn = QPushButton("Delete Staff")
            delete_btn.setObjectName("danger_btn")
            delete_btn.setStyleSheet("background-color: #ef4444; color: white;")
            delete_btn.clicked.connect(self.delete_staff)
            btn_layout.addWidget(delete_btn)
            
            reset_pwd_btn = QPushButton("Reset Password")
            reset_pwd_btn.setObjectName("secondary_btn")
            reset_pwd_btn.clicked.connect(self.reset_password)
            btn_layout.addWidget(reset_pwd_btn)
            
        btn_layout.addStretch()
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_data)
        btn_box.rejected.connect(self.reject)
        
        btn_layout.addWidget(btn_box)
        layout.addLayout(btn_layout)
        
    def load_data(self):
        session = get_session()
        try:
            staff = session.query(Staff).filter(Staff.id == self.staff_id).first()
            if staff:
                self.fname_input.setText(staff.first_name)
                self.lname_input.setText(staff.last_name)
                self.onames_input.setText(staff.other_names or "")
                self.email_input.setText(staff.email or "")
                self.phone_input.setText(staff.phone)
                self.role_input.setCurrentText(staff.role_title)
                self.dept_input.setCurrentText(staff.department or "Academics")
                self.status_input.setCurrentText(staff.status)
                
                self.qualification_input.setText(staff.qualification or "")
                self.hire_date_input.setDate(QDate(staff.hire_date.year, staff.hire_date.month, staff.hire_date.day))
                self.address_input.setText(staff.address or "")
                self.salary_input.setText(str(staff.base_salary or 0.0))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load staff details:\n{e}")
        finally:
            session.close()

    def save_data(self):
        fname = self.fname_input.text().strip()
        lname = self.lname_input.text().strip()
        phone = self.phone_input.text().strip()
        
        if not fname or not lname or not phone:
            QMessageBox.warning(self, "Validation Error", "First Name, Last Name and Phone Number are required.")
            return
            
        sal_val = 0.0
        try:
            sal_val = float(self.salary_input.text().strip() or 0.0)
            if sal_val < 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid non-negative base salary.")
            return
            
        session = get_session()
        try:
            staff = session.query(Staff).filter(Staff.id == self.staff_id).first()
            if staff:
                staff.first_name = fname
                staff.last_name = lname
                staff.other_names = self.onames_input.text().strip() or None
                staff.email = self.email_input.text().strip() or None
                staff.phone = phone
                staff.role_title = self.role_input.currentText()
                staff.department = self.dept_input.currentText()
                staff.status = self.status_input.currentText()
                
                staff.qualification = self.qualification_input.text().strip() or None
                hd = self.hire_date_input.date()
                staff.hire_date = datetime.date(hd.year(), hd.month(), hd.day())
                staff.address = self.address_input.text().strip() or None
                staff.base_salary = sal_val
                
                session.commit()
                QMessageBox.information(self, "Success", "Staff details updated successfully.")
                self.data_changed.emit()
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save staff info:\n{e}")
        finally:
            session.close()
            
    def delete_staff(self):
        confirm = QMessageBox.question(
            self, "Confirm Delete",
            "Are you sure you want to permanently delete this staff member?\n"
            "This will delete all their attendance records and payslips. Their login account will also be deleted. This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.No:
            return
            
        session = get_session()
        try:
            staff = session.query(Staff).filter(Staff.id == self.staff_id).first()
            if staff:
                # Nullify foreign key references in related tables to prevent constraint violations
                from database.models import Result, Payment, StockTransaction, LibraryIssue, Announcement, Expense
                session.query(Result).filter(Result.teacher_id == self.staff_id).update({Result.teacher_id: None})
                session.query(Payment).filter(Payment.received_by == self.staff_id).update({Payment.received_by: None})
                session.query(StockTransaction).filter(StockTransaction.staff_id == self.staff_id).update({StockTransaction.staff_id: None})
                session.query(LibraryIssue).filter(LibraryIssue.issued_by == self.staff_id).update({LibraryIssue.issued_by: None})
                session.query(Announcement).filter(Announcement.created_by == self.staff_id).update({Announcement.created_by: None})
                session.query(Expense).filter(Expense.recorded_by == self.staff_id).update({Expense.recorded_by: None})
                session.flush()

                # User account to delete
                user_id = staff.user_id
                
                # Delete staff
                session.delete(staff)
                
                # Delete user account if exists
                if user_id:
                    user_obj = session.query(User).filter(User.id == user_id).first()
                    if user_obj:
                        session.delete(user_obj)
                        
                session.commit()
                QMessageBox.information(self, "Success", "Staff record and user account deleted successfully.")
                self.data_changed.emit()
                self.accept()
            else:
                QMessageBox.warning(self, "Error", "Staff record not found.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to delete staff: {e}")
        finally:
            session.close()

    def reset_password(self):
        session = get_session()
        try:
            staff = session.query(Staff).filter(Staff.id == self.staff_id).first()
            if not staff or not staff.user:
                QMessageBox.warning(self, "No Account", "This staff member does not have a login user account.")
                return
                
            username = staff.user.username
            text, ok = QInputDialog.getText(
                self, "Reset Password", f"Enter new password for user '{username}':",
                QLineEdit.EchoMode.Password, ""
            )
            if ok and text:
                if len(text) < 6:
                    QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
                    return
                staff.user.password_hash = hash_password(text)
                session.commit()
                QMessageBox.information(self, "Success", f"Password for '{username}' has been successfully reset.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to reset password: {e}")
        finally:
            session.close()

class RegisterStaffDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Register Staff Member")
        self.setMinimumWidth(450)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.fname_input = QLineEdit()
        self.lname_input = QLineEdit()
        self.onames_input = QLineEdit()
        self.email_input = QLineEdit()
        self.phone_input = QLineEdit()
        
        self.role_input = QComboBox()
        self.role_input.addItems(["Teacher", "Accountant", "Librarian", "Storekeeper", "Admin Officer", "Headteacher"])
        
        self.dept_input = QComboBox()
        self.dept_input.addItems(["Academics", "Administration", "Operations"])
        
        self.qualification_input = QLineEdit()
        self.hire_date_input = QDateEdit()
        self.hire_date_input.setCalendarPopup(True)
        self.hire_date_input.setDate(QDate.currentDate())
        self.salary_input = QLineEdit()
        self.salary_input.setPlaceholderText("e.g. 2500.00")
        
        form_layout.addRow("First Name *:", self.fname_input)
        form_layout.addRow("Last Name *:", self.lname_input)
        form_layout.addRow("Other Names:", self.onames_input)
        form_layout.addRow("Email:", self.email_input)
        form_layout.addRow("Phone Number *:", self.phone_input)
        form_layout.addRow("Role Title:", self.role_input)
        form_layout.addRow("Department:", self.dept_input)
        form_layout.addRow("Qualifications:", self.qualification_input)
        form_layout.addRow("Hire Date:", self.hire_date_input)
        form_layout.addRow("Base Salary (GHS):", self.salary_input)
        
        layout.addLayout(form_layout)
        
        # User credentials creation section
        self.create_user_cb = QCheckBox("Create login user credentials for this staff member")
        self.create_user_cb.toggled.connect(self.toggle_credentials_section)
        layout.addWidget(self.create_user_cb)
        
        self.credentials_widget = QFrame()
        self.credentials_widget.setObjectName("card")
        self.credentials_widget.setStyleSheet("padding: 10px;")
        cred_layout = QFormLayout(self.credentials_widget)
        cred_layout.setSpacing(8)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("e.g. jdoe")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Minimum 6 characters")
        self.confirm_pwd_input = QLineEdit()
        self.confirm_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pwd_input.setPlaceholderText("Confirm password")
        
        cred_layout.addRow("Username *:", self.username_input)
        cred_layout.addRow("Password *:", self.password_input)
        cred_layout.addRow("Confirm Password *:", self.confirm_pwd_input)
        
        layout.addWidget(self.credentials_widget)
        self.credentials_widget.hide() # Hidden by default
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_data)
        btn_box.rejected.connect(self.reject)
        
        layout.addWidget(btn_box)

    def toggle_credentials_section(self, checked):
        self.credentials_widget.setVisible(checked)
        if checked:
            self.adjustSize()
            
    def save_data(self):
        fname = self.fname_input.text().strip()
        lname = self.lname_input.text().strip()
        phone = self.phone_input.text().strip()
        email = self.email_input.text().strip() or None
        
        if not fname or not lname or not phone:
            QMessageBox.warning(self, "Validation Error", "First Name, Last Name and Phone Number are required.")
            return
            
        sal_val = 0.0
        try:
            sal_val = float(self.salary_input.text().strip() or 0.0)
            if sal_val < 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid non-negative base salary.")
            return
            
        create_user = self.create_user_cb.isChecked()
        username = ""
        password = ""
        
        if create_user:
            username = self.username_input.text().strip()
            password = self.password_input.text()
            confirm = self.confirm_pwd_input.text()
            
            if not username:
                QMessageBox.warning(self, "Validation Error", "Username is required when creating credentials.")
                return
            if len(password) < 6:
                QMessageBox.warning(self, "Validation Error", "Password must be at least 6 characters.")
                return
            if password != confirm:
                QMessageBox.warning(self, "Validation Error", "Passwords do not match confirmation.")
                return
                
        session = get_session()
        try:
            # Check duplicate username
            if create_user:
                existing_user = session.query(User).filter(User.username == username).first()
                if existing_user:
                    QMessageBox.warning(self, "Validation Error", f"Username '{username}' is already taken.")
                    return
                # Check duplicate user email if email is provided
                if email:
                    existing_email = session.query(User).filter(User.email == email).first()
                    if existing_email:
                        QMessageBox.warning(self, "Validation Error", f"Email '{email}' is already linked to another login account.")
                        return
            
            hd = self.hire_date_input.date()
            new_staff = Staff(
                first_name=fname,
                last_name=lname,
                other_names=self.onames_input.text().strip() or None,
                email=email,
                phone=phone,
                role_title=self.role_input.currentText(),
                department=self.dept_input.currentText(),
                qualification=self.qualification_input.text().strip() or None,
                hire_date=datetime.date(hd.year(), hd.month(), hd.day()),
                base_salary=sal_val,
                status="Active"
            )
            session.add(new_staff)
            session.flush() # Populate new_staff.id
            
            if create_user:
                # Resolve role
                role_mapping = {
                    "Teacher": "Teacher",
                    "Accountant": "Accountant",
                    "Librarian": "Librarian",
                    "Storekeeper": "Storekeeper",
                    "Headteacher": "Admin/Headteacher",
                    "Admin Officer": "Admin/Headteacher"
                }
                db_role_name = role_mapping.get(self.role_input.currentText(), "Teacher")
                role_obj = session.query(Role).filter(Role.name == db_role_name).first()
                
                # If target role doesn't exist, fallback to first role
                if not role_obj:
                    role_obj = session.query(Role).first()
                    
                new_user = User(
                    username=username,
                    password_hash=hash_password(password),
                    email=email,
                    role_id=role_obj.id if role_obj else None,
                    is_active=True
                )
                session.add(new_user)
                session.flush() # Populate new_user.id
                
                # Link staff to user
                new_staff.user_id = new_user.id
                
            session.commit()
            
            QMessageBox.information(self, "Success", "Staff member registered successfully.")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to register staff:\n{e}")
        finally:
            session.close()


class BulkUploadStaffDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bulk Upload Staff")
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
            "2. Fill in staff records. Required fields: <i>first_name, last_name, phone, role_title</i>.<br/>"
            "   (Supported roles: teacher, accountant, librarian, storekeeper, headteacher)<br/>"
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
            self, "Save Staff Template", "staff_upload_template.csv", "CSV Files (*.csv)"
        )
        if not file_path:
            return
        try:
            import csv
            headers = [
                'first_name', 'last_name', 'other_names', 'phone', 'email',
                'role_title', 'department', 'qualification', 'address', 'base_salary'
            ]
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerow([
                    'Jane', 'Smith', 'Naa', '+233242222222', 'jane.smith@example.com',
                    'Teacher', 'Science', 'B.Ed Science', 'Cantonments, Accra', '3500.0'
                ])
            QMessageBox.information(self, "Success", f"Staff upload template saved successfully at:\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save template:\n{e}")
            
    def import_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Staff Import File", "", "Data Files (*.csv *.xlsx *.xls)"
        )
        if not file_path:
            return
            
        self.selected_file_path = file_path
        self.accept()

class EditPayslipDialog(QDialog):
    payslip_saved = Signal()
    
    def __init__(self, payslip_id, user, parent_widget=None):
        super().__init__(parent_widget)
        self.payslip_id = payslip_id
        self.user = user
        self.setWindowTitle("Edit Payslip")
        self.setMinimumWidth(420)
        self._loading = True
        self.init_ui()
        self.load_payslip_data()
        self._loading = False
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        
        info_lbl = QLabel("Edit the payroll components below. Net Pay updates automatically.")
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(info_lbl)
        
        form_frame = QFrame()
        form_frame.setObjectName("card")
        form_layout = QFormLayout(form_frame)
        form_layout.setSpacing(12)
        
        # Basic Salary
        self.basic_spin = QDoubleSpinBox()
        self.basic_spin.setRange(0.0, 999999.99)
        self.basic_spin.setDecimals(2)
        self.basic_spin.setPrefix("GHS ")
        self.basic_spin.setSingleStep(50.0)
        form_layout.addRow("Basic Salary:", self.basic_spin)
        
        # Allowances
        self.allow_spin = QDoubleSpinBox()
        self.allow_spin.setRange(0.0, 999999.99)
        self.allow_spin.setDecimals(2)
        self.allow_spin.setPrefix("GHS ")
        self.allow_spin.setSingleStep(50.0)
        form_layout.addRow("Allowances:", self.allow_spin)
        
        # Tax (PAYE)
        self.tax_spin = QDoubleSpinBox()
        self.tax_spin.setRange(0.0, 999999.99)
        self.tax_spin.setDecimals(2)
        self.tax_spin.setPrefix("GHS ")
        self.tax_spin.setSingleStep(10.0)
        form_layout.addRow("Tax — PAYE:", self.tax_spin)
        
        # Recalc tax hint button
        recalc_tax_btn = QPushButton("↺ Auto-calc Tax (15%)")
        recalc_tax_btn.setObjectName("secondary_btn")
        recalc_tax_btn.setFixedHeight(28)
        recalc_tax_btn.clicked.connect(self._recalc_tax)
        form_layout.addRow("", recalc_tax_btn)
        
        # SSNIT Pension
        self.ssnit_spin = QDoubleSpinBox()
        self.ssnit_spin.setRange(0.0, 999999.99)
        self.ssnit_spin.setDecimals(2)
        self.ssnit_spin.setPrefix("GHS ")
        self.ssnit_spin.setSingleStep(10.0)
        form_layout.addRow("Pension — SSNIT:", self.ssnit_spin)
        
        # Recalc SSNIT hint button
        recalc_ssnit_btn = QPushButton("↺ Auto-calc SSNIT (5.5%)")
        recalc_ssnit_btn.setObjectName("secondary_btn")
        recalc_ssnit_btn.setFixedHeight(28)
        recalc_ssnit_btn.clicked.connect(self._recalc_ssnit)
        form_layout.addRow("", recalc_ssnit_btn)
        
        # Net Pay — read-only live display
        self.net_lbl = QLabel("GHS 0.00")
        self.net_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #10b981;")
        form_layout.addRow("Net Pay (Auto):", self.net_lbl)
        
        layout.addWidget(form_frame)
        
        # Connect value changes to live recalculation
        self.basic_spin.valueChanged.connect(self._update_net)
        self.allow_spin.valueChanged.connect(self._update_net)
        self.tax_spin.valueChanged.connect(self._update_net)
        self.ssnit_spin.valueChanged.connect(self._update_net)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_payslip)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def load_payslip_data(self):
        session = get_session()
        try:
            from database.models import Payslip
            sl = session.query(Payslip).filter(Payslip.id == self.payslip_id).first()
            if sl:
                self.setWindowTitle(f"Edit Payslip — {sl.staff.first_name} {sl.staff.last_name} ({sl.pay_period})")
                self.basic_spin.setValue(sl.base_salary or 0.0)
                self.allow_spin.setValue(sl.allowances or 0.0)
                self.tax_spin.setValue(sl.tax_deductions or 0.0)
                self.ssnit_spin.setValue(sl.pension_deductions or 0.0)
                self._update_net()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load payslip: {e}")
        finally:
            session.close()
            
    def _update_net(self):
        gross = self.basic_spin.value() + self.allow_spin.value()
        net = gross - self.tax_spin.value() - self.ssnit_spin.value()
        self.net_lbl.setText(f"GHS {net:,.2f}")
        if net >= 0:
            self.net_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #10b981;")
        else:
            self.net_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ef4444;")
            
    def _recalc_tax(self):
        gross = self.basic_spin.value() + self.allow_spin.value()
        self.tax_spin.setValue(round(gross * 0.15, 2))
        
    def _recalc_ssnit(self):
        self.ssnit_spin.setValue(round(self.basic_spin.value() * 0.055, 2))
        
    def save_payslip(self):
        session = get_session()
        try:
            from database.models import Payslip
            sl = session.query(Payslip).filter(Payslip.id == self.payslip_id).first()
            if not sl:
                QMessageBox.warning(self, "Error", "Payslip record not found.")
                return
                
            basic = self.basic_spin.value()
            allowances = self.allow_spin.value()
            tax = self.tax_spin.value()
            ssnit = self.ssnit_spin.value()
            net = (basic + allowances) - tax - ssnit
            
            sl.base_salary = basic
            sl.allowances = allowances
            sl.tax_deductions = tax
            sl.pension_deductions = ssnit
            sl.net_salary = net
            
            # Also sync staff base salary so future payroll generations pick it up
            staff_obj = sl.staff
            if staff_obj:
                staff_obj.base_salary = basic
                
            session.commit()
            QMessageBox.information(
                self, "Saved",
                f"Payslip updated.\nNet Pay: GHS {net:,.2f}"
            )
            self.payslip_saved.emit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save payslip: {e}")
        finally:
            session.close()

