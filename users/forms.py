from django import forms

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