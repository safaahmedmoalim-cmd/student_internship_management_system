from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    STUDENT = 'student', 'Student'
    ACADEMIC = 'academic', 'Academic Supervisor'
    INDUSTRIAL = 'industrial', 'Industrial Supervisor'
    ADMIN = 'admin', 'Administrator'


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra):
        if not username:
            raise ValueError('A username is required.')
        if not email:
            raise ValueError('An email address is required.')
        user = self.model(username=username.strip(), email=self.normalize_email(email).strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, email, password=None, **extra):
        extra.setdefault('is_staff', False)
        extra.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra)

    def create_superuser(self, username, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', Role.ADMIN)
        if not extra['is_staff'] or not extra['is_superuser']:
            raise ValueError('Superuser must have is_staff=True and is_superuser=True.')
        return self._create_user(username, email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Table 1 - users. One account per person; role-specific details live in the profile tables
    (students, academic_supervisors, industrial_supervisors). `password` and `last_login` come
    from AbstractBaseUser."""

    username = models.CharField(max_length=150, unique=True, validators=[UnicodeUsernameValidator()])
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, db_index=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text='Can log in to the Django admin site.')
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['email']

    class Meta:
        db_table = 'users'
        ordering = ['username']

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    def save(self, *args, **kwargs):
        self.email = (self.email or '').strip().lower()
        super().save(*args, **kwargs)

    @property
    def profile(self):
        """The role-specific profile row, or None (administrators have no profile)."""
        attr = {Role.STUDENT: 'student_profile', Role.ACADEMIC: 'academic_profile',
                Role.INDUSTRIAL: 'industrial_profile'}.get(self.role)
        return getattr(self, attr, None) if attr else None

    @property
    def full_name(self):
        p = self.profile
        if p and (p.first_name or p.last_name):
            return f'{p.first_name} {p.last_name}'.strip()
        return self.username

    is_student = property(lambda self: self.role == Role.STUDENT)
    is_academic = property(lambda self: self.role == Role.ACADEMIC)
    is_industrial = property(lambda self: self.role == Role.INDUSTRIAL)
    is_admin_role = property(lambda self: self.role == Role.ADMIN)


class Department(models.Model):
    """Table 5 - departments."""
    department_name = models.CharField(max_length=150, unique=True)
    department_code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        db_table = 'departments'
        ordering = ['department_name']

    def __str__(self):
        return f'{self.department_code} - {self.department_name}'

    def save(self, *args, **kwargs):
        self.department_code = (self.department_code or '').strip().upper()
        super().save(*args, **kwargs)


class AuditLog(models.Model):
    """Table 17 - audit_logs. Important system activities."""
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_logs')
    action = models.CharField(max_length=60, db_index=True)
    description = models.TextField(blank=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.timestamp:%Y-%m-%d %H:%M} {self.action}'


class SystemSetting(models.Model):
    """Single-row table of settings the administrator can change from the dashboard."""
    institution_name = models.CharField(max_length=200, default='Langata Technical and Vocational College')
    allow_student_registration = models.BooleanField(default=True)
    required_logbook_weeks = models.PositiveSmallIntegerField(default=12)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'system_settings'

    def __str__(self):
        return 'System settings'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
