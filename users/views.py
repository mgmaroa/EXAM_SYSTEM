from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from django.template.loader import get_template
from reportlab.pdfgen import canvas
from .permissions import role_required
from .models import StudentProfile
from .forms import StudentSearchForm, FeeUpdateForm

# Assuming 0.00 is the requirement, or adjust to your "Minimum Requirement"
MINIMUM_BALANCE_THRESHOLD = 10000

# Create your views here.
@login_required
def dashboard_redirect(request):
    user = request.user

    if user.role == 'ICT':
        return redirect('ict_dashboard')
    elif user.role == 'ACCOUNTS':
        return redirect('accounts_dashboard')
    elif user.role == 'REGISTRAR':
        return redirect('registrar_dashboard')
    else:
        return redirect('student_dashboard')

@role_required(['ICT'])
@login_required
def ict_dashboard(request):
    return HttpResponse("ICT Dashboard")

@role_required(['ACCOUNTS'])
@login_required
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

@role_required(['STUDENT'])
@login_required
def student_dashboard(request):
    return HttpResponse("Student Dashboard")