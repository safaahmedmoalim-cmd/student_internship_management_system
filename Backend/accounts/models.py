from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    STUDENT = 'student', 'Student'
    ACADEMIC = 'academic', 'Academic Supervisor'
    INDUSTRIAL = 'industrial', 'Industrial Supervisor'
    COORDINATOR = 'coordinator', 'Coordinator'


# Extra details each role must provide when signing up. These mirror the
# sign-up form of the frontend. (model_field_name -> label used in errors)
ROLE_REQUIRED_FIELDS = {
    Role.STUDENT: {'adm_no': 'Admission number', 'course': 'Course', 'year': 'Year of study'},
    Role.ACADEMIC: {'staff_no': 'Staff number', 'department': 'Department'},
    Role.INDUSTRIAL: {'company': 'Company', 'position': 'Position', 'company_location': 'Company location'},
    Role.COORDINATOR: {'staff_no': 'Staff number'},
}


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError('An email address is required.')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', Role.COORDINATOR)
        if not extra['is_staff'] or not extra['is_superuser']:
            raise ValueError('Superuser must have is_staff=True and is_superuser=True.')
        return self._create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """One user table for all four roles; a few columns only apply to some roles."""

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT, db_index=True)

    # Student
    adm_no = models.CharField('admission number', max_length=40, unique=True, null=True, blank=True)
    course = models.CharField(max_length=120, blank=True)
    year = models.CharField('year of study', max_length=20, blank=True)
    # db_constraint=False: no database-level FOREIGN KEY. The tables are related purely
    # through these id columns and joined by the ORM (same design as the MySQL script).
    academic_supervisor = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False,
        related_name='academic_students', limit_choices_to={'role': Role.ACADEMIC},
    )
    industrial_supervisor = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, db_constraint=False,
        related_name='industrial_interns', limit_choices_to={'role': Role.INDUSTRIAL},
    )

    # Academic supervisor / coordinator
    staff_no = models.CharField('staff number', max_length=40, blank=True)
    department = models.CharField(max_length=120, blank=True)

    # Industrial supervisor
    company = models.CharField(max_length=150, blank=True)
    position = models.CharField(max_length=120, blank=True)
    company_location = models.CharField(max_length=150, blank=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.get_role_display()})'

    def save(self, *args, **kwargs):
        self.email = (self.email or '').strip().lower()
        if not self.adm_no:  # keep the unique column NULL (not '') for non-students
            self.adm_no = None
        super().save(*args, **kwargs)

    # Handy role checks
    @property
    def is_student(self):
        return self.role == Role.STUDENT

    @property
    def is_academic(self):
        return self.role == Role.ACADEMIC

    @property
    def is_industrial(self):
        return self.role == Role.INDUSTRIAL

    @property
    def is_coordinator(self):
        return self.role == Role.COORDINATOR
