from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.accounts.audit import log_action
from apps.accounts.models import Role
from apps.accounts.permissions import IsIndustrialSupervisor, IsSupervisor
from apps.common.files import file_download
from apps.notifications.services import Type, notify
from apps.placements.models import Placement
from apps.supervisors.access import active_assignment, visible_students

from .models import Attendance, Logbook, LogbookReview
from .serializers import (
    AttendanceBulkSerializer, AttendanceSerializer, LogbookSerializer, LogbookWriteSerializer,
    ReviewDecisionSerializer,
)

R = LogbookReview.Status


class LogbookViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """/api/logbooks/ - weekly logbook (module 4.5, workflow 5.4).

    Students create entries and correct rejected ones; each supervisor reviews independently via
    POST /logbooks/<id>/review/ {decision: approved|rejected, comments}. The administrator monitors.
    Filters: ?student= ?status= ?week= ?pending_my_review=true
    """
    serializer_class = LogbookSerializer

    def get_queryset(self):
        user = self.request.user
        qs = (Logbook.objects.filter(student__in=visible_students(user))
              .select_related('student__user', 'student__department')
              .prefetch_related('reviews__supervisor__academic_profile', 'reviews__supervisor__industrial_profile'))
        p = self.request.query_params
        if p.get('student'):
            qs = qs.filter(student_id=p['student'])
        if p.get('status') in Logbook.Status.values:
            qs = qs.filter(status=p['status'])
        if p.get('week'):
            qs = qs.filter(week_number=p['week'])
        if p.get('pending_my_review') == 'true' and user.role in (Role.ACADEMIC, Role.INDUSTRIAL):
            qs = qs.filter(reviews__supervisor_role=user.role, reviews__review_status=R.PENDING)
        return qs.order_by('-submission_date') if user.role != Role.STUDENT else qs.order_by('-week_number')

    def _current_placement_and_assignment(self):
        student = getattr(self.request.user, 'student_profile', None)
        if student is None:
            raise PermissionDenied('Only students submit logbooks.')
        placement = Placement.current_for(student)
        if placement is None:
            raise ValidationError({'detail': 'You can submit logbooks once your placement is approved.'})
        assignment = active_assignment(student)
        if assignment is None or assignment.placement_id != placement.pk:
            raise ValidationError({'detail': 'You can submit logbooks once your supervisors have been assigned.'})
        return student, placement, assignment

    def _sync_reviewers(self, logbook, assignment, reset):
        """Make sure there is one review row per current supervisor; `reset` puts them back to pending."""
        for role, sup in ((Role.ACADEMIC, assignment.academic_supervisor.user),
                          (Role.INDUSTRIAL, assignment.industrial_supervisor.user)):
            review, created = LogbookReview.objects.get_or_create(
                logbook=logbook, supervisor_role=role, defaults={'supervisor': sup})
            if not created and (reset or review.supervisor_id != sup.pk):
                review.supervisor = sup
                if reset:
                    review.review_status, review.review_date = R.PENDING, None
                review.save()
        logbook.refresh_status()

    @transaction.atomic
    def create(self, request):
        student, placement, assignment = self._current_placement_and_assignment()
        serializer = LogbookWriteSerializer(data=request.data, context={'placement': placement})
        serializer.is_valid(raise_exception=True)
        logbook = serializer.save(student=student, placement=placement, submission_date=timezone.now())
        self._sync_reviewers(logbook, assignment, reset=False)
        log_action(request, 'logbook.submit', f'{student} submitted logbook week {logbook.week_number}.')
        notify([assignment.academic_supervisor.user, assignment.industrial_supervisor.user],
               'New logbook submission', f'{student.full_name} submitted the logbook for week '
                                         f'{logbook.week_number}.', Type.LOGBOOK)
        return Response(LogbookSerializer(logbook).data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def update(self, request, pk=None, partial=False):
        """Correct and resubmit an entry. Allowed while nobody has reviewed it yet, or after a rejection."""
        logbook = self.get_object()
        if logbook.student.user_id != request.user.pk:
            raise PermissionDenied('You can only edit your own logbook.')
        if logbook.status not in (Logbook.Status.SUBMITTED, Logbook.Status.REJECTED):
            raise ValidationError({'detail': 'This entry is being reviewed or is approved and can no longer be edited.'})
        _, placement, assignment = self._current_placement_and_assignment()
        if placement.pk != logbook.placement_id:
            raise ValidationError({'detail': 'This entry belongs to an earlier placement.'})
        was_rejected = logbook.status == Logbook.Status.REJECTED
        serializer = LogbookWriteSerializer(logbook, data=request.data, partial=partial,
                                            context={'placement': placement})
        serializer.is_valid(raise_exception=True)
        logbook = serializer.save(submission_date=timezone.now())
        self._sync_reviewers(logbook, assignment, reset=True)
        logbook = Logbook.objects.get(pk=logbook.pk)
        log_action(request, 'logbook.resubmit', f'{logbook.student} updated logbook week {logbook.week_number}.')
        if was_rejected:
            notify([assignment.academic_supervisor.user, assignment.industrial_supervisor.user],
                   'Logbook resubmitted', f'{logbook.student.full_name} corrected and resubmitted week '
                                          f'{logbook.week_number}.', Type.LOGBOOK)
        return Response(LogbookSerializer(logbook).data)

    def partial_update(self, request, pk=None):
        return self.update(request, pk, partial=True)

    @action(detail=True, methods=['post'], permission_classes=[IsSupervisor])
    @transaction.atomic
    def review(self, request, pk=None):
        logbook = self.get_object()  # scoped: only the student's own supervisors reach this
        serializer = ReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if logbook.status == Logbook.Status.APPROVED:
            raise ValidationError({'detail': 'This entry has already been approved by both supervisors.'})
        review, _ = LogbookReview.objects.get_or_create(logbook=logbook, supervisor_role=request.user.role,
                                                        defaults={'supervisor': request.user})
        review.supervisor = request.user
        review.review_status = serializer.validated_data['decision']
        review.comments = serializer.validated_data['comments']
        review.review_date = timezone.now()
        review.save()
        logbook.refresh_status()
        log_action(request, f'logbook.{review.review_status}',
                   f'{request.user.get_role_display()} {review.review_status} week {logbook.week_number} '
                   f'of {logbook.student}.')
        verb = 'approved' if review.review_status == R.APPROVED else 'rejected'
        notify(logbook.student.user, f'Logbook week {logbook.week_number} {verb}',
               f'Your {review.get_supervisor_role_display().lower()} {verb} the entry.'
               + (f' Comments: {review.comments}' if review.comments else ''), Type.LOGBOOK, '/student/logbook')
        return Response(LogbookSerializer(Logbook.objects.get(pk=logbook.pk)).data)

    @action(detail=True, methods=['get'])
    def attachment(self, request, pk=None):
        return file_download(self.get_object().attachment)


class AttendanceViewSet(viewsets.ModelViewSet):
    """/api/attendance/ - recorded by the industrial supervisor; read by the student, academic supervisor
    and administrator. ?student= ?date= ?date_from= ?date_to=
    POST /attendance/bulk/ {attendance_date, records: [{student, attendance_status, remarks}]} records a day."""
    serializer_class = AttendanceSerializer

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy', 'bulk'):
            return [IsIndustrialSupervisor()]
        return super().get_permissions()

    def get_queryset(self):
        qs = Attendance.objects.filter(student__in=visible_students(self.request.user)).select_related(
            'student', 'recorded_by__industrial_profile')
        p = self.request.query_params
        if p.get('student'):
            qs = qs.filter(student_id=p['student'])
        if parse_date(p.get('date') or ''):
            qs = qs.filter(attendance_date=parse_date(p['date']))
        if parse_date(p.get('date_from') or ''):
            qs = qs.filter(attendance_date__gte=parse_date(p['date_from']))
        if parse_date(p.get('date_to') or ''):
            qs = qs.filter(attendance_date__lte=parse_date(p['date_to']))
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        if d['attendance_date'] > timezone.localdate():
            raise ValidationError({'attendance_date': 'Attendance cannot be recorded for a future date.'})
        obj, created = Attendance.objects.update_or_create(
            student=d['student'], attendance_date=d['attendance_date'],
            defaults={'attendance_status': d['attendance_status'], 'remarks': d.get('remarks', ''),
                      'recorded_by': request.user})
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def perform_update(self, serializer):
        serializer.save(recorded_by=self.request.user)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def bulk(self, request):
        serializer = AttendanceBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        day = serializer.validated_data['attendance_date']
        if day > timezone.localdate():
            raise ValidationError({'attendance_date': 'Attendance cannot be recorded for a future date.'})
        allowed = set(visible_students(request.user).values_list('pk', flat=True))
        saved = []
        for rec in serializer.validated_data['records']:
            if rec['student'] not in allowed:
                raise ValidationError({'records': f'Student #{rec["student"]} is not assigned to you.'})
            obj, _ = Attendance.objects.update_or_create(
                student_id=rec['student'], attendance_date=day,
                defaults={'attendance_status': rec['attendance_status'], 'remarks': rec['remarks'],
                          'recorded_by': request.user})
            saved.append(obj)
        log_action(request, 'attendance.record', f'Recorded attendance for {len(saved)} intern(s) on {day}.')
        return Response(self.get_serializer(saved, many=True).data)
