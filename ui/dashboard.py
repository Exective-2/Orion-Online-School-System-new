from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QListWidget, QListWidgetItem, QProgressBar, QGridLayout,
    QScrollArea, QPushButton, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis, QPieSeries, QPieSlice
from PySide6.QtGui import QPainter, QColor
from database.connection import get_session
from database.models import (
    Student, Staff, Class, Attendance, StudentBill, Announcement,
    Payslip, Payment, Expense, Inventory, StockTransaction, LibraryBook, LibraryIssue,
    ClassTeacher, Result, Subject
)
import datetime
from config import config

class DashboardPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Scroll Area for responsive dashboard
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)
        
        # 1. Grid of KPI cards
        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(20)
        scroll_layout.addLayout(self.kpi_grid)
        
        # Actions layout for download buttons
        self.actions_layout = QHBoxLayout()
        scroll_layout.addLayout(self.actions_layout)

        
        # 2. Charts and lists split section
        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)
        
        # Financial / Activity chart card
        self.chart_frame = QFrame()
        self.chart_frame.setObjectName("card")
        chart_layout = QVBoxLayout(self.chart_frame)
        chart_layout.setContentsMargins(15, 15, 15, 15)
        
        self.chart_title = QLabel("Term fee Collection Analytics (GHS)")
        self.chart_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b82f6;")
        chart_layout.addWidget(self.chart_title)
        
        self.chart_view = QChartView()
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.chart_view.setMinimumHeight(300)
        chart_layout.addWidget(self.chart_view)
        
        split_layout.addWidget(self.chart_frame, stretch=3)
        
        # Enrollment / Attendance chart card
        self.enrollment_chart_frame = QFrame()
        self.enrollment_chart_frame.setObjectName("card")
        enrollment_chart_layout = QVBoxLayout(self.enrollment_chart_frame)
        enrollment_chart_layout.setContentsMargins(15, 15, 15, 15)
        
        self.enrollment_chart_title = QLabel("Student Distribution")
        self.enrollment_chart_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #10b981;")
        enrollment_chart_layout.addWidget(self.enrollment_chart_title)
        
        self.enrollment_chart_view = QChartView()
        self.enrollment_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.enrollment_chart_view.setMinimumHeight(300)
        enrollment_chart_layout.addWidget(self.enrollment_chart_view)
        
        split_layout.addWidget(self.enrollment_chart_frame, stretch=3)
        
        # Announcements and news list
        ann_frame = QFrame()
        ann_frame.setObjectName("card")
        ann_layout = QVBoxLayout(ann_frame)
        ann_layout.setContentsMargins(15, 15, 15, 15)
        
        self.ann_title = QLabel("Recent Announcements")
        self.ann_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b82f6;")
        ann_layout.addWidget(self.ann_title)
        
        self.announcements_list = QListWidget()
        self.announcements_list.setStyleSheet("background-color: transparent; border: none;")
        self.announcements_list.setWordWrap(True)
        ann_layout.addWidget(self.announcements_list)
        
        split_layout.addWidget(ann_frame, stretch=2)
        
        scroll_layout.addLayout(split_layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        self.refresh()
        
    def create_kpi_card(self, title, val, color_hex, row, col):
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"border-left: 5px solid {color_hex};")
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)
        
        lbl_title = QLabel(title)
        lbl_title.setObjectName("stat_label")
        
        lbl_val = QLabel(str(val))
        lbl_val.setObjectName("stat_val")
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_val)
        
        self.kpi_grid.addWidget(card, row, col)

    def refresh(self):
        session = get_session()
        try:
            # Check user role and profile
            is_teacher = False
            role_name = ""
            if self.user.role:
                role_name = self.user.role.name
                is_teacher = role_name == "Teacher"
                
            # Clear previous layout widgets
            for i in reversed(range(self.kpi_grid.count())):
                widget = self.kpi_grid.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
                    
            # Clear actions layout first
            while self.actions_layout.count():
                item = self.actions_layout.takeAt(0)
                if item:
                    widget = item.widget()
                    if widget:
                        widget.setParent(None)
                    
            # Populate Announcements/Alerts
            self.announcements_list.clear()
            
            if role_name == "Librarian":
                self.ann_title.setText("Overdue Book Alerts")
                self.ann_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #ef4444;")
                today = datetime.date.today()
                overdues = session.query(LibraryIssue).filter(
                    LibraryIssue.return_date == None,
                    LibraryIssue.due_date < today
                ).order_by(LibraryIssue.due_date.asc()).limit(5).all()
                
                if not overdues:
                    item = QListWidgetItem("No overdue books.")
                    self.announcements_list.addItem(item)
                else:
                    for issue in overdues:
                        item = QListWidgetItem()
                        widget = QWidget()
                        w_layout = QVBoxLayout(widget)
                        w_layout.setContentsMargins(5, 5, 5, 5)
                        w_layout.setSpacing(2)
                        
                        active_theme = config.get("theme", "dark").lower()
                        is_light = active_theme == "light"
                        
                        borrower_name = f"{issue.student.first_name} {issue.student.last_name}" if issue.student else "Unknown Student"
                        title_lbl = QLabel(f"{issue.book.title} ({borrower_name})")
                        title_lbl.setStyleSheet("font-weight: bold; color: #ef4444;" if is_light else "font-weight: bold; color: #fca5a5;")
                        title_lbl.setWordWrap(True)
                        
                        days_late = (today - issue.due_date).days
                        body_lbl = QLabel(f"Due: {issue.due_date.strftime('%Y-%m-%d')} ({days_late} days overdue)")
                        body_lbl.setWordWrap(True)
                        body_lbl.setStyleSheet("color: #334155; font-size: 12px;" if is_light else "color: #94a3b8; font-size: 12px;")
                        
                        parent_phone = issue.student.parent.phone if (issue.student and issue.student.parent) else "N/A"
                        target_lbl = QLabel(f"Parent Contact: {parent_phone}")
                        target_lbl.setStyleSheet("color: #64748b; font-size: 10px;")
                        
                        w_layout.addWidget(title_lbl)
                        w_layout.addWidget(body_lbl)
                        w_layout.addWidget(target_lbl)
                        
                        item.setSizeHint(widget.sizeHint())
                        self.announcements_list.addItem(item)
                        self.announcements_list.setItemWidget(item, widget)
            else:
                self.ann_title.setText("Recent Announcements")
                self.ann_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b82f6;")
                announcements = session.query(Announcement).order_by(Announcement.created_at.desc()).limit(5).all()
                for ann in announcements:
                    item = QListWidgetItem()
                    widget = QWidget()
                    w_layout = QVBoxLayout(widget)
                    w_layout.setContentsMargins(5, 5, 5, 5)
                    w_layout.setSpacing(2)
                    
                    active_theme = config.get("theme", "dark").lower()
                    is_light = active_theme == "light"
                    
                    title_lbl = QLabel(ann.title)
                    title_lbl.setStyleSheet("font-weight: bold; color: #0f172a;" if is_light else "font-weight: bold; color: #f8fafc;")
                    
                    body_lbl = QLabel(ann.content)
                    body_lbl.setWordWrap(True)
                    body_lbl.setStyleSheet("color: #334155; font-size: 12px;" if is_light else "color: #94a3b8; font-size: 12px;")
                    
                    target_lbl = QLabel(f"Target: {ann.target_audience} | {ann.created_at.strftime('%Y-%m-%d')}")
                    target_lbl.setStyleSheet("color: #64748b; font-size: 10px;")
                    
                    w_layout.addWidget(title_lbl)
                    w_layout.addWidget(body_lbl)
                    w_layout.addWidget(target_lbl)
                    
                    item.setSizeHint(widget.sizeHint())
                    self.announcements_list.addItem(item)
                    self.announcements_list.setItemWidget(item, widget)
                
            if is_teacher:
                self.chart_title.setText("Class Subject Performance Averages (Marks)")
                
                ay_id = config.get("active_academic_year_id", 1)
                
                teacher_staff = self.user.staff_profile
                ct_record = None
                if teacher_staff:
                    ct_record = session.query(ClassTeacher).filter(
                        ClassTeacher.staff_id == teacher_staff.id,
                        ClassTeacher.academic_year_id == ay_id
                    ).first()
                    
                class_name = "Not Assigned"
                class_students_count = 0
                if ct_record and ct_record.class_obj:
                    class_name = ct_record.class_obj.name
                    class_students_count = session.query(Student).filter(
                        Student.class_id == ct_record.class_id,
                        Student.status == "Active"
                    ).count()
                    
                latest_net_pay = "GHS 0.00"
                pay_period = "N/A"
                if teacher_staff:
                    latest_payslip = session.query(Payslip).filter(
                        Payslip.staff_id == teacher_staff.id
                    ).order_by(Payslip.payment_date.desc()).first()
                    if latest_payslip:
                        latest_net_pay = f"GHS {latest_payslip.net_salary:.2f}"
                        pay_period = latest_payslip.pay_period
                        
                # Create Teacher KPI Cards
                self.create_kpi_card("My Assigned Class", class_name, "#3b82f6", 0, 0)
                self.create_kpi_card("Students in Class", class_students_count, "#10b981", 0, 1)
                self.create_kpi_card("My Net Salary (Latest)", latest_net_pay, "#8b5cf6", 0, 2)
                self.create_kpi_card("Latest Pay Period", pay_period, "#f59e0b", 0, 3)
                
                # Fetch Subject Averages for the Teacher's class
                subjects = []
                subject_averages = {}
                if ct_record and ct_record.class_obj:
                    subjects = session.query(Subject).filter(Subject.class_level == ct_record.class_obj.level).all()
                    student_ids = [s.id for s in session.query(Student).filter(Student.class_id == ct_record.class_id).all()]
                    if student_ids and subjects:
                        for subj in subjects:
                            avg_score = session.query(Result.total_score).filter(
                                Result.student_id.in_(student_ids),
                                Result.subject_id == subj.id
                            ).all()
                            if avg_score:
                                vals = [v[0] for v in avg_score if v[0] is not None]
                                if vals:
                                    subject_averages[subj.name] = sum(vals) / len(vals)
                                    
                # Setup teacher bar chart
                series = QBarSeries()
                categories = []
                bar_set = QBarSet("Average Mark")
                bar_set.setColor(QColor("#3b82f6"))
                
                if subject_averages:
                    for s_name, s_avg in subject_averages.items():
                        categories.append(s_name)
                        bar_set.append(s_avg)
                else:
                    categories.append("No Data")
                    bar_set.append(0)
                    
                series.append(bar_set)
                
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle(f"Class Subject Averages - {class_name}")
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                active_theme = config.get("theme", "dark").lower()
                if active_theme == "light":
                    chart.setBackgroundBrush(QColor("#ffffff"))
                    chart.setTitleBrush(QColor("#0f172a"))
                    chart.legend().setLabelColor(QColor("#334155"))
                else:
                    bg_color = "#1e293b"
                    if active_theme == "emerald":
                        bg_color = "#0d291e"
                    elif active_theme == "sapphire":
                        bg_color = "#111a2e"
                    elif active_theme == "amber":
                        bg_color = "#2c1e10"
                    chart.setBackgroundBrush(QColor(bg_color))
                    chart.setTitleBrush(QColor("#f8fafc"))
                    chart.legend().setLabelColor(QColor("#f8fafc"))
                    
                axis_x = QBarCategoryAxis()
                axis_x.append(categories)
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                
                axis_y = QValueAxis()
                axis_y.setRange(0, 100)
                chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
                
                self.chart_view.setChart(chart)
                
                # Render Teacher attendance overview pie chart
                self.enrollment_chart_title.setText("Class Attendance Overview")
                attendance_stats = {"Present": 0, "Absent": 0, "Late": 0}
                if ct_record and ct_record.class_obj:
                    class_student_ids = [s.id for s in session.query(Student).filter(Student.class_id == ct_record.class_id).all()]
                    if class_student_ids:
                        att_records = session.query(Attendance).filter(
                            Attendance.student_id.in_(class_student_ids)
                        ).all()
                        for att in att_records:
                            if att.status in attendance_stats:
                                attendance_stats[att.status] += 1
                                
                pie_series = QPieSeries()
                has_att_data = False
                for status, count in attendance_stats.items():
                    if count > 0:
                        has_att_data = True
                    pie_series.append(f"{status} ({count})", count)
                if not has_att_data:
                    pie_series.append("No Attendance Logged", 1)
                    
                pie_chart = QChart()
                pie_chart.addSeries(pie_series)
                pie_chart.setTitle("Overall Attendance Distribution")
                pie_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                # Theme styling
                bg_color = "#1e293b"
                if active_theme == "emerald":
                    bg_color = "#0d291e"
                elif active_theme == "sapphire":
                    bg_color = "#111a2e"
                elif active_theme == "amber":
                    bg_color = "#2c1e10"
                    
                if active_theme == "light":
                    pie_chart.setBackgroundBrush(QColor("#ffffff"))
                    pie_chart.setTitleBrush(QColor("#0f172a"))
                    pie_chart.legend().setLabelColor(QColor("#334155"))
                else:
                    pie_chart.setBackgroundBrush(QColor(bg_color))
                    pie_chart.setTitleBrush(QColor("#f8fafc"))
                    pie_chart.legend().setLabelColor(QColor("#f8fafc"))
                    
                self.enrollment_chart_view.setChart(pie_chart)
                
            elif role_name in ["Accountant", "Bursar"]:
                self.chart_title.setText("Billing & Collection Overview (GHS)")
                
                revenue_sum = session.query(Payment.amount).all()
                expense_sum = session.query(Expense.amount).all()
                
                total_rev = sum(r[0] for r in revenue_sum) if revenue_sum else 0.0
                total_exp = sum(e[0] for e in expense_sum) if expense_sum else 0.0
                net_diff = total_rev - total_exp
                
                bursar_staff = self.user.staff_profile
                latest_net_pay = "No payslip"
                if bursar_staff:
                    latest_payslip = session.query(Payslip).filter(
                        Payslip.staff_id == bursar_staff.id
                    ).order_by(Payslip.payment_date.desc()).first()
                    if latest_payslip:
                        latest_net_pay = f"GHS {latest_payslip.net_salary:.2f} ({latest_payslip.pay_period})"
                        
                # Create Bursar KPI cards
                self.create_kpi_card("Income Collected", f"GHS {total_rev:.2f}", "#10b981", 0, 0)
                self.create_kpi_card("Total Expenses", f"GHS {total_exp:.2f}", "#ef4444", 0, 1)
                self.create_kpi_card("Surplus / Deficit", f"GHS {net_diff:.2f}", "#3b82f6", 0, 2)
                self.create_kpi_card("Bursar Payroll Info", latest_net_pay, "#8b5cf6", 0, 3)
                
                # Render collection chart
                billed_sum = session.query(StudentBill.amount_billed).all()
                paid_sum = session.query(StudentBill.amount_paid).all()
                total_billed = sum(b[0] for b in billed_sum) if billed_sum else 0
                total_paid = sum(p[0] for p in paid_sum) if paid_sum else 0
                total_outstanding = total_billed - total_paid
                
                set_billed = QBarSet("Billed")
                set_billed.append(total_billed)
                set_billed.setColor(QColor("#3b82f6"))
                
                set_paid = QBarSet("Paid")
                set_paid.append(total_paid)
                set_paid.setColor(QColor("#10b981"))
                
                set_outstanding = QBarSet("Outstanding")
                set_outstanding.append(total_outstanding)
                set_outstanding.setColor(QColor("#ef4444"))
                
                series = QBarSeries()
                series.append(set_billed)
                series.append(set_paid)
                series.append(set_outstanding)
                
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle("Billing & Collection Overview")
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                active_theme = config.get("theme", "dark").lower()
                bg_color = "#1e293b"
                if active_theme == "emerald":
                    bg_color = "#0d291e"
                elif active_theme == "sapphire":
                    bg_color = "#111a2e"
                elif active_theme == "amber":
                    bg_color = "#2c1e10"
                    
                if active_theme == "light":
                    chart.setBackgroundBrush(QColor("#ffffff"))
                    chart.setTitleBrush(QColor("#0f172a"))
                    chart.legend().setLabelColor(QColor("#334155"))
                else:
                    chart.setBackgroundBrush(QColor(bg_color))
                    chart.setTitleBrush(QColor("#f8fafc"))
                    chart.legend().setLabelColor(QColor("#f8fafc"))
                    
                axis_x = QBarCategoryAxis()
                axis_x.append(["Total Summary"])
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                
                axis_y = QValueAxis()
                max_val = max(total_billed, 1000)
                axis_y.setRange(0, max_val * 1.1)
                chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
                
                self.chart_view.setChart(chart)
                
                # Render Expenses by category pie chart
                self.enrollment_chart_title.setText("Expenses by Category")
                expenses = session.query(Expense).all()
                expense_categories = {}
                for e in expenses:
                    expense_categories[e.category] = expense_categories.get(e.category, 0.0) + e.amount
                    
                pie_series = QPieSeries()
                if expense_categories:
                    for cat, amt in expense_categories.items():
                        pie_series.append(f"{cat} (GHS {amt:.2f})", amt)
                else:
                    pie_series.append("No Expenses Logged", 1)
                    
                pie_chart = QChart()
                pie_chart.addSeries(pie_series)
                pie_chart.setTitle("Operational Expenses Breakdown")
                pie_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                if active_theme == "light":
                    pie_chart.setBackgroundBrush(QColor("#ffffff"))
                    pie_chart.setTitleBrush(QColor("#0f172a"))
                    pie_chart.legend().setLabelColor(QColor("#334155"))
                else:
                    pie_chart.setBackgroundBrush(QColor(bg_color))
                    pie_chart.setTitleBrush(QColor("#f8fafc"))
                    pie_chart.legend().setLabelColor(QColor("#f8fafc"))
                    
                self.enrollment_chart_view.setChart(pie_chart)
                
            elif role_name == "Storekeeper":
                self.chart_title.setText("Top Item Stock Levels")
                
                total_catalog_items = session.query(Inventory).count()
                total_stock_qty = sum(item[0] for item in session.query(Inventory.available_quantity).all() if item[0] is not None)
                low_stock_count = session.query(Inventory).filter(
                    Inventory.available_quantity <= 5,
                    Inventory.available_quantity > 0
                ).count()
                out_of_stock_count = session.query(Inventory).filter(
                    Inventory.available_quantity == 0
                ).count()
                
                store_staff = self.user.staff_profile
                latest_net_pay = "GHS 0.00"
                if store_staff:
                    latest_payslip = session.query(Payslip).filter(
                        Payslip.staff_id == store_staff.id
                    ).order_by(Payslip.payment_date.desc()).first()
                    if latest_payslip:
                        latest_net_pay = f"GHS {latest_payslip.net_salary:.2f}"
                        
                # Create Storekeeper KPI cards
                self.create_kpi_card("Total Catalogue Items", total_catalog_items, "#3b82f6", 0, 0)
                self.create_kpi_card("Total Stock Quantity", total_stock_qty, "#10b981", 0, 1)
                self.create_kpi_card("Low / Out of Stock", f"{low_stock_count} / {out_of_stock_count}", "#ef4444", 0, 2)
                self.create_kpi_card("My Net Salary (Latest)", latest_net_pay, "#8b5cf6", 0, 3)
                
                # Render stock levels bar chart for top items
                top_items = session.query(Inventory).order_by(Inventory.total_quantity.desc()).limit(5).all()
                
                series = QBarSeries()
                set_avail = QBarSet("Available Qty")
                set_avail.setColor(QColor("#10b981"))
                set_tot = QBarSet("Total Qty")
                set_tot.setColor(QColor("#3b82f6"))
                
                categories = []
                max_qty = 0
                if top_items:
                    for item in top_items:
                        categories.append(item.item_name[:12])
                        set_avail.append(item.available_quantity)
                        set_tot.append(item.total_quantity)
                        max_qty = max(max_qty, item.total_quantity)
                else:
                    categories.append("No Items")
                    set_avail.append(0)
                    set_tot.append(0)
                    
                series.append(set_avail)
                series.append(set_tot)
                
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle("Top 5 Items Stock Levels")
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                active_theme = config.get("theme", "dark").lower()
                bg_color = "#1e293b"
                if active_theme == "emerald":
                    bg_color = "#0d291e"
                elif active_theme == "sapphire":
                    bg_color = "#111a2e"
                elif active_theme == "amber":
                    bg_color = "#2c1e10"
                    
                if active_theme == "light":
                    chart.setBackgroundBrush(QColor("#ffffff"))
                    chart.setTitleBrush(QColor("#0f172a"))
                    chart.legend().setLabelColor(QColor("#334155"))
                else:
                    chart.setBackgroundBrush(QColor(bg_color))
                    chart.setTitleBrush(QColor("#f8fafc"))
                    chart.legend().setLabelColor(QColor("#f8fafc"))
                    
                axis_x = QBarCategoryAxis()
                axis_x.append(categories)
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                
                axis_y = QValueAxis()
                axis_y.setRange(0, max(max_qty, 10) * 1.1)
                chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
                
                self.chart_view.setChart(chart)
                
                # Render stock category distribution pie chart
                self.enrollment_chart_title.setText("Stock Category Distribution")
                assets_qty = sum(item[0] for item in session.query(Inventory.available_quantity).filter(Inventory.category == "Asset").all() if item[0] is not None)
                supplies_qty = sum(item[0] for item in session.query(Inventory.available_quantity).filter(Inventory.category == "Supply").all() if item[0] is not None)
                
                pie_series = QPieSeries()
                if assets_qty or supplies_qty:
                    pie_series.append(f"Assets ({assets_qty})", assets_qty)
                    pie_series.append(f"Supplies ({supplies_qty})", supplies_qty)
                else:
                    pie_series.append("No Stock", 1)
                    
                pie_chart = QChart()
                pie_chart.addSeries(pie_series)
                pie_chart.setTitle("Available Stock by Category")
                pie_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                if active_theme == "light":
                    pie_chart.setBackgroundBrush(QColor("#ffffff"))
                    pie_chart.setTitleBrush(QColor("#0f172a"))
                    pie_chart.legend().setLabelColor(QColor("#334155"))
                else:
                    pie_chart.setBackgroundBrush(QColor(bg_color))
                    pie_chart.setTitleBrush(QColor("#f8fafc"))
                    pie_chart.legend().setLabelColor(QColor("#f8fafc"))
                self.enrollment_chart_view.setChart(pie_chart)
                
                # Add action buttons
                btn_excel = QPushButton("Download Stock Report (Excel)")
                btn_excel.setObjectName("secondary_btn")
                btn_excel.clicked.connect(self.download_inventory_excel)
                btn_pdf = QPushButton("Download Stock Report (PDF)")
                btn_pdf.setObjectName("primary_btn")
                btn_pdf.clicked.connect(self.download_inventory_pdf)
                self.actions_layout.addWidget(btn_excel)
                self.actions_layout.addWidget(btn_pdf)
                self.actions_layout.addStretch()
                
            elif role_name == "Librarian":
                self.chart_title.setText("Book Catalogue Categories")
                
                total_books = session.query(LibraryBook).count()
                total_copies = sum(b[0] for b in session.query(LibraryBook.total_copies).all() if b[0] is not None)
                active_borrows = session.query(LibraryIssue).filter(LibraryIssue.return_date == None).count()
                
                today = datetime.date.today()
                overdue_count = session.query(LibraryIssue).filter(
                    LibraryIssue.return_date == None,
                    LibraryIssue.due_date < today
                ).count()
                
                lib_staff = self.user.staff_profile
                latest_net_pay = "GHS 0.00"
                if lib_staff:
                    latest_payslip = session.query(Payslip).filter(
                        Payslip.staff_id == lib_staff.id
                    ).order_by(Payslip.payment_date.desc()).first()
                    if latest_payslip:
                        latest_net_pay = f"GHS {latest_payslip.net_salary:.2f}"
                        
                # Create Librarian KPI cards
                self.create_kpi_card("Unique Book Titles", total_books, "#3b82f6", 0, 0)
                self.create_kpi_card("Total Book Copies", total_copies, "#10b981", 0, 1)
                self.create_kpi_card("Overdue Lending Alerts", overdue_count, "#ef4444", 0, 2)
                self.create_kpi_card("My Net Salary (Latest)", latest_net_pay, "#8b5cf6", 0, 3)
                
                # Pie Chart 1: Books grouped by category
                books_by_cat = {}
                for b in session.query(LibraryBook.category).all():
                    cat = b[0] or "General"
                    books_by_cat[cat] = books_by_cat.get(cat, 0) + 1
                    
                pie_series = QPieSeries()
                if books_by_cat:
                    for cat, cnt in books_by_cat.items():
                        pie_series.append(f"{cat} ({cnt})", cnt)
                else:
                    pie_series.append("No Books", 1)
                    
                chart = QChart()
                chart.addSeries(pie_series)
                chart.setTitle("Books in Catalogue by Category")
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                active_theme = config.get("theme", "dark").lower()
                bg_color = "#1e293b"
                if active_theme == "emerald":
                    bg_color = "#0d291e"
                elif active_theme == "sapphire":
                    bg_color = "#111a2e"
                elif active_theme == "amber":
                    bg_color = "#2c1e10"
                    
                if active_theme == "light":
                    chart.setBackgroundBrush(QColor("#ffffff"))
                    chart.setTitleBrush(QColor("#0f172a"))
                    chart.legend().setLabelColor(QColor("#334155"))
                else:
                    chart.setBackgroundBrush(QColor(bg_color))
                    chart.setTitleBrush(QColor("#f8fafc"))
                    chart.legend().setLabelColor(QColor("#f8fafc"))
                self.chart_view.setChart(chart)
                
                # Pie Chart 2: Books lending status availability
                self.enrollment_chart_title.setText("Book Copy Availability Status")
                avail_copies = sum(b[0] for b in session.query(LibraryBook.available_copies).all() if b[0] is not None)
                lent_copies = total_copies - avail_copies
                
                pie_series2 = QPieSeries()
                if total_copies > 0:
                    pie_series2.append(f"Available ({avail_copies})", avail_copies)
                    pie_series2.append(f"Issued/Lent ({lent_copies})", lent_copies)
                else:
                    pie_series2.append("No Inventory", 1)
                    
                pie_chart = QChart()
                pie_chart.addSeries(pie_series2)
                pie_chart.setTitle("Lending Status Overview")
                pie_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                if active_theme == "light":
                    pie_chart.setBackgroundBrush(QColor("#ffffff"))
                    pie_chart.setTitleBrush(QColor("#0f172a"))
                    pie_chart.legend().setLabelColor(QColor("#334155"))
                else:
                    pie_chart.setBackgroundBrush(QColor(bg_color))
                    pie_chart.setTitleBrush(QColor("#f8fafc"))
                    pie_chart.legend().setLabelColor(QColor("#f8fafc"))
                self.enrollment_chart_view.setChart(pie_chart)
                
                # Add action buttons
                btn_excel = QPushButton("Download Books Report (Excel)")
                btn_excel.setObjectName("secondary_btn")
                btn_excel.clicked.connect(self.download_library_excel)
                btn_pdf = QPushButton("Download Books Report (PDF)")
                btn_pdf.setObjectName("primary_btn")
                btn_pdf.clicked.connect(self.download_library_pdf)
                self.actions_layout.addWidget(btn_excel)
                self.actions_layout.addWidget(btn_pdf)
                self.actions_layout.addStretch()
                
            else:
                self.chart_title.setText("Term fee Collection Analytics (GHS)")
                
                total_students = session.query(Student).filter(Student.status == "Active").count()
                total_staff = session.query(Staff).filter(Staff.status == "Active").count()
                total_classes = session.query(Class).count()
                
                # Today's attendance percentage
                today = datetime.date.today()
                present_today = session.query(Attendance).filter(
                    Attendance.date == today, 
                    Attendance.student_id != None,
                    Attendance.status == "Present"
                ).count()
                total_marked_today = session.query(Attendance).filter(
                    Attendance.date == today,
                    Attendance.student_id != None
                ).count()
                
                attendance_rate = "N/A"
                if total_marked_today > 0:
                    attendance_rate = f"{int((present_today / total_marked_today) * 100)}%"
                    
                # Add Admin KPI cards
                self.create_kpi_card("Total Active Students", total_students, "#3b82f6", 0, 0)
                self.create_kpi_card("Registered Staff", total_staff, "#10b981", 0, 1)
                self.create_kpi_card("Total Class Streams", total_classes, "#8b5cf6", 0, 2)
                self.create_kpi_card("Today's Attendance Rate", attendance_rate, "#f59e0b", 0, 3)
                
                # Render collection chart
                # Summarize billed fees vs paid fees
                billed_sum = session.query(StudentBill.amount_billed).all()
                paid_sum = session.query(StudentBill.amount_paid).all()
                
                total_billed = sum(b[0] for b in billed_sum) if billed_sum else 0
                total_paid = sum(p[0] for p in paid_sum) if paid_sum else 0
                total_outstanding = total_billed - total_paid
                
                # Setup bar chart
                set_billed = QBarSet("Billed")
                set_billed.append(total_billed)
                set_billed.setColor(QColor("#3b82f6"))
                
                set_paid = QBarSet("Paid")
                set_paid.append(total_paid)
                set_paid.setColor(QColor("#10b981"))
                
                set_outstanding = QBarSet("Outstanding")
                set_outstanding.append(total_outstanding)
                set_outstanding.setColor(QColor("#ef4444"))
                
                series = QBarSeries()
                series.append(set_billed)
                series.append(set_paid)
                series.append(set_outstanding)
                
                chart = QChart()
                chart.addSeries(series)
                chart.setTitle("Billing & Collection Overview")
                chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                # Dark mode theme styling for charts
                active_theme = config.get("theme", "dark").lower()
                if active_theme == "light":
                    chart.setBackgroundBrush(QColor("#ffffff"))
                    chart.setTitleBrush(QColor("#0f172a"))
                    chart.legend().setLabelColor(QColor("#334155"))
                else:
                    bg_color = "#1e293b"
                    if active_theme == "emerald":
                        bg_color = "#0d291e"
                    elif active_theme == "sapphire":
                        bg_color = "#111a2e"
                    elif active_theme == "amber":
                        bg_color = "#2c1e10"
                    chart.setBackgroundBrush(QColor(bg_color))
                    chart.setTitleBrush(QColor("#f8fafc"))
                    chart.legend().setLabelColor(QColor("#f8fafc"))
                    
                axis_x = QBarCategoryAxis()
                axis_x.append(["Total Summary"])
                chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
                series.attachAxis(axis_x)
                
                axis_y = QValueAxis()
                max_val = max(total_billed, 1000)
                axis_y.setRange(0, max_val * 1.1)
                chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
                series.attachAxis(axis_y)
                
                self.chart_view.setChart(chart)
                
                # Render Admin student distribution pie chart
                self.enrollment_chart_title.setText("Student Class Distribution")
                classes = session.query(Class).all()
                class_students = {}
                for c in classes:
                    cnt = session.query(Student).filter(Student.class_id == c.id, Student.status == "Active").count()
                    if cnt > 0:
                        class_students[c.name] = cnt
                        
                pie_series = QPieSeries()
                if class_students:
                    for c_name, count in class_students.items():
                        pie_series.append(f"{c_name} ({count})", count)
                else:
                    pie_series.append("No Active Students", 1)
                    
                pie_chart = QChart()
                pie_chart.addSeries(pie_series)
                pie_chart.setTitle("Active Students by Class Stream")
                pie_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
                
                bg_color = "#1e293b"
                if active_theme == "emerald":
                    bg_color = "#0d291e"
                elif active_theme == "sapphire":
                    bg_color = "#111a2e"
                elif active_theme == "amber":
                    bg_color = "#2c1e10"
                    
                if active_theme == "light":
                    pie_chart.setBackgroundBrush(QColor("#ffffff"))
                    pie_chart.setTitleBrush(QColor("#0f172a"))
                    pie_chart.legend().setLabelColor(QColor("#334155"))
                else:
                    pie_chart.setBackgroundBrush(QColor(bg_color))
                    pie_chart.setTitleBrush(QColor("#f8fafc"))
                    pie_chart.legend().setLabelColor(QColor("#f8fafc"))
                    
                self.enrollment_chart_view.setChart(pie_chart)
                
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
        finally:
            session.close()

    def download_inventory_excel(self):
        from utils.exporter import export_to_excel
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Inventory Excel Report", "inventory_report.xlsx", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
            
        session = get_session()
        try:
            items = session.query(Inventory).all()
            if not items:
                QMessageBox.warning(self, "No Data", "No inventory items to export.")
                return
            data = [{
                "item_id": item.id,
                "item_name": item.item_name,
                "category": item.category,
                "description": item.description or "",
                "total_quantity": item.total_quantity,
                "available_quantity": item.available_quantity,
                "unit": item.unit,
                "condition": item.condition or "Good",
                "location": item.location or "N/A"
            } for item in items]
            success, msg = export_to_excel(data, file_path, "Inventory")
            if success:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.critical(self, "Error", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")
        finally:
            session.close()

    def download_inventory_pdf(self):
        from utils.pdf_generator import generate_inventory_report_pdf
        import os
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Inventory PDF Report", "inventory_report.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
            
        session = get_session()
        try:
            items = session.query(Inventory).all()
            if not items:
                QMessageBox.warning(self, "No Data", "No inventory items to export.")
                return
            headers = ["ID", "Item Name", "Category", "Total Qty", "Available Qty", "Unit", "Condition", "Location"]
            rows = [[
                item.id,
                item.item_name,
                item.category,
                item.total_quantity,
                item.available_quantity,
                item.unit,
                item.condition or "Good",
                item.location or "N/A"
            ] for item in items]
            success, filepath = generate_inventory_report_pdf(headers, rows, file_path)
            if success:
                QMessageBox.information(self, "Success", f"Inventory PDF Report generated at:\n{filepath}")
                if os.path.exists(filepath):
                    os.startfile(filepath)
            else:
                QMessageBox.critical(self, "Error", f"Failed to generate PDF: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")
        finally:
            session.close()

    def download_library_excel(self):
        from utils.exporter import export_to_excel
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Library Books Excel Report", "library_books_report.xlsx", "Excel Files (*.xlsx)"
        )
        if not file_path:
            return
            
        session = get_session()
        try:
            books = session.query(LibraryBook).all()
            if not books:
                QMessageBox.warning(self, "No Data", "No library books to export.")
                return
            data = [{
                "book_id": b.id,
                "title": b.title,
                "author": b.author,
                "isbn": b.isbn or "N/A",
                "category": b.category or "General",
                "total_copies": b.total_copies,
                "available_copies": b.available_copies,
                "location": b.location or "N/A"
            } for b in books]
            success, msg = export_to_excel(data, file_path, "Library Books")
            if success:
                QMessageBox.information(self, "Success", msg)
            else:
                QMessageBox.critical(self, "Error", msg)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")
        finally:
            session.close()

    def download_library_pdf(self):
        from utils.pdf_generator import generate_library_report_pdf
        import os
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Library PDF Report", "library_books_report.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
            
        session = get_session()
        try:
            books = session.query(LibraryBook).all()
            if not books:
                QMessageBox.warning(self, "No Data", "No books in library to export.")
                return
            headers = ["ID", "Title", "Author", "ISBN", "Category", "Total Copies", "Available Copies", "Location"]
            rows = [[
                b.id,
                b.title,
                b.author,
                b.isbn or "N/A",
                b.category or "General",
                b.total_copies,
                b.available_copies,
                b.location or "N/A"
            ] for b in books]
            success, filepath = generate_library_report_pdf(headers, rows, file_path)
            if success:
                QMessageBox.information(self, "Success", f"Library Books PDF Report generated at:\n{filepath}")
                if os.path.exists(filepath):
                    os.startfile(filepath)
            else:
                QMessageBox.critical(self, "Error", f"Failed to generate PDF: {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")
        finally:
            session.close()

