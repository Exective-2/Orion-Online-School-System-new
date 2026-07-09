import sys
from PySide6.QtWidgets import QApplication, QDialog
from database.connection import init_db
from ui.auth import LoginWindow
from ui.main_window import MainWindow

class SchoolManagementApp:
    def __init__(self):
        # Check if setup is completed
        from config import config
        if not config.get("setup_completed", False):
            from ui.setup_wizard import SetupWizardDialog
            self.setup_wizard = SetupWizardDialog()
            if self.setup_wizard.exec() != QDialog.DialogCode.Accepted:
                import sys
                sys.exit(0)
        else:
            # Initialize database tables if already configured
            init_db()
            
            # Execute automated backups (open and monthly periodic check)
            try:
                from utils.backup import run_auto_backup
                run_auto_backup("open")
                run_auto_backup("monthly")
            except Exception as e:
                print(f"Failed to start auto backups: {e}")
            
            
        # Start Auth screen
        self.login_window = LoginWindow()
        self.login_window.login_success.connect(self.show_main_window)
        self.login_window.show()
        
        self.main_window = None
        
    def show_main_window(self, user):
        # Hide auth screen
        self.login_window.hide()
        
        # Start main window
        self.main_window = MainWindow(user)
        self.main_window.logout_requested.connect(self.handle_logout)
        self.main_window.show()
        
    def handle_logout(self):
        # Close main window
        if self.main_window:
            self.main_window.close()
            self.main_window = None
            
        # Re-create and show login screen
        self.login_window = LoginWindow()
        self.login_window.login_success.connect(self.show_main_window)
        self.login_window.show()

def main():
    app = QApplication(sys.argv)
    
    # Start and execute splash screen
    from ui.splash import OrionSplashScreen
    splash = OrionSplashScreen()
    splash.start_loading()
    
    while splash.isVisible():
        app.processEvents()
    
    # Connect aboutToQuit signal for auto-backup on close
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
