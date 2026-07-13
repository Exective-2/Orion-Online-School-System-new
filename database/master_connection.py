"""
master_connection.py
--------------------
Manages the SQLAlchemy engine and session factory for the **master database**
(``orion_master.db``).  This database is completely separate from any branch
database and holds only:

  * The ``branches`` registry (one row per school branch)
  * The ``branch_admins`` lookup table (username → branch mapping for login routing)
  * The ``system_admins`` table (System Administrator accounts)

Import :func:`get_master_session` wherever you need to query these tables.
Never mix master-DB sessions with branch-DB sessions in the same transaction.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

# Separate declarative base — keeps master-DB models completely isolated from
# branch-DB models which use the ``Base`` defined in ``database.connection``.
MasterBase = declarative_base()

_master_engine = None
_MasterSession = None


# ---------------------------------------------------------------------------
# Engine / session helpers
# ---------------------------------------------------------------------------

def get_master_engine():
    """Return (and lazily create) the SQLAlchemy engine for ``orion_master.db``."""
    global _master_engine
    if _master_engine is None:
        from config import DATA_DIR
        db_path = DATA_DIR / "orion_master.db"
        _master_engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            poolclass=NullPool,
            echo=False,
        )

        @event.listens_for(_master_engine, "connect")
        def _set_pragmas(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA journal_mode=WAL;")
            dbapi_conn.execute("PRAGMA busy_timeout=5000;")

    return _master_engine


def get_master_session():
    """Open and return a new session bound to the master database."""
    global _MasterSession
    if _MasterSession is None:
        engine = get_master_engine()
        _MasterSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _MasterSession()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_master_db() -> None:
    """Create all master-DB tables if they do not already exist."""
    # Import models here to ensure they are registered against MasterBase
    import database.master_models  # noqa: F401 — side-effect import
    engine = get_master_engine()
    MasterBase.metadata.create_all(bind=engine)


def init_master_defaults() -> None:
    """
    Idempotent bootstrap routine called once on application startup.

    Responsibilities:
    1. Ensure the schema exists.
    2. Create the default ``sysadmin`` account if no SystemAdmin rows exist.
    3. If no Branch rows exist, register the pre-existing ``school_management.db``
       as Branch #1 ("Main Campus") — this preserves backward compatibility for
       existing single-school installations.
    """
    init_master_db()

    from database.master_models import SystemAdmin, Branch
    from database.seed import hash_password
    from config import DATA_DIR, config

    session = get_master_session()
    try:
        # --- 1. Default System Admin ---
        if not session.query(SystemAdmin).first():
            sysadmin = SystemAdmin(
                username="sysadmin",
                password_hash=hash_password("sysadmin123"),
                full_name="System Administrator",
                email="",
                is_active=True,
            )
            session.add(sysadmin)
            session.flush()

        # --- 2. Migrate existing single-school DB as Branch #1 ---
        if not session.query(Branch).first():
            existing_db = DATA_DIR / "school_management.db"
            if existing_db.exists():
                branch1 = Branch(
                    name=config.get("school_name", "Main Campus"),
                    code="MAIN",
                    address=config.get("school_address", ""),
                    phone=config.get("school_phone", ""),
                    email=config.get("school_email", ""),
                    db_filename="school_management.db",
                    is_active=True,
                )
                session.add(branch1)
                session.flush()

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[master_connection] init_master_defaults error: {e}")
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Per-branch session helper (for cross-branch reporting — read-only)
# ---------------------------------------------------------------------------

def get_branch_session(db_filename: str):
    """
    Return a **temporary** SQLAlchemy session pointed at a specific branch DB
    file.  Used for cross-branch reporting in the System Admin Portal.

    The caller is responsible for closing the returned session.  The engine
    created here is NOT cached — each call builds a fresh connection.
    """
    from config import DATA_DIR
    from sqlalchemy.orm import sessionmaker as sm
    db_path = DATA_DIR / db_filename
    tmp_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=False,
    )
    TmpSession = sm(autocommit=False, autoflush=False, bind=tmp_engine)
    return TmpSession()
