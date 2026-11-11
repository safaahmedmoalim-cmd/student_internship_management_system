from django.db.models import Q
from rest_framework import viewsets
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response

from apps.accounts.models import Role
from apps.reports import analytics
from apps.supervisors.access import visible_students


class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    """/api/students/ - assigned students (supervisors) or all students (administrator), with progress.
    GET /api/students/<id>/ adds the full progress record. Filters: ?search= ?department= ?placement_status="""

    def get_queryset(self):
        if self.request.user.role == Role.STUDENT:
            raise PermissionDenied('Students use /api/dashboard/ for their own record.')
        qs = visible_students(self.request.user)
        p = self.request.query_params
        if p.get('department'):
            qs = qs.filter(department_id=p['department'])
        if p.get('search'):
            s = p['search']
            qs = qs.filter(Q(first_name__icontains=s) | Q(last_name__icontains=s)
                           | Q(registration_number__icontains=s) | Q(user__email__icontains=s))
        return analytics.annotate_students(qs)

    def list(self, request, *args, **kwargs):
        rows = [analytics.student_row(s) for s in self.get_queryset()]
        status_filter = request.query_params.get('placement_status')
        if status_filter:
            rows = [r for r in rows if r['placement_status'] == status_filter]
        return Response(rows)

    def retrieve(self, request, *args, **kwargs):
        student = self.get_queryset().filter(pk=kwargs['pk']).first()
        if student is None:
            raise NotFound('Student not found or not assigned to you.')
        return Response({**analytics.student_row(student), 'progress': analytics.student_progress(student, request.user)})
