import datetime
import os
import base64
import tempfile
from pathlib import Path
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch, mm

from database.connection import get_session
from database.models import Student, Parent, Class, Payment, StudentBill, Examination, Result, AcademicYear, Term, Subject, Fee, Staff, Expense, StudentReportRemark, ClassResultApproval
from config import config
from utils.branch_config import get_branch_setting, get_active_year_id, get_active_term_id

# Output folder for PDFs — resolved lazily so mkdir() never runs at import time
# (running mkdir at import time crashes the app if the path is not yet writable)
from config import DATA_DIR

def _get_pdf_dir() -> Path:
    """Return (and lazily create) the exports directory under DATA_DIR."""
    out = DATA_DIR / "exports"
    out.mkdir(parents=True, exist_ok=True)
    return out

# Module-level alias kept for backward compatibility (resolves lazily via _get_pdf_dir())
# Do NOT call PDF_OUTPUT_DIR directly — use _get_pdf_dir() inside functions.

# Keeps track of temp files created for Base64 images so they can be cleaned up
_temp_image_files: list = []

def _resolve_image_path(path_or_uri: str, base_dir: str = None) -> str:
    """
    Resolve a logo/signature path to an actual on-disk file path that ReportLab can open.

    Handles three cases:
    1. Absolute path already on disk → returned as-is.
    2. Relative path (e.g. 'uploads/branch_1/logo.png') → resolved against web/ and project root.
    3. Base64 data URI ('data:image/...;base64,...') → decoded to a NamedTemporaryFile and the
       temp path is returned.  The temp file is registered for later clean-up.

    Returns an empty string if the image cannot be found/decoded.
    """
    if not path_or_uri:
        return ""

    val = path_or_uri.strip()

    # Case 3: Base64 data URI
    if val.startswith("data:") and "base64," in val:
        try:
            header, encoded = val.split("base64,", 1)
            # Determine extension from MIME type
            mime = header.replace("data:", "").replace(";", "").strip()
            ext_map = {
                "image/jpeg": ".jpg",
                "image/jpg": ".jpg",
                "image/png": ".png",
                "image/webp": ".webp",
                "image/gif": ".gif",
            }
            ext = ext_map.get(mime, ".png")
            pad = -len(encoded) % 4
            img_bytes = base64.b64decode(encoded + "=" * pad)
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp.write(img_bytes)
            tmp.flush()
            tmp.close()
            _temp_image_files.append(tmp.name)
            return tmp.name
        except Exception as ex:
            print(f"[pdf_generator] Failed to decode Base64 image: {ex}")
            return ""

    # Case 1: Absolute path
    if os.path.isabs(val):
        return val if os.path.exists(val) else ""

    # Case 2: Relative path — also fetch base64 fallback from DB if disk file is absent
    clean = val.lstrip("/")
    project_root = os.path.dirname(os.path.dirname(__file__))
    candidates = [
        os.path.join(project_root, "web", clean),
        os.path.join(project_root, clean),
    ]
    if base_dir:
        candidates.insert(0, os.path.join(base_dir, clean))
    for c in candidates:
        try:
            if os.path.exists(c):
                return c
        except OSError:
            pass

    # Not found on disk — try the *_base64 sibling setting from the DB
    # (school_logo → school_logo_base64, headteacher_signature → headteacher_signature_base64)
    for setting_key in ("school_logo", "headteacher_signature"):
        if setting_key.replace("_", "") in clean.replace("_", "").replace("-", "").replace("/", "").lower() or \
           any(kw in clean.lower() for kw in ("logo", "sig", "signature")):
            # Determine which key to use
            if any(kw in clean.lower() for kw in ("sig", "signature")):
                b64 = get_branch_setting("headteacher_signature_base64", "") or ""
            else:
                b64 = get_branch_setting("school_logo_base64", "") or ""
            if b64 and "base64," in b64:
                return _resolve_image_path(b64)
            break

    return ""

def _cleanup_temp_images():
    """Remove any temp files created by _resolve_image_path."""
    global _temp_image_files
    for f in _temp_image_files:
        try:
            os.unlink(f)
        except Exception:
            pass
    _temp_image_files = []


def draw_pdf_watermark_and_footer(canvas, doc):
    canvas.saveState()
    try:
        # 1. Logo Watermark (90% fade = 10% opacity)
        # Resolve logo — supports relative paths, absolute paths, and Base64 data URIs
        logo_path = get_branch_setting("school_logo_base64", "") or get_branch_setting("school_logo", "") or ""
        logo_file = _resolve_image_path(logo_path)
        if logo_file:
            try:
                canvas.setFillAlpha(0.1) # 90% fade (10% opacity)
                canvas.setStrokeAlpha(0.1)
                page_w, page_h = doc.pagesize
                w, h = 220, 220
                x = (page_w - w) / 2.0
                y = (page_h - h) / 2.0
                canvas.drawImage(logo_file, x, y, width=w, height=h, mask='auto', preserveAspectRatio=True)
            except Exception as w_err:
                pass

        # 2. Footer (School Motto at bottom center, font size 8px, 50% fade)
        school_motto = get_branch_setting("school_motto", "") or ""
        if school_motto:
            canvas.setFont("Helvetica-Oblique", 8)
            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.setFillAlpha(0.5) # 50% fade
            page_w, page_h = doc.pagesize
            canvas.drawCentredString(page_w / 2.0, 15, f"{school_motto}")
    except Exception as e:
        print(f"PDF watermark/footer error: {e}")
    finally:
        canvas.restoreState()

def add_pdf_header(story, title_text=None):
    from reportlab.platypus import Image
    
    # Prefer the base64 setting (always available on Vercel), fall back to path
    logo_path = get_branch_setting("school_logo_base64", "") or get_branch_setting("school_logo", "") or ""
    logo_file = _resolve_image_path(logo_path)
    logo_exists = bool(logo_file)
    
    school_name = get_branch_setting("school_name", "Orion School System") or "Orion School System"
    school_motto = get_branch_setting("school_motto", "") or ""
    school_phone = get_branch_setting("school_phone", "") or ""
    school_email = get_branch_setting("school_email", "") or ""
    school_address = get_branch_setting("school_address", "") or ""
    gps_address = get_branch_setting("gps_address", "") or ""
    
    align_val = 0 if logo_exists else 1

    # Distinct header styles with proper leading and spacing to prevent text collisions
    name_style = ParagraphStyle(
        'HeaderSchoolName',
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        spaceAfter=2,
        alignment=align_val,
        textColor=colors.HexColor("#1d4ed8")
    )
    motto_style = ParagraphStyle(
        'HeaderSchoolMotto',
        fontName='Helvetica-Oblique',
        fontSize=9.5,
        leading=13,
        spaceAfter=3,
        alignment=align_val,
        textColor=colors.HexColor("#475569")
    )
    contact_style = ParagraphStyle(
        'HeaderSchoolContact',
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        spaceAfter=0,
        alignment=align_val,
        textColor=colors.HexColor("#64748b")
    )
    
    info_layout = []
    info_layout.append(Paragraph(school_name.upper(), name_style))
    if school_motto:
        info_layout.append(Paragraph(f"<i>{school_motto}</i>", motto_style))
    
    contact_parts = []
    if school_address:
        contact_parts.append(f"Address: {school_address}")
    if gps_address:
        contact_parts.append(f"GPS: {gps_address}")
    if school_phone:
        contact_parts.append(f"Phone: {school_phone}")
    if school_email:
        contact_parts.append(f"Email: {school_email}")
        
    if contact_parts:
        info_layout.append(Paragraph(" | ".join(contact_parts), contact_style))
        
    if logo_exists:
        try:
            img = Image(logo_file, width=54, height=54)
            img.hAlign = 'LEFT'
            
            header_table = Table([[img, info_layout]], colWidths=[65, 475])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (0,0), 0),
                ('RIGHTPADDING', (0,0), (0,0), 10),
                ('LEFTPADDING', (1,0), (1,0), 4),
                ('RIGHTPADDING', (1,0), (1,0), 0),
                ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 0),
            ]))
            story.append(header_table)
        except Exception as e:
            print(f"Error embedding logo in PDF: {e}")
            story.append(Paragraph(school_name.upper(), name_style))
            if school_motto:
                story.append(Paragraph(f"<i>{school_motto}</i>", motto_style))
            if contact_parts:
                story.append(Paragraph(" | ".join(contact_parts), contact_style))
    else:
        story.append(Paragraph(school_name.upper(), name_style))
        if school_motto:
            story.append(Paragraph(f"<i>{school_motto}</i>", motto_style))
        if contact_parts:
            story.append(Paragraph(" | ".join(contact_parts), contact_style))
            
    story.append(Spacer(1, 8))
    # Elegant horizontal accent separator line
    sep = Table([[""]], colWidths=[540], rowHeights=[1.5])
    sep.setStyle(TableStyle([
        ('LINEABOVE', (0,0), (-1,-1), 1.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(sep)
    story.append(Spacer(1, 12))
    
    if title_text:
        title_style = ParagraphStyle(
            'DocTitle',
            fontName='Helvetica-Bold',
            fontSize=12.5,
            leading=16,
            alignment=1,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=14
        )
        story.append(Paragraph(title_text.upper(), title_style))

def generate_student_id_card(student_id: str, output_path: str = None) -> tuple[bool, str]:
    """
    Generates a CR80 standard sized student ID Card PDF.
    """
    try:
        session = get_session()
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            return False, "Student not found."
            
        file_path = Path(output_path) if output_path else _get_pdf_dir() / f"id_card_{student_id}.pdf"
        
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
        
        school_name = get_branch_setting("school_name", "Orion School System")
        story.append(Paragraph(school_name.upper(), title_style))
        story.append(Spacer(1, 2*mm))
        
        from reportlab.platypus import Image
        photo_width = 18 * mm
        photo_height = 22 * mm
        
        photo_element = None
        if student.photo_path:
            resolved = _resolve_image_path(student.photo_path)
            if resolved:
                try:
                    photo_element = Image(resolved, width=photo_width, height=photo_height)
                except Exception:
                    pass
                    
        if not photo_element:
            photo_element = Table([["PHOTO"]], colWidths=[photo_width], rowHeights=[photo_height])
            photo_element.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#e2e8f0")),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#94a3b8")),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 6),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ]))

        details_data = [
            [Paragraph("Name:", body_style), Paragraph(f"<b>{student.first_name} {student.last_name}</b>", body_style)],
            [Paragraph("ID:", body_style), Paragraph(f"<b>{student.id}</b>", body_style)],
            [Paragraph("Class:", body_style), Paragraph(student.class_assigned.name if student.class_assigned else "Unassigned", body_style)],
            [Paragraph("Gender:", body_style), Paragraph(student.gender, body_style)],
            [Paragraph("Emerg:", body_style), Paragraph(student.emergency_contact_phone or "N/A", body_style)]
        ]
        t_details = Table(details_data, colWidths=[10*mm, 43*mm])
        t_details.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('LEFTPADDING', (0,0), (-1,-1), 2),
            ('RIGHTPADDING', (0,0), (-1,-1), 2),
        ]))
        
        grid_data = [
            [Paragraph("<b>STUDENT ID CARD</b>", ParagraphStyle('Sub', parent=body_style, fontName='Helvetica-Bold', fontSize=8, alignment=1)), ""],
            [photo_element, t_details]
        ]
        t_grid = Table(grid_data, colWidths=[20*mm, 55*mm])
        t_grid.setStyle(TableStyle([
            ('SPAN', (0,0), (1,0)),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 1),
            ('TOPPADDING', (0,0), (-1,-1), 1),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ]))
        story.append(t_grid)
        
        doc.build(story)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_admission_form(student_id: str, output_path: str = None) -> tuple[bool, str]:
    """
    Generates a full A4 sized student admission slip document.
    """
    try:
        session = get_session()
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            return False, "Student not found."
            
        file_path = Path(output_path) if output_path else _get_pdf_dir() / f"admission_slip_{student_id}.pdf"
        
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
        
        from reportlab.platypus import Image
        photo_width = 1.4 * inch
        photo_height = 1.7 * inch
        
        photo_element = None
        if student.photo_path:
            resolved = _resolve_image_path(student.photo_path)
            if resolved:
                try:
                    photo_element = Image(resolved, width=photo_width, height=photo_height)
                except Exception:
                    pass
                    
        if not photo_element:
            photo_element = Table([["PASSPORT PHOTO"]], colWidths=[photo_width], rowHeights=[photo_height])
            photo_element.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#94a3b8")),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            
        t_details = Table(student_details, colWidths=[2.0*inch, 3.0*inch])
        t_details.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        outer_data = [
            [t_details, photo_element]
        ]
        t_stud = Table(outer_data, colWidths=[5.0*inch, 1.7*inch])
        t_stud.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
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
        
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_fee_receipt(payment_id: int, output_path: str = None) -> tuple[bool, str]:
    """
    Generates a Receipt PDF for a recorded fee payment.
    """
    try:
        session = get_session()
        payment = session.query(Payment).filter(Payment.id == payment_id).first()
        if not payment:
            return False, "Payment transaction record not found."
            
        file_path = Path(output_path) if output_path else _get_pdf_dir() / f"fee_receipt_pmt_{payment_id}.pdf"
        
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
        outstanding = max(0.0, bill.amount_billed - bill.amount_paid)
        
        fee_name = bill.fee.name if (bill and bill.fee) else "Fee Item"
        is_arrears = "arrears" in fee_name.lower() or "debt brought forward" in fee_name.lower()
        fee_type_label = "Arrears / Previous Term Debt" if is_arrears else "Current Term Bill Particular"

        # Calculate student overall balance across all bills
        all_student_bills = session.query(StudentBill).filter(StudentBill.student_id == student.id).all()
        total_student_due = sum(max(0.0, sb.amount_billed - sb.amount_paid) for sb in all_student_bills)

        receipt_data = [
            [Paragraph("<b>Receipt Reference No:</b>", body_style), Paragraph(payment.reference_no or f"REC-{payment.id}", body_style)],
            [Paragraph("<b>Payment Date:</b>", body_style), Paragraph(payment.payment_date.strftime("%Y-%m-%d %H:%M"), body_style)],
            [Paragraph("<b>Student ID:</b>", body_style), Paragraph(student.id, body_style)],
            [Paragraph("<b>Student Name:</b>", body_style), Paragraph(f"{student.last_name}, {student.first_name}", body_style)],
            [Paragraph("<b>Particular Item:</b>", body_style), Paragraph(fee_name, body_style)],
            [Paragraph("<b>Bill Classification:</b>", body_style), Paragraph(f"<b>{fee_type_label}</b>", ParagraphStyle('FType', parent=body_style, textColor=colors.HexColor("#dc2626") if is_arrears else colors.HexColor("#2563eb")))],
            [Paragraph("<b>Particular Amount Billed:</b>", body_style), Paragraph(f"GHS {bill.amount_billed:.2f}", body_style)],
            [Paragraph("<b>Amount Paid in this Tx:</b>", body_style), Paragraph(f"GHS {payment.amount:.2f}", ParagraphStyle('PAmt', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#10b981")))],
            [Paragraph("<b>Particular Paid to Date:</b>", body_style), Paragraph(f"GHS {bill.amount_paid:.2f}", body_style)],
            [Paragraph("<b>Particular Outstanding:</b>", body_style), Paragraph(f"GHS {outstanding:.2f}", ParagraphStyle('OAmt', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#ef4444")))],
            [Paragraph("<b>Net Total Balance Remaining:</b>", body_style), Paragraph(f"<b>GHS {total_student_due:.2f}</b>", ParagraphStyle('NetAmt', parent=body_style, fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#dc2626")))],
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
        
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_report_card(student_id: str, examination_id: int, output_path: str = None) -> tuple[bool, str]:
    """
    Compiles terminal grades & assessment averages for a student.
    """
    try:
        session = get_session()
        student = session.query(Student).filter(Student.id == student_id).first()
        exam = session.query(Examination).filter(Examination.id == examination_id).first()
        
        if not student or not exam:
            return False, "Student or Examination session not found."

        approval = session.query(ClassResultApproval).filter(
            ClassResultApproval.class_id == student.class_id,
            ClassResultApproval.academic_year_id == exam.academic_year_id,
            ClassResultApproval.term_id == exam.term_id
        ).first()

        if not approval or approval.status not in ["Approved", "Published"]:
            return False, "Class results have not yet been approved by the headteacher. Please review and approve results before generating report cards."
            
        file_path = Path(output_path) if output_path else _get_pdf_dir() / f"report_card_{student_id}_exam_{examination_id}.pdf"
        
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
        
        # Compute student position & stats
        all_class_students = session.query(Student).filter(
            Student.class_id == student.class_id,
            Student.status == "Active"
        ).all()
        
        class_student_ids = [s.id for s in all_class_students]
        all_results = session.query(Result).filter(
            Result.examination_id == examination_id,
            Result.student_id.in_(class_student_ids)
        ).all()
        
        totals = {}
        subject_counts = {}
        for r in all_results:
            totals[r.student_id] = totals.get(r.student_id, 0.0) + r.total_score
            subject_counts[r.student_id] = subject_counts.get(r.student_id, 0) + 1
            
        for s_id in class_student_ids:
            if s_id not in totals:
                totals[s_id] = 0.0
                subject_counts[s_id] = 0
                
        sorted_totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        
        ranks = {}
        curr_rank = 1
        for idx, (s_id, tot) in enumerate(sorted_totals):
            if idx > 0 and tot < sorted_totals[idx - 1][1]:
                curr_rank = idx + 1
            ranks[s_id] = curr_rank
            
        def get_rank_suffix(rank):
            if 11 <= rank % 100 <= 13:
                suffix = "th"
            else:
                suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
            return f"{rank}{suffix}"
            
        pos = ranks.get(student_id, 0)
        pos_text = f"{get_rank_suffix(pos)} out of {len(class_student_ids)}" if pos > 0 else "N/A"
        
        student_avg = (totals.get(student_id, 0.0) / subject_counts.get(student_id, 1)) if subject_counts.get(student_id, 0) > 0 else 0.0
        
        # Student Meta Grid
        cls_name = student.class_assigned.name if student.class_assigned else "Unassigned"
        meta_data = [
            [Paragraph(f"<b>Student ID:</b> {student.id}", body_style), Paragraph(f"<b>Student Name:</b> {student.first_name} {student.last_name}", body_style)],
            [Paragraph(f"<b>Class Stream:</b> {cls_name}", body_style), Paragraph(f"<b>Academic Session:</b> {exam.academic_year.name} - {exam.term.name}", body_style)],
            [Paragraph(f"<b>Class Position:</b> {pos_text}", body_style), Paragraph(f"<b>Average Score:</b> {student_avg:.1f}%", body_style)]
        ]
        from reportlab.platypus import Image
        photo_width = 1.1 * inch
        photo_height = 1.3 * inch
        
        photo_element = None
        if student.photo_path:
            resolved = _resolve_image_path(student.photo_path)
            if resolved:
                try:
                    photo_element = Image(resolved, width=photo_width, height=photo_height)
                except Exception:
                    pass
                    
        if not photo_element:
            photo_element = Table([["PHOTO"]], colWidths=[photo_width], rowHeights=[photo_height])
            photo_element.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
                ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor("#94a3b8")),
                ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 8),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            
        t_meta_details = Table(meta_data, colWidths=[2.6*inch, 2.7*inch])
        t_meta_details.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 5),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        outer_meta_data = [
            [t_meta_details, photo_element]
        ]
        t_meta = Table(outer_meta_data, colWidths=[5.4*inch, 1.3*inch])
        t_meta.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('ALIGN', (1,0), (1,0), 'RIGHT'),
            ('BOTTOMPADDING', (0,0), (-1,-1), 0),
            ('TOPPADDING', (0,0), (-1,-1), 0),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 15))
        
        max_c = int(float(get_branch_setting("max_class_score", 30.0, session=session)))
        max_e = int(float(get_branch_setting("max_exam_score", 70.0, session=session)))
        
        # Results Table Header
        results_header = [
            Paragraph("<b>Subject Code</b>", th_style),
            Paragraph("<b>Subject Title</b>", th_style),
            Paragraph(f"<b>Class Score ({max_c})</b>", th_style),
            Paragraph(f"<b>Exam Score ({max_e})</b>", th_style),
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
        
        # Fetch custom remarks if available
        remark_rec = session.query(StudentReportRemark).filter(
            StudentReportRemark.student_id == student_id,
            StudentReportRemark.examination_id == examination_id
        ).first()
        
        teacher_remark_val = remark_rec.teacher_remark if (remark_rec and remark_rec.teacher_remark) else "Promising performance. Shows diligence and effort. Keep up the high standard."
        headteacher_remark_val = remark_rec.headteacher_remark if (remark_rec and remark_rec.headteacher_remark) else "Satisfactory progress made during the term. Approved for promotional transition."
        student_interest_val = remark_rec.student_interest if (remark_rec and remark_rec.student_interest) else "N/A"
        attitude_val = remark_rec.attitude_score if (remark_rec and remark_rec.attitude_score) else "Very Good"

        summary_block = [
            [Paragraph(f"<b>Overall Academic Performance Summary:</b>", ParagraphStyle('SBold', parent=body_style, fontName='Helvetica-Bold')), ""],
            [Paragraph(overall_gpa_text, body_style), ""],
            [Paragraph(f"<b>Student Interest / Hobbies:</b> {student_interest_val} | <b>Conduct / Attitude:</b> {attitude_val}", body_style), ""],
            [Paragraph(f"<b>Class Teacher Remarks:</b> {teacher_remark_val}", body_style), ""],
            [Paragraph(f"<b>Headteacher Remarks:</b> {headteacher_remark_val}", body_style), ""]
        ]
        t_sum = Table(summary_block, colWidths=[3.5*inch, 3.5*inch])
        t_sum.setStyle(TableStyle([
            ('SPAN', (0,0), (1,0)),
            ('SPAN', (0,1), (1,1)),
            ('SPAN', (0,2), (1,2)),
            ('SPAN', (0,3), (1,3)),
            ('SPAN', (0,4), (1,4)),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(t_sum)
        
        # --- NEXT ACADEMIC TERM FEE BILL & ARREARS STATEMENT ATTACHMENT ---
        story.append(Spacer(1, 10))
        
        # 1. Calculate student existing outstanding arrears across all bills
        all_student_bills = session.query(StudentBill).filter(StudentBill.student_id == student.id).all()
        student_arrears = sum(max(0.0, sb.amount_billed - sb.amount_paid) for sb in all_student_bills)

        # 2. Determine Next Term / Academic Year Fee Structure items for student class
        active_year_id = get_active_year_id(session)
        active_term_id = get_active_term_id(session)
        next_term_id = active_term_id + 1 if active_term_id < 3 else 1
        next_year_id = active_year_id + 1 if active_term_id >= 3 else active_year_id

        cls_level = student.class_assigned.level if (student.class_assigned and student.class_assigned.level) else "All"
        
        next_fees = session.query(Fee).filter(
            Fee.academic_year_id == next_year_id,
            Fee.term_id == next_term_id
        ).all()

        if not next_fees:
            next_fees = session.query(Fee).filter(
                Fee.academic_year_id == active_year_id,
                Fee.term_id == active_term_id,
                Fee.name != "Arrears / Debt Brought Forward"
            ).all()

        fee_items = []
        next_term_subtotal = 0.0
        for f in next_fees:
            if "arrears" in f.name.lower() or "debt brought forward" in f.name.lower():
                continue
            if f.class_level in ["All", cls_level]:
                fee_items.append((f.name, f.amount))
                next_term_subtotal += f.amount

        fee_section_title = ParagraphStyle('FeeSecTitle', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#2563eb"), fontSize=10, spaceBefore=6, spaceAfter=4)
        story.append(Paragraph("<b>NEXT ACADEMIC TERM / YEAR FEE BILL & ARREARS STATEMENT</b>", fee_section_title))

        fee_table_rows = [
            [
                Paragraph("<b>Fee Particular Description</b>", ParagraphStyle('FTH1', parent=th_style, textColor=colors.white, fontSize=9)),
                Paragraph("<b>Classification</b>", ParagraphStyle('FTH2', parent=th_style, textColor=colors.white, fontSize=9)),
                Paragraph("<b>Amount (GHS)</b>", ParagraphStyle('FTH3', parent=th_style, textColor=colors.white, fontSize=9, alignment=2))
            ]
        ]

        if fee_items:
            for item_name, item_amt in fee_items:
                fee_table_rows.append([
                    Paragraph(item_name, body_style),
                    Paragraph("Current Term Bill", body_style),
                    Paragraph(f"{item_amt:.2f}", ParagraphStyle('FAmt', parent=body_style, alignment=2))
                ])
        else:
            fee_table_rows.append([
                Paragraph("Standard Tuition & Facility Fee", body_style),
                Paragraph("Current Term Bill", body_style),
                Paragraph(f"{next_term_subtotal:.2f}", ParagraphStyle('FAmt', parent=body_style, alignment=2))
            ])

        # Next Term Subtotal Row
        fee_table_rows.append([
            Paragraph("<b>SUBTOTAL (Next Term Billed Fees)</b>", ParagraphStyle('SubB', parent=body_style, fontName='Helvetica-Bold')),
            Paragraph("<b>Next Term</b>", body_style),
            Paragraph(f"<b>{next_term_subtotal:.2f}</b>", ParagraphStyle('SubA', parent=body_style, fontName='Helvetica-Bold', alignment=2))
        ])

        # Arrears Row if > 0
        if student_arrears > 0:
            fee_table_rows.append([
                Paragraph("<b>⚠️ Arrears / Debt Brought Forward</b>", ParagraphStyle('ArrB', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#dc2626"))),
                Paragraph("<b>Previous Debt</b>", ParagraphStyle('ArrC', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#dc2626"))),
                Paragraph(f"<b>{student_arrears:.2f}</b>", ParagraphStyle('ArrA', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#dc2626"), alignment=2))
            ])

        # Net Total Payable Row
        total_payable = next_term_subtotal + student_arrears
        fee_table_rows.append([
            Paragraph("<b>TOTAL PAYABLE FOR NEXT TERM</b>", ParagraphStyle('TotB', parent=body_style, fontName='Helvetica-Bold', fontSize=9.5, textColor=colors.HexColor("#1e293b"))),
            Paragraph("<b>Net Total</b>", ParagraphStyle('TotC', parent=body_style, fontName='Helvetica-Bold', fontSize=9.5, textColor=colors.HexColor("#1e293b"))),
            Paragraph(f"<b>GHS {total_payable:.2f}</b>", ParagraphStyle('TotA', parent=body_style, fontName='Helvetica-Bold', fontSize=10.5, textColor=colors.HexColor("#2563eb"), alignment=2))
        ])

        t_fees = Table(fee_table_rows, colWidths=[3.8*inch, 1.7*inch, 1.5*inch])
        t_fees.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#475569")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#eff6ff")),
        ]))
        story.append(t_fees)
        
        # Signature block
        story.append(Spacer(1, 15))
        sig_raw = get_branch_setting("headteacher_signature_base64", "") or get_branch_setting("headteacher_signature", "") or ""
        sig_file = _resolve_image_path(sig_raw)
        sig_exists = bool(sig_file)

        if sig_exists:
            try:
                sig_img = Image(sig_file, width=100, height=35)
                sig_img.hAlign = 'RIGHT'
                head_cell = [sig_img, Paragraph("_____________________________<br/><b>Headteacher Endorsement</b>", ParagraphStyle('Sig2', parent=body_style, alignment=2))]
            except Exception:
                head_cell = Paragraph("_____________________________<br/><b>Headteacher Endorsement</b>", ParagraphStyle('Sig2', parent=body_style, alignment=2))
        else:
            head_cell = Paragraph("_____________________________<br/><b>Headteacher Endorsement</b>", ParagraphStyle('Sig2', parent=body_style, alignment=2))

        sig_data = [
            [Paragraph("_____________________________<br/><b>Class Teacher Signature</b>", ParagraphStyle('Sig1', parent=body_style, alignment=0)),
             head_cell]
        ]
        t_sig = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ]))
        story.append(t_sig)
        
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_class_report_cards(class_id: int, examination_id: int, student_ids: list[str] = None, output_path: str = None) -> tuple[bool, str]:
    """
    Generates a single merged PDF containing student report cards for a class, separated by page breaks.
    If student_ids list is provided, filters to only those student IDs.
    """
    try:
        session = get_session()
        cls = session.query(Class).filter(Class.id == class_id).first()
        exam = session.query(Examination).filter(Examination.id == examination_id).first()
        if not cls or not exam:
            return False, "Class or Examination session not found."
            
        query = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active")
        if student_ids:
            query = query.filter(Student.id.in_(student_ids))
        students = query.all()
        if not students:
            return False, "No matching active students found in this class."

        approval = session.query(ClassResultApproval).filter(
            ClassResultApproval.class_id == class_id,
            ClassResultApproval.academic_year_id == exam.academic_year_id,
            ClassResultApproval.term_id == exam.term_id
        ).first()

        if not approval or approval.status not in ["Approved", "Published"]:
            return False, "Class results have not yet been approved by the headteacher. Please review and approve results before generating report cards."
            
        file_path = Path(output_path) if output_path else _get_pdf_dir() / f"class_report_cards_class_{class_id}_exam_{examination_id}.pdf"
        
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=0.75*inch,
            rightMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'BodyClass',
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor("#334155")
        )
        th_style = ParagraphStyle(
            'TableHeaderClass',
            parent=body_style,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )
        
        # Compute student positions & stats for the class
        class_student_ids = [s.id for s in students]
        all_results = session.query(Result).filter(
            Result.examination_id == examination_id,
            Result.student_id.in_(class_student_ids)
        ).all()
        
        totals = {}
        subject_counts = {}
        for r in all_results:
            totals[r.student_id] = totals.get(r.student_id, 0.0) + r.total_score
            subject_counts[r.student_id] = subject_counts.get(r.student_id, 0) + 1
            
        for s_id in class_student_ids:
            if s_id not in totals:
                totals[s_id] = 0.0
                subject_counts[s_id] = 0
                
        sorted_totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        
        ranks = {}
        curr_rank = 1
        for idx, (s_id, tot) in enumerate(sorted_totals):
            if idx > 0 and tot < sorted_totals[idx - 1][1]:
                curr_rank = idx + 1
            ranks[s_id] = curr_rank
            
        def get_rank_suffix(rank):
            if 11 <= rank % 100 <= 13:
                suffix = "th"
            else:
                suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank % 10, "th")
            return f"{rank}{suffix}"
            
        story = []
        
        for idx, student in enumerate(students):
            if idx > 0:
                story.append(PageBreak())
                
            add_pdf_header(story, f"STUDENT TERMINAL REPORT CARD - {exam.name}")
            
            pos = ranks.get(student.id, 0)
            pos_text = f"{get_rank_suffix(pos)} out of {len(class_student_ids)}" if pos > 0 else "N/A"
            student_avg = (totals.get(student.id, 0.0) / subject_counts.get(student.id, 1)) if subject_counts.get(student.id, 0) > 0 else 0.0
            
            # Student Meta Grid
            cls_name = cls.name
            meta_data = [
                [Paragraph(f"<b>Student ID:</b> {student.id}", body_style), Paragraph(f"<b>Student Name:</b> {student.first_name} {student.last_name}", body_style)],
                [Paragraph(f"<b>Class Stream:</b> {cls_name}", body_style), Paragraph(f"<b>Academic Session:</b> {exam.academic_year.name} - {exam.term.name}", body_style)],
                [Paragraph(f"<b>Class Position:</b> {pos_text}", body_style), Paragraph(f"<b>Average Score:</b> {student_avg:.1f}%", body_style)]
            ]
            t_meta = Table(meta_data, colWidths=[3.5*inch, 3.5*inch])
            t_meta.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(t_meta)
            story.append(Spacer(1, 15))
            
            max_c = int(float(get_branch_setting("max_class_score", 30.0, session=session)))
            max_e = int(float(get_branch_setting("max_exam_score", 70.0, session=session)))
            
            # Results Table Header
            results_header = [
                Paragraph("<b>Subject Code</b>", th_style),
                Paragraph("<b>Subject Title</b>", th_style),
                Paragraph(f"<b>Class Score ({max_c})</b>", th_style),
                Paragraph(f"<b>Exam Score ({max_e})</b>", th_style),
                Paragraph("<b>Total (100)</b>", th_style),
                Paragraph("<b>Grade</b>", th_style),
                Paragraph("<b>Remarks</b>", th_style)
            ]
            
            table_rows = [results_header]
            
            student_results = [r for r in all_results if r.student_id == student.id]
            
            if not student_results:
                table_rows.append([Paragraph("No exam result records submitted for this period.", body_style)] + [""] * 6)
            else:
                for r in student_results:
                    table_rows.append([
                        Paragraph(r.subject.code, body_style),
                        Paragraph(r.subject.name, body_style),
                        Paragraph(f"{r.class_score:.1f}", body_style),
                        Paragraph(f"{r.exam_score:.1f}", body_style),
                        Paragraph(f"{r.total_score:.1f}", ParagraphStyle('TotalBoldClass', parent=body_style, fontName='Helvetica-Bold')),
                        Paragraph(r.grade or "9", ParagraphStyle('GStyleClass', parent=body_style, alignment=1)),
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
            
            if not student_results:
                t_res.setStyle(TableStyle([('SPAN', (0,1), (6,1))]))
                
            story.append(t_res)
            story.append(Spacer(1, 30))
            
            total_subjects = len(student_results)
            total_grade_units = sum(int(r.grade or 9) for r in student_results) if student_results else 0
            overall_gpa_text = f"Grade Point Sum: {total_grade_units} across {total_subjects} subjects." if student_results else "No graded subjects."
            
            # Fetch custom remarks if available
            remark_rec = session.query(StudentReportRemark).filter(
                StudentReportRemark.student_id == student.id,
                StudentReportRemark.examination_id == examination_id
            ).first()
            
            teacher_remark_val = remark_rec.teacher_remark if (remark_rec and remark_rec.teacher_remark) else "Promising performance. Shows diligence and effort. Keep up the high standard."
            headteacher_remark_val = remark_rec.headteacher_remark if (remark_rec and remark_rec.headteacher_remark) else "Satisfactory progress made during the term. Approved for promotional transition."
            
            summary_block = [
                [Paragraph(f"<b>Overall Academic Performance Summary:</b>", ParagraphStyle('SBoldClass', parent=body_style, fontName='Helvetica-Bold')), ""],
                [Paragraph(overall_gpa_text, body_style), ""],
                [Paragraph(f"<b>Class Teacher Remarks:</b> {teacher_remark_val}", body_style), ""],
                [Paragraph(f"<b>Headteacher Remarks:</b> {headteacher_remark_val}", body_style), ""]
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
            story.append(Spacer(1, 40))
            
            sig_data = [
                [Paragraph("_____________________________<br/><b>Class Teacher Signature</b>", ParagraphStyle('Sig1Class', parent=body_style, alignment=0)),
                 Paragraph("_____________________________<br/><b>Headteacher Endorsement</b>", ParagraphStyle('Sig2Class', parent=body_style, alignment=2))]
            ]
            t_sig = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
            story.append(t_sig)
            
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_class_report_cards_zip(class_id: int, examination_id: int, student_ids: list[str] = None, output_path: str = None) -> tuple[bool, str]:
    """
    Generates individual report card PDFs for active students in a class
    and packages them into a single downloadable ZIP archive.
    If student_ids list is provided, packages only those students.
    """
    import zipfile
    try:
        session = get_session()
        cls = session.query(Class).filter(Class.id == class_id).first()
        exam = session.query(Examination).filter(Examination.id == examination_id).first()
        if not cls or not exam:
            return False, "Class or Examination session not found."

        query = session.query(Student).filter(Student.class_id == class_id, Student.status == "Active")
        if student_ids:
            query = query.filter(Student.id.in_(student_ids))
        students = query.all()
        if not students:
            return False, "No matching active students found in this class."

        approval = session.query(ClassResultApproval).filter(
            ClassResultApproval.class_id == class_id,
            ClassResultApproval.academic_year_id == exam.academic_year_id,
            ClassResultApproval.term_id == exam.term_id
        ).first()

        if not approval or approval.status not in ["Approved", "Published"]:
            return False, "Class results have not yet been approved by the headteacher. Please review and approve results before generating report cards."

        zip_file_path = Path(output_path) if output_path else _get_pdf_dir() / f"class_reports_bundle_{class_id}_exam_{examination_id}.zip"

        with zipfile.ZipFile(str(zip_file_path), 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for s in students:
                s_filename = f"Report_Card_{s.id}_{s.first_name}_{s.last_name}.pdf".replace(" ", "_")
                s_pdf_path = _get_pdf_dir() / s_filename
                success, path_or_err = generate_report_card(s.id, examination_id, str(s_pdf_path))
                if success and Path(path_or_err).exists():
                    zip_file.write(path_or_err, arcname=s_filename)

        session.close()
        return True, str(zip_file_path)
    except Exception as e:
        return False, str(e)

def generate_financial_statement(output_path: str = None) -> tuple[bool, str]:
    """
    Compiles all system payments and operational expenses into a Financial PDF Ledger sheet.
    """
    try:
        session = get_session()
        payments = session.query(Payment).all()
        expenses = session.query(Expense).all()
        
        file_path = Path(output_path) if output_path else _get_pdf_dir() / "financial_income_statement.pdf"
        
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
        
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        session.close()
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_payslip_pdf(payslip, output_path: str = None):
    try:
        file_path = Path(output_path) if output_path else _get_pdf_dir() / f"payslip_{payslip.staff_id}_{payslip.pay_period.replace(' ', '_')}.pdf"
        
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
        story.append(Spacer(1, 20))
        sig_raw = get_branch_setting("headteacher_signature_base64", "") or get_branch_setting("headteacher_signature", "") or ""
        sig_file = _resolve_image_path(sig_raw)
        sig_exists = bool(sig_file)
        if sig_exists:
            try:
                sig_img = Image(sig_file, width=90, height=30)
                head_cell = [sig_img, Paragraph("<b>Headteacher Endorsement</b>", ParagraphStyle('HeadSig', parent=body_style, alignment=1))]
            except Exception:
                head_cell = Paragraph("_____________________________<br/><b>Headteacher Endorsement</b>", ParagraphStyle('HeadSig', parent=body_style, alignment=1))
        else:
            head_cell = Paragraph("_____________________________<br/><b>Headteacher Endorsement</b>", ParagraphStyle('HeadSig', parent=body_style, alignment=1))

        sig_data = [
            [Paragraph("Prepared by Bursar: ____________________", body_style),
             head_cell,
             Paragraph("Staff Signature: ____________________", ParagraphStyle('RightSig', parent=body_style, alignment=2))]
        ]
        t_sig = Table(sig_data, colWidths=[2.4*inch, 2.4*inch, 2.4*inch])
        t_sig.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ]))
        story.append(t_sig)
        
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        return str(file_path), None
    except Exception as e:
        return None, str(e)

def generate_class_summary_pdf(class_name: str, exam_name: str, headers: list, rows: list, output_path: str = None) -> tuple[bool, str]:
    """
    Generates a Landscape A4 PDF containing the class report summary table.
    """
    try:
        file_path = Path(output_path) if output_path else _get_pdf_dir() / "class_report_summary.pdf"
        
        from reportlab.lib.pagesizes import A4, landscape
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'BodySummary',
            fontName='Helvetica',
            fontSize=7,
            textColor=colors.HexColor("#334155")
        )
        th_style = ParagraphStyle(
            'TableHeaderSummary',
            parent=body_style,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )
        
        story = []
        add_pdf_header(story, f"CLASS REPORT SUMMARY - {class_name.upper()}")
        
        title_style = ParagraphStyle(
            'SubSummary',
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=1,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=12
        )
        story.append(Paragraph(f"EXAMINATION SESSION: {exam_name.upper()}", title_style))
        
        table_rows = []
        table_rows.append([Paragraph(f"<b>{h}</b>", th_style) for h in headers])
        
        for r in rows:
            table_rows.append([Paragraph(str(cell), body_style) for cell in r])
            
        col_count = len(headers)
        # Landscape A4 width is 841.89 points. Printable width is ~770 points.
        col_width = 770.0 / col_count
        
        t = Table(table_rows, colWidths=[col_width] * col_count)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2563eb")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        story.append(t)
        
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_attendance_report_pdf(class_name: str, date_range: str, headers: list, rows: list, output_path: str = None) -> tuple[bool, str]:
    """
    Generates a Landscape A4 PDF containing the student attendance report.
    """
    try:
        file_path = Path(output_path) if output_path else _get_pdf_dir() / "attendance_report.pdf"
        
        from reportlab.lib.pagesizes import A4, landscape
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'BodyAtt',
            fontName='Helvetica',
            fontSize=8,
            textColor=colors.HexColor("#334155")
        )
        th_style = ParagraphStyle(
            'TableHeaderAtt',
            parent=body_style,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )
        
        story = []
        add_pdf_header(story, f"STUDENT ATTENDANCE REPORT - {class_name.upper()}")
        
        title_style = ParagraphStyle(
            'SubAtt',
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=1,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=12
        )
        story.append(Paragraph(f"DATE RANGE: {date_range.upper()}", title_style))
        
        table_rows = []
        table_rows.append([Paragraph(f"<b>{h}</b>", th_style) for h in headers])
        
        for r in rows:
            table_rows.append([Paragraph(str(cell), body_style) for cell in r])
            
        col_count = len(headers)
        col_width = 770.0 / col_count
        
        t = Table(table_rows, colWidths=[col_width] * col_count)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2563eb")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('PADDING', (0,0), (-1,-1), 4),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        story.append(t)
        
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_timetable_pdf(class_name: str, term_name: str, headers: list, rows: list, output_path: str = None) -> tuple[bool, str]:
    """
    Generates a Landscape A4 PDF containing the class timetable schedule.
    """
    try:
        file_path = Path(output_path) if output_path else _get_pdf_dir() / "timetable.pdf"
        
        from reportlab.lib.pagesizes import A4, landscape
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'BodyTT',
            fontName='Helvetica',
            fontSize=8,
            alignment=1, # Center text in cells
            textColor=colors.HexColor("#334155")
        )
        th_style = ParagraphStyle(
            'TableHeaderTT',
            parent=body_style,
            fontName='Helvetica-Bold',
            fontSize=9,
            alignment=1,
            textColor=colors.white
        )
        
        story = []
        add_pdf_header(story, f"CLASS TIMETABLE SCHEDULE - {class_name.upper()}")
        
        title_style = ParagraphStyle(
            'SubTT',
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=1,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=12
        )
        story.append(Paragraph(f"ACADEMIC SESSION: {term_name.upper()}", title_style))
        
        table_rows = []
        table_rows.append([Paragraph(f"<b>{h}</b>", th_style) for h in headers])
        
        for r_idx, r in enumerate(rows):
            row_cells = []
            for c_idx, cell in enumerate(r):
                formatted_cell = cell.replace('\n', '<br/>')
                
                if formatted_cell in ["BREAK", "LUNCH"]:
                    txt_style = ParagraphStyle('BreakTxt', parent=body_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#475569"))
                    row_cells.append(Paragraph(formatted_cell, txt_style))
                else:
                    if c_idx == 0:
                        ts_style = ParagraphStyle('TSCol', parent=body_style, fontName='Helvetica-Bold', alignment=0)
                        row_cells.append(Paragraph(formatted_cell, ts_style))
                    else:
                        row_cells.append(Paragraph(formatted_cell, body_style))
            table_rows.append(row_cells)
            
        col_count = len(headers)
        col_widths = [120] + [(770.0 - 120.0) / (col_count - 1)] * (col_count - 1)
        
        t = Table(table_rows, colWidths=col_widths)
        
        t_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2563eb")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('PADDING', (0,0), (-1,-1), 8),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ])
        
        for r_idx, r in enumerate(rows):
            # Check if this row is a break (either all cells contain BREAK/LUNCH, or it's empty)
            has_substances = False
            for cell in r[1:]:
                c_upper = str(cell).strip().upper()
                if c_upper and c_upper not in ["BREAK", "LUNCH", "MORNING BREAK", "LUNCH BREAK", "FREE SLOT", ""]:
                    has_substances = True
                    break
            if not has_substances and len(r) > 1:
                t_style.add('SPAN', (1, r_idx + 1), (col_count - 1, r_idx + 1))
                t_style.add('BACKGROUND', (1, r_idx + 1), (col_count - 1, r_idx + 1), colors.HexColor("#cbd5e1"))
        
        t.setStyle(t_style)
        story.append(t)
        
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_inventory_report_pdf(headers: list, rows: list, output_path: str = None) -> tuple[bool, str]:
    """
    Generates an A4 PDF containing the school inventory stock report.
    """
    try:
        file_path = Path(output_path) if output_path else _get_pdf_dir() / "inventory_report.pdf"
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'BodyInv',
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor("#334155")
        )
        th_style = ParagraphStyle(
            'TableHeaderInv',
            parent=body_style,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )
        
        story = []
        add_pdf_header(story, "INVENTORY STOCK REPORT")
        
        title_style = ParagraphStyle(
            'SubInv',
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=1,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=12
        )
        story.append(Paragraph(f"DATE GENERATED: {datetime.date.today().strftime('%Y-%m-%d')}", title_style))
        
        table_rows = []
        table_rows.append([Paragraph(f"<b>{h}</b>", th_style) for h in headers])
        
        for r in rows:
            table_rows.append([Paragraph(str(cell), body_style) for cell in r])
            
        col_count = len(headers)
        col_width = 520.0 / col_count
        
        t = Table(table_rows, colWidths=[col_width] * col_count)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2563eb")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        story.append(t)
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_library_report_pdf(headers: list, rows: list, output_path: str = None) -> tuple[bool, str]:
    """
    Generates an A4 PDF containing the library books catalogue report.
    """
    try:
        file_path = Path(output_path) if output_path else _get_pdf_dir() / "library_books_report.pdf"
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle(
            'BodyLib',
            fontName='Helvetica',
            fontSize=9,
            textColor=colors.HexColor("#334155")
        )
        th_style = ParagraphStyle(
            'TableHeaderLib',
            parent=body_style,
            fontName='Helvetica-Bold',
            textColor=colors.white
        )
        
        story = []
        add_pdf_header(story, "LIBRARY BOOK CATALOGUE REPORT")
        
        title_style = ParagraphStyle(
            'SubLib',
            fontName='Helvetica-Bold',
            fontSize=10,
            alignment=1,
            textColor=colors.HexColor("#1e293b"),
            spaceAfter=12
        )
        story.append(Paragraph(f"DATE GENERATED: {datetime.date.today().strftime('%Y-%m-%d')}", title_style))
        
        table_rows = []
        table_rows.append([Paragraph(f"<b>{h}</b>", th_style) for h in headers])
        
        for r in rows:
            table_rows.append([Paragraph(str(cell), body_style) for cell in r])
            
        col_count = len(headers)
        col_width = 520.0 / col_count
        
        t = Table(table_rows, colWidths=[col_width] * col_count)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2563eb")),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ('PADDING', (0,0), (-1,-1), 6),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        story.append(t)
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        return True, str(file_path)
    except Exception as e:
        return False, str(e)

def generate_ledger_report_pdf(headers: list, rows: list, output_path: str = None) -> tuple[bool, str]:
    """
    Generates a landscape A4 PDF report for the Income & Expense Ledger.
    """
    try:
        from reportlab.lib.pagesizes import landscape
        file_path = Path(output_path) if output_path else _get_pdf_dir() / "income_expense_ledger.pdf"
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=landscape(A4),
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle('BodyLedger', fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#334155"))
        th_style = ParagraphStyle('THLedger', parent=body_style, fontName='Helvetica-Bold', textColor=colors.white)
        
        story = []
        add_pdf_header(story, "INCOME & EXPENSE LEDGER STATEMENT")
        
        title_style = ParagraphStyle('SubLedger', fontName='Helvetica-Bold', fontSize=10, alignment=1, textColor=colors.HexColor("#1e293b"), spaceAfter=12)
        story.append(Paragraph(f"DATE GENERATED: {datetime.date.today().strftime('%Y-%m-%d')}", title_style))
        
        table_rows = [[Paragraph(f"<b>{h}</b>", th_style) for h in headers]]
        for r in rows:
            table_rows.append([Paragraph(str(cell), body_style) for cell in r])
            
        t = Table(table_rows, colWidths=[45, 65, 175, 95, 60, 75, 75, 80, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])
        ]))
        story.append(t)
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        return True, str(file_path)
    except Exception as e:
        print(f"Error generating ledger PDF: {e}")
        return False, str(e)

def generate_balances_report_pdf(headers: list, rows: list, output_path: str = None) -> tuple[bool, str]:
    """
    Generates an A4 PDF report for Outstanding Fee Balances and Debtors.
    """
    try:
        file_path = Path(output_path) if output_path else _get_pdf_dir() / "outstanding_balances_report.pdf"
        doc = SimpleDocTemplate(
            str(file_path),
            pagesize=A4,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )
        styles = getSampleStyleSheet()
        body_style = ParagraphStyle('BodyBal', fontName='Helvetica', fontSize=9, textColor=colors.HexColor("#334155"))
        th_style = ParagraphStyle('THBal', parent=body_style, fontName='Helvetica-Bold', textColor=colors.white)
        
        story = []
        add_pdf_header(story, "OUTSTANDING FEE BALANCES & DEBTORS REPORT")
        
        title_style = ParagraphStyle('SubBal', fontName='Helvetica-Bold', fontSize=10, alignment=1, textColor=colors.HexColor("#1e293b"), spaceAfter=12)
        story.append(Paragraph(f"DATE GENERATED: {datetime.date.today().strftime('%Y-%m-%d')}", title_style))
        
        table_rows = [[Paragraph(f"<b>{h}</b>", th_style) for h in headers]]
        for r in rows:
            table_rows.append([Paragraph(str(cell), body_style) for cell in r])
            
        t = Table(table_rows, colWidths=[80, 140, 75, 75, 75, 75])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#991b1b")),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")])
        ]))
        story.append(t)
        doc.build(story, onFirstPage=draw_pdf_watermark_and_footer, onLaterPages=draw_pdf_watermark_and_footer)
        return True, str(file_path)
    except Exception as e:
        print(f"Error generating balances PDF: {e}")
        return False, str(e)

