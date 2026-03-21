from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib import messages
from django.utils import timezone
from .permissions import role_required
from .models import StudentProfile
from .forms import StudentSearchForm

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
    student_profile = None

    if request.method == 'POST':
        search_form = StudentSearchForm(request.POST)

        if search_form.is_valid():
            student_id = search_form.cleaned_data['student_id']

            try:
                student_profile = StudentProfile.objects.get(student_id=student_id)
            except StudentProfile.DoesNotExist:
                messages.error(request, "Student ID not found.")
    
    return render(request, 'accounts/dashboard.html', {
        'search_form': search_form,
        'student_profile': student_profile
    })


@role_required(['REGISTRAR'])
@login_required
def registrar_dashboard(request):
    return HttpResponse("Registrar Dashboard")

@role_required(['STUDENT'])
@login_required
def student_dashboard(request):
    return HttpResponse("Student Dashboard")