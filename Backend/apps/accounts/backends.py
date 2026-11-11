from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class UsernameOrEmailBackend(ModelBackend):
    """Users may sign in with either their username or their email address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        login = (username or kwargs.get('email') or '').strip()
        if not login or password is None:
            return None
        user = User.objects.filter(Q(username__iexact=login) | Q(email__iexact=login)).first()
        if user is None:
            User().set_password(password)  # same work as a real check - avoids leaking which accounts exist
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
