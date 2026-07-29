import contextvars
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from config import get_db_url, DATA_DIR

# Base model class
Base = declarative_base()

_engine = None
_SessionLocal = None

# A dictionary to cache branch engines and sessionmakers for web multi-tenancy
_branch_engines = {}
_branch_session_makers = {}

# Context variable to hold the active database URL for the current request context
current_db_url = contextvars.ContextVar("current_db_url", default=None)

def get_engine():
    global _engine
    
    # Check request context (for multi-tenant web app)
    db_url = current_db_url.get()
    if db_url is not None:
        if db_url not in _branch_engines:
            connect_args = {}
            pool_kwargs = {}
            if db_url.startswith("sqlite"):
                connect_args = {"check_same_thread": False}
                pool_kwargs = {"poolclass": NullPool}
            
            engine = create_engine(
                db_url,
                connect_args=connect_args,
                echo=False,
                **pool_kwargs
            )
            
            if db_url.startswith("sqlite"):
                @event.listens_for(engine, "connect")
                def set_wal_mode(dbapi_conn, connection_record):
                    dbapi_conn.execute("PRAGMA journal_mode=WAL;")
                    dbapi_conn.execute("PRAGMA busy_timeout=5000;")
            
            _branch_engines[db_url] = engine
            _branch_session_makers[db_url] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            init_db()
            
        return _branch_engines[db_url]

    # Fallback to default desktop engine
    if _engine is None:
        db_url = get_db_url()
        connect_args = {}
        pool_kwargs = {}
        if db_url.startswith("sqlite"):
            # NullPool: every session.close() truly releases the file lock.
            connect_args = {"check_same_thread": False}
            pool_kwargs = {"poolclass": NullPool}
            
        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            echo=False,
            **pool_kwargs
        )
        
        # Enable WAL mode for SQLite so readers never block writers
        if db_url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def set_wal_mode(dbapi_conn, connection_record):
                dbapi_conn.execute("PRAGMA journal_mode=WAL;")
                dbapi_conn.execute("PRAGMA busy_timeout=5000;")
                
    return _engine


def get_session():
    global _SessionLocal
    db_url = current_db_url.get()
    if db_url is not None:
        get_engine()  # ensures engine & sessionmaker exist
        return _branch_session_makers[db_url]()

    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal()

def init_db():
    from database.models import Base
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    
    # Schema migration to add missing columns in older SQLite/Postgres setups
    from sqlalchemy import text
    with engine.begin() as conn:
        for col_def in [
            "ALTER TABLE staff ADD COLUMN base_salary FLOAT DEFAULT 0.0;",
            "ALTER TABLE student_report_remarks ADD COLUMN student_interest VARCHAR(250);",
            "ALTER TABLE student_report_remarks ADD COLUMN attitude_score VARCHAR(100);",
            "ALTER TABLE student_report_remarks ADD COLUMN overall_score FLOAT DEFAULT 0.0;",
            "ALTER TABLE student_report_remarks ADD COLUMN average_score FLOAT DEFAULT 0.0;",
            "ALTER TABLE student_report_remarks ADD COLUMN class_rank INTEGER;",
            "ALTER TABLE student_report_remarks ADD COLUMN total_subjects INTEGER DEFAULT 0;",
            "ALTER TABLE fees ADD COLUMN is_system_fee INTEGER DEFAULT 0;",
            "ALTER TABLE expenses ADD COLUMN transaction_type VARCHAR(20) DEFAULT 'Expense';",
            "ALTER TABLE expenses ADD COLUMN payment_method VARCHAR(50) DEFAULT 'Cash';",
            "ALTER TABLE expenses ADD COLUMN reference_no VARCHAR(100);"
        ]:
            try:
                conn.execute(text(col_def))
            except Exception:
                pass

def reset_engine():
    """Dispose the current engine and clear the singleton references.

    Call this after a full system reset (drop_all / create_all) so that the
    next call to get_session() / get_engine() opens fresh connections instead
    of reusing pooled connections that may still hold write locks.
    """
    global _engine, _SessionLocal
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass
    _engine = None
    _SessionLocal = None


def close_branch_engine(db_filename: str) -> None:
    """Dispose cached SQLAlchemy engine for a branch database file to release file locks."""
    global _branch_engines, _branch_session_makers
    if not db_filename:
        return
    db_url = f"sqlite:///{DATA_DIR}/{db_filename}"
    engine = _branch_engines.pop(db_url, None)
    _branch_session_makers.pop(db_url, None)
    if engine is not None:
        try:
            engine.dispose()
        except Exception:
            pass


def set_active_branch_db(db_path) -> None:
    """
    Point the branch-DB engine at *db_path* and reset the session factory.

    Call this immediately after a successful login for a branch user so that
    all subsequent ``get_session()`` calls automatically use the correct
    branch database file.

    Parameters
    ----------
    db_path : str or pathlib.Path
        Absolute path to the branch's SQLite file.
    """
    global _engine, _SessionLocal
    db_url = f"sqlite:///{db_path}"
    current_db_url.set(db_url)
    
    # Dispose the old engine if one exists
    if _engine is not None:
        try:
            _engine.dispose()
        except Exception:
            pass

    _engine = create_engine(
        db_url,
        connect_args={"check_same_thread": False},
        poolclass=NullPool,
        echo=False,
    )

    @event.listens_for(_engine, "connect")
    def _set_pragmas(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA journal_mode=WAL;")
        dbapi_conn.execute("PRAGMA busy_timeout=5000;")

    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

