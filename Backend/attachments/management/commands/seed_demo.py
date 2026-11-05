"""python manage.py seed_demo [--force] [--password demo1234]

Creates the same demo accounts and records the frontend ships with, so the portal can be tried straight away.
DEVELOPMENT ONLY - never run this against a real installation.
"""
import datetime as dt

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from accounts.models import Role, User
from attachments.constants import CRITERIA
from attachments.models import (
    Announcement, ApprovalStatus, Assessment, LogbookEntry, Placement, Visit,
)

DEMO_EMAILS = [
    'coordinator@langata.ac.ke', 'academic@langata.ac.ke', 'industrial@langata.ac.ke',
    'student@langata.ac.ke', 'brian@langata.ac.ke', 'grace@langata.ac.ke',
]
ANNOUNCEMENTS = [
    ('Final reports deadline',
     'Final attachment reports must be submitted through the portal by the end of the attachment period.'),
    ('Weekly logbooks',
     'Remember to submit your logbook every week so your industrial supervisor can approve it on time.'),
]
# week -> (activities, skills, industrial comment, academic comment, status)
AMINA_WEEKS = [
    ('Orientation, office tour and introduction to the IT support team. Set up workstation and company email.',
     'Ticketing system, basic helpdesk etiquette', 'Good start.', '', ApprovalStatus.APPROVED),
    ('Handled first-line support tickets: password resets, printer faults and software installs under supervision.',
     'Troubleshooting, documentation of fixes', 'Keep documenting each fix.',
     'Well written. Add more detail on tools used.', ApprovalStatus.APPROVED),
    ('Assisted in configuring five new laptops and joining them to the company network.',
     'Network setup, imaging, asset tagging', 'Excellent initiative this week.', '', ApprovalStatus.APPROVED),
    ('Helped back up the file server and tested restore of selected folders. Started inventory of network cabling.',
     'Backup and recovery basics', '', '', ApprovalStatus.PENDING),
]


class Command(BaseCommand):
    help = 'Create the demo accounts and sample records used by the frontend (development only).'

    def add_arguments(self, parser):
        parser.add_argument('--password', default='demo1234', help='password for every demo account')
        parser.add_argument('--force', action='store_true',
                            help='delete the existing demo accounts (and their records) and create them again')

    @transaction.atomic
    def handle(self, *args, **options):
        existing = User.objects.filter(email__in=DEMO_EMAILS)
        if existing.exists():
            if not options['force']:
                raise CommandError('The demo accounts already exist. Run with --force to recreate them.')
            existing.delete()                      # cascades to their placements, logbooks, reports, visits...
            Announcement.objects.filter(title__in=[t for t, _ in ANNOUNCEMENTS]).delete()

        pw = options['password']
        now = timezone.now()

        coord = User.objects.create_user('coordinator@langata.ac.ke', pw, role=Role.COORDINATOR, name='Mary Wanjiku',
                                         phone='0711 000 001', staff_no='LC-C-001')
        acad = User.objects.create_user('academic@langata.ac.ke', pw, role=Role.ACADEMIC, name='Dr. Peter Otieno',
                                        phone='0711 000 002', staff_no='LC-A-014',
                                        department='Information & Communication Technology')
        ind = User.objects.create_user('industrial@langata.ac.ke', pw, role=Role.INDUSTRIAL, name='James Mwangi',
                                       phone='0711 000 003', company='Savannah Tech Ltd',
                                       position='IT Operations Manager', company_location='Westlands, Nairobi')
        amina = User.objects.create_user('student@langata.ac.ke', pw, role=Role.STUDENT, name='Amina Hassan',
                                         phone='0711 000 004', adm_no='LC/2024/0101', course='Diploma in ICT',
                                         year='Year 2', academic_supervisor=acad, industrial_supervisor=ind)
        brian = User.objects.create_user('brian@langata.ac.ke', pw, role=Role.STUDENT, name='Brian Kiptoo',
                                         phone='0711 000 005', adm_no='LC/2024/0102',
                                         course='Diploma in Business Management', year='Year 2',
                                         academic_supervisor=acad)
        User.objects.create_user('grace@langata.ac.ke', pw, role=Role.STUDENT, name='Grace Achieng',
                                 phone='0711 000 006', adm_no='LC/2024/0103', course='Diploma in Accounting',
                                 year='Year 2')

        # Placements: Amina approved, Brian waiting for the coordinator, Grace has none yet.
        Placement.objects.create(student=amina, company='Savannah Tech Ltd', location='Westlands, Nairobi',
                                 department='IT Support', start_date=dt.date(2026, 9, 1),
                                 end_date=dt.date(2026, 11, 6), industrial_supervisor=ind,
                                 status=ApprovalStatus.APPROVED, decided_by=coord, decided_at=now)
        Placement.objects.create(student=brian, company='Savannah Tech Ltd', location='Westlands, Nairobi',
                                 department='Accounts', start_date=dt.date(2026, 9, 7),
                                 end_date=dt.date(2026, 11, 13), industrial_supervisor=ind,
                                 status=ApprovalStatus.PENDING)

        # Amina's first four logbook weeks.
        for i, (activities, skills, ind_comment, acad_comment, status) in enumerate(AMINA_WEEKS):
            LogbookEntry.objects.create(
                student=amina, week_no=i + 1, week_start=dt.date(2026, 9, 1) + dt.timedelta(days=7 * i),
                hours_worked=40, activities=activities, skills_learned=skills, status=status,
                industrial_comment=ind_comment, academic_comment=acad_comment,
                reviewed_at=now if status == ApprovalStatus.APPROVED else None)

        # Industrial evaluation: ratings 5,4,4,4,4 -> 21 / 25 = 84 %
        Assessment.objects.create(
            student=amina, assessor=ind, assessor_role=Role.INDUSTRIAL, assessment_type='Industrial evaluation',
            marks=84, ratings=dict(zip(CRITERIA, [5, 4, 4, 4, 4])), comment='Reliable and eager to learn.')

        Visit.objects.create(student=amina, academic=acad, visit_date=timezone.localdate() + dt.timedelta(days=12),
                             mode=Visit.Mode.PHYSICAL, notes='Mid-attachment visit and logbook check.')

        for title, body in ANNOUNCEMENTS:
            Announcement.objects.create(title=title, body=body, author=coord)

        self.stdout.write(self.style.SUCCESS('Demo data created. Sign in with any of these (password: %s):' % pw))
        for email in DEMO_EMAILS:
            self.stdout.write('  ' + email)
