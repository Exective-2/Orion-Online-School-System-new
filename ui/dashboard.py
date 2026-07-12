from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QListWidget, QListWidgetItem, QProgressBar, QGridLayout,
    QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtCharts import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis, QPieSeries, QPieSlice
from PySide6.QtGui import QPainter, QColor
from database.connection import get_session
from database.models import Student, Staff, Class, Attendance, StudentBill, Announcement
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
        
        ann_title = QLabel("Recent Announcements")
        ann_title.setStyleSheet("font-size: 15px; font-weight: bold; color: #3b82f6;")
        ann_layout.addWidget(ann_title)
        
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
            # Check if user is a Teacher
            is_teacher = False
            if self.user.role:
                is_teacher = self.user.role.name == "Teacher"
                
            # Clear previous layout widgets
            for i in reversed(range(self.kpi_grid.count())):
                widget = self.kpi_grid.itemAt(i).widget()
                if widget:
                    widget.setParent(None)
                    
            # Populate Announcements
            self.announcements_list.clear()
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
                
                from database.models import ClassTeacher, Result, Payslip, Subject
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
