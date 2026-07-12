from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QTabWidget, QFileDialog
)
from PySide6.QtCore import Qt
from database.connection import get_session
from database.models import Student, Subject, Class, Examination, Result, SMSLog
from utils.pdf_generator import generate_report_card
from config import config

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

class ExamsPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.updating_table = False # Prevention flag for infinite loops on edit change
        self.init_ui()
        
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        self.tabs = QTabWidget()
        
        # --- TAB 1: Grading Sheet ---
        self.grading_tab = QWidget()
        layout = QVBoxLayout(self.grading_tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Top controls
        top_bar = QFrame()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.setSpacing(10)
        
        top_bar_layout.addWidget(QLabel("Examination:"))
        self.exam_combo = QComboBox()
        top_bar_layout.addWidget(self.exam_combo, stretch=2)
        
        top_bar_layout.addWidget(QLabel("Class Stream:"))
        self.class_combo = QComboBox()
        self.class_combo.currentIndexChanged.connect(self.load_subjects_combo)
        self.class_combo.currentIndexChanged.connect(self.clear_table)
        top_bar_layout.addWidget(self.class_combo, stretch=2)
        
        top_bar_layout.addWidget(QLabel("Subject:"))
        self.subject_combo = QComboBox()
        self.subject_combo.currentIndexChanged.connect(self.clear_table)
        top_bar_layout.addWidget(self.subject_combo, stretch=2)
        
        load_btn = QPushButton("Load Mark Sheet")
        load_btn.setObjectName("secondary_btn")
        load_btn.clicked.connect(self.load_mark_sheet)
        top_bar_layout.addWidget(load_btn)
        
        layout.addWidget(top_bar)
        
        # Grid table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Student ID", "Student Name", "Class Score (30%)", "Exam Score (70%)", "Total (100)", "Grade", "Remarks"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self.handle_cell_edit)
        layout.addWidget(self.table)
        
        # Bottom controls
        bottom_bar = QHBoxLayout()
        
        save_btn = QPushButton("Save Marks")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self.save_marks)
        bottom_bar.addWidget(save_btn)
        
        rank_btn = QPushButton("Compute Class Ranks")
        rank_btn.setObjectName("secondary_btn")
        rank_btn.clicked.connect(self.compute_class_ranks)
        bottom_bar.addWidget(rank_btn)
        
        print_reports_btn = QPushButton("Print Terminal Reports")
        print_reports_btn.setObjectName("secondary_btn")
        print_reports_btn.clicked.connect(self.print_class_report_cards)
        bottom_bar.addWidget(print_reports_btn)
        
        sms_grades_btn = QPushButton("SMS Grades to Parents")
        sms_grades_btn.setObjectName("secondary_btn")
        sms_grades_btn.clicked.connect(self.sms_class_grades)
        bottom_bar.addWidget(sms_grades_btn)
        
        bottom_bar.addStretch()
        layout.addLayout(bottom_bar)
        
        self.tabs.addTab(self.grading_tab, "Mark Sheet & Grading")
        
        # --- TAB 2: Academic Analytics ---
        self.analytics_tab = QWidget()
        self.init_analytics_ui()
        self.tabs.addTab(self.analytics_tab, "Academic Analytics")
        
        main_layout.addWidget(self.tabs)
        
        self.load_combos()
        
    def load_combos(self):
        session = get_session()
        try:
            # Exams
            exams = session.query(Examination).all()
            self.exam_combo.clear()
            self.an_exam_combo.clear()
            for e in exams:
                self.exam_combo.addItem(e.name, e.id)
                self.an_exam_combo.addItem(e.name, e.id)
                
            # Classes
            classes = session.query(Class).all()
            self.class_combo.clear()
            self.an_class_combo.clear()
            for c in classes:
                self.class_combo.addItem(c.name, c.id)
                self.an_class_combo.addItem(c.name, c.id)
                
            self.load_subjects_combo()
            self.update_analytics_subjects()
        finally:
            session.close()

    def init_analytics_ui(self):
        a_layout = QVBoxLayout(self.analytics_tab)
        a_layout.setContentsMargins(15, 15, 15, 15)
        a_layout.setSpacing(15)
        
        # Top filters for analytics
        filter_bar = QFrame()
        fb_layout = QHBoxLayout(filter_bar)
        fb_layout.setContentsMargins(0, 0, 0, 0)
        fb_layout.setSpacing(10)
        
        fb_layout.addWidget(QLabel("Examination:"))
        self.an_exam_combo = QComboBox()
        self.an_exam_combo.currentIndexChanged.connect(self.update_analytics)
        fb_layout.addWidget(self.an_exam_combo, stretch=2)
        
        fb_layout.addWidget(QLabel("Class Stream:"))
        self.an_class_combo = QComboBox()
        self.an_class_combo.currentIndexChanged.connect(self.update_analytics_subjects)
        self.an_class_combo.currentIndexChanged.connect(self.update_analytics)
        fb_layout.addWidget(self.an_class_combo, stretch=2)
        
        fb_layout.addWidget(QLabel("Subject:"))
        self.an_subject_combo = QComboBox()
        self.an_subject_combo.currentIndexChanged.connect(self.update_analytics)
        fb_layout.addWidget(self.an_subject_combo, stretch=2)
        
        refresh_btn = QPushButton("Refresh Charts")
        refresh_btn.setObjectName("secondary_btn")
        refresh_btn.clicked.connect(self.update_analytics)
        fb_layout.addWidget(refresh_btn)
        
        fb_layout.addStretch()
        a_layout.addWidget(filter_bar)
        
        # Split layout for charts
        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(20)
        
        # 1. Subject Averages Canvas
        self.averages_figure = Figure(figsize=(5, 4), dpi=100)
        self.averages_canvas = FigureCanvas(self.averages_figure)
        charts_layout.addWidget(self.averages_canvas)
        
        # 2. Grade Distribution Canvas
        self.distribution_figure = Figure(figsize=(5, 4), dpi=100)
        self.distribution_canvas = FigureCanvas(self.distribution_figure)
        charts_layout.addWidget(self.distribution_canvas)
        
        a_layout.addLayout(charts_layout)

    def update_analytics_subjects(self):
        class_id = self.an_class_combo.currentData()
        if not class_id:
            return
            
        session = get_session()
        try:
            self.an_subject_combo.blockSignals(True)
            self.an_subject_combo.clear()
            self.an_subject_combo.addItem("All Subjects", None)
            
            cls = session.query(Class).filter(Class.id == class_id).first()
            if cls:
                subjects = session.query(Subject).filter(Subject.class_level == cls.level).all()
                for subj in subjects:
                    self.an_subject_combo.addItem(subj.name, subj.id)
            self.an_subject_combo.blockSignals(False)
        finally:
            session.close()

    def update_analytics(self):
        exam_id = self.an_exam_combo.currentData()
        class_id = self.an_class_combo.currentData()
        subj_id = self.an_subject_combo.currentData()
        
        if not exam_id or not class_id:
            self.averages_figure.clear()
            self.distribution_figure.clear()
            self.averages_canvas.draw()
            self.distribution_canvas.draw()
            return
            
        session = get_session()
        try:
            # 1. Fetch Subject Averages
            results = session.query(Result).filter(
                Result.examination_id == exam_id,
                Result.class_id == class_id
            ).all()
            
            subj_totals = {}
            for r in results:
                s_name = r.subject.name
                if s_name not in subj_totals:
                    subj_totals[s_name] = []
                subj_totals[s_name].append(r.total_score)
                
            subj_averages = {s_name: (sum(scores)/len(scores)) for s_name, scores in subj_totals.items()}
            
            # 2. Draw Subject Averages Bar Chart
            self.averages_figure.clear()
            ax1 = self.averages_figure.add_subplot(111)
            
            active_theme = config.get("theme", "dark").lower()
            is_dark = active_theme != "light"
            bg_color = '#1e293b' if is_dark else '#f8fafc'
            if active_theme == "emerald":
                bg_color = '#0d291e'
            elif active_theme == "sapphire":
                bg_color = '#111a2e'
            elif active_theme == "amber":
                bg_color = '#2c1e10'
                
            text_color = '#f8fafc' if is_dark else '#1e293b'
            grid_color = '#475569' if is_dark else '#e2e8f0'
            
            self.averages_figure.patch.set_facecolor(bg_color)
            ax1.set_facecolor(bg_color)
            
            if subj_averages:
                subjects = list(subj_averages.keys())
                averages = list(subj_averages.values())
                
                bars = ax1.bar(subjects, averages, color='#3b82f6', width=0.5, edgecolor='#2563eb', linewidth=1)
                
                for bar in bars:
                    yval = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2, yval + 1, f"{yval:.1f}", ha='center', va='bottom', color=text_color, fontsize=8)
            else:
                ax1.text(0.5, 0.5, "No grade data available", ha='center', va='center', color=text_color)
                
            ax1.set_title("Class Subject Averages (%)", color=text_color, fontweight='bold', pad=12)
            ax1.set_ylabel("Average Score (%)", color=text_color)
            ax1.tick_params(colors=text_color, labelsize=9)
            ax1.set_ylim(0, 110)
            ax1.grid(True, linestyle='--', alpha=0.3, color=grid_color)
            
            for tick in ax1.get_xticklabels():
                tick.set_rotation(15)
                
            self.averages_canvas.draw()
            
            # 3. Fetch Grade Distribution
            self.distribution_figure.clear()
            ax2 = self.distribution_figure.add_subplot(111)
            self.distribution_figure.patch.set_facecolor(bg_color)
            ax2.set_facecolor(bg_color)
            
            if subj_id:
                dist_results = [r for r in results if r.subject_id == subj_id]
                title_suffix = f"({self.an_subject_combo.currentText()})"
            else:
                dist_results = results
                title_suffix = "(All Subjects)"
                
            grade_counts = {}
            for r in dist_results:
                g = r.grade or "Ungraded"
                grade_counts[g] = grade_counts.get(g, 0) + 1
                
            if grade_counts:
                labels = list(grade_counts.keys())
                sizes = list(grade_counts.values())
                colors_list = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#64748b']
                
                wedges, texts, autotexts = ax2.pie(
                    sizes, labels=labels, autopct='%1.1f%%', startangle=140,
                    colors=colors_list[:len(labels)],
                    textprops=dict(color=text_color, fontsize=9)
                )
                for autotext in autotexts:
                    autotext.set_color('white')
                    autotext.set_fontsize(8)
            else:
                ax2.text(0.5, 0.5, "No grade data available", ha='center', va='center', color=text_color)
                
            ax2.set_title(f"Grade Distribution {title_suffix}", color=text_color, fontweight='bold', pad=12)
            self.distribution_canvas.draw()
            
        except Exception as e:
            print(f"Failed to update analytics: {e}")
        finally:
            session.close()
            
    def load_subjects_combo(self):
        class_id = self.class_combo.currentData()
        if not class_id:
            return
            
        session = get_session()
        try:
            cls = session.query(Class).filter(Class.id == class_id).first()
            if cls:
                subjects = session.query(Subject).filter(Subject.class_level == cls.level).all()
                self.subject_combo.clear()
                for s in subjects:
                    self.subject_combo.addItem(s.name, s.id)
        except Exception as e:
            print(f"Error loading subjects: {e}")
        finally:
            session.close()
            
    def clear_table(self):
        self.table.setRowCount(0)
        
    def get_ges_grade(self, total):
        scale = config.get("grading_scale", [])
        # Sort scale descending by min_score
        sorted_scale = sorted(scale, key=lambda x: x.get("min_score", 0.0), reverse=True)
        for rule in sorted_scale:
            if total >= rule.get("min_score", 0.0):
                return rule.get("grade", "9")
        return "9"

    def get_ges_remark(self, grade):
        scale = config.get("grading_scale", [])
        for rule in scale:
            if rule.get("grade") == grade:
                return rule.get("remark", "")
        return ""

    def load_mark_sheet(self):
        exam_id = self.exam_combo.currentData()
        class_id = self.class_combo.currentData()
        subject_id = self.subject_combo.currentData()
        
        if not exam_id or not class_id or not subject_id:
            QMessageBox.warning(self, "Selection Required", "Please select examination, class, and subject.")
            return
            
        self.updating_table = True
        self.table.setRowCount(0)
        session = get_session()
        try:
            students = session.query(Student).filter(
                Student.class_id == class_id, 
                Student.status == "Active"
            ).order_by(Student.last_name.asc()).all()
            
            self.table.setRowCount(len(students))
            
            for i, s in enumerate(students):
                self.table.setItem(i, 0, QTableWidgetItem(s.id))
                self.table.setItem(i, 1, QTableWidgetItem(f"{s.last_name}, {s.first_name}"))
                
                # Fetch existing score
                res = session.query(Result).filter(
                    Result.examination_id == exam_id,
                    Result.student_id == s.id,
                    Result.subject_id == subject_id
                ).first()
                
                c_score = str(res.class_score) if res else "0.0"
                e_score = str(res.exam_score) if res else "0.0"
                tot_score = str(res.total_score) if res else "0.0"
                grade_str = res.grade if res else "9"
                remarks_str = res.remarks if res and res.remarks else self.get_ges_remark(grade_str)
                
                # Setup items
                # Student ID (ReadOnly)
                self.table.item(i, 0).setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                # Student Name (ReadOnly)
                self.table.item(i, 1).setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                
                # Editable score inputs
                self.table.setItem(i, 2, QTableWidgetItem(c_score))
                self.table.setItem(i, 3, QTableWidgetItem(e_score))
                
                # Auto totals and grades (ReadOnly)
                tot_item = QTableWidgetItem(tot_score)
                tot_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(i, 4, tot_item)
                
                grade_item = QTableWidgetItem(grade_str)
                grade_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.table.setItem(i, 5, grade_item)
                
                self.table.setItem(i, 6, QTableWidgetItem(remarks_str))
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load mark sheet:\n{e}")
        finally:
            self.updating_table = False
            session.close()

    def handle_cell_edit(self, item):
        if self.updating_table:
            return
            
        row = item.row()
        col = item.column()
        
        # Listen only to class score (2) and exam score (3) edits
        if col not in [2, 3]:
            return
            
        self.updating_table = True
        try:
            c_val = float(self.table.item(row, 2).text().strip() or "0.0")
            e_val = float(self.table.item(row, 3).text().strip() or "0.0")
            
            # Constrain inputs
            if c_val < 0 or c_val > 30:
                QMessageBox.warning(self, "Invalid Value", "Class score must be between 0 and 30.")
                c_val = min(max(c_val, 0.0), 30.0)
                self.table.item(row, 2).setText(str(c_val))
                
            if e_val < 0 or e_val > 70:
                QMessageBox.warning(self, "Invalid Value", "Exam score must be between 0 and 70.")
                e_val = min(max(e_val, 0.0), 70.0)
                self.table.item(row, 3).setText(str(e_val))
                
            total = c_val + e_val
            grade = self.get_ges_grade(total)
            remark = self.get_ges_remark(grade)
            
            self.table.item(row, 4).setText(f"{total:.1f}")
            self.table.item(row, 5).setText(grade)
            
            remark_item = self.table.item(row, 6)
            if not remark_item:
                remark_item = QTableWidgetItem()
                self.table.setItem(row, 6, remark_item)
            remark_item.setText(remark)
        except ValueError:
            # Revert to 0.0 if not a valid float
            self.table.item(col).setText("0.0")
        finally:
            self.updating_table = False

    def save_marks(self):
        exam_id = self.exam_combo.currentData()
        class_id = self.class_combo.currentData()
        subject_id = self.subject_combo.currentData()
        
        if not exam_id or not class_id or not subject_id:
            return
            
        session = get_session()
        try:
            for row in range(self.table.rowCount()):
                s_id = self.table.item(row, 0).text()
                c_score = float(self.table.item(row, 2).text().strip() or "0.0")
                e_score = float(self.table.item(row, 3).text().strip() or "0.0")
                tot_score = c_score + e_score
                grade = self.table.item(row, 5).text()
                remarks = self.table.item(row, 6).text().strip() or None
                
                # Check for existing Result
                res = session.query(Result).filter(
                    Result.examination_id == exam_id,
                    Result.student_id == s_id,
                    Result.subject_id == subject_id
                ).first()
                
                if res:
                    res.class_score = c_score
                    res.exam_score = e_score
                    res.total_score = tot_score
                    res.grade = grade
                    res.remarks = remarks
                else:
                    res = Result(
                        examination_id=exam_id,
                        student_id=s_id,
                        subject_id=subject_id,
                        class_id=class_id,
                        class_score=c_score,
                        exam_score=e_score,
                        total_score=tot_score,
                        grade=grade,
                        remarks=remarks
                    )
                    session.add(res)
            
            session.commit()
            QMessageBox.information(self, "Success", "Marks saved successfully.")
            self.load_mark_sheet()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save marks: {e}")
        finally:
            session.close()

    def compute_class_ranks(self):
        exam_id = self.exam_combo.currentData()
        class_id = self.class_combo.currentData()
        subject_id = self.subject_combo.currentData()
        
        if not exam_id or not class_id or not subject_id:
            return
            
        session = get_session()
        try:
            # Query results for this class + subject + exam
            results = session.query(Result).filter(
                Result.examination_id == exam_id,
                Result.class_id == class_id,
                Result.subject_id == subject_id
            ).order_by(Result.total_score.desc()).all()
            
            if not results:
                QMessageBox.warning(self, "No Records", "Please enter and save marks first before computing ranks.")
                return
                
            # Assign rankings (handle ties)
            current_rank = 1
            for idx, res in enumerate(results):
                if idx > 0 and res.total_score < results[idx - 1].total_score:
                    current_rank = idx + 1
                res.position = current_rank
                
            session.commit()
            QMessageBox.information(self, "Success", f"Positions computed successfully for {len(results)} students.")
            self.load_mark_sheet()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to compute rankings: {e}")
        finally:
            session.close()

    def print_class_report_cards(self):
        # Open dialog selection of student report cards to print
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Select Student", "Please select a student row in the table first.")
            return
            
        student_id = self.table.item(selected_row, 0).text()
        exam_id = self.exam_combo.currentData()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Report Card", f"report_card_{student_id}_exam_{exam_id}.pdf", "PDF Files (*.pdf)"
        )
        if not file_path:
            return
            
        success, filepath = generate_report_card(student_id, exam_id, file_path)
        if success:
            QMessageBox.information(self, "Success", f"Terminal Report Card PDF generated at:\n{filepath}")
        else:
            QMessageBox.warning(self, "Failed", f"Failed to generate report card:\n{filepath}")
            
    def sms_class_grades(self):
        selected_row = self.table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Select Student", "Please select a student row in the table first.")
            return
            
        student_id = self.table.item(selected_row, 0).text()
        exam_id = self.exam_combo.currentData()
        subject_id = self.subject_combo.currentData()
        
        if not exam_id or not subject_id:
            QMessageBox.warning(self, "Validation Error", "Please select an exam and subject first.")
            return
            
        session = get_session()
        try:
            res = session.query(Result).filter(
                Result.student_id == student_id,
                Result.examination_id == exam_id,
                Result.subject_id == subject_id
            ).first()
            
            if not res:
                QMessageBox.warning(self, "No Grades", "No grades recorded for this student in this subject.")
                return
                
            student = res.student
            if student.parent and student.parent.phone:
                msg = f"Orion Grades: Dear Parent, terminal score for {student.first_name} in {res.subject.name} ({res.examination.name}) is: Class Score: {res.class_score:.1f}, Exam Score: {res.exam_score:.1f}, Total: {res.total_score:.1f} (Grade {res.grade})."
                sms = SMSLog(
                    recipient_phone=student.parent.phone,
                    message_content=msg,
                    status="Sent",
                    trigger_type="Grades"
                )
                session.add(sms)
                session.commit()
                QMessageBox.information(self, "SMS Sent", f"Grades alert sent to parent phone: {student.parent.phone}")
            else:
                QMessageBox.warning(self, "No Phone", "No parent phone number linked to this student profile.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to dispatch grades SMS: {e}")
        finally:
            session.close()
            
    def refresh(self):
        self.load_combos()
