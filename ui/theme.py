# Theme configurations for the School Management System (SMS)

DARK_THEME = """
QMainWindow, QDialog, QMessageBox, QInputDialog {
    background-color: #0b0f19;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
    color: #e2e8f0;
}
QFrame#sidebar {
    background-color: #0f172a;
    border-right: 1px solid #1e293b;
}
QFrame#header {
    background-color: #0f172a;
    border-bottom: 1px solid #1e293b;
}
QFrame#card {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
}
QLabel#title_label {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#header_title {
    font-size: 20px;
    font-weight: bold;
    color: #3b82f6;
}
QLabel#stat_val {
    font-size: 26px;
    font-weight: bold;
    color: #f8fafc;
}
QLabel#stat_label {
    font-size: 12px;
    color: #94a3b8;
}
QLineEdit, QTextEdit {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px;
    color: #f8fafc;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #3b82f6;
}
QComboBox {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #0f172a;
    border: 1px solid #334155;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton#secondary_btn {
    background-color: #334155;
    color: #f8fafc;
    border: 1px solid #475569;
}
QPushButton#secondary_btn:hover {
    background-color: #475569;
}
QTableWidget QPushButton {
    padding: 2px 6px;
    font-size: 11px;
    font-weight: normal;
    min-width: 40px;
    min-height: 24px;
    max-height: 24px;
}
QTableWidget QLineEdit {
    padding: 3px 8px;
    font-size: 12px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#danger_btn {
    background-color: #ef4444;
    color: #ffffff;
}
QPushButton#danger_btn:hover {
    background-color: #dc2626;
}
QPushButton#sidebar_btn {
    background-color: transparent;
    color: #94a3b8;
    text-align: left;
    padding: 10px 15px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: normal;
}
QPushButton#sidebar_btn:hover {
    background-color: #1e293b;
    color: #ffffff;
}
QPushButton#sidebar_btn[active="true"] {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
}
QTableWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    gridline-color: #334155;
    color: #f8fafc;
}
QTableWidget::item {
    padding: 6px 12px;
}
QTableWidget::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #334155;
    font-weight: bold;
}
QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #475569;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 6px;
    background-color: #1e293b;
}
QTabBar::tab {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1e293b;
    color: #ffffff;
    border-bottom: none;
}
QMenu {
    background-color: #0f172a;
    border: 1px solid #334155;
}
QMenu::item {
    background: transparent;
    color: #e2e8f0;
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
}
QDateEdit {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QCalendarWidget QWidget {
    background-color: #0f172a;
    color: #e2e8f0;
}
QCalendarWidget QAbstractItemView {
    background-color: #0f172a;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
"""

LIGHT_THEME = """
QMainWindow, QDialog, QMessageBox, QInputDialog {
    background-color: #f8fafc;
}
QWidget {
    color: #334155;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
    color: #334155;
}
QFrame#sidebar {
    background-color: #ffffff;
    border-right: 1px solid #e2e8f0;
}
QFrame#header {
    background-color: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}
QFrame#card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
}
QLabel#title_label {
    font-size: 18px;
    font-weight: bold;
    color: #0f172a;
}
QLabel#header_title {
    font-size: 20px;
    font-weight: bold;
    color: #2563eb;
}
QLabel#stat_val {
    font-size: 26px;
    font-weight: bold;
    color: #0f172a;
}
QLabel#stat_label {
    font-size: 12px;
    color: #64748b;
}
QLineEdit, QTextEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 8px;
    color: #0f172a;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #2563eb;
}
QComboBox {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    color: #0f172a;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QPushButton#secondary_btn {
    background-color: #f1f5f9;
    color: #334155;
    border: 1px solid #cbd5e1;
}
QPushButton#secondary_btn:hover {
    background-color: #e2e8f0;
}
QTableWidget QPushButton {
    padding: 2px 6px;
    font-size: 11px;
    font-weight: normal;
    min-width: 40px;
    min-height: 24px;
    max-height: 24px;
}
QTableWidget QLineEdit {
    padding: 3px 8px;
    font-size: 12px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#danger_btn {
    background-color: #ef4444;
    color: #ffffff;
}
QPushButton#danger_btn:hover {
    background-color: #dc2626;
}
QPushButton#sidebar_btn {
    background-color: transparent;
    color: #64748b;
    text-align: left;
    padding: 10px 15px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: normal;
}
QPushButton#sidebar_btn:hover {
    background-color: #f1f5f9;
    color: #0f172a;
}
QPushButton#sidebar_btn[active="true"] {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: bold;
}
QTableWidget {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    gridline-color: #e2e8f0;
    color: #334155;
}
QTableWidget::item {
    padding: 6px 12px;
}
QTableWidget::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #e2e8f0;
    font-weight: bold;
}
QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    background-color: #ffffff;
}
QTabBar::tab {
    background-color: #f8fafc;
    color: #64748b;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    color: #0f172a;
    border-bottom: none;
}
QMenu {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
}
QMenu::item {
    background: transparent;
    color: #334155;
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #2563eb;
    color: #ffffff;
}
QDateEdit {
    background-color: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    padding: 6px 12px;
    color: #0f172a;
}
QCalendarWidget QWidget {
    background-color: #ffffff;
    color: #334155;
}
QCalendarWidget QAbstractItemView {
    background-color: #ffffff;
    selection-background-color: #2563eb;
    selection-color: #ffffff;
}
"""

def get_theme_stylesheet(theme_name: str) -> str:
    if theme_name.lower() == "light":
        return LIGHT_THEME
    return DARK_THEME

EMERALD_THEME = """
QMainWindow, QDialog, QMessageBox, QInputDialog {
    background-color: #05140f;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
    color: #e2e8f0;
}
QFrame#sidebar {
    background-color: #030f0a;
    border-right: 1px solid #14402e;
}
QFrame#header {
    background-color: #030f0a;
    border-bottom: 1px solid #14402e;
}
QFrame#card {
    background-color: #0d291e;
    border: 1px solid #14402e;
    border-radius: 8px;
}
QLabel#title_label {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#header_title {
    font-size: 20px;
    font-weight: bold;
    color: #10b981;
}
QLabel#stat_val {
    font-size: 26px;
    font-weight: bold;
    color: #f8fafc;
}
QLabel#stat_label {
    font-size: 12px;
    color: #a7f3d0;
}
QLineEdit, QTextEdit {
    background-color: #030f0a;
    border: 1px solid #14402e;
    border-radius: 6px;
    padding: 8px;
    color: #f8fafc;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #10b981;
}
QComboBox {
    background-color: #030f0a;
    border: 1px solid #14402e;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #030f0a;
    border: 1px solid #14402e;
    selection-background-color: #10b981;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #10b981;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #059669;
}
QPushButton:pressed {
    background-color: #047857;
}
QPushButton#secondary_btn {
    background-color: #0d291e;
    color: #e2e8f0;
    border: 1px solid #14402e;
}
QPushButton#secondary_btn:hover {
    background-color: #14402e;
}
QTableWidget QPushButton {
    padding: 2px 6px;
    font-size: 11px;
    font-weight: normal;
    min-width: 40px;
    min-height: 24px;
    max-height: 24px;
}
QTableWidget QLineEdit {
    padding: 3px 8px;
    font-size: 12px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#danger_btn {
    background-color: #ef4444;
    color: #ffffff;
}
QPushButton#danger_btn:hover {
    background-color: #dc2626;
}
QPushButton#sidebar_btn {
    background-color: transparent;
    color: #a7f3d0;
    text-align: left;
    padding: 10px 15px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: normal;
}
QPushButton#sidebar_btn:hover {
    background-color: #0d291e;
    color: #ffffff;
}
QPushButton#sidebar_btn[active="true"] {
    background-color: #10b981;
    color: #ffffff;
    font-weight: bold;
}
QTableWidget {
    background-color: #0d291e;
    border: 1px solid #14402e;
    border-radius: 6px;
    gridline-color: #14402e;
    color: #f8fafc;
}
QTableWidget::item {
    padding: 6px 12px;
}
QTableWidget::item:selected {
    background-color: #10b981;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #030f0a;
    color: #a7f3d0;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #14402e;
    font-weight: bold;
}
QScrollBar:vertical {
    border: none;
    background: #030f0a;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #14402e;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QTabWidget::pane {
    border: 1px solid #14402e;
    border-radius: 6px;
    background-color: #0d291e;
}
QTabBar::tab {
    background-color: #030f0a;
    color: #a7f3d0;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #0d291e;
    color: #ffffff;
    border-bottom: none;
}
QMenu {
    background-color: #030f0a;
    border: 1px solid #14402e;
}
QMenu::item {
    background: transparent;
    color: #e2e8f0;
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #10b981;
    color: #ffffff;
}
QDateEdit {
    background-color: #030f0a;
    border: 1px solid #14402e;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QCalendarWidget QWidget {
    background-color: #030f0a;
    color: #e2e8f0;
}
QCalendarWidget QAbstractItemView {
    background-color: #030f0a;
    selection-background-color: #10b981;
    selection-color: #ffffff;
}
"""

SAPPHIRE_THEME = """
QMainWindow, QDialog, QMessageBox, QInputDialog {
    background-color: #060b13;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
    color: #e2e8f0;
}
QFrame#sidebar {
    background-color: #0b111e;
    border-right: 1px solid #1e2e4f;
}
QFrame#header {
    background-color: #0b111e;
    border-bottom: 1px solid #1e2e4f;
}
QFrame#card {
    background-color: #111a2e;
    border: 1px solid #1e2e4f;
    border-radius: 8px;
}
QLabel#title_label {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#header_title {
    font-size: 20px;
    font-weight: bold;
    color: #3b82f6;
}
QLabel#stat_val {
    font-size: 26px;
    font-weight: bold;
    color: #f8fafc;
}
QLabel#stat_label {
    font-size: 12px;
    color: #93c5fd;
}
QLineEdit, QTextEdit {
    background-color: #0b111e;
    border: 1px solid #1e2e4f;
    border-radius: 6px;
    padding: 8px;
    color: #f8fafc;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #3b82f6;
}
QComboBox {
    background-color: #0b111e;
    border: 1px solid #1e2e4f;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #0b111e;
    border: 1px solid #1e2e4f;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #3b82f6;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #2563eb;
}
QPushButton:pressed {
    background-color: #1d4ed8;
}
QPushButton#secondary_btn {
    background-color: #111a2e;
    color: #e2e8f0;
    border: 1px solid #1e2e4f;
}
QPushButton#secondary_btn:hover {
    background-color: #1e2e4f;
}
QTableWidget QPushButton {
    padding: 2px 6px;
    font-size: 11px;
    font-weight: normal;
    min-width: 40px;
    min-height: 24px;
    max-height: 24px;
}
QTableWidget QLineEdit {
    padding: 3px 8px;
    font-size: 12px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#danger_btn {
    background-color: #ef4444;
    color: #ffffff;
}
QPushButton#danger_btn:hover {
    background-color: #dc2626;
}
QPushButton#sidebar_btn {
    background-color: transparent;
    color: #93c5fd;
    text-align: left;
    padding: 10px 15px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: normal;
}
QPushButton#sidebar_btn:hover {
    background-color: #111a2e;
    color: #ffffff;
}
QPushButton#sidebar_btn[active="true"] {
    background-color: #3b82f6;
    color: #ffffff;
    font-weight: bold;
}
QTableWidget {
    background-color: #111a2e;
    border: 1px solid #1e2e4f;
    border-radius: 6px;
    gridline-color: #1e2e4f;
    color: #f8fafc;
}
QTableWidget::item {
    padding: 6px 12px;
}
QTableWidget::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #0b111e;
    color: #93c5fd;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #1e2e4f;
    font-weight: bold;
}
QScrollBar:vertical {
    border: none;
    background: #0b111e;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #1e2e4f;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QTabWidget::pane {
    border: 1px solid #1e2e4f;
    border-radius: 6px;
    background-color: #111a2e;
}
QTabBar::tab {
    background-color: #0b111e;
    color: #93c5fd;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #111a2e;
    color: #ffffff;
    border-bottom: none;
}
QMenu {
    background-color: #0b111e;
    border: 1px solid #1e2e4f;
}
QMenu::item {
    background: transparent;
    color: #e2e8f0;
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #3b82f6;
    color: #ffffff;
}
QDateEdit {
    background-color: #0b111e;
    border: 1px solid #1e2e4f;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QCalendarWidget QWidget {
    background-color: #0b111e;
    color: #e2e8f0;
}
QCalendarWidget QAbstractItemView {
    background-color: #0b111e;
    selection-background-color: #3b82f6;
    selection-color: #ffffff;
}
"""

AMBER_THEME = """
QMainWindow, QDialog, QMessageBox, QInputDialog {
    background-color: #150f07;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QDialog QLabel, QMessageBox QLabel, QInputDialog QLabel {
    color: #e2e8f0;
}
QFrame#sidebar {
    background-color: #1f150b;
    border-right: 1px solid #4a331a;
}
QFrame#header {
    background-color: #1f150b;
    border-bottom: 1px solid #4a331a;
}
QFrame#card {
    background-color: #2c1e10;
    border: 1px solid #4a331a;
    border-radius: 8px;
}
QLabel#title_label {
    font-size: 18px;
    font-weight: bold;
    color: #ffffff;
}
QLabel#header_title {
    font-size: 20px;
    font-weight: bold;
    color: #f59e0b;
}
QLabel#stat_val {
    font-size: 26px;
    font-weight: bold;
    color: #f8fafc;
}
QLabel#stat_label {
    font-size: 12px;
    color: #fde68a;
}
QLineEdit, QTextEdit {
    background-color: #1f150b;
    border: 1px solid #4a331a;
    border-radius: 6px;
    padding: 8px;
    color: #f8fafc;
}
QLineEdit:focus, QTextEdit:focus {
    border: 1px solid #f59e0b;
}
QComboBox {
    background-color: #1f150b;
    border: 1px solid #4a331a;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #1f150b;
    border: 1px solid #4a331a;
    selection-background-color: #f59e0b;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #f59e0b;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #d97706;
}
QPushButton:pressed {
    background-color: #b45309;
}
QPushButton#secondary_btn {
    background-color: #2c1e10;
    color: #e2e8f0;
    border: 1px solid #4a331a;
}
QPushButton#secondary_btn:hover {
    background-color: #4a331a;
}
QTableWidget QPushButton {
    padding: 2px 6px;
    font-size: 11px;
    font-weight: normal;
    min-width: 40px;
    min-height: 24px;
    max-height: 24px;
}
QTableWidget QLineEdit {
    padding: 3px 8px;
    font-size: 12px;
    min-height: 24px;
    max-height: 24px;
}
QPushButton#danger_btn {
    background-color: #ef4444;
    color: #ffffff;
}
QPushButton#danger_btn:hover {
    background-color: #dc2626;
}
QPushButton#sidebar_btn {
    background-color: transparent;
    color: #fde68a;
    text-align: left;
    padding: 10px 15px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: normal;
}
QPushButton#sidebar_btn:hover {
    background-color: #2c1e10;
    color: #ffffff;
}
QPushButton#sidebar_btn[active="true"] {
    background-color: #f59e0b;
    color: #ffffff;
    font-weight: bold;
}
QTableWidget {
    background-color: #2c1e10;
    border: 1px solid #4a331a;
    border-radius: 6px;
    gridline-color: #4a331a;
    color: #f8fafc;
}
QTableWidget::item {
    padding: 6px 12px;
}
QTableWidget::item:selected {
    background-color: #f59e0b;
    color: #ffffff;
}
QHeaderView::section {
    background-color: #1f150b;
    color: #fde68a;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #4a331a;
    font-weight: bold;
}
QScrollBar:vertical {
    border: none;
    background: #1f150b;
    width: 8px;
    margin: 0px;
}
QScrollBar::handle:vertical {
    background: #4a331a;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}
QTabWidget::pane {
    border: 1px solid #4a331a;
    border-radius: 6px;
    background-color: #2c1e10;
}
QTabBar::tab {
    background-color: #1f150b;
    color: #fde68a;
    padding: 8px 16px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #2c1e10;
    color: #ffffff;
    border-bottom: none;
}
QMenu {
    background-color: #1f150b;
    border: 1px solid #4a331a;
}
QMenu::item {
    background: transparent;
    color: #e2e8f0;
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #f59e0b;
    color: #ffffff;
}
QDateEdit {
    background-color: #1f150b;
    border: 1px solid #4a331a;
    border-radius: 6px;
    padding: 6px 12px;
    color: #f8fafc;
}
QCalendarWidget QWidget {
    background-color: #1f150b;
    color: #e2e8f0;
}
QCalendarWidget QAbstractItemView {
    background-color: #1f150b;
    selection-background-color: #f59e0b;
    selection-color: #ffffff;
}
"""

def get_theme_stylesheet(theme_name: str) -> str:
    name = theme_name.lower()
    if name == "light":
        return LIGHT_THEME
    elif name == "emerald":
        return EMERALD_THEME
    elif name == "sapphire":
        return SAPPHIRE_THEME
    elif name == "amber":
        return AMBER_THEME
    return DARK_THEME

