from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

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