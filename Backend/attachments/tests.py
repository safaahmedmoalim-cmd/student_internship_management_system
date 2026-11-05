import datetime as dt
import shutil
import tempfile

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from rest_framework.test import APIClient, APITestCase

from accounts.models import Role, User

from .constants import CRITERIA
from .models import (
    Announcement, ApprovalStatus, Assessment, FinalReport, LogbookEntry, Placement, Visit,
)

PASSWORD = 'S3cure-pass!'


def make_user(role, email, **extra):
    extra.setdefault('name', email.split('@')[0].title())
    if role == Role.STUDENT:
        extra.setdefault('adm_no', 'LC/T/' + email.split('@')[0])
        extra.setdefault('course', 'Diploma in ICT')
        extra.setdefault('year', 'Year 2')
    return User.objects.create_user(email, PASSWORD, role=role, **extra)


def client_for(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def week_payload(week=1, **over):
    data = {'week_no': week, 'week_start': '2026-09-01', 'hours_worked': 40,
            'activities': 'Helpdesk tickets and laptop set-up.', 'skills_learned': 'Troubleshooting'}
    data.update(over)
    return data


def placement_payload(**over):
    data = {'company': 'Savannah Tech Ltd', 'location': 'Westlands', 'department': 'IT Support',
            'start_date': '2026-09-01', 'end_date': '2026-11-06'}
    data.update(over)
    return data


class BaseCase(APITestCase):
    """Creates one user of every role plus a second student, and a temporary MEDIA_ROOT."""

    def setUp(self):
        cache.clear()
        media = tempfile.mkdtemp()
        override = override_settings(MEDIA_ROOT=media)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)

        self.coord = make_user(Role.COORDINATOR, 'coord@example.com', staff_no='C1')
        self.acad = make_user(Role.ACADEMIC, 'acad@example.com', staff_no='A1', department='ICT')
        self.other_acad = make_user(Role.ACADEMIC, 'acad2@example.com', staff_no='A2', department='ICT')
        self.ind = make_user(Role.INDUSTRIAL, 'ind@example.com', company='Acme', position='Manager',
                             company_location='Nairobi')
        self.other_ind = make_user(Role.INDUSTRIAL, 'ind2@example.com', company='Beta', position='Lead',
                                   company_location='Nairobi')
        self.amina = make_user(Role.STUDENT, 'amina@example.com',
                               academic_supervisor=self.acad, industrial_supervisor=self.ind)
        self.brian = make_user(Role.STUDENT, 'brian@example.com')          # nobody assigned

        self.c_coord = client_for(self.coord)
        self.c_acad = client_for(self.acad)
        self.c_other_acad = client_for(self.other_acad)
        self.c_ind = client_for(self.ind)
        self.c_other_ind = client_for(self.other_ind)
        self.c_amina = client_for(self.amina)
        self.c_brian = client_for(self.brian)

    def approved_placement(self, student=None, **extra):
        return Placement.objects.create(student=student or self.amina, company='Acme', location='Nairobi',
                                        department='IT', start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 11, 6),
                                        status=ApprovalStatus.APPROVED, **extra)

    def entry(self, week, status=ApprovalStatus.PENDING, hours=40, student=None):
        return LogbookEntry.objects.create(student=student or self.amina, week_no=week,
                                           week_start=dt.date(2026, 9, 1) + dt.timedelta(days=7 * (week - 1)),
                                           hours_worked=hours, activities='Work', status=status)


# =============================================================================
class PlacementTests(BaseCase):
    def test_student_submits_a_placement(self):
        res = self.c_amina.post('/api/placements/', placement_payload(), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['status'], 'pending')
        self.assertEqual(res.data['student'], self.amina.pk)

    def test_student_cannot_pick_the_status_or_the_student(self):
        res = self.c_amina.post('/api/placements/', placement_payload(status='approved', student=self.brian.pk),
                                format='json')
        self.assertEqual(res.status_code, 201, res.data)
        placement = Placement.objects.get()
        self.assertEqual(placement.status, ApprovalStatus.PENDING)
        self.assertEqual(placement.student_id, self.amina.pk)

    def test_only_one_placement_per_student(self):
        self.c_amina.post('/api/placements/', placement_payload(), format='json')
        res = self.c_amina.post('/api/placements/', placement_payload(), format='json')
        self.assertEqual(res.status_code, 400)

    def test_end_date_must_follow_start_date(self):
        res = self.c_amina.post('/api/placements/', placement_payload(end_date='2026-08-01'), format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('end_date', res.data)

    def test_supervisors_cannot_submit_placements(self):
        self.assertEqual(self.c_acad.post('/api/placements/', placement_payload(), format='json').status_code, 403)
        self.assertEqual(self.c_coord.post('/api/placements/', placement_payload(), format='json').status_code, 403)

    def test_coordinator_approves_and_the_industrial_supervisor_is_attached(self):
        self.brian.industrial_supervisor = None
        self.brian.save()
        self.c_brian.post('/api/placements/', placement_payload(industrial_supervisor=self.ind.pk), format='json')
        pid = Placement.objects.get(student=self.brian).pk
        res = self.c_coord.post(f'/api/placements/{pid}/approve/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['status'], 'approved')
        self.brian.refresh_from_db()
        self.assertEqual(self.brian.industrial_supervisor_id, self.ind.pk)
        # a second decision is refused
        self.assertEqual(self.c_coord.post(f'/api/placements/{pid}/approve/').status_code, 400)

    def test_reject_needs_a_reason_and_the_student_sees_it(self):
        self.c_amina.post('/api/placements/', placement_payload(), format='json')
        pid = Placement.objects.get().pk
        self.assertEqual(self.c_coord.post(f'/api/placements/{pid}/reject/', {}, format='json').status_code, 400)
        res = self.c_coord.post(f'/api/placements/{pid}/reject/', {'comment': 'Company not accredited'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['status'], 'rejected')
        mine = self.c_amina.get('/api/placements/').data
        self.assertEqual(mine[0]['coordinator_comment'], 'Company not accredited')

    def test_only_the_coordinator_decides(self):
        self.c_amina.post('/api/placements/', placement_payload(), format='json')
        pid = Placement.objects.get().pk
        for client in (self.c_amina, self.c_acad, self.c_ind):
            self.assertEqual(client.post(f'/api/placements/{pid}/approve/').status_code, 403)

    def test_visibility_of_placements(self):
        self.approved_placement(self.amina)
        Placement.objects.create(student=self.brian, company='Other', location='X', department='Y',
                                 start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 11, 6))
        self.assertEqual(len(self.c_coord.get('/api/placements/').data), 2)
        self.assertEqual(len(self.c_amina.get('/api/placements/').data), 1)
        self.assertEqual(len(self.c_acad.get('/api/placements/').data), 1)          # only Amina is theirs
        self.assertEqual(len(self.c_other_acad.get('/api/placements/').data), 0)
        self.assertEqual(len(self.c_coord.get('/api/placements/?status=pending').data), 1)

    def test_withdrawing_a_placement(self):
        self.c_amina.post('/api/placements/', placement_payload(), format='json')
        pid = Placement.objects.get().pk
        self.assertEqual(self.c_amina.delete(f'/api/placements/{pid}/').status_code, 204)
        self.approved_placement(self.amina)
        pid = Placement.objects.get().pk
        self.assertEqual(self.c_amina.delete(f'/api/placements/{pid}/').status_code, 400)       # approved: locked


# =============================================================================
class LogbookTests(BaseCase):
    def test_entries_need_an_approved_placement(self):
        res = self.c_amina.post('/api/logbook/', week_payload(), format='json')
        self.assertEqual(res.status_code, 400)
        Placement.objects.create(student=self.amina, company='A', location='B', department='C',
                                 start_date=dt.date(2026, 9, 1), end_date=dt.date(2026, 11, 6))       # still pending
        self.assertEqual(self.c_amina.post('/api/logbook/', week_payload(), format='json').status_code, 400)

    def test_student_adds_an_entry(self):
        self.approved_placement()
        res = self.c_amina.post('/api/logbook/', week_payload(), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['status'], 'pending')

    def test_week_must_be_unique_and_hours_in_range(self):
        self.approved_placement()
        self.assertEqual(self.c_amina.post('/api/logbook/', week_payload(1), format='json').status_code, 201)
        self.assertEqual(self.c_amina.post('/api/logbook/', week_payload(1), format='json').status_code, 400)
        self.assertEqual(self.c_amina.post('/api/logbook/', week_payload(2, hours_worked=0), format='json').status_code, 400)
        self.assertEqual(self.c_amina.post('/api/logbook/', week_payload(2, hours_worked=61), format='json').status_code, 400)
        self.assertEqual(self.c_amina.post('/api/logbook/', week_payload(31), format='json').status_code, 400)

    def test_student_cannot_set_the_status(self):
        self.approved_placement()
        res = self.c_amina.post('/api/logbook/', week_payload(status='approved', industrial_comment='fake'),
                                format='json')
        self.assertEqual(res.status_code, 201)
        entry = LogbookEntry.objects.get()
        self.assertEqual(entry.status, ApprovalStatus.PENDING)
        self.assertEqual(entry.industrial_comment, '')

    def test_industrial_supervisor_approves_and_rejects(self):
        e1, e2 = self.entry(1), self.entry(2)
        res = self.c_ind.post(f'/api/logbook/{e1.pk}/approve/', {'comment': 'Well done'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['status'], 'approved')
        self.assertEqual(res.data['industrial_comment'], 'Well done')
        self.assertEqual(self.c_ind.post(f'/api/logbook/{e1.pk}/approve/').status_code, 400)     # already decided

        self.assertEqual(self.c_ind.post(f'/api/logbook/{e2.pk}/reject/', {}, format='json').status_code, 400)
        res = self.c_ind.post(f'/api/logbook/{e2.pk}/reject/', {'comment': 'More detail please'}, format='json')
        self.assertEqual(res.data['status'], 'rejected')

    def test_approve_without_a_comment_gets_a_default(self):
        e = self.entry(1)
        res = self.c_ind.post(f'/api/logbook/{e.pk}/approve/', {}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['industrial_comment'], 'Approved.')

    def test_only_the_assigned_industrial_supervisor_may_review(self):
        e = self.entry(1)
        self.assertEqual(self.c_other_ind.post(f'/api/logbook/{e.pk}/approve/').status_code, 404)   # not visible
        self.assertEqual(self.c_acad.post(f'/api/logbook/{e.pk}/approve/').status_code, 403)
        self.assertEqual(self.c_amina.post(f'/api/logbook/{e.pk}/approve/').status_code, 403)
        self.assertEqual(self.c_coord.post(f'/api/logbook/{e.pk}/approve/').status_code, 403)

    def test_academic_supervisor_comments(self):
        e = self.entry(1)
        res = self.c_acad.post(f'/api/logbook/{e.pk}/comment/', {'comment': 'Add tools used.'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['academic_comment'], 'Add tools used.')
        self.assertEqual(self.c_other_acad.post(f'/api/logbook/{e.pk}/comment/', {'comment': 'x'},
                                                format='json').status_code, 404)
        self.assertEqual(self.c_ind.post(f'/api/logbook/{e.pk}/comment/', {'comment': 'x'},
                                         format='json').status_code, 403)

    def test_visibility_and_filters(self):
        self.entry(1, ApprovalStatus.APPROVED)
        self.entry(2)
        brian_entry = self.entry(1, student=self.brian)
        self.assertEqual(len(self.c_amina.get('/api/logbook/').data), 2)
        self.assertEqual(len(self.c_brian.get('/api/logbook/').data), 1)
        self.assertEqual(len(self.c_coord.get('/api/logbook/').data), 3)
        self.assertEqual(len(self.c_acad.get('/api/logbook/').data), 2)
        self.assertEqual(len(self.c_other_acad.get('/api/logbook/').data), 0)
        self.assertEqual(len(self.c_coord.get('/api/logbook/?status=pending').data), 2)
        self.assertEqual(len(self.c_coord.get(f'/api/logbook/?student={self.brian.pk}').data), 1)
        self.assertEqual(self.c_amina.get(f'/api/logbook/{brian_entry.pk}/').status_code, 404)

    def test_delete_rules(self):
        approved = self.entry(1, ApprovalStatus.APPROVED)
        pending = self.entry(2)
        self.assertEqual(self.c_amina.delete(f'/api/logbook/{approved.pk}/').status_code, 400)
        self.assertEqual(self.c_amina.delete(f'/api/logbook/{pending.pk}/').status_code, 204)
        self.assertEqual(self.c_acad.delete(f'/api/logbook/{approved.pk}/').status_code, 403)


# =============================================================================
class FinalReportTests(BaseCase):
    def upload(self, client, name='report.pdf', content=b'%PDF-1.4 test report', **over):
        data = {'title': 'My attachment report', 'summary': 'What I learned.',
                'file': SimpleUploadedFile(name, content, content_type='application/octet-stream')}
        data.update(over)
        return client.post('/api/final-reports/', data, format='multipart')

    def test_student_uploads_and_supervisors_download(self):
        res = self.upload(self.c_amina)
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['original_name'], 'report.pdf')
        self.assertEqual(res.data['status'], 'submitted')
        self.assertNotIn('file', res.data)                       # the raw storage path is never exposed
        url = res.data['download_url']
        for client in (self.c_amina, self.c_acad, self.c_ind, self.c_coord):
            dl = client.get(url)
            self.assertEqual(dl.status_code, 200)
            self.assertEqual(b''.join(dl.streaming_content), b'%PDF-1.4 test report')
        self.assertEqual(self.c_other_acad.get(url).status_code, 404)
        self.assertEqual(self.c_brian.get(url).status_code, 404)
        self.assertEqual(APIClient().get(url).status_code, 401)

    def test_only_pdf_doc_docx(self):
        for name in ('report.exe', 'report.png', 'report.txt'):
            res = self.upload(self.c_amina, name=name)
            self.assertEqual(res.status_code, 400, name)
        self.assertEqual(FinalReport.objects.count(), 0)
        self.assertEqual(self.upload(self.c_amina, name='report.docx').status_code, 201)

    @override_settings(MAX_REPORT_SIZE_MB=1)
    def test_size_limit(self):
        res = self.upload(self.c_amina, content=b'x' * (1024 * 1024 + 1))
        self.assertEqual(res.status_code, 400)
        self.assertEqual(self.upload(self.c_amina, content=b'x' * 1024).status_code, 201)

    def test_resubmitting_replaces_the_report_until_it_is_reviewed(self):
        first = self.upload(self.c_amina)
        second = self.upload(self.c_amina, name='v2.pdf', content=b'%PDF second', title='Version 2')
        self.assertEqual(second.status_code, 200, second.data)
        self.assertEqual(FinalReport.objects.count(), 1)
        self.assertEqual(second.data['id'], first.data['id'])
        self.assertEqual(second.data['title'], 'Version 2')
        dl = self.c_amina.get(second.data['download_url'])
        self.assertEqual(b''.join(dl.streaming_content), b'%PDF second')

        self.assertEqual(self.c_acad.post(f"/api/final-reports/{second.data['id']}/review/").status_code, 200)
        self.assertEqual(self.upload(self.c_amina).status_code, 400)          # reviewed reports are final

    def test_review_permissions(self):
        rid = self.upload(self.c_amina).data['id']
        self.assertEqual(self.c_amina.post(f'/api/final-reports/{rid}/review/').status_code, 403)
        self.assertEqual(self.c_ind.post(f'/api/final-reports/{rid}/review/').status_code, 403)
        self.assertEqual(self.c_other_acad.post(f'/api/final-reports/{rid}/review/').status_code, 404)
        res = self.c_acad.post(f'/api/final-reports/{rid}/review/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'reviewed')
        self.assertEqual(self.c_acad.post(f'/api/final-reports/{rid}/review/').status_code, 400)

    def test_supervisors_cannot_upload(self):
        self.assertEqual(self.upload(self.c_acad).status_code, 403)


# =============================================================================
class VisitTests(BaseCase):
    def test_academic_schedules_a_visit_for_an_assigned_student(self):
        res = self.c_acad.post('/api/visits/', {'student': self.amina.pk, 'visit_date': '2026-10-20',
                                                'mode': 'Physical', 'notes': 'Mid visit'}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['status'], 'scheduled')
        self.assertEqual(res.data['academic'], self.acad.pk)

    def test_cannot_visit_a_student_who_is_not_assigned(self):
        res = self.c_acad.post('/api/visits/', {'student': self.brian.pk, 'visit_date': '2026-10-20',
                                                'mode': 'Virtual'}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('student', res.data)

    def test_other_roles_cannot_schedule(self):
        body = {'student': self.amina.pk, 'visit_date': '2026-10-20', 'mode': 'Physical'}
        for client in (self.c_amina, self.c_ind, self.c_coord):
            self.assertEqual(client.post('/api/visits/', body, format='json').status_code, 403)

    def test_complete_and_cancel(self):
        v1 = Visit.objects.create(student=self.amina, academic=self.acad, visit_date=dt.date(2026, 10, 20))
        v2 = Visit.objects.create(student=self.amina, academic=self.acad, visit_date=dt.date(2026, 10, 27))
        self.assertEqual(self.c_acad.post(f'/api/visits/{v1.pk}/complete/').data['status'], 'completed')
        self.assertEqual(self.c_acad.post(f'/api/visits/{v2.pk}/cancel/').data['status'], 'cancelled')
        self.assertEqual(self.c_acad.post(f'/api/visits/{v1.pk}/cancel/').status_code, 400)
        self.assertEqual(self.c_other_acad.post(f'/api/visits/{v1.pk}/complete/').status_code, 404)

    def test_visibility(self):
        Visit.objects.create(student=self.amina, academic=self.acad, visit_date=dt.date(2026, 10, 20))
        self.assertEqual(len(self.c_acad.get('/api/visits/').data), 1)
        self.assertEqual(len(self.c_other_acad.get('/api/visits/').data), 0)
        self.assertEqual(len(self.c_amina.get('/api/visits/').data), 1)
        self.assertEqual(len(self.c_brian.get('/api/visits/').data), 0)
        self.assertEqual(len(self.c_coord.get('/api/visits/').data), 1)
        self.assertEqual(len(self.c_acad.get('/api/visits/?status=completed').data), 0)


# =============================================================================
class AssessmentTests(BaseCase):
    def ratings(self, *values):
        return dict(zip(CRITERIA, values))

    def test_industrial_marks_are_calculated_from_the_ratings(self):
        res = self.c_ind.post('/api/assessments/', {'student': self.amina.pk, 'ratings': self.ratings(5, 4, 4, 4, 4),
                                                    'comment': 'Reliable.', 'marks': 1}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['marks'], 84)                  # 21 / 25 = 84 %, the client-sent marks are ignored
        self.assertEqual(res.data['assessor_role'], 'industrial')
        self.assertEqual(res.data['assessment_type'], 'Industrial evaluation')

    def test_industrial_rounding_matches_the_frontend(self):
        res = self.c_ind.post('/api/assessments/', {'student': self.amina.pk, 'ratings': self.ratings(3, 3, 3, 3, 3)},
                              format='json')
        self.assertEqual(res.data['marks'], 60)
        res = self.c_ind.post('/api/assessments/', {'student': self.amina.pk, 'ratings': self.ratings(1, 1, 1, 1, 1)},
                              format='json')
        self.assertEqual(res.data['marks'], 20)

    def test_industrial_ratings_are_validated(self):
        for bad in (self.ratings(5, 4, 4, 4, 6), self.ratings(5, 4, 4, 4, 0), self.ratings(5, 4, 4, 4, 'a'),
                    self.ratings(5, 4, 4, 4, True), {CRITERIA[0]: 5}, 'nope', None):
            res = self.c_ind.post('/api/assessments/', {'student': self.amina.pk, 'ratings': bad}, format='json')
            self.assertEqual(res.status_code, 400, bad)
        self.assertEqual(Assessment.objects.count(), 0)

    def test_academic_assessment(self):
        res = self.c_acad.post('/api/assessments/', {'student': self.amina.pk, 'marks': 70,
                                                     'assessment_type': 'Final assessment', 'comment': 'Good'},
                               format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['assessor_role'], 'academic')
        self.assertEqual(res.data['marks'], 70)

    def test_academic_validation(self):
        base = {'student': self.amina.pk, 'assessment_type': 'Final assessment'}
        self.assertEqual(self.c_acad.post('/api/assessments/', base, format='json').status_code, 400)          # no marks
        self.assertEqual(self.c_acad.post('/api/assessments/', {**base, 'marks': 101}, format='json').status_code, 400)
        self.assertEqual(self.c_acad.post('/api/assessments/', {**base, 'marks': -1}, format='json').status_code, 400)
        self.assertEqual(self.c_acad.post('/api/assessments/', {**base, 'marks': 50, 'assessment_type': 'Bogus'},
                                          format='json').status_code, 400)

    def test_cannot_assess_students_who_are_not_assigned(self):
        res = self.c_acad.post('/api/assessments/', {'student': self.brian.pk, 'marks': 70}, format='json')
        self.assertEqual(res.status_code, 400)
        res = self.c_other_ind.post('/api/assessments/', {'student': self.amina.pk, 'ratings': self.ratings(5, 5, 5, 5, 5)},
                                    format='json')
        self.assertEqual(res.status_code, 400)

    def test_students_and_the_coordinator_cannot_assess(self):
        self.assertEqual(self.c_amina.post('/api/assessments/', {'student': self.amina.pk, 'marks': 100},
                                           format='json').status_code, 403)
        self.assertEqual(self.c_coord.post('/api/assessments/', {'student': self.amina.pk, 'marks': 100},
                                           format='json').status_code, 403)

    def test_visibility(self):
        Assessment.objects.create(student=self.amina, assessor=self.acad, assessor_role=Role.ACADEMIC,
                                  assessment_type='Final assessment', marks=70)
        Assessment.objects.create(student=self.brian, assessor=self.other_acad, assessor_role=Role.ACADEMIC,
                                  assessment_type='Final assessment', marks=55)
        self.assertEqual(len(self.c_amina.get('/api/assessments/').data), 1)
        self.assertEqual(len(self.c_brian.get('/api/assessments/').data), 1)
        self.assertEqual(len(self.c_acad.get('/api/assessments/').data), 1)       # only what they gave
        self.assertEqual(len(self.c_ind.get('/api/assessments/').data), 0)
        self.assertEqual(len(self.c_coord.get('/api/assessments/').data), 2)
        self.assertEqual(len(self.c_coord.get(f'/api/assessments/?student={self.brian.pk}').data), 1)


# =============================================================================
class AnnouncementTests(BaseCase):
    def test_coordinator_posts_and_everyone_reads(self):
        res = self.c_coord.post('/api/announcements/', {'title': 'Deadline', 'body': 'Submit by Friday.'}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(res.data['author'], self.coord.pk)
        for client in (self.c_amina, self.c_acad, self.c_ind, self.c_coord):
            self.assertEqual(len(client.get('/api/announcements/').data), 1)

    def test_others_cannot_post_or_delete(self):
        for client in (self.c_amina, self.c_acad, self.c_ind):
            self.assertEqual(client.post('/api/announcements/', {'title': 'x', 'body': 'y'}, format='json').status_code, 403)
        a = Announcement.objects.create(title='T', body='B', author=self.coord)
        self.assertEqual(self.c_amina.delete(f'/api/announcements/{a.pk}/').status_code, 403)
        self.assertEqual(self.c_coord.delete(f'/api/announcements/{a.pk}/').status_code, 204)


# =============================================================================
class StudentAndReportTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.approved_placement()
        for week in (1, 2, 3):
            self.entry(week, ApprovalStatus.APPROVED)            # 120 approved hours
        self.entry(4)                                            # 40 more, still pending
        Assessment.objects.create(student=self.amina, assessor=self.acad, assessor_role=Role.ACADEMIC,
                                  assessment_type='Final assessment', marks=70)
        Assessment.objects.create(student=self.amina, assessor=self.ind, assessor_role=Role.INDUSTRIAL,
                                  assessment_type='Industrial evaluation', marks=84,
                                  ratings=dict(zip(CRITERIA, [5, 4, 4, 4, 4])))

    def row(self, client, pk=None):
        rows = client.get('/api/students/').data
        return next(r for r in rows if r['id'] == (pk or self.amina.pk))

    def test_summary_numbers(self):
        row = self.row(self.c_coord)
        self.assertEqual(row['approved_hours'], 120)
        self.assertEqual(row['logged_hours'], 160)
        self.assertEqual(row['academic_marks'], 70)
        self.assertEqual(row['industrial_marks'], 84)
        self.assertEqual(row['overall_marks'], 77)
        self.assertEqual(row['placement_status'], 'approved')
        self.assertEqual(row['placement_company'], 'Acme')
        brian = self.row(self.c_coord, self.brian.pk)
        self.assertEqual(brian['placement_status'], 'none')
        self.assertEqual(brian['approved_hours'], 0)
        self.assertIsNone(brian['overall_marks'])

    def test_who_sees_which_students(self):
        self.assertEqual(len(self.c_coord.get('/api/students/').data), 2)
        self.assertEqual([r['id'] for r in self.c_acad.get('/api/students/').data], [self.amina.pk])
        self.assertEqual([r['id'] for r in self.c_ind.get('/api/students/').data], [self.amina.pk])
        self.assertEqual(self.c_other_acad.get('/api/students/').data, [])
        self.assertEqual(self.c_amina.get('/api/students/').status_code, 403)           # students use /dashboard/
        self.assertEqual(self.c_acad.get(f'/api/students/{self.brian.pk}/').status_code, 404)

    def test_search_and_filters(self):
        self.assertEqual(len(self.c_coord.get('/api/students/?search=amin').data), 1)
        self.assertEqual(len(self.c_coord.get('/api/students/?search=nobody').data), 0)
        self.assertEqual(len(self.c_coord.get('/api/students/?placement_status=none').data), 1)
        self.assertEqual(len(self.c_coord.get('/api/students/?placement_status=approved').data), 1)
        self.assertEqual(len(self.c_coord.get('/api/students/', {'course': 'Diploma in ICT'}).data), 2)
        self.assertEqual(len(self.c_coord.get('/api/students/', {'course': 'Diploma in Accounting'}).data), 0)

    def test_coordinator_assigns_supervisors(self):
        res = self.c_coord.patch(f'/api/students/{self.brian.pk}/assign/',
                                 {'academic_supervisor': self.other_acad.pk, 'industrial_supervisor': self.other_ind.pk},
                                 format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['academic_supervisor']['id'], self.other_acad.pk)
        self.brian.refresh_from_db()
        self.assertEqual(self.brian.industrial_supervisor_id, self.other_ind.pk)
        self.assertEqual(len(self.c_other_acad.get('/api/students/').data), 1)            # now visible to them

        res = self.c_coord.patch(f'/api/students/{self.brian.pk}/assign/', {'academic_supervisor': None}, format='json')
        self.assertEqual(res.status_code, 200)
        self.brian.refresh_from_db()
        self.assertIsNone(self.brian.academic_supervisor_id)
        self.assertEqual(self.brian.industrial_supervisor_id, self.other_ind.pk)          # untouched key stays

    def test_assign_rejects_wrong_roles_and_non_coordinators(self):
        res = self.c_coord.patch(f'/api/students/{self.brian.pk}/assign/', {'academic_supervisor': self.ind.pk},
                                 format='json')
        self.assertEqual(res.status_code, 400)
        res = self.c_acad.patch(f'/api/students/{self.amina.pk}/assign/', {'academic_supervisor': self.acad.pk},
                                format='json')
        self.assertEqual(res.status_code, 403)

    def test_report_summary_and_csv(self):
        res = self.c_coord.get('/api/reports/summary/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 2)
        for client in (self.c_acad, self.c_ind, self.c_amina):
            self.assertEqual(client.get('/api/reports/summary/').status_code, 403)
            self.assertEqual(client.get('/api/reports/summary.csv').status_code, 403)

        csv_res = self.c_coord.get('/api/reports/summary.csv')
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn('text/csv', csv_res['Content-Type'])
        lines = csv_res.content.decode().strip().splitlines()
        self.assertEqual(lines[0], 'Name,Admission No,Course,Organisation,Approved hours,Academic %,Industrial %,'
                                   'Overall %,Final report')
        self.assertEqual(len(lines), 3)
        amina_line = next(line for line in lines if 'LC/T/amina' in line)
        self.assertIn(',120,70,84,77,none', amina_line)


# =============================================================================
class DashboardAndMetaTests(BaseCase):
    def test_meta_is_public(self):
        res = APIClient().get('/api/meta/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['criteria'], CRITERIA)
        self.assertIn('Diploma in ICT', res.data['courses'])
        # a stale token must not break the public endpoint
        stale = APIClient()
        stale.credentials(HTTP_AUTHORIZATION='Token deadbeef')
        self.assertEqual(stale.get('/api/meta/').status_code, 200)

    def test_health_check(self):
        self.assertEqual(APIClient().get('/api/health/').status_code, 200)

    def test_student_dashboard(self):
        self.approved_placement()
        self.entry(1, ApprovalStatus.APPROVED)
        self.entry(2)
        Announcement.objects.create(title='Hello', body='World', author=self.coord)
        res = self.c_amina.get('/api/dashboard/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['role'], 'student')
        stats = res.data['stats']
        self.assertEqual(stats['approved_hours'], 40)
        self.assertEqual(stats['logged_hours'], 80)
        self.assertEqual(stats['entries_total'], 2)
        self.assertEqual(stats['entries_approved'], 1)
        self.assertIsNone(stats['average_score'])
        self.assertEqual(res.data['placement']['status'], 'approved')
        self.assertEqual(len(res.data['recent_logbook']), 2)
        self.assertEqual(len(res.data['announcements']), 1)

    def test_student_dashboard_without_a_placement(self):
        res = self.c_brian.get('/api/dashboard/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIsNone(res.data['placement'])
        self.assertEqual(res.data['stats']['percent_complete'], 0)

    def test_academic_dashboard(self):
        Visit.objects.create(student=self.amina, academic=self.acad, visit_date=dt.date(2026, 11, 3))
        self.entry(1)
        res = self.c_acad.get('/api/dashboard/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['role'], 'academic')
        self.assertEqual(res.data['stats']['assigned_students'], 1)
        self.assertEqual(res.data['stats']['upcoming_visits'], 1)
        self.assertEqual(res.data['stats']['entries_to_review'], 1)

    def test_industrial_dashboard(self):
        self.entry(1)
        self.entry(2, ApprovalStatus.APPROVED)
        res = self.c_ind.get('/api/dashboard/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['stats'], {'interns': 1, 'pending_approvals': 1, 'approved_entries': 1,
                                             'evaluations': 0})
        self.assertEqual(len(res.data['pending_entries']), 1)

    def test_coordinator_dashboard(self):
        self.approved_placement(self.amina)
        res = self.c_coord.get('/api/dashboard/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['stats']['students'], 2)
        self.assertEqual(res.data['stats']['placed'], 1)
        self.assertEqual(res.data['stats']['academic_supervisors'], 2)
        self.assertEqual(res.data['stats']['industrial_supervisors'], 2)
        self.assertEqual(res.data['placement_overview'], {'none': 1, 'pending': 0, 'approved': 1, 'rejected': 0})
        self.assertEqual(len(res.data['recent_registrations']), 2)


# =============================================================================
class SeedCommandTests(BaseCase):
    def test_seed_demo_creates_the_demo_accounts_and_can_be_rerun_with_force(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from io import StringIO

        call_command('seed_demo', stdout=StringIO())
        self.assertTrue(User.objects.filter(email='student@langata.ac.ke').exists())
        with self.assertRaises(CommandError):
            call_command('seed_demo', stdout=StringIO())
        call_command('seed_demo', '--force', stdout=StringIO())
        self.assertEqual(User.objects.filter(email__endswith='@langata.ac.ke').count(), 6)
        self.assertEqual(Announcement.objects.filter(title='Weekly logbooks').count(), 1)

        client = APIClient()
        res = client.post('/api/auth/login/', {'email': 'student@langata.ac.ke', 'password': 'demo1234'})
        self.assertEqual(res.status_code, 200, res.data)
        client.credentials(HTTP_AUTHORIZATION='Token ' + res.data['token'])
        stats = client.get('/api/dashboard/').data['stats']
        self.assertEqual(stats['approved_hours'], 120)
        self.assertEqual(stats['average_score'], 84)
