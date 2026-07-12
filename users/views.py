import csv

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.template.loader import get_template
from reportlab.pdfgen import canvas
from .permissions import role_required
from .models import StudentProfile
from .forms import StudentSearchForm, FeeUpdateForm, StudentImportForm
from .services import import_students_from_excel, StudentImportError

SKIPPED_REPORT_FIELDS = ['row', 'student_id', 'full_name', 'course', 'reason']

# Assuming 0.00 is the requirement, or adjust to your "Minimum Requirement"
MINIMUM_BALANCE_THRESHOLD = 10000

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
    
    # check 3: success
    student_profile.is_approved = True
    student_profile.approved_by = request.user
    student_profile.date_approved = timezone.now()
    student_profile.save()

    messages.success(request, "Student approved successfully")
    return redirect('accounts_dashboard')


@login_required
@role_required(['REGISTRAR'])
def registrar_dashboard(request):
    # Fetch only students approved by Accounts
    approved_students = StudentProfile.objects.filter(is_approved=True).order_by('student_id')

    return render(request, 'registrar/dashboard.html', {
        'approved_students': approved_students
    })


@login_required
@role_required(['REGISTRAR'])
def generate_exam_card(request, student_id):
    student = get_object_or_404(StudentProfile, student_id=student_id)

    if not student.is_approved:
        return HttpResponse("Student not approved", status=403)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="exam_card_{student.student_id}.pdf"'

    p = canvas.Canvas(response)

    # Content
    p.setFont("Helvetica", 14)
    p.drawString(100, 800, "KIMC EXAMINATION CARD")

    p.setFont("Helvetica", 12)
    p.drawString(100, 750, f"Student ID: {student.student_id}")
    p.drawString(100, 730, f"Name: {student.user.get_full_name()}")
    p.drawString(100, 710, f"Course: {student.course}")

    p.drawString(100, 670, "Status: APPROVED")

    p.drawString(100, 630, "Signature: __________________")

    p.showPage()
    p.save()

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