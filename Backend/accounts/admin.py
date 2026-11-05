from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm, UserChangeForm

from .models import User


class UserCreateForm(BaseUserCreationForm):
    """Django's default form is built around `username`; ours signs in with e-mail."""

    class Meta:
        model = User
        fields = ('email', 'name', 'role')


class UserEditForm(UserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = UserEditForm
    add_form = UserCreateForm
    ordering = ['name']
    list_display = ['name', 'email', 'role', 'adm_no', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['name', 'email', 'adm_no', 'staff_no', 'company']

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal', {'fields': ('name', 'phone', 'role')}),
        ('Student', {'fields': ('adm_no', 'course', 'year', 'academic_supervisor', 'industrial_supervisor')}),
        ('Staff', {'fields': ('staff_no', 'department')}),
        ('Industrial supervisor', {'fields': ('company', 'position', 'company_location')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'role', 'password1', 'password2'),
        }),
    )
