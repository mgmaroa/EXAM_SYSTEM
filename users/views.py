import csv
import string
import os

# LOGO SECTION START
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Image, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from django.http import HttpResponse
from io import BytesIO

# LOGO SECTION END

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.template.loader import get_template
from django.contrib.staticfiles import finders
from django.core.paginator import Paginator
from django.db.models import Q
from reportlab.pdfgen import canvas
from .permissions import role_required
from .models import StudentProfile
from .forms import StudentSearchForm, FeeUpdateForm, StudentImportForm
from .services import import_students_from_excel, StudentImportError

SKIPPED_REPORT_FIELDS = ['row', 'student_id', 'full_name', 'course', 'reason']

# Assuming 0.00 is the requirement, or adjust to your "Minimum Requirement"
MINIMUM_BALANCE_THRESHOLD = 10000

# serial number generation function
def compute_checksum_char(value: str) -> str:
    """
    Simple checksum: sum of character codes mod 36, mapped to 0-9A-Z.
    Not cryptographic — just catches typos/transcription errors.
    """
    alphabet = string.digits + string.ascii_uppercase  # 0-9, A-Z
    total = sum(ord(c) for c in value)
    return alphabet[total % 36]

def generate_serial_number():
    """
    Generates e.g. SN-2026-000123-K
    The trailing letter is a checksum so mistyped/forged serials
    can be caught on verification.
    """
    year = timezone.now().year
    prefix = f"KIMC-{year}-"

    last = (
        StudentProfile.objects
        .filter(serial_number__startswith=prefix)
        .order_by('-serial_number')
        .first()
    )

    if last and last.serial_number:
        # strip checksum char before parsing the sequence
        last_body = last.serial_number.rsplit('-', 1)[0]
        last_seq = int(last_body.split('-')[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    body = f"{prefix}{next_seq:06d}"
    checksum = compute_checksum_char(body)
    return f"{body}-{checksum}"


# Create your views here.
@login_required
def dashboard_redirect(request):
    user = request.user

    if user.role == 'ICT':
        # return redirect('admin:index')
        return redirect('ict_dashboard')
    elif user.role == 'ACCOUNTS':
        return redirect('accounts_dashboard')
    elif user.role == 'REGISTRAR':
        return redirect('registrar_dashboard')
    else:
        return redirect('student_dashboard')

@login_required
@role_required(['ICT'])
def ict_dashboard(request):
    return render(request, 'ict/dashboard.html')

@login_required
@role_required(['ACCOUNTS'])
def accounts_dashboard(request):
    search_form = StudentSearchForm() # Handles the get request i.e display form
    fee_form = None    
    student_profile = None

    if request.method == 'POST':

        # SEARCH FORM
        if 'search_student' in request.POST:
            search_form = StudentSearchForm(request.POST)

            if search_form.is_valid():
                student_id = search_form.cleaned_data['student_id']

                try:
                    student_profile = StudentProfile.objects.get(student_id=student_id)

                    # Only allow editing if not approved
                    if not student_profile.is_approved:
                        fee_form = FeeUpdateForm(instance=student_profile)

                except StudentProfile.DoesNotExist:
                    messages.error(request, "Student not found.")

        # UPDATE FEE FORM
        elif 'update_fee' in request.POST:
            student_id = request.POST.get('student_id')
            student_profile = get_object_or_404(StudentProfile, student_id=student_id)

            if student_profile.is_approved:
                messages.warning(request, "Cannot update. Student already approved")
            else:
                fee_form = FeeUpdateForm(request.POST, instance=student_profile)
                if fee_form.is_valid():
                    profile = fee_form.save(commit=False)

                    # mark as updated
                    profile.fee_updated = True

                    profile.save()
                    messages.success(request, "Fee balance updated successfully")

                    # RELOAD UPDATED INSTANCES
                    student_profile.refresh_from_db()

                else:
                    messages.error(request, "Error updating fee.")
            # ALWAYS REINITIALIZE FORMS
            search_form = StudentSearchForm(initial={'student_id': student_profile.student_id})

    return render(request, 'accounts/dashboard.html', {
        'search_form': search_form,
        'fee_form': fee_form,
        'student_profile': student_profile,
        'threshold': MINIMUM_BALANCE_THRESHOLD
    })

@login_required
@role_required(['ACCOUNTS'])
def approve_student(request, student_id):
    student_profile = get_object_or_404(StudentProfile, student_id=student_id)

    # check 1: Prevent double approval
    if student_profile.is_approved:
        messages.info(request, "Student already approved")
        return redirect('accounts_dashboard')
    
    # check 2: Verify Fee requirement
    if student_profile.fee_balance > MINIMUM_BALANCE_THRESHOLD:
        messages.error(request, f"Cannot approve. Outstanding balance: {student_profile.fee_balance}")
        return redirect('accounts_dashboard')
    
    # check 3: Fee balance must have been reviewed/updated first
    if not student_profile.fee_updated:
        messages.error(request, "Cannot approve. Fee balance has not been updated yet.")
        return redirect('accounts_dashboard')

    # check 4: success
    student_profile.is_approved = True
    student_profile.approved_by = request.user
    student_profile.date_approved = timezone.now()
    student_profile.serial_number = generate_serial_number()
    student_profile.save()

    messages.success(request, f"Student approved successfully. Serial: {student_profile.serial_number}")
    return redirect('accounts_dashboard')


@login_required
@role_required(['REGISTRAR'])
def registrar_dashboard(request):
    query = request.GET.get('q', '').strip()

    # select_related('user') avoids one extra query per row when the
    # template calls student.user.get_full_name() — worth keeping even
    # without the search feature.
    approved_students = (
        StudentProfile.objects
        .filter(is_approved=True)
        .select_related('user')
        .order_by('student_id')
    )

    if query:
        approved_students = approved_students.filter(
            Q(student_id__icontains=query) |
            Q(user__first_name__icontains=query) |
            Q(user__last_name__icontains=query) |
            Q(course__icontains=query)
        )

    paginator = Paginator(approved_students, 25)  # 25 rows per page
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'registrar/dashboard.html', {
        'page_obj': page_obj,
        'query': query,
        'total_approved': StudentProfile.objects.filter(is_approved=True).count(),
    })


@login_required
@role_required(['REGISTRAR'])
def generate_exam_card(request, student_id):
    student = get_object_or_404(StudentProfile, student_id=student_id)
    if not student.is_approved:
        return HttpResponse("Student not approved", status=403)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('title', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=18)
    small_center = ParagraphStyle('small', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8)
    cell_label_style = ParagraphStyle('cell_label', parent=styles['Normal'], fontSize=11, leading=13, fontName='Helvetica-Bold')
    cell_style = ParagraphStyle('cell', parent=styles['Normal'], fontSize=11, leading=13)

    elements = []

    # Logo
    logo_path = finders.find('img/kimc_logo.jpeg')
    if logo_path and os.path.exists(logo_path):
        elements.append(Image(logo_path, width=3*cm, height=3*cm, hAlign='CENTER'))

    # Institution header text
    elements.append(Paragraph("<b>KENYA INSTITUTE OF MASS COMMUNICATION</b>", small_center))
    elements.append(Paragraph("<b>P.O. Box 42422 - 00100 NAIROBI | Uholo Road, Nairobi South B, off Mombasa Road</b>", small_center))
    elements.append(Spacer(1, 12))

    # Card title
    elements.append(Paragraph("EXAMINATION CARD", title_style))
    elements.append(Spacer(1, 16))

    # Details table — values wrapped in Paragraph so long text wraps instead of overflowing
    data = [
        [Paragraph("Serial Number", cell_label_style), Paragraph(student.serial_number, cell_style)],
        [Paragraph("Student ID", cell_label_style), Paragraph(student.student_id, cell_style)],
        [Paragraph("Full Name", cell_label_style), Paragraph(student.user.get_full_name(), cell_style)],
        [Paragraph("Course", cell_label_style), Paragraph(student.course, cell_style)],
        [Paragraph("Approval Date", cell_label_style), Paragraph(student.date_approved.strftime("%d %b %Y"), cell_style)],
    ]
    table = Table(data, colWidths=[6*cm, 9*cm])
    table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 40))

    # Registrar / signature section
    elements.append(Paragraph("<b>Academic Registrar:</b>", styles['Normal']))
    elements.append(Spacer(1, 30))

    sig_data = [["Signature: _______", "Stamp: _______"]]
    sig_table = Table(sig_data, colWidths=[9*cm, 9*cm])
    sig_table.setStyle(TableStyle([('FONTSIZE', (0, 0), (-1, -1), 11)]))
    elements.append(sig_table)

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="exam_card_{student.student_id}.pdf"'
    return response

@login_required
@role_required(['STUDENT'])
def student_dashboard(request):
    # Retrieve the profile linked to the currently logged-in user
    try:
        profile = request.user.profile
    except StudentProfile.DoesNotExist:
        profile = None
    
    return render(request, 'student/profile.html', {
        'profile': profile,
        'threshold': MINIMUM_BALANCE_THRESHOLD
    })


@login_required
@role_required(['ICT'])
def import_students(request):
    result = None
    error = None

    if request.method == 'POST':
        form = StudentImportForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                result = import_students_from_excel(form.cleaned_data['excel_file'])

                # Stash the skipped rows in the session so they can be downloaded
                # as a CSV without re-uploading or re-processing the file.
                request.session['last_import_skipped'] = result.skipped

                if result.created_count:
                    messages.success(request, f"Created {result.created_count} student account(s).")
                if result.skipped_count:
                    messages.warning(
                        request,
                        f"Skipped {result.skipped_count} row(s) — see the report below for details."
                    )
                if not result.created_count and not result.skipped_count:
                    messages.info(request, "No rows were processed.")

            except StudentImportError as exc:
                error = str(exc)
                messages.error(request, error)
        else:
            error = "Please correct the errors below."
    else:
        form = StudentImportForm()

    return render(request, 'ict/import_students.html', {
        'form': form,
        'result': result,
        'error': error,
        'has_report': bool(request.session.get('last_import_skipped')),
    })

@login_required
@role_required(['ICT'])
def download_skipped_report(request):
    skipped = request.session.get('last_import_skipped')
    if not skipped:
        messages.info(request, "No skipped-rows report available yet. Run an import first.")
        return redirect('import_students')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="skipped_students.csv"'

    writer = csv.DictWriter(response, fieldnames=SKIPPED_REPORT_FIELDS)
    writer.writeheader()
    writer.writerows(skipped)

    return response