from django.core import mail
from rest_framework.test import APIClient

from apps.common.testing import PASSWORD, ApiTestCase, make_admin, make_department, make_student

from .models import AuditLog, Role, SystemSetting, User


class AuthenticationTests(ApiTestCase):
    def setUp(self):
        self.dept = make_department()
        self.client = APIClient()

    def register(self, **over):
        data = {'username': 'jdoe', 'email': 'JDoe@Example.com', 'password': PASSWORD, 'confirm_password': PASSWORD,
                'registration_number': 'ltv/ict/1/2025', 'first_name': 'Jane', 'last_name': 'Doe',
                'phone_number': '0711', 'department': self.dept.pk, 'academic_year': 'Year 1'}
        data.update(over)
        return self.client.post('/api/auth/register/', data)

    def test_student_registration_returns_jwt_and_profile(self):
        r = self.register()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIn('access', r.data)
        self.assertEqual(r.data['user']['role'], Role.STUDENT)
        self.assertEqual(r.data['user']['email'], 'jdoe@example.com')
        self.assertEqual(r.data['user']['profile']['registration_number'], 'LTV/ICT/1/2025')
        me = self.client.get('/api/auth/me/', HTTP_AUTHORIZATION=f'Bearer {r.data["access"]}')
        self.assertEqual(me.status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action='user.register').exists())

    def test_registration_rejects_duplicates_and_mismatched_passwords(self):
        self.register()
        r = self.register(username='other', email='other@example.com')
        self.assertIn('registration_number', r.data)
        r = self.register(username='x2', email='x2@example.com', registration_number='NEW/1', confirm_password='nope')
        self.assertIn('confirm_password', r.data)

    def test_registration_can_be_closed(self):
        s = SystemSetting.load()
        s.allow_student_registration = False
        s.save()
        self.assertEqual(self.register().status_code, 400)

    def test_login_with_username_or_email_and_logout_blacklists_refresh(self):
        self.register()
        for login in ('jdoe', 'jdoe@example.com'):
            r = self.client.post('/api/auth/login/', {'username': login, 'password': PASSWORD})
            self.assertEqual(r.status_code, 200, r.data)
        refresh = r.data['refresh']
        auth = {'HTTP_AUTHORIZATION': f'Bearer {r.data["access"]}'}
        self.assertEqual(self.client.post('/api/auth/logout/', {'refresh': refresh}, **auth).status_code, 204)
        self.assertEqual(self.client.post('/api/auth/refresh/', {'refresh': refresh}).status_code, 401)

    def test_wrong_password_and_inactive_account_cannot_log_in(self):
        self.register()
        self.assertEqual(self.client.post('/api/auth/login/', {'username': 'jdoe', 'password': 'bad'}).status_code, 400)
        User.objects.filter(username='jdoe').update(is_active=False)
        self.assertEqual(self.client.post('/api/auth/login/', {'username': 'jdoe', 'password': PASSWORD}).status_code, 400)
        self.assertTrue(AuditLog.objects.filter(action='auth.login_failed').exists())

    def test_password_reset_flow(self):
        self.register()
        r = self.client.post('/api/auth/password-reset/', {'email': 'jdoe@example.com'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        link = [w for w in mail.outbox[0].body.split() if 'reset-password' in w][0]
        query = dict(p.split('=') for p in link.split('?')[1].split('&'))
        new = 'An0ther-pass-456'
        r = self.client.post('/api/auth/password-reset/confirm/', {**query, 'new_password': new, 'confirm_password': new})
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(self.client.post('/api/auth/login/', {'username': 'jdoe', 'password': new}).status_code, 200)
        # the link is single-use
        r = self.client.post('/api/auth/password-reset/confirm/', {**query, 'new_password': new, 'confirm_password': new})
        self.assertEqual(r.status_code, 400)

    def test_profile_update_only_changes_allowed_fields(self):
        student = make_student()
        c = self.client_for(student.user)
        r = c.patch('/api/auth/me/', {'first_name': 'Changed', 'registration_number': 'HACK'})
        self.assertEqual(r.status_code, 200)
        student.refresh_from_db()
        self.assertEqual(student.first_name, 'Changed')
        self.assertNotEqual(student.registration_number, 'HACK')


class UserManagementTests(ApiTestCase):
    def setUp(self):
        self.admin = make_admin()
        self.api = self.client_for(self.admin)
        self.dept = make_department()

    def test_admin_creates_supervisor_with_generated_password(self):
        r = self.api.post('/api/users/', {
            'username': 'lect1', 'email': 'lect1@example.com', 'role': 'academic',
            'profile': {'staff_number': 's-1', 'first_name': 'Lec', 'last_name': 'Turer', 'department': self.dept.pk}},
            format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data['profile']['staff_number'], 'S-1')
        pw = r.data['temporary_password']
        self.assertTrue(APIClient().post('/api/auth/login/', {'username': 'lect1', 'password': pw}).status_code == 200)

    def test_profile_required_and_role_locked(self):
        r = self.api.post('/api/users/', {'username': 'x', 'email': 'x@example.com', 'role': 'student'}, format='json')
        self.assertIn('profile', r.data)
        student = make_student()
        r = self.api.patch(f'/api/users/{student.user.pk}/', {'role': 'admin'}, format='json')
        self.assertIn('role', r.data)

    def test_deactivate_and_reset_password(self):
        student = make_student()
        r = self.api.post(f'/api/users/{student.user.pk}/deactivate/')
        self.assertFalse(r.data['is_active'])
        self.assertEqual(self.api.post(f'/api/users/{self.admin.pk}/deactivate/').status_code, 400)
        r = self.api.post(f'/api/users/{student.user.pk}/reset-password/', {})
        self.assertTrue(r.data['temporary_password'])

    def test_only_admin_manages_users_departments_settings_and_audit(self):
        c = self.client_for(make_student().user)
        self.assertEqual(c.get('/api/users/').status_code, 403)
        self.assertEqual(c.post('/api/departments/', {'department_name': 'X', 'department_code': 'X'}).status_code, 403)
        self.assertEqual(c.get('/api/audit-logs/').status_code, 403)
        self.assertEqual(c.patch('/api/settings/', {'required_logbook_weeks': 1}).status_code, 403)
        self.assertEqual(APIClient().get('/api/departments/').status_code, 200)  # public, for registration
        self.assertEqual(self.api.patch('/api/settings/', {'required_logbook_weeks': 10}).data['required_logbook_weeks'], 10)
