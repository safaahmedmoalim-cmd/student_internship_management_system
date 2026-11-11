from django.contrib import admin

from .models import FinalReport


@admin.register(FinalReport)
class FinalReportAdmin(admin.ModelAdmin):
    list_display = ['student', 'version', 'title', 'review_status', 'submission_date']
    list_filter = ['review_status']
