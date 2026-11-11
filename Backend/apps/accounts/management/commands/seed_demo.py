"""python manage.py seed_demo [--password X] [--force]

Creates demonstration data for every role (development only): departments, organizations, an attachment
period, an administrator, supervisors, and students at different stages of the attachment process.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Department, Role, SystemSetting, User
from apps.announcements.models import Announcement
from apps.assessments.models import ACADEMIC_CRITERIA, WORKPLACE_CRITERIA, Assessment
from apps.logbooks.models import Attendance, Logbook, LogbookReview
from apps.organizations.models import Organization
from apps.placements.models import AttachmentPeriod, Placement
from apps.students.models import Student
from apps.supervisors.models import AcademicSupervisor, IndustrialSupervisor, SupervisorAssignment
from apps.visits.models import SupervisionVisit

DEPARTMENTS = [
    ('ICT', 'Information and Communication Technology'),
    ('BUS', 'Business Studies'),
    ('ELE', 'Electrical and Electronic Engineering'),
    ('HOS', 'Hospitality and Institutional Management'),
    ('ACC', 'Accounting and Finance'),
]

ORGANIZATIONS = [
    ('Nairobi Tech Solutions Ltd', 'Ngong Road, Nairobi', 'Nairobi', 'Grace Wanjiru', '0712000001',
     'hr@nairobitech.example', 'Information Technology'),
    ('Lakeview Hospitality Group', 'Lake Road, Naivasha', 'Nakuru', 'Peter Otieno', '0712000002',
     'careers@lakeview.example', 'Hospitality'),
    ('Kilimani Power Engineering', 'Industrial Area, Nairobi', 'Nairobi', 'Ann Mutua', '0712000003',
     'info@kilimanipower.example', 'Engineering'),
    ('Greenfield Accounting Partners', 'Moi Avenue, Mombasa', 'Mombasa', 'Hassan Ali', '0712000004',
     'office@greenfield.example', 'Finance'),
]

DEMO_USERNAMES = ['admin', 'akamau', 'mnjeri', 'jmwangi', 'lochieng', 'skiprop',
                  'bwekesa', 'cakinyi', 'dmutiso', 'eatieno', 'fnyambura']


class Command(BaseCommand):
    help = 'Create demonstration data for every role (development only).'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='Langata@2026', help='Password for every demo account.')
        parser.add_argument('--force', action='store_true', help='Delete existing demo accounts first.')

    @transaction.atomic
    def handle(self, *args, password, force, **options):
        if User.objects.filter(username__in=DEMO_USERNAMES).exists():
            if not force:
                raise CommandError('Demo data already exists. Use --force to recreate it.')
            User.objects.filter(username__in=DEMO_USERNAMES).delete()
            Organization.objects.filter(organization_name__in=[o[0] for o in ORGANIZATIONS]).delete()

        today = timezone.localdate()
        settings_row = SystemSetting.load()
        settings_row.required_logbook_weeks = 12
        settings_row.save()

        depts = {code: Department.objects.get_or_create(department_code=code, defaults={'department_name': name})[0]
                 for code, name in DEPARTMENTS}
        orgs = [Organization.objects.create(organization_name=n, address=a, county=c, contact_person=p,
                                            phone_number=t, email=e, industry_category=i)
                for n, a, c, p, t, e, i in ORGANIZATIONS]
        period, _ = AttachmentPeriod.objects.get_or_create(
            name=f'Attachment Period {today.year}', defaults={
                'start_date': today - timedelta(weeks=6), 'end_date': today + timedelta(weeks=6),
                'application_deadline': today + timedelta(weeks=2), 'report_deadline': today + timedelta(weeks=8)})

        def user(username, email, role, **extra):
            return User.objects.create_user(username=username, email=email, password=password, role=role, **extra)

        admin = user('admin', 'admin@langata.example', Role.ADMIN, is_staff=True, is_superuser=True)

        def academic(username, first, last, staff, dept):
            u = user(username, f'{username}@langata.example', Role.ACADEMIC)
            return AcademicSupervisor.objects.create(user=u, staff_number=staff, first_name=first, last_name=last,
                                                     phone_number='0722000100', department=depts[dept])

        def industrial(username, first, last, org, title):
            u = user(username, f'{username}@{org.email.split("@")[1]}', Role.INDUSTRIAL)
            return IndustrialSupervisor.objects.create(user=u, organization=org, first_name=first, last_name=last,
                                                       phone_number='0733000100', job_title=title,
                                                       employee_number=f'EMP-{username.upper()}')

        def student(username, first, last, reg, dept, year='Year 2'):
            u = user(username, f'{username}@students.langata.example', Role.STUDENT)
            return Student.objects.create(user=u, registration_number=reg, first_name=first, last_name=last,
                                          phone_number='0700000100', department=depts[dept], academic_year=year)

        aca1 = academic('akamau', 'Alice', 'Kamau', 'LTV/STAFF/001', 'ICT')
        aca2 = academic('mnjeri', 'Mary', 'Njeri', 'LTV/STAFF/002', 'HOS')
        ind1 = industrial('jmwangi', 'James', 'Mwangi', orgs[0], 'Systems Administrator')
        ind2 = industrial('lochieng', 'Lucy', 'Ochieng', orgs[1], 'Front Office Manager')
        industrial('skiprop', 'Samuel', 'Kiprop', orgs[2], 'Electrical Engineer')

        s1 = student('bwekesa', 'Brian', 'Wekesa', 'LTV/ICT/001/2024', 'ICT')
        s2 = student('cakinyi', 'Cynthia', 'Akinyi', 'LTV/HOS/014/2024', 'HOS')
        s3 = student('dmutiso', 'David', 'Mutiso', 'LTV/ELE/022/2024', 'ELE')
        s4 = student('eatieno', 'Esther', 'Atieno', 'LTV/ACC/031/2024', 'ACC')
        student('fnyambura', 'Faith', 'Nyambura', 'LTV/BUS/045/2024', 'BUS', 'Year 1')

        def approved(s, org, weeks_ago=6):
            return Placement.objects.create(
                student=s, organization=org, attachment_period=period, start_date=today - timedelta(weeks=weeks_ago),
                end_date=today + timedelta(weeks=12 - weeks_ago), application_status=Placement.Status.APPROVED,
                attachment_status=Placement.AttachmentStatus.ACTIVE, reviewed_by=admin, reviewed_at=timezone.now(),
                approval_comments='Approved.')

        # Brian: active attachment, supervisors assigned, logbooks at various review stages, visit, assessments.
        p1 = approved(s1, orgs[0])
        SupervisorAssignment.objects.create(placement=p1, student=s1, academic_supervisor=aca1,
                                            industrial_supervisor=ind1, assigned_by=admin)
        for week in range(1, 6):
            start = p1.start_date + timedelta(weeks=week - 1)
            lb = Logbook.objects.create(
                student=s1, placement=p1, week_number=week, start_date=start, end_date=start + timedelta(days=4),
                activities=f'Week {week}: supported the help desk, configured user accounts and documented network '
                           'issues.', skills_acquired='Active Directory, network troubleshooting',
                challenges='Slow ticket system.' if week % 2 else '', solutions='Prioritised tickets by impact.',
                submission_date=timezone.now() - timedelta(weeks=6 - week))
            a_status = (LogbookReview.Status.APPROVED if week <= 3 else
                        LogbookReview.Status.REJECTED if week == 4 else LogbookReview.Status.PENDING)
            i_status = LogbookReview.Status.APPROVED if week <= 4 else LogbookReview.Status.PENDING
            LogbookReview.objects.create(logbook=lb, supervisor=aca1.user, supervisor_role=Role.ACADEMIC,
                                         review_status=a_status, review_date=timezone.now() if week <= 4 else None,
                                         comments='Add more detail on the skills you used.' if week == 4 else 'Good.')
            LogbookReview.objects.create(logbook=lb, supervisor=ind1.user, supervisor_role=Role.INDUSTRIAL,
                                         review_status=i_status, review_date=timezone.now() if week <= 4 else None,
                                         comments='Well done.' if week <= 4 else '')
            lb.refresh_status()
        for d in range(1, 11):
            day = today - timedelta(days=d)
            if day.weekday() < 5:
                Attendance.objects.create(student=s1, attendance_date=day, recorded_by=ind1.user,
                                          attendance_status='late' if d == 3 else 'present')
        SupervisionVisit.objects.create(
            student=s1, academic_supervisor=aca1, organization=orgs[0], created_by=aca1.user,
            visit_date=timezone.now() - timedelta(days=10), visit_type='physical',
            objectives='Confirm placement suitability and review progress.', visit_status='completed',
            observations='Student is well integrated in the IT team.', recommendations='Rotate to the networks unit.')
        SupervisionVisit.objects.create(
            student=s1, academic_supervisor=aca1, organization=orgs[0], created_by=aca1.user,
            visit_date=timezone.now() + timedelta(days=14), visit_type='virtual',
            meeting_link='https://meet.example.com/langata-visit', objectives='Mid-attachment review.')
        scores = {c: 4 for c in WORKPLACE_CRITERIA}
        Assessment.objects.create(student=s1, placement=p1, supervisor=ind1.user, supervisor_role=Role.INDUSTRIAL,
                                  assessment_type='workplace', assessment_criteria=scores,
                                  marks=Assessment.compute_marks(scores), comments='Reliable and eager to learn.',
                                  assessment_status=Assessment.Status.COMPLETED)
        scores = {c: 3 for c in ACADEMIC_CRITERIA}
        Assessment.objects.create(student=s1, placement=p1, supervisor=aca1.user, supervisor_role=Role.ACADEMIC,
                                  assessment_type='academic', assessment_criteria=scores,
                                  marks=Assessment.compute_marks(scores), assessment_status=Assessment.Status.IN_PROGRESS)

        # Cynthia: approved and assigned, just starting.
        p2 = approved(s2, orgs[1], weeks_ago=1)
        SupervisorAssignment.objects.create(placement=p2, student=s2, academic_supervisor=aca2,
                                            industrial_supervisor=ind2, assigned_by=admin)

        # David: approved but no supervisors yet. Esther: pending application. Faith: nothing yet.
        approved(s3, orgs[2], weeks_ago=0)
        Placement.objects.create(student=s4, organization=orgs[3], attachment_period=period,
                                 start_date=today + timedelta(days=7), end_date=today + timedelta(weeks=13))

        Announcement.objects.create(administrator=admin, title='Welcome to the attachment portal',
                                    message='Submit your placement details before the application deadline.')
        Announcement.objects.create(administrator=admin, title='Logbook reminder', target_audience='student',
                                    message='Weekly logbooks must be submitted every Friday.')
        Announcement.objects.create(administrator=admin, title='Supervision visits', target_audience='academic',
                                    message='Please schedule at least one visit per student before mid-term.')

        self.stdout.write(self.style.SUCCESS('Demo data created.'))
        self.stdout.write(f'Password for every account: {password}')
        for row in ['admin (administrator)', 'akamau, mnjeri (academic supervisors)',
                    'jmwangi, lochieng, skiprop (industrial supervisors)',
                    'bwekesa, cakinyi, dmutiso, eatieno, fnyambura (students)']:
            self.stdout.write(f'  {row}')
