import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
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
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    admins = relationship("BranchAdmin", back_populates="branch", cascade="all, delete-orphan")

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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<SystemAdmin id={self.id} username='{self.username}'>"
