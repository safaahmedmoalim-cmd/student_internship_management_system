from django.db import transaction
from django.db.models import Count, Q
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.accounts.audit import log_action
from apps.accounts.models import Role
from apps.accounts.permissions import IsAdministrator
from apps.notifications.services import Type, notify

from .models import AcademicSupervisor, IndustrialSupervisor, SupervisorAssignment
from .serializers import AcademicBriefSerializer, IndustrialBriefSerializer, SupervisorAssignmentSerializer

ACTIVE = SupervisorAssignment.Status.ACTIVE


class AcademicSupervisorViewSet(viewsets.ReadOnlyModelViewSet):
    """/api/supervisors/academic/ ?department= - used by the administrator when assigning supervisors."""
    serializer_class = AcademicBriefSerializer
    permission_classes = [IsAdministrator]

    def get_queryset(self):
        qs = AcademicSupervisor.objects.filter(user__is_active=True).select_related('user', 'department').annotate(
            active_students=Count('assignments', filter=Q(assignments__assignment_status=ACTIVE)))
        if self.request.query_params.get('department'):
            qs = qs.filter(department_id=self.request.query_params['department'])
        return qs

    def list(self, request, *args, **kwargs):
        rows = self.get_queryset()
        data = self.get_serializer(rows, many=True).data
        for item, obj in zip(data, rows):
            item['active_students'] = obj.active_students
        return Response(data)


class IndustrialSupervisorViewSet(viewsets.ReadOnlyModelViewSet):
    """/api/supervisors/industrial/ ?organization= - supervisors at a host organization."""
    serializer_class = IndustrialBriefSerializer
    permission_classes = [IsAdministrator]

    def get_queryset(self):
        qs = IndustrialSupervisor.objects.filter(user__is_active=True).select_related('user', 'organization')
        if self.request.query_params.get('organization'):
            qs = qs.filter(organization_id=self.request.query_params['organization'])
        return qs


class SupervisorAssignmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                                  viewsets.GenericViewSet):
    """/api/assignments/ - module 4.4.

    POST (administrator) {placement, academic_supervisor, industrial_supervisor}. Assigning again to the same
    placement replaces the previous assignment (which becomes inactive). Everyone else sees only their own.
    """
    serializer_class = SupervisorAssignmentSerializer

    def get_permissions(self):
        if self.action in ('create', 'deactivate'):
            return [IsAdministrator()]
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        qs = SupervisorAssignment.objects.select_related(
            'student__user', 'student__department', 'placement__organization',
            'academic_supervisor__user', 'academic_supervisor__department',
            'industrial_supervisor__user', 'industrial_supervisor__organization')
        if user.role == Role.STUDENT:
            qs = qs.filter(student__user=user)
        elif user.role == Role.ACADEMIC:
            qs = qs.filter(academic_supervisor__user=user)
        elif user.role == Role.INDUSTRIAL:
            qs = qs.filter(industrial_supervisor__user=user)
        p = self.request.query_params
        if p.get('status') in SupervisorAssignment.Status.values:
            qs = qs.filter(assignment_status=p['status'])
        if p.get('placement'):
            qs = qs.filter(placement_id=p['placement'])
        return qs

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        placement = serializer.validated_data['placement']
        replaced = SupervisorAssignment.objects.filter(placement=placement, assignment_status=ACTIVE)
        replaced.update(assignment_status=SupervisorAssignment.Status.INACTIVE)
        a = serializer.save(assigned_by=request.user)
        student = a.student
        log_action(request, 'assignment.create',
                   f'Assigned {a.academic_supervisor} and {a.industrial_supervisor} to {student}.')
        notify(student.user, 'Supervisors assigned',
               f'Academic supervisor: {a.academic_supervisor.full_name}. '
               f'Industrial supervisor: {a.industrial_supervisor.full_name}.', Type.ASSIGNMENT, '/student')
        notify([a.academic_supervisor.user, a.industrial_supervisor.user], 'New student assigned',
               f'{student.full_name} ({student.registration_number}) at {placement.organization} has been '
               f'assigned to you.', Type.ASSIGNMENT)
        return Response(self.get_serializer(a).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        a = self.get_object()
        a.assignment_status = SupervisorAssignment.Status.INACTIVE
        a.save(update_fields=['assignment_status'])
        log_action(request, 'assignment.deactivate', f'Deactivated supervisor assignment #{a.pk} of {a.student}.')
        return Response(self.get_serializer(a).data)
