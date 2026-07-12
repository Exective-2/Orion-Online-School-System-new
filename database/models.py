import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Date, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from database.connection import Base

# Association table for User Roles and Permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
)

class Role(Base):
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)  # e.g., "Super Admin", "Teacher"
    description = Column(String(200))
    
    users = relationship("User", back_populates="role")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")

class Permission(Base):
    __tablename__ = "permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # e.g., "view_dashboard", "edit_fees"
    description = Column(String(200))
    
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    email = Column(String(100), unique=True, nullable=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    role = relationship("Role", back_populates="users")
    staff_profile = relationship("Staff", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")

class AcademicYear(Base):
    __tablename__ = "academic_years"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(20), unique=True, nullable=False)  # e.g., "2025/2026"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False)
    
    terms = relationship("Term", back_populates="academic_year", cascade="all, delete-orphan")
    attendance = relationship("Attendance", back_populates="academic_year")
    examinations = relationship("Examination", back_populates="academic_year")
    fees = relationship("Fee", back_populates="academic_year")

class Term(Base):
    __tablename__ = "terms"
    
    id = Column(Integer, primary_key=True, index=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(20), nullable=False)  # e.g., "Term 1", "Term 2", "Term 3"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_current = Column(Boolean, default=False)
    
    academic_year = relationship("AcademicYear", back_populates="terms")
    attendance = relationship("Attendance", back_populates="term")
    examinations = relationship("Examination", back_populates="term")
    fees = relationship("Fee", back_populates="term")

class Class(Base):
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)  # e.g., "Primary 1", "JHS 1"
    level = Column(String(20), nullable=False)  # e.g., "Kindergarten", "Primary", "JHS"
    stream = Column(String(20), nullable=True)  # e.g., "A", "B"
    
    students = relationship("Student", back_populates="class_assigned")
    teacher_assignments = relationship("TeacherSubject", back_populates="class_obj")
    class_teachers = relationship("ClassTeacher", back_populates="class_obj")
    results = relationship("Result", back_populates="class_obj")

class Parent(Base):
    __tablename__ = "parents"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    occupation = Column(String(100), nullable=True)
    address = Column(String(200), nullable=True)
    
    students = relationship("Student", back_populates="parent")

class Student(Base):
    __tablename__ = "students"
    
    id = Column(String(30), primary_key=True, index=True)  # e.g. SMS-2026-0001
    first_name = Column(String(50), nullable=False, index=True)
    last_name = Column(String(50), nullable=False, index=True)
    other_names = Column(String(100), nullable=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(10), nullable=False)
    admission_date = Column(Date, default=datetime.date.today)
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    parent_id = Column(Integer, ForeignKey("parents.id"), nullable=True)
    status = Column(String(20), default="Active")  # "Active", "Promoted", "Transferred", "Withdrawn", "Alumnus"
    photo_path = Column(String(255), nullable=True)
    medical_info = Column(Text, nullable=True)
    emergency_contact_name = Column(String(100), nullable=True)
    emergency_contact_phone = Column(String(20), nullable=True)
    
    class_assigned = relationship("Class", back_populates="students")
    parent = relationship("Parent", back_populates="students")
    attendance = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    results = relationship("Result", back_populates="student", cascade="all, delete-orphan")
    bills = relationship("StudentBill", back_populates="student", cascade="all, delete-orphan")
    library_issues = relationship("LibraryIssue", back_populates="student")

class Staff(Base):
    __tablename__ = "staff"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    first_name = Column(String(50), nullable=False, index=True)
    last_name = Column(String(50), nullable=False, index=True)
    other_names = Column(String(100), nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    phone = Column(String(20), nullable=False)
    role_title = Column(String(50), nullable=False)  # "Teacher", "Accountant", "Librarian", "Storekeeper"
    department = Column(String(50), nullable=True)
    hire_date = Column(Date, default=datetime.date.today)
    status = Column(String(20), default="Active")  # "Active", "Resigned", "Suspended"
    address = Column(String(200), nullable=True)
    photo_path = Column(String(255), nullable=True)
    qualification = Column(String(100), nullable=True)
    base_salary = Column(Float, default=0.0)
    
    user = relationship("User", back_populates="staff_profile")
    attendance = relationship("Attendance", back_populates="staff", cascade="all, delete-orphan")
    class_teachers = relationship("ClassTeacher", back_populates="staff", cascade="all, delete-orphan")
    subject_assignments = relationship("TeacherSubject", back_populates="staff", cascade="all, delete-orphan")
    payslips = relationship("Payslip", back_populates="staff", cascade="all, delete-orphan")

class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    class_level = Column(String(20), nullable=False)  # "Kindergarten", "Primary", "JHS"
    
    teacher_assignments = relationship("TeacherSubject", back_populates="subject")
    results = relationship("Result", back_populates="subject")

class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    
    staff = relationship("Staff", back_populates="subject_assignments")
    subject = relationship("Subject", back_populates="teacher_assignments")
    class_obj = relationship("Class", back_populates="teacher_assignments")

class ClassTeacher(Base):
    __tablename__ = "class_teachers"
    
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    
    class_obj = relationship("Class", back_populates="class_teachers")
    staff = relationship("Staff", back_populates="class_teachers")

class Attendance(Base):
    __tablename__ = "attendance"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    student_id = Column(String(30), ForeignKey("students.id", ondelete="CASCADE"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=True)
    status = Column(String(20), nullable=False)  # "Present", "Absent", "Late"
    remarks = Column(String(200), nullable=True)
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"))
    term_id = Column(Integer, ForeignKey("terms.id"))
    
    student = relationship("Student", back_populates="attendance")
    staff = relationship("Staff", back_populates="attendance")
    academic_year = relationship("AcademicYear", back_populates="attendance")
    term = relationship("Term", back_populates="attendance")

class Examination(Base):
    __tablename__ = "examinations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Term 1 Final Exam"
    academic_year_id = Column(Integer, ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id", ondelete="CASCADE"), nullable=False)
    exam_date = Column(Date, nullable=False)
    max_score = Column(Integer, default=100)
    
    academic_year = relationship("AcademicYear", back_populates="examinations")
    term = relationship("Term", back_populates="examinations")
    results = relationship("Result", back_populates="examination", cascade="all, delete-orphan")

class Result(Base):
    __tablename__ = "results"
    
    id = Column(Integer, primary_key=True, index=True)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(30), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    class_score = Column(Float, default=0.0)  # Continuous Assessment (e.g. 30%)
    exam_score = Column(Float, default=0.0)   # Examination Score (e.g. 70%)
    total_score = Column(Float, default=0.0)  # class_score + exam_score
    grade = Column(String(5), nullable=True)   # e.g. "A+", "1", "9"
    position = Column(Integer, nullable=True) # Rank of student in this subject/class
    remarks = Column(String(200), nullable=True)
    teacher_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    
    examination = relationship("Examination", back_populates="results")
    student = relationship("Student", back_populates="results")
    subject = relationship("Subject", back_populates="results")
    class_obj = relationship("Class", back_populates="results")

class Fee(Base):
    __tablename__ = "fees"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)  # e.g., "Tuition Fee", "PTA Levy", "Computer Lab Fee"
    amount = Column(Float, nullable=False)
    class_level = Column(String(50), nullable=False)  # "All", "Kindergarten", "Primary", "JHS"
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"))
    term_id = Column(Integer, ForeignKey("terms.id"))
    
    academic_year = relationship("AcademicYear", back_populates="fees")
    term = relationship("Term", back_populates="fees")
    student_bills = relationship("StudentBill", back_populates="fee", cascade="all, delete-orphan")

class StudentBill(Base):
    __tablename__ = "student_bills"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(30), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    fee_id = Column(Integer, ForeignKey("fees.id", ondelete="CASCADE"), nullable=False)
    amount_billed = Column(Float, nullable=False)
    amount_paid = Column(Float, default=0.0)
    status = Column(String(20), default="Unpaid")  # "Unpaid", "Partially Paid", "Paid"
    
    student = relationship("Student", back_populates="bills")
    fee = relationship("Fee", back_populates="student_bills")
    payments = relationship("Payment", back_populates="student_bill", cascade="all, delete-orphan")

class Payment(Base):
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    student_bill_id = Column(Integer, ForeignKey("student_bills.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    payment_date = Column(DateTime, default=datetime.datetime.utcnow)
    payment_method = Column(String(50), nullable=False)  # "Cash", "Mobile Money", "Bank Transfer", "Cheque"
    reference_no = Column(String(100), nullable=True)
    received_by = Column(Integer, ForeignKey("staff.id"), nullable=True)
    
    student_bill = relationship("StudentBill", back_populates="payments")

class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)  # "Asset" (desks, computers) or "Supply" (chalk, textbooks)
    description = Column(String(200), nullable=True)
    total_quantity = Column(Integer, default=0)
    available_quantity = Column(Integer, default=0)
    unit = Column(String(20), default="pcs")  # e.g., "pcs", "boxes", "books"
    condition = Column(String(50), nullable=True)  # "Good", "Needs Repair", "Damaged"
    location = Column(String(100), nullable=True)
    
    transactions = relationship("StockTransaction", back_populates="inventory_item", cascade="all, delete-orphan")

class StockTransaction(Base):
    __tablename__ = "stock_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    transaction_type = Column(String(10), nullable=False)  # "IN", "OUT"
    quantity = Column(Integer, nullable=False)
    transaction_date = Column(DateTime, default=datetime.datetime.utcnow)
    reference = Column(String(100), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id"), nullable=True)
    supplier_name = Column(String(100), nullable=True)
    
    inventory_item = relationship("Inventory", back_populates="transactions")

class LibraryBook(Base):
    __tablename__ = "library_books"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(150), nullable=False, index=True)
    author = Column(String(100), nullable=False)
    isbn = Column(String(20), nullable=True)
    category = Column(String(50), nullable=True)
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
    location = Column(String(50), nullable=True)  # e.g. Shelf A-3
    
    issues = relationship("LibraryIssue", back_populates="book")

class LibraryIssue(Base):
    __tablename__ = "library_issues"
    
    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("library_books.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(String(30), ForeignKey("students.id", ondelete="CASCADE"), nullable=True)
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=True)
    issue_date = Column(Date, default=datetime.date.today)
    due_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    fine_amount = Column(Float, default=0.0)
    fine_status = Column(String(20), default="None")  # "None", "Unpaid", "Paid"
    issued_by = Column(Integer, ForeignKey("staff.id"), nullable=True)
    
    book = relationship("LibraryBook", back_populates="issues")
    student = relationship("Student", back_populates="library_issues")

class Announcement(Base):
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    target_audience = Column(String(50), default="All")  # "All", "Teachers", "Parents", "Students"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    created_by = Column(Integer, ForeignKey("staff.id"), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)  # e.g. "Login", "Create Student", "Record Payment"
    table_name = Column(String(50), nullable=True)
    record_id = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    details = Column(Text, nullable=True)
    
    user = relationship("User", back_populates="audit_logs")

class TimetableSlot(Base):
    __tablename__ = "timetable_slots"
    
    id = Column(Integer, primary_key=True, index=True)
    class_id = Column(Integer, ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    day_of_week = Column(String(20), nullable=False)  # e.g., "Monday"
    time_slot = Column(String(50), nullable=False)    # e.g., "08:00 - 08:45"
    academic_year_id = Column(Integer, ForeignKey("academic_years.id"))
    term_id = Column(Integer, ForeignKey("terms.id"))
    
    class_obj = relationship("Class")
    subject = relationship("Subject")
    staff = relationship("Staff")

class Expense(Base):
    __tablename__ = "expenses"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)     # e.g., "Utilities", "Maintenance", "Salaries"
    amount = Column(Float, nullable=False)
    date = Column(Date, default=datetime.date.today)
    description = Column(Text, nullable=True)
    recorded_by = Column(Integer, ForeignKey("staff.id"), nullable=True)
    
    recorder = relationship("Staff")

class SMSLog(Base):
    __tablename__ = "sms_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_phone = Column(String(20), nullable=False)
    message_content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.datetime.utcnow)
    status = Column(String(20), default="Sent")        # "Sent", "Failed"
    trigger_type = Column(String(50), nullable=True)   # "Attendance", "Grades", "Notice", "Library"

class Payslip(Base):
    __tablename__ = "payslips"
    
    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("staff.id", ondelete="CASCADE"), nullable=False)
    pay_period = Column(String(30), nullable=False)  # e.g., "July 2026"
    base_salary = Column(Float, default=0.0)
    allowances = Column(Float, default=0.0)
    tax_deductions = Column(Float, default=0.0)  # PAYE tax
    pension_deductions = Column(Float, default=0.0)  # SSNIT pension
    net_salary = Column(Float, default=0.0)
    status = Column(String(20), default="Pending")  # "Paid", "Pending"
    payment_date = Column(Date, nullable=True)
    
    staff = relationship("Staff", back_populates="payslips")


class StudentReportRemark(Base):
    __tablename__ = "student_report_remarks"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String(30), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    examination_id = Column(Integer, ForeignKey("examinations.id", ondelete="CASCADE"), nullable=False)
    teacher_remark = Column(String(500), nullable=True)
    headteacher_remark = Column(String(500), nullable=True)
    
    student = relationship("Student")
    examination = relationship("Examination")


