from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import AuditLog, Department, SystemSetting, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ['username']
    list_display = ['username', 'email', 'role', 'is_active', 'last_login']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'email']
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password', 'role')}),
        ('Access', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = ((None, {'classes': ('wide',),
                             'fields': ('username', 'email', 'role', 'password1', 'password2')}),)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['department_code', 'department_name']
    search_fields = ['department_code', 'department_name']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'ip_address']
    list_filter = ['action']
    search_fields = ['description', 'user__username']
    readonly_fields = ['timestamp', 'user', 'action', 'description', 'ip_address']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(SystemSetting)
