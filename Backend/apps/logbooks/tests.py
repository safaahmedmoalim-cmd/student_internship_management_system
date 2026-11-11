from datetime import timedelta

from django.utils import timezone

from apps.common.testing import ApiTestCase, make_admin, make_attached_student, make_placement, make_student
from apps.notifications.models import Notification

from .models import Attendance, Logbook

TODAY = timezone.localdate()


class LogbookTests(ApiTestCase):
    def setUp(self):
        self.student, self.placement, self.academic, self.industrial, _ = make_attached_student()
        self.s_api = self.client_for(self.student.user)
        self.a_api = self.client_for(self.academic.user)
        self.i_api = self.client_for(self.industrial.user)

    def submit(self, week=1, **over):
        start = self.placement.start_date + timedelta(weeks=week - 1)
        data = {'week_number': week, 'start_date': start, 'end_date': start + timedelta(days=4),
                'activities': 'Configured routers', 'skills_acquired': 'Networking'}
        data.update(over)
        return self.s_api.post('/api/logbooks/', data, format='multipart')

    def test_dual_independent_review(self):
        r = self.submit()
        self.assertEqual(r.status_code, 201, r.data)
        lid = r.data['id']
        self.assertEqual(len(r.data['reviews']), 2)
        self.assertTrue(Notification.objects.filter(user=self.academic.user, notification_type='logbook').exists())
        self.assertTrue(Notification.objects.filter(user=self.industrial.user, notification_type='logbook').exists())

        self.assertEqual(len(self.a_api.get('/api/logbooks/?pending_my_review=true').data), 1)
        r = self.i_api.post(f'/api/logbooks/{lid}/review/', {'decision': 'approved'})
        self.assertEqual(r.data['status'], 'under_review')
        self.assertEqual(len(self.i_api.get('/api/logbooks/?pending_my_review=true').data), 0)
        r = self.a_api.post(f'/api/logbooks/{lid}/review/', {'decision': 'approved', 'comments': 'Good'})
        self.assertEqual(r.data['status'], 'approved')
        # approved entries are locked
        self.assertEqual(self.s_api.patch(f'/api/logbooks/{lid}/', {'activities': 'x'}).status_code, 400)

    def test_rejection_requires_comment_and_resubmission_resets_reviews(self):
        lid = self.submit().data['id']
        self.assertEqual(self.a_api.post(f'/api/logbooks/{lid}/review/', {'decision': 'rejected'}).status_code, 400)
        self.i_api.post(f'/api/logbooks/{lid}/review/', {'decision': 'approved'})
        r = self.a_api.post(f'/api/logbooks/{lid}/review/', {'decision': 'rejected', 'comments': 'More detail'})
        self.assertEqual(r.data['status'], 'rejected')
        r = self.s_api.patch(f'/api/logbooks/{lid}/', {'activities': 'Configured routers and switches'})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['status'], 'submitted')
        self.assertTrue(all(rv['review_status'] == 'pending' for rv in r.data['reviews']))

    def test_rules(self):
        self.submit()
        self.assertIn('week_number', self.submit().data)  # duplicate week
        start = self.placement.start_date
        self.assertIn('end_date', self.submit(week=2, start_date=start, end_date=start + timedelta(days=9)).data)
        # a student without assigned supervisors cannot submit
        other = make_student()
        make_placement(other)
        r = self.client_for(other.user).post('/api/logbooks/', {'week_number': 1, 'start_date': TODAY,
                                                                'end_date': TODAY, 'activities': 'x'})
        self.assertEqual(r.status_code, 400)

    def test_access_is_restricted(self):
        lid = self.submit().data['id']
        stranger, *_ = make_attached_student()
        self.assertEqual(self.client_for(stranger.user).get(f'/api/logbooks/{lid}/').status_code, 404)
        _, _, other_academic, *_ = make_attached_student()
        r = self.client_for(other_academic.user).post(f'/api/logbooks/{lid}/review/', {'decision': 'approved'})
        self.assertEqual(r.status_code, 404)
        self.assertEqual(self.s_api.post(f'/api/logbooks/{lid}/review/', {'decision': 'approved'}).status_code, 403)
        self.assertEqual(len(self.client_for(make_admin()).get('/api/logbooks/').data), 1)


class AttendanceTests(ApiTestCase):
    def test_industrial_supervisor_records_attendance(self):
        student, _, academic, industrial, _ = make_attached_student()
        api = self.client_for(industrial.user)
        day = TODAY - timedelta(days=1)
        r = api.post('/api/attendance/bulk/', {'attendance_date': day, 'records': [
            {'student': student.pk, 'attendance_status': 'present'}]}, format='json')
        self.assertEqual(r.status_code, 200, r.data)
        # recording the same day again updates instead of duplicating
        api.post('/api/attendance/', {'student': student.pk, 'attendance_date': day, 'attendance_status': 'late'})
        self.assertEqual(Attendance.objects.get(student=student).attendance_status, 'late')
        self.assertEqual(api.post('/api/attendance/', {'student': student.pk, 'attendance_status': 'present',
                                                       'attendance_date': TODAY + timedelta(days=1)}).status_code, 400)
        self.assertEqual(len(self.client_for(student.user).get('/api/attendance/').data), 1)
        self.assertEqual(self.client_for(academic.user).post('/api/attendance/', {}).status_code, 403)
        other, *_ = make_attached_student()
        r = api.post('/api/attendance/', {'student': other.pk, 'attendance_date': day, 'attendance_status': 'present'})
        self.assertIn('student', r.data)
        self.assertEqual(Logbook.objects.count(), 0)
