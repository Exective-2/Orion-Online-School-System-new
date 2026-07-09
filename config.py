import os
import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "school_management.db"

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
}

CONFIG_FILE = BASE_DIR / "config.json"

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
