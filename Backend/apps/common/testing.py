"""Factories shared by the test suites."""
from datetime import timedelta
from itertools import count

from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import Department, Role, User
from apps.organizations.models import Organization
from apps.placements.models import Placement
from apps.students.models import Student
from apps.supervisors.models import AcademicSupervisor, IndustrialSupervisor, SupervisorAssignment

PASSWORD = 'Str0ng-pass-123'
_seq = count(1)


def make_department(code=None):
    n = next(_seq)
    return Department.objects.create(department_code=code or f'D{n}', department_name=f'Department {n}')


def make_organization(**kw):
    n = next(_seq)
    data = dict(organization_name=f'Org {n}', address='Street 1', county='Nairobi', contact_person='HR',
                phone_number='0700', email=f'org{n}@example.com', industry_category='IT')
    data.update(kw)
    return Organization.objects.create(**data)


def make_user(role, **kw):
    n = next(_seq)
    return User.objects.create_user(username=kw.pop('username', f'{role}{n}'), email=f'{role}{n}@example.com',
                                    password=PASSWORD, role=role, **kw)


def make_admin():
    return make_user(Role.ADMIN)


def make_student(department=None):
    u = make_user(Role.STUDENT)
    return Student.objects.create(user=u, registration_number=f'REG/{u.pk}', first_name='Stu', last_name=str(u.pk),
                                  department=department or make_department(), academic_year='Year 2')


def make_academic(department=None):
    u = make_user(Role.ACADEMIC)
    return AcademicSupervisor.objects.create(user=u, staff_number=f'STAFF{u.pk}', first_name='Aca',
                                             last_name=str(u.pk), department=department or make_department())


def make_industrial(organization=None):
    u = make_user(Role.INDUSTRIAL)
    return IndustrialSupervisor.objects.create(user=u, organization=organization or make_organization(),
                                               first_name='Ind', last_name=str(u.pk), job_title='Manager')


def make_placement(student, organization=None, status=Placement.Status.APPROVED, **kw):
    today = timezone.localdate()
    return Placement.objects.create(student=student, organization=organization or make_organization(),
                                    start_date=kw.pop('start_date', today - timedelta(days=14)),
                                    end_date=kw.pop('end_date', today + timedelta(days=60)),
                                    application_status=status, **kw)


def make_attached_student():
    """A student with an approved placement and both supervisors assigned."""
    student = make_student()
    org = make_organization()
    placement = make_placement(student, org)
    academic = make_academic()
    industrial = make_industrial(org)
    assignment = SupervisorAssignment.objects.create(placement=placement, student=student,
                                                     academic_supervisor=academic, industrial_supervisor=industrial)
    return student, placement, academic, industrial, assignment


class ApiTestCase(APITestCase):
    def client_for(self, user):
        c = APIClient()
        c.force_authenticate(user)
        return c
