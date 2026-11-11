from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q

from apps.accounts.models import Role
from apps.common.validators import UploadTo, attachment_extension_validator, validate_upload_size
from apps.placements.models import Placement
from apps.students.models import Student

SUPERVISOR_ROLES = [(Role.ACADEMIC.value, 'Academic Supervisor'), (Role.INDUSTRIAL.value, 'Industrial Supervisor')]


class Logbook(models.Model):
    """Table 9 - logbooks. One weekly entry, reviewed independently by both supervisors."""

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='logbooks')
    placement = models.ForeignKey(Placement, on_delete=models.CASCADE, related_name='logbooks')
    week_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(52)])
    start_date = models.DateField()
    end_date = models.DateField()
    activities = models.TextField()
    skills_acquired = models.TextField(blank=True)
    challenges = models.TextField(blank=True)
    solutions = models.TextField(blank=True)
    attachment = models.FileField(upload_to=UploadTo('logbooks'), blank=True,
                                  validators=[attachment_extension_validator, validate_upload_size])
    submission_date = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'logbooks'
        ordering = ['student', 'week_number']
        constraints = [
            models.UniqueConstraint(fields=['placement', 'week_number'], name='one_logbook_per_week'),
            models.CheckConstraint(condition=Q(end_date__gte=F('start_date')), name='logbook_end_after_start'),
        ]

    def __str__(self):
        return f'{self.student} - week {self.week_number}'

    def refresh_status(self):
        """Overall status is derived from the two independent supervisor reviews."""
        decisions = list(self.reviews.values_list('review_status', flat=True))
        if LogbookReview.Status.REJECTED in decisions:
            status = self.Status.REJECTED
        elif decisions and all(d == LogbookReview.Status.APPROVED for d in decisions):
            status = self.Status.APPROVED
        elif LogbookReview.Status.APPROVED in decisions:
            status = self.Status.UNDER_REVIEW
        else:
            status = self.Status.SUBMITTED
        if status != self.status:
            self.status = status
            self.save(update_fields=['status', 'updated_at'])
        return status


class LogbookReview(models.Model):
    """Table 10 - logbook_reviews. Each supervisor's own decision on an entry."""

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'

    logbook = models.ForeignKey(Logbook, on_delete=models.CASCADE, related_name='reviews')
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='logbook_reviews')
    supervisor_role = models.CharField(max_length=12, choices=SUPERVISOR_ROLES)
    review_status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    comments = models.TextField(blank=True)
    review_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'logbook_reviews'
        ordering = ['supervisor_role']
        constraints = [
            # Relationship 10: one logbook receives one review from each of the two supervisors.
            models.UniqueConstraint(fields=['logbook', 'supervisor_role'], name='one_review_per_supervisor_role'),
        ]

    def __str__(self):
        return f'{self.logbook} - {self.supervisor_role}: {self.review_status}'


class Attendance(models.Model):
    """Table 16 - attendance. Recorded by the industrial supervisor."""

    class Status(models.TextChoices):
        PRESENT = 'present', 'Present'
        ABSENT = 'absent', 'Absent'
        LATE = 'late', 'Late'
        EXCUSED = 'excused', 'Excused'

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    attendance_date = models.DateField()
    attendance_status = models.CharField(max_length=10, choices=Status.choices)
    remarks = models.CharField(max_length=255, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'attendance'
        ordering = ['-attendance_date']
        verbose_name_plural = 'attendance'
        constraints = [
            models.UniqueConstraint(fields=['student', 'attendance_date'], name='one_attendance_per_day'),
        ]

    def __str__(self):
        return f'{self.student} {self.attendance_date}: {self.attendance_status}'
