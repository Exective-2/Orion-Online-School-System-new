from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, 
    QLineEdit, QComboBox, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QDialog, QFormLayout, QDialogButtonBox, QMessageBox,
    QTabWidget, QDateEdit
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor
from database.connection import get_session
from database.models import AcademicYear, Term, Class, Subject, TeacherSubject, Staff, TimetableSlot
from config import config, save_config
import datetime

class AcademicsPanel(QWidget):
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Main Tab Widget
        self.tabs = QTabWidget()
        
        # 1. Term Settings Tab
        self.term_tab = QWidget()
        self.init_term_tab()
        self.tabs.addTab(self.term_tab, "Academic Terms")
        
        # 2. Classes Tab
        self.classes_tab = QWidget()
        self.init_classes_tab()
        self.tabs.addTab(self.classes_tab, "Classes & Streams")
        
        # 3. Subjects Tab
        self.subjects_tab = QWidget()
        self.init_subjects_tab()
        self.tabs.addTab(self.subjects_tab, "Subjects Directory")
        
        # 4. Teacher Allocations Tab
        self.alloc_tab = QWidget()
        self.init_alloc_tab()
        self.tabs.addTab(self.alloc_tab, "Teacher Subject Allocation")
        
        # 5. Timetable Tab
        self.timetable_tab = QWidget()
        self.init_timetable_tab()
        self.tabs.addTab(self.timetable_tab, "Class Timetable Scheduler")
        
        layout.addWidget(self.tabs)
        
    def init_term_tab(self):
        tab_layout = QVBoxLayout(self.term_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        # Current active summary
        self.active_lbl = QLabel()
        self.active_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6; padding-bottom: 10px;")
        tab_layout.addWidget(self.active_lbl)
        
        # Actions bar
        actions = QHBoxLayout()
        add_year_btn = QPushButton("Add Academic Year")
        add_year_btn.setObjectName("secondary_btn")
        add_year_btn.clicked.connect(self.open_add_year)
        actions.addWidget(add_year_btn)
        
        set_active_btn = QPushButton("Activate Selected Term")
        set_active_btn.setObjectName("primary_btn")
        set_active_btn.clicked.connect(self.activate_term)
        actions.addWidget(set_active_btn)
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        # Terms table
        self.terms_table = QTableWidget()
        self.terms_table.setColumnCount(6)
        self.terms_table.setHorizontalHeaderLabels(["Term ID", "Academic Year", "Term Name", "Start Date", "End Date", "Status"])
        self.terms_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.terms_table)
        
        self.load_terms()
        
    def load_terms(self):
        self.terms_table.setRowCount(0)
        session = get_session()
        try:
            active_year = session.query(AcademicYear).filter(AcademicYear.is_current == True).first()
            active_term = session.query(Term).filter(Term.is_current == True).first()
            
            y_name = active_year.name if active_year else "None"
            t_name = active_term.name if active_term else "None"
            self.active_lbl.setText(f"Current Active Session: {y_name} - {t_name}")
            
            # Save updated values to config
            if active_year and active_term:
                config["active_academic_year_id"] = active_year.id
                config["active_term_id"] = active_term.id
                save_config(config)
            
            terms = session.query(Term).join(AcademicYear).order_by(AcademicYear.name.desc(), Term.name.asc()).all()
            self.terms_table.setRowCount(len(terms))
            for i, term in enumerate(terms):
                self.terms_table.setItem(i, 0, QTableWidgetItem(str(term.id)))
                self.terms_table.setItem(i, 1, QTableWidgetItem(term.academic_year.name))
                self.terms_table.setItem(i, 2, QTableWidgetItem(term.name))
                self.terms_table.setItem(i, 3, QTableWidgetItem(term.start_date.strftime("%Y-%m-%d")))
                self.terms_table.setItem(i, 4, QTableWidgetItem(term.end_date.strftime("%Y-%m-%d")))
                
                status = "ACTIVE" if term.is_current else "Inactive"
                self.terms_table.setItem(i, 5, QTableWidgetItem(status))
        except Exception as e:
            print(f"Error loading terms: {e}")
        finally:
            session.close()
            
    def open_add_year(self):
        # Open small dialog to register new year and default 3 terms
        dialog = AddAcademicYearDialog(self)
        dialog.data_changed.connect(self.load_terms)
        dialog.exec()
        
    def activate_term(self):
        selected_row = self.terms_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Required", "Please select a term row in the table to activate.")
            return
            
        term_id = int(self.terms_table.item(selected_row, 0).text())
        session = get_session()
        try:
            # Set all terms to false
            session.query(Term).update({Term.is_current: False})
            session.query(AcademicYear).update({AcademicYear.is_current: False})
            
            # Select target term
            term = session.query(Term).filter(Term.id == term_id).first()
            if term:
                term.is_current = True
                term.academic_year.is_current = True
                session.commit()
                QMessageBox.information(self, "Success", f"Term {term.name} of {term.academic_year.name} is now set as the active term.")
                self.load_terms()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to activate term: {e}")
        finally:
            session.close()
            
    # --- Classes setup ---
    def init_classes_tab(self):
        tab_layout = QVBoxLayout(self.classes_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        actions = QHBoxLayout()
        add_class_btn = QPushButton("Add Class Stream")
        add_class_btn.setObjectName("primary_btn")
        add_class_btn.clicked.connect(self.open_add_class)
        actions.addWidget(add_class_btn)
        
        assign_teacher_btn = QPushButton("Assign Class Teacher")
        assign_teacher_btn.setObjectName("secondary_btn")
        assign_teacher_btn.clicked.connect(self.open_assign_teacher)
        actions.addWidget(assign_teacher_btn)
        
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        self.classes_table = QTableWidget()
        self.classes_table.setColumnCount(5)
        self.classes_table.setHorizontalHeaderLabels(["Class ID", "Name", "Level Category", "Stream / Division", "Class Teacher"])
        self.classes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.classes_table)
        self.load_classes()
        
    def load_classes(self):
        self.classes_table.setRowCount(0)
        session = get_session()
        try:
            from database.models import ClassTeacher
            ay_id = config.get("active_academic_year_id", 1)
            
            classes = session.query(Class).all()
            self.classes_table.setRowCount(len(classes))
            for i, c in enumerate(classes):
                self.classes_table.setItem(i, 0, QTableWidgetItem(str(c.id)))
                self.classes_table.setItem(i, 1, QTableWidgetItem(c.name))
                self.classes_table.setItem(i, 2, QTableWidgetItem(c.level))
                self.classes_table.setItem(i, 3, QTableWidgetItem(c.stream or "None"))
                
                # Fetch class teacher name
                ct = session.query(ClassTeacher).filter(
                    ClassTeacher.class_id == c.id,
                    ClassTeacher.academic_year_id == ay_id
                ).first()
                t_name = f"{ct.staff.last_name}, {ct.staff.first_name}" if ct and ct.staff else "Not Assigned"
                self.classes_table.setItem(i, 4, QTableWidgetItem(t_name))
        except Exception as e:
            print(f"Error loading classes: {e}")
        finally:
            session.close()
            
    def open_add_class(self):
        dialog = AddClassDialog(self)
        dialog.data_changed.connect(self.load_classes)
        dialog.exec()

    def open_assign_teacher(self):
        selected_row = self.classes_table.currentRow()
        if selected_row < 0:
            QMessageBox.warning(self, "Selection Error", "Please select a class stream from the table first.")
            return
            
        class_id = int(self.classes_table.item(selected_row, 0).text())
        class_name = self.classes_table.item(selected_row, 1).text()
        
        dialog = AssignClassTeacherDialog(class_id, class_name, self)
        dialog.data_changed.connect(self.load_classes)
        dialog.exec()

    # --- Subjects Setup ---
    def init_subjects_tab(self):
        tab_layout = QVBoxLayout(self.subjects_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        actions = QHBoxLayout()
        add_sub_btn = QPushButton("Add Subject")
        add_sub_btn.setObjectName("primary_btn")
        add_sub_btn.clicked.connect(self.open_add_subject)
        actions.addWidget(add_sub_btn)
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        self.sub_table = QTableWidget()
        self.sub_table.setColumnCount(4)
        self.sub_table.setHorizontalHeaderLabels(["Subject ID", "Code", "Subject Name", "Class Level Category"])
        self.sub_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.sub_table)
        self.load_subjects()
        
    def load_subjects(self):
        self.sub_table.setRowCount(0)
        session = get_session()
        try:
            subjects = session.query(Subject).all()
            self.sub_table.setRowCount(len(subjects))
            for i, s in enumerate(subjects):
                self.sub_table.setItem(i, 0, QTableWidgetItem(str(s.id)))
                self.sub_table.setItem(i, 1, QTableWidgetItem(s.code))
                self.sub_table.setItem(i, 2, QTableWidgetItem(s.name))
                self.sub_table.setItem(i, 3, QTableWidgetItem(s.class_level))
        except Exception as e:
            print(f"Error loading subjects: {e}")
        finally:
            session.close()
            
    def open_add_subject(self):
        dialog = AddSubjectDialog(self)
        dialog.data_changed.connect(self.load_subjects)
        dialog.exec()

    # --- Teacher Allocations ---
    def init_alloc_tab(self):
        tab_layout = QVBoxLayout(self.alloc_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        actions = QHBoxLayout()
        add_alloc_btn = QPushButton("Allocate Teacher to Subject")
        add_alloc_btn.setObjectName("primary_btn")
        add_alloc_btn.clicked.connect(self.open_add_alloc)
        actions.addWidget(add_alloc_btn)
        actions.addStretch()
        tab_layout.addLayout(actions)
        
        self.alloc_table = QTableWidget()
        self.alloc_table.setColumnCount(5)
        self.alloc_table.setHorizontalHeaderLabels(["Allocation ID", "Teacher Name", "Subject", "Class Stream", "Action"])
        self.alloc_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        tab_layout.addWidget(self.alloc_table)
        self.load_allocations()
        
    def load_allocations(self):
        self.alloc_table.setRowCount(0)
        session = get_session()
        try:
            allocs = session.query(TeacherSubject).all()
            self.alloc_table.setRowCount(len(allocs))
            for i, a in enumerate(allocs):
                self.alloc_table.setItem(i, 0, QTableWidgetItem(str(a.id)))
                
                t_name = f"{a.staff.last_name}, {a.staff.first_name}"
                self.alloc_table.setItem(i, 1, QTableWidgetItem(t_name))
                self.alloc_table.setItem(i, 2, QTableWidgetItem(a.subject.name))
                self.alloc_table.setItem(i, 3, QTableWidgetItem(a.class_obj.name))
                
                del_btn = QPushButton("Remove")
                del_btn.setObjectName("danger_btn")
                del_btn.clicked.connect(lambda checked=False, a_id=a.id: self.delete_allocation(a_id))
                self.alloc_table.setCellWidget(i, 4, del_btn)
        except Exception as e:
            print(f"Error loading allocations: {e}")
        finally:
            session.close()
            
    def open_add_alloc(self):
        dialog = AddAllocationDialog(self)
        dialog.data_changed.connect(self.load_allocations)
        dialog.exec()
        
    def delete_allocation(self, a_id):
        confirm = QMessageBox.question(
            self, "Confirm Delete", "Are you sure you want to remove this teacher assignment?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            session = get_session()
            try:
                alloc = session.query(TeacherSubject).filter(TeacherSubject.id == a_id).first()
                if alloc:
                    session.delete(alloc)
                    session.commit()
                    QMessageBox.information(self, "Success", "Allocation removed.")
                    self.load_allocations()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete assignment: {e}")
            finally:
                session.close()
                
    # --- Timetable Scheduler ---
    def init_timetable_tab(self):
        tab_layout = QVBoxLayout(self.timetable_tab)
        tab_layout.setContentsMargins(15, 15, 15, 15)
        tab_layout.setSpacing(15)
        
        top_bar = QFrame()
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        top_bar_layout.addWidget(QLabel("Select Class Stream:"))
        self.tt_class_combo = QComboBox()
        self.tt_class_combo.currentIndexChanged.connect(self.load_timetable)
        top_bar_layout.addWidget(self.tt_class_combo, stretch=2)
        top_bar_layout.addStretch()
        
        self.auto_gen_btn = QPushButton("Auto-Generate Timetable")
        self.auto_gen_btn.setObjectName("secondary_btn")
        self.auto_gen_btn.clicked.connect(self.auto_generate_timetable)
        top_bar_layout.addWidget(self.auto_gen_btn)
        
        tab_layout.addWidget(top_bar)
        
        # Scheduler Grid (9 rows for time slots, 5 columns for days)
        self.tt_table = QTableWidget()
        self.tt_table.setColumnCount(5)
        self.tt_table.setRowCount(9)
        
        self.days_list = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.time_slots_list = [
            "08:00 - 08:45",
            "08:45 - 09:30",
            "09:30 - 10:15",
            "10:15 - 10:45 (BREAK)",
            "10:45 - 11:30",
            "11:30 - 12:15",
            "12:15 - 13:00 (LUNCH)",
            "13:00 - 13:45",
            "13:45 - 14:30"
        ]
        
        self.tt_table.setHorizontalHeaderLabels(self.days_list)
        self.tt_table.setVerticalHeaderLabels(self.time_slots_list)
        self.tt_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tt_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tt_table.cellDoubleClicked.connect(self.open_timetable_cell_dialog)
        
        tab_layout.addWidget(self.tt_table)
        
        self.load_timetable_combos()
        
    def load_timetable_combos(self):
        session = get_session()
        try:
            classes = session.query(Class).all()
            self.tt_class_combo.clear()
            for c in classes:
                self.tt_class_combo.addItem(c.name, c.id)
        except Exception as e:
            print(f"Error loading tt combos: {e}")
        finally:
            session.close()
            
    def load_timetable(self):
        self.tt_table.clearContents()
        class_id = self.tt_class_combo.currentData()
        if not class_id:
            return
            
        session = get_session()
        try:
            # Active term ids
            ay_id = config.get("active_academic_year_id", 1)
            term_id = config.get("active_term_id", 1)
            
            # Format rows static displays for Breaks
            for row in [3, 6]:
                label_text = "B R E A K" if row == 3 else "L U N C H"
                for col in range(5):
                    item = QTableWidgetItem(label_text)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    active_theme = config.get("theme", "dark").lower()
                    if active_theme == "light":
                        bg_color, fg_color = "#cbd5e1", "#475569"
                    else:
                        fg_color = "#94a3b8"
                        if active_theme == "emerald":
                            bg_color = "#14402e"
                        elif active_theme == "sapphire":
                            bg_color = "#1e2e4f"
                        elif active_theme == "amber":
                            bg_color = "#4a331a"
                        else:
                            bg_color = "#334155"
                    item.setBackground(QColor(bg_color))
                    item.setForeground(QColor(fg_color))
                    self.tt_table.setItem(row, col, item)
                    
            # Fetch slots
            slots = session.query(TimetableSlot).filter(
                TimetableSlot.class_id == class_id,
                TimetableSlot.academic_year_id == ay_id,
                TimetableSlot.term_id == term_id
            ).all()
            
            for slot in slots:
                try:
                    col_idx = self.days_list.index(slot.day_of_week)
                    row_idx = self.time_slots_list.index(slot.time_slot)
                    
                    display_text = f"{slot.subject.name}\n({slot.staff.last_name})"
                    item = QTableWidgetItem(display_text)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    # Don't let users edit inline directly
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.tt_table.setItem(row_idx, col_idx, item)
                except ValueError:
                    continue # Ignore mismatches
        except Exception as e:
            print(f"Error loading timetable: {e}")
        finally:
            session.close()

    def auto_generate_timetable(self):
        from PySide6.QtWidgets import QInputDialog
        import random
        
        # 1. Ask for confirmation
        confirm = QMessageBox.question(
            self, "Auto-Generate Timetable",
            "This will clear the current timetable for the active academic year/term and generate a new one based on Teacher-Subject allocations.\n\n"
            "Are you sure you want to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.No:
            return
            
        # 2. Get sessions per subject count
        sessions, ok = QInputDialog.getInt(
            self, "Sessions Per Subject",
            "Enter weekly sessions per allocated subject (e.g. 3 or 4):",
            3, 1, 10
        )
        if not ok:
            return
            
        session = get_session()
        try:
            # Active term ids
            ay_id = config.get("active_academic_year_id", 1)
            term_id = config.get("active_term_id", 1)
            
            # Fetch all classes, teachers, and allocations
            classes = session.query(Class).all()
            allocations = session.query(TeacherSubject).all()
            
            if not classes:
                QMessageBox.warning(self, "Scheduling Error", "No classes defined in the database yet.")
                return
                
            if not allocations:
                QMessageBox.warning(self, "Scheduling Error", "No Teacher-Subject allocations defined. Please assign teachers to subjects first.")
                return
                
            # Group allocations by class_id
            class_allocs = {}
            for alloc in allocations:
                if alloc.class_id not in class_allocs:
                    class_allocs[alloc.class_id] = []
                class_allocs[alloc.class_id].append(alloc)
                
            # Define slots and days
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            time_slots = [
                "08:00 - 08:45",
                "08:45 - 09:30",
                "09:30 - 10:15",
                # "10:15 - 10:45 (BREAK)" - skipped
                "10:45 - 11:30",
                "11:30 - 12:15",
                # "12:15 - 13:00 (LUNCH)" - skipped
                "13:00 - 13:45",
                "13:45 - 14:30"
            ]
            
            slots_to_schedule = []
            for d in days:
                for ts in time_slots:
                    slots_to_schedule.append((d, ts))
                    
            # Setup session trackers
            remaining_sessions = {}
            for c in classes:
                allocs = class_allocs.get(c.id, [])
                rem = []
                for a in allocs:
                    rem.extend([a] * sessions)
                # Shuffle initially to distribute subjects nicely
                random.shuffle(rem)
                remaining_sessions[c.id] = rem
                
            generated_slots = []
            
            # Bipartite matching solver for each slot using backtracking
            def schedule_slot(slot_idx):
                if slot_idx >= len(slots_to_schedule):
                    return True # Successfully scheduled all slots!
                    
                d, ts = slots_to_schedule[slot_idx]
                
                # Active classes that still have remaining sessions
                active_classes = [c.id for c in classes if remaining_sessions[c.id]]
                if not active_classes:
                    return True # All class sessions scheduled!
                    
                class_order = list(active_classes)
                
                def assign_class(class_idx, busy_teachers_slot):
                    if class_idx >= len(class_order):
                        return schedule_slot(slot_idx + 1)
                        
                    cid = class_order[class_idx]
                    
                    # Options for this class
                    avail_allocs = remaining_sessions[cid]
                    seen_ids = set()
                    options = []
                    for a in avail_allocs:
                        if a.id not in seen_ids:
                            options.append(a)
                            seen_ids.add(a.id)
                            
                    # Always include None (free period / study hall) as a fallback option
                    options.append(None)
                    random.shuffle(options)
                    
                    for opt in options:
                        if opt is None:
                            # Assign free period
                            if assign_class(class_idx + 1, busy_teachers_slot):
                                return True
                        else:
                            # Check teacher availability conflict
                            if opt.staff_id in busy_teachers_slot:
                                continue
                                
                            # Apply choice
                            remaining_sessions[cid].remove(opt)
                            busy_teachers_slot.add(opt.staff_id)
                            generated_slots.append((cid, opt.subject_id, opt.staff_id, d, ts))
                            
                            if assign_class(class_idx + 1, busy_teachers_slot):
                                return True
                                
                            # Revert choice
                            generated_slots.pop()
                            busy_teachers_slot.remove(opt.staff_id)
                            remaining_sessions[cid].append(opt)
                            
                    return False
                    
                return assign_class(0, set())
                
            success = schedule_slot(0)
            if not success:
                QMessageBox.critical(self, "Scheduling Error", "The scheduling algorithm was unable to find a conflict-free solution. Please check teacher workloads and allocations.")
                return
                
            # Save to Database:
            # First delete all existing slots for this year/term
            session.query(TimetableSlot).filter(
                TimetableSlot.academic_year_id == ay_id,
                TimetableSlot.term_id == term_id
            ).delete()
            
            # Save new slots
            for cid, sub_id, staff_id, d, ts in generated_slots:
                slot = TimetableSlot(
                    class_id=cid,
                    subject_id=sub_id,
                    staff_id=staff_id,
                    day_of_week=d,
                    time_slot=ts,
                    academic_year_id=ay_id,
                    term_id=term_id
                )
                session.add(slot)
                
            session.commit()
            
            empty_classes = [c.name for c in classes if c.id not in class_allocs]
            msg = f"Timetable automatically generated successfully!\nScheduled {len(generated_slots)} active teaching periods.\n"
            if empty_classes:
                msg += f"\nNote: The following classes have no Teacher-Subject allocations and were left empty:\n- " + "\n- ".join(empty_classes)
                msg += "\n\nTo populate them, please assign teachers to subjects first under the 'Teacher Subject Allocation' tab."
                
            QMessageBox.information(self, "Success", msg)
            self.load_timetable()
            
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to auto-generate timetable: {e}")
        finally:
            session.close()

    def open_timetable_cell_dialog(self, row, col):
        # Ignore double clicks on Break and Lunch
        if row in [3, 6]:
            return
            
        class_id = self.tt_class_combo.currentData()
        if not class_id:
            return
            
        day = self.days_list[col]
        slot_time = self.time_slots_list[row]
        
        dialog = AddTimetableSlotDialog(class_id, day, slot_time, self)
        dialog.timetable_changed.connect(self.load_timetable)
        dialog.exec()
        
    def refresh(self):
        self.load_terms()
        self.load_classes()
        self.load_subjects()
        self.load_allocations()

class AddAcademicYearDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Add Academic Year")
        self.setMinimumWidth(350)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. 2026/2027")
        self.start_input = QDateEdit()
        self.start_input.setCalendarPopup(True)
        self.start_input.setDate(QDate.currentDate())
        
        self.end_input = QDateEdit()
        self.end_input.setCalendarPopup(True)
        self.end_input.setDate(QDate.currentDate().addDays(330))
        
        form_layout.addRow("Academic Year Name:", self.name_input)
        form_layout.addRow("Start Date:", self.start_input)
        form_layout.addRow("End Date:", self.end_input)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_data)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def save_data(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Name is required.")
            return
            
        sd = self.start_input.date()
        ed = self.end_input.date()
        
        session = get_session()
        try:
            # Create Academic Year
            ay = AcademicYear(
                name=name,
                start_date=datetime.date(sd.year(), sd.month(), sd.day()),
                end_date=datetime.date(ed.year(), ed.month(), ed.day()),
                is_current=False
            )
            session.add(ay)
            session.flush()
            
            # Setup standard three terms automatically
            t1_s = ay.start_date
            t1_e = t1_s + datetime.timedelta(days=108)
            t2_s = t1_e + datetime.timedelta(days=18)
            t2_e = t2_s + datetime.timedelta(days=90)
            t3_s = t2_e + datetime.timedelta(days=26)
            t3_e = ay.end_date
            
            term1 = Term(academic_year_id=ay.id, name="Term 1", start_date=t1_s, end_date=t1_e)
            term2 = Term(academic_year_id=ay.id, name="Term 2", start_date=t2_s, end_date=t2_e)
            term3 = Term(academic_year_id=ay.id, name="Term 3", start_date=t3_s, end_date=t3_e)
            
            session.add_all([term1, term2, term3])
            session.commit()
            
            QMessageBox.information(self, "Success", f"Academic Year {name} and default terms created successfully.")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create academic year: {e}")
        finally:
            session.close()

class AddClassDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Add Class Stream")
        self.setMinimumWidth(300)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. JHS 1 A")
        self.level_combo = QComboBox()
        self.level_combo.addItems(["Kindergarten", "Primary", "JHS"])
        self.stream_input = QLineEdit()
        self.stream_input.setPlaceholderText("e.g. A, B, Gold, Silver")
        
        form_layout.addRow("Class Name:", self.name_input)
        form_layout.addRow("Level Category:", self.level_combo)
        form_layout.addRow("Stream Name:", self.stream_input)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_data)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def save_data(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Validation Error", "Class Name is required.")
            return
            
        session = get_session()
        try:
            cls = Class(
                name=name,
                level=self.level_combo.currentText(),
                stream=self.stream_input.text().strip() or None
            )
            session.add(cls)
            session.commit()
            
            QMessageBox.information(self, "Success", "Class Stream added.")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save class: {e}")
        finally:
            session.close()

class AddSubjectDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Add Subject")
        self.setMinimumWidth(320)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g. Integrated Science")
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("e.g. SCI-JHS1")
        self.level_combo = QComboBox()
        self.level_combo.addItems(["Kindergarten", "Primary", "JHS"])
        
        form_layout.addRow("Subject Name:", self.name_input)
        form_layout.addRow("Subject Code:", self.code_input)
        form_layout.addRow("Class Level:", self.level_combo)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_data)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def save_data(self):
        name = self.name_input.text().strip()
        code = self.code_input.text().strip()
        
        if not name or not code:
            QMessageBox.warning(self, "Validation Error", "Name and Code are required.")
            return
            
        session = get_session()
        try:
            sub = Subject(
                name=name,
                code=code,
                class_level=self.level_combo.currentText()
            )
            session.add(sub)
            session.commit()
            
            QMessageBox.information(self, "Success", "Subject registered successfully.")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save subject: {e}")
        finally:
            session.close()

class AddAllocationDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, parent_widget=None):
        super().__init__(parent_widget)
        self.setWindowTitle("Allocate Teacher Subject")
        self.setMinimumWidth(380)
        self.init_ui()
        self.load_combos()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.teacher_combo = QComboBox()
        self.class_combo = QComboBox()
        self.subject_combo = QComboBox()
        
        form_layout.addRow("Select Teacher:", self.teacher_combo)
        form_layout.addRow("Select Class Stream:", self.class_combo)
        form_layout.addRow("Select Subject:", self.subject_combo)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_data)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def load_combos(self):
        session = get_session()
        try:
            # Teachers only
            teachers = session.query(Staff).filter(Staff.role_title == "Teacher", Staff.status == "Active").all()
            for t in teachers:
                self.teacher_combo.addItem(f"{t.last_name}, {t.first_name}", t.id)
                
            # Classes
            classes = session.query(Class).all()
            for c in classes:
                self.class_combo.addItem(c.name, c.id)
                
            # Subjects
            subjects = session.query(Subject).all()
            for s in subjects:
                self.subject_combo.addItem(f"{s.name} ({s.code})", s.id)
        except Exception as e:
            print(f"Error loading allocation combos: {e}")
        finally:
            session.close()
            
    def save_data(self):
        teacher_id = self.teacher_combo.currentData()
        class_id = self.class_combo.currentData()
        subject_id = self.subject_combo.currentData()
        
        if not teacher_id or not class_id or not subject_id:
            QMessageBox.warning(self, "Selection Error", "Please make all selections.")
            return
            
        session = get_session()
        try:
            # Check duplicate allocation
            exists = session.query(TeacherSubject).filter(
                TeacherSubject.staff_id == teacher_id,
                TeacherSubject.class_id == class_id,
                TeacherSubject.subject_id == subject_id
            ).first()
            
            if exists:
                QMessageBox.warning(self, "Duplicate", "This teacher is already allocated to this subject in this class.")
                return
                
            alloc = TeacherSubject(
                staff_id=teacher_id,
                class_id=class_id,
                subject_id=subject_id
            )
            session.add(alloc)
            session.commit()
            
            QMessageBox.information(self, "Success", "Teacher allocated successfully.")
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save allocation: {e}")
        finally:
            session.close()



class AddTimetableSlotDialog(QDialog):
    timetable_changed = Signal()
    
    def __init__(self, class_id, day, slot_time, parent_widget=None):
        super().__init__(parent_widget)
        self.class_id = class_id
        self.day = day
        self.slot_time = slot_time
        
        self.setWindowTitle(f"Schedule: {day} ({slot_time})")
        self.setMinimumWidth(320)
        self.init_ui()
        self.load_combos()
        self.load_existing()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.subject_combo = QComboBox()
        self.teacher_combo = QComboBox()
        
        form_layout.addRow("Select Subject:", self.subject_combo)
        form_layout.addRow("Assign Teacher:", self.teacher_combo)
        
        layout.addLayout(form_layout)
        
        btn_box = QHBoxLayout()
        
        clear_btn = QPushButton("Clear Slot")
        clear_btn.setObjectName("danger_btn")
        clear_btn.clicked.connect(self.clear_slot)
        btn_box.addWidget(clear_btn)
        
        save_btn = QPushButton("Save Allocation")
        save_btn.setObjectName("primary_btn")
        save_btn.clicked.connect(self.save_slot)
        btn_box.addWidget(save_btn)
        
        layout.addLayout(btn_box)
        
    def load_combos(self):
        session = get_session()
        try:
            # Subject matching this class level
            cls = session.query(Class).filter(Class.id == self.class_id).first()
            if cls:
                subjects = session.query(Subject).filter(Subject.class_level == cls.level).all()
                for s in subjects:
                    self.subject_combo.addItem(f"{s.name} ({s.code})", s.id)
                    
            # Teachers
            teachers = session.query(Staff).filter(Staff.role_title == "Teacher", Staff.status == "Active").all()
            for t in teachers:
                self.teacher_combo.addItem(f"{t.last_name}, {t.first_name}", t.id)
        except Exception as e:
            print(f"Error loading combos: {e}")
        finally:
            session.close()

    def load_existing(self):
        session = get_session()
        try:
            ay_id = config.get("active_academic_year_id", 1)
            term_id = config.get("active_term_id", 1)
            
            slot = session.query(TimetableSlot).filter(
                TimetableSlot.class_id == self.class_id,
                TimetableSlot.day_of_week == self.day,
                TimetableSlot.time_slot == self.slot_time,
                TimetableSlot.academic_year_id == ay_id,
                TimetableSlot.term_id == term_id
            ).first()
            
            if slot:
                s_idx = self.subject_combo.findData(slot.subject_id)
                self.subject_combo.setCurrentIndex(s_idx)
                
                t_idx = self.teacher_combo.findData(slot.staff_id)
                self.teacher_combo.setCurrentIndex(t_idx)
        except Exception as e:
            print(f"Error loading existing slot: {e}")
        finally:
            session.close()

    def save_slot(self):
        subject_id = self.subject_combo.currentData()
        teacher_id = self.teacher_combo.currentData()
        
        if not subject_id or not teacher_id:
            QMessageBox.warning(self, "Validation Error", "Please select subject and teacher.")
            return
            
        session = get_session()
        try:
            ay_id = config.get("active_academic_year_id", 1)
            term_id = config.get("active_term_id", 1)
            
            # Conflict checking: Has this teacher been scheduled elsewhere at the same time?
            conflict = session.query(TimetableSlot).filter(
                TimetableSlot.staff_id == teacher_id,
                TimetableSlot.day_of_week == self.day,
                TimetableSlot.time_slot == self.slot_time,
                TimetableSlot.class_id != self.class_id,
                TimetableSlot.academic_year_id == ay_id,
                TimetableSlot.term_id == term_id
            ).first()
            
            if conflict:
                conflict_class = session.query(Class).filter(Class.id == conflict.class_id).first()
                class_name = conflict_class.name if conflict_class else f"ID {conflict.class_id}"
                
                confirm = QMessageBox.question(
                    self, "Scheduling Conflict Alert",
                    f"Warning: The selected teacher is already scheduled to teach '{conflict.subject.name}' "
                    f"in class '{class_name}' on {self.day} at {self.slot_time}.\n\n"
                    "Are you sure you want to proceed and save this overlapping allocation?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if confirm == QMessageBox.StandardButton.No:
                    return
            
            slot = session.query(TimetableSlot).filter(
                TimetableSlot.class_id == self.class_id,
                TimetableSlot.day_of_week == self.day,
                TimetableSlot.time_slot == self.slot_time,
                TimetableSlot.academic_year_id == ay_id,
                TimetableSlot.term_id == term_id
            ).first()
            
            if slot:
                slot.subject_id = subject_id
                slot.staff_id = teacher_id
            else:
                slot = TimetableSlot(
                    class_id=self.class_id,
                    subject_id=subject_id,
                    staff_id=teacher_id,
                    day_of_week=self.day,
                    time_slot=self.slot_time,
                    academic_year_id=ay_id,
                    term_id=term_id
                )
                session.add(slot)
                
            session.commit()
            self.timetable_changed.emit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save slot: {e}")
        finally:
            session.close()

    def clear_slot(self):
        session = get_session()
        try:
            ay_id = config.get("active_academic_year_id", 1)
            term_id = config.get("active_term_id", 1)
            
            slot = session.query(TimetableSlot).filter(
                TimetableSlot.class_id == self.class_id,
                TimetableSlot.day_of_week == self.day,
                TimetableSlot.time_slot == self.slot_time,
                TimetableSlot.academic_year_id == ay_id,
                TimetableSlot.term_id == term_id
            ).first()
            
            if slot:
                session.delete(slot)
                session.commit()
                self.timetable_changed.emit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to clear slot: {e}")
        finally:
            session.close()

class AssignClassTeacherDialog(QDialog):
    data_changed = Signal()
    
    def __init__(self, class_id, class_name, parent_widget=None):
        super().__init__(parent_widget)
        self.class_id = class_id
        self.class_name = class_name
        self.setWindowTitle(f"Assign Teacher to {class_name}")
        self.setMinimumWidth(350)
        self.init_ui()
        self.load_teachers()
        self.load_current_assignment()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        
        self.teacher_combo = QComboBox()
        form_layout.addRow("Select Teacher:", self.teacher_combo)
        
        layout.addLayout(form_layout)
        
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(self.save_assignment)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
        
    def load_teachers(self):
        session = get_session()
        try:
            self.teacher_combo.clear()
            self.teacher_combo.addItem("None / Unassign", None)
            
            # import Staff here to be safe
            from database.models import Staff
            teachers = session.query(Staff).filter(
                Staff.role_title == "Teacher",
                Staff.status == "Active"
            ).order_by(Staff.last_name.asc()).all()
            
            for t in teachers:
                self.teacher_combo.addItem(f"{t.last_name}, {t.first_name}", t.id)
        except Exception as e:
            print(f"Error loading teachers: {e}")
        finally:
            session.close()
            
    def load_current_assignment(self):
        session = get_session()
        try:
            from database.models import ClassTeacher
            ay_id = config.get("active_academic_year_id", 1)
            ct = session.query(ClassTeacher).filter(
                ClassTeacher.class_id == self.class_id,
                ClassTeacher.academic_year_id == ay_id
            ).first()
            if ct:
                idx = self.teacher_combo.findData(ct.staff_id)
                self.teacher_combo.setCurrentIndex(idx)
        except Exception as e:
            print(f"Error loading current assignment: {e}")
        finally:
            session.close()
            
    def save_assignment(self):
        teacher_id = self.teacher_combo.currentData()
        session = get_session()
        try:
            from database.models import ClassTeacher
            ay_id = config.get("active_academic_year_id", 1)
            
            # Find if there is an existing assignment for this class
            ct = session.query(ClassTeacher).filter(
                ClassTeacher.class_id == self.class_id,
                ClassTeacher.academic_year_id == ay_id
            ).first()
            
            if teacher_id is None:
                # Remove assignment if selected None
                if ct:
                    session.delete(ct)
            else:
                # Upsert assignment
                if ct:
                    ct.staff_id = teacher_id
                else:
                    ct = ClassTeacher(
                        class_id=self.class_id,
                        staff_id=teacher_id,
                        academic_year_id=ay_id
                    )
                    session.add(ct)
            
            session.commit()
            self.data_changed.emit()
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to save assignment:\n{e}")
        finally:
            session.close()
