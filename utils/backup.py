import os
import shutil
import zipfile
import datetime
from pathlib import Path
from config import DATABASE_PATH, config

def create_backup(dest_directory: str) -> tuple[bool, str]:
    """
    Creates a zip backup of the active database file.
    Returns (success, message).
    """
    try:
        db_type = config.get("db_type", "sqlite")
        if db_type != "sqlite":
            return False, "Automated file backups are only supported for SQLite single-school installations."
        
        if not DATABASE_PATH.exists():
            return False, "Database file not found. Nothing to backup."
        
        dest_dir = Path(dest_directory)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"sms_backup_{timestamp}.zip"
        backup_path = dest_dir / backup_filename
        
        # Compress the database file into a zip
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(DATABASE_PATH, arcname=DATABASE_PATH.name)
            
        return True, f"Backup created successfully at: {backup_path}"
    except Exception as e:
        return False, f"Failed to create backup: {str(e)}"

def restore_backup(backup_zip_path: str) -> tuple[bool, str]:
    """
    Restores the database from a backup zip file.
    Warning: Overwrites current database!
    """
    try:
        db_type = config.get("db_type", "sqlite")
        if db_type != "sqlite":
            return False, "Restoring backups from file is only supported for SQLite."
        
        zip_path = Path(backup_zip_path)
        if not zip_path.exists():
            return False, "Backup file does not exist."
        
        # Create a temporary restore directory or unpack directly
        with zipfile.ZipFile(zip_path, "r") as zipf:
            # Check if database file is in the zip
            if DATABASE_PATH.name not in zipf.namelist():
                return False, "Invalid backup file: main database file not found in zip."
            
            # Close existing connections before replacing (handled by caller, but we overwrite file)
            # Create a safety copy of the current DB just in case
            if DATABASE_PATH.exists():
                safety_copy = DATABASE_PATH.with_suffix(".db.bak")
                shutil.copy2(DATABASE_PATH, safety_copy)
            
            try:
                # Extract and overwrite
                zipf.extract(DATABASE_PATH.name, path=DATABASE_PATH.parent)
                
                # Delete safety copy on success
                if safety_copy.exists():
                    os.remove(safety_copy)
                return True, "Database restored successfully."
            except Exception as e:
                # Rollback safety copy if extraction failed
                if safety_copy.exists():
                    shutil.copy2(safety_copy, DATABASE_PATH)
                    os.remove(safety_copy)
                raise e
                
    except Exception as e:
        return False, f"Failed to restore backup: {str(e)}"

def run_auto_backup(event_type: str) -> tuple[bool, str]:
    """
    Executes auto-backup logic based on event_type: 'open', 'close', or 'monthly'.
    Reads settings from config and saves backup if appropriate.
    Returns (executed_bool, message).
    """
    try:
        db_type = config.get("db_type", "sqlite")
        if db_type != "sqlite":
            return False, "Automated backups only supported for SQLite."

        # Check settings
        if event_type == "open":
            if not config.get("auto_backup_on_open", False):
                return False, "Auto-backup on open is disabled."
        elif event_type == "close":
            if not config.get("auto_backup_on_close", False):
                return False, "Auto-backup on close is disabled."
        elif event_type == "monthly":
            if not config.get("auto_backup_monthly", False):
                return False, "Monthly periodic auto-backup is disabled."
            
            # Check if monthly backup is already done for this month
            current_month = datetime.datetime.now().strftime("%Y-%m")
            last_monthly = config.get("last_monthly_backup_date", "")
            if last_monthly == current_month:
                return False, f"Monthly backup for {current_month} already performed."
        else:
            return False, f"Unknown event type: {event_type}"

        # Get target directory
        dest_directory = config.get("backup_directory", "")
        if not dest_directory:
            # Fallback to default backups folder in the workspace
            dest_directory = str(DATABASE_PATH.parent / "backups")
            config["backup_directory"] = dest_directory
            from config import save_config
            save_config(config)

        dest_dir = Path(dest_directory)
        dest_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"sms_auto_backup_{event_type}_{timestamp}.zip"
        backup_path = dest_dir / backup_filename
        
        if not DATABASE_PATH.exists():
            return False, "Database file not found."
            
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(DATABASE_PATH, arcname=DATABASE_PATH.name)
            
        # Update monthly date if event was monthly
        if event_type == "monthly":
            config["last_monthly_backup_date"] = datetime.datetime.now().strftime("%Y-%m")
            from config import save_config
            save_config(config)
            
        # Print info to console for logging/debugging
        print(f"Auto-backup success: {backup_path}")
        return True, f"Auto-backup ({event_type}) completed successfully at: {backup_path}"
    except Exception as e:
        print(f"Auto-backup error ({event_type}): {str(e)}")
        return False, f"Auto-backup failed: {str(e)}"

