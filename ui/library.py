from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QFormLayout, QDialogButtonBox,
    QTabWidget, QDateEdit
)
from PySide6.QtCore import Qt, QDate, Signal
from database.connection import get_session
from database.models import LibraryBook, LibraryIssue, Student, Staff, SMSLog
import datetime

class LibraryPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.tabs = QTabWidget()
        
        # 1. Books Directory Tab
        self.books_tab = QWidget()
        self.init_books_tab()
        self.tabs.addTab(self.books_tab, "Book Catalogue")
        
        # 2. Issues Tab
        self.issues_tab = QWidget()
        self.init_issues_tab()
        self.tabs.addTab(self.issues_tab, "Lending & Returns")
        
        # 3. Overdue Alerts Tab
        self.overdue_tab = QWidget()
        self.init_overdue_tab()
        self.tabs.addTab(self.overdue_tab, "Overdue & Notices")
        
        layout.addWidget(self.tabs)
        
    # --- Books Directory ---
    def init_books_tab(self):
        tab_layout = QVBoxLayout(self.books_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        actions = QHBoxLayout()
        self.search_book_input = QLineEdit()
        self.search_book_input.setPlaceholderText("Search book catalog by title or author...")
        self.search_book_input.textChanged.connect(self.load_books)
        actions.addWidget(self.search_book_input, stretch=3)
        
        add_book_btn = QPushButton("Add Book")
        add_book_btn.setObjectName("primary_btn")
        add_book_btn.clicked.connect(self.open_add_book_dialog)
        actions.addWidget(add_book_btn)
        
        tab_layout.addLayout(actions)
        
        self.books_table = QTableWidget()
        self.books_table.setColumnCount(7)
        self.books_table.setHorizontalHeaderLabels([
            "Book ID", "Title", "Author", "ISBN", "Category", "Available / Total", "Location"
        ])
        self.books_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.books_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tab_layout.addWidget(self.books_table)
        self.load_books()
        
    def load_books(self):
        self.books_table.setRowCount(0)
        session = get_session()
        try:
            query = session.query(LibraryBook)
            search_text = self.search_book_input.text().strip()
            if search_text:
                query = query.filter(
                    (LibraryBook.title.ilike(f"%{search_text}%")) |
                    (LibraryBook.author.ilike(f"%{search_text}%"))
                )
                
            books = query.order_by(LibraryBook.title.asc()).all()
            self.books_table.setRowCount(len(books))
            for i, b in enumerate(books):
                self.books_table.setItem(i, 0, QTableWidgetItem(str(b.id)))
                self.books_table.setItem(i, 1, QTableWidgetItem(b.title))
                self.books_table.setItem(i, 2, QTableWidgetItem(b.author))
                self.books_table.setItem(i, 3, QTableWidgetItem(b.isbn or "N/A"))
                self.books_table.setItem(i, 4, QTableWidgetItem(b.category or "General"))
                self.books_table.setItem(i, 5, QTableWidgetItem(f"{b.available_copies} / {b.total_copies}"))
                self.books_table.setItem(i, 6, QTableWidgetItem(b.location or "N/A"))
        except Exception as e:
            print(f"Error loading books: {e}")
        finally:
            session.close()
            
    def open_add_book_dialog(self):
        dialog = AddBookDialog(self)
        dialog.data_changed.connect(self.load_books)
        dialog.exec()

    # --- Issues & Borrowing ---
    def init_issues_tab(self):
        tab_layout = QVBoxLayout(self.issues_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        actions = QHBoxLayout()
        issue_book_btn = QPushButton("Issue Book to Student")
        issue_book_btn.setObjectName("primary_btn")
        issue_book_btn.clicked.connect(self.open_issue_dialog)
        actions.addWidget(issue_book_btn)
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        self.issues_table = QTableWidget()
        self.issues_table.setColumnCount(8)
        self.issues_table.setHorizontalHeaderLabels([
            "Issue ID", "Book Title", "Student ID", "Issue Date", "Due Date", "Return Date", "Fine (GHS)", "Action"
        ])
        self.issues_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.issues_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tab_layout.addWidget(self.issues_table)
        self.load_issues()
        
    def load_issues(self):
        self.issues_table.setRowCount(0)
        session = get_session()
        try:
            issues = session.query(LibraryIssue).order_by(LibraryIssue.return_date.asc(), LibraryIssue.due_date.asc()).all()
            self.issues_table.setRowCount(len(issues))
            
            for i, issue in enumerate(issues):
                self.issues_table.setItem(i, 0, QTableWidgetItem(str(issue.id)))
                self.issues_table.setItem(i, 1, QTableWidgetItem(issue.book.title))
                
                borrower = issue.student_id if issue.student_id else f"Staff: {issue.staff_id}"
                self.issues_table.setItem(i, 2, QTableWidgetItem(borrower))
                
                self.issues_table.setItem(i, 3, QTableWidgetItem(issue.issue_date.strftime("%Y-%m-%d")))
                self.issues_table.setItem(i, 4, QTableWidgetItem(issue.due_date.strftime("%Y-%m-%d")))
                
                ret_str = issue.return_date.strftime("%Y-%m-%d") if issue.return_date else "Not Returned"
                self.issues_table.setItem(i, 5, QTableWidgetItem(ret_str))
                
                # Overdue Fine computation: GHS 2.00 per day late
                fine = 0.0
                if issue.return_date:
                    fine = issue.fine_amount
                else:
                    today = datetime.date.today()
                    if today > issue.due_date:
                        days_late = (today - issue.due_date).days
                        fine = days_late * 2.00
                
                self.issues_table.setItem(i, 6, QTableWidgetItem(f"{fine:.2f}"))
                
                # Action button inside table
                if not issue.return_date:
                    return_btn = QPushButton("Return Book")
                    return_btn.setObjectName("secondary_btn")
                    return_btn.clicked.connect(lambda checked=False, iss_id=issue.id: self.return_book(iss_id))
                    self.issues_table.setCellWidget(i, 7, return_btn)
                else:
                    comp_lbl = QLabel("Completed")
                    comp_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    comp_lbl.setStyleSheet("color: #10b981; font-weight: bold;")
                    self.issues_table.setCellWidget(i, 7, comp_lbl)
        except Exception as e:
            print(f"Error loading library issues: {e}")
        finally:
            session.close()

    def open_issue_dialog(self):
        dialog = IssueBookDialog(self)
        dialog.data_changed.connect(self.load_issues)
        dialog.data_changed.connect(self.load_books)
        dialog.exec()
        
    def return_book(self, issue_id):
        session = get_session()
        try:
            issue = session.query(LibraryIssue).filter(LibraryIssue.id == issue_id).first()
            if issue:
                today = datetime.date.today()
                issue.return_date = today
                
                # Check overdue fine
                fine = 0.0
                if today > issue.due_date:
                    days_late = (today - issue.due_date).days
                    fine = days_late * 2.00
                    issue.fine_amount = fine
                    issue.fine_status = "Unpaid"
                
                # Update copy availability
                issue.book.available_copies += 1
                
                session.commit()
                msg = "Book returned successfully."
                if fine > 0:
                    msg += f"\nLate penalty incurred: GHS {fine:.2f}"
                QMessageBox.information(self, "Success", msg)
                
                self.load_issues()
                self.load_books()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to return book: {e}")
        finally:
            session.close()
            
    # --- Overdue & Notices ---
    def init_overdue_tab(self):
        tab_layout = QVBoxLayout(self.overdue_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        top_bar = QHBoxLayout()
        notify_all_btn = QPushButton("Auto-Notify All Overdue Borrowers via SMS")
        notify_all_btn.setObjectName("danger_btn")
        notify_all_btn.clicked.connect(self.sms_all_overdue)
        top_bar.addWidget(notify_all_btn)
        top_bar.addStretch()
        tab_layout.addLayout(top_bar)
        
        self.overdue_table = QTableWidget()
        self.overdue_table.verticalHeader().setDefaultSectionSize(36)
        self.overdue_table.setColumnCount(6)
        self.overdue_table.setHorizontalHeaderLabels(["ID", "Book Title", "Student Name", "Due Date", "Days Overdue", "Actions"])
        self.overdue_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.overdue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.overdue_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)
        self.overdue_table.setColumnWidth(5, 150)
        tab_layout.addWidget(self.overdue_table)
        
        self.load_overdue_log()
        
    def load_overdue_log(self):
        self.overdue_table.setRowCount(0)
        session = get_session()
        try:
            today = datetime.date.today()
            # Fetch active issues where due_date has passed
            overdues = session.query(LibraryIssue).filter(
                LibraryIssue.return_date == None,
                LibraryIssue.due_date < today
            ).all()
            
            self.overdue_table.setRowCount(len(overdues))
            for idx, issue in enumerate(overdues):
                self.overdue_table.setItem(idx, 0, QTableWidgetItem(str(issue.id)))
                self.overdue_table.setItem(idx, 1, QTableWidgetItem(issue.book.title))
                
                borrower_name = f"{issue.student.last_name}, {issue.student.first_name}" if issue.student else "Unknown Student"
                self.overdue_table.setItem(idx, 2, QTableWidgetItem(borrower_name))
                
                self.overdue_table.setItem(idx, 3, QTableWidgetItem(issue.due_date.strftime("%Y-%m-%d")))
                
                days_late = (today - issue.due_date).days
                self.overdue_table.setItem(idx, 4, QTableWidgetItem(f"{days_late} days"))
                
                # Action Alert button
                btn = QPushButton("Send Parent SMS")
                btn.setObjectName("secondary_btn")
                btn.clicked.connect(lambda checked=False, i_id=issue.id: self.sms_single_overdue(i_id))
                self.overdue_table.setCellWidget(idx, 5, btn)
        except Exception as e:
            print(f"Error loading overdue issues: {e}")
        finally:
            session.close()

    def sms_single_overdue(self, issue_id):
        session = get_session()
        try:
            issue = session.query(LibraryIssue).filter(LibraryIssue.id == issue_id).first()
            if not issue:
                return
                
            student = issue.student
            if student and student.parent and student.parent.phone:
                days_late = (datetime.date.today() - issue.due_date).days
                msg = f"Orion Notice: Dear Parent, the library book '{issue.book.title}' borrowed by your ward {student.first_name} was due on {issue.due_date.strftime('%Y-%m-%d')} and is overdue by {days_late} days. Please return it to the library."
                
                sms = SMSLog(
                    recipient_phone=student.parent.phone,
                    message_content=msg,
                    status="Sent",
                    trigger_type="Library"
                )
                session.add(sms)
                session.commit()
                QMessageBox.information(self, "Success", f"Overdue SMS sent to parent: {student.parent.phone}")
                self.load_overdue_log()
            else:
                QMessageBox.warning(self, "No Phone", "No parent phone number linked to this student profile.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to dispatch SMS: {e}")
        finally:
            session.close()

    def sms_all_overdue(self):
        session = get_session()
        try:
            today = datetime.date.today()
            overdues = session.query(LibraryIssue).filter(
                LibraryIssue.return_date == None,
                LibraryIssue.due_date < today
            ).all()
            
            if not overdues:
                QMessageBox.information(self, "No Overdues", "No overdue book borrowings found.")
                return
                
            confirm = QMessageBox.question(
                self, "Confirm Broadcast", f"Are you sure you want to send overdue SMS alerts to the parents of all {len(overdues)} overdue books?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirm == QMessageBox.StandardButton.No:
                return
                
            sent_count = 0
            for issue in overdues:
                student = issue.student
                if student and student.parent and student.parent.phone:
                    days_late = (today - issue.due_date).days
                    msg = f"Orion Notice: Dear Parent, the library book '{issue.book.title}' borrowed by your ward {student.first_name} was due on {issue.due_date.strftime('%Y-%m-%d')} and is overdue by {days_late} days. Please return it to the library."
                    
                    sms = SMSLog(
                        recipient_phone=student.parent.phone,
                        message_content=msg,
                        status="Sent",
                        trigger_type="Library"
                    )
                    session.add(sms)
                    sent_count += 1
                    
            session.commit()
            QMessageBox.information(self, "Broadcast Complete", f"Successfully dispatched overdue alerts SMS to {sent_count} parents.")
            self.load_overdue_log()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to dispatch batch SMS: {e}")
        finally:
            session.close()

    def refresh(self):
        self.load_books()
        self.load_issues()
        self.load_overdue_log()

class AddBookDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Register Book")
        self.setMinimumWidth(320)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.title_input = QLineEdit()
        self.author_input = QLineEdit()
        self.isbn_input = QLineEdit()
        self.cat_input = QLineEdit()
        self.copies_input = QLineEdit("1")
        self.loc_input = QLineEdit()
        
        form_layout.addRow("Book Title:", self.title_input)
        form_layout.addRow("Author Name:", self.author_input)
        form_layout.addRow("ISBN Number:", self.isbn_input)
        form_layout.addRow("Category / Subject:", self.cat_input)
        form_layout.addRow("Total Copies:", self.copies_input)
        form_layout.addRow("Shelf / Location:", self.loc_input)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_book)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def save_book(self):
        title = self.title_input.text().strip()
        author = self.author_input.text().strip()
        try:
            copies = int(self.copies_input.text().strip() or "1")
        except ValueError:
            QMessageBox.warning(self, "Validation Error", "Invalid copies count.")
            return
            
        if not title or not author or copies <= 0:
            QMessageBox.warning(self, "Validation Error", "Title, Author and positive copies count are required.")
            return
            
        session = get_session()
        try:
            book = LibraryBook(
                title=title,
                author=author,
                isbn=self.isbn_input.text().strip() or None,
                category=self.cat_input.text().strip() or None,
                total_copies=copies,
                available_copies=copies,
                location=self.loc_input.text().strip() or None
            )
            session.add(book)
            session.commit()
            
            QMessageBox.information(self, "Success", f"Book '{title}' registered.")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save book: {e}")
        finally:
            session.close()

class IssueBookDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Issue Library Book")
        self.setMinimumWidth(380)
        self.init_ui()
        self.load_combos()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.book_combo = QComboBox()
        self.borrower_type_combo = QComboBox()
        self.borrower_type_combo.addItems(["Student", "Staff Member"])
        self.borrower_type_combo.currentTextChanged.connect(self.on_borrower_type_changed)
        self.borrower_combo = QComboBox()
        
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate.currentDate().addDays(14)) # 14 days standard lend
        
        form_layout.addRow("Select Book:", self.book_combo)
        form_layout.addRow("Borrower Type:", self.borrower_type_combo)
        form_layout.addRow("Select Borrower:", self.borrower_combo)
        form_layout.addRow("Lending Due Date:", self.due_date_edit)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_issue)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def on_borrower_type_changed(self):
        self.borrower_combo.clear()
        session = get_session()
        try:
            if self.borrower_type_combo.currentText() == "Student":
                students = session.query(Student).filter(Student.status == "Active").order_by(Student.last_name.asc()).all()
                for s in students:
                    self.borrower_combo.addItem(f"{s.last_name}, {s.first_name} ({s.id})", s.id)
            else:
                staff_list = session.query(Staff).filter(Staff.status == "Active").order_by(Staff.last_name.asc()).all()
                for st in staff_list:
                    self.borrower_combo.addItem(f"{st.last_name}, {st.first_name} (ID: {st.id})", st.id)
        except Exception as e:
            print(f"Error loading borrowers: {e}")
        finally:
            session.close()
            
    def load_combos(self):
        session = get_session()
        try:
            # Books with copies available
            books = session.query(LibraryBook).filter(LibraryBook.available_copies > 0).all()
            for b in books:
                self.book_combo.addItem(f"{b.title} ({b.available_copies} avail)", b.id)
        except Exception as e:
            print(f"Error loading combos: {e}")
        finally:
            session.close()
            
        self.on_borrower_type_changed()
            
    def save_issue(self):
        book_id = self.book_combo.currentData()
        borrower_id = self.borrower_combo.currentData()
        borrower_type = self.borrower_type_combo.currentText()
        
        if not book_id or not borrower_id:
            QMessageBox.warning(self, "Validation Error", "Please select both a book and borrower.")
            return
            
        due_qdate = self.due_date_edit.date()
        due_date = datetime.date(due_qdate.year(), due_qdate.month(), due_qdate.day())
        
        if due_date <= datetime.date.today():
            QMessageBox.warning(self, "Validation Error", "Due date must be in the future.")
            return
            
        session = get_session()
        try:
            book = session.query(LibraryBook).filter(LibraryBook.id == book_id).first()
            if book:
                if book.available_copies <= 0:
                    QMessageBox.warning(self, "No Copies", "This book has no available copies remaining.")
                    return
                    
                # Decrement available count
                book.available_copies -= 1
                
                # Log issue
                issue = LibraryIssue(
                    book_id=book_id,
                    student_id=borrower_id if borrower_type == "Student" else None,
                    staff_id=borrower_id if borrower_type == "Staff Member" else None,
                    due_date=due_date
                )
                session.add(issue)
                session.commit()
                
                QMessageBox.information(self, "Success", "Book issued successfully.")
                self.data_changed.emit()
                self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to issue book: {e}")
        finally:
            session.close()


