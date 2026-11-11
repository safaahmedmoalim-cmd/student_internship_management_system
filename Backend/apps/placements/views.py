from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.audit import log_action
from apps.accounts.models import Role
from apps.accounts.permissions import IsAdministrator, IsAdministratorOrReadOnly, IsStudent
from apps.common.files import file_download
from apps.notifications.services import Type, notify, notify_admins
from apps.supervisors.access import visible_students
from apps.supervisors.models import SupervisorAssignment

from .models import AttachmentPeriod, Placement
from .serializers import (
    AttachmentPeriodSerializer, AttachmentStatusSerializer, DecisionSerializer, PlacementApplicationSerializer,
    PlacementSerializer, RequiredReasonSerializer, WithdrawSerializer,
)

S = Placement.Status
A = Placement.AttachmentStatus

# Allowed administrative changes to the attachment status of an approved placement.
ATTACHMENT_TRANSITIONS = {
    A.NOT_STARTED: {A.ACTIVE, A.TERMINATED},
    A.ACTIVE: {A.COMPLETED, A.TERMINATED},
    A.COMPLETED: {A.ACTIVE},     # re-open if confirmed by mistake
    A.TERMINATED: {A.ACTIVE},
}


class AttachmentPeriodViewSet(viewsets.ModelViewSet):
    """/api/attachment-periods/ - attachment periods and deadlines (administrator manages)."""
    serializer_class = AttachmentPeriodSerializer
    permission_classes = [IsAdministratorOrReadOnly]

    def get_queryset(self):
        qs = AttachmentPeriod.objects.all()
        if self.request.user.role != Role.ADMIN or self.request.query_params.get('active') == 'true':
            qs = qs.filter(is_active=True)
        return qs

    def perform_create(self, serializer):
        p = serializer.save()
        log_action(self.request, 'period.create', f'Created attachment period "{p}".')

    def perform_update(self, serializer):
        p = serializer.save()
        log_action(self.request, 'period.update', f'Updated attachment period "{p}".')


class PlacementViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """/api/placements/ - placement applications (module 4.2, workflow 5.2).

    Students: create, correct/resubmit (PUT), withdraw. Administrator: approve, reject, return,
    set attachment status. Supervisors: read placements of their assigned students.
    Filters: ?status= ?attachment_status= ?organization= ?search= ?unassigned=true
    """
    serializer_class = PlacementSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Placement.objects.select_related('student__user', 'student__department', 'organization',
                                              'attachment_period', 'reviewed_by')
        if user.role == Role.STUDENT:
            qs = qs.filter(student__user=user)
        elif user.role in (Role.ACADEMIC, Role.INDUSTRIAL):
            qs = qs.filter(assignments__in=SupervisorAssignment.objects.filter(
                assignment_status=SupervisorAssignment.Status.ACTIVE,
                **({'academic_supervisor__user': user} if user.role == Role.ACADEMIC
                   else {'industrial_supervisor__user': user}))).distinct()
        p = self.request.query_params
        if p.get('status') in S.values:
            qs = qs.filter(application_status=p['status'])
        if p.get('attachment_status') in A.values:
            qs = qs.filter(attachment_status=p['attachment_status'])
        if p.get('organization'):
            qs = qs.filter(organization_id=p['organization'])
        if p.get('unassigned') == 'true':
            qs = qs.filter(application_status=S.APPROVED).exclude(
                assignments__assignment_status=SupervisorAssignment.Status.ACTIVE)
        if p.get('search'):
            s = p['search']
            qs = qs.filter(Q(student__first_name__icontains=s) | Q(student__last_name__icontains=s)
                           | Q(student__registration_number__icontains=s)
                           | Q(organization__organization_name__icontains=s))
        return qs

    def _student(self):
        profile = getattr(self.request.user, 'student_profile', None)
        if profile is None:
            raise PermissionDenied('Only students can do this.')
        return profile

    # --- Student actions -------------------------------------------------------
    @transaction.atomic
    def create(self, request):
        if request.user.role != Role.STUDENT:
            raise PermissionDenied('Only students submit placement applications.')
        student = self._student()
        if Placement.objects.filter(student=student, application_status__in=Placement.OPEN_STATUSES).exists():
            raise ValidationError({'detail': 'You already have an application awaiting a decision or correction.'})
        if Placement.current_for(student):
            raise ValidationError({'detail': 'You already have an approved placement in progress.'})
        serializer = PlacementApplicationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        placement = serializer.save_for(student)
        log_action(request, 'placement.submit', f'{student} applied for placement at {placement.organization}.')
        notify_admins('New placement application',
                      f'{student.full_name} ({student.registration_number}) submitted a placement at '
                      f'{placement.organization}.', Type.PLACEMENT, '/admin/placements')
        return Response(PlacementSerializer(placement).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, pk=None):
        """Correct and resubmit an application that is pending or was returned for correction."""
        placement = self.get_object()
        if placement.student.user_id != request.user.pk:
            raise PermissionDenied('You can only edit your own application.')
        if placement.application_status not in Placement.OPEN_STATUSES:
            raise ValidationError({'detail': 'Only pending or returned applications can be changed.'})
        was_returned = placement.application_status == S.RETURNED
        serializer = PlacementApplicationSerializer(placement, data=request.data)
        serializer.is_valid(raise_exception=True)
        placement = serializer.save_for(placement.student, instance=placement)
        log_action(request, 'placement.resubmit', f'{placement.student} updated placement #{placement.pk}.')
        if was_returned:
            notify_admins('Placement resubmitted',
                          f'{placement.student.full_name} corrected and resubmitted their placement application.',
                          Type.PLACEMENT, '/admin/placements')
        return Response(PlacementSerializer(placement).data)

    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    def withdraw(self, request, pk=None):
        placement = self.get_object()
        if placement.application_status not in Placement.OPEN_STATUSES:
            raise ValidationError({'detail': 'Only pending or returned applications can be withdrawn.'})
        serializer = WithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        placement.application_status = S.WITHDRAWN
        placement.withdrawal_reason = serializer.validated_data['reason']
        placement.save(update_fields=['application_status', 'withdrawal_reason', 'updated_at'])
        log_action(request, 'placement.withdraw', f'{placement.student} withdrew placement #{placement.pk}.')
        notify_admins('Placement withdrawn', f'{placement.student.full_name} withdrew their application: '
                                             f'{placement.withdrawal_reason}', Type.PLACEMENT, '/admin/placements')
        return Response(PlacementSerializer(placement).data)

    # --- Administrator decisions --------------------------------------------
    def _decide(self, request, new_status, serializer_class, title, verb):
        placement = self.get_object()
        if placement.application_status != S.PENDING:
            raise ValidationError({'detail': f'Only pending applications can be {verb}.'})
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        if new_status == S.APPROVED and Placement.current_for(placement.student):
            raise ValidationError({'detail': 'This student already has an approved placement in progress.'})
        placement.application_status = new_status
        placement.approval_comments = serializer.validated_data.get('comments', '')
        placement.reviewed_by = request.user
        placement.reviewed_at = timezone.now()
        if new_status == S.APPROVED and placement.organization.status == placement.organization.Status.PENDING:
            placement.organization.status = placement.organization.Status.ACTIVE  # verified by the approval
            placement.organization.save(update_fields=['status'])
        placement.save()
        log_action(request, f'placement.{new_status}', f'Placement #{placement.pk} of {placement.student} {verb}.')
        message = f'Your placement application at {placement.organization} was {verb}.'
        if placement.approval_comments:
            message += f' Comments: {placement.approval_comments}'
        notify(placement.student.user, title, message, Type.PLACEMENT, '/student/placement')
        return Response(PlacementSerializer(placement).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAdministrator])
    def approve(self, request, pk=None):
        return self._decide(request, S.APPROVED, DecisionSerializer, 'Placement approved', 'approved')

    @action(detail=True, methods=['post'], permission_classes=[IsAdministrator])
    def reject(self, request, pk=None):
        return self._decide(request, S.REJECTED, RequiredReasonSerializer, 'Placement rejected', 'rejected')

    @action(detail=True, methods=['post'], permission_classes=[IsAdministrator], url_path='return')
    def return_for_correction(self, request, pk=None):
        return self._decide(request, S.RETURNED, RequiredReasonSerializer, 'Placement returned for correction',
                            'returned for correction')

    @action(detail=True, methods=['post'], permission_classes=[IsAdministrator], url_path='attachment-status')
    def attachment_status(self, request, pk=None):
        """Start, complete (workflow 5.8) or terminate an approved attachment."""
        placement = self.get_object()
        if placement.application_status != S.APPROVED:
            raise ValidationError({'detail': 'Only approved placements have an attachment status.'})
        serializer = AttachmentStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new = serializer.validated_data['attachment_status']
        if new not in ATTACHMENT_TRANSITIONS[placement.attachment_status]:
            raise ValidationError({'attachment_status': f'Cannot change from '
                                   f'{placement.get_attachment_status_display()} to {A(new).label}.'})
        placement.attachment_status = new
        placement.save(update_fields=['attachment_status', 'updated_at'])
        log_action(request, 'placement.attachment_status',
                   f'Attachment of {placement.student} set to {placement.get_attachment_status_display()}.')
        recipients = [placement.student.user]
        a = placement.active_assignment()
        if a:
            recipients += [a.academic_supervisor.user, a.industrial_supervisor.user]
        notify(recipients, 'Attachment status updated',
               f'The attachment of {placement.student.full_name} at {placement.organization} is now '
               f'{placement.get_attachment_status_display()}.', Type.PLACEMENT)
        return Response(PlacementSerializer(placement).data)

    @action(detail=True, methods=['get'])
    def document(self, request, pk=None):
        placement = self.get_object()  # scoped by get_queryset, so only authorised users get here
        return file_download(placement.supporting_document)

    def get_object(self):
        obj = super().get_object()
        if self.request.user.role in (Role.ACADEMIC, Role.INDUSTRIAL) and \
                not visible_students(self.request.user).filter(pk=obj.student_id).exists():
            raise PermissionDenied()
        return obj
