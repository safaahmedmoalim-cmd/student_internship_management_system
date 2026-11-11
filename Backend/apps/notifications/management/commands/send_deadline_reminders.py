"""python manage.py send_deadline_reminders [--days 3]

Schedule this daily (cron / Task Scheduler). It notifies:
  * students without a placement when an application deadline is near,
  * students on attachment without an approved/submitted final report when the report deadline is near.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import Notification
from apps.notifications.services import Type, notify
from apps.placements.models import AttachmentPeriod, Placement
from apps.reports.models import FinalReport
from apps.students.models import Student


class Command(BaseCommand):
    help = 'Notify users about approaching attachment deadlines.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=3, help='Warn this many days before a deadline.')

    def handle(self, *args, days, **options):
        today = timezone.localdate()
        horizon = today + timedelta(days=days)
        sent = 0
        for period in AttachmentPeriod.objects.filter(is_active=True):
            if today <= period.application_deadline <= horizon:
                placed = Placement.objects.exclude(application_status__in=['rejected', 'withdrawn']) \
                    .values('student_id')
                users = [s.user for s in Student.objects.filter(user__is_active=True).exclude(pk__in=placed)
                         .select_related('user')]
                sent += len(self._send(users, f'Placement deadline: {period.application_deadline:%d %b %Y}',
                                       f'Submit your placement details for {period.name} before the deadline.'))
            if today <= period.report_deadline <= horizon:
                done = FinalReport.objects.filter(review_status__in=FinalReport.BLOCKING_STATUSES).values('placement_id')
                users = [p.student.user for p in Placement.objects.filter(
                    attachment_period=period, application_status='approved').exclude(pk__in=done)
                    .select_related('student__user')]
                sent += len(self._send(users, f'Final report deadline: {period.report_deadline:%d %b %Y}',
                                       f'Upload your final attachment report for {period.name}.'))
        self.stdout.write(self.style.SUCCESS(f'Sent {sent} reminder(s).'))

    def _send(self, users, title, message):
        # Do not repeat the same reminder on the same day.
        already = set(Notification.objects.filter(title=title, created_at__date=timezone.localdate())
                      .values_list('user_id', flat=True))
        return notify([u for u in users if u.pk not in already], title, message, Type.DEADLINE)
