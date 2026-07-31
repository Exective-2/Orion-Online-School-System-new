import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from database.master_connection import MasterBase


class Branch(MasterBase):
    """Represents a school branch. Each branch has its own isolated SQLite database file."""
    __tablename__ = "branches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)           # e.g., "Main Campus", "North Annexe"
    code = Column(String(20), unique=True, nullable=False)  # Short code e.g., "MAIN", "NORTH"
    address = Column(String(250), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(120), nullable=True)
    db_filename = Column(String(120), nullable=False)    # e.g., "branch_1.db"
    system_fee = Column(Float, default=0.0)             # Per-student mandatory system software fee
    disabled_modules = Column(Text, default="")         # Comma-separated disabled modules e.g., "fees,payroll"
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    admins = relationship("BranchAdmin", back_populates="branch", cascade="all, delete-orphan")
    platform_bills = relationship("PlatformBill", back_populates="branch", cascade="all, delete-orphan")
    support_tickets = relationship("SupportTicket", back_populates="branch", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Branch id={self.id} name='{self.name}' code='{self.code}'>"


class BranchAdmin(MasterBase):
    """
    Lookup table used by the login flow to quickly find which branch a user
    belongs to — so we know which branch DB to query for full credentials.

    The actual User record (with role & permissions) still lives inside the
    branch's own SQLite database.
    """
    __tablename__ = "branch_admins"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    username = Column(String(80), nullable=False, index=True)
    # Mirrors the username registered in the branch DB for routing only.
    # Actual password verification always happens against the branch DB.
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    branch = relationship("Branch", back_populates="admins")

    def __repr__(self):
        return f"<BranchAdmin id={self.id} username='{self.username}' branch_id={self.branch_id}>"


class SystemAdmin(MasterBase):
    """
    System-level administrator account stored exclusively in the master DB.
    A SystemAdmin is NOT associated with any single branch and has access to
    the System Admin Portal where branches and branch admins are managed.
    """
    __tablename__ = "system_admins"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(300), nullable=False)
    full_name = Column(String(120), nullable=False)
    email = Column(String(120), nullable=True)
    phone = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<SystemAdmin id={self.id} username='{self.username}'>"


class MasterAuditLog(MasterBase):
    """Stores master audit trail for all System Admin activities across school branches."""
    __tablename__ = "master_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    admin_username = Column(String(80), nullable=False)
    action_type = Column(String(50), nullable=False)  # e.g., BRANCH_CREATE, BRANCH_UPDATE, STATUS_TOGGLE, PASSWORD_RESET, BACKUP_EXPORT
    target_branch = Column(String(150), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class GlobalAnnouncement(MasterBase):
    """System-wide announcements broadcasted across all or specific school branches."""
    __tablename__ = "global_announcements"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    target_branch_id = Column(Integer, nullable=True)  # Null = All branches
    priority = Column(String(20), default="Info")  # Info, Warning, Critical
    is_active = Column(Boolean, default=True)
    created_by = Column(String(80), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class GlobalSMSGateway(MasterBase):
    """Centralized SMS Gateway Configuration (Arkesel, Hubtel, mNotify, Twilio)."""
    __tablename__ = "global_sms_gateways"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), default="Arkesel")  # Arkesel, Hubtel, mNotify, Twilio, Generic
    sender_id = Column(String(20), default="ORION")
    api_key = Column(String(250), nullable=True)
    api_secret = Column(String(250), nullable=True)
    endpoint_url = Column(String(250), nullable=True)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class GlobalPaymentGateway(MasterBase):
    """Centralized Payment Gateway Configuration (Paystack, Hubtel, Flutterwave, Sandbox)."""
    __tablename__ = "global_payment_gateways"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), default="Paystack")  # Paystack, Hubtel, Flutterwave, Sandbox
    public_key = Column(String(250), nullable=True)
    secret_key = Column(String(250), nullable=True)
    merchant_id = Column(String(250), nullable=True)
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)


class PlatformBill(MasterBase):
    """Stores term-by-term platform software bill records per school branch managed by SystemAdmin."""
    __tablename__ = "platform_bills"

    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    academic_year = Column(String(50), nullable=False)  # e.g., "2025/2026"
    term_name = Column(String(50), nullable=False)      # e.g., "Term 1"
    student_count = Column(Integer, default=0)
    fee_per_student = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    status = Column(String(20), default="Pending")     # "Pending", "Paid", "Approved"
    paid_at = Column(DateTime, nullable=True)
    approved_by = Column(String(80), nullable=True)
    reference_no = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    branch = relationship("Branch", back_populates="platform_bills")

    def __repr__(self):
        return f"<PlatformBill id={self.id} branch_id={self.branch_id} term='{self.academic_year} {self.term_name}' total={self.total_amount} status='{self.status}'>"


class SupportTicket(MasterBase):
    """Stores help/complaint support tickets sent by Branch Admins & Headteachers to System Admin."""
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String(50), unique=True, nullable=False)  # e.g., TCK-202607-001
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="CASCADE"), nullable=False)
    sender_username = Column(String(80), nullable=False)
    sender_name = Column(String(120), nullable=False)
    sender_role = Column(String(80), default="Branch Admin")
    subject = Column(String(200), nullable=False)
    category = Column(String(80), default="Technical Issue")  # "Technical Issue", "Billing / System Fee", "Feature Request", "Account / Access", "General"
    priority = Column(String(20), default="Medium")           # "Low", "Medium", "High", "Critical"
    description = Column(Text, nullable=False)
    status = Column(String(20), default="Open")              # "Open", "In Progress", "Resolved", "Closed"
    admin_response = Column(Text, nullable=True)              # Feedback provided by System Admin when resolving
    resolved_by = Column(String(80), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    branch = relationship("Branch", back_populates="support_tickets")

    def __repr__(self):
        return f"<SupportTicket {self.ticket_number} status='{self.status}' subject='{self.subject}'>"



