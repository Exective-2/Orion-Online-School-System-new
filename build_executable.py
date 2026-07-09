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
    
    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=OrionSchoolManagementSystem",
        str(main_file)
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("\nBuild completed successfully!")
        print(f"The standalone executable is located in: {base_dir / 'dist'}")
    except subprocess.CalledProcessError as e:
        print(f"\nError: PyInstaller build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_app()
