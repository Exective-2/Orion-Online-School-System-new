import os
import subprocess
import sys
from pathlib import Path

def build_app():
    print("Preparing executable build...")
    base_dir = Path(__file__).resolve().parent
    main_file = base_dir / "main.py"
    
    if not main_file.exists():
        print(f"Error: {main_file} not found.")
        sys.exit(1)
        
    print("Running PyInstaller...")
    # Build configurations:
    # --onefile: bundle into single executable
    # --windowed: do not open terminal window (GUI only)
    # --add-data: include default config files or assets
    # --name: executable name
    
    # OS-specific settings
    separator = ";" if sys.platform.startswith("win") else ":"
    
    icon_file = base_dir / "assets" / "sms.ico"
    cmd = [
        "python",
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",
        f"--icon={icon_file}" if icon_file.exists() else None,
        "--name=OrionSchoolManagementSystem",
        str(main_file)
    ]
    cmd = [c for c in cmd if c is not None]
    
    print(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        import shutil
        dist_dir = base_dir / 'dist'
        
        # Note: We do NOT copy the development school_management.db database to the dist folder.
        # This ensures the packaged application is a clean installation and initializes a new database during the Setup Wizard.
        
        # Copy config.json if it exists, but reset setup parameters for a clean installation
        config_file = base_dir / "config.json"
        if config_file.exists():
            print("Creating clean config.json for distribution...")
            import json
            try:
                with open(config_file, "r") as f:
                    config_data = json.load(f)
                config_data["setup_completed"] = False
                config_data["school_name"] = "Orion Desktop School System"
                config_data["school_logo"] = ""
                with open(dist_dir / "config.json", "w") as f:
                    json.dump(config_data, f, indent=4)
            except Exception as e:
                print(f"Warning: Failed to copy and reset config.json: {e}")
            
        # Copy assets folder if it exists
        assets_dir = base_dir / "assets"
        if assets_dir.exists():
            print("Copying assets folder to dist folder...")
            shutil.copytree(assets_dir, dist_dir / "assets", dirs_exist_ok=True)
            
        print("\nBuild completed successfully!")
        print(f"The packaged application files are located in: {dist_dir}")
    except subprocess.CalledProcessError as e:
        print(f"\nError: PyInstaller build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_app()
