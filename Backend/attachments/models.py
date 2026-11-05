import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from accounts.models import Role


class ApprovalStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'


User = settings.AUTH_USER_MODEL

# Every ForeignKey below uses db_constraint=False: the database has NO foreign-key constraints, rows are related
# only through these id columns and joined by the ORM (same design as the MySQL script). Django still applies
# on_delete (e.g. deleting a student deletes their logbook) in Python, so behaviour is unchanged.


# -----------------------------------------------------------------------------
# Placement - where a student does the attachment (one per student)
# -----------------------------------------------------------------------------
class Placement(models.Model):
    student = models.OneToOneField(User, on_delete=models.CASCADE, db_constraint=False, related_name='placement',
                                   limit_choices_to={'role': Role.STUDENT})
    company = models.CharField(max_length=150)
    location = models.CharField(max_length=150)
    department = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    industrial_supervisor = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name='supervised_placements',
        limit_choices_to={'role': Role.INDUSTRIAL})
    status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING,
                              db_index=True)
    coordinator_comment = models.TextField(blank=True)
    decided_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name='+')
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=Q(end_date__gt=F('start_date')), name='placement_end_after_start'),
        ]

    def __str__(self):
        return f'{self.student} @ {self.company} ({self.status})'

    def approve(self, by):
        self.status = ApprovalStatus.APPROVED
        self.coordinator_comment = ''
        self.decided_by = by
        self.decided_at = timezone.now()
        self.save()
        # Attach the student to the placement's industrial supervisor (unless one is already set).
        student = self.student
        if self.industrial_supervisor_id and not student.industrial_supervisor_id:
            student.industrial_supervisor_id = self.industrial_supervisor_id
            student.save(update_fields=['industrial_supervisor'])

    def reject(self, by, comment):
        self.status = ApprovalStatus.REJECTED
        self.coordinator_comment = comment
        self.decided_by = by
        self.decided_at = timezone.now()
        self.save()


# -----------------------------------------------------------------------------
# Weekly logbook
# -----------------------------------------------------------------------------
class LogbookEntry(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_constraint=False, related_name='logbook_entries',
                                limit_choices_to={'role': Role.STUDENT})
    week_no = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(30)])
    week_start = models.DateField()
    hours_worked = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(60)])
    activities = models.TextField()
    skills_learned = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=ApprovalStatus.choices, default=ApprovalStatus.PENDING,
                              db_index=True)
    industrial_comment = models.TextField(blank=True)
    academic_comment = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student', 'week_no']
        verbose_name_plural = 'logbook entries'
        constraints = [
            models.UniqueConstraint(fields=['student', 'week_no'], name='one_logbook_entry_per_week'),
        ]

    def __str__(self):
        return f'{self.student} - week {self.week_no}'

    def approve(self, comment=''):
        self.status = ApprovalStatus.APPROVED
        self.industrial_comment = comment or self.industrial_comment or 'Approved.'
        self.reviewed_at = timezone.now()
        self.save()

    def reject(self, comment):
        self.status = ApprovalStatus.REJECTED
        self.industrial_comment = comment
        self.reviewed_at = timezone.now()
        self.save()


# -----------------------------------------------------------------------------
# Final report (one per student, resubmitting replaces the file)
# -----------------------------------------------------------------------------
def report_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'reports/{instance.student_id}/{uuid.uuid4().hex}{ext}'


def validate_report_size(file):
    limit = settings.MAX_REPORT_SIZE_MB * 1024 * 1024
    if file.size > limit:
        raise ValidationError(f'File is larger than {settings.MAX_REPORT_SIZE_MB} MB.')


class FinalReport(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        REVIEWED = 'reviewed', 'Reviewed'

    student = models.OneToOneField(User, on_delete=models.CASCADE, db_constraint=False, related_name='final_report',
                                   limit_choices_to={'role': Role.STUDENT})
    title = models.CharField(max_length=200)
    summary = models.TextField()
    file = models.FileField(upload_to=report_upload_path,
                            validators=[FileExtensionValidator(['pdf', 'doc', 'docx']), validate_report_size])
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name='+')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f'{self.student} - {self.title}'

    def mark_reviewed(self, by):
        self.status = self.Status.REVIEWED
        self.reviewed_by = by
        self.reviewed_at = timezone.now()
        self.save()


# -----------------------------------------------------------------------------
# Supervisor visits
# -----------------------------------------------------------------------------
class Visit(models.Model):
    class Mode(models.TextChoices):
        PHYSICAL = 'Physical', 'Physical'
        VIRTUAL = 'Virtual', 'Virtual'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    student = models.ForeignKey(User, on_delete=models.CASCADE, db_constraint=False, related_name='visits',
                                limit_choices_to={'role': Role.STUDENT})
    academic = models.ForeignKey(User, on_delete=models.CASCADE, db_constraint=False, related_name='academic_visits',
                                 limit_choices_to={'role': Role.ACADEMIC})
    visit_date = models.DateField()
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.PHYSICAL)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-visit_date']

    def __str__(self):
        return f'{self.student} - {self.visit_date} ({self.status})'


# -----------------------------------------------------------------------------
# Assessments (academic marks + industrial evaluations)
# -----------------------------------------------------------------------------
class Assessment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, db_constraint=False, related_name='assessments',
                                limit_choices_to={'role': Role.STUDENT})
    assessor = models.ForeignKey(User, on_delete=models.CASCADE, db_constraint=False, related_name='given_assessments')
    assessor_role = models.CharField(max_length=12, choices=[(Role.ACADEMIC, 'Academic'),
                                                              (Role.INDUSTRIAL, 'Industrial')])
    assessment_type = models.CharField(max_length=60)
    marks = models.PositiveSmallIntegerField(validators=[MaxValueValidator(100)])
    ratings = models.JSONField(default=dict, blank=True)     # {"Teamwork": 4, ...} for industrial evaluations
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student} - {self.assessment_type} ({self.marks}%)'


# -----------------------------------------------------------------------------
# Announcements
# -----------------------------------------------------------------------------
class Announcement(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    author = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False, related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
