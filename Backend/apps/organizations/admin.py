from django.contrib import admin

from .models import Organization


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ['organization_name', 'county', 'contact_person', 'phone_number', 'status']
    list_filter = ['status', 'county', 'industry_category']
    search_fields = ['organization_name', 'contact_person', 'email']
