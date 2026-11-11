"""Progress figures, dashboards and the report builders (modules 4.11 and Chapter 3 dashboards)."""
from django.db.models import Avg, CharField, Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce, Concat
from django.utils import timezone

from apps.accounts.models import Role, SystemSetting
from apps.announcements.models import Announcement
from apps.assessments.models import Assessment
from apps.logbooks.models import Attendance, Logbook, LogbookReview
from apps.notifications.models import Notification
from apps.organizations.models import Organization
from apps.placements.models import Placement
from apps.students.models import Student
from apps.supervisors.access import active_assignment, visible_students
from apps.supervisors.models import AcademicSupervisor, IndustrialSupervisor, SupervisorAssignment
from apps.visits.models import SupervisionVisit

from .models import FinalReport

P = Placement.Status
ACTIVE_ASSIGNMENT = SupervisorAssignment.Status.ACTIVE


def _count(model, **flt):
    return Coalesce(Subquery(
        model.objects.filter(student=OuterRef('pk'), **flt).order_by().values('student')
        .annotate(c=Count('pk')).values('c'), output_field=IntegerField()), 0)


def annotate_students(qs):
    """Add one-row-per-student summary columns without multiplying joins."""
    latest = Placement.objects.filter(student=OuterRef('pk')).order_by('-application_date')
    assignment = SupervisorAssignment.objects.filter(student=OuterRef('pk'), assignment_status=ACTIVE_ASSIGNMENT) \
        .order_by('-assigned_date')
    report = FinalReport.objects.filter(student=OuterRef('pk')).order_by('-submission_date')
    full = lambda prefix: Concat(f'{prefix}__first_name', Value(' '), f'{prefix}__last_name', output_field=CharField())
    return qs.select_related('user', 'department').annotate(
        placement_status=Subquery(latest.values('application_status')[:1]),
        attachment_status=Subquery(latest.values('attachment_status')[:1]),
        organization_name=Subquery(latest.values('organization__organization_name')[:1]),
        academic_supervisor_name=Subquery(assignment.annotate(n=full('academic_supervisor')).values('n')[:1]),
        industrial_supervisor_name=Subquery(assignment.annotate(n=full('industrial_supervisor')).values('n')[:1]),
        logbooks_total=_count(Logbook),
        logbooks_approved=_count(Logbook, status=Logbook.Status.APPROVED),
        logbooks_rejected=_count(Logbook, status=Logbook.Status.REJECTED),
        visits_completed=_count(SupervisionVisit, visit_status=SupervisionVisit.Status.COMPLETED),
        report_status=Subquery(report.values('review_status')[:1]),
        assessments_done=_count(Assessment, assessment_status__in=[Assessment.Status.COMPLETED,
                                                                    Assessment.Status.RELEASED]),
    )


def student_row(s):
    return {
        'id': s.pk, 'user_id': s.user_id, 'registration_number': s.registration_number, 'full_name': s.full_name,
        'email': s.user.email, 'phone_number': s.phone_number, 'department_name': s.department.department_name,
        'academic_year': s.academic_year, 'is_active': s.user.is_active,
        'placement_status': s.placement_status or 'none', 'attachment_status': s.attachment_status,
        'organization_name': s.organization_name, 'academic_supervisor_name': s.academic_supervisor_name,
        'industrial_supervisor_name': s.industrial_supervisor_name, 'logbooks_total': s.logbooks_total,
        'logbooks_approved': s.logbooks_approved, 'logbooks_rejected': s.logbooks_rejected,
        'visits_completed': s.visits_completed, 'report_status': s.report_status,
        'assessments_done': s.assessments_done,
    }


def _assessment_view(a, viewer):
    if a is None:
        return {'status': Assessment.Status.PENDING, 'marks': None}
    can_see_marks = (viewer.role == Role.ADMIN or a.supervisor_id == viewer.pk
                     or a.assessment_status == Assessment.Status.RELEASED)
    return {'id': a.pk, 'status': a.assessment_status, 'status_label': a.get_assessment_status_display(),
            'marks': float(a.marks) if can_see_marks else None, 'supervisor_name': a.supervisor.full_name}


def student_progress(student, viewer):
    """Everything about one student's attachment, as allowed for `viewer`."""
    placement = Placement.current_for(student) or student.placements.filter(application_status=P.APPROVED).first() \
        or student.placements.first()
    assignment = active_assignment(student)
    required = SystemSetting.load().required_logbook_weeks
    logs = Logbook.objects.filter(student=student, **({'placement': placement} if placement else {}))
    by_status = dict(logs.values_list('status').annotate(c=Count('pk')))
    att = dict(Attendance.objects.filter(student=student).values_list('attendance_status').annotate(c=Count('pk')))
    attended = att.get('present', 0) + att.get('late', 0)
    att_total = sum(att.values())
    visits = dict(SupervisionVisit.objects.filter(student=student).values_list('visit_status').annotate(c=Count('pk')))
    report = FinalReport.objects.filter(student=student).first()
    assessments = {a.assessment_type: a for a in Assessment.objects.filter(student=student, placement=placement)
                   .select_related('supervisor__academic_profile', 'supervisor__industrial_profile')} if placement else {}
    return {
        'placement': {
            'id': placement.pk, 'organization_name': placement.organization.organization_name,
            'county': placement.organization.county, 'start_date': placement.start_date,
            'end_date': placement.end_date, 'application_status': placement.application_status,
            'application_status_label': placement.get_application_status_display(),
            'attachment_status': placement.attachment_status,
            'attachment_status_label': placement.get_attachment_status_display(),
        } if placement else None,
        'supervisors': {
            'academic': {'name': assignment.academic_supervisor.full_name,
                         'email': assignment.academic_supervisor.user.email,
                         'phone_number': assignment.academic_supervisor.phone_number},
            'industrial': {'name': assignment.industrial_supervisor.full_name,
                           'email': assignment.industrial_supervisor.user.email,
                           'phone_number': assignment.industrial_supervisor.phone_number,
                           'job_title': assignment.industrial_supervisor.job_title},
            'assigned_date': assignment.assigned_date,
        } if assignment else None,
        'logbooks': {
            'required': required, 'total': sum(by_status.values()),
            'approved': by_status.get(Logbook.Status.APPROVED, 0),
            'rejected': by_status.get(Logbook.Status.REJECTED, 0),
            'pending': by_status.get(Logbook.Status.SUBMITTED, 0) + by_status.get(Logbook.Status.UNDER_REVIEW, 0),
            'percent': min(100, round(by_status.get(Logbook.Status.APPROVED, 0) * 100 / required)) if required else 0,
        },
        'attendance': {**{k: att.get(k, 0) for k in Attendance.Status.values}, 'total': att_total,
                       'rate': round(attended * 100 / att_total) if att_total else None},
        'visits': {'scheduled': visits.get('scheduled', 0) + visits.get('rescheduled', 0),
                   'completed': visits.get('completed', 0), 'cancelled': visits.get('cancelled', 0)},
        'final_report': {'id': report.pk, 'version': report.version, 'status': report.review_status,
                         'status_label': report.get_review_status_display()} if report else None,
        'assessments': {
            'academic': _assessment_view(assessments.get(Assessment.AssessmentType.ACADEMIC), viewer),
            'workplace': _assessment_view(assessments.get(Assessment.AssessmentType.WORKPLACE), viewer),
        },
    }


# =============================================================================
# Dashboards
# =============================================================================
def _recent_announcements(user, n=5):
    return [{'id': a.pk, 'title': a.title, 'message': a.message, 'publication_date': a.publication_date}
            for a in Announcement.visible_to(user)[:n]]


def _upcoming_visits(qs, n=5):
    rows = qs.filter(visit_status__in=SupervisionVisit.UPCOMING_STATUSES, visit_date__gte=timezone.now()) \
        .select_related('student', 'organization').order_by('visit_date')[:n]
    return [{'id': v.pk, 'student_name': v.student.full_name, 'visit_date': v.visit_date,
             'visit_type': v.visit_type, 'organization_name': v.organization.organization_name if v.organization else None}
            for v in rows]


def dashboard(user):
    base = {'role': user.role, 'full_name': user.full_name,
            'unread_notifications': Notification.objects.filter(user=user, is_read=False).count(),
            'announcements': _recent_announcements(user)}

    if user.role == Role.STUDENT:
        student = user.student_profile
        latest = student.placements.select_related('organization').first()
        base.update(student_progress(student, user))
        base['latest_application'] = {
            'id': latest.pk, 'status': latest.application_status,
            'status_label': latest.get_application_status_display(),
            'organization_name': latest.organization.organization_name,
            'approval_comments': latest.approval_comments} if latest else None
        base['upcoming_visits'] = _upcoming_visits(SupervisionVisit.objects.filter(student=student))
        return base

    if user.role in (Role.ACADEMIC, Role.INDUSTRIAL):
        students = visible_students(user)
        pending_reviews = Logbook.objects.filter(
            student__in=students, reviews__supervisor_role=user.role,
            reviews__review_status=LogbookReview.Status.PENDING).distinct().count()
        a_type = Assessment.TYPE_FOR_ROLE[user.role]
        assessed = Assessment.objects.filter(student__in=students, assessment_type=a_type,
                                             assessment_status__in=[Assessment.Status.COMPLETED,
                                                                    Assessment.Status.RELEASED])
        base.update({
            'assigned_students': students.count(),
            'pending_logbook_reviews': pending_reviews,
            'assessments_completed': assessed.count(),
            'assessments_pending': max(students.count() - assessed.count(), 0),
            'students': [student_row(s) for s in annotate_students(students)[:10]],
        })
        if user.role == Role.ACADEMIC:
            base['pending_report_reviews'] = FinalReport.objects.filter(
                student__in=students, review_status__in=[FinalReport.Status.SUBMITTED,
                                                         FinalReport.Status.UNDER_REVIEW]).count()
            base['upcoming_visits'] = _upcoming_visits(SupervisionVisit.objects.filter(academic_supervisor__user=user))
        else:
            today = timezone.localdate()
            base['attendance_recorded_today'] = Attendance.objects.filter(student__in=students,
                                                                          attendance_date=today).count()
            base['organization_name'] = user.industrial_profile.organization.organization_name
        return base

    # Administrator
    placements = Placement.objects.all()
    status_counts = dict(placements.values_list('application_status').annotate(c=Count('pk')))
    base.update({
        'total_students': Student.objects.filter(user__is_active=True).count(),
        'total_academic_supervisors': AcademicSupervisor.objects.filter(user__is_active=True).count(),
        'total_industrial_supervisors': IndustrialSupervisor.objects.filter(user__is_active=True).count(),
        'total_organizations': Organization.objects.filter(status=Organization.Status.ACTIVE).count(),
        'organizations_pending_verification': Organization.objects.filter(status=Organization.Status.PENDING).count(),
        'pending_placements': status_counts.get(P.PENDING, 0),
        'approved_placements': status_counts.get(P.APPROVED, 0),
        'rejected_placements': status_counts.get(P.REJECTED, 0),
        'returned_placements': status_counts.get(P.RETURNED, 0),
        'active_attachment_students': placements.filter(
            application_status=P.APPROVED, attachment_status=Placement.AttachmentStatus.ACTIVE).count(),
        'completed_attachments': placements.filter(attachment_status=Placement.AttachmentStatus.COMPLETED).count(),
        'unassigned_placements': placements.filter(
            application_status=P.APPROVED,
            attachment_status__in=[Placement.AttachmentStatus.NOT_STARTED, Placement.AttachmentStatus.ACTIVE],
        ).exclude(assignments__assignment_status=ACTIVE_ASSIGNMENT).count(),
        'pending_logbook_reviews': Logbook.objects.filter(
            status__in=[Logbook.Status.SUBMITTED, Logbook.Status.UNDER_REVIEW]).count(),
        'completed_assessments': Assessment.objects.filter(assessment_status=Assessment.Status.COMPLETED).count(),
        'released_assessments': Assessment.objects.filter(assessment_status=Assessment.Status.RELEASED).count(),
        'pending_final_reports': FinalReport.objects.filter(
            review_status__in=[FinalReport.Status.SUBMITTED, FinalReport.Status.UNDER_REVIEW]).count(),
        'placement_status_chart': [{'status': s.label, 'count': status_counts.get(s.value, 0)} for s in P],
        'recent_placements': [
            {'id': p.pk, 'student_name': p.student.full_name, 'organization_name': p.organization.organization_name,
             'status': p.application_status, 'status_label': p.get_application_status_display(),
             'application_date': p.application_date}
            for p in placements.select_related('student', 'organization').order_by('-application_date')[:6]],
    })
    return base


# =============================================================================
# Reports (module 4.11). Each builder returns (columns, rows, summary).
# Supervisors get "limited" reports: the same builders, restricted to their own students.
# =============================================================================
def _fmt_date(d):
    return d.strftime('%Y-%m-%d') if d else ''


def _students_for(user, params):
    qs = visible_students(user)
    if params.get('department'):
        qs = qs.filter(department_id=params['department'])
    return qs


def report_students(user, params):
    rows = [student_row(s) for s in annotate_students(_students_for(user, params))]
    cols = ['Reg. No.', 'Name', 'Department', 'Year', 'Email', 'Phone', 'Placement', 'Organization']
    data = [[r['registration_number'], r['full_name'], r['department_name'], r['academic_year'], r['email'],
             r['phone_number'], P(r['placement_status']).label if r['placement_status'] != 'none' else 'None',
             r['organization_name'] or ''] for r in rows]
    placed = sum(1 for r in rows if r['placement_status'] == P.APPROVED)
    return cols, data, {'Registered students': len(rows), 'Placed in organizations': placed}


def report_placements(user, params):
    qs = Placement.objects.filter(student__in=_students_for(user, params)).select_related('student', 'organization')
    if params.get('status') in P.values:
        qs = qs.filter(application_status=params['status'])
    cols = ['Reg. No.', 'Student', 'Organization', 'County', 'Start', 'End', 'Applied', 'Status', 'Attachment']
    data = [[p.student.registration_number, p.student.full_name, p.organization.organization_name,
             p.organization.county, _fmt_date(p.start_date), _fmt_date(p.end_date), _fmt_date(p.application_date),
             p.get_application_status_display(), p.get_attachment_status_display()] for p in qs]
    counts = dict(qs.values_list('application_status').annotate(c=Count('pk')))
    total = sum(counts.values())
    summary = {s.label: counts.get(s.value, 0) for s in P}
    summary['Approval rate'] = f'{round(counts.get(P.APPROVED, 0) * 100 / total)}%' if total else '-'
    return cols, data, summary


def report_allocation(user, params):
    qs = SupervisorAssignment.objects.filter(student__in=_students_for(user, params),
                                             assignment_status=ACTIVE_ASSIGNMENT).select_related(
        'student', 'placement__organization', 'academic_supervisor', 'industrial_supervisor')
    cols = ['Reg. No.', 'Student', 'Organization', 'Academic Supervisor', 'Industrial Supervisor', 'Assigned']
    data = [[a.student.registration_number, a.student.full_name, a.placement.organization.organization_name,
             a.academic_supervisor.full_name, a.industrial_supervisor.full_name, _fmt_date(a.assigned_date)]
            for a in qs]
    per_sup = qs.values('academic_supervisor').distinct().count()
    return cols, data, {'Students with supervisors': len(data), 'Academic supervisors in use': per_sup}


def report_logbooks(user, params):
    required = SystemSetting.load().required_logbook_weeks
    rows = annotate_students(_students_for(user, params)).annotate(
        logbooks_pending=_count(Logbook, status__in=[Logbook.Status.SUBMITTED, Logbook.Status.UNDER_REVIEW]))
    cols = ['Reg. No.', 'Student', 'Submitted', 'Approved', 'Rejected', 'Awaiting review', 'Required', 'Progress']
    data = [[s.registration_number, s.full_name, s.logbooks_total, s.logbooks_approved, s.logbooks_rejected,
             s.logbooks_pending, required, f'{min(100, round(s.logbooks_approved * 100 / required)) if required else 0}%']
            for s in rows]
    return cols, data, {'Entries submitted': sum(r[2] for r in data), 'Entries approved': sum(r[3] for r in data),
                        'Awaiting review': sum(r[5] for r in data)}


def report_assessments(user, params):
    students = _students_for(user, params)
    qs = Assessment.objects.filter(student__in=students)
    if user.role == Role.STUDENT:
        qs = qs.filter(assessment_status=Assessment.Status.RELEASED)
    elif user.role != Role.ADMIN:
        qs = qs.filter(Q(supervisor=user) | Q(assessment_status=Assessment.Status.RELEASED))
    by_student = {}
    for a in qs:
        by_student.setdefault(a.student_id, {})[a.assessment_type] = a
    cols = ['Reg. No.', 'Student', 'Academic (%)', 'Academic status', 'Workplace (%)', 'Workplace status', 'Average (%)']
    data = []
    for s in students:
        ac = by_student.get(s.pk, {}).get(Assessment.AssessmentType.ACADEMIC)
        wp = by_student.get(s.pk, {}).get(Assessment.AssessmentType.WORKPLACE)
        marks = [float(a.marks) for a in (ac, wp) if a]
        data.append([s.registration_number, s.full_name, float(ac.marks) if ac else '',
                     ac.get_assessment_status_display() if ac else 'Pending', float(wp.marks) if wp else '',
                     wp.get_assessment_status_display() if wp else 'Pending',
                     round(sum(marks) / len(marks), 2) if marks else ''])
    avg = qs.aggregate(a=Avg('marks'))['a']
    return cols, data, {'Assessments recorded': qs.count(),
                        'Average mark': f'{round(float(avg), 2)}%' if avg is not None else '-'}


def report_progress(user, params, completed_only=False):
    qs = annotate_students(_students_for(user, params))
    if completed_only:
        qs = qs.filter(placements__attachment_status=Placement.AttachmentStatus.COMPLETED).distinct()
    required = SystemSetting.load().required_logbook_weeks
    cols = ['Reg. No.', 'Student', 'Organization', 'Attachment', 'Logbooks approved', 'Visits done',
            'Final report', 'Assessments']
    data = [[s.registration_number, s.full_name, s.organization_name or '',
             Placement.AttachmentStatus(s.attachment_status).label if s.attachment_status else 'Not placed',
             f'{s.logbooks_approved}/{required}', s.visits_completed,
             FinalReport.Status(s.report_status).label if s.report_status else 'Not submitted',
             f'{s.assessments_done}/2'] for s in qs]
    return cols, data, {'Students': len(data)}


REPORTS = {
    'students': ('Registered Students', report_students),
    'placements': ('Placement Applications and Approval Statistics', report_placements),
    'supervisor-allocation': ('Supervisor Allocation', report_allocation),
    'logbooks': ('Logbook Submission Statistics', report_logbooks),
    'assessments': ('Assessment Results', report_assessments),
    'attachment-progress': ('Student Attachment Progress', report_progress),
    'completed-attachments': ('Completed Attachments', lambda u, p: report_progress(u, p, completed_only=True)),
}
ADMIN_ONLY_REPORTS = {'students', 'placements', 'supervisor-allocation'}
