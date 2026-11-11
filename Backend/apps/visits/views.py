from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.audit import log_action
from apps.accounts.models import Role
from apps.notifications.services import Type, notify
from apps.placements.models import Placement
from apps.supervisors.access import active_assignment, visible_students

from .models import SupervisionVisit
from .serializers import CancelSerializer, RescheduleSerializer, SupervisionVisitSerializer, VisitReportSerializer

V = SupervisionVisit.Status
CAN_MANAGE = (Role.ACADEMIC, Role.ADMIN)


def _when(dt):
    return f'{timezone.localtime(dt):%d %b %Y, %H:%M}'


class SupervisionVisitViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                              viewsets.GenericViewSet):
    """/api/visits/ - supervision visits (module 4.6, workflow 5.5).

    Academic supervisors (and the administrator) schedule, reschedule, cancel and complete visits;
    students and industrial supervisors see the visits of their own placements.
    Filters: ?student= ?status= ?upcoming=true
    """
    serializer_class = SupervisionVisitSerializer

    def get_queryset(self):
        user = self.request.user
        qs = SupervisionVisit.objects.filter(student__in=visible_students(user)).select_related(
            'student__user', 'student__department', 'academic_supervisor__user', 'organization')
        if user.role == Role.ACADEMIC:
            qs = qs.filter(academic_supervisor__user=user)
        p = self.request.query_params
        if p.get('student'):
            qs = qs.filter(student_id=p['student'])
        if p.get('status') in V.values:
            qs = qs.filter(visit_status=p['status'])
        if p.get('upcoming') == 'true':
            qs = qs.filter(visit_status__in=SupervisionVisit.UPCOMING_STATUSES,
                           visit_date__gte=timezone.now()).order_by('visit_date')
        return qs

    def _require_manager(self):
        if self.request.user.role not in CAN_MANAGE:
            raise PermissionDenied('Only academic supervisors and the administrator manage visits.')

    def _recipients(self, visit):
        users = [visit.student.user, visit.academic_supervisor.user]
        a = active_assignment(visit.student)
        if a:
            users.append(a.industrial_supervisor.user)
        return [u for u in users if u.pk != self.request.user.pk]

    def create(self, request, *args, **kwargs):
        self._require_manager()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student = serializer.validated_data['student']
        assignment = active_assignment(student)
        if assignment is None:
            raise ValidationError({'student': 'This student has no supervisors assigned yet.'})
        if request.user.role == Role.ACADEMIC:
            academic = request.user.academic_profile
        else:
            academic = serializer.validated_data.get('academic_supervisor') or assignment.academic_supervisor
        placement = Placement.current_for(student)
        visit = serializer.save(academic_supervisor=academic, created_by=request.user,
                                organization=placement.organization if placement else None)
        log_action(request, 'visit.schedule', f'Scheduled a {visit.visit_type} visit to {student} on {_when(visit.visit_date)}.')
        notify(self._recipients(visit), 'Supervision visit scheduled',
               f'A {visit.get_visit_type_display().lower()} supervision visit for {student.full_name} is '
               f'scheduled for {_when(visit.visit_date)}.', Type.VISIT)
        return Response(self.get_serializer(visit).data, status=status.HTTP_201_CREATED)

    def _upcoming_visit(self):
        self._require_manager()
        visit = self.get_object()
        if visit.visit_status not in SupervisionVisit.UPCOMING_STATUSES:
            raise ValidationError({'detail': f'This visit is already {visit.get_visit_status_display().lower()}.'})
        return visit

    @action(detail=True, methods=['post'])
    def reschedule(self, request, pk=None):
        visit = self._upcoming_visit()
        serializer = RescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit.visit_date = serializer.validated_data['visit_date']
        visit.visit_status = V.RESCHEDULED
        visit.save()
        log_action(request, 'visit.reschedule', f'Rescheduled visit #{visit.pk} to {_when(visit.visit_date)}.')
        reason = serializer.validated_data['reason']
        notify(self._recipients(visit), 'Supervision visit rescheduled',
               f'The visit for {visit.student.full_name} moved to {_when(visit.visit_date)}.'
               + (f' Reason: {reason}' if reason else ''), Type.VISIT)
        return Response(self.get_serializer(visit).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        visit = self._upcoming_visit()
        serializer = CancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit.visit_status = V.CANCELLED
        visit.save()
        log_action(request, 'visit.cancel', f'Cancelled visit #{visit.pk}.')
        reason = serializer.validated_data['reason']
        notify(self._recipients(visit), 'Supervision visit cancelled',
               f'The visit for {visit.student.full_name} was cancelled.' + (f' Reason: {reason}' if reason else ''),
               Type.VISIT)
        return Response(self.get_serializer(visit).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Record the visit report: observations and recommendations (workflow 5.5 steps 6-7)."""
        visit = self._upcoming_visit()
        if visit.visit_date > timezone.now():
            raise ValidationError({'detail': 'A visit can only be recorded after it has taken place.'})
        serializer = VisitReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        visit.observations = serializer.validated_data['observations']
        visit.recommendations = serializer.validated_data['recommendations']
        visit.visit_status = V.COMPLETED
        visit.save()
        log_action(request, 'visit.complete', f'Recorded visit report for {visit.student}.')
        notify(visit.student.user, 'Visit report recorded',
               'Your academic supervisor recorded the report of your supervision visit.', Type.VISIT, '/student')
        return Response(self.get_serializer(visit).data)
