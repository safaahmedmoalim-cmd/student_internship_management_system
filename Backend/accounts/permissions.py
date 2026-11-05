from rest_framework.permissions import BasePermission

from .models import Role


def _role_permission(role, label):
    class _HasRole(BasePermission):
        message = f'Only a {label} can do this.'

        def has_permission(self, request, view):
            u = request.user
            return bool(u and u.is_authenticated and u.role == role)

    _HasRole.__name__ = f'Is{role.capitalize()}'
    return _HasRole


IsStudent = _role_permission(Role.STUDENT, 'student')
IsAcademicSupervisor = _role_permission(Role.ACADEMIC, 'academic supervisor')
IsIndustrialSupervisor = _role_permission(Role.INDUSTRIAL, 'industrial supervisor')
IsCoordinator = _role_permission(Role.COORDINATOR, 'coordinator')


class IsStaffRole(BasePermission):
    """Supervisors and the coordinator - everyone except students."""
    message = 'Students cannot access this.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.role != Role.STUDENT)
