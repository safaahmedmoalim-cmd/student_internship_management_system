from django.contrib import admin

from .models import Announcement


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'target_audience', 'publication_date', 'expiry_date', 'administrator']
    list_filter = ['target_audience']
