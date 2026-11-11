from django.conf import settings
from django.db import models

from apps.common.validators import UploadTo, document_extension_validator, validate_upload_size
from apps.placements.models import Placement
from apps.students.models import Student


class FinalReport(models.Model):
    """Table 12 - final_reports. Each upload is a new version; the history is kept."""

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        RETURNED = 'returned', 'Returned for Correction'
        APPROVED = 'approved', 'Approved'

    # While the latest version is in one of these states the student cannot upload another one.
    BLOCKING_STATUSES = (Status.SUBMITTED, Status.UNDER_REVIEW, Status.APPROVED)

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='final_reports')
    placement = models.ForeignKey(Placement, on_delete=models.CASCADE, related_name='final_reports')
    version = models.PositiveSmallIntegerField(default=1)
    title = models.CharField(max_length=200)
    report_file = models.FileField(upload_to=UploadTo('final_reports'),
                                   validators=[document_extension_validator, validate_upload_size])
    original_filename = models.CharField(max_length=255, blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)
    review_status = models.CharField(max_length=12, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    feedback = models.TextField(blank=True)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+')
    review_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'final_reports'
        ordering = ['-submission_date']
        constraints = [
            models.UniqueConstraint(fields=['placement', 'version'], name='unique_report_version'),
        ]

    def __str__(self):
        return f'{self.student} - v{self.version} ({self.review_status})'
