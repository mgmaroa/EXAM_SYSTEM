"""
Shared logic for importing students from an Excel file.

Used by both:
  - the `import_students` management command (CLI)
  - the ICT "Upload Students" view (web)

Keeping this in one place means the two entry points can never drift apart —
fix a bug here and both are fixed.
"""
from dataclasses import dataclass, field
from typing import BinaryIO, List, Dict

import pandas as pd
from django.db import transaction

from .models import User, StudentProfile

REQUIRED_COLUMNS = ['student_id', 'full_name', 'course']
MAX_ROWS = 5000  # sanity cap for a single upload; split larger batches


class StudentImportError(Exception):
    """Raised for file-level problems (unreadable file, missing columns, too many rows)
    that stop processing before any row is looked at."""
    pass


@dataclass
class ImportResult:
    created: List[Dict] = field(default_factory=list)
    skipped: List[Dict] = field(default_factory=list)
    total_rows: int = 0

    @property
    def created_count(self) -> int:
        return len(self.created)

    @property
    def skipped_count(self) -> int:
        return len(self.skipped)


def import_students_from_excel(file_obj: BinaryIO) -> ImportResult:
    """
    Parses an uploaded Excel file (path, open file handle, or Django
    UploadedFile — anything pandas.read_excel accepts) and creates a
    User + StudentProfile for each valid, non-duplicate row.

    Raises StudentImportError for file-level problems.
    Row-level problems (missing fields, duplicate student_id, etc.) are
    collected in ImportResult.skipped instead of raising, so one bad row
    doesn't stop the rest of the batch.
    """
    try:
        df = pd.read_excel(file_obj)
    except Exception as exc:
        raise StudentImportError(f"Could not read the Excel file: {exc}")

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise StudentImportError(
            f"Missing required column(s): {', '.join(missing_columns)}. "
            f"Expected columns: {', '.join(REQUIRED_COLUMNS)}."
        )

    if len(df) == 0:
        raise StudentImportError("The file has no data rows.")

    if len(df) > MAX_ROWS:
        raise StudentImportError(
            f"File has {len(df)} rows, which exceeds the {MAX_ROWS}-row limit per upload. "
            f"Split it into smaller batches."
        )

    result = ImportResult(total_rows=len(df))

    for idx, row in df.iterrows():
        excel_row_number = idx + 2  # +1 for zero-index, +1 for the header row

        raw_student_id = row.get('student_id')
        raw_full_name = row.get('full_name')
        raw_course = row.get('course')

        student_id = '' if pd.isna(raw_student_id) else str(raw_student_id).strip()
        full_name = '' if pd.isna(raw_full_name) else str(raw_full_name).strip()
        course = '' if pd.isna(raw_course) else str(raw_course).strip()

        if not student_id or not full_name or not course:
            result.skipped.append({
                'row': excel_row_number,
                'student_id': student_id,
                'full_name': full_name,
                'course': course,
                'reason': 'Missing student_id, full_name, or course',
            })
            continue

        if User.objects.filter(username=student_id).exists():
            result.skipped.append({
                'row': excel_row_number,
                'student_id': student_id,
                'full_name': full_name,
                'course': course,
                'reason': 'Student ID already exists',
            })
            continue

        name_parts = full_name.split(' ')
        first_name = name_parts[0]
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        try:
            # Wrapped so a failure creating StudentProfile can't leave a
            # dangling User with no profile behind it.
            with transaction.atomic():
                user = User.objects.create_user(
                    username=student_id,
                    password=student_id,  # initial password == student_id, as in the original script
                    role=User.STUDENT,
                    first_name=first_name,
                    last_name=last_name,
                )
                StudentProfile.objects.create(
                    user=user,
                    student_id=student_id,
                    course=course,
                )
        except Exception as exc:
            result.skipped.append({
                'row': excel_row_number,
                'student_id': student_id,
                'full_name': full_name,
                'course': course,
                'reason': f'Error creating record: {exc}',
            })
            continue

        result.created.append({
            'row': excel_row_number,
            'student_id': student_id,
            'full_name': full_name,
            'course': course,
        })

    return result