from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import get_db_url

# Base model class
Base = declarative_base()

_engine = None
_SessionLocal = None

def get_engine():
    global _engine
    if _engine is None:
        db_url = get_db_url()
        # For SQLite, enable multi-threading access
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        
        _engine = create_engine(db_url, connect_args=connect_args, echo=False)
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
