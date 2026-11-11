from django.conf import settings
from django.db import models

from apps.organizations.models import Organization
from apps.students.models import Student
from apps.supervisors.models import AcademicSupervisor


class SupervisionVisit(models.Model):
    """Table 11 - supervision_visits."""

    class VisitType(models.TextChoices):
        PHYSICAL = 'physical', 'Physical'
        VIRTUAL = 'virtual', 'Virtual'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        RESCHEDULED = 'rescheduled', 'Rescheduled'
        CANCELLED = 'cancelled', 'Cancelled'

    UPCOMING_STATUSES = (Status.SCHEDULED, Status.RESCHEDULED)

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='visits')
    academic_supervisor = models.ForeignKey(AcademicSupervisor, on_delete=models.CASCADE, related_name='visits')
    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='visits')
    visit_date = models.DateTimeField()
    visit_type = models.CharField(max_length=10, choices=VisitType.choices, default=VisitType.PHYSICAL)
    meeting_link = models.URLField(blank=True, help_text='For virtual visits.')
    objectives = models.TextField()
    observations = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    visit_status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'supervision_visits'
        ordering = ['-visit_date']

    def __str__(self):
        return f'{self.student} - {self.visit_date:%Y-%m-%d} ({self.visit_status})'
