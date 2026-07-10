from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QTabWidget
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor
from database.connection import get_session
from database.models import Student, Fee, StudentBill, Payment, Class, Expense, SMSLog
from utils.pdf_generator import generate_fee_receipt, generate_financial_statement
from utils.exporter import export_to_excel
import datetime

class FeesPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.active_student_id = None
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QTabWidget()
        
        # 1. Collect Fees Tab
        self.collect_tab = QWidget()
        self.init_collect_tab()
        self.tabs.addTab(self.collect_tab, "Collect Payments")
        
        # 2. Fee Structure Setup Tab
        self.structure_tab = QWidget()
        self.init_structure_tab()
        self.tabs.addTab(self.structure_tab, "Fee Structure")
        
        # 3. Defaulters / Balances Ledger Tab
        self.balances_tab = QWidget()
        self.init_balances_tab()
        self.tabs.addTab(self.balances_tab, "Balances Ledger")
        
        # 4. Income & Expense Ledger Tab
        self.ledger_tab = QWidget()
        self.init_ledger_tab()
        self.tabs.addTab(self.ledger_tab, "Income & Expense Ledger")
        
        layout.addWidget(self.tabs)
        
    def init_collect_tab(self):
        tab_layout = QVBoxLayout(self.collect_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        # Student Search Bar
        search_bar = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search student by ID or Name to record payment...")
        self.search_input.returnPressed.connect(self.search_student_bills)
        search_bar.addWidget(self.search_input, stretch=4)
        
        search_btn = QPushButton("Load Bills")
        search_btn.setObjectName("secondary_btn")
        search_btn.clicked.connect(self.search_student_bills)
        search_bar.addWidget(search_btn)
        
        tab_layout.addLayout(search_bar)
        
        # Student name label
        self.student_name_lbl = QLabel("No student loaded.")
        self.student_name_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b82f6;")
        tab_layout.addWidget(self.student_name_lbl)
        
        # Bills table
        self.bills_table = QTableWidget()
        self.bills_table.setColumnCount(6)
        self.bills_table.setHorizontalHeaderLabels([
            "Bill ID", "Fee Name", "Amount Billed", "Amount Paid", "Outstanding Balance", "Status"
        ])
        self.bills_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.bills_table)
        
        # Action layout
        actions = QHBoxLayout()
        pay_btn = QPushButton("Record Selected Payment")
        pay_btn.setObjectName("primary_btn")
        pay_btn.clicked.connect(self.open_payment_dialog)
        actions.addWidget(pay_btn)
        
        receipt_btn = QPushButton("Print Selected Receipt")
        receipt_btn.setObjectName("secondary_btn")
        receipt_btn.clicked.connect(self.print_payment_receipt)
        actions.addWidget(receipt_btn)
        
        actions.addStretch()
        tab_layout.addLayout(actions)
        
    def search_student_bills(self):
        search_term = self.search_input.text().strip()
        if not search_term:
            return
            
        self.bills_table.setRowCount(0)
        self.student_name_lbl.setText("No student loaded.")
        self.active_student_id = None
        
        session = get_session()
        try:
            # Query Student
            student = session.query(Student).filter(
                (Student.id == search_term) |
                (Student.first_name.ilike(f"%{search_term}%")) |
                (Student.last_name.ilike(f"%{search_term}%"))
            ).first()
            
            if not student:
                QMessageBox.warning(self, "Not Found", f"No active student found for query: '{search_term}'")
                return
                
            self.active_student_id = student.id
            self.student_name_lbl.setText(f"Billing Profile: {student.last_name}, {student.first_name} ({student.id}) - {student.class_assigned.name if student.class_assigned else 'Unassigned'}")
            
            # Fetch bills
            bills = session.query(StudentBill).filter(StudentBill.student_id == student.id).all()
            self.bills_table.setRowCount(len(bills))
            for i, bill in enumerate(bills):
                self.bills_table.setItem(i, 0, QTableWidgetItem(str(bill.id)))
                self.bills_table.setItem(i, 1, QTableWidgetItem(bill.fee.name))
                self.bills_table.setItem(i, 2, QTableWidgetItem(f"{bill.amount_billed:.2f}"))
                self.bills_table.setItem(i, 3, QTableWidgetItem(f"{bill.amount_paid:.2f}"))
                
                outstanding = bill.amount_billed - bill.amount_paid
                self.bills_table.setItem(i, 4, QTableWidgetItem(f"{outstanding:.2f}"))
                self.bills_table.setItem(i, 5, QTableWidgetItem(bill.status))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to search bills: {e}")
        finally:
            session.close()

    def open_payment_dialog(self):
        selected_row = self.bills_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Select Bill", "Please select a fee bill from the table first.")
            return
            
        bill_id = int(self.bills_table.item(selected_row, 0).text())
        dialog = RecordPaymentDialog(bill_id, self.user, self)
        dialog.payment_saved.connect(self.search_student_bills)
        dialog.exec()
        
    def print_payment_receipt(self):
        selected_row = self.bills_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Select Bill", "Please select a fee bill from the table first.")
            return
            
        bill_id = int(self.bills_table.item(selected_row, 0).text())
        
        session = get_session()
        try:
            # Query last payment ID for this bill
            pmt = session.query(Payment).filter(Payment.student_bill_id == bill_id).order_by(Payment.payment_date.desc()).first()
            if not pmt:
                QMessageBox.warning(self, "No Payments", "No payments have been recorded for this bill yet.")
                return
                
            success, filepath = generate_fee_receipt(pmt.id)
            if success:
                QMessageBox.information(self, "Success", f"Fee Receipt PDF generated at:\n{filepath}")
            else:
                QMessageBox.warning(self, "Failed", f"Failed to generate receipt:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database error: {e}")
        finally:
            session.close()

    # --- Fee Structure ---
    def init_structure_tab(self):
        tab_layout = QVBoxLayout(self.structure_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        actions = QHBoxLayout()
        create_fee_btn = QPushButton("Create Fee Item")
        create_fee_btn.setObjectName("primary_btn")
        create_fee_btn.clicked.connect(self.open_create_fee_dialog)
        actions.addWidget(create_fee_btn)
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        self.fee_table = QTableWidget()
        self.fee_table.setColumnCount(4)
        self.fee_table.setHorizontalHeaderLabels(["Fee ID", "Fee Item Name", "Term Amount (GHS)", "Target Class Level"])
        self.fee_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.fee_table)
        self.load_fees()
        
    def load_fees(self):
        self.fee_table.setRowCount(0)
        session = get_session()
        try:
            fees = session.query(Fee).all()
            self.fee_table.setRowCount(len(fees))
            for i, fee in enumerate(fees):
                self.fee_table.setItem(i, 0, QTableWidgetItem(str(fee.id)))
                self.fee_table.setItem(i, 1, QTableWidgetItem(fee.name))
                self.fee_table.setItem(i, 2, QTableWidgetItem(f"{fee.amount:.2f}"))
                self.fee_table.setItem(i, 3, QTableWidgetItem(fee.class_level))
        except Exception as e:
            print(f"Error loading fees: {e}")
        finally:
            session.close()
            
    def open_create_fee_dialog(self):
        dialog = CreateFeeDialog(self)
        dialog.data_changed.connect(self.load_fees)
        dialog.exec()

    # --- Balances Ledger ---
    def init_balances_tab(self):
        tab_layout = QVBoxLayout(self.balances_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        # Export Bar
        actions = QHBoxLayout()
        export_btn = QPushButton("Export Defaulters to Excel")
        export_btn.setObjectName("secondary_btn")
        export_btn.clicked.connect(self.export_balances)
        actions.addWidget(export_btn)
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        self.ledger_table = QTableWidget()
        self.ledger_table.setColumnCount(6)
        self.ledger_table.setHorizontalHeaderLabels([
            "Student ID", "Student Name", "Class", "Total Billed", "Total Paid", "Outstanding Balance"
        ])
        self.ledger_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.ledger_table)
        self.load_ledger()
        
    def load_ledger(self):
        self.ledger_table.setRowCount(0)
        session = get_session()
        try:
            students = session.query(Student).filter(Student.status == "Active").all()
            self.ledger_table.setRowCount(len(students))
            for i, s in enumerate(students):
                self.ledger_table.setItem(i, 0, QTableWidgetItem(s.id))
                self.ledger_table.setItem(i, 1, QTableWidgetItem(f"{s.last_name}, {s.first_name}"))
                self.ledger_table.setItem(i, 2, QTableWidgetItem(s.class_assigned.name if s.class_assigned else "Unassigned"))
                
                # Fetch summary bills
                bills = session.query(StudentBill).filter(StudentBill.student_id == s.id).all()
                total_billed = sum(b.amount_billed for b in bills)
                total_paid = sum(b.amount_paid for b in bills)
                balance = total_billed - total_paid
                
                self.ledger_table.setItem(i, 3, QTableWidgetItem(f"{total_billed:.2f}"))
                self.ledger_table.setItem(i, 4, QTableWidgetItem(f"{total_paid:.2f}"))
                self.ledger_table.setItem(i, 5, QTableWidgetItem(f"{balance:.2f}"))
        except Exception as e:
            print(f"Error loading ledger: {e}")
        finally:
            session.close()
            
    def export_balances(self):
        # Gather ledger table data
        data = []
        for row in range(self.ledger_table.rowCount()):
            data.append({
                "student_id": self.ledger_table.item(row, 0).text(),
                "student_name": self.ledger_table.item(row, 1).text(),
                "class_stream": self.ledger_table.item(row, 2).text(),
                "total_billed_ghs": float(self.ledger_table.item(row, 3).text()),
                "total_paid_ghs": float(self.ledger_table.item(row, 4).text()),
                "outstanding_balance_ghs": float(self.ledger_table.item(row, 5).text()),
            })
            
        success, message = export_to_excel(data, "exports/fee_balances.xlsx", "Defaulters Ledger")
        if success:
            QMessageBox.information(self, "Export Complete", message)
        else:
            QMessageBox.warning(self, "Export Failed", message)
            
    # --- Income & Expense Ledger ---
    def init_ledger_tab(self):
        tab_layout = QVBoxLayout(self.ledger_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        # Summary KPI Boxes
        summary_frame = QFrame()
        summary_frame.setObjectName("card")
        summary_frame.setStyleSheet("padding: 10px;")
        summary_layout = QHBoxLayout(summary_frame)
        
        # Rev
        rev_widget = QWidget()
        rev_l = QVBoxLayout(rev_widget)
        rev_l.addWidget(QLabel("Total Revenue Collected:"))
        self.total_rev_lbl = QLabel("GHS 0.00")
        self.total_rev_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #10b981;")
        rev_l.addWidget(self.total_rev_lbl)
        summary_layout.addWidget(rev_widget)
        
        # Exp
        exp_widget = QWidget()
        exp_l = QVBoxLayout(exp_widget)
        exp_l.addWidget(QLabel("Total Expenses Logged:"))
        self.total_exp_lbl = QLabel("GHS 0.00")
        self.total_exp_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ef4444;")
        exp_l.addWidget(self.total_exp_lbl)
        summary_layout.addWidget(exp_widget)
        
        # Net
        net_widget = QWidget()
        net_l = QVBoxLayout(net_widget)
        net_l.addWidget(QLabel("Net Surplus / Deficit:"))
        self.total_net_lbl = QLabel("GHS 0.00")
        self.total_net_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6;")
        net_l.addWidget(self.total_net_lbl)
        summary_layout.addWidget(net_widget)
        
        tab_layout.addWidget(summary_frame)
        
        # Actions bar
        actions = QHBoxLayout()
        add_expense_btn = QPushButton("Log Operational Expense")
        add_expense_btn.setObjectName("primary_btn")
        add_expense_btn.clicked.connect(self.open_expense_dialog)
        actions.addWidget(add_expense_btn)
        
        pdf_statement_btn = QPushButton("Print Income Statement PDF")
        pdf_statement_btn.setObjectName("secondary_btn")
        pdf_statement_btn.clicked.connect(self.print_financial_statement)
        actions.addWidget(pdf_statement_btn)
        
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        # Ledger Table
        self.ledger_list_table = QTableWidget()
        self.ledger_list_table.setColumnCount(5)
        self.ledger_list_table.setHorizontalHeaderLabels(["Date", "Ledger Type", "Transaction Title", "Category Block", "Amount (GHS)"])
        self.ledger_list_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.ledger_list_table)
        self.load_income_expense_ledger()
        
    def load_income_expense_ledger(self):
        self.ledger_list_table.setRowCount(0)
        session = get_session()
        try:
            # Fetch payments (Incomes)
            payments = session.query(Payment).all()
            
            # Fetch expenses (Expenses)
            expenses = session.query(Expense).all()
            
            # Combine items with dates and details
            combined = []
            total_revenue = 0.0
            total_expenses = 0.0
            
            for p in payments:
                total_revenue += p.amount
                combined.append({
                    "date": p.payment_date,
                    "type": "INCOME",
                    "title": p.student_bill.fee.name if p.student_bill else "Student Fee Payment",
                    "category": "Fee Revenue",
                    "amount": p.amount
                })
                
            for e in expenses:
                # Convert date to datetime for sorting
                dt = datetime.datetime.combine(e.date, datetime.time.min)
                total_expenses += e.amount
                combined.append({
                    "date": dt,
                    "type": "EXPENSE",
                    "title": e.title,
                    "category": e.category,
                    "amount": e.amount
                })
                
            # Update labels
            self.total_rev_lbl.setText(f"GHS {total_revenue:.2f}")
            self.total_exp_lbl.setText(f"GHS {total_expenses:.2f}")
            
            net = total_revenue - total_expenses
            self.total_net_lbl.setText(f"GHS {net:.2f}")
            if net >= 0:
                self.total_net_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #10b981;")
            else:
                self.total_net_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #ef4444;")
                
            # Sort combined logs by date descending
            combined.sort(key=lambda x: x["date"], reverse=True)
            self.ledger_list_table.setRowCount(len(combined))
            
            for idx, item in enumerate(combined):
                self.ledger_list_table.setItem(idx, 0, QTableWidgetItem(item["date"].strftime("%Y-%m-%d")))
                self.ledger_list_table.setItem(idx, 1, QTableWidgetItem(item["type"]))
                
                # Style row type item
                type_item = self.ledger_list_table.item(idx, 1)
                if item["type"] == "INCOME":
                    type_item.setForeground(QColor("#10b981"))
                else:
                    type_item.setForeground(QColor("#ef4444"))
                    
                self.ledger_list_table.setItem(idx, 2, QTableWidgetItem(item["title"]))
                self.ledger_list_table.setItem(idx, 3, QTableWidgetItem(item["category"]))
                
                amt_str = f"+GHS {item['amount']:.2f}" if item["type"] == "INCOME" else f"-GHS {item['amount']:.2f}"
                amt_item = QTableWidgetItem(amt_str)
                if item["type"] == "INCOME":
                    amt_item.setForeground(QColor("#10b981"))
                else:
                    amt_item.setForeground(QColor("#ef4444"))
                    
                self.ledger_list_table.setItem(idx, 4, amt_item)
        except Exception as e:
            print(f"Error loading financial ledger: {e}")
        finally:
            session.close()

    def open_expense_dialog(self):
        dialog = LogExpenseDialog(self.user, self)
        dialog.expense_logged.connect(self.load_income_expense_ledger)
        dialog.exec()
        
    def print_financial_statement(self):
        success, filepath = generate_financial_statement()
        if success:
            QMessageBox.information(self, "Success", f"Financial Income Statement PDF generated at:\n{filepath}")
        else:
            QMessageBox.warning(self, "Failed", f"Failed to generate income statement:\n{filepath}")

    def refresh(self):
        if self.active_student_id:
            self.search_input.setText(self.active_student_id)
            self.search_student_bills()
        self.load_fees()
        self.load_ledger()
        self.load_income_expense_ledger()

class RecordPaymentDialog(QDialog):
    payment_saved = Signal()
    
    def __init__(self, bill_id, user, parent_widget=None):
        super().__init__(parent_widget)
        self.bill_id = bill_id
        self.user = user
        self.setWindowTitle("Record Fee Payment")
        self.setMinimumWidth(350)
        self.init_ui()
        self.load_bill_data()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.desc_lbl = QLabel()
        self.desc_lbl.setStyleSheet("font-weight: bold; color: #3b82f6;")
        
        self.billed_lbl = QLabel()
        self.paid_lbl = QLabel()
        self.outstanding_lbl = QLabel()
        
        self.amount_input = QLineEdit()
        self.method_combo = QComboBox()
        self.method_combo.addItems(["Cash", "Mobile Money", "Bank Transfer", "Cheque"])
        self.ref_input = QLineEdit()
        
        form_layout.addRow("Fee Item:", self.desc_lbl)
        form_layout.addRow("Amount Billed (GHS):", self.billed_lbl)
        form_layout.addRow("Amount Paid (GHS):", self.paid_lbl)
        form_layout.addRow("Remaining Outstanding:", self.outstanding_lbl)
        form_layout.addRow("Payment Amount (GHS):", self.amount_input)
        form_layout.addRow("Payment Mode:", self.method_combo)
        form_layout.addRow("Transaction / Reference Ref:", self.ref_input)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_payment)
        btn_box.rejected.connect(self.reject)
        
        layout.addWidget(btn_box)
        
    def load_bill_data(self):
        session = get_session()
        try:
            bill = session.query(StudentBill).filter(StudentBill.id == self.bill_id).first()
            if bill:
                self.desc_lbl.setText(bill.fee.name)
                self.billed_lbl.setText(f"{bill.amount_billed:.2f}")
                self.paid_lbl.setText(f"{bill.amount_paid:.2f}")
                
                outstanding = bill.amount_billed - bill.amount_paid
                self.outstanding_lbl.setText(f"{outstanding:.2f}")
                self.amount_input.setText(f"{outstanding:.2f}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load bill: {e}")
        finally:
            session.close()

    def save_payment(self):
        try:
            amount_to_pay = float(self.amount_input.text().strip() or "0.0")
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Invalid payment amount.")
            return
            
        session = get_session()
        try:
            bill = session.query(StudentBill).filter(StudentBill.id == self.bill_id).first()
            if bill:
                outstanding = bill.amount_billed - bill.amount_paid
                if amount_to_pay <= 0 or amount_to_pay > outstanding:
                    QMessageBox.warning(self, "Validation Error", f"Payment must be between GHS 0.01 and GHS {outstanding:.2f}.")
                    return
                    
                # Update bill balances
                bill.amount_paid += amount_to_pay
                if bill.amount_paid >= bill.amount_billed:
                    bill.status = "Paid"
                else:
                    bill.status = "Partially Paid"
                    
                # Record Payment transaction log
                staff_id = self.user.staff_profile.id if self.user.staff_profile else None
                payment = Payment(
                    student_bill_id=self.bill_id,
                    amount=amount_to_pay,
                    payment_method=self.method_combo.currentText(),
                    reference_no=self.ref_input.text().strip() or None,
                    received_by=staff_id
                )
                session.add(payment)
                
                # Send SMS receipt to parent if phone exists
                student = bill.student
                if student and student.parent and student.parent.phone:
                    parent_phone = student.parent.phone
                    sms_msg = f"Orion School Payment Receipt: GHS {amount_to_pay:.2f} received for {student.first_name} {student.last_name} (Category: {bill.fee_category.name}). Remaining Balance: GHS {(bill.amount_billed - bill.amount_paid - amount_to_pay):.2f}."
                    sms_log = SMSLog(
                        recipient_phone=parent_phone,
                        message_content=sms_msg,
                        status="Sent",
                        trigger_type="Fees"
                    )
                    session.add(sms_log)
                    
                session.commit()
                
                # Generate receipt PDF instantly
                success, filepath = generate_fee_receipt(payment.id)
                msg = f"Payment of GHS {amount_to_pay:.2f} recorded successfully."
                if success:
                    msg += f"\nReceipt generated at:\n{filepath}"
                QMessageBox.information(self, "Success", msg)
                
                self.payment_saved.emit()
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to record payment: {e}")
        finally:
            session.close()

class CreateFeeDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Create Term Fee")
        self.setMinimumWidth(320)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.amount_input = QLineEdit()
        
        self.level_combo = QComboBox()
        self.level_combo.addItems(["All", "Kindergarten", "Primary", "JHS"])
        
        form_layout.addRow("Fee Name:", self.name_input)
        form_layout.addRow("Amount (GHS):", self.amount_input)
        form_layout.addRow("Target Level:", self.level_combo)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_fee)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def save_fee(self):
        name = self.name_input.text().strip()
        try:
            amount = float(self.amount_input.text().strip() or "0.0")
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Invalid fee amount.")
            return
            
        if not name or amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Please input a valid name and positive amount.")
            return
            
        session = get_session()
        try:
            # Get active session from config
            ay_id = config.get("active_academic_year_id", 1)
            term_id = config.get("active_term_id", 1)
            
            fee = Fee(
                name=name,
                amount=amount,
                class_level=self.level_combo.currentText(),
                academic_year_id=ay_id,
                term_id=term_id
            )
            session.add(fee)
            session.flush()
            
            # Automatically bill active students matching this category
            students = session.query(Student).filter(Student.status == "Active").all()
            for s in students:
                cls_obj = session.query(Class).filter(Class.id == s.class_id).first()
                if fee.class_level == "All" or fee.class_level == cls_obj.level:
                    bill = StudentBill(
                        student_id=s.id,
                        fee_id=fee.id,
                        amount_billed=fee.amount,
                        amount_paid=0.0,
                        status="Unpaid"
                    )
                    session.add(bill)
            
            QMessageBox.information(self, "Success", f"Fee '{name}' created and students billed successfully.")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save fee structure: {e}")
        finally:
            session.close()



class LogExpenseDialog(QDialog):
    expense_logged = Signal()
    
    def __init__(self, user, parent_widget=None):
        super().__init__(parent_widget)
        self.user = user
        self.setWindowTitle("Log School Expense")
        self.setMinimumWidth(320)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g. Fuel for generator")
        
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["Utilities", "Maintenance", "Salaries", "Supplies", "Branding / Events", "Other"])
        
        self.amount_input = QLineEdit()
        self.desc_input = QLineEdit()
        
        form_layout.addRow("Expense Title:", self.title_input)
        form_layout.addRow("Category:", self.cat_combo)
        form_layout.addRow("Amount (GHS):", self.amount_input)
        form_layout.addRow("Description / Details:", self.desc_input)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_expense)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def save_expense(self):
        title = self.title_input.text().strip()
        try:
            amount = float(self.amount_input.text().strip() or "0.0")
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Invalid expense amount.")
            return
            
        if not title or amount <= 0:
            QMessageBox.warning(self, "Validation Error", "Please enter a valid title and positive amount.")
            return
            
        session = get_session()
        try:
            staff_id = self.user.staff_profile.id if self.user.staff_profile else None
            exp = Expense(
                title=title,
                category=self.cat_combo.currentText(),
                amount=amount,
                description=self.desc_input.text().strip() or None,
                recorded_by=staff_id
            )
            session.add(exp)
            session.commit()
            
            QMessageBox.information(self, "Success", "Operational expense logged successfully.")
            self.expense_logged.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to log expense: {e}")
        finally:
            session.close()
