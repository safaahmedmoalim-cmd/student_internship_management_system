import csv

from django.db.models import Avg, Q
from django.http import FileResponse, HttpResponse
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.conf import settings

from accounts.models import Role, User
from accounts.permissions import (
    IsAcademicSupervisor, IsCoordinator, IsIndustrialSupervisor, IsStaffRole, IsStudent,
)
from accounts.serializers import UserSerializer

from .access import js_round, students_with_summary, visible_students
from .constants import ACADEMIC_ASSESSMENT_TYPES, COURSES, CRITERIA, INDUSTRIAL_ASSESSMENT_TYPE, YEARS
from .models import (
    Announcement, ApprovalStatus, Assessment, FinalReport, LogbookEntry, Placement, Visit,
)
from .serializers import (
    AnnouncementSerializer, AssessmentSerializer, AssignSerializer, FinalReportSerializer,
    LogbookEntrySerializer, OptionalCommentSerializer, PlacementSerializer, ReasonSerializer,
    StudentSummarySerializer, VisitSerializer,
)


def _filter_by_status(qs, request, valid):
    value = request.query_params.get('status')
    return qs.filter(status=value) if value in valid else qs


def _forbidden(message):
    return Response({'detail': message}, status=status.HTTP_403_FORBIDDEN)


def _bad_request(message):
    return Response({'detail': message}, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# Placements
# =============================================================================
class PlacementViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                       mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    GET    /api/placements/               list (students: own, supervisors: their students', coordinator: all)
    POST   /api/placements/               student submits placement details
    DELETE /api/placements/<id>/          student withdraws a pending/rejected placement
    POST   /api/placements/<id>/approve/  coordinator
    POST   /api/placements/<id>/reject/   coordinator  {"comment": "reason"}
    """
    serializer_class = PlacementSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Placement.objects.select_related('student', 'industrial_supervisor')
        if user.role != Role.COORDINATOR:
            qs = qs.filter(student__in=visible_students(user))
        return _filter_by_status(qs, self.request, ApprovalStatus.values)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsStudent()]
        if self.action in ('approve', 'reject'):
            return [IsAuthenticated(), IsCoordinator()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def destroy(self, request, *args, **kwargs):
        placement = self.get_object()
        if placement.student_id != request.user.id:
            return _forbidden('Only the student can withdraw their own placement.')
        if placement.status == ApprovalStatus.APPROVED:
            return _bad_request('An approved placement cannot be withdrawn. Ask the coordinator.')
        placement.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        placement = self.get_object()
        if placement.status != ApprovalStatus.PENDING:
            return _bad_request('Only pending placements can be approved.')
        placement.approve(request.user)
        return Response(self.get_serializer(placement).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        placement = self.get_object()
        if placement.status != ApprovalStatus.PENDING:
            return _bad_request('Only pending placements can be rejected.')
        body = ReasonSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        placement.reject(request.user, body.validated_data['comment'])
        return Response(self.get_serializer(placement).data)


# =============================================================================
# Logbook
# =============================================================================
class LogbookViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                     mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """
    GET    /api/logbook/?student=<id>&status=pending
    POST   /api/logbook/                   student adds a weekly entry (placement must be approved)
    DELETE /api/logbook/<id>/              student deletes an entry that is not approved
    POST   /api/logbook/<id>/approve/      industrial supervisor  {"comment": "optional"}
    POST   /api/logbook/<id>/reject/       industrial supervisor  {"comment": "reason"}
    POST   /api/logbook/<id>/comment/      academic supervisor    {"comment": "feedback"}
    """
    serializer_class = LogbookEntrySerializer

    def get_queryset(self):
        qs = (LogbookEntry.objects.select_related('student')
              .filter(student__in=visible_students(self.request.user)))
        student = self.request.query_params.get('student')
        if student and student.isdigit():
            qs = qs.filter(student_id=int(student))
        return _filter_by_status(qs, self.request, ApprovalStatus.values)

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsStudent()]
        if self.action in ('approve', 'reject'):
            return [IsAuthenticated(), IsIndustrialSupervisor()]
        if self.action == 'comment':
            return [IsAuthenticated(), IsAcademicSupervisor()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def destroy(self, request, *args, **kwargs):
        entry = self.get_object()
        if entry.student_id != request.user.id:
            return _forbidden('Only the student can delete their own entries.')
        if entry.status == ApprovalStatus.APPROVED:
            return _bad_request('Approved entries cannot be deleted.')
        entry.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        entry = self.get_object()
        if entry.status != ApprovalStatus.PENDING:
            return _bad_request('Only pending entries can be approved.')
        body = OptionalCommentSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        entry.approve(body.validated_data['comment'])
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        entry = self.get_object()
        if entry.status != ApprovalStatus.PENDING:
            return _bad_request('Only pending entries can be rejected.')
        body = ReasonSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        entry.reject(body.validated_data['comment'])
        return Response(self.get_serializer(entry).data)

    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):
        entry = self.get_object()
        body = ReasonSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        entry.academic_comment = body.validated_data['comment']
        entry.save(update_fields=['academic_comment', 'updated_at'])
        return Response(self.get_serializer(entry).data)


# =============================================================================
# Final reports
# =============================================================================
class FinalReportViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                         viewsets.GenericViewSet):
    """
    GET  /api/final-reports/
    POST /api/final-reports/                  student, multipart form: title, summary, file (pdf/doc/docx, max 10 MB)
    GET  /api/final-reports/<id>/download/    the uploaded file (authenticated)
    POST /api/final-reports/<id>/review/      academic supervisor marks it reviewed
    """
    serializer_class = FinalReportSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        return (FinalReport.objects.select_related('student')
                .filter(student__in=visible_students(self.request.user)))

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsStudent()]
        if self.action == 'review':
            return [IsAuthenticated(), IsAcademicSupervisor()]
        return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        existing = FinalReport.objects.filter(student=request.user).first()
        if existing and existing.status == FinalReport.Status.REVIEWED:
            return _bad_request('Your report has already been reviewed and can no longer be replaced.')
        serializer = self.get_serializer(existing, data=request.data)   # existing -> replace it
        serializer.is_valid(raise_exception=True)
        old_file = existing.file.name if existing and existing.file else None
        report = serializer.save(student=request.user, status=FinalReport.Status.SUBMITTED,
                                 submitted_at=timezone.now(), reviewed_by=None, reviewed_at=None)
        if old_file and old_file != report.file.name:
            report.file.storage.delete(old_file)
        return Response(self.get_serializer(report).data,
                        status=status.HTTP_200_OK if existing else status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        report = self.get_object()
        return FileResponse(report.file.open('rb'), as_attachment=True, filename=report.original_name)

    @action(detail=True, methods=['post'])
    def review(self, request, pk=None):
        report = self.get_object()
        if report.status == FinalReport.Status.REVIEWED:
            return _bad_request('This report is already reviewed.')
        report.mark_reviewed(request.user)
        return Response(self.get_serializer(report).data)


# =============================================================================
# Visits
# =============================================================================
class VisitViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                   viewsets.GenericViewSet):
    """
    GET  /api/visits/
    POST /api/visits/                  academic supervisor  {student, visit_date, mode, notes}
    POST /api/visits/<id>/complete/    academic supervisor
    POST /api/visits/<id>/cancel/      academic supervisor
    """
    serializer_class = VisitSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Visit.objects.select_related('student', 'academic')
        if user.role == Role.ACADEMIC:
            qs = qs.filter(academic=user)
        elif user.role != Role.COORDINATOR:
            qs = qs.filter(student__in=visible_students(user))
        return _filter_by_status(qs, self.request, Visit.Status.values)

    def get_permissions(self):
        if self.action in ('create', 'complete', 'cancel'):
            return [IsAuthenticated(), IsAcademicSupervisor()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(academic=self.request.user)

    def _set_status(self, new_status):
        visit = self.get_object()
        if visit.status != Visit.Status.SCHEDULED:
            return _bad_request('Only scheduled visits can be changed.')
        visit.status = new_status
        visit.save(update_fields=['status'])
        return Response(self.get_serializer(visit).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        return self._set_status(Visit.Status.COMPLETED)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        return self._set_status(Visit.Status.CANCELLED)


# =============================================================================
# Assessments
# =============================================================================
class AssessmentViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                        viewsets.GenericViewSet):
    """
    GET  /api/assessments/?student=<id>
    POST /api/assessments/   academic: {student, assessment_type, marks, comment}
                             industrial: {student, ratings: {"<skill>": 1-5, ...}, comment}  (marks are calculated)
    """
    serializer_class = AssessmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Assessment.objects.select_related('student', 'assessor')
        if user.role == Role.STUDENT:
            qs = qs.filter(student=user)
        elif user.role != Role.COORDINATOR:
            qs = qs.filter(assessor=user)
        student = self.request.query_params.get('student')
        if student and student.isdigit():
            qs = qs.filter(student_id=int(student))
        return qs

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), (IsAcademicSupervisor | IsIndustrialSupervisor)()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(assessor=self.request.user, assessor_role=self.request.user.role)


# =============================================================================
# Announcements
# =============================================================================
class AnnouncementViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
                          mixins.DestroyModelMixin, viewsets.GenericViewSet):
    """Everyone can read; only the coordinator can post or delete."""
    serializer_class = AnnouncementSerializer
    queryset = Announcement.objects.select_related('author')

    def get_permissions(self):
        if self.action in ('create', 'destroy'):
            return [IsAuthenticated(), IsCoordinator()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


# =============================================================================
# Students (supervisor / coordinator views) and supervisor assignment
# =============================================================================
class StudentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET   /api/students/?search=&course=&placement_status=   students you may see, with progress
    GET   /api/students/<id>/
    PATCH /api/students/<id>/assign/   coordinator  {"academic_supervisor": id|null, "industrial_supervisor": id|null}
    """
    serializer_class = StudentSummarySerializer
    permission_classes = [IsAuthenticated, IsStaffRole]

    def get_queryset(self):
        qs = students_with_summary(visible_students(self.request.user))
        params = self.request.query_params
        search = params.get('search')
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(adm_no__icontains=search) | Q(email__icontains=search))
        if params.get('course'):
            qs = qs.filter(course=params['course'])
        state = params.get('placement_status')
        if state == 'none':
            qs = qs.filter(placement_status__isnull=True)
        elif state in ApprovalStatus.values:
            qs = qs.filter(placement_status=state)
        return qs.order_by('adm_no')

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsCoordinator])
    def assign(self, request, pk=None):
        student = self.get_object()
        body = AssignSerializer(data=request.data)
        body.is_valid(raise_exception=True)
        fields = []
        for key in ('academic_supervisor', 'industrial_supervisor'):
            if key in body.validated_data:
                setattr(student, key, body.validated_data[key])
                fields.append(key)
        if fields:
            student.save(update_fields=fields)
        return Response(self.get_serializer(self.get_queryset().get(pk=student.pk)).data)


# =============================================================================
# Reports (coordinator)
# =============================================================================
class ReportSummaryView(APIView):
    """GET /api/reports/summary/  - progress and assessment results for every student."""
    permission_classes = [IsAuthenticated, IsCoordinator]

    def get(self, request):
        qs = students_with_summary(visible_students(request.user)).order_by('adm_no')
        return Response(StudentSummarySerializer(qs, many=True).data)


class ReportCsvView(APIView):
    """GET /api/reports/summary.csv  - the same data as a downloadable CSV."""
    permission_classes = [IsAuthenticated, IsCoordinator]

    def get(self, request):
        qs = students_with_summary(visible_students(request.user)).order_by('adm_no')
        rows = StudentSummarySerializer(qs, many=True).data
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="langata-attachment-report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Name', 'Admission No', 'Course', 'Organisation', 'Approved hours', 'Academic %',
                         'Industrial %', 'Overall %', 'Final report'])
        for r in rows:
            writer.writerow([r['name'], r['adm_no'], r['course'], r['placement_company'] or '', r['approved_hours'],
                             _blank(r['academic_marks']), _blank(r['industrial_marks']), _blank(r['overall_marks']),
                             r['report_status'] or 'none'])
        return response


def _blank(value):
    return '' if value is None else value


# =============================================================================
# Lists the frontend needs for dropdowns (no login required - used on the sign-up form)
# =============================================================================
@api_view(['GET'])
@authentication_classes([])      # public: a stale token in the browser must not turn this into a 401
@permission_classes([AllowAny])
def meta(request):
    return Response({
        'courses': COURSES,
        'years': YEARS,
        'criteria': CRITERIA,
        'academic_assessment_types': ACADEMIC_ASSESSMENT_TYPES,
        'industrial_assessment_type': INDUSTRIAL_ASSESSMENT_TYPE,
        'target_hours': settings.TARGET_HOURS,
        'max_report_size_mb': settings.MAX_REPORT_SIZE_MB,
    })


# =============================================================================
# Dashboards - one endpoint, the content depends on the caller's role
# =============================================================================
def _latest_announcements(request, limit=4):
    return AnnouncementSerializer(Announcement.objects.select_related('author')[:limit], many=True,
                                  context={'request': request}).data


def _student_dashboard(request):
    user = request.user
    ctx = {'request': request}
    placement = Placement.objects.select_related('student', 'industrial_supervisor').filter(student=user).first()
    entries = LogbookEntry.objects.filter(student=user)
    approved_hours = sum(e.hours_worked for e in entries if e.status == ApprovalStatus.APPROVED)
    average = Assessment.objects.filter(student=user).aggregate(a=Avg('marks'))['a']
    return {
        'user': UserSerializer(user).data,
        'placement': PlacementSerializer(placement, context=ctx).data if placement else None,
        'stats': {
            'approved_hours': approved_hours,
            'logged_hours': sum(e.hours_worked for e in entries),
            'target_hours': settings.TARGET_HOURS,
            'percent_complete': min(100, round(approved_hours * 100 / settings.TARGET_HOURS)),
            'entries_total': len(entries),
            'entries_approved': sum(1 for e in entries if e.status == ApprovalStatus.APPROVED),
            'average_score': js_round(average),
        },
        'recent_logbook': LogbookEntrySerializer_data(entries.order_by('-week_no')[:3], ctx),
        'assessments': AssessmentSerializer(Assessment.objects.select_related('student', 'assessor')
                                            .filter(student=user), many=True, context=ctx).data,
        'announcements': _latest_announcements(request),
    }


def LogbookEntrySerializer_data(queryset, ctx):
    from .serializers import LogbookEntrySerializer
    return LogbookEntrySerializer(queryset, many=True, context=ctx).data


def _academic_dashboard(request):
    user = request.user
    students = visible_students(user)
    visits = Visit.objects.select_related('student', 'academic').filter(academic=user, status=Visit.Status.SCHEDULED)
    entries = LogbookEntry.objects.filter(student__in=students)
    return {
        'user': UserSerializer(user).data,
        'stats': {
            'assigned_students': students.count(),
            'upcoming_visits': visits.count(),
            'entries_to_review': entries.filter(academic_comment='').count(),
            'assessments_done': Assessment.objects.filter(assessor=user).count(),
        },
        'upcoming_visits': VisitSerializer(visits.order_by('visit_date')[:4], many=True,
                                           context={'request': request}).data,
        'announcements': _latest_announcements(request),
    }


def _industrial_dashboard(request):
    user = request.user
    students = visible_students(user)
    entries = LogbookEntry.objects.select_related('student').filter(student__in=students)
    pending = entries.filter(status=ApprovalStatus.PENDING)
    return {
        'user': UserSerializer(user).data,
        'stats': {
            'interns': students.count(),
            'pending_approvals': pending.count(),
            'approved_entries': entries.filter(status=ApprovalStatus.APPROVED).count(),
            'evaluations': Assessment.objects.filter(assessor=user).count(),
        },
        'pending_entries': LogbookEntrySerializer_data(pending.order_by('created_at')[:5], {'request': request}),
        'announcements': _latest_announcements(request),
    }


def _coordinator_dashboard(request):
    students = visible_students(request.user)
    total = students.count()
    counts = {'none': 0, ApprovalStatus.PENDING: 0, ApprovalStatus.APPROVED: 0, ApprovalStatus.REJECTED: 0}
    for placement_status in Placement.objects.filter(student__in=students).values_list('status', flat=True):
        counts[placement_status] += 1
    counts['none'] = total - sum(v for k, v in counts.items() if k != 'none')
    recent = students_with_summary(students).order_by('-date_joined')[:5]
    return {
        'user': UserSerializer(request.user).data,
        'stats': {
            'students': total,
            'placed': counts[ApprovalStatus.APPROVED],
            'pending_placements': counts[ApprovalStatus.PENDING],
            'academic_supervisors': User.objects.filter(role=Role.ACADEMIC, is_active=True).count(),
            'industrial_supervisors': User.objects.filter(role=Role.INDUSTRIAL, is_active=True).count(),
        },
        'placement_overview': {str(k): v for k, v in counts.items()},
        'recent_registrations': StudentSummarySerializer(recent, many=True).data,
        'announcements': _latest_announcements(request),
    }


@api_view(['GET'])
def dashboard(request):
    """GET /api/dashboard/ - the numbers and lists behind the caller's dashboard."""
    builders = {
        Role.STUDENT: _student_dashboard,
        Role.ACADEMIC: _academic_dashboard,
        Role.INDUSTRIAL: _industrial_dashboard,
        Role.COORDINATOR: _coordinator_dashboard,
    }
    return Response({'role': request.user.role, **builders[request.user.role](request)})
