import json
from database.connection import get_session
from database.models import SystemSetting
from config import config

def get_branch_setting(key: str, default=None, session=None):
    """Retrieve a setting value for the current active branch database session.
    If JSON serialized, deserialize it; if not present in branch DB, fall back to global config default.
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    try:
        setting = session.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting and setting.value is not None:
            try:
                return json.loads(setting.value)
            except Exception:
                return setting.value
        return config.get(key, default)
    except Exception:
        return config.get(key, default)
    finally:
        if close_session:
            session.close()

def set_branch_setting(key: str, value, session=None):
    """Persist a setting value in the current active branch database session.
    Serializes complex objects/lists/dicts/booleans to JSON strings.
    """
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    try:
        if isinstance(value, (dict, list, bool, int, float)):
            val_str = json.dumps(value)
        else:
            val_str = str(value) if value is not None else ""
            
        setting = session.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            setting.value = val_str
        else:
            setting = SystemSetting(key=key, value=val_str)
            session.add(setting)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error setting branch config '{key}': {e}")
        return False
    finally:
        if close_session:
            session.close()

def get_active_year_id(session=None):
    """Get the active academic year ID for the current branch context."""
    val = get_branch_setting("active_academic_year_id", None, session=session)
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    try:
        from database.models import AcademicYear
        curr_year = session.query(AcademicYear).filter(AcademicYear.is_current == True).first()
        if curr_year:
            return curr_year.id
        first_year = session.query(AcademicYear).first()
        if first_year:
            return first_year.id
    except Exception:
        pass
    finally:
        if close_session:
            session.close()
    return 1

def get_active_term_id(session=None):
    """Get the active term ID for the current branch context."""
    val = get_branch_setting("active_term_id", None, session=session)
    if val is not None:
        try:
            return int(val)
        except (ValueError, TypeError):
            pass
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    try:
        from database.models import Term
        curr_term = session.query(Term).filter(Term.is_current == True).first()
        if curr_term:
            return curr_term.id
        first_term = session.query(Term).first()
        if first_term:
            return first_term.id
    except Exception:
        pass
    finally:
        if close_session:
            session.close()
    return 1

