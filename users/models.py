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
