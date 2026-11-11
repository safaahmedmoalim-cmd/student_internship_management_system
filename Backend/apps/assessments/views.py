from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.audit import log_action
from apps.accounts.models import Role
from apps.accounts.permissions import IsAdministrator, IsSupervisor
from apps.common.files import file_download
from apps.notifications.services import Type, notify, notify_admins
from apps.supervisors.access import active_assignment, visible_students

from .models import ACADEMIC_CRITERIA, MAX_SCORE, WORKPLACE_CRITERIA, Assessment
from .serializers import AssessmentSerializer, AssessmentWriteSerializer

St = Assessment.Status


class AssessmentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """/api/assessments/ - module 4.7, workflow 5.6.

    Academic supervisors record the academic assessment, industrial supervisors the workplace
    assessment (one of each per placement). Students only see released assessments; supervisors see
    their own plus released ones for their students; the administrator sees everything and releases.
    Filters: ?student= ?status= ?type=
    """
    serializer_class = AssessmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Assessment.objects.filter(student__in=visible_students(user)).select_related(
            'student__user', 'student__department', 'supervisor__academic_profile', 'supervisor__industrial_profile')
        if user.role == Role.STUDENT:
            qs = qs.filter(assessment_status=St.RELEASED)
        elif user.role in (Role.ACADEMIC, Role.INDUSTRIAL):
            qs = qs.filter(Q(supervisor=user) | Q(assessment_status=St.RELEASED))
        p = self.request.query_params
        if p.get('student'):
            qs = qs.filter(student_id=p['student'])
        if p.get('status') in St.values:
            qs = qs.filter(assessment_status=p['status'])
        if p.get('type') in Assessment.AssessmentType.values:
            qs = qs.filter(assessment_type=p['type'])
        return qs

    @action(detail=False, methods=['get'], permission_classes=[])
    def criteria(self, request):
        return Response({'max_score': MAX_SCORE, 'academic': ACADEMIC_CRITERIA, 'workplace': WORKPLACE_CRITERIA})

    def _after_save(self, request, assessment, submitted, verb):
        log_action(request, f'assessment.{verb}', f'{request.user.get_role_display()} {verb} the '
                   f'{assessment.get_assessment_type_display().lower()} of {assessment.student} ({assessment.marks}%).')
        if submitted:
            notify_admins('Assessment completed',
                          f'{assessment.get_assessment_type_display()} for {assessment.student.full_name} was '
                          f'submitted by {request.user.full_name}.', Type.ASSESSMENT, '/admin/assessments')

    @transaction.atomic
    def create(self, request):
        if request.user.role not in (Role.ACADEMIC, Role.INDUSTRIAL):
            raise PermissionDenied('Only supervisors assess students.')
        serializer = AssessmentWriteSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        assignment = active_assignment(d['student'])
        if assignment is None:
            raise ValidationError({'student': 'This student has no active supervisor assignment.'})
        if Assessment.objects.filter(placement=assignment.placement, assessment_type=d['assessment_type']).exists():
            raise ValidationError({'detail': 'This assessment already exists - open it to edit the draft.'})
        assessment = Assessment.objects.create(
            student=d['student'], placement=assignment.placement, supervisor=request.user,
            supervisor_role=request.user.role, assessment_type=d['assessment_type'],
            assessment_criteria=d['assessment_criteria'], marks=d['marks'], comments=d['comments'],
            recommendations=d['recommendations'], evaluation_form=d.get('evaluation_form') or '',
            assessment_status=St.COMPLETED if d['submit'] else St.IN_PROGRESS,
        )
        self._after_save(request, assessment, d['submit'], 'submitted' if d['submit'] else 'saved')
        return Response(AssessmentSerializer(assessment).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, pk=None):
        assessment = self.get_object()
        if assessment.supervisor_id != request.user.pk:
            raise PermissionDenied('You can only edit your own assessments.')
        if assessment.assessment_status != St.IN_PROGRESS:
            raise ValidationError({'detail': 'Submitted assessments are locked. Ask the administrator to re-open it.'})
        serializer = AssessmentWriteSerializer(assessment, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        for f in ('assessment_criteria', 'marks', 'comments', 'recommendations'):
            setattr(assessment, f, d[f])
        if d.get('evaluation_form'):
            assessment.evaluation_form = d['evaluation_form']
        if d['submit']:
            assessment.assessment_status = St.COMPLETED
        assessment.save()
        self._after_save(request, assessment, d['submit'], 'submitted' if d['submit'] else 'updated')
        return Response(AssessmentSerializer(assessment).data)

    def get_permissions(self):
        if self.action in ('update',):
            return [IsSupervisor()]
        if self.action in ('release', 'reopen'):
            return [IsAdministrator()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def release(self, request, pk=None):
        """Release marks and feedback to the student (workflow 5.6 step 6)."""
        assessment = self.get_object()
        if assessment.assessment_status != St.COMPLETED:
            raise ValidationError({'detail': 'Only completed assessments can be released.'})
        assessment.assessment_status = St.RELEASED
        assessment.released_by = request.user
        assessment.released_at = timezone.now()
        assessment.save()
        log_action(request, 'assessment.release', f'Released {assessment.get_assessment_type_display()} '
                                                  f'of {assessment.student}.')
        notify(assessment.student.user, 'Assessment results released',
               f'Your {assessment.get_assessment_type_display().lower()} results are now available.',
               Type.ASSESSMENT, '/student/assessments')
        return Response(AssessmentSerializer(assessment).data)

    @action(detail=True, methods=['post'])
    def reopen(self, request, pk=None):
        """Send a completed (not yet released) assessment back to the supervisor for changes."""
        assessment = self.get_object()
        if assessment.assessment_status != St.COMPLETED:
            raise ValidationError({'detail': 'Only completed, unreleased assessments can be re-opened.'})
        assessment.assessment_status = St.IN_PROGRESS
        assessment.save()
        log_action(request, 'assessment.reopen', f'Re-opened assessment #{assessment.pk} of {assessment.student}.')
        notify(assessment.supervisor, 'Assessment re-opened',
               f'The administrator re-opened your assessment of {assessment.student.full_name} for changes.',
               Type.ASSESSMENT)
        return Response(AssessmentSerializer(assessment).data)

    @action(detail=True, methods=['get'], url_path='evaluation-form')
    def evaluation_form(self, request, pk=None):
        return file_download(self.get_object().evaluation_form)
