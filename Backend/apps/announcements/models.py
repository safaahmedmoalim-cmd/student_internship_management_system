from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Announcement(models.Model):
    """Table 14 - announcements published by the administrator."""

    class Audience(models.TextChoices):
        ALL = 'all', 'All Users'
        STUDENTS = 'student', 'Students'
        ACADEMIC = 'academic', 'Academic Supervisors'
        INDUSTRIAL = 'industrial', 'Industrial Supervisors'

    administrator = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                      related_name='announcements')
    title = models.CharField(max_length=200)
    message = models.TextField()
    target_audience = models.CharField(max_length=12, choices=Audience.choices, default=Audience.ALL, db_index=True)
    publication_date = models.DateTimeField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'announcements'
        ordering = ['-publication_date']

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        return bool(self.expiry_date and self.expiry_date < timezone.localdate())

    @classmethod
    def visible_to(cls, user):
        """Published, unexpired announcements addressed to everyone or to the user's role."""
        return cls.objects.filter(
            Q(target_audience=cls.Audience.ALL) | Q(target_audience=user.role),
            publication_date__lte=timezone.now(),
        ).filter(Q(expiry_date__isnull=True) | Q(expiry_date__gte=timezone.localdate()))
