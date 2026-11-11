from django.contrib import admin

from .models import Assessment


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'assessment_type', 'supervisor', 'marks', 'assessment_status', 'assessment_date']
    list_filter = ['assessment_type', 'assessment_status']
