from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),

    path('ict/dashboard/', views.ict_dashboard, name='ict_dashboard'),
    path('accounts/dashboard/', views.accounts_dashboard, name='accounts_dashboard'),
    path('registrar/dashboard/', views.registrar_dashboard, name='registrar_dashboard'),
    path('student/dashboard/', views.student_dashboard, name='student_dashboard'),
    path('accounts/approve/<path:student_id>/', views.approve_student, name='approve_student'),
    path('registrar/exam-card/<path:student_id>/', views.generate_exam_card, name='generate_exam_card'),
    path('student/profile/', views.student_dashboard, name='student_dashboard'),
    path('ict/import-students/', views.import_students, name='import_students'),
    path('ict/import-students/report/', views.download_skipped_report, name='download_skipped_report'),
]