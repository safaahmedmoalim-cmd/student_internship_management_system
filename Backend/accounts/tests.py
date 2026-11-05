from django.core.cache import cache
from django.test import override_settings
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from .models import Role, User

PASSWORD = 'S3cure-pass!'


def make_user(role, email, **extra):
    extra.setdefault('name', email.split('@')[0].replace('.', ' ').title() + ' Tester')
    if role == Role.STUDENT:
        extra.setdefault('adm_no', 'LC/T/' + email.split('@')[0])
        extra.setdefault('course', 'Diploma in ICT')
        extra.setdefault('year', 'Year 2')
    return User.objects.create_user(email, PASSWORD, role=role, **extra)


def student_payload(**over):
    data = {'role': 'student', 'name': 'Test Student', 'email': 'ts@example.com', 'phone': '0700 000 000',
            'adm_no': 'LC/2024/0999', 'course': 'Diploma in ICT', 'year': 'Year 1',
            'password': PASSWORD, 'confirm_password': PASSWORD}
    data.update(over)
    return data


class AuthTests(APITestCase):
    def setUp(self):
        cache.clear()                     # the login/register throttle keeps its counters in the cache

    # ------------------------------------------------------------------ sign up
    def test_student_can_register_and_gets_a_token(self):
        res = self.client.post('/api/auth/register/', student_payload())
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['user']['role'], 'student')
        self.assertEqual(res.data['user']['adm_no'], 'LC/2024/0999')
        self.assertNotIn('password', res.data['user'])
        user = User.objects.get(email='ts@example.com')
        self.assertTrue(user.check_password(PASSWORD))
        self.assertNotEqual(user.password, PASSWORD)                  # stored hashed
        self.assertTrue(Token.objects.filter(user=user, key=res.data['token']).exists())

    def test_each_role_needs_its_own_details(self):
        res = self.client.post('/api/auth/register/', student_payload(adm_no=''))
        self.assertEqual(res.status_code, 400)
        self.assertIn('adm_no', res.data)

        res = self.client.post('/api/auth/register/', {
            'role': 'industrial', 'name': 'Ind Person', 'email': 'ip@example.com',
            'password': PASSWORD, 'confirm_password': PASSWORD})
        self.assertEqual(res.status_code, 400)
        self.assertIn('company', res.data)

        res = self.client.post('/api/auth/register/', {
            'role': 'academic', 'name': 'Acad Person', 'email': 'ap@example.com', 'staff_no': 'A-1',
            'department': 'ICT', 'password': PASSWORD, 'confirm_password': PASSWORD})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['user']['department'], 'ICT')

    def test_duplicate_email_is_rejected_case_insensitively(self):
        self.client.post('/api/auth/register/', student_payload())
        res = self.client.post('/api/auth/register/', student_payload(email='TS@Example.com', adm_no='LC/2024/1000'))
        self.assertEqual(res.status_code, 400)
        self.assertIn('email', res.data)

    def test_duplicate_admission_number_is_rejected(self):
        self.client.post('/api/auth/register/', student_payload())
        res = self.client.post('/api/auth/register/', student_payload(email='other@example.com'))
        self.assertEqual(res.status_code, 400)
        self.assertIn('adm_no', res.data)

    def test_passwords_must_match_and_be_strong(self):
        res = self.client.post('/api/auth/register/', student_payload(confirm_password='different-pass1'))
        self.assertEqual(res.status_code, 400)
        self.assertIn('confirm_password', res.data)
        res = self.client.post('/api/auth/register/', student_payload(password='12345', confirm_password='12345'))
        self.assertEqual(res.status_code, 400)
        self.assertIn('password', res.data)

    @override_settings(COORDINATOR_ACCESS_CODE='TEST-CODE')
    def test_coordinator_needs_the_access_code(self):
        body = {'role': 'coordinator', 'name': 'Co Ordinator', 'email': 'co@example.com', 'staff_no': 'C-9',
                'password': PASSWORD, 'confirm_password': PASSWORD}
        res = self.client.post('/api/auth/register/', {**body, 'access_code': 'wrong'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('access_code', res.data)
        res = self.client.post('/api/auth/register/', {**body, 'access_code': 'TEST-CODE'})
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['user']['role'], 'coordinator')

    @override_settings(COORDINATOR_ACCESS_CODE='')
    def test_coordinator_signup_can_be_disabled(self):
        res = self.client.post('/api/auth/register/', {
            'role': 'coordinator', 'name': 'Co Ordinator', 'email': 'co@example.com', 'staff_no': 'C-9',
            'access_code': '', 'password': PASSWORD, 'confirm_password': PASSWORD})
        self.assertEqual(res.status_code, 400)

    # ------------------------------------------------------------------ login
    def test_login_success_and_failures(self):
        make_user(Role.STUDENT, 'amina@example.com')
        res = self.client.post('/api/auth/login/', {'email': 'Amina@Example.com', 'password': PASSWORD})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn('token', res.data)
        self.assertEqual(res.data['user']['email'], 'amina@example.com')

        res = self.client.post('/api/auth/login/', {'email': 'amina@example.com', 'password': 'wrong-password'})
        self.assertEqual(res.status_code, 400)

    def test_login_checks_the_chosen_role(self):
        make_user(Role.STUDENT, 'amina@example.com')
        res = self.client.post('/api/auth/login/', {'email': 'amina@example.com', 'password': PASSWORD,
                                                    'role': 'academic'})
        self.assertEqual(res.status_code, 400)
        res = self.client.post('/api/auth/login/', {'email': 'amina@example.com', 'password': PASSWORD,
                                                    'role': 'student'})
        self.assertEqual(res.status_code, 200)

    def test_disabled_account_cannot_log_in(self):
        user = make_user(Role.STUDENT, 'amina@example.com')
        user.is_active = False
        user.save()
        res = self.client.post('/api/auth/login/', {'email': 'amina@example.com', 'password': PASSWORD})
        self.assertEqual(res.status_code, 400)

    # ------------------------------------------------------------------ session
    def _login(self, email):
        res = self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD})
        self.assertEqual(res.status_code, 200, res.data)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Token ' + res.data['token'])
        return client, res.data['token']

    def test_protected_endpoints_need_a_token(self):
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 401)
        self.assertEqual(self.client.get('/api/dashboard/').status_code, 401)
        self.assertEqual(self.client.get('/api/placements/').status_code, 401)

    def test_me_returns_and_updates_the_profile(self):
        make_user(Role.STUDENT, 'amina@example.com', adm_no='LC/T/1')
        client, _ = self._login('amina@example.com')
        res = client.get('/api/auth/me/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['adm_no'], 'LC/T/1')

        res = client.patch('/api/auth/me/', {'name': 'Amina Hassan', 'phone': '0799 111 222',
                                             'adm_no': 'LC/HACKED/1', 'role': 'coordinator', 'company': 'Nope'})
        self.assertEqual(res.status_code, 200, res.data)
        user = User.objects.get(email='amina@example.com')
        self.assertEqual(user.name, 'Amina Hassan')
        self.assertEqual(user.phone, '0799 111 222')
        self.assertEqual(user.adm_no, 'LC/T/1')              # identity fields cannot be edited
        self.assertEqual(user.role, Role.STUDENT)
        self.assertEqual(user.company, '')                    # fields of another role are ignored

    def test_logout_invalidates_the_token(self):
        make_user(Role.STUDENT, 'amina@example.com')
        client, _ = self._login('amina@example.com')
        self.assertEqual(client.post('/api/auth/logout/').status_code, 204)
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)

    def test_change_password(self):
        make_user(Role.STUDENT, 'amina@example.com')
        client, old_token = self._login('amina@example.com')

        res = client.post('/api/auth/change-password/', {'current_password': 'nope-nope-1', 'new_password': 'N3w-pass-word',
                                                         'confirm_password': 'N3w-pass-word'})
        self.assertEqual(res.status_code, 400)
        self.assertIn('current_password', res.data)

        res = client.post('/api/auth/change-password/', {'current_password': PASSWORD, 'new_password': 'N3w-pass-word',
                                                         'confirm_password': 'N3w-pass-word'})
        self.assertEqual(res.status_code, 200, res.data)
        self.assertNotEqual(res.data['token'], old_token)
        self.assertEqual(client.get('/api/auth/me/').status_code, 401)        # the old token stopped working
        fresh = APIClient()
        fresh.credentials(HTTP_AUTHORIZATION='Token ' + res.data['token'])
        self.assertEqual(fresh.get('/api/auth/me/').status_code, 200)
        self.assertEqual(self.client.post('/api/auth/login/', {'email': 'amina@example.com',
                                                               'password': 'N3w-pass-word'}).status_code, 200)

    # ------------------------------------------------------------------ supervisor lists
    def test_supervisor_lists_depend_on_the_caller(self):
        make_user(Role.ACADEMIC, 'acad@example.com', staff_no='A1', department='ICT')
        make_user(Role.INDUSTRIAL, 'ind@example.com', company='Acme', position='Manager', company_location='Nairobi')
        student = make_user(Role.STUDENT, 'amina@example.com')
        coordinator = make_user(Role.COORDINATOR, 'coord@example.com', staff_no='C1')

        client = APIClient()
        client.force_authenticate(student)
        res = client.get('/api/supervisors/')
        self.assertEqual([u['email'] for u in res.data], ['ind@example.com'])      # students only need industrial ones

        client.force_authenticate(coordinator)
        self.assertEqual(len(client.get('/api/supervisors/').data), 2)
        self.assertEqual([u['email'] for u in client.get('/api/supervisors/?role=academic').data], ['acad@example.com'])
