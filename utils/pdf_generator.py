import datetime
import os
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, mm

from database.connection import get_session
from database.models import Student, Parent, Class, Payment, StudentBill, Examination, Result, AcademicYear, Term, Subject, Fee, Staff
from config import config

# Output folder for PDFs
PDF_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "exports"
PDF_OUTPUT_DIR.mkdir(exist_ok=True)

def add_pdf_header(story, title_text=None):
    from reportlab.platypus import Image
    
    logo_path = config.get("school_logo", "")
    logo_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), logo_path) if logo_path else ""
    logo_exists = logo_path and os.path.exists(logo_file)
    
    school_name = config.get("school_name", "Orion School System")
    school_motto = config.get("school_motto", "Knowledge, Integrity, Excellence")
    school_phone = config.get("school_phone", "")
    school_email = config.get("school_email", "")
    school_address = config.get("school_address", "")
    
    # Styles
    name_style = ParagraphStyle(
        'SName',
        fontName='Helvetica-Bold',
        fontSize=18,
        alignment=0 if logo_exists else 1,
        textColor=colors.HexColor("#2563eb")
    )
    details_style = ParagraphStyle(
        'SDetails',
        fontName='Helvetica',
        fontSize=9,
        alignment=0 if logo_exists else 1,
        textColor=colors.HexColor("#475569")
    )
    
    info_layout = []
    info_layout.append(Paragraph(school_name.upper(), name_style))
    if school_motto:
        info_layout.append(Paragraph(f"<i>{school_motto}</i>", details_style))
    
    contact_parts = []
    if school_phone:
        contact_parts.append(f"Phone: {school_phone}")
    if school_email:
        contact_parts.append(f"Email: {school_email}")
    if school_address:
        contact_parts.append(f"Address: {school_address}")
        
    if contact_parts:
        info_layout.append(Paragraph(" | ".join(contact_parts), details_style))
        
    if logo_exists:
        try:
            img = Image(logo_file, width=50, height=50)
            img.hAlign = 'LEFT'
            
            header_table = Table([[img, info_layout]], colWidths=[60, 480])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(header_table)
        except Exception as e:
            print(f"Error copying logo in PDF: {e}")
            story.append(Paragraph(school_name.upper(), name_style))
            if school_motto:
                story.append(Paragraph(f"<i>{school_motto}</i>", details_style))
            story.append(Paragraph(" | ".join(contact_parts), details_style))
    else:
        story.append(Paragraph(school_name.upper(), name_style))
        if school_motto:
            story.append(Paragraph(f"<i>{school_motto}</i>", details_style))
        if contact_parts:
            story.append(Paragraph(" | ".join(contact_parts), details_style))
            
    story.append(Spacer(1, 10))
    # Horizontal separator line
    sep = Table([[""]], colWidths=[540], rowHeights=[1])
    sep.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(sep)
    story.append(Spacer(1, 15))
    
    if title_text:
        title_style = ParagraphStyle(
            'DocTitle',
            fontName='Helvetica-Bold',
            fontSize=13,
            alignment=1,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=15
        )
        story.append(Paragraph(title_text.upper(), title_style))

def generate_student_id_card(student_id: str) -> tuple[bool, str]:
    """
    Generates a CR80 standard sized student ID Card PDF.
    """
    try:
        session = get_session()
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            return False, "Student not found."
            
        file_path = PDF_OUTPUT_DIR / f"id_card_{student_id}.pdf"
        
        # ID Card size: CR80 is 85.6mm x 54mm (approx 3.37 x 2.125 inches)
        # We will make the page size slightly larger or exactly CR80
        width = 85.6 * mm
        height = 54.0 * mm
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=(width, height),
            leftMargin=5*mm,
            rightMargin=5*mm,
            topMargin=4*mm,
            bottomMargin=4*mm
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'IDTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.HexColor("#2563eb"),
            alignment=1, # Center
            spaceAfter=2
        )
        body_style = ParagraphStyle(
            'IDBody',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=7,
            textColor=colors.HexColor("#0f172a"),
            alignment=0, # Left
            spaceAfter=2
        )
        body_bold = ParagraphStyle(
            'IDBodyBold',
            parent=body_style,
            fontName='Helvetica-Bold'
        )
        
        story = []
        
        school_name = config.get("school_name", "Orion School System")
        story.append(Paragraph(school_name.upper(), title_style))
        story.append(Spacer(1, 2*mm))
        
        # Grid details: photo placeholder on left, details on right
        details = [
            [Paragraph("<b>STUDENT ID CARD</b>", ParagraphStyle('Sub', parent=body_style, fontName='Helvetica-Bold', fontSize=8, alignment=1)), ""],
            [Paragraph("Name:", body_style), Paragraph(f"<b>{student.first_name} {student.last_name}</b>", body_style)],
            [Paragraph("Student ID:", body_style), Paragraph(f"<b>{student.id}</b>", body_style)],
            [Paragraph("Class:", body_style), Paragraph(student.class_assigned.name if student.class_assigned else "Unassigned", body_style)],
            [Paragraph("Gender:", body_style), Paragraph(student.gender, body_style)],
            [Paragraph("Emergency Call:", body_style), Paragraph(student.emergency_contact_phone or "N/A", body_style)]
        ]
        
        t = Table(details, colWidths=[20*mm, 55*mm])
        t.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('SPAN', (0,0), (1,0)),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
        ]))
        story.append(t)
        
        doc.build(story)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_admission_form(student_id: str) -> tuple[bool, str]:
    """
    Generates a full A4 sized student admission slip document.
    """
    try:
        session = get_session()
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            return False, "Student not found."
            
        file_path = PDF_OUTPUT_DIR / f"admission_slip_{student_id}.pdf"
        
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Header',
            fontName='Helvetica-Bold',
            fontSize=22,
            textColor=colors.HexColor("#2563eb"),
            alignment=1,
            spaceAfter=5
        )
        subtitle_style = ParagraphStyle(
            'SubHeader',
            fontName='Helvetica-Bold',
            fontSize=14,
            textColor=colors.HexColor("#475569"),
            alignment=1,
            spaceAfter=20
        )
        section_style = ParagraphStyle(
            'SecTitle',
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=15,
            spaceAfter=8,
            borderPadding=2
        )
        body_style = ParagraphStyle(
            'Body',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6
        )
        
        story = []
        add_pdf_header(story, "OFFICIAL ADMISSION SLIP")
        
        # Student Section
        story.append(Paragraph("<b>STUDENT DETAILS</b>", section_style))
        
        dob_str = student.date_of_birth.strftime("%Y-%m-%d")
        adm_str = student.admission_date.strftime("%Y-%m-%d")
        
        student_details = [
            [Paragraph("<b>Student Unique ID:</b>", body_style), Paragraph(student.id, body_style)],
            [Paragraph("<b>Full Name:</b>", body_style), Paragraph(f"{student.first_name} {student.other_names or ''} {student.last_name}", body_style)],
            [Paragraph("<b>Gender:</b>", body_style), Paragraph(student.gender, body_style)],
            [Paragraph("<b>Date of Birth:</b>", body_style), Paragraph(dob_str, body_style)],
            [Paragraph("<b>Class Admitted To:</b>", body_style), Paragraph(student.class_assigned.name if student.class_assigned else "Unassigned", body_style)],
            [Paragraph("<b>Admission Date:</b>", body_style), Paragraph(adm_str, body_style)],
            [Paragraph("<b>Medical Conditions:</b>", body_style), Paragraph(student.medical_info or "None Listed", body_style)],
            [Paragraph("<b>Emergency Contacts:</b>", body_style), Paragraph(f"{student.emergency_contact_name or 'N/A'} ({student.emergency_contact_phone or 'N/A'})", body_style)]
        ]
        
        t_stud = Table(student_details, colWidths=[2.5*inch, 4.5*inch])
        t_stud.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_stud)
        
        # Parent Section
        story.append(Spacer(1, 15))
        story.append(Paragraph("<b>PARENT / GUARDIAN DETAILS</b>", section_style))
        
        parent_details = []
        if student.parent:
            p = student.parent
            parent_details = [
                [Paragraph("<b>Full Name:</b>", body_style), Paragraph(f"{p.first_name} {p.last_name}", body_style)],
                [Paragraph("<b>Phone Contact:</b>", body_style), Paragraph(p.phone, body_style)],
                [Paragraph("<b>Email Address:</b>", body_style), Paragraph(p.email or "N/A", body_style)],
                [Paragraph("<b>Occupation:</b>", body_style), Paragraph(p.occupation or "N/A", body_style)],
                [Paragraph("<b>Residential Address:</b>", body_style), Paragraph(p.address or "N/A", body_style)]
            ]
        else:
            parent_details = [
                [Paragraph("<b>Details:</b>", body_style), Paragraph("No Parent Profile Linked.", body_style)]
            ]
            
        t_par = Table(parent_details, colWidths=[2.5*inch, 4.5*inch])
        t_par.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t_par)
        
        # Signatures
        story.append(Spacer(1, 40))
        sig_data = [
            [Paragraph("_____________________________<br/><b>Headteacher / Administrator</b>", ParagraphStyle('Sig1', parent=body_style, alignment=0)),
             Paragraph("_____________________________<br/><b>Parent / Guardian Signature</b>", ParagraphStyle('Sig2', parent=body_style, alignment=2))]
        ]
        t_sig = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
        story.append(t_sig)
        
        doc.build(story)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_fee_receipt(payment_id: int) -> tuple[bool, str]:
    """
    Generates a Receipt PDF for a recorded fee payment.
    """
    try:
        session = get_session()
        payment = session.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return False, "Payment transaction record not found."
            
        file_path = PDF_OUTPUT_DIR / f"fee_receipt_pmt_{payment_id}.pdf"
        
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Header',
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor("#10b981"),
            alignment=1,
            spaceAfter=15
        )
        body_style = ParagraphStyle(
            'Body',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6
        )
        
        story = []
        add_pdf_header(story, "OFFICIAL PAYMENT RECEIPT")
        
        student = payment.student_bill.student
        bill = payment.student_bill
        outstanding = bill.amount_billed - bill.amount_paid
        
        receipt_data = [
            [Paragraph("<b>Receipt Reference No:</b>", body_style), Paragraph(payment.reference_no or f"REC-{payment.id}", body_style)],
            [Paragraph("<b>Payment Date:</b>", body_style), Paragraph(payment.payment_date.strftime("%Y-%m-%d %H:%M"), body_style)],
            [Paragraph("<b>Student ID:</b>", body_style), Paragraph(student.id, body_style)],
            [Paragraph("<b>Student Name:</b>", body_style), Paragraph(f"{student.last_name}, {student.first_name}", body_style)],
            [Paragraph("<b>Fee Category:</b>", body_style), Paragraph(bill.fee.name, body_style)],
            [Paragraph("<b>Total Fee Billed:</b>", body_style), Paragraph(f"GHS {bill.amount_billed:.2f}", body_style)],
            [Paragraph("<b>Amount Paid in this Tx:</b>", body_style), Paragraph(f"GHS {payment.amount:.2f}", ParagraphStyle('PAmt', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#10b981")))],
            [Paragraph("<b>Cumulative Total Paid:</b>", body_style), Paragraph(f"GHS {bill.amount_paid:.2f}", body_style)],
            [Paragraph("<b>Remaining Outstanding:</b>", body_style), Paragraph(f"GHS {outstanding:.2f}", ParagraphStyle('OAmt', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#ef4444")))],
            [Paragraph("<b>Payment Mode:</b>", body_style), Paragraph(payment.payment_method, body_style)]
        ]
        
        t = Table(receipt_data, colWidths=[2.5*inch, 4.5*inch])
        t.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t)
        
        story.append(Spacer(1, 30))
        story.append(Paragraph("Thank you for your payment. Education is the greatest legacy.", ParagraphStyle('Footer', parent=body_style, fontName='Helvetica-Oblique', alignment=1)))
        
        doc.build(story)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_report_card(student_id: str, examination_id: int) -> tuple[bool, str]:
    """
    Compiles terminal grades & assessment averages for a student.
    """
    try:
        session = get_session()
        student = session.query(Student).filter(Student.id == student_id).first()
        exam = session.query(Examination).filter(Examination.id == examination_id).first()
        
        if not student or not exam:
            return False, "Student or Examination session not found."
            
        file_path = PDF_OUTPUT_DIR / f"report_card_{student_id}_exam_{examination_id}.pdf"
        
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Header',
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor("#2563eb"),
            alignment=1,
            spaceAfter=5
        )
        body_style = ParagraphStyle(
            'Body',
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor("#334155")
        )
        th_style = ParagraphStyle(
            'TableHeader',
            parent=body_style,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )
        
        story = []
        add_pdf_header(story, f"STUDENT TERMINAL REPORT CARD - {exam.name}")
        
        # Student Meta Grid
        cls_name = student.class_assigned.name if student.class_assigned else "Unassigned"
        meta_data = [
            [Paragraph(f"<b>Student ID:</b> {student.id}", body_style), Paragraph(f"<b>Student Name:</b> {student.first_name} {student.last_name}", body_style)],
            [Paragraph(f"<b>Class Stream:</b> {cls_name}", body_style), Paragraph(f"<b>Academic Session:</b> {exam.academic_year.name} - {exam.term.name}", body_style)]
        ]
        t_meta = Table(meta_data, colWidths=[3.5*inch, 3.5*inch])
        t_meta.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 15))
        
        # Results Table Header
        results_header = [
            Paragraph("<b>Subject Code</b>", th_style),
            Paragraph("<b>Subject Title</b>", th_style),
            Paragraph("<b>Class Score (30)</b>", th_style),
            Paragraph("<b>Exam Score (70)</b>", th_style),
            Paragraph("<b>Total (100)</b>", th_style),
            Paragraph("<b>Grade</b>", th_style),
            Paragraph("<b>Remarks</b>", th_style)
        ]
        
        table_rows = [results_header]
        
        # Fetch results
        results = session.query(Result).filter(
            Result.student_id == student_id,
            Result.examination_id == examination_id
        ).all()
        
        # If no results, place mock/no data
        if not results:
            table_rows.append([Paragraph("No exam result records submitted for this period.", body_style)] + [""] * 6)
        else:
            for r in results:
                table_rows.append([
                    Paragraph(r.subject.code, body_style),
                    Paragraph(r.subject.name, body_style),
                    Paragraph(f"{r.class_score:.1f}", body_style),
                    Paragraph(f"{r.exam_score:.1f}", body_style),
                    Paragraph(f"{r.total_score:.1f}", ParagraphStyle('TotalBold', parent=body_style, fontName='Helvetica-Bold')),
                    Paragraph(r.grade or "9", ParagraphStyle('GStyle', parent=body_style, alignment=1)),
                    Paragraph(r.remarks or "", body_style)
                ])
                
        t_res = Table(table_rows, colWidths=[1.0*inch, 2.0*inch, 1.0*inch, 1.0*inch, 0.8*inch, 0.6*inch, 1.6*inch])
        t_res.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2563eb")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#94a3b8")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        # Spanning for empty results
        if not results:
            t_res.setStyle(TableStyle([('SPAN', (0,1), (6,1))]))
            
        story.append(t_res)
        
        # Bottom Summary & Signatures
        story.append(Spacer(1, 30))
        
        # Continuous assessment remarks rules:
        total_subjects = len(results)
        total_grade_units = sum(int(r.grade or 9) for r in results) if results else 0
        overall_gpa_text = f"Grade Point Sum: {total_grade_units} across {total_subjects} subjects." if results else "No graded subjects."
        
        summary_block = [
            [Paragraph(f"<b>Overall Academic Performance Summary:</b>", ParagraphStyle('SBold', parent=body_style, fontName='Helvetica-Bold')), ""],
            [Paragraph(overall_gpa_text, body_style), ""],
            [Paragraph("<b>Class Teacher Remarks:</b> Promising performance. Shows diligence and effort. Keep up the high standard.", body_style), ""],
            [Paragraph("<b>Headteacher Remarks:</b> Satisfactory progress made during the term. Approved for promotional transition.", body_style), ""]
        ]
        t_sum = Table(summary_block, colWidths=[3.5*inch, 3.5*inch])
        t_sum.setStyle(TableStyle([
            ('SPAN', (0,0), (1,0)),
            ('SPAN', (0,1), (1,1)),
            ('SPAN', (0,2), (1,2)),
            ('SPAN', (0,3), (1,3)),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_sum)
        
        # Signature block
        story.append(Spacer(1, 40))
        sig_data = [
            [Paragraph("_____________________________<br/><b>Class Teacher Signature</b>", ParagraphStyle('Sig1', parent=body_style, alignment=0)),
             Paragraph("_____________________________<br/><b>Headteacher Endorsement</b>", ParagraphStyle('Sig2', parent=body_style, alignment=2))]
        ]
        t_sig = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
        story.append(t_sig)
        
        doc.build(story)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_financial_statement() -> tuple[bool, str]:
    """
    Compiles all system payments and operational expenses into a Financial PDF Ledger sheet.
    """
    try:
        session = get_session()
        payments = session.query(Payment).all()
        expenses = session.query(Expense).all()
        
        file_path = PDF_OUTPUT_DIR / "financial_income_statement.pdf"
        
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Header',
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor("#2563eb"),
            alignment=1,
            spaceAfter=5
        )
        body_style = ParagraphStyle(
            'Body',
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor("#334155")
        )
        th_style = ParagraphStyle(
            'TableHeader',
            parent=body_style,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )
        
        story = []
        add_pdf_header(story, "FINANCIAL INCOME STATEMENT & LEDGER")
        
        # Calculate totals
        total_revenue = sum(p.amount for p in payments)
        total_expenses = sum(e.amount for e in expenses)
        net_surplus = total_revenue - total_expenses
        
        summary_rows = [
            [Paragraph("<b>Total Revenue Collected:</b>", body_style), Paragraph(f"GHS {total_revenue:.2f}", ParagraphStyle('PBold', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#10b981")))],
            [Paragraph("<b>Total Operational Expenses:</b>", body_style), Paragraph(f"GHS {total_expenses:.2f}", ParagraphStyle('EBold', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#ef4444")))],
            [Paragraph("<b>Net surplus / (deficit):</b>", body_style), Paragraph(f"GHS {net_surplus:.2f}", ParagraphStyle('NBold', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#10b981") if net_surplus >= 0 else colors.HexColor("#ef4444")))]
        ]
        t_meta = Table(summary_rows, colWidths=[3.5*inch, 3.5*inch])
        t_meta.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 8),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 20))
        
        # Table of transactions
        ledger_header = [
            Paragraph("<b>Date</b>", th_style),
            Paragraph("<b>Type</b>", th_style),
            Paragraph("<b>Title / Details</b>", th_style),
            Paragraph("<b>Category</b>", th_style),
            Paragraph("<b>Amount (GHS)</b>", th_style)
        ]
        
        table_rows = [ledger_header]
        
        combined = []
        for p in payments:
            combined.append({
                "date": p.payment_date,
                "type": "INCOME",
                "title": p.student_bill.fee.name if p.student_bill else "Student Fee Payment",
                "category": "Fee Revenue",
                "amount": p.amount
            })
            
        for e in expenses:
            dt = datetime.datetime.combine(e.date, datetime.time.min)
            combined.append({
                "date": dt,
                "type": "EXPENSE",
                "title": e.title,
                "category": e.category,
                "amount": e.amount
            })
            
        combined.sort(key=lambda x: x["date"], reverse=True)
        
        for item in combined:
            amt_str = f"+GHS {item['amount']:.2f}" if item["type"] == "INCOME" else f"-GHS {item['amount']:.2f}"
            
            type_p_style = ParagraphStyle(
                'TStyle',
                parent=body_style,
                fontName='Helvetica-Bold',
                textColor=colors.HexColor("#10b981") if item["type"] == "INCOME" else colors.HexColor("#ef4444")
            )
            
            table_rows.append([
                Paragraph(item["date"].strftime("%Y-%m-%d"), body_style),
                Paragraph(item["type"], type_p_style),
                Paragraph(item["title"], body_style),
                Paragraph(item["category"], body_style),
                Paragraph(amt_str, type_p_style)
            ])
            
        t_res = Table(table_rows, colWidths=[1.0*inch, 1.0*inch, 2.5*inch, 1.3*inch, 1.2*inch])
        t_res.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        story.append(t_res)
        
        story.append(Spacer(1, 40))
        sig_data = [
            [Paragraph("Report Compiled on: " + datetime.date.today().strftime("%Y-%m-%d"), body_style),
             Paragraph("Approved by: _____________________________", ParagraphStyle('Sig', parent=body_style, alignment=2))]
        ]
        t_sig = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
        story.append(t_sig)
        
        doc.build(story)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_payslip_pdf(payslip):
    try:
        pdf_dir = Path("exports")
        pdf_dir.mkdir(exist_ok=True)
        file_path = pdf_dir / f"payslip_{payslip.staff_id}_{payslip.pay_period.replace(' ', '_')}.pdf"
        
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=letter,
            rightMargin=54, leftMargin=54, topMargin=54, bottomMargin=54
        )
        
        styles = getSampleStyleSheet()
        
        body_style = ParagraphStyle(
            'Body',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6
        )
        
        bold_style = ParagraphStyle(
            'BodyBold',
            parent=body_style,
            fontName='Helvetica-Bold'
        )
        
        section_style = ParagraphStyle(
            'Section',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=8
        )
        
        header_style = ParagraphStyle(
            'Head',
            parent=bold_style,
            textColor=colors.white
        )
        
        story = []
        
        # Header
        add_pdf_header(story, "OFFICIAL SALARY PAYSLIP")
        
        # Staff Info
        story.append(Paragraph("<b>STAFF INFORMATION</b>", section_style))
        staff = payslip.staff
        staff_data = [
            [Paragraph("<b>Staff Name:</b>", body_style), Paragraph(f"{staff.first_name} {staff.last_name}", body_style),
             Paragraph("<b>Staff ID:</b>", body_style), Paragraph(str(staff.id), body_style)],
            [Paragraph("<b>Role:</b>", body_style), Paragraph(staff.role_title, body_style),
             Paragraph("<b>Department:</b>", body_style), Paragraph(staff.department or "Academics", body_style)],
            [Paragraph("<b>Pay Period:</b>", body_style), Paragraph(payslip.pay_period, body_style),
             Paragraph("<b>Payment Date:</b>", body_style), Paragraph(payslip.payment_date.strftime("%Y-%m-%d") if payslip.payment_date else datetime.date.today().strftime("%Y-%m-%d"), body_style)]
        ]
        t_staff = Table(staff_data, colWidths=[1.5*inch, 2.0*inch, 1.5*inch, 2.0*inch])
        t_staff.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 5),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ]))
        story.append(t_staff)
        
        # Salary breakdown
        story.append(Spacer(1, 15))
        story.append(Paragraph("<b>SALARY BREAKDOWN</b>", section_style))
        
        salary_rows = [
            [Paragraph("<b>Description</b>", header_style), Paragraph("<b>Earnings (GHS)</b>", header_style), Paragraph("<b>Deductions (GHS)</b>", header_style)],
            [Paragraph("Basic Salary", body_style), Paragraph(f"{payslip.base_salary:.2f}", body_style), Paragraph("", body_style)],
            [Paragraph("Allowances", body_style), Paragraph(f"{payslip.allowances:.2f}", body_style), Paragraph("", body_style)],
            [Paragraph("Income Tax (PAYE 15%)", body_style), Paragraph("", body_style), Paragraph(f"{payslip.tax_deductions:.2f}", body_style)],
            [Paragraph("SSNIT Pension (5.5%)", body_style), Paragraph("", body_style), Paragraph(f"{payslip.pension_deductions:.2f}", body_style)],
            [Paragraph("<b>Gross Earnings</b>", bold_style), Paragraph(f"{(payslip.base_salary + payslip.allowances):.2f}", bold_style), Paragraph("", body_style)],
            [Paragraph("<b>Total Deductions</b>", bold_style), Paragraph("", body_style), Paragraph(f"{(payslip.tax_deductions + payslip.pension_deductions):.2f}", bold_style)],
            [Paragraph("<b>NET TAKE-HOME PAY</b>", bold_style), Paragraph("", bold_style), Paragraph(f"<b>GHS {payslip.net_salary:.2f}</b>", ParagraphStyle('Net', parent=bold_style, textColor=colors.HexColor("#10b981")))]
        ]
        
        t_salary = Table(salary_rows, colWidths=[3.0*inch, 2.0*inch, 2.0*inch])
        t_salary.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 6),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
            ('ROWBACKGROUNDS', (0,1), (-1,-3), [colors.white, colors.HexColor("#f8fafc")]),
            ('BACKGROUND', (0,-3), (-1,-1), colors.HexColor("#e2e8f0")),
        ]))
        story.append(t_salary)
        
        # Signatures
        story.append(Spacer(1, 30))
        sig_data = [
            [Paragraph("Prepared by Bursar: ____________________", body_style),
             Paragraph("Staff Signature: ____________________", ParagraphStyle('RightSig', parent=body_style, alignment=2))]
        ]
        t_sig = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
        story.append(t_sig)
        
        doc.build(story)
        return str(file_path), None
    except Exception as e:
        return None, str(e)
