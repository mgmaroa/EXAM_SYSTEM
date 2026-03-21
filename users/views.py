from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .permissions import role_required

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
    return HttpResponse("Accounts Dashboard")

@role_required(['REGISTRAR'])
@login_required
def registrar_dashboard(request):
    return HttpResponse("Registrar Dashboard")

@role_required(['STUDENT'])
@login_required
def student_dashboard(request):
    return HttpResponse("Student Dashboard")