from django import forms
from .models import StudentProfile

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