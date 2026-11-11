from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from apps.accounts.models import Department
from apps.organizations.models import Organization


class AcademicSupervisor(models.Model):
    """Table 3 - academic_supervisors (lecturers / institutional staff)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='academic_profile')
    staff_number = models.CharField(max_length=40, unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone_number = models.CharField(max_length=30, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='academic_supervisors')

    class Meta:
        db_table = 'academic_supervisors'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.full_name} ({self.staff_number})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class IndustrialSupervisor(models.Model):
    """Table 4 - industrial_supervisors (employees of host organizations)."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='industrial_profile')
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name='industrial_supervisors')
    employee_number = models.CharField(max_length=40, blank=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone_number = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=120)

    class Meta:
        db_table = 'industrial_supervisors'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.full_name} - {self.organization}'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()


class SupervisorAssignment(models.Model):
    """Table 8 - supervisor_assignments. Links a student, an approved placement and both supervisors."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'   # replaced by a newer assignment or the placement was withdrawn

    placement = models.ForeignKey('placements.Placement', on_delete=models.CASCADE, related_name='assignments')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='assignments')
    academic_supervisor = models.ForeignKey(AcademicSupervisor, on_delete=models.PROTECT, related_name='assignments')
    industrial_supervisor = models.ForeignKey(IndustrialSupervisor, on_delete=models.PROTECT, related_name='assignments')
    assigned_date = models.DateTimeField(auto_now_add=True)
    assignment_status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+')

    class Meta:
        db_table = 'supervisor_assignments'
        ordering = ['-assigned_date']
        constraints = [
            # Relationship 6: one placement has at most one ACTIVE supervisor assignment.
            models.UniqueConstraint(fields=['placement'], condition=Q(assignment_status='active'),
                                    name='one_active_assignment_per_placement'),
        ]

    def __str__(self):
        return f'{self.student} -> {self.academic_supervisor} / {self.industrial_supervisor}'

    def clean(self):
        if self.placement_id and self.student_id and self.placement.student_id != self.student_id:
            raise ValidationError('The placement does not belong to this student.')
