from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),

    path('ict/dashboard/', views.ict_dashboard, name='ict_dashboard'),
    path('accounts/dashboard/', views.accounts_dashboard, name='accounts_dashboard'),
    path('registrar/dashboard/', views.registrar_dashboard, name='registrar_dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
]