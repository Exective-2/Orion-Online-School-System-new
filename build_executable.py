"""
build_executable.py
-------------------
Builds the Orion School Management System as a --onedir PyInstaller package.

Onedir mode is used (NOT onefile) so that sys.executable correctly resolves
to the install directory at runtime, allowing config.json and the database
to be found next to the .exe.

After PyInstaller runs, this script:
  1. Copies a clean config.json (setup_completed = False) into the dist folder
  2. Copies the assets/ folder into the dist folder
  3. Removes any leftover development database from dist

Usage:
    python build_executable.py
"""

import os
import subprocess
import sys
import shutil
import json
from pathlib import Path


def build_app():
    print("=" * 60)
    print("  Orion School Management System — Build Script")
    print("=" * 60)

    base_dir = Path(__file__).resolve().parent
    spec_file = base_dir / "OrionSchoolManagementSystem.spec"
    dist_dir = base_dir / "dist" / "OrionSchoolManagementSystem"

    if not spec_file.exists():
        print(f"ERROR: Spec file not found: {spec_file}")
        sys.exit(1)

    # ── 1. Run PyInstaller using the .spec file ──────────────────────────────
    print("\n[1/3] Running PyInstaller (onedir mode)...")
    cmd = [
        "python", "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        str(spec_file),
    ]
    print(f"  Command: {' '.join(cmd)}\n")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: PyInstaller failed: {e}")
        sys.exit(1)

    # ── 2. Copy clean config.json ─────────────────────────────────────────────
    print("\n[2/3] Writing clean config.json for distribution...")
    config_src = base_dir / "config.json"
    config_dst = dist_dir / "config.json"
    try:
        with open(config_src, "r") as f:
            config_data = json.load(f)
        # Reset to clean install state
        config_data["setup_completed"] = False
        config_data["school_name"] = "Orion Desktop School System"
        config_data["school_logo"] = ""
        config_data["backup_directory"] = ""
        config_data["last_monthly_backup_date"] = ""
        with open(config_dst, "w") as f:
            json.dump(config_data, f, indent=4)
        print(f"  Written: {config_dst}")
    except Exception as e:
        print(f"  WARNING: Could not write clean config.json: {e}")

    # ── 3. Remove dev database from dist (fresh install gets new DB) ──────────
    dev_db = dist_dir / "school_management.db"
    if dev_db.exists():
        dev_db.unlink()
        print(f"  Removed dev database from dist folder.")

    # ── Done ──────────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  BUILD COMPLETE")
    print("=" * 60)
    print(f"\n  Output folder : {dist_dir}")
    print(f"  Next step     : Compile installer.iss with Inno Setup 6")
    print(f"                  --> produces OrionSMS_Setup.exe\n")


if __name__ == "__main__":
    build_app()
