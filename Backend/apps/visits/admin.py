from django.contrib import admin

from .models import SupervisionVisit


@admin.register(SupervisionVisit)
class SupervisionVisitAdmin(admin.ModelAdmin):
    list_display = ['student', 'academic_supervisor', 'visit_date', 'visit_type', 'visit_status']
    list_filter = ['visit_status', 'visit_type']
