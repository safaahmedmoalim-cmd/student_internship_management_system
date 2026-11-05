"""Who may see which students - the single source of truth for every endpoint."""
import math

from django.db.models import Avg, FloatField, IntegerField, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce

from accounts.models import Role, User

from .models import ApprovalStatus, Assessment, FinalReport, LogbookEntry, Placement


def visible_students(user):
    """Students this user is allowed to see.

    student      -> only themselves
    academic     -> students assigned to them
    industrial   -> students (interns) assigned to them
    coordinator  -> every student
    """
    qs = User.objects.filter(role=Role.STUDENT, is_active=True)
    if user.role == Role.STUDENT:
        return qs.filter(pk=user.pk)
    if user.role == Role.ACADEMIC:
        return qs.filter(academic_supervisor=user)
    if user.role == Role.INDUSTRIAL:
        return qs.filter(industrial_supervisor=user)
    return qs


def js_round(x):
    """Round half up (the frontend uses Math.round); Python's round() rounds half to even."""
    return None if x is None else int(math.floor(x + 0.5))


def students_with_summary(qs):
    """Annotate a student queryset with hours, placement/report status and average marks."""
    def hours(**flt):
        return (LogbookEntry.objects.filter(student=OuterRef('pk'), **flt).order_by()
                .values('student').annotate(t=Sum('hours_worked')).values('t'))

    def avg_marks(role):
        return (Assessment.objects.filter(student=OuterRef('pk'), assessor_role=role).order_by()
                .values('student').annotate(a=Avg('marks')).values('a'))

    return qs.select_related('academic_supervisor', 'industrial_supervisor').annotate(
        approved_hours=Coalesce(Subquery(hours(status=ApprovalStatus.APPROVED), output_field=IntegerField()), 0),
        logged_hours=Coalesce(Subquery(hours(), output_field=IntegerField()), 0),
        placement_status=Subquery(Placement.objects.filter(student=OuterRef('pk')).values('status')[:1]),
        placement_company=Subquery(Placement.objects.filter(student=OuterRef('pk')).values('company')[:1]),
        report_status=Subquery(FinalReport.objects.filter(student=OuterRef('pk')).values('status')[:1]),
        academic_avg=Subquery(avg_marks(Role.ACADEMIC), output_field=FloatField()),
        industrial_avg=Subquery(avg_marks(Role.INDUSTRIAL), output_field=FloatField()),
    )
