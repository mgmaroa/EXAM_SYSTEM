import pandas as pd
from django.core.management.base import BaseCommand
from users.models import User, StudentProfile

import random
import string

class Command(BaseCommand):
    help = 'Import students from Excel and create User and StudentProfile records'

    def add_arguments(self, parser):
        parser.add_argument('excel_file', type=str, help='Path to Excel file with student data')

    def handle(self, *args, **options):
        file_path = options['excel_file']

        # Load Excel using pandas
        try:
            df = pd.read_excel(file_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading Excel file: {e}"))
            return

        required_columns = ['student_id', 'full_name', 'course']
        for col in required_columns:
            if col not in df.columns:
                self.stderr.write(self.style.ERROR(f"Missing required column: {col}"))
                return

        created_count = 0
        skipped_count = 0

        for _, row in df.iterrows():
            student_id = str(row['student_id']).strip()
            full_name = str(row['full_name']).strip()
            course = str(row['course']).strip()

            # Check if User already exists
            if User.objects.filter(username=student_id).exists():
                self.stdout.write(self.style.WARNING(f"Skipping existing user: {student_id}"))
                skipped_count += 1
                continue

            # Generate a random password
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

            # Create the User
            user = User.objects.create_user(
                username=student_id,
                password=student_id, # To be chnaged later
                role=User.STUDENT,
                first_name=full_name.split(' ')[0],
                last_name=' '.join(full_name.split(' ')[1:]) if len(full_name.split(' ')) > 1 else ''
            )

            # Create the StudentProfile
            StudentProfile.objects.create(
                user=user,
                student_id=student_id,
                course=course,
                # fee_balance=0.00,
                # is_approved=True  # automatically approve eligible students
            )

            self.stdout.write(self.style.SUCCESS(f"Created student: {student_id} ({full_name})"))
            created_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Import finished. Created: {created_count}, Skipped: {skipped_count}"
        ))