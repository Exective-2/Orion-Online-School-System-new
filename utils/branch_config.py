import os
import re
import hashlib
import datetime
import json
from database.connection import get_session
from database.models import SystemSetting
from config import config

BRANCH_PROFILE_KEYS = {
    "school_name", "school_motto", "school_tagline", "school_email", 
    "school_phone", "school_address", "gps_address", "school_logo", "school_logo_base64", 
    "headteacher_signature", "headteacher_signature_base64", 
    "curriculum", "currency", "theme", "max_class_score", "max_exam_score",
    "branch_prefix"
}

def get_active_branch_prefix(user=None, session=None) -> str:
    """Determine the branch prefix to be used for generating student IDs.
    
    Resolution order:
    1. 'school_tagline' or 'branch_prefix' stored in the branch's system_settings table.
    2. Branch 'code' from master database using user['branch_id'] or active branch context.
    3. Global config 'school_tagline' or 'branch_code' or 'branch_prefix'.
    4. Default fallback: 'ORION'.
    """
    # 1. Branch database settings
    try:
        tagline = get_branch_setting("school_tagline", None, session=session)
        if not tagline:
            tagline = get_branch_setting("branch_prefix", None, session=session)
        if tagline and str(tagline).strip():
            clean = re.sub(r'[^A-Za-z0-9]', '', str(tagline).strip()).upper()
            if clean:
                return clean
    except Exception:
        pass

    # 2. Master DB Branch record
    try:
        branch_id = None
        if user and isinstance(user, dict) and user.get("branch_id"):
            branch_id = user.get("branch_id")
        else:
            from database.branch_context import get_active_branch_id
            branch_id = get_active_branch_id()

        if branch_id:
            from database.master_connection import get_master_session
            from database.master_models import Branch
            m_session = get_master_session()
            try:
                branch = m_session.query(Branch).filter(Branch.id == branch_id).first()
                if branch and branch.code:
                    clean_code = re.sub(r'[^A-Za-z0-9]', '', str(branch.code).strip()).upper()
                    if clean_code:
                        return clean_code
            finally:
                m_session.close()
    except Exception:
        pass

    # 3. Global config
    cfg_val = config.get("school_tagline") or config.get("branch_code") or config.get("branch_prefix")
    if cfg_val and str(cfg_val).strip():
        clean_cfg = re.sub(r'[^A-Za-z0-9]', '', str(cfg_val).strip()).upper()
        if clean_cfg:
            return clean_cfg

    return "ORION"

def generate_next_student_id(session, user=None, custom_id=None) -> str:
    """Generates a unique student ID prefixed with the active branch prefix.
    Format: {PREFIX}-{YY}-{RANDOM_HEX_4}
    Ensures that the generated ID does not collide with existing student records in the branch.
    """
    if custom_id and str(custom_id).strip():
        return str(custom_id).strip()

    from database.models import Student
    prefix = get_active_branch_prefix(user=user, session=session)
    year_suffix = datetime.datetime.now().strftime("%y")

    for _ in range(30):
        rand_code = hashlib.sha256(os.urandom(16)).hexdigest()[:4].upper()
        candidate = f"{prefix}-{year_suffix}-{rand_code}"
        exists = session.query(Student.id).filter(Student.id == candidate).first()
        if not exists:
            return candidate

    # In case of high collision density, append timestamp component
    ts_suffix = str(int(datetime.datetime.now().timestamp()))[-4:]
    return f"{prefix}-{year_suffix}-{ts_suffix}"

def get_branch_setting(key: str, default=None, session=None):
    """Retrieve a setting value for the current active branch database session.
    If JSON serialized, deserialize it; if not present in branch DB, return default for branch-specific keys.
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
        
        # Branch-specific branding/profile keys should NEVER inherit global config values from other branches
        if key in BRANCH_PROFILE_KEYS:
            return default if default is not None else ""

        return config.get(key, default)
    except Exception:
        if key in BRANCH_PROFILE_KEYS:
            return default if default is not None else ""
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

