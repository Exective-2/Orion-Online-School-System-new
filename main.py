import sys
from PySide6.QtWidgets import QApplication, QDialog
from database.connection import init_db
from ui.auth import LoginWindow
from ui.main_window import MainWindow


class SchoolManagementApp:
    def __init__(self):
        from config import config

        # ── 1. First-run setup wizard ──────────────────────────────────
        if not config.get("setup_completed", False):
            from ui.setup_wizard import SetupWizardDialog
            self.setup_wizard = SetupWizardDialog()
            if self.setup_wizard.exec() != QDialog.DialogCode.Accepted:
                sys.exit(0)
        else:
            # Initialize branch database tables
            init_db()

            # Auto-backups on open
            try:
                from utils.backup import run_auto_backup
                run_auto_backup("open")
                run_auto_backup("monthly")
            except Exception as e:
                print(f"Failed to start auto backups: {e}")

        # ── 2. Initialize the master database (idempotent) ─────────────
        # This creates orion_master.db, seeds the sysadmin account, and
        # registers school_management.db as Branch #1 if it has not been
        # registered yet (backward-compatibility migration).
        try:
            from database.master_connection import init_master_defaults
            init_master_defaults()
        except Exception as e:
            print(f"[main] Master DB init error: {e}")

        # ── 3. Show login window ───────────────────────────────────────
        self.login_window = LoginWindow()
        self.login_window.login_success.connect(self.show_main_window)
        self.login_window.sysadmin_login.connect(self.show_system_admin_portal)
        self.login_window.show()

        self.main_window = None
        self.admin_portal = None

    # ------------------------------------------------------------------
    # Window routing
    # ------------------------------------------------------------------

    def show_main_window(self, user):
        """Open the regular school management window for a branch user."""
        self.login_window.hide()
        self.main_window = MainWindow(user)
        self.main_window.logout_requested.connect(self.handle_logout)
        self.main_window.show()

    def show_system_admin_portal(self, sysadmin):
        """Open the System Administrator portal (branch/admin management)."""
        self.login_window.hide()
        from ui.system_admin_portal import SystemAdminPortal
        self.admin_portal = SystemAdminPortal(sysadmin)
        self.admin_portal.logout_requested.connect(self.handle_logout)
        self.admin_portal.show()

    def handle_logout(self):
        """Close any open window, clear branch context, and return to login."""
        # Clear the active branch context so the engine is reset
        try:
            from database.branch_context import clear_active_branch
            clear_active_branch()
        except Exception:
            pass

        if self.main_window:
            self.main_window.close()
            self.main_window = None
        if self.admin_portal:
            self.admin_portal.close()
            self.admin_portal = None

        # Re-create login window (refreshes branch list)
        self.login_window = LoginWindow()
        self.login_window.login_success.connect(self.show_main_window)
        self.login_window.sysadmin_login.connect(self.show_system_admin_portal)
        self.login_window.show()


def main():
    app = QApplication(sys.argv)

    # Splash screen
    from ui.splash import OrionSplashScreen
    splash = OrionSplashScreen()
    splash.start_loading()
    while splash.isVisible():
        app.processEvents()

    # Auto-backup on application quit
    def on_app_quit():
        try:
            from utils.backup import run_auto_backup
            run_auto_backup("close")
        except Exception as e:
            print(f"Failed to run auto backup on close: {e}")

    app.aboutToQuit.connect(on_app_quit)

    sms_app = SchoolManagementApp()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
