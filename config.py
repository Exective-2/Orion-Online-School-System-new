import os
import json
from pathlib import Path
import sys

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
# When running as a PyInstaller-frozen executable (installed app), the .exe
# lives in C:\Program Files\... which is READ-ONLY for normal users.
# All mutable user data (database, config) must go to a writable location.
#
# - APP_DIR  : directory of the .exe / source root (read-only in production)
# - DATA_DIR : writable user-data folder (always has write permission)
#
# Development:  both point to the project root.
# Installed:    APP_DIR = install dir, DATA_DIR = %LOCALAPPDATA%\OrionSMS\
# ---------------------------------------------------------------------------

if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).resolve().parent
    DATA_DIR = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "OrionSMS"
else:
    APP_DIR = Path(__file__).resolve().parent
    DATA_DIR = APP_DIR

# Ensure the data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Keep BASE_DIR as an alias to APP_DIR for backward compatibility
BASE_DIR = APP_DIR

DATABASE_PATH = DATA_DIR / "school_management.db"


# Default configs
DEFAULT_CONFIG = {
    "db_type": "sqlite",  # 'sqlite', 'postgresql', or 'mysql'
    "db_host": "localhost",
    "db_port": 5432,
    "db_name": "school_management",
    "db_user": "postgres",
    "db_password": "",
    "school_name": "Orion Desktop School System",
    "school_motto": "Knowledge, Integrity, Excellence",
    "school_email": "info@orionschool.edu.gh",
    "school_phone": "+233 24 123 4567",
    "school_address": "P.O. Box 45, Accra, Ghana",
    "curriculum": "GES",  # Ghana Education Service
    "active_academic_year_id": 1,
    "active_term_id": 1,
    "theme": "dark",  # 'dark' or 'light'
    "currency": "GHS",  # Ghana Cedi
    "school_logo": "",
    "setup_completed": False,
    "auto_backup_on_open": False,
    "auto_backup_on_close": False,
    "auto_backup_monthly": False,
    "backup_directory": "",
    "last_monthly_backup_date": "",
    "grading_scale": [
        {"grade": "1", "min_score": 80.0, "remark": "Excellent"},
        {"grade": "2", "min_score": 70.0, "remark": "Very Good"},
        {"grade": "3", "min_score": 65.0, "remark": "Good"},
        {"grade": "4", "min_score": 60.0, "remark": "High Average"},
        {"grade": "5", "min_score": 55.0, "remark": "Average"},
        {"grade": "6", "min_score": 50.0, "remark": "Low Average"},
        {"grade": "7", "min_score": 45.0, "remark": "Low"},
        {"grade": "8", "min_score": 40.0, "remark": "Lower"},
        {"grade": "9", "min_score": 0.0, "remark": "Lowest"}
    ]
}

CONFIG_FILE = DATA_DIR / "config.json"

def load_config():
    if not CONFIG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
            # Ensure all keys from DEFAULT_CONFIG exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception:
        return DEFAULT_CONFIG

def save_config(config_dict):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_dict, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

# Load config globally
config = load_config()

def get_db_url():
    db_type = config.get("db_type", "sqlite")
    if db_type == "sqlite":
        return f"sqlite:///{DATABASE_PATH}"
    elif db_type == "postgresql":
        user = config.get("db_user", "postgres")
        pwd = config.get("db_password", "")
        host = config.get("db_host", "localhost")
        port = config.get("db_port", 5432)
        name = config.get("db_name", "school_management")
        return f"postgresql://{user}:{pwd}@{host}:{port}/{name}"
    elif db_type == "mysql":
        user = config.get("db_user", "root")
        pwd = config.get("db_password", "")
        host = config.get("db_host", "localhost")
        port = config.get("db_port", 3306)
        name = config.get("db_name", "school_management")
        return f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{name}"
    return f"sqlite:///{DATABASE_PATH}"
