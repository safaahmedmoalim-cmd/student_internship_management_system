import tempfile
from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone

from apps.common.testing import (
    ApiTestCase, make_academic, make_admin, make_industrial, make_organization, make_placement, make_student,
)
from apps.notifications.models import Notification
from apps.organizations.models import Organization
from apps.supervisors.models import SupervisorAssignment

from .models import Placement

TODAY = timezone.localdate()


@override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix='sims-test-'))
class PlacementWorkflowTests(ApiTestCase):
    def setUp(self):
        self.admin = make_admin()
        self.student = make_student()
        self.s_api = self.client_for(self.student.user)
        self.a_api = self.client_for(self.admin)

    def apply(self, **over):
        data = {'organization_name': 'New  Host Ltd', 'address': 'Road 1', 'county': 'Kisumu',
                'contact_person': 'Jane', 'phone_number': '0700', 'email': 'hr@host.example',
                'start_date': TODAY + timedelta(days=5), 'end_date': TODAY + timedelta(days=90)}
        data.update(over)
        return self.s_api.post('/api/placements/', data, format='multipart')

    def test_full_cycle_submit_return_resubmit_approve(self):
        r = self.apply(supporting_document=SimpleUploadedFile('letter.pdf', b'%PDF-1.4', 'application/pdf'))
        self.assertEqual(r.status_code, 201, r.data)
        pid = r.data['id']
        self.assertEqual(r.data['application_status'], 'pending')
        self.assertEqual(r.data['organization']['status'], Organization.Status.PENDING)
        self.assertTrue(Notification.objects.filter(user=self.admin, notification_type='placement').exists())
        self.assertEqual(self.a_api.get(f'/api/placements/{pid}/document/').status_code, 200)

        # cannot apply twice while one is open
        self.assertEqual(self.apply().status_code, 400)

        # return needs a reason
        self.assertEqual(self.a_api.post(f'/api/placements/{pid}/return/', {}).status_code, 400)
        r = self.a_api.post(f'/api/placements/{pid}/return/', {'comments': 'Wrong dates'})
        self.assertEqual(r.data['application_status'], 'returned')

        # student corrects and resubmits
        org = make_organization()
        r = self.s_api.put(f'/api/placements/{pid}/', {'organization': org.pk, 'start_date': TODAY,
                                                      'end_date': TODAY + timedelta(days=60)}, format='multipart')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['application_status'], 'pending')
        self.assertEqual(r.data['organization']['id'], org.pk)

        r = self.a_api.post(f'/api/placements/{pid}/approve/', {'comments': 'OK'})
        self.assertEqual(r.data['application_status'], 'approved')
        self.assertTrue(Notification.objects.filter(user=self.student.user, title='Placement approved').exists())
        # decisions only on pending applications
        self.assertEqual(self.a_api.post(f'/api/placements/{pid}/reject/', {'comments': 'x'}).status_code, 400)

    def test_withdraw_requires_reason_and_frees_student_to_reapply(self):
        pid = self.apply().data['id']
        self.assertEqual(self.s_api.post(f'/api/placements/{pid}/withdraw/', {}).status_code, 400)
        r = self.s_api.post(f'/api/placements/{pid}/withdraw/', {'reason': 'Found another place'})
        self.assertEqual(r.data['application_status'], 'withdrawn')
        self.assertEqual(self.apply(organization_name='Second Host').status_code, 201)

    def test_validation(self):
        r = self.apply(end_date=TODAY)
        self.assertIn('end_date', r.data)
        r = self.apply(organization_name='')
        self.assertIn('organization_name', r.data)
        r = self.apply(supporting_document=SimpleUploadedFile('x.exe', b'MZ', 'application/octet-stream'))
        self.assertIn('supporting_document', r.data)

    def test_existing_organization_is_reused_case_insensitively(self):
        org = make_organization(organization_name='Acme Ltd')
        r = self.apply(organization_name='acme ltd')
        self.assertEqual(r.data['organization']['id'], org.pk)

    def test_role_restrictions_and_scoping(self):
        other = make_student()
        make_placement(other, status=Placement.Status.PENDING)
        self.assertEqual(self.s_api.get('/api/placements/').data, [])
        pid = Placement.objects.get(student=other).pk
        self.assertEqual(self.s_api.post(f'/api/placements/{pid}/approve/').status_code, 403)
        self.assertEqual(self.client_for(self.admin).post('/api/placements/', {}).status_code, 403)

    def test_attachment_status_transitions(self):
        p = make_placement(self.student)
        r = self.a_api.post(f'/api/placements/{p.pk}/attachment-status/', {'attachment_status': 'completed'})
        self.assertEqual(r.status_code, 400)  # not_started -> completed is not allowed
        for s in ('active', 'completed'):
            r = self.a_api.post(f'/api/placements/{p.pk}/attachment-status/', {'attachment_status': s})
            self.assertEqual(r.data['attachment_status'], s)


class AssignmentTests(ApiTestCase):
    def setUp(self):
        self.admin = make_admin()
        self.api = self.client_for(self.admin)
        self.student = make_student()
        self.org = make_organization()
        self.placement = make_placement(self.student, self.org)
        self.academic = make_academic()
        self.industrial = make_industrial(self.org)

    def assign(self, **over):
        data = {'placement': self.placement.pk, 'academic_supervisor': self.academic.pk,
                'industrial_supervisor': self.industrial.pk}
        data.update(over)
        return self.api.post('/api/assignments/', data)

    def test_assign_notifies_and_scopes_access(self):
        r = self.assign()
        self.assertEqual(r.status_code, 201, r.data)
        for u in (self.student.user, self.academic.user, self.industrial.user):
            self.assertTrue(Notification.objects.filter(user=u, notification_type='assignment').exists())
        self.assertEqual(len(self.client_for(self.academic.user).get('/api/students/').data), 1)
        self.assertEqual(len(self.client_for(make_academic().user).get('/api/students/').data), 0)
        detail = self.client_for(self.industrial.user).get(f'/api/students/{self.student.pk}/')
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(self.client_for(make_industrial().user).get(f'/api/students/{self.student.pk}/').status_code, 404)

    def test_reassignment_keeps_one_active(self):
        self.assign()
        new_academic = make_academic()
        self.assign(academic_supervisor=new_academic.pk)
        active = SupervisorAssignment.objects.filter(placement=self.placement, assignment_status='active')
        self.assertEqual(active.count(), 1)
        self.assertEqual(active.get().academic_supervisor, new_academic)

    def test_industrial_supervisor_must_work_at_host(self):
        r = self.assign(industrial_supervisor=make_industrial().pk)
        self.assertIn('industrial_supervisor', r.data)

    def test_cannot_assign_pending_placement(self):
        self.placement.application_status = Placement.Status.PENDING
        self.placement.save()
        self.assertIn('placement', self.assign().data)
