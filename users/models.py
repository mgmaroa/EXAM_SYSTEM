from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class User(AbstractUser):
    # Define constants for roles
    ICT = 'ICT'
    ACCOUNTS = 'ACCOUNTS'
    REGISTRAR = 'REGISTRAR'
    STUDENT = 'STUDENT'

    ROLE_CHOICES = [
        (ICT, 'ICT / Admin'),
        (ACCOUNTS, 'Accounts Office'),
        (REGISTRAR, 'Academic Registrar'),
        (STUDENT, 'Student'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=STUDENT
    )

    def __str__(self):
        return f"{self.username} - {self.role}"

class StudentProfile(models.Model):
    # Link to the User model
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # Academic Data
    student_id = models.CharField(max_length=20, unique=True)
    course = models.CharField(max_length=100)
    # fee_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # Approval logic
    is_approved = models.BooleanField(default=False)
    date_approved = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approvals_made'
    )

    def __str__(self):
        return f"{self.student_id} - {self.user.get_full_name}"