"""Who may see which students - the single source of truth used by every module.

student     -> only their own record
academic    -> students with an active assignment to them
industrial  -> interns with an active assignment to them
admin       -> every student
"""
from apps.accounts.models import Role
from apps.students.models import Student

from .models import SupervisorAssignment

ACTIVE = SupervisorAssignment.Status.ACTIVE


def visible_students(user):
    qs = Student.objects.select_related('user', 'department')
    if not (user and user.is_authenticated):
        return qs.none()
    if user.role == Role.STUDENT:
        return qs.filter(user=user)
    if user.role == Role.ACADEMIC:
        return qs.filter(assignments__academic_supervisor__user=user, assignments__assignment_status=ACTIVE).distinct()
    if user.role == Role.INDUSTRIAL:
        return qs.filter(assignments__industrial_supervisor__user=user,
                         assignments__assignment_status=ACTIVE).distinct()
    if user.role == Role.ADMIN:
        return qs
    return qs.none()


def active_assignment(student):
    return (SupervisorAssignment.objects.filter(student=student, assignment_status=ACTIVE)
            .select_related('placement__organization', 'academic_supervisor__user', 'industrial_supervisor__user')
            .order_by('-assigned_date').first())


def supervisor_users(student):
    """(academic user, industrial user) currently supervising the student - either may be None."""
    a = active_assignment(student)
    if not a:
        return None, None
    return a.academic_supervisor.user, a.industrial_supervisor.user
