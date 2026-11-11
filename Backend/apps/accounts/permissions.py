"""Role-based access control (Chapter 8). Object-level scoping lives in apps.supervisors.access."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import Role


def has_role(*roles):
    labels = ', '.join(Role(r).label for r in roles)

    class _HasRole(BasePermission):
        message = f'Only these users can do this: {labels}.'

        def has_permission(self, request, view):
            u = request.user
            return bool(u and u.is_authenticated and u.role in roles)

    _HasRole.__name__ = 'Has' + ''.join(r.capitalize() for r in roles)
    return _HasRole


IsStudent = has_role(Role.STUDENT)
IsAcademicSupervisor = has_role(Role.ACADEMIC)
IsIndustrialSupervisor = has_role(Role.INDUSTRIAL)
IsAdministrator = has_role(Role.ADMIN)
IsSupervisor = has_role(Role.ACADEMIC, Role.INDUSTRIAL)
IsStaffRole = has_role(Role.ACADEMIC, Role.INDUSTRIAL, Role.ADMIN)


class IsAdministratorOrReadOnly(BasePermission):
    """Everyone signed in can read; only the administrator can write."""

    def has_permission(self, request, view):
        u = request.user
        if not (u and u.is_authenticated):
            return False
        return request.method in SAFE_METHODS or u.role == Role.ADMIN
