from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from config import get_db_url

# Base model class
Base = declarative_base()

_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        db_url = get_db_url()
        connect_args = {}
        pool_kwargs = {}
        if db_url.startswith("sqlite"):
            # NullPool: every session.close() truly releases the file lock.
            # This prevents "database is locked" when sequential operations
            # (init_db → seed → wizard admin update) each open a new session.
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
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal()

def init_db():
    from database.models import Base
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    
    # Schema migration to add base_salary column if missing in older SQLite/Postgres setups
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE staff ADD COLUMN base_salary FLOAT DEFAULT 0.0;"))
    except Exception:
        pass # Column already exists or table has not been created yet

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

