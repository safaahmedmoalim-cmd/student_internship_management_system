from django.conf import settings
from django.db import models


class Notification(models.Model):
    """Table 15 - notifications."""

    class Type(models.TextChoices):
        PLACEMENT = 'placement', 'Placement'
        ASSIGNMENT = 'assignment', 'Supervisor Assignment'
        LOGBOOK = 'logbook', 'Logbook'
        VISIT = 'visit', 'Supervision Visit'
        ASSESSMENT = 'assessment', 'Assessment'
        REPORT = 'report', 'Final Report'
        ANNOUNCEMENT = 'announcement', 'Announcement'
        DEADLINE = 'deadline', 'Deadline'
        ACCOUNT = 'account', 'Account'

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=15, choices=Type.choices, db_index=True)
    link = models.CharField(max_length=255, blank=True, help_text='Frontend path to open, e.g. /student/logbook')
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user}: {self.title}'
