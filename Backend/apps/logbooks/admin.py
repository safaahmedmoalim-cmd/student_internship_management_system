from django.contrib import admin

from .models import Attendance, Logbook, LogbookReview


class LogbookReviewInline(admin.TabularInline):
    model = LogbookReview
    extra = 0


@admin.register(Logbook)
class LogbookAdmin(admin.ModelAdmin):
    list_display = ['student', 'week_number', 'start_date', 'end_date', 'status', 'submission_date']
    list_filter = ['status']
    search_fields = ['student__registration_number', 'student__first_name']
    inlines = [LogbookReviewInline]


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['student', 'attendance_date', 'attendance_status', 'recorded_by']
    list_filter = ['attendance_status']
