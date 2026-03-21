from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, StudentProfile
from django.utils.timezone import now

# Register your models here.
# Custom User admin
class CustomUserAdmin(UserAdmin):
    model = User

    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role',)}),
    )
    list_display = ['username', 'email', 'role', 'is_staff']

# Custom StudentProfle admin
@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'get_name', 'course', 'fee_balance', 'is_approved', 'approved_by']
    search_fields = ['student_id', 'user__first_name', 'user__last_name']
    list_filter = ['is_approved', 'course']
    readonly_fields = ['date_approved']

    def get_name(self, obj):
        return obj.user.get_full_name()
    get_name.short_description = 'Student Name'

    def save_model(self, request, obj, form, change):
        # Automaticall set approval info
        if obj.is_approved and not obj.approved_by:
            obj.approved_by = request.user
        if obj.is_approved and not obj.date_approved:
            obj.date_approved = now()
        return super().save_model(request, obj, form, change)

admin.site.register(User, CustomUserAdmin)