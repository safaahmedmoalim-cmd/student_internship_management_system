from django.contrib import admin

from .models import AcademicSupervisor, IndustrialSupervisor, SupervisorAssignment


@admin.register(AcademicSupervisor)
class AcademicSupervisorAdmin(admin.ModelAdmin):
    list_display = ['staff_number', 'first_name', 'last_name', 'department', 'phone_number']
    search_fields = ['staff_number', 'first_name', 'last_name']
    list_filter = ['department']


@admin.register(IndustrialSupervisor)
class IndustrialSupervisorAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'organization', 'job_title', 'phone_number']
    search_fields = ['first_name', 'last_name', 'organization__organization_name']


@admin.register(SupervisorAssignment)
class SupervisorAssignmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'academic_supervisor', 'industrial_supervisor', 'assigned_date', 'assignment_status']
    list_filter = ['assignment_status']
