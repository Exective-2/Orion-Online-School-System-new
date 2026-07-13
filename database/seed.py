import os
import hashlib
import datetime
from sqlalchemy.orm import Session
from database.connection import init_db, get_session
from database.models import (
    Role, Permission, User, AcademicYear, Term, Class, Parent, Student, 
    Staff, Subject, TeacherSubject, ClassTeacher, Attendance, Examination, 
    Result, Fee, StudentBill, Payment, Inventory, StockTransaction, 
    LibraryBook, LibraryIssue, Announcement, AuditLog, TimetableSlot, Expense, SMSLog
)

def hash_password(password: str) -> str:
    salt = os.urandom(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return salt.hex() + ":" + pwd_hash.hex()

def seed_database(seed_demo: bool = True):
    session = get_session()
    
    # Check if roles are already seeded
    if session.query(Role).first():
        print("Database already seeded.")
        session.close()
        return

    print("Seeding database...")

    # 1. Permissions
    permissions_list = [
        ("view_dashboard", "View the dashboard stats and graphs"),
        ("manage_students", "Admit, edit, promote, and withdraw students"),
        ("manage_staff", "Register and edit staff details, view performance"),
        ("manage_academics", "Setup academic years, terms, classes, and subjects"),
        ("manage_attendance", "Take daily attendance for students and staff"),
        ("manage_exams", "Set up examinations, enter scores, and generate report cards"),
        ("manage_fees", "Configure fee structures, record payments, and view finances"),
        ("manage_library", "Manage book registry and book borrowing logs"),
        ("manage_inventory", "Manage school assets and supplies stock list"),
        ("manage_communication", "Post school announcements and notices"),
        ("manage_settings", "Access system configurations, backups, and user settings"),
        ("view_reports", "Access student, financial, attendance, and academic reports")
    ]
    
    perms = {}
    for p_name, p_desc in permissions_list:
        perm = Permission(name=p_name, description=p_desc)
        session.add(perm)
        perms[p_name] = perm
    session.flush()

    # 2. Roles
    roles_permissions = {
        "Super Admin": list(perms.keys()),
        "Admin/Headteacher": ["view_dashboard", "manage_students", "manage_staff", "manage_academics", "manage_attendance", "manage_exams", "manage_library", "manage_inventory", "manage_communication", "manage_settings", "view_reports"],
        "Accountant": ["view_dashboard", "manage_fees", "view_reports"],
        "Librarian": ["view_dashboard", "manage_library", "view_reports"],
        "Storekeeper": ["view_dashboard", "manage_inventory", "view_reports"],
        "Teacher": ["view_dashboard", "manage_attendance", "manage_exams", "manage_communication", "view_reports"]
    }
    
    roles = {}
    for r_name, r_perms in roles_permissions.items():
        role = Role(name=r_name)
        session.add(role)
        for p_name in r_perms:
            role.permissions.append(perms[p_name])
        roles[r_name] = role
    session.flush()

    # 3. Users and Staff
    default_users = [
        ("admin", "admin123", "admin@orionschool.edu.gh", "Super Admin", "John", "Doe", "Admin Officer", "+233 24 111 2222"),
    ]
    if seed_demo:
        default_users += [
            ("headteacher", "head123", "head@orionschool.edu.gh", "Admin/Headteacher", "Kofi", "Mensah", "Headteacher", "+233 24 333 4444"),
            ("bursar", "bursar123", "bursar@orionschool.edu.gh", "Accountant", "Ama", "Osei", "Bursar", "+233 24 555 6666"),
            ("teacher_kwame", "teacher123", "kwame@orionschool.edu.gh", "Teacher", "Kwame", "Appiah", "Teacher", "+233 24 777 8888"),
            ("teacher_abena", "teacher123", "abena@orionschool.edu.gh", "Teacher", "Abena", "Ofori", "Teacher", "+233 24 999 0000"),
            ("librarian", "lib123", "librarian@orionschool.edu.gh", "Librarian", "Ekow", "Arthur", "Librarian", "+233 20 111 3333"),
            ("storekeeper", "store123", "store@orionschool.edu.gh", "Storekeeper", "Yao", "Dogbe", "Storekeeper", "+233 20 444 5555"),
        ]
    
    staff_objs = []
    for username, password, email, role_name, fname, lname, title, phone in default_users:
        user = User(
            username=username,
            password_hash=hash_password(password),
            email=email,
            role=roles[role_name]
        )
        session.add(user)
        session.flush()
        
        staff = Staff(
            user_id=user.id,
            first_name=fname,
            last_name=lname,
            email=email,
            phone=phone,
            role_title=title,
            department="Administration" if "Admin" in role_name or "Accountant" in role_name else "Academics" if "Teacher" in role_name else "Operations",
            hire_date=datetime.date(2023, 1, 15)
        )
        session.add(staff)
        staff_objs.append(staff)
    session.flush()

    # 4. Academic Years and Terms
    ay_2025_2026 = AcademicYear(
        name="2025/2026",
        start_date=datetime.date(2025, 9, 1),
        end_date=datetime.date(2026, 7, 31),
        is_current=True
    )
    session.add(ay_2025_2026)
    session.flush()
    
    t1 = Term(academic_year_id=ay_2025_2026.id, name="Term 1", start_date=datetime.date(2025, 9, 1), end_date=datetime.date(2025, 12, 18), is_current=True)
    t2 = Term(academic_year_id=ay_2025_2026.id, name="Term 2", start_date=datetime.date(2026, 1, 6), end_date=datetime.date(2026, 4, 9), is_current=False)
    t3 = Term(academic_year_id=ay_2025_2026.id, name="Term 3", start_date=datetime.date(2026, 5, 5), end_date=datetime.date(2026, 7, 24), is_current=False)
    session.add_all([t1, t2, t3])
    session.flush()

    # 5. Classes and Streams
    classes_list = [
        ("Kindergarten 1", "Kindergarten", "A"),
        ("Kindergarten 2", "Kindergarten", "A"),
        ("Primary 1", "Primary", "A"),
        ("Primary 2", "Primary", "A"),
        ("Primary 3", "Primary", "A"),
        ("Primary 4", "Primary", "A"),
        ("Primary 5", "Primary", "A"),
        ("Primary 6", "Primary", "A"),
        ("JHS 1", "JHS", "A"),
        ("JHS 2", "JHS", "A"),
        ("JHS 3", "JHS", "A")
    ]
    
    classes_map = {}
    for c_name, c_level, c_stream in classes_list:
        cls = Class(name=c_name, level=c_level, stream=c_stream)
        session.add(cls)
        classes_map[c_name] = cls
    session.flush()

    # Assign class teachers
    if seed_demo:
        ct1 = ClassTeacher(class_id=classes_map["JHS 1"].id, staff_id=staff_objs[3].id, academic_year_id=ay_2025_2026.id) # Kwame Appiah class teacher of JHS 1
        ct2 = ClassTeacher(class_id=classes_map["JHS 2"].id, staff_id=staff_objs[4].id, academic_year_id=ay_2025_2026.id) # Abena Ofori class teacher of JHS 2
        session.add_all([ct1, ct2])

    # 6. Subjects
    subjects_list = [
        ("Mathematics", "MATH-JHS", "JHS"),
        ("English Language", "ENG-JHS", "JHS"),
        ("Integrated Science", "SCI-JHS", "JHS"),
        ("Social Studies", "SOC-JHS", "JHS"),
        ("Computing", "COMP-JHS", "JHS"),
        ("Religious and Moral Education (RME)", "RME-JHS", "JHS"),
        ("Ghanaian Language (Twi)", "TWI-JHS", "JHS"),
        
        ("Mathematics", "MATH-PRI", "Primary"),
        ("English Language", "ENG-PRI", "Primary"),
        ("Science", "SCI-PRI", "Primary"),
        ("ICT", "COMP-PRI", "Primary"),
        
        ("Numeracy", "NUM-KG", "Kindergarten"),
        ("Literacy", "LIT-KG", "Kindergarten"),
        ("Creative Activities", "ART-KG", "Kindergarten")
    ]
    
    subjects_map = {}
    for s_name, s_code, s_level in subjects_list:
        sub = Subject(name=s_name, code=s_code, class_level=s_level)
        session.add(sub)
        subjects_map[s_code] = sub
    session.flush()

    # Assign teacher subjects
    if seed_demo:
        ts1 = TeacherSubject(staff_id=staff_objs[3].id, subject_id=subjects_map["MATH-JHS"].id, class_id=classes_map["JHS 1"].id)
        ts2 = TeacherSubject(staff_id=staff_objs[3].id, subject_id=subjects_map["SCI-JHS"].id, class_id=classes_map["JHS 1"].id)
        ts3 = TeacherSubject(staff_id=staff_objs[4].id, subject_id=subjects_map["ENG-JHS"].id, class_id=classes_map["JHS 1"].id)
        ts4 = TeacherSubject(staff_id=staff_objs[4].id, subject_id=subjects_map["SOC-JHS"].id, class_id=classes_map["JHS 1"].id)
        ts5 = TeacherSubject(staff_id=staff_objs[3].id, subject_id=subjects_map["MATH-JHS"].id, class_id=classes_map["JHS 2"].id)
        ts6 = TeacherSubject(staff_id=staff_objs[4].id, subject_id=subjects_map["ENG-JHS"].id, class_id=classes_map["JHS 2"].id)
        session.add_all([ts1, ts2, ts3, ts4, ts5, ts6])
        session.flush()

    if not seed_demo:
        audit = AuditLog(
            user_id=1,
            action="Database Initialize",
            table_name="All",
            details="Initial system setup and database seeder run completed successfully (Fresh Install)."
        )
        session.add(audit)
        session.commit()
        session.close()
        print("Database seeding (fresh) completed successfully.")
        return

    # 7. Parents
    parents_data = [
        ("Emmanuel", "Owusu", "+233 24 100 2001", "owusu@gmail.com", "Engineer", "12 Ring Road, Accra"),
        ("Theresa", "Acheampong", "+233 24 100 2002", "theresa@hotmail.com", "Trader", "Kaneshie Market, Accra"),
        ("George", "Adjei", "+233 24 100 2003", "georgeadjei@outlook.com", "Civil Servant", "Block C, Airport Residential Area"),
        ("Patricia", "Lartey", "+233 20 100 2004", None, "Nurse", "Ridge Hospital Staff Quarters"),
        ("David", "Annan", "+233 50 100 2005", "dannan@yahoo.com", "Business Man", "East Legon, Accra"),
    ]
    
    parent_objs = []
    for fname, lname, phone, email, occ, addr in parents_data:
        parent = Parent(first_name=fname, last_name=lname, phone=phone, email=email, occupation=occ, address=addr)
        session.add(parent)
        parent_objs.append(parent)
    session.flush()

    # 8. Students
    students_data = [
        # (id, first_name, last_name, gender, dob, class_name, parent_index)
        ("SMS-2025-0001", "Prince", "Owusu", "Male", datetime.date(2013, 5, 12), "JHS 1", 0),
        ("SMS-2025-0002", "Grace", "Owusu", "Female", datetime.date(2015, 8, 20), "Primary 5", 0),
        ("SMS-2025-0003", "Kofi", "Acheampong", "Male", datetime.date(2012, 11, 30), "JHS 2", 1),
        ("SMS-2025-0004", "Akosua", "Acheampong", "Female", datetime.date(2017, 2, 14), "Primary 3", 1),
        ("SMS-2025-0005", "Ebenezer", "Adjei", "Male", datetime.date(2013, 3, 22), "JHS 1", 2),
        ("SMS-2025-0006", "Mary", "Adjei", "Female", datetime.date(2018, 6, 18), "Primary 1", 2),
        ("SMS-2025-0007", "Samuel", "Lartey", "Male", datetime.date(2014, 10, 5), "Primary 6", 3),
        ("SMS-2025-0008", "Blessing", "Annan", "Female", datetime.date(2020, 1, 29), "Kindergarten 2", 4),
        ("SMS-2025-0009", "Daniel", "Annan", "Male", datetime.date(2014, 4, 1), "Primary 6", 4),
        ("SMS-2025-0010", "Michael", "Annan", "Male", datetime.date(2013, 9, 15), "JHS 1", 4)
    ]
    
    student_objs = []
    for sid, fname, lname, gen, dob, c_name, p_idx in students_data:
        student = Student(
            id=sid,
            first_name=fname,
            last_name=lname,
            gender=gen,
            date_of_birth=dob,
            class_id=classes_map[c_name].id,
            parent_id=parent_objs[p_idx].id,
            admission_date=datetime.date(2025, 9, 1),
            status="Active"
        )
        session.add(student)
        student_objs.append(student)
    session.flush()

    # 9. Attendance Logs
    # Attendance for the last 5 days
    today = datetime.date.today()
    for offset in range(5):
        date_val = today - datetime.timedelta(days=offset)
        # Skip weekends
        if date_val.weekday() >= 5:
            continue
        
        # Student attendance
        for student in student_objs:
            # Randomly make a student absent or late with low probability
            import random
            val = random.random()
            status = "Present"
            remarks = "On time"
            if val < 0.05:
                status = "Absent"
                remarks = "Sick leave"
            elif val < 0.15:
                status = "Late"
                remarks = "Late by 15 mins"
                
            att = Attendance(
                date=date_val,
                student_id=student.id,
                status=status,
                remarks=remarks,
                academic_year_id=ay_2025_2026.id,
                term_id=t1.id
            )
            session.add(att)
            
        # Staff attendance
        for staff in staff_objs:
            val = random.random()
            status = "Present"
            remarks = ""
            if val < 0.02:
                status = "Absent"
                remarks = "Official permission"
            elif val < 0.08:
                status = "Late"
                remarks = "Traffic delay"
            
            att = Attendance(
                date=date_val,
                staff_id=staff.id,
                status=status,
                remarks=remarks,
                academic_year_id=ay_2025_2026.id,
                term_id=t1.id
            )
            session.add(att)
    session.flush()

    # 10. Examinations and Results
    exam_t1 = Examination(
        name="Term 1 Examinations",
        academic_year_id=ay_2025_2026.id,
        term_id=t1.id,
        exam_date=datetime.date(2025, 12, 10),
        max_score=100
    )
    session.add(exam_t1)
    session.flush()

    # Grade boundary helper for Ghana Education Service:
    # 80-100: 1 (Highest - Excellent)
    # 70-79: 2 (Very Good)
    # 65-69: 3 (Good)
    # 60-64: 4 (Credit - Above Average)
    # 55-59: 5 (Credit - Average)
    # 50-54: 6 (Pass)
    # 45-49: 7 (Pass - Weak)
    # 40-44: 8 (Pass - Very Weak)
    # 0-39: 9 (Fail)
    def compute_ges_grade(score):
        if score >= 80: return "1"
        elif score >= 70: return "2"
        elif score >= 65: return "3"
        elif score >= 60: return "4"
        elif score >= 55: return "5"
        elif score >= 50: return "6"
        elif score >= 45: return "7"
        elif score >= 40: return "8"
        else: return "9"

    # Seed JHS 1 results (student IDs: SMS-2025-0001, SMS-2025-0005, SMS-2025-0010)
    jhs1_students = [student_objs[0], student_objs[4], student_objs[9]]
    jhs1_subjects = [subjects_map["MATH-JHS"], subjects_map["ENG-JHS"], subjects_map["SCI-JHS"], subjects_map["SOC-JHS"]]
    
    # Mock scores
    scores_pool = {
        "SMS-2025-0001": [(25, 62), (28, 68), (22, 58), (26, 65)], # Math, Eng, Sci, Soc
        "SMS-2025-0005": [(18, 48), (20, 52), (19, 45), (21, 50)],
        "SMS-2025-0010": [(27, 65), (29, 69), (26, 64), (28, 68)]
    }

    for student in jhs1_students:
        pool = scores_pool[student.id]
        for idx, sub in enumerate(jhs1_subjects):
            class_score, exam_score = pool[idx]
            total = class_score + exam_score
            grade = compute_ges_grade(total)
            
            res = Result(
                examination_id=exam_t1.id,
                student_id=student.id,
                subject_id=sub.id,
                class_id=classes_map["JHS 1"].id,
                class_score=class_score,
                exam_score=exam_score,
                total_score=total,
                grade=grade,
                remarks="Excellent performance" if total >= 80 else "Very good" if total >= 70 else "Pass" if total >= 50 else "Needs improvement",
                teacher_id=staff_objs[3].id if sub.code in ["MATH-JHS", "SCI-JHS"] else staff_objs[4].id
            )
            session.add(res)
    session.flush()

    # 11. Fees, Invoices, and Payments
    fees_list = [
        ("Tuition Fee", 600.0, "All"),
        ("ICT Laboratory Levy", 100.0, "JHS"),
        ("ICT Laboratory Levy", 50.0, "Primary"),
        ("PTA Dues", 50.0, "All")
    ]
    
    fee_objs = []
    for f_name, f_amt, f_lvl in fees_list:
        fee = Fee(name=f_name, amount=f_amt, class_level=f_lvl, academic_year_id=ay_2025_2026.id, term_id=t1.id)
        session.add(fee)
        fee_objs.append(fee)
    session.flush()

    # Bill students
    for student in student_objs:
        cls_obj = session.query(Class).filter(Class.id == student.class_id).first()
        for fee in fee_objs:
            # Apply class level filters
            if fee.class_level == "All" or fee.class_level == cls_obj.level:
                bill = StudentBill(
                    student_id=student.id,
                    fee_id=fee.id,
                    amount_billed=fee.amount,
                    amount_paid=0.0,
                    status="Unpaid"
                )
                session.add(bill)
    session.flush()

    # Record some payments
    # Let's pay half of the bills for Prince Owusu (SMS-2025-0001) and full for Kofi Acheampong (SMS-2025-0003)
    prince_bills = session.query(StudentBill).filter(StudentBill.student_id == "SMS-2025-0001").all()
    for bill in prince_bills:
        amount_to_pay = bill.amount_billed * 0.6
        bill.amount_paid = amount_to_pay
        bill.status = "Partially Paid"
        
        pay = Payment(
            student_bill_id=bill.id,
            amount=amount_to_pay,
            payment_method="Mobile Money",
            reference_no="MM-TXN-902341",
            received_by=staff_objs[2].id # Bursar
        )
        session.add(pay)
        
    kofi_bills = session.query(StudentBill).filter(StudentBill.student_id == "SMS-2025-0003").all()
    for bill in kofi_bills:
        amount_to_pay = bill.amount_billed
        bill.amount_paid = amount_to_pay
        bill.status = "Paid"
        
        pay = Payment(
            student_bill_id=bill.id,
            amount=amount_to_pay,
            payment_method="Cash",
            reference_no="CSH-REC-89012",
            received_by=staff_objs[2].id
        )
        session.add(pay)
    session.flush()

    # 12. Library Books
    library_books = [
        ("Standard Integrated Science for JHS 1", "A. A. Danquah", "978-9988-12-1", "Textbook", 15, 15, "Shelf A-1"),
        ("Core Mathematics for Basic Schools", "E. K. Boadi", "978-9988-12-2", "Textbook", 20, 19, "Shelf A-2"),
        ("Standard English Grammar & Composition", "Patricia Appiah", "978-9988-12-3", "General Study", 10, 10, "Shelf B-1"),
        ("Chaka the Zulu", "Thomas Mofolo", "978-0195-71-4", "Literature", 5, 4, "Shelf C-2"),
    ]
    
    book_objs = []
    for title, author, isbn, cat, copies, avail, loc in library_books:
        book = LibraryBook(title=title, author=author, isbn=isbn, category=cat, total_copies=copies, available_copies=avail, location=loc)
        session.add(book)
        book_objs.append(book)
    session.flush()

    # Book issues
    li1 = LibraryIssue(
        book_id=book_objs[1].id, # Core Math
        student_id="SMS-2025-0001",
        issue_date=today - datetime.timedelta(days=7),
        due_date=today + datetime.timedelta(days=7),
        issued_by=staff_objs[5].id # Librarian
    )
    li2 = LibraryIssue(
        book_id=book_objs[3].id, # Chaka Zulu
        student_id="SMS-2025-0003",
        issue_date=today - datetime.timedelta(days=12),
        due_date=today - datetime.timedelta(days=5),  # Overdue!
        issued_by=staff_objs[5].id
    )
    session.add_all([li1, li2])
    session.flush()

    # 13. Inventory items
    inventory_items = [
        ("Wooden Desk & Bench Combo", "Asset", "Combined school desk and bench", 150, 150, "pcs", "Good", "Classrooms"),
        ("Dell OptiPlex Desktop Computers", "Asset", "ICT Lab computers for students", 25, 25, "pcs", "Good", "ICT Lab"),
        ("Whiteboard Markers (Blue)", "Supply", "Dry erase markers for whiteboards", 50, 35, "boxes", "Good", "Store Room 1"),
        ("Chalk Boxes (White)", "Supply", "Dustless chalk boxes", 20, 20, "boxes", "Good", "Store Room 1"),
        ("Junior High Mathematics Textbook Grade 7", "Supply", "Textbooks distributed to students", 60, 10, "books", "Good", "Library Store"),
    ]
    
    inv_objs = []
    for name, cat, desc, qty, avail, unit, cond, loc in inventory_items:
        inv = Inventory(item_name=name, category=cat, description=desc, total_quantity=qty, available_quantity=avail, unit=unit, condition=cond, location=loc)
        session.add(inv)
        inv_objs.append(inv)
    session.flush()

    # Log initial stock transactions
    for inv in inv_objs:
        st = StockTransaction(
            inventory_id=inv.id,
            transaction_type="IN",
            quantity=inv.total_quantity,
            reference="Initial stock upload",
            staff_id=staff_objs[6].id, # Storekeeper
            supplier_name="GES Supply Depot / Kingdom Books"
        )
        session.add(st)
    session.flush()

    # 14. Announcements
    announcements = [
        ("PTA General Meeting", "Dear Parents, there will be a general PTA meeting on Friday, 18th July 2026, at 2:00 PM in the School Assembly Hall. We will discuss the new school grading dashboard, fees schedule, and upcoming term projects. Attendance is highly encouraged.", "Parents"),
        ("Term Re-opening Notice", "Staff and students are reminded that Term 1 of the 2025/2026 academic year reopens officially on Tuesday, 2nd September 2025. Please ensure all classroom materials are prepared.", "All"),
        ("Continuous Assessment Entries Due", "Teachers are kindly requested to complete and submit all Continuous Assessment (30% weight) records for the current term by Friday, 5th December 2025.", "Teachers")
    ]
    
    for title, content, target in announcements:
        ann = Announcement(
            title=title,
            content=content,
            target_audience=target,
            created_at=datetime.datetime.utcnow() - datetime.timedelta(days=1),
            created_by=staff_objs[1].id # Headteacher
        )
        session.add(ann)
        
    # 16. Timetables
    tt1 = TimetableSlot(
        class_id=classes_map["JHS 1"].id,
        subject_id=subjects_map["MATH-JHS"].id,
        staff_id=staff_objs[3].id, # Kwame Appiah
        day_of_week="Monday",
        time_slot="08:00 - 08:45",
        academic_year_id=ay_2025_2026.id,
        term_id=t1.id
    )
    tt2 = TimetableSlot(
        class_id=classes_map["JHS 1"].id,
        subject_id=subjects_map["SCI-JHS"].id,
        staff_id=staff_objs[3].id, # Kwame Appiah
        day_of_week="Monday",
        time_slot="08:45 - 09:30",
        academic_year_id=ay_2025_2026.id,
        term_id=t1.id
    )
    tt3 = TimetableSlot(
        class_id=classes_map["JHS 1"].id,
        subject_id=subjects_map["ENG-JHS"].id,
        staff_id=staff_objs[4].id, # Abena Ofori
        day_of_week="Tuesday",
        time_slot="08:00 - 08:45",
        academic_year_id=ay_2025_2026.id,
        term_id=t1.id
    )
    session.add_all([tt1, tt2, tt3])

    # 17. Expenses
    exp1 = Expense(title="Electricity Prepaid Credit", category="Utilities", amount=350.0, description="Monthly prepaid recharge for JHS block and admin office", recorded_by=staff_objs[2].id)
    exp2 = Expense(title="Whiteboard Cleaners & Dusters", category="Maintenance", amount=120.0, description="Purchase of dusters and cleaner spray", recorded_by=staff_objs[2].id)
    session.add_all([exp1, exp2])

    # 18. SMS Logs
    sms1 = SMSLog(recipient_phone="+233241002001", message_content="Orion SMS Notice: Prince Owusu was marked PRESENT today.", status="Sent", trigger_type="Attendance")
    sms2 = SMSLog(recipient_phone="+233241002002", message_content="Orion SMS Notice: Grace Owusu was marked PRESENT today.", status="Sent", trigger_type="Attendance")
    session.add_all([sms1, sms2])
        
    # 15. Audit Logs
    audit = AuditLog(
        user_id=1,
        action="Database Initialize",
        table_name="All",
        details="Initial system setup and database seeder run completed successfully."
    )
    session.add(audit)
    
    session.commit()
    session.close()
    print("Database seeding completed successfully.")

def seed_fresh_branch(branch_db_path, branch_name: str = "New Branch") -> bool:
    """
    Minimal seed for a brand-new branch database.

    Creates the full schema (roles, permissions, system classes, default
    academic year) but NO demo students, staff, fees, or attendance data.
    The branch admin account is created separately via the System Admin Portal.

    Parameters
    ----------
    branch_db_path : str or pathlib.Path
        Absolute path to the new branch's SQLite file.
    branch_name : str
        Used in the audit log entry only.

    Returns
    -------
    bool  True on success, False on failure.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import NullPool
    from database.models import Base

    try:
        engine = create_engine(
            f"sqlite:///{branch_db_path}",
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
            echo=False,
        )
        Base.metadata.create_all(bind=engine)

        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()

        # Guard: already seeded?
        if session.query(Role).first():
            session.close()
            engine.dispose()
            return True

        # 1. Permissions
        permissions_list = [
            ("view_dashboard", "View the dashboard stats and graphs"),
            ("manage_students", "Admit, edit, promote, and withdraw students"),
            ("manage_staff", "Register and edit staff details, view performance"),
            ("manage_academics", "Setup academic years, terms, classes, and subjects"),
            ("manage_attendance", "Take daily attendance for students and staff"),
            ("manage_exams", "Set up examinations, enter scores, and generate report cards"),
            ("manage_fees", "Configure fee structures, record payments, and view finances"),
            ("manage_library", "Manage book registry and book borrowing logs"),
            ("manage_inventory", "Manage school assets and supplies stock list"),
            ("manage_communication", "Post school announcements and notices"),
            ("manage_settings", "Access system configurations, backups, and user settings"),
            ("view_reports", "Access student, financial, attendance, and academic reports"),
        ]
        perms = {}
        for p_name, p_desc in permissions_list:
            perm = Permission(name=p_name, description=p_desc)
            session.add(perm)
            perms[p_name] = perm
        session.flush()

        # 2. Roles
        roles_permissions = {
            "Super Admin": list(perms.keys()),
            "Admin/Headteacher": [
                "view_dashboard", "manage_students", "manage_staff", "manage_academics",
                "manage_attendance", "manage_exams", "manage_library", "manage_inventory",
                "manage_communication", "manage_settings", "view_reports",
            ],
            "Accountant": ["view_dashboard", "manage_fees", "view_reports"],
            "Librarian": ["view_dashboard", "manage_library", "view_reports"],
            "Storekeeper": ["view_dashboard", "manage_inventory", "view_reports"],
            "Teacher": ["view_dashboard", "manage_attendance", "manage_exams", "manage_communication", "view_reports"],
        }
        roles = {}
        for r_name, r_perms in roles_permissions.items():
            role = Role(name=r_name)
            session.add(role)
            for p_name in r_perms:
                role.permissions.append(perms[p_name])
            roles[r_name] = role
        session.flush()

        # 3. Default academic year (current calendar year)
        import datetime as _dt
        year = _dt.date.today().year
        ay = AcademicYear(
            name=f"{year}/{year + 1}",
            start_date=_dt.date(year, 9, 1),
            end_date=_dt.date(year + 1, 7, 31),
            is_current=True,
        )
        session.add(ay)
        session.flush()

        t1 = Term(academic_year_id=ay.id, name="Term 1",
                  start_date=_dt.date(year, 9, 1), end_date=_dt.date(year, 12, 18), is_current=True)
        t2 = Term(academic_year_id=ay.id, name="Term 2",
                  start_date=_dt.date(year + 1, 1, 6), end_date=_dt.date(year + 1, 4, 9), is_current=False)
        t3 = Term(academic_year_id=ay.id, name="Term 3",
                  start_date=_dt.date(year + 1, 5, 5), end_date=_dt.date(year + 1, 7, 24), is_current=False)
        session.add_all([t1, t2, t3])
        session.flush()

        # 4. Standard classes
        classes_list = [
            ("Kindergarten 1", "Kindergarten", "A"),
            ("Kindergarten 2", "Kindergarten", "A"),
            ("Primary 1", "Primary", "A"), ("Primary 2", "Primary", "A"),
            ("Primary 3", "Primary", "A"), ("Primary 4", "Primary", "A"),
            ("Primary 5", "Primary", "A"), ("Primary 6", "Primary", "A"),
            ("JHS 1", "JHS", "A"), ("JHS 2", "JHS", "A"), ("JHS 3", "JHS", "A"),
        ]
        for c_name, c_level, c_stream in classes_list:
            session.add(Class(name=c_name, level=c_level, stream=c_stream))
        session.flush()

        # 5. Standard subjects
        subjects_list = [
            ("Mathematics", "MATH-JHS", "JHS"), ("English Language", "ENG-JHS", "JHS"),
            ("Integrated Science", "SCI-JHS", "JHS"), ("Social Studies", "SOC-JHS", "JHS"),
            ("Computing", "COMP-JHS", "JHS"), ("Religious and Moral Education (RME)", "RME-JHS", "JHS"),
            ("Ghanaian Language (Twi)", "TWI-JHS", "JHS"),
            ("Mathematics", "MATH-PRI", "Primary"), ("English Language", "ENG-PRI", "Primary"),
            ("Science", "SCI-PRI", "Primary"), ("ICT", "COMP-PRI", "Primary"),
            ("Numeracy", "NUM-KG", "Kindergarten"), ("Literacy", "LIT-KG", "Kindergarten"),
            ("Creative Activities", "ART-KG", "Kindergarten"),
        ]
        for s_name, s_code, s_level in subjects_list:
            session.add(Subject(name=s_name, code=s_code, class_level=s_level))
        session.flush()

        # 6. Audit log
        session.add(AuditLog(
            user_id=None,
            action="Branch Initialize",
            table_name="All",
            details=f"Fresh branch database initialized for '{branch_name}'. No demo data seeded.",
        ))

        session.commit()
        session.close()
        engine.dispose()
        print(f"[seed] Fresh branch seeded: {branch_db_path}")
        return True

    except Exception as e:
        print(f"[seed] seed_fresh_branch error: {e}")
        return False


if __name__ == "__main__":
    init_db()
    seed_database()
