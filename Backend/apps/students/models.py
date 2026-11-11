from django.conf import settings
from django.db import models

from apps.accounts.models import Department


class Student(models.Model):
    """Table 2 - students."""

    class AcademicYear(models.TextChoices):
        YEAR_1 = 'Year 1', 'Year 1'
        YEAR_2 = 'Year 2', 'Year 2'
        YEAR_3 = 'Year 3', 'Year 3'
        YEAR_4 = 'Year 4', 'Year 4'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    registration_number = models.CharField(max_length=40, unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    phone_number = models.CharField(max_length=30, blank=True)
    department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name='students')
    academic_year = models.CharField(max_length=10, choices=AcademicYear.choices)

    class Meta:
        db_table = 'students'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return f'{self.full_name} ({self.registration_number})'

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    def save(self, *args, **kwargs):
        self.registration_number = (self.registration_number or '').strip().upper()
        super().save(*args, **kwargs)
