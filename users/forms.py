from django import forms
from django.core.validators import FileExtensionValidator
from .models import StudentProfile

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB

# Form for searching student details
class StudentSearchForm(forms.Form):
    student_id = forms.CharField(
        label='Enter Student ID',
        max_length=20,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control'
            }
        )
    )

# Form for updating Student data
class FeeUpdateForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['fee_balance'] # only allow editing this

        widgets = {
            'fee_balance': forms.NumberInput(attrs={
                'class': 'form-control'
            })
        }

# Form for uploading Excel file of students
class StudentImportForm(forms.Form):
    excel_file = forms.FileField(
        label="Excel file",
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls'])],
        help_text="Required columns: student_id, full_name, course. Max size 5MB.",
    )

    def clean_excel_file(self):
        f = self.cleaned_data['excel_file']
        if f.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError("File is too large. Maximum size is 5MB.")
        return f
