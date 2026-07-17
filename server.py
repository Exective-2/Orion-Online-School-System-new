import os
import sys
import jwt
import hashlib
import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, status, Header, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from database.connection import get_session, init_db, current_db_url
from database.master_connection import get_master_session, init_master_defaults
from database.master_models import Branch, SystemAdmin, BranchAdmin
from database.models import (
    User, Role, Permission, Student, Parent, Class, Staff, Subject,
    TeacherSubject, ClassTeacher, Attendance, Examination, Result, Fee,
    StudentBill, Payment, LibraryBook, LibraryIssue, Inventory, StockTransaction,
    Announcement, AuditLog, SMSLog
)
from database.seed import hash_password, seed_database
from config import config, DATA_DIR, save_config
from utils.sms_sender import send_sms
from utils.pdf_generator import (
    generate_student_id_card, generate_admission_form, generate_fee_receipt,
    generate_report_card, generate_class_report_cards, generate_financial_statement,
    generate_class_summary_pdf, generate_attendance_report_pdf, generate_timetable_pdf,
    generate_inventory_report_pdf, generate_library_report_pdf
)
from utils.backup import run_auto_backup

# --- Configuration & Constants ---
JWT_SECRET = "orion-super-secret-key-12345!@#$"
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

app = FastAPI(title="Orion School Management System API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize master defaults on load
try:
    init_master_defaults()
except Exception as e:
    print(f"Failed to init master db defaults: {e}")

# --- Cache & Helper Functions ---
_branch_db_cache = {}

def get_branch_db_filename(branch_id: int) -> Optional[str]:
    if branch_id in _branch_db_cache:
        return _branch_db_cache[branch_id]
    
    session = get_master_session()
    try:
        branch = session.query(Branch).filter(Branch.id == branch_id).first()
        if branch:
            _branch_db_cache[branch_id] = branch.db_filename
            return branch.db_filename
    except Exception as e:
        print(f"Error resolving branch DB filename: {e}")
    finally:
        session.close()
    return None

def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        salt_hex, hash_hex = stored_password.split(":")
        salt = bytes.fromhex(salt_hex)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return pwd_hash.hex() == hash_hex
    except Exception:
        return False

# --- Middleware: Multi-Tenancy Request Context ---
@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    # Exclude public or setup endpoints from requiring a tenant DB context
    path = request.url.path
    if path.startswith("/static") or path in ["/", "/index.html"] or path.startswith("/web"):
        return await call_next(request)
        
    auth_header = request.headers.get("Authorization")
    db_url = None
    if auth_header and auth_header.startswith("Bearer "):
        token_str = auth_header[7:]
        try:
            payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            branch_id = payload.get("branch_id")
            if branch_id:
                db_filename = get_branch_db_filename(branch_id)
                if db_filename:
                    db_url = f"sqlite:///{DATA_DIR}/{db_filename}"
        except Exception:
            pass
            
    # Set thread/async context var
    token = current_db_url.set(db_url)
    try:
        response = await call_next(request)
        return response
    finally:
        current_db_url.reset(token)

# --- JWT Auth Dependency ---
async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    token_str = authorization[7:]
    try:
        payload = jwt.decode(token_str, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")

def log_audit(user_payload: dict, action: str, details: str):
    """Write an entry to the current branch audit log."""
    # Only logs if we are in a branch context
    if not user_payload.get("branch_id"):
        return
    session = get_session()
    try:
        log = AuditLog(
            user_id=user_payload.get("user_id"),
            action=action,
            details=details,
            ip_address="Web Interface",
            timestamp=datetime.datetime.utcnow()
        )
        session.add(log)
        session.commit()
    except Exception as e:
        print(f"Failed to log audit event: {e}")
    finally:
        session.close()

# --- Pydantic Schemes ---
class LoginRequest(BaseModel):
    username: str
    password: str
    branch_id: Optional[int] = None

class SetupRequest(BaseModel):
    school_name: str
    school_motto: str
    school_phone: str
    school_email: str
    school_address: str
    admin_user: str
    admin_pass: str
    academic_year: str
    term_name: str

class BranchCreate(BaseModel):
    name: str
    code: str
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    notes: Optional[str] = ""
    head_username: str
    head_password: str
    head_full_name: str
    head_email: Optional[str] = ""

class BranchUpdate(BaseModel):
    name: str
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    is_active: bool
    notes: Optional[str] = ""

class SystemAdminCreate(BaseModel):
    username: str
    password: str
    full_name: str
    email: Optional[str] = ""

# --- API Routing ---

# --- public endpoints ---
@app.get("/api/auth/branches")
def get_branches():
    session = get_master_session()
    try:
        branches = session.query(Branch).filter(Branch.is_active == True).order_by(Branch.name).all()
        return [{"id": b.id, "name": b.name, "code": b.code} for b in branches]
    finally:
        session.close()

@app.post("/api/auth/login")
def login(req: LoginRequest):
    username = req.username.strip()
    password = req.password.strip()
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required")
        
    # 1. Try System Admin Login (stored in Master DB)
    m_session = get_master_session()
    try:
        sysadmin = m_session.query(SystemAdmin).filter(
            SystemAdmin.username == username,
            SystemAdmin.is_active == True
        ).first()
        if sysadmin and verify_password(sysadmin.password_hash, password):
            # Generate Token
            payload = {
                "username": sysadmin.username,
                "user_id": sysadmin.id,
                "full_name": sysadmin.full_name,
                "branch_id": None,
                "role": "System Admin",
                "permissions": ["all"],
                "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            }
            token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
            return {"token": token, "role": "System Admin", "full_name": sysadmin.full_name, "branch_id": None}
    finally:
        m_session.close()

    # 2. Try Branch Login
    branches = []
    m_session = get_master_session()
    try:
        if req.branch_id:
            br = m_session.query(Branch).filter(Branch.id == req.branch_id, Branch.is_active == True).first()
            if br:
                branches = [br]
        else:
            branches = m_session.query(Branch).filter(Branch.is_active == True).all()
    finally:
        m_session.close()
        
    for br in branches:
        # Check this branch db
        db_path = DATA_DIR / br.db_filename
        if not db_path.exists():
            continue
            
        token = current_db_url.set(f"sqlite:///{db_path}")
        try:
            b_session = get_session()
            user = (
                b_session.query(User)
                .filter(User.username == username, User.is_active == True)
                .first()
            )
            if user and verify_password(user.password_hash, password):
                perms = [p.name for p in user.role.permissions] if user.role else []
                payload = {
                    "username": user.username,
                    "user_id": user.id,
                    "full_name": f"{user.staff_profile.first_name} {user.staff_profile.last_name}" if user.staff_profile else user.username,
                    "branch_id": br.id,
                    "branch_name": br.name,
                    "role": user.role.name if user.role else "Staff",
                    "permissions": perms,
                    "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
                }
                token_str = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
                # Audit log in branch db
                log_audit(payload, "Login", f"User logged in from Web UI")
                return {
                    "token": token_str,
                    "role": user.role.name if user.role else "Staff",
                    "full_name": payload["full_name"],
                    "branch_id": br.id,
                    "branch_name": br.name
                }
        except Exception as e:
            print(f"Error checking branch {br.name}: {e}")
        finally:
            current_db_url.reset(token)
            
    raise HTTPException(status_code=401, detail="Invalid credentials or inactive account")

@app.get("/api/setup/status")
def setup_status():
    return {"setup_completed": config.get("setup_completed", False)}

@app.post("/api/setup/execute")
def run_setup(req: SetupRequest):
    if config.get("setup_completed", False):
        raise HTTPException(status_code=400, detail="Setup has already been completed.")
        
    # 1. Update config
    config["school_name"] = req.school_name
    config["school_motto"] = req.school_motto
    config["school_phone"] = req.school_phone
    config["school_email"] = req.school_email
    config["school_address"] = req.school_address
    config["setup_completed"] = True
    save_config(config)
    
    # 2. Initialize Branch database schemas
    try:
        init_db()
        seed_database(seed_demo=True)
        
        # Override seeded super admin password/username if provided
        session = get_session()
        try:
            admin_user = session.query(User).filter(User.username == "admin").first()
            if admin_user:
                if req.admin_user != "admin":
                    admin_user.username = req.admin_user
                admin_user.password_hash = hash_password(req.admin_pass)
                session.commit()
        finally:
            session.close()
            
        # Re-init master to bind the newly setup database as Branch #1
        init_master_defaults()
        
        return {"status": "success", "message": "School setup wizard completed successfully!"}
    except Exception as e:
        config["setup_completed"] = False
        save_config(config)
        raise HTTPException(status_code=500, detail=f"Setup failed: {e}")

# --- Dashboard API ---
@app.get("/api/dashboard/stats")
def dashboard_stats(user=Depends(get_current_user)):
    session = get_session()
    try:
        active_students = session.query(Student).filter(Student.status == "Active").count()
        staff_count = session.query(Staff).filter(Staff.status == "Active").count()
        library_books = session.query(LibraryBook).count()
        
        # Financial summary: Total payments made
        payments = session.query(Payment).all()
        total_collected = sum(p.amount for p in payments)
        
        # Billing details
        billed_sum = session.query(StudentBill.amount_billed).all()
        paid_sum = session.query(StudentBill.amount_paid).all()
        total_billed = sum(b[0] for b in billed_sum) if billed_sum else 0.0
        total_paid = sum(p[0] for p in paid_sum) if paid_sum else 0.0
        total_outstanding = total_billed - total_paid
        
        # Student enrollment by class for Charts
        classes = session.query(Class).all()
        class_stats = []
        for c in classes:
            cnt = session.query(Student).filter(Student.class_id == c.id, Student.status == "Active").count()
            class_stats.append({"class_name": c.name, "count": cnt})
            
        # Attendance distribution stats
        attendance_stats = {"Present": 0, "Absent": 0, "Late": 0}
        y_id = config.get("active_academic_year_id", 1)
        t_id = config.get("active_term_id", 1)
        
        is_teacher = user.get("role") == "Teacher"
        if is_teacher:
            user_obj = session.query(User).filter(User.id == user.get("user_id")).first()
            staff_profile = user_obj.staff_profile if user_obj else None
            ct_record = None
            if staff_profile:
                ct_record = session.query(ClassTeacher).filter(
                    ClassTeacher.staff_id == staff_profile.id,
                    ClassTeacher.academic_year_id == y_id,
                    ClassTeacher.term_id == t_id
                ).first()
            if ct_record:
                class_student_ids = [s.id for s in session.query(Student).filter(Student.class_id == ct_record.class_id).all()]
                if class_student_ids:
                    att_records = session.query(Attendance).filter(
                        Attendance.student_id.in_(class_student_ids)
                    ).all()
                    for att in att_records:
                        if att.status in attendance_stats:
                            attendance_stats[att.status] += 1
        else:
            # School-wide attendance stats
            att_records = session.query(Attendance).filter(Attendance.student_id != None).all()
            for att in att_records:
                if att.status in attendance_stats:
                    attendance_stats[att.status] += 1
            
        return {
            "students": active_students,
            "staff": staff_count,
            "books": library_books,
            "fees_collected": total_collected,
            "class_distribution": class_stats,
            "billing_stats": {
                "billed": total_billed,
                "paid": total_paid,
                "outstanding": total_outstanding
            },
            "attendance_distribution": attendance_stats
        }
    finally:
        session.close()

@app.get("/api/dashboard/recent-activity")
def dashboard_recent_activity(user=Depends(get_current_user)):
    session = get_session()
    try:
        logs = session.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(15).all()
        return [
            {
                "id": log.id,
                "user": log.user.username if log.user else "System",
                "action": log.action,
                "details": log.details,
                "time": log.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            } for log in logs
        ]
    finally:
        session.close()

# --- Students API ---
@app.get("/api/students")
def get_students(search: Optional[str] = "", class_id: Optional[int] = None, status: Optional[str] = "Active", user=Depends(get_current_user)):
    session = get_session()
    try:
        query = session.query(Student)
        if search:
            query = query.filter(
                (Student.first_name.ilike(f"%{search}%")) |
                (Student.last_name.ilike(f"%{search}%")) |
                (Student.id.ilike(f"%{search}%"))
            )
        if class_id:
            query = query.filter(Student.class_id == class_id)
        if status:
            query = query.filter(Student.status == status)
            
        students = query.order_by(Student.last_name.asc()).all()
        return [
            {
                "id": s.id,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "other_names": s.other_names,
                "class_name": s.class_assigned.name if s.class_assigned else "Unassigned",
                "class_id": s.class_id,
                "status": s.status,
                "parent_name": f"{s.parent.first_name} {s.parent.last_name}" if s.parent else "N/A",
                "parent_phone": s.parent.phone if s.parent else "N/A",
                "dob": s.date_of_birth.strftime("%Y-%m-%d") if s.date_of_birth else "",
                "gender": s.gender
            } for s in students
        ]
    finally:
        session.close()

@app.post("/api/students")
def admit_student(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        # Create parent first
        parent_data = data.get("parent", {})
        parent = Parent(
            first_name=parent_data.get("first_name", "N/A"),
            last_name=parent_data.get("last_name", "N/A"),
            phone=parent_data.get("phone", "N/A"),
            email=parent_data.get("email", ""),
            occupation=parent_data.get("occupation", ""),
            address=parent_data.get("address", "")
        )
        session.add(parent)
        session.flush()
        
        # Determine student ID
        year_suffix = datetime.datetime.now().strftime("%y")
        random_num = hashlib.sha256(os.urandom(16)).hexdigest()[:4].upper()
        student_id = f"OS-{year_suffix}-{random_num}"
        
        dob = None
        if data.get("dob"):
            dob = datetime.datetime.strptime(data["dob"], "%Y-%m-%d").date()
            
        student = Student(
            id=student_id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            other_names=data.get("other_names", ""),
            date_of_birth=dob,
            gender=data.get("gender"),
            class_id=data.get("class_id"),
            parent_id=parent.id,
            admission_date=datetime.date.today(),
            status="Active"
        )
        session.add(student)
        session.commit()
        log_audit(user, "Admit Student", f"Admitted student {student.first_name} {student.last_name} ({student.id})")
        return {"status": "success", "id": student.id}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/students/bulk")
def admit_students_bulk(data: List[dict], user=Depends(get_current_user)):
    session = get_session()
    try:
        from database.models import Class
        classes = session.query(Class).all()
        class_map = {c.name.strip().lower(): c.id for c in classes}
        
        admitted = []
        errors = []
        
        for idx, row in enumerate(data):
            row_num = idx + 1
            first_name = row.get("first_name")
            last_name = row.get("last_name")
            gender = row.get("gender")
            dob_str = row.get("dob")
            class_name = row.get("class_name")
            
            if not first_name or not last_name:
                errors.append(f"Row {row_num}: First name and Last name are required.")
                continue
            if not gender:
                errors.append(f"Row {row_num}: Gender is required.")
                continue
            if not dob_str:
                errors.append(f"Row {row_num}: Date of birth is required.")
                continue
                
            try:
                datetime.datetime.strptime(dob_str, "%Y-%m-%d")
            except ValueError:
                errors.append(f"Row {row_num}: DOB '{dob_str}' must be in YYYY-MM-DD format.")
                continue
                
            if class_name:
                normalized_cname = class_name.strip().lower()
                if normalized_cname not in class_map:
                    errors.append(f"Row {row_num}: Class '{class_name}' does not exist.")
                    continue
                    
        if errors:
            raise HTTPException(status_code=400, detail="Validation errors:\n" + "\n".join(errors))
            
        year_suffix = datetime.datetime.now().strftime("%y")
        
        for row in data:
            parent_data = row.get("parent", {})
            parent = Parent(
                first_name=parent_data.get("first_name", "N/A"),
                last_name=parent_data.get("last_name", "N/A"),
                phone=parent_data.get("phone", "N/A"),
                email=parent_data.get("email", ""),
                occupation=parent_data.get("occupation", ""),
                address=parent_data.get("address", "")
            )
            session.add(parent)
            session.flush()
            
            random_num = hashlib.sha256(os.urandom(16)).hexdigest()[:4].upper()
            student_id = f"OS-{year_suffix}-{random_num}"
            
            dob = datetime.datetime.strptime(row["dob"], "%Y-%m-%d").date()
            class_name = row.get("class_name")
            class_id = class_map[class_name.strip().lower()] if class_name else None
            
            student = Student(
                id=student_id,
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                other_names=row.get("other_names", ""),
                date_of_birth=dob,
                gender=row.get("gender"),
                class_id=class_id,
                parent_id=parent.id,
                admission_date=datetime.date.today(),
                status="Active",
                emergency_contact_name=row.get("emergency_contact_name"),
                emergency_contact_phone=row.get("emergency_contact_phone")
            )
            session.add(student)
            admitted.append(student_id)
            
        session.commit()
        log_audit(user, "Bulk Admit Students", f"Admitted {len(admitted)} students in bulk")
        return {"status": "success", "count": len(admitted)}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.put("/api/students/{student_id}")
def update_student(student_id: str, data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
            
        student.first_name = data.get("first_name", student.first_name)
        student.last_name = data.get("last_name", student.last_name)
        student.other_names = data.get("other_names", student.other_names)
        student.gender = data.get("gender", student.gender)
        student.class_id = data.get("class_id", student.class_id)
        student.status = data.get("status", student.status)
        
        if data.get("dob"):
            student.date_of_birth = datetime.datetime.strptime(data["dob"], "%Y-%m-%d").date()
            
        if student.parent and data.get("parent"):
            p_data = data["parent"]
            student.parent.first_name = p_data.get("first_name", student.parent.first_name)
            student.parent.last_name = p_data.get("last_name", student.parent.last_name)
            student.parent.phone = p_data.get("phone", student.parent.phone)
            student.parent.email = p_data.get("email", student.parent.email)
            student.parent.occupation = p_data.get("occupation", student.parent.occupation)
            student.parent.address = p_data.get("address", student.parent.address)
            
        session.commit()
        log_audit(user, "Update Student", f"Updated student details for {student.id}")
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/students/bulk-promote")
def bulk_promote(req: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        student_ids = req.get("student_ids", [])
        target_class_id = req.get("target_class_id")
        if not student_ids or not target_class_id:
            raise HTTPException(status_code=400, detail="Missing student list or target class")
            
        cnt = session.query(Student).filter(Student.id.in_(student_ids)).update(
            {Student.class_id: target_class_id}, synchronize_session=False
        )
        session.commit()
        log_audit(user, "Bulk Promote", f"Promoted {cnt} students to class ID {target_class_id}")
        return {"status": "success", "count": cnt}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/students/bulk-status")
def bulk_status_change(req: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        student_ids = req.get("student_ids", [])
        new_status = req.get("status")
        if not student_ids or not new_status:
            raise HTTPException(status_code=400, detail="Missing students or status")
            
        cnt = session.query(Student).filter(Student.id.in_(student_ids)).update(
            {Student.status: new_status}, synchronize_session=False
        )
        session.commit()
        log_audit(user, "Bulk Status Change", f"Changed status of {cnt} students to {new_status}")
        return {"status": "success", "count": cnt}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/students/{student_id}/id-card")
def export_id_card(student_id: str, user=Depends(get_current_user)):
    success, filepath = generate_student_id_card(student_id)
    if not success or not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Failed to generate ID card")
    return FileResponse(filepath, media_type="application/pdf", filename=f"ID_Card_{student_id}.pdf")

@app.get("/api/students/{student_id}/admission-form")
def export_admission_form(student_id: str, user=Depends(get_current_user)):
    success, filepath = generate_admission_form(student_id)
    if not success or not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Failed to generate admission form")
    return FileResponse(filepath, media_type="application/pdf", filename=f"Admission_Form_{student_id}.pdf")

# --- Staff API ---
@app.get("/api/staff")
def get_staff(user=Depends(get_current_user)):
    session = get_session()
    try:
        staff_members = session.query(Staff).filter(Staff.status == "Active").all()
        return [
            {
                "id": s.id,
                "first_name": s.first_name,
                "last_name": s.last_name,
                "email": s.email,
                "phone": s.phone,
                "role_name": s.user.role.name if (s.user and s.user.role) else "Staff",
                "username": s.user.username if s.user else "N/A",
                "base_salary": s.base_salary or 0.0,
                "qualification": s.qualification or "",
                "hire_date": s.hire_date.strftime("%Y-%m-%d") if s.hire_date else ""
            } for s in staff_members
        ]
    finally:
        session.close()

@app.post("/api/staff")
def register_staff(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        username = data.get("username").strip()
        role_name = data.get("role_name", "Teacher")
        
        # Create User Account
        role = session.query(Role).filter(Role.name == role_name).first()
        new_user = User(
            username=username,
            password_hash=hash_password("Orion@123"), # default password
            email=data.get("email"),
            role_id=role.id if role else None
        )
        session.add(new_user)
        session.flush()
        
        # Create Staff Profile
        staff = Staff(
            user_id=new_user.id,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            qualification=data.get("qualification"),
            base_salary=float(data.get("base_salary", 0.0)),
            hire_date=datetime.date.today(),
            status="Active"
        )
        session.add(staff)
        session.commit()
        log_audit(user, "Register Staff", f"Registered staff profile for {username} ({role_name})")
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/staff/bulk")
def register_staff_bulk(data: List[dict], user=Depends(get_current_user)):
    session = get_session()
    try:
        from database.models import User, Role
        
        # Load roles
        roles = session.query(Role).all()
        role_map = {r.name.strip().lower(): r for r in roles}
        
        # Load existing usernames in DB
        existing_users = {u.username.lower() for u in session.query(User).all()}
        
        errors = []
        payload_usernames = set()
        
        # Pre-validate all records
        for idx, row in enumerate(data):
            row_num = idx + 1
            first_name = row.get("first_name")
            last_name = row.get("last_name")
            username = row.get("username")
            role_name = row.get("role_name", "Teacher")
            phone = row.get("phone")
            
            if not first_name or not last_name:
                errors.append(f"Row {row_num}: First name and Last name are required.")
                continue
            if not username:
                errors.append(f"Row {row_num}: Username is required.")
                continue
            if not phone:
                errors.append(f"Row {row_num}: Phone number is required.")
                continue
                
            clean_username = username.strip().lower()
            if clean_username in existing_users:
                errors.append(f"Row {row_num}: Username '{username}' is already taken.")
                continue
            if clean_username in payload_usernames:
                errors.append(f"Row {row_num}: Duplicate username '{username}' in upload list.")
                continue
                
            payload_usernames.add(clean_username)
            
            normalized_role = role_name.strip().lower()
            if normalized_role not in role_map:
                errors.append(f"Row {row_num}: Role '{role_name}' does not exist.")
                continue
                
        if errors:
            raise HTTPException(status_code=400, detail="Validation errors:\n" + "\n".join(errors))
            
        # If no validation errors, proceed with creation
        for row in data:
            username = row.get("username").strip()
            role_name = row.get("role_name", "Teacher")
            role = role_map[role_name.strip().lower()]
            
            new_user = User(
                username=username,
                password_hash=hash_password("Orion@123"), # default password
                email=row.get("email"),
                role_id=role.id if role else None
            )
            session.add(new_user)
            session.flush()
            
            staff = Staff(
                user_id=new_user.id,
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                email=row.get("email"),
                phone=row.get("phone"),
                qualification=row.get("qualification"),
                base_salary=float(row.get("base_salary", 0.0)) if row.get("base_salary") else 0.0,
                hire_date=datetime.date.today(),
                status="Active"
            )
            session.add(staff)
            
        session.commit()
        log_audit(user, "Bulk Register Staff", f"Registered {len(data)} staff profiles in bulk")
        return {"status": "success", "count": len(data)}
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


@app.put("/api/staff/{staff_id}")
def update_staff(staff_id: int, data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        staff = session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff member not found")
            
        staff.first_name = data.get("first_name", staff.first_name)
        staff.last_name = data.get("last_name", staff.last_name)
        staff.email = data.get("email", staff.email)
        staff.phone = data.get("phone", staff.phone)
        staff.qualification = data.get("qualification", staff.qualification)
        staff.base_salary = float(data.get("base_salary", staff.base_salary))
        
        if staff.user:
            staff.user.email = staff.email
            role_name = data.get("role_name")
            if role_name:
                role = session.query(Role).filter(Role.name == role_name).first()
                if role:
                    staff.user.role_id = role.id
                    
        session.commit()
        log_audit(user, "Update Staff", f"Updated staff details for profile ID {staff_id}")
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/staff/{staff_id}/reset-password")
def reset_staff_password(staff_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        staff = session.query(Staff).filter(Staff.id == staff_id).first()
        if not staff or not staff.user:
            raise HTTPException(status_code=404, detail="User account not found")
            
        staff.user.password_hash = hash_password("Orion@123")
        session.commit()
        log_audit(user, "Reset Password", f"Reset staff user password for {staff.user.username} to default")
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- Academics API ---
@app.get("/api/academics/years")
def get_years(user=Depends(get_current_user)):
    session = get_session()
    try:
        years = session.query(AcademicYear).all()
        return [{"id": y.id, "name": y.name, "is_current": y.is_current} for y in years]
    finally:
        session.close()

@app.post("/api/academics/years")
def add_year(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        name = data.get("name")
        start = datetime.datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        end = datetime.datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        is_curr = bool(data.get("is_current", False))
        
        if is_curr:
            session.query(AcademicYear).update({AcademicYear.is_current: False})
            
        year = AcademicYear(name=name, start_date=start, end_date=end, is_current=is_curr)
        session.add(year)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/academics/years/{year_id}/set-current")
def set_current_year(year_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        session.query(AcademicYear).update({AcademicYear.is_current: False})
        year = session.query(AcademicYear).filter(AcademicYear.id == year_id).first()
        if year:
            year.is_current = True
            
        config["active_academic_year_id"] = year_id
        save_config(config)
        
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/academics/terms")
def get_terms(user=Depends(get_current_user)):
    session = get_session()
    try:
        terms = session.query(Term).all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "year_name": t.academic_year.name if t.academic_year else "N/A",
                "is_current": t.is_current
            } for t in terms
        ]
    finally:
        session.close()

@app.post("/api/academics/terms")
def add_term(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        name = data.get("name")
        year_id = data.get("academic_year_id")
        start = datetime.datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        end = datetime.datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        is_curr = bool(data.get("is_current", False))
        
        if is_curr:
            session.query(Term).update({Term.is_current: False})
            
        term = Term(academic_year_id=year_id, name=name, start_date=start, end_date=end, is_current=is_curr)
        session.add(term)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/academics/terms/{term_id}/set-current")
def set_current_term(term_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        session.query(Term).update({Term.is_current: False})
        term = session.query(Term).filter(Term.id == term_id).first()
        if term:
            term.is_current = True
            
        config["active_term_id"] = term_id
        save_config(config)
        
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/academics/classes")
def get_classes(user=Depends(get_current_user)):
    session = get_session()
    try:
        classes = session.query(Class).all()
        return [
            {
                "id": c.id,
                "name": c.name,
                "level": c.level,
                "stream": c.stream or ""
            } for c in classes
        ]
    finally:
        session.close()

@app.post("/api/academics/classes")
def add_class(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        name = data.get("name")
        level = data.get("level")
        stream = data.get("stream", "")
        c = Class(name=name, level=level, stream=stream)
        session.add(c)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/academics/subjects")
def get_subjects(user=Depends(get_current_user)):
    session = get_session()
    try:
        subjects = session.query(Subject).all()
        return [{"id": s.id, "name": s.name, "code": s.code, "category": s.category} for s in subjects]
    finally:
        session.close()

@app.post("/api/academics/subjects")
def add_subject(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        s = Subject(name=data.get("name"), code=data.get("code"), category=data.get("category", "Core"))
        session.add(s)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/academics/assignments")
def get_assignments(user=Depends(get_current_user)):
    session = get_session()
    try:
        assigns = session.query(TeacherSubject).all()
        return [
            {
                "id": a.id,
                "class_name": a.class_obj.name if a.class_obj else "N/A",
                "subject_name": a.subject.name if a.subject else "N/A",
                "teacher_name": f"{a.teacher.first_name} {a.teacher.last_name}" if a.teacher else "N/A"
            } for a in assigns
        ]
    finally:
        session.close()

@app.post("/api/academics/assignments")
def make_assignment(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        a = TeacherSubject(
            teacher_id=data.get("teacher_id"),
            class_id=data.get("class_id"),
            subject_id=data.get("subject_id")
        )
        session.add(a)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- Attendance API ---
@app.get("/api/attendance")
def get_attendance(class_id: int, date: str, user=Depends(get_current_user)):
    session = get_session()
    try:
        att_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        students = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active").all()
        student_ids = [s.id for s in students]
        records = session.query(Attendance).filter(
            Attendance.student_id.in_(student_ids),
            Attendance.date == att_date
        ).all() if student_ids else []
        rec_map = {r.student_id: r.status for r in records}
        
        return [
            {
                "student_id": s.id,
                "student_name": f"{s.last_name}, {s.first_name}",
                "status": rec_map.get(s.id, "Present")
            } for s in students
        ]
    finally:
        session.close()
 
@app.post("/api/attendance")
def save_attendance(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        class_id = data.get("class_id")
        att_date = datetime.datetime.strptime(data["date"], "%Y-%m-%d").date()
        records = data.get("records", [])
        
        students = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active").all()
        student_ids = [s.id for s in students]
        
        if student_ids:
            session.query(Attendance).filter(
                Attendance.student_id.in_(student_ids),
                Attendance.date == att_date
            ).delete(synchronize_session=False)
        
        y_id = config.get("active_academic_year_id", 1)
        t_id = config.get("active_term_id", 1)
        
        for r in records:
            if r["student_id"] in student_ids:
                att = Attendance(
                    student_id=r["student_id"],
                    academic_year_id=y_id,
                    term_id=t_id,
                    date=att_date,
                    status=r["status"],
                    remarks=""
                )
                session.add(att)
            
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/attendance/report")
def get_attendance_report(class_id: int, start_date: str, end_date: str, user=Depends(get_current_user)):
    session = get_session()
    try:
        sd = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        
        students = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active").all()
        student_ids = [s.id for s in students]
        
        records = session.query(Attendance).filter(
            Attendance.student_id.in_(student_ids),
            Attendance.date >= sd,
            Attendance.date <= ed
        ).all() if student_ids else []
        
        student_records = {sid: [] for sid in student_ids}
        for r in records:
            if r.student_id in student_records:
                student_records[r.student_id].append(r)
                
        report_rows = []
        for s in students:
            s_recs = student_records.get(s.id, [])
            total = len(s_recs)
            present = sum(1 for r in s_recs if r.status == "Present")
            absent = sum(1 for r in s_recs if r.status == "Absent")
            late = sum(1 for r in s_recs if r.status == "Late")
            
            percentage = ((present + late) / total * 100) if total > 0 else 100.0
            
            report_rows.append({
                "student_id": s.id,
                "student_name": f"{s.last_name}, {s.first_name} {s.other_names or ''}".strip(),
                "present": present,
                "absent": absent,
                "late": late,
                "total_days": total,
                "percentage": round(percentage, 1)
            })
            
        return report_rows
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/attendance/report/pdf")
def get_attendance_report_pdf(class_id: int, start_date: str, end_date: str, user=Depends(get_current_user)):
    session = get_session()
    try:
        class_obj = session.query(Class).filter(Class.id == class_id).first()
        if not class_obj:
            raise HTTPException(status_code=404, detail="Class not found")
            
        sd = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
        ed = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
        
        students = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active").all()
        student_ids = [s.id for s in students]
        
        records = session.query(Attendance).filter(
            Attendance.student_id.in_(student_ids),
            Attendance.date >= sd,
            Attendance.date <= ed
        ).all() if student_ids else []
        
        student_records = {sid: [] for sid in student_ids}
        for r in records:
            if r.student_id in student_records:
                student_records[r.student_id].append(r)
                
        headers = ["Student ID", "Name", "Present", "Absent", "Late", "Total Days", "Attendance %"]
        rows = []
        for s in students:
            s_recs = student_records.get(s.id, [])
            total = len(s_recs)
            present = sum(1 for r in s_recs if r.status == "Present")
            absent = sum(1 for r in s_recs if r.status == "Absent")
            late = sum(1 for r in s_recs if r.status == "Late")
            percentage = ((present + late) / total * 100) if total > 0 else 100.0
            
            rows.append([
                s.id,
                f"{s.last_name}, {s.first_name}",
                str(present),
                str(absent),
                str(late),
                str(total),
                f"{percentage:.1f}%"
            ])
            
        date_range = f"{start_date} to {end_date}"
        success, filepath = generate_attendance_report_pdf(class_obj.name, date_range, headers, rows)
        
        if not success or not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="Failed to generate Attendance Report PDF")
            
        return FileResponse(filepath, media_type="application/pdf", filename=f"Attendance_Report_{class_obj.name.replace(' ', '_')}.pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/attendance/staff")
def get_staff_attendance(date: str, user=Depends(get_current_user)):
    session = get_session()
    try:
        att_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
        staff_members = session.query(Staff).filter(Staff.status == "Active").all()
        staff_ids = [st.id for st in staff_members]
        records = session.query(Attendance).filter(
            Attendance.staff_id.in_(staff_ids),
            Attendance.date == att_date
        ).all() if staff_ids else []
        rec_map = {r.staff_id: r.status for r in records}
        
        return [
            {
                "staff_id": st.id,
                "staff_name": f"{st.last_name}, {st.first_name} {st.other_names or ''}".strip(),
                "role_title": st.role_title,
                "status": rec_map.get(st.id, "Present")
            } for st in staff_members
        ]
    finally:
        session.close()

@app.post("/api/attendance/staff")
def save_staff_attendance(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        att_date = datetime.datetime.strptime(data["date"], "%Y-%m-%d").date()
        records = data.get("records", [])
        
        staff_members = session.query(Staff).filter(Staff.status == "Active").all()
        staff_ids = [st.id for st in staff_members]
        
        if staff_ids:
            session.query(Attendance).filter(
                Attendance.staff_id.in_(staff_ids),
                Attendance.date == att_date
            ).delete(synchronize_session=False)
            
        y_id = config.get("active_academic_year_id", 1)
        t_id = config.get("active_term_id", 1)
        
        for r in records:
            s_id = int(r["staff_id"])
            if s_id in staff_ids:
                att = Attendance(
                    staff_id=s_id,
                    academic_year_id=y_id,
                    term_id=t_id,
                    date=att_date,
                    status=r["status"],
                    remarks=""
                )
                session.add(att)
                
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- Exams API ---
@app.get("/api/exams")
def get_exams(user=Depends(get_current_user)):
    session = get_session()
    try:
        exams = session.query(Examination).all()
        return [
            {
                "id": e.id,
                "name": e.name,
                "term_name": e.term.name if e.term else "N/A",
                "is_active": True
            } for e in exams
        ]
    finally:
        session.close()

@app.post("/api/exams")
def add_exam(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        y_id = config.get("active_academic_year_id", 1)
        t_id = config.get("active_term_id", 1)
        e = Examination(
            academic_year_id=y_id,
            term_id=t_id,
            name=data.get("name"),
            exam_date=datetime.date.today(),
            max_score=100
        )
        session.add(e)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/exams/grades")
def get_grades(user=Depends(get_current_user)):
    return config.get("grading_scale", [])

@app.put("/api/exams/grades")
def save_grades(grades: list, user=Depends(get_current_user)):
    config["grading_scale"] = grades
    save_config(config)
    return {"status": "success"}

@app.get("/api/exams/results")
def get_results(class_id: int, subject_id: int, exam_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        students = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active").all()
        results = session.query(Result).filter(
            Result.class_id == class_id,
            Result.subject_id == subject_id,
            Result.examination_id == exam_id
        ).all()
        
        res_map = {r.student_id: (r.class_score, r.exam_score, r.remarks) for r in results}
        
        return [
            {
                "student_id": s.id,
                "student_name": f"{s.last_name}, {s.first_name}",
                "class_score": res_map.get(s.id, (0.0, 0.0, ""))[0],
                "exam_score": res_map.get(s.id, (0.0, 0.0, ""))[1],
                "remarks": res_map.get(s.id, (0.0, 0.0, ""))[2]
            } for s in students
        ]
    finally:
        session.close()

@app.post("/api/exams/results")
def save_results(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        class_id = data.get("class_id")
        subject_id = data.get("subject_id")
        exam_id = data.get("exam_id")
        scores = data.get("scores", [])
        
        session.query(Result).filter(
            Result.class_id == class_id,
            Result.subject_id == subject_id,
            Result.examination_id == exam_id
        ).delete()
        
        for sc in scores:
            c_score = float(sc.get("class_score", 0.0))
            e_score = float(sc.get("exam_score", 0.0))
            t_score = (c_score * 0.3) + (e_score * 0.7)
            
            scale = config.get("grading_scale", [])
            grade_letter = "9"
            for g in sorted(scale, key=lambda x: x["min_score"], reverse=True):
                if t_score >= g["min_score"]:
                    grade_letter = g["grade"]
                    break
                    
            r = Result(
                student_id=sc["student_id"],
                class_id=class_id,
                subject_id=subject_id,
                examination_id=exam_id,
                class_score=c_score,
                exam_score=e_score,
                total_score=t_score,
                grade=grade_letter,
                remarks=sc.get("remarks", "")
            )
            session.add(r)
            
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/exams/reports/summary")
def get_report_card_summary(class_id: int, exam_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        class_obj = session.query(Class).filter(Class.id == class_id).first()
        exam_obj = session.query(Examination).filter(Examination.id == exam_id).first()
        
        if not class_obj or not exam_obj:
            raise HTTPException(status_code=404, detail="Class or Exam not found")
            
        students = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active").all()
        subjects = session.query(Subject).all()
        
        headers = ["Rank", "Student ID", "Name"] + [s.name for s in subjects] + ["Total", "Avg", "Grade"]
        
        rows = []
        for s in students:
            res = session.query(Result).filter(Result.student_id == s.id, Result.examination_id == exam_id).all()
            res_map = {r.subject_id: r.total_score for r in res}
            
            sub_scores = []
            total = 0.0
            for sb in subjects:
                sc = res_map.get(sb.id, 0.0)
                sub_scores.append(f"{sc:.1f}")
                total += sc
                
            avg = total / len(subjects) if subjects else 0.0
            
            scale = config.get("grading_scale", [])
            grade_letter = "9"
            for g in sorted(scale, key=lambda x: x["min_score"], reverse=True):
                if avg >= g["min_score"]:
                    grade_letter = g["grade"]
                    break
                    
            rows.append({
                "student_id": s.id,
                "name": f"{s.last_name}, {s.first_name}",
                "scores": sub_scores,
                "total": total,
                "avg": avg,
                "grade": grade_letter
            })
            
        rows = sorted(rows, key=lambda x: x["total"], reverse=True)
        pdf_rows = []
        for idx, r in enumerate(rows):
            pdf_rows.append([str(idx + 1), r["student_id"], r["name"]] + r["scores"] + [f"{r['total']:.1f}", f"{r['avg']:.1f}", r["grade"]])
            
        success, filepath = generate_class_summary_pdf(class_obj.name, exam_obj.name, headers, pdf_rows)
        if not success or not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="Failed to generate Class Summary PDF")
            
        return FileResponse(filepath, media_type="application/pdf", filename=f"Class_Summary_{class_obj.name.replace(' ', '_')}.pdf")
    finally:
        session.close()

@app.get("/api/exams/reports/student/{student_id}")
def get_student_report_card(student_id: str, exam_id: int, user=Depends(get_current_user)):
    success, filepath = generate_report_card(student_id, exam_id)
    if not success or not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Failed to generate student report card")
    return FileResponse(filepath, media_type="application/pdf", filename=f"Report_Card_{student_id}.pdf")

# --- Fees API ---
@app.get("/api/fees/structures")
def get_fees(user=Depends(get_current_user)):
    session = get_session()
    try:
        bills = session.query(StudentBill).all()
        return [
            {
                "id": b.id,
                "student_id": b.student_id,
                "student_name": f"{b.student.last_name}, {b.student.first_name}" if b.student else "N/A",
                "term_name": b.term.name if b.term else "N/A",
                "total_billed": b.total_billed,
                "total_paid": b.total_paid,
                "balance": b.total_billed - b.total_paid
            } for b in bills
        ]
    finally:
        session.close()

@app.post("/api/fees/structures")
def create_fee_structure(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        class_id = data.get("class_id")
        amount = float(data.get("amount", 0.0))
        bill_item = data.get("bill_item", "School Fees")
        
        y_id = config.get("active_academic_year_id", 1)
        t_id = config.get("active_term_id", 1)
        
        students = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active").all()
        for s in students:
            bill = session.query(StudentBill).filter(
                StudentBill.student_id == s.id,
                StudentBill.academic_year_id == y_id,
                StudentBill.term_id == t_id
            ).first()
            if not bill:
                bill = StudentBill(
                    student_id=s.id,
                    academic_year_id=y_id,
                    term_id=t_id,
                    total_billed=0.0,
                    total_paid=0.0
                )
                session.add(bill)
                session.flush()
                
            bill.total_billed += amount
            
            fee = Fee(
                student_id=s.id,
                academic_year_id=y_id,
                term_id=t_id,
                amount=amount,
                description=f"{bill_item} for {s.class_assigned.name if s.class_assigned else 'Class'}",
                due_date=datetime.date.today() + datetime.timedelta(days=30),
                status="Unpaid"
            )
            session.add(fee)
            
        session.commit()
        return {"status": "success", "billed_students": len(students)}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/fees/payments")
def get_payments(user=Depends(get_current_user)):
    session = get_session()
    try:
        payments = session.query(Payment).order_by(Payment.payment_date.desc()).all()
        return [
            {
                "id": p.id,
                "student_name": f"{p.student_bill.student.last_name}, {p.student_bill.student.first_name}" if (p.student_bill and p.student_bill.student) else "N/A",
                "student_id": p.student_bill.student_id if (p.student_bill and p.student_bill.student) else "N/A",
                "amount": p.amount,
                "payment_mode": p.payment_method,
                "ref_number": p.reference_no or "",
                "date": p.payment_date.strftime("%Y-%m-%d %H:%M:%S")
            } for p in payments
        ]
    finally:
        session.close()

@app.post("/api/fees/payments")
def record_payment(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        student_id = data.get("student_id")
        amount = float(data.get("amount", 0.0))
        mode = data.get("payment_mode", "Cash")
        ref = data.get("ref_number", "")
        
        y_id = config.get("active_academic_year_id", 1)
        t_id = config.get("active_term_id", 1)
        
        bill = session.query(StudentBill).filter(
            StudentBill.student_id == student_id,
            StudentBill.academic_year_id == y_id,
            StudentBill.term_id == t_id
        ).first()
        if not bill:
            bill = StudentBill(
                student_id=student_id,
                academic_year_id=y_id,
                term_id=t_id,
                total_billed=0.0,
                total_paid=0.0
            )
            session.add(bill)
            session.flush()
            
        bill.total_paid += amount
        
        payment = Payment(
            student_bill_id=bill.id,
            amount=amount,
            payment_date=datetime.datetime.utcnow(),
            payment_method=mode,
            reference_no=ref,
            received_by=user.get("user_id")
        )
        session.add(payment)
        session.commit()
        
        log_audit(user, "Record Fee Payment", f"Recorded payment of {amount} for student {student_id}")
        return {"status": "success", "payment_id": payment.id}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/fees/payments/{payment_id}/receipt")
def export_payment_receipt(payment_id: int, user=Depends(get_current_user)):
    success, filepath = generate_fee_receipt(payment_id)
    if not success or not os.path.exists(filepath):
        raise HTTPException(status_code=500, detail="Failed to generate payment receipt")
    return FileResponse(filepath, media_type="application/pdf", filename=f"Receipt_{payment_id}.pdf")

@app.get("/api/fees/balances")
def get_fee_balances(user=Depends(get_current_user)):
    session = get_session()
    try:
        bills = session.query(StudentBill).all()
        res = []
        for b in bills:
            bal = b.total_billed - b.total_paid
            if bal > 0:
                res.append({
                    "student_id": b.student_id,
                    "student_name": f"{b.student.last_name}, {b.student.first_name}" if b.student else "N/A",
                    "class_name": b.student.class_assigned.name if (b.student and b.student.class_assigned) else "N/A",
                    "total_billed": b.total_billed,
                    "total_paid": b.total_paid,
                    "balance": bal
                })
        return res
    finally:
        session.close()

# --- Library API ---
@app.get("/api/library/books")
def get_books(user=Depends(get_current_user)):
    session = get_session()
    try:
        books = session.query(LibraryBook).all()
        return [
            {
                "id": b.id,
                "title": b.title,
                "author": b.author,
                "isbn": b.isbn or "",
                "quantity": b.copies_total,
                "available": b.copies_available,
                "location": b.shelf_location or ""
            } for b in books
        ]
    finally:
        session.close()

@app.post("/api/library/books")
def add_book(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        qty = int(data.get("quantity", 1))
        b = LibraryBook(
            title=data.get("title"),
            author=data.get("author"),
            isbn=data.get("isbn", ""),
            copies_total=qty,
            copies_available=qty,
            shelf_location=data.get("location", "")
        )
        session.add(b)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/library/logs")
def get_library_logs(user=Depends(get_current_user)):
    session = get_session()
    try:
        logs = session.query(LibraryIssue).order_by(LibraryIssue.issue_date.desc()).all()
        result = []
        for log in logs:
            if log.student:
                borrower = f"Student: {log.student.last_name}, {log.student.first_name}"
            elif log.staff_id:
                from database.models import Staff
                staff_member = session.query(Staff).filter(Staff.id == log.staff_id).first()
                borrower = f"Staff: {staff_member.last_name}, {staff_member.first_name}" if staff_member else "Staff: Unknown"
            else:
                borrower = "N/A"
                
            result.append({
                "id": log.id,
                "book_title": log.book.title if log.book else "N/A",
                "student_name": borrower,
                "issue_date": log.issue_date.strftime("%Y-%m-%d"),
                "due_date": log.due_date.strftime("%Y-%m-%d") if log.due_date else "",
                "return_date": log.return_date.strftime("%Y-%m-%d") if log.return_date else "",
                "status": log.status
            })
        return result
    finally:
        session.close()
 
@app.post("/api/library/borrow")
def borrow_book(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        book_id = data.get("book_id")
        student_id = data.get("student_id")
        staff_id = data.get("staff_id")
        
        book = session.query(LibraryBook).filter(LibraryBook.id == book_id).first()
        if not book or book.copies_available < 1:
            raise HTTPException(status_code=400, detail="Book not available")
            
        book.copies_available -= 1
        
        due = datetime.date.today() + datetime.timedelta(days=14)
        issue = LibraryIssue(
            book_id=book_id,
            student_id=student_id if student_id else None,
            staff_id=int(staff_id) if staff_id else None,
            issue_date=datetime.date.today(),
            due_date=due,
            status="Issued"
        )
        session.add(issue)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/library/return/{log_id}")
def return_book(log_id: int, user=Depends(get_current_user)):
    session = get_session()
    try:
        issue = session.query(LibraryIssue).filter(LibraryIssue.id == log_id).first()
        if not issue or issue.status == "Returned":
            raise HTTPException(status_code=400, detail="Invalid log or already returned")
            
        issue.status = "Returned"
        issue.return_date = datetime.date.today()
        
        if issue.book:
            issue.book.copies_available += 1
            
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- Inventory API ---
@app.get("/api/inventory")
def get_inventory(user=Depends(get_current_user)):
    session = get_session()
    try:
        items = session.query(Inventory).all()
        return [
            {
                "id": i.id,
                "item_name": i.item_name,
                "category": i.category or "",
                "quantity": i.quantity_total,
                "condition": i.condition or "Good",
                "value": i.unit_value or 0.0
            } for i in items
        ]
    finally:
        session.close()

@app.post("/api/inventory")
def add_inventory(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        qty = int(data.get("quantity", 0))
        val = float(data.get("value", 0.0))
        i = Inventory(
            item_name=data.get("item_name"),
            category=data.get("category", ""),
            quantity_total=qty,
            condition=data.get("condition", "Good"),
            unit_value=val
        )
        session.add(i)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

# --- Communication API ---
@app.get("/api/communication/announcements")
def get_announcements(user=Depends(get_current_user)):
    session = get_session()
    try:
        ann = session.query(Announcement).order_by(Announcement.date_posted.desc()).all()
        return [
            {
                "id": a.id,
                "title": a.title,
                "content": a.content,
                "audience": a.target_audience or "All",
                "date": a.date_posted.strftime("%Y-%m-%d %H:%M:%S")
            } for a in ann
        ]
    finally:
        session.close()

@app.post("/api/communication/announcements")
def add_announcement(data: dict, user=Depends(get_current_user)):
    session = get_session()
    try:
        a = Announcement(
            title=data.get("title"),
            content=data.get("content"),
            target_audience=data.get("audience", "All"),
            date_posted=datetime.datetime.utcnow(),
            posted_by=user.get("user_id")
        )
        session.add(a)
        session.commit()
        return {"status": "success"}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.post("/api/communication/sms")
def send_custom_sms(data: dict, user=Depends(get_current_user)):
    phone = data.get("phone")
    message = data.get("message")
    success, msg = send_sms(phone, message, "Notice")
    if not success:
         raise HTTPException(status_code=500, detail=msg)
    return {"status": "success", "message": msg}

@app.post("/api/communication/sms/broadcast")
def broadcast_sms(data: dict, user=Depends(get_current_user)):
    broadcast_type = data.get("broadcast_type") # "fee_reminder" or "report_summary"
    class_id = data.get("class_id") # optional: filter by class, if null/all then do school-wide
    
    session = get_session()
    try:
        # Find active academic year and term
        active_year_id = config.get("active_academic_year_id", 1)
        active_term_id = config.get("active_term_id", 1)
        
        # Build query for active students
        query = session.query(Student).filter(Student.status == "Active")
        if class_id:
            query = query.filter(Student.class_id == class_id)
        students = query.all()
        
        if not students:
            return {"status": "success", "sent_count": 0, "message": "No active students found."}
            
        sent_count = 0
        
        if broadcast_type == "fee_reminder":
            for s in students:
                # Get outstanding balance
                bills = session.query(StudentBill).filter(StudentBill.student_id == s.id).all()
                total_billed = sum(b.amount_billed for b in bills)
                total_paid = sum(b.amount_paid for b in bills)
                outstanding = total_billed - total_paid
                
                if outstanding > 0 and s.parent and s.parent.phone:
                    parent_phone = s.parent.phone
                    student_name = f"{s.first_name} {s.last_name}"
                    message = f"Dear Parent, this is a reminder that the outstanding fee balance for your ward {student_name} is {outstanding:.2f} GHS. Please make payment. Thank you."
                    success, msg = send_sms(parent_phone, message, "Fee Reminder")
                    if success:
                        sent_count += 1
                        
        elif broadcast_type == "report_summary":
            # Find the exam
            exam = session.query(Examination).filter(
                Examination.academic_year_id == active_year_id,
                Examination.term_id == active_term_id
            ).first()
            
            if not exam:
                raise HTTPException(status_code=400, detail="No examination found for the active term to broadcast report summaries.")
                
            # Precompute ranks per class for speed/efficiency
            # Group students by class_id to compute ranks
            class_groups = {}
            for s in students:
                if s.class_id not in class_groups:
                    class_groups[s.class_id] = []
                class_groups[s.class_id].append(s)
                
            class_ranks = {} # class_id -> { student_id -> rank }
            for cid, s_list in class_groups.items():
                student_totals = []
                for s in s_list:
                    res = session.query(Result).filter(Result.student_id == s.id, Result.examination_id == exam.id).all()
                    tot = sum(r.total_score for r in res) if res else 0.0
                    student_totals.append((s.id, tot, res))
                # Sort descending by total score
                student_totals.sort(key=lambda x: x[1], reverse=True)
                
                class_ranks[cid] = {}
                for idx, (sid, tot, res) in enumerate(student_totals):
                    class_ranks[cid][sid] = {
                        "rank": idx + 1,
                        "total_students": len(s_list),
                        "total_score": tot,
                        "results_count": len(res)
                    }
                    
            for s in students:
                if s.parent and s.parent.phone:
                    parent_phone = s.parent.phone
                    student_name = f"{s.first_name} {s.last_name}"
                    class_name = s.class_assigned.name if s.class_assigned else "Unknown Class"
                    
                    # Get rank info
                    rank_info = class_ranks.get(s.class_id, {}).get(s.id, {"rank": 0, "total_students": 0, "total_score": 0.0, "results_count": 0})
                    rank = rank_info["rank"]
                    total_class_students = rank_info["total_students"]
                    avg_score = rank_info["total_score"] / rank_info["results_count"] if rank_info["results_count"] > 0 else 0.0
                    
                    # Get attendance info
                    total_days = session.query(Attendance).filter(
                        Attendance.student_id == s.id,
                        Attendance.academic_year_id == active_year_id,
                        Attendance.term_id == active_term_id
                    ).count()
                    
                    present_days = session.query(Attendance).filter(
                        Attendance.student_id == s.id,
                        Attendance.academic_year_id == active_year_id,
                        Attendance.term_id == active_term_id,
                        Attendance.status.in_(["Present", "Late"])
                    ).count()
                    
                    message = f"Dear Parent, report card summary for {student_name} ({class_name}): Average Score: {avg_score:.1f}%, Position: {rank}/{total_class_students}, Attendance: {present_days}/{total_days} days. Please contact the administration."
                    success, msg = send_sms(parent_phone, message, "Report Summary")
                    if success:
                        sent_count += 1
                        
        return {"status": "success", "sent_count": sent_count, "message": f"Successfully broadcasted {sent_count} SMS alerts."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()

@app.get("/api/communication/sms-logs")
def get_sms_logs(user=Depends(get_current_user)):
    session = get_session()
    try:
        logs = session.query(SMSLog).order_by(SMSLog.sent_at.desc()).all()
        return [
            {
                "id": log.id,
                "phone": log.recipient_phone,
                "content": log.message_content,
                "status": log.status,
                "date": log.sent_at.strftime("%Y-%m-%d %H:%M:%S")
            } for log in logs
        ]
    finally:
        session.close()

# --- Settings & Profile API ---
@app.get("/api/settings/school-profile")
def get_school_profile(user=Depends(get_current_user)):
    return {
        "school_name": config.get("school_name", ""),
        "school_motto": config.get("school_motto", ""),
        "school_email": config.get("school_email", ""),
        "school_phone": config.get("school_phone", ""),
        "school_address": config.get("school_address", ""),
        "curriculum": config.get("curriculum", "GES"),
        "currency": config.get("currency", "GHS"),
        "theme": config.get("theme", "dark")
    }

@app.put("/api/settings/school-profile")
def update_school_profile(data: dict, user=Depends(get_current_user)):
    for key in ["school_name", "school_motto", "school_email", "school_phone", "school_address", "curriculum", "currency", "theme"]:
        if key in data:
            config[key] = data[key]
    save_config(config)
    log_audit(user, "Update School Profile", "Updated general settings profile")
    return {"status": "success"}

@app.get("/api/settings/backups")
def get_backups(user=Depends(get_current_user)):
    backup_dir = Path(config.get("backup_directory")) if config.get("backup_directory") else DATA_DIR / "backups"
    if not backup_dir.exists():
        return []
    files = sorted(backup_dir.glob("*.zip"), key=os.path.getmtime, reverse=True)
    return [
        {
            "filename": f.name,
            "size": f.stat().st_size,
            "created": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        } for f in files
    ]

@app.post("/api/settings/backups")
def trigger_backup(user=Depends(get_current_user)):
    try:
        success = run_auto_backup("manual")
        if success:
             log_audit(user, "Trigger Backup", "Manually triggered data backup")
             return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=500, detail="Failed to run manual backup")

# --- System Admin API (Global Scope) ---
@app.get("/api/sysadmin/branches")
def sysadmin_get_branches(user=Depends(get_current_user)):
    if user.get("role") != "System Admin":
        raise HTTPException(status_code=403, detail="Forbidden")
        
    m_session = get_master_session()
    try:
        branches = m_session.query(Branch).order_by(Branch.name).all()
        res = []
        for b in branches:
            db_path = DATA_DIR / b.db_filename
            students_cnt = 0
            staff_cnt = 0
            if db_path.exists():
                try:
                    from sqlalchemy import create_engine
                    from sqlalchemy.orm import sessionmaker
                    engine = create_engine(f"sqlite:///{db_path}")
                    SessionLocal = sessionmaker(bind=engine)
                    session = SessionLocal()
                    try:
                        students_cnt = session.query(Student).filter(Student.status == "Active").count()
                        staff_cnt = session.query(Staff).filter(Staff.status == "Active").count()
                    finally:
                        session.close()
                        engine.dispose()
                except Exception:
                    pass
                    
            res.append({
                "id": b.id,
                "name": b.name,
                "code": b.code,
                "address": b.address or "",
                "phone": b.phone or "",
                "email": b.email or "",
                "is_active": b.is_active,
                "db_filename": b.db_filename,
                "students": students_cnt,
                "staff": staff_cnt
            })
        return res
    finally:
        m_session.close()

@app.post("/api/sysadmin/branches")
def sysadmin_create_branch(req: BranchCreate, user=Depends(get_current_user)):
    if user.get("role") != "System Admin":
        raise HTTPException(status_code=403, detail="Forbidden")
        
    m_session = get_master_session()
    try:
        dup = m_session.query(Branch).filter(Branch.code == req.code.upper().strip()).first()
        if dup:
            raise HTTPException(status_code=400, detail="Branch code already exists")
            
        # Check for duplicate username in master database (SystemAdmin or other BranchAdmin)
        dup_sys = m_session.query(SystemAdmin).filter(SystemAdmin.username == req.head_username.strip()).first()
        dup_br = m_session.query(BranchAdmin).filter(BranchAdmin.username == req.head_username.strip()).first()
        if dup_sys or dup_br:
            raise HTTPException(status_code=400, detail="Head Teacher username is already registered as an admin")
            
        db_filename = f"branch_{hashlib.sha256(os.urandom(16)).hexdigest()[:8]}.db"
        
        branch = Branch(
            name=req.name,
            code=req.code.upper().strip(),
            address=req.address,
            phone=req.phone,
            email=req.email,
            db_filename=db_filename,
            is_active=True,
            notes=req.notes
        )
        m_session.add(branch)
        m_session.flush()
        
        # Create BranchAdmin record in master DB
        branch_admin = BranchAdmin(
            branch_id=branch.id,
            username=req.head_username.strip(),
            full_name=req.head_full_name.strip(),
            email=req.head_email.strip() if req.head_email else None,
            is_active=True
        )
        m_session.add(branch_admin)
        m_session.flush()
        
        branch_db_path = DATA_DIR / db_filename
        token = current_db_url.set(f"sqlite:///{branch_db_path}")
        try:
            init_db()
            seed_database(seed_demo=True)
            
            # Insert custom Head Teacher account and staff profile into branch DB
            b_session = get_session()
            try:
                role_head = b_session.query(Role).filter(Role.name == "Admin/Headteacher").first()
                if not role_head:
                    role_head = b_session.query(Role).filter(Role.name == "Super Admin").first()
                    
                # Delete default seeded 'headteacher' user and staff if they exist
                default_head = b_session.query(User).filter(User.username == "headteacher").first()
                if default_head:
                    if default_head.staff_profile:
                        b_session.delete(default_head.staff_profile)
                    b_session.delete(default_head)
                    b_session.flush()
                    
                # Insert the custom Head Teacher user
                custom_user = User(
                    username=req.head_username.strip(),
                    password_hash=hash_password(req.head_password),
                    email=req.head_email.strip() if req.head_email else None,
                    role_id=role_head.id if role_head else None,
                    is_active=True
                )
                b_session.add(custom_user)
                b_session.flush()
                
                # Split full name into first and last name
                name_parts = req.head_full_name.strip().split(maxsplit=1)
                first_name = name_parts[0] if name_parts else "Head"
                last_name = name_parts[1] if len(name_parts) > 1 else "Teacher"
                
                # Insert the corresponding staff profile
                custom_staff = Staff(
                    user_id=custom_user.id,
                    first_name=first_name,
                    last_name=last_name,
                    email=custom_user.email,
                    phone=req.phone or "+233 24 000 0000",
                    role_title="Headteacher",
                    department="Administration",
                    hire_date=datetime.date.today(),
                    status="Active"
                )
                b_session.add(custom_staff)
                b_session.commit()
            except Exception as b_err:
                b_session.rollback()
                raise b_err
            finally:
                b_session.close()
        finally:
            current_db_url.reset(token)
            
        m_session.commit()
        return {"status": "success", "branch_id": branch.id}
    except Exception as e:
        m_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        m_session.close()

@app.put("/api/sysadmin/branches/{branch_id}")
def sysadmin_update_branch(branch_id: int, req: BranchUpdate, user=Depends(get_current_user)):
    if user.get("role") != "System Admin":
         raise HTTPException(status_code=403, detail="Forbidden")
         
    m_session = get_master_session()
    try:
        branch = m_session.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
             raise HTTPException(status_code=404, detail="Branch not found")
             
        branch.name = req.name
        branch.address = req.address
        branch.phone = req.phone
        branch.email = req.email
        branch.is_active = req.is_active
        branch.notes = req.notes
        
        m_session.commit()
        return {"status": "success"}
    except Exception as e:
        m_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        m_session.close()

@app.get("/api/sysadmin/admins")
def sysadmin_get_admins(user=Depends(get_current_user)):
    if user.get("role") != "System Admin":
        raise HTTPException(status_code=403, detail="Forbidden")
        
    m_session = get_master_session()
    try:
        admins = m_session.query(SystemAdmin).all()
        return [
            {
                "id": a.id,
                "username": a.username,
                "full_name": a.full_name,
                "email": a.email or "",
                "is_active": a.is_active,
                "created_at": a.created_at.strftime("%Y-%m-%d")
            } for a in admins
        ]
    finally:
        m_session.close()

@app.post("/api/sysadmin/admins")
def sysadmin_create_admin(req: SystemAdminCreate, user=Depends(get_current_user)):
    if user.get("role") != "System Admin":
        raise HTTPException(status_code=403, detail="Forbidden")
        
    m_session = get_master_session()
    try:
        dup = m_session.query(SystemAdmin).filter(SystemAdmin.username == req.username.strip()).first()
        if dup:
            raise HTTPException(status_code=400, detail="Admin username already exists")
            
        admin = SystemAdmin(
            username=req.username.strip(),
            password_hash=hash_password(req.password),
            full_name=req.full_name,
            email=req.email,
            is_active=True
        )
        m_session.add(admin)
        m_session.commit()
        return {"status": "success"}
    except Exception as e:
        m_session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        m_session.close()

# --- Serve Static HTML App ---
web_dir = Path(__file__).parent / "web"

@app.get("/")
def get_index():
    index_path = web_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"status": "error", "message": "Frontend files not found. Please create web/index.html"}, status_code=404)

if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")
    for subdir in ["css", "js", "assets", "img"]:
         sd = web_dir / subdir
         if sd.exists():
             app.mount(f"/{subdir}", StaticFiles(directory=str(sd)), name=f"static_{subdir}")
