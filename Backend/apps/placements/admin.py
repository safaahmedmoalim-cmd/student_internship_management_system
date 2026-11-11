from django.contrib import admin

from .models import AttachmentPeriod, Placement


@admin.register(Placement)
class PlacementAdmin(admin.ModelAdmin):
    list_display = ['student', 'organization', 'start_date', 'end_date', 'application_status', 'attachment_status']
    list_filter = ['application_status', 'attachment_status', 'attachment_period']
    search_fields = ['student__registration_number', 'student__first_name', 'organization__organization_name']


@admin.register(AttachmentPeriod)
class AttachmentPeriodAdmin(admin.ModelAdmin):
    list_display = ['name', 'start_date', 'end_date', 'application_deadline', 'report_deadline', 'is_active']
