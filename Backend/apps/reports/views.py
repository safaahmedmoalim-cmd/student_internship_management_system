from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.urls import reverse
from django.utils import timezone
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import log_action
from apps.accounts.models import Role
from apps.accounts.permissions import IsAcademicSupervisor, IsStudent
from apps.announcements.models import Announcement
from apps.assessments.models import ACADEMIC_CRITERIA, MAX_SCORE, WORKPLACE_CRITERIA, Assessment
from apps.common.files import file_download
from apps.common.validators import ATTACHMENT_EXTENSIONS, DOCUMENT_EXTENSIONS
from apps.logbooks.models import Attendance, Logbook, LogbookReview
from apps.notifications.services import Type, notify
from apps.organizations.models import Organization
from apps.placements.models import Placement
from apps.students.models import Student
from apps.students.serializers import StudentBriefSerializer
from apps.supervisors.access import active_assignment, visible_students
from apps.visits.models import SupervisionVisit

from . import analytics, exports
from .models import FinalReport

F = FinalReport.Status


# =============================================================================
# Final reports (module 4.8, workflow 5.7)
# =============================================================================
class FinalReportSerializer(serializers.ModelSerializer):
    student = StudentBriefSerializer(read_only=True)
    review_status_label = serializers.CharField(source='get_review_status_display', read_only=True)
    reviewed_by_name = serializers.CharField(source='reviewed_by.full_name', read_only=True, default=None)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FinalReport
        fields = ['id', 'student', 'placement', 'version', 'title', 'report_file', 'original_filename',
                  'submission_date', 'review_status', 'review_status_label', 'feedback', 'reviewed_by_name',
                  'review_date', 'download_url']
        read_only_fields = ['id', 'student', 'placement', 'version', 'original_filename', 'submission_date',
                            'review_status', 'feedback', 'reviewed_by_name', 'review_date']
        extra_kwargs = {'report_file': {'write_only': True}}  # model validators (pdf/doc/docx, size) still apply

    def get_download_url(self, obj):
        return reverse('final-report-download', args=[obj.pk])


class FeedbackSerializer(serializers.Serializer):
    feedback = serializers.CharField(required=False, allow_blank=True, default='')


class RequiredFeedbackSerializer(serializers.Serializer):
    feedback = serializers.CharField(allow_blank=False, trim_whitespace=True)


class FinalReportViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                         viewsets.GenericViewSet):
    """/api/final-reports/ - students upload (multipart: title, report_file); every upload is a new version.
    The academic supervisor starts the review, approves, or returns it for correction. ?student= ?status="""
    serializer_class = FinalReportSerializer

    def get_queryset(self):
        qs = FinalReport.objects.filter(student__in=visible_students(self.request.user)).select_related(
            'student__user', 'student__department', 'reviewed_by__academic_profile')
        p = self.request.query_params
        if p.get('student'):
            qs = qs.filter(student_id=p['student'])
        if p.get('status') in F.values:
            qs = qs.filter(review_status=p['status'])
        return qs

    def get_permissions(self):
        if self.action == 'create':
            return [IsStudent()]
        if self.action in ('start_review', 'approve', 'return_for_correction'):
            return [IsAcademicSupervisor()]
        return super().get_permissions()

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        student = request.user.student_profile
        assignment = active_assignment(student)
        if assignment is None:
            raise ValidationError({'detail': 'You can submit the final report once your supervisors are assigned.'})
        placement = assignment.placement
        latest = FinalReport.objects.filter(placement=placement).order_by('-version').first()
        if latest and latest.review_status in FinalReport.BLOCKING_STATUSES:
            raise ValidationError({'detail': f'Your report (version {latest.version}) is '
                                             f'{latest.get_review_status_display().lower()}; you cannot upload a new '
                                             'version now.'})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data['report_file']
        version = (FinalReport.objects.filter(placement=placement).aggregate(v=Max('version'))['v'] or 0) + 1
        report = serializer.save(student=student, placement=placement, version=version,
                                 original_filename=upload.name[:255])
        log_action(request, 'report.submit', f'{student} submitted final report version {version}.')
        notify(assignment.academic_supervisor.user, 'Final report submitted',
               f'{student.full_name} submitted the final attachment report (version {version}).', Type.REPORT)
        deadline = placement.attachment_period.report_deadline if placement.attachment_period else None
        data = self.get_serializer(report).data
        data['late'] = bool(deadline and timezone.localdate() > deadline)
        return Response(data, status=status.HTTP_201_CREATED)

    def _reviewable(self):
        report = self.get_object()
        latest = FinalReport.objects.filter(placement=report.placement).order_by('-version').first()
        if report.pk != latest.pk:
            raise ValidationError({'detail': 'A newer version of this report exists.'})
        if report.review_status not in (F.SUBMITTED, F.UNDER_REVIEW):
            raise ValidationError({'detail': f'This report is already {report.get_review_status_display().lower()}.'})
        return report

    def _decide(self, request, report, new_status, feedback, title):
        report.review_status = new_status
        report.feedback = feedback
        report.reviewed_by = request.user
        report.review_date = timezone.now()
        report.save()
        log_action(request, f'report.{new_status}', f'Final report v{report.version} of {report.student}: '
                                                    f'{report.get_review_status_display()}.')
        notify(report.student.user, title, feedback or f'Your final report is {report.get_review_status_display().lower()}.',
               Type.REPORT, '/student/final-report')
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=['post'], url_path='start-review')
    def start_review(self, request, pk=None):
        report = self._reviewable()
        report.review_status = F.UNDER_REVIEW
        report.reviewed_by = request.user
        report.save()
        notify(report.student.user, 'Final report under review',
               'Your academic supervisor has started reviewing your final report.', Type.REPORT, '/student/final-report')
        return Response(self.get_serializer(report).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        report = self._reviewable()
        s = FeedbackSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return self._decide(request, report, F.APPROVED, s.validated_data['feedback'], 'Final report approved')

    @action(detail=True, methods=['post'], url_path='return')
    def return_for_correction(self, request, pk=None):
        report = self._reviewable()
        s = RequiredFeedbackSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        return self._decide(request, report, F.RETURNED, s.validated_data['feedback'],
                            'Final report returned for correction')

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        report = self.get_object()
        return file_download(report.report_file, report.original_filename or None)


# =============================================================================
# Dashboards, student records, reports
# =============================================================================
@api_view(['GET'])
def dashboard(request):
    """GET /api/dashboard/ - the numbers and lists for the signed-in user's dashboard."""
    return Response(analytics.dashboard(request.user))


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def meta(request):
    """GET /api/meta/ - choice lists shared with the frontend."""
    def choices(c):
        return [{'value': v, 'label': lbl} for v, lbl in c.choices]
    return Response({
        'roles': choices(Role),
        'academic_years': choices(Student.AcademicYear),
        'placement_statuses': choices(Placement.Status),
        'attachment_statuses': choices(Placement.AttachmentStatus),
        'logbook_statuses': choices(Logbook.Status),
        'review_statuses': choices(LogbookReview.Status),
        'report_statuses': choices(FinalReport.Status),
        'visit_statuses': choices(SupervisionVisit.Status),
        'visit_types': choices(SupervisionVisit.VisitType),
        'assessment_statuses': choices(Assessment.Status),
        'assessment_types': choices(Assessment.AssessmentType),
        'attendance_statuses': choices(Attendance.Status),
        'organization_statuses': choices(Organization.Status),
        'announcement_audiences': choices(Announcement.Audience),
        'criteria': {'max_score': MAX_SCORE, 'academic': ACADEMIC_CRITERIA, 'workplace': WORKPLACE_CRITERIA},
        'uploads': {'max_size_mb': settings.MAX_UPLOAD_SIZE_MB, 'document_extensions': DOCUMENT_EXTENSIONS,
                    'attachment_extensions': ATTACHMENT_EXTENSIONS},
    })


class ReportListView(APIView):
    """GET /api/reports/ - reports this user may generate."""

    def get(self, request):
        if request.user.role == Role.STUDENT:
            raise PermissionDenied('Students cannot generate system reports.')
        allowed = [(k, t) for k, (t, _) in analytics.REPORTS.items()
                   if request.user.role == Role.ADMIN or k not in analytics.ADMIN_ONLY_REPORTS]
        return Response([{'slug': k, 'title': t} for k, t in allowed])


class ReportView(APIView):
    """GET /api/reports/<slug>/?export=xlsx|pdf  (&department= &status=)

    Administrator: every report over all students. Supervisors: limited to their own students and
    to the progress, logbook and assessment reports (Chapter 8, "Generate system reports: Limited")."""

    def get(self, request, slug):
        if slug not in analytics.REPORTS:
            raise NotFound('Unknown report.')
        user = request.user
        if user.role == Role.STUDENT or (user.role != Role.ADMIN and slug in analytics.ADMIN_ONLY_REPORTS):
            raise PermissionDenied('You cannot generate this report.')
        title, builder = analytics.REPORTS[slug]
        columns, rows, summary = builder(user, request.query_params)
        export = request.query_params.get('export')
        if export in ('xlsx', 'pdf'):
            log_action(request, 'report.export', f'Exported "{title}" as {export.upper()}.')
            fn = exports.to_excel if export == 'xlsx' else exports.to_pdf
            return fn(slug, title, columns, rows, summary)
        return Response({'slug': slug, 'title': title, 'columns': columns, 'rows': rows, 'summary': summary})
