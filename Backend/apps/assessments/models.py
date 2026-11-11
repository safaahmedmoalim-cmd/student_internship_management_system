from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.common.validators import UploadTo, document_extension_validator, validate_upload_size
from apps.logbooks.models import SUPERVISOR_ROLES
from apps.placements.models import Placement
from apps.students.models import Student

# Workplace evaluation areas (section 3.3) - each rated 1 (poor) to 5 (excellent).
WORKPLACE_CRITERIA = [
    'Technical competence',
    'Communication skills',
    'Teamwork',
    'Time management',
    'Problem-solving',
    'Professional conduct',
    'Adaptability',
    'Initiative',
    'Responsibility',
    'Attendance and punctuality',
]

# Academic assessment rubric used by academic supervisors - each rated 1 to 5.
ACADEMIC_CRITERIA = [
    'Logbook completeness and quality',
    'Application of theoretical knowledge',
    'Practical skills demonstrated',
    'Understanding of the organization',
    'Professionalism and conduct',
    'Communication and presentation',
]

MAX_SCORE = 5


class Assessment(models.Model):
    """Table 13 - assessments."""

    class AssessmentType(models.TextChoices):
        ACADEMIC = 'academic', 'Academic Assessment'
        WORKPLACE = 'workplace', 'Workplace Assessment'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'   # saved as a draft by the supervisor
        COMPLETED = 'completed', 'Completed'         # submitted; locked for the supervisor
        RELEASED = 'released', 'Released'            # released by the administrator; visible to the student

    CRITERIA = {AssessmentType.ACADEMIC: ACADEMIC_CRITERIA, AssessmentType.WORKPLACE: WORKPLACE_CRITERIA}
    TYPE_FOR_ROLE = {'academic': AssessmentType.ACADEMIC, 'industrial': AssessmentType.WORKPLACE}

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='assessments')
    placement = models.ForeignKey(Placement, on_delete=models.CASCADE, related_name='assessments')
    supervisor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='assessments_given')
    supervisor_role = models.CharField(max_length=12, choices=SUPERVISOR_ROLES)
    assessment_type = models.CharField(max_length=10, choices=AssessmentType.choices)
    assessment_criteria = models.JSONField(default=dict, help_text='{"criterion": score 1-5}')
    marks = models.DecimalField(max_digits=5, decimal_places=2,
                                validators=[MinValueValidator(0), MaxValueValidator(100)])
    comments = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    evaluation_form = models.FileField(upload_to=UploadTo('evaluation_forms'), blank=True,
                                       validators=[document_extension_validator, validate_upload_size])
    assessment_date = models.DateField(auto_now_add=True)
    assessment_status = models.CharField(max_length=12, choices=Status.choices, default=Status.IN_PROGRESS,
                                         db_index=True)
    released_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='+')
    released_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assessments'
        ordering = ['-updated_at']
        constraints = [
            models.UniqueConstraint(fields=['placement', 'assessment_type'], name='one_assessment_per_type'),
        ]

    def __str__(self):
        return f'{self.student} - {self.get_assessment_type_display()} ({self.marks}%)'

    @staticmethod
    def compute_marks(criteria_scores):
        total = sum(criteria_scores.values())
        return round(total * 100 / (len(criteria_scores) * MAX_SCORE), 2)
