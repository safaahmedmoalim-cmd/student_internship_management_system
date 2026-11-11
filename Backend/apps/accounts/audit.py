"""Audit logging helper - call log_action() for every important action (security requirement 10)."""
from .models import AuditLog


def client_ip(request):
    if request is None:
        return None
    # REMOTE_ADDR only: X-Forwarded-For is client-controlled unless a trusted proxy sets it.
    return request.META.get('REMOTE_ADDR') or None


def log_action(request, action, description='', user=None):
    actor = user
    if actor is None and request is not None and getattr(request, 'user', None) and request.user.is_authenticated:
        actor = request.user
    return AuditLog.objects.create(user=actor, action=action, description=description[:2000],
                                   ip_address=client_ip(request))
