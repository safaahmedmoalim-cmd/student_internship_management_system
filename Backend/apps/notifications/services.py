"""Create in-app notifications (module 4.10)."""
from django.contrib.auth import get_user_model

from .models import Notification

Type = Notification.Type


def notify(users, title, message, notification_type, link=''):
    """Send one notification to each user. `users` may be a user, a list or a queryset; None entries are skipped."""
    if users is None:
        return []
    if isinstance(users, get_user_model()):
        users = [users]
    seen, rows = set(), []
    for user in users:
        if user is None or user.pk in seen:
            continue
        seen.add(user.pk)
        rows.append(Notification(user=user, title=title[:200], message=message,
                                 notification_type=notification_type, link=link[:255]))
    return Notification.objects.bulk_create(rows)


def notify_admins(title, message, notification_type, link=''):
    from apps.accounts.models import Role
    admins = get_user_model().objects.filter(role=Role.ADMIN, is_active=True)
    return notify(admins, title, message, notification_type, link)
