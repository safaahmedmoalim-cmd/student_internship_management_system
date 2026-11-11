from django.conf import settings
from django.db import models
from django.db.models import F, Q

from apps.common.validators import UploadTo, attachment_extension_validator, validate_upload_size
from apps.organizations.models import Organization
from apps.students.models import Student


class AttachmentPeriod(models.Model):
    """Attachment periods and deadlines managed by the administrator."""
    name = models.CharField(max_length=120, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    application_deadline = models.DateField(help_text='Last day to submit placement applications.')
    report_deadline = models.DateField(help_text='Last day to submit the final attachment report.')
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'attachment_periods'
        ordering = ['-start_date']
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gt=F('start_date')), name='period_end_after_start'),
        ]

    def __str__(self):
        return self.name


class Placement(models.Model):
    """Table 7 - placements. A student's application to do attachment at an organization."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        RETURNED = 'returned', 'Returned for Correction'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    class AttachmentStatus(models.TextChoices):
        NOT_STARTED = 'not_started', 'Not Started'
        ACTIVE = 'active', 'Active'
        COMPLETED = 'completed', 'Completed'
        TERMINATED = 'terminated', 'Terminated'

    # A student may only hold one "open" application at a time.
    OPEN_STATUSES = (Status.PENDING, Status.RETURNED)

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='placements')
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='placements')
    attachment_period = models.ForeignKey(AttachmentPeriod, null=True, blank=True, on_delete=models.SET_NULL,
                                          related_name='placements')
    start_date = models.DateField()
    end_date = models.DateField()
    application_date = models.DateTimeField(auto_now_add=True)
    application_status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING,
                                          db_index=True)
    attachment_status = models.CharField(max_length=12, choices=AttachmentStatus.choices,
                                         default=AttachmentStatus.NOT_STARTED, db_index=True)
    supporting_document = models.FileField(
        upload_to=UploadTo('placement_documents'), blank=True,
        validators=[attachment_extension_validator, validate_upload_size])
    withdrawal_reason = models.TextField(blank=True)
    approval_comments = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'placements'
        ordering = ['-application_date']
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gt=F('start_date')), name='placement_end_after_start'),
        ]

    def __str__(self):
        return f'{self.student} @ {self.organization} ({self.application_status})'

    @property
    def is_running(self):
        """Approved and not yet finished - the placement the student is currently attached to."""
        return (self.application_status == self.Status.APPROVED and
                self.attachment_status in (self.AttachmentStatus.NOT_STARTED, self.AttachmentStatus.ACTIVE))

    def active_assignment(self):
        return self.assignments.filter(assignment_status='active').select_related(
            'academic_supervisor__user', 'industrial_supervisor__user').first()

    @classmethod
    def current_for(cls, student):
        """The approved placement a student is currently on (or None)."""
        return cls.objects.filter(
            student=student, application_status=cls.Status.APPROVED,
            attachment_status__in=[cls.AttachmentStatus.NOT_STARTED, cls.AttachmentStatus.ACTIVE],
        ).select_related('organization').first()
