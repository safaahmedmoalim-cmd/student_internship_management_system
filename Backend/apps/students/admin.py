from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['registration_number', 'first_name', 'last_name', 'department', 'academic_year']
    search_fields = ['registration_number', 'first_name', 'last_name', 'user__email']
    list_filter = ['department', 'academic_year']
