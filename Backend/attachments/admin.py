from django.contrib import admin

from .models import Announcement, Assessment, FinalReport, LogbookEntry, Placement, Visit


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ['student', 'company', 'department', 'start_date', 'end_date', 'status']
    list_filter = ['status', 'start_date']
    search_fields = ['student__name', 'student__adm_no', 'company']
    raw_id_fields = ['student', 'industrial_supervisor', 'decided_by']


@admin.register(LogbookEntry)
class LogbookEntryAdmin(admin.ModelAdmin):
    list_display = ['student', 'week_no', 'week_start', 'hours_worked', 'status']
    list_filter = ['status']
    search_fields = ['student__name', 'student__adm_no']
    raw_id_fields = ['student']


@admin.register(FinalReport)
class FinalReportAdmin(admin.ModelAdmin):
    list_display = ['student', 'title', 'original_name', 'size', 'status', 'submitted_at']
    list_filter = ['status']
    search_fields = ['student__name', 'title']
    raw_id_fields = ['student', 'reviewed_by']


@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ['student', 'academic', 'visit_date', 'mode', 'status']
    list_filter = ['status', 'mode']
    search_fields = ['student__name', 'academic__name']
    raw_id_fields = ['student', 'academic']


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'assessment_type', 'assessor', 'assessor_role', 'marks', 'created_at']
    list_filter = ['assessor_role', 'assessment_type']
    search_fields = ['student__name', 'assessor__name']
    raw_id_fields = ['student', 'assessor']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'created_at']
    search_fields = ['title', 'body']
    raw_id_fields = ['author']
