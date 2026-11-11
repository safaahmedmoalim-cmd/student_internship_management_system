import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.assessments.models import ACADEMIC_CRITERIA, WORKPLACE_CRITERIA
from apps.common.testing import ApiTestCase, make_admin, make_attached_student, make_student
from apps.notifications.models import Notification
from apps.visits.models import SupervisionVisit


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='sims-test-'))
class FinalReportTests(ApiTestCase):
    def setUp(self):
        self.student, self.placement, self.academic, self.industrial, _ = make_attached_student()
        self.s_api = self.client_for(self.student.user)
        self.a_api = self.client_for(self.academic.user)

    def upload(self, name='report.pdf'):
        return self.s_api.post('/api/final-reports/', {'title': 'Attachment report',
                                                       'report_file': SimpleUploadedFile(name, b'%PDF-1.4')},
                               format='multipart')

    def test_versions_review_cycle(self):
        r = self.upload()
        self.assertEqual(r.status_code, 201, r.data)
        rid = r.data['id']
        self.assertEqual(self.upload().status_code, 400)  # blocked while under review
        self.assertEqual(self.a_api.post(f'/api/final-reports/{rid}/start-review/').data['review_status'], 'under_review')
        self.assertEqual(self.a_api.post(f'/api/final-reports/{rid}/return/', {}).status_code, 400)
        self.a_api.post(f'/api/final-reports/{rid}/return/', {'feedback': 'Add a conclusion'})
        r2 = self.upload()
        self.assertEqual(r2.data['version'], 2)
        self.assertEqual(self.a_api.post(f'/api/final-reports/{rid}/approve/').status_code, 400)  # old version
        r = self.a_api.post(f'/api/final-reports/{r2.data["id"]}/approve/', {'feedback': 'Well done'})
        self.assertEqual(r.data['review_status'], 'approved')
        self.assertEqual(self.s_api.get(f'/api/final-reports/{rid}/download/').status_code, 200)
        self.assertEqual(len(self.s_api.get('/api/final-reports/').data), 2)  # history kept

    def test_only_documents_and_only_academic_reviews(self):
        self.assertIn('report_file', self.upload('virus.exe').data)
        rid = self.upload().data['id']
        self.assertEqual(self.client_for(self.industrial.user).post(f'/api/final-reports/{rid}/approve/').status_code, 403)
        stranger = make_student()
        self.assertEqual(self.client_for(stranger.user).get(f'/api/final-reports/{rid}/download/').status_code, 404)


class VisitTests(ApiTestCase):
    def test_schedule_reschedule_complete(self):
        student, _, academic, _, _ = make_attached_student()
        api = self.client_for(academic.user)
        when = timezone.now() + timedelta(days=3)
        r = api.post('/api/visits/', {'student': student.pk, 'visit_date': when.isoformat(),
                                      'visit_type': 'physical', 'objectives': 'Progress check'})
        self.assertEqual(r.status_code, 201, r.data)
        vid = r.data['id']
        self.assertTrue(Notification.objects.filter(user=student.user, notification_type='visit').exists())
        r = api.post(f'/api/visits/{vid}/reschedule/', {'visit_date': (when + timedelta(days=1)).isoformat()})
        self.assertEqual(r.data['visit_status'], 'rescheduled')
        self.assertEqual(api.post(f'/api/visits/{vid}/complete/', {'observations': 'x'}).status_code, 400)  # future
        SupervisionVisit.objects.filter(pk=vid).update(visit_date=timezone.now() - timedelta(hours=1))
        r = api.post(f'/api/visits/{vid}/complete/', {'observations': 'Doing well', 'recommendations': 'Keep going'})
        self.assertEqual(r.data['visit_status'], 'completed')
        self.assertEqual(len(self.client_for(student.user).get('/api/visits/').data), 1)
        self.assertEqual(self.client_for(student.user).post('/api/visits/', {}).status_code, 403)

    def test_cannot_schedule_for_unassigned_student(self):
        _, _, academic, _, _ = make_attached_student()
        other, *_ = make_attached_student()
        r = self.client_for(academic.user).post('/api/visits/', {
            'student': other.pk, 'visit_date': (timezone.now() + timedelta(days=1)).isoformat(), 'objectives': 'x'})
        self.assertIn('student', r.data)


class AssessmentTests(ApiTestCase):
    def setUp(self):
        self.student, self.placement, self.academic, self.industrial, _ = make_attached_student()
        self.admin = make_admin()

    def test_draft_submit_release_visibility(self):
        i_api = self.client_for(self.industrial.user)
        scores = {c: 5 for c in WORKPLACE_CRITERIA}
        r = i_api.post('/api/assessments/', {'student': self.student.pk, 'assessment_criteria': scores}, format='json')
        self.assertEqual(r.status_code, 201, r.data)
        aid = r.data['id']
        self.assertEqual(r.data['assessment_status'], 'in_progress')
        self.assertEqual(float(r.data['marks']), 100.0)
        scores['Teamwork'] = 3
        r = i_api.put(f'/api/assessments/{aid}/', {'assessment_criteria': scores, 'submit': True}, format='json')
        self.assertEqual(r.data['assessment_status'], 'completed')
        self.assertEqual(float(r.data['marks']), 96.0)
        self.assertEqual(i_api.put(f'/api/assessments/{aid}/', {'assessment_criteria': scores}, format='json').status_code, 400)

        s_api = self.client_for(self.student.user)
        self.assertEqual(s_api.get('/api/assessments/').data, [])  # not released yet
        self.assertEqual(len(self.client_for(self.academic.user).get('/api/assessments/').data), 0)
        self.assertEqual(self.client_for(self.academic.user).post(f'/api/assessments/{aid}/release/').status_code, 403)
        r = self.client_for(self.admin).post(f'/api/assessments/{aid}/release/')
        self.assertEqual(r.data['assessment_status'], 'released')
        self.assertEqual(len(s_api.get('/api/assessments/').data), 1)

    def test_criteria_validation_and_one_per_type(self):
        a_api = self.client_for(self.academic.user)
        r = a_api.post('/api/assessments/', {'student': self.student.pk, 'assessment_criteria': {'Teamwork': 4}},
                       format='json')
        self.assertIn('assessment_criteria', r.data)
        scores = {c: 6 for c in ACADEMIC_CRITERIA}
        self.assertIn('assessment_criteria', a_api.post('/api/assessments/', {
            'student': self.student.pk, 'assessment_criteria': scores}, format='json').data)
        scores = {c: 4 for c in ACADEMIC_CRITERIA}
        self.assertEqual(a_api.post('/api/assessments/', {'student': self.student.pk, 'assessment_criteria': scores},
                                    format='json').status_code, 201)
        self.assertEqual(a_api.post('/api/assessments/', {'student': self.student.pk, 'assessment_criteria': scores},
                                    format='json').status_code, 400)
        self.assertEqual(self.client_for(self.student.user).post('/api/assessments/', {}).status_code, 403)


class AnnouncementTests(ApiTestCase):
    def test_targeting_expiry_and_notifications(self):
        admin = make_admin()
        student, _, academic, industrial, _ = make_attached_student()
        api = self.client_for(admin)
        api.post('/api/announcements/', {'title': 'For students', 'message': 'Hi', 'target_audience': 'student'})
        api.post('/api/announcements/', {'title': 'Everyone', 'message': 'Hello'})
        api.post('/api/announcements/', {'title': 'Old', 'message': 'x', 'target_audience': 'all',
                                         'publication_date': (timezone.now() - timedelta(days=10)).isoformat(),
                                         'expiry_date': str(timezone.localdate() - timedelta(days=1))})
        titles = lambda u: {a['title'] for a in self.client_for(u).get('/api/announcements/').data}
        self.assertEqual(titles(student.user), {'For students', 'Everyone'})
        self.assertEqual(titles(academic.user), {'Everyone'})
        self.assertEqual(len(api.get('/api/announcements/').data), 3)
        self.assertTrue(Notification.objects.filter(user=student.user, notification_type='announcement').exists())
        self.assertEqual(self.client_for(student.user).post('/api/announcements/', {}).status_code, 403)


class NotificationTests(ApiTestCase):
    def test_own_notifications_only(self):
        student, _, academic, *_ = make_attached_student()
        n = Notification.objects.create(user=student.user, title='t', message='m', notification_type='account')
        api = self.client_for(student.user)
        self.assertEqual(api.get('/api/notifications/unread-count/').data['unread'], 1)
        api.post(f'/api/notifications/{n.pk}/read/')
        self.assertEqual(api.get('/api/notifications/unread-count/').data['unread'], 0)
        self.assertEqual(self.client_for(academic.user).post(f'/api/notifications/{n.pk}/read/').status_code, 404)


class DashboardAndReportTests(ApiTestCase):
    def test_dashboards_for_every_role(self):
        student, _, academic, industrial, _ = make_attached_student()
        admin = make_admin()
        for user, key in ((student.user, 'logbooks'), (academic.user, 'pending_report_reviews'),
                          (industrial.user, 'attendance_recorded_today'), (admin, 'pending_placements')):
            r = self.client_for(user).get('/api/dashboard/')
            self.assertEqual(r.status_code, 200)
            self.assertIn(key, r.data)

    def test_reports_and_exports(self):
        student, _, academic, *_ = make_attached_student()
        admin_api = self.client_for(make_admin())
        slugs = [r['slug'] for r in admin_api.get('/api/reports/').data]
        self.assertEqual(len(slugs), 7)
        for slug in slugs:
            r = admin_api.get(f'/api/reports/{slug}/')
            self.assertEqual(r.status_code, 200, slug)
        self.assertTrue(admin_api.get('/api/reports/students/?export=xlsx')['Content-Type'].startswith(
            'application/vnd.openxmlformats'))
        pdf = admin_api.get('/api/reports/placements/?export=pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))

        a_api = self.client_for(academic.user)
        self.assertEqual(a_api.get('/api/reports/students/').status_code, 403)       # admin-only report
        self.assertEqual(len(a_api.get('/api/reports/attachment-progress/').data['rows']), 1)  # limited
        self.assertEqual(self.client_for(student.user).get('/api/reports/logbooks/').status_code, 403)

    def test_meta_is_public(self):
        from rest_framework.test import APIClient
        r = APIClient().get('/api/meta/')
        self.assertEqual(len(r.data['criteria']['workplace']), 10)
