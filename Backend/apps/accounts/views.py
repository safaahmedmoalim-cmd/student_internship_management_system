from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.utils.dateparse import parse_date
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.services import Type, notify

from .audit import log_action
from .models import AuditLog, Department, Role, SystemSetting, User
from .permissions import IsAdministrator, IsAdministratorOrReadOnly
from .serializers import (
    AdminPasswordResetSerializer, AdminUserSerializer, AuditLogSerializer, ChangePasswordSerializer,
    DepartmentSerializer, LoginSerializer, PasswordResetConfirmSerializer, PasswordResetRequestSerializer,
    ProfileUpdateSerializer, StudentRegistrationSerializer, SystemSettingSerializer, UserSerializer,
    generate_temporary_password,
)

USER_QS = User.objects.select_related(
    'student_profile__department', 'academic_profile__department', 'industrial_profile__organization')


def tokens_for(user):
    refresh = RefreshToken.for_user(user)
    refresh['role'] = user.role
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


def revoke_all_tokens(user):
    """Log a user out everywhere (after a password change/reset or deactivation)."""
    for token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=token)


class AuthThrottleMixin:
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'auth'


# =============================================================================
# Authentication
# =============================================================================
class RegisterView(AuthThrottleMixin, APIView):
    """POST /api/auth/register/ - student self-registration (workflow 5.1)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = StudentRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_action(request, 'user.register', f'Student {user.username} registered.', user=user)
        notify(user, 'Welcome', 'Your student account has been created. Complete your profile and submit your '
                                'placement details when ready.', Type.ACCOUNT, '/student/profile')
        user = USER_QS.get(pk=user.pk)
        return Response({**tokens_for(user), 'user': UserSerializer(user).data}, status=status.HTTP_201_CREATED)


class LoginView(AuthThrottleMixin, APIView):
    """POST /api/auth/login/ {username (or email), password} -> {access, refresh, user}"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            log_action(request, 'auth.login_failed', f'Failed login for "{request.data.get("username", "")}".')
            raise ValidationError(serializer.errors)
        user = serializer.validated_data['user']
        from django.contrib.auth.models import update_last_login
        update_last_login(None, user)
        log_action(request, 'auth.login', f'{user.username} logged in.', user=user)
        user = USER_QS.get(pk=user.pk)
        return Response({**tokens_for(user), 'user': UserSerializer(user).data})


class LogoutView(APIView):
    """POST /api/auth/logout/ {refresh} - blacklists the refresh token."""

    def post(self, request):
        token = request.data.get('refresh')
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass
        log_action(request, 'auth.logout', f'{request.user.username} logged out.')
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    """GET / PATCH /api/auth/me/ - view and edit own profile."""

    def get(self, request):
        return Response(UserSerializer(USER_QS.get(pk=request.user.pk)).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request, 'user.profile_update', f'{request.user.username} updated their profile.')
        return Response(UserSerializer(USER_QS.get(pk=request.user.pk)).data)


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/ - other sessions are logged out; fresh tokens are returned."""

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        revoke_all_tokens(user)
        log_action(request, 'auth.password_change', f'{user.username} changed their password.')
        return Response(tokens_for(user))


class PasswordResetRequestView(AuthThrottleMixin, APIView):
    """POST /api/auth/password-reset/ {email} - always answers 200 so accounts cannot be discovered."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data['email'], is_active=True).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
            send_mail(
                'Password reset - Student Internship and Attachment Management System',
                f'Hello {user.full_name},\n\nUse the link below to choose a new password. '
                f'It expires in {settings.PASSWORD_RESET_TIMEOUT // 3600} hours.\n\n{link}\n\n'
                'If you did not ask for this, ignore this email.',
                settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True,
            )
            log_action(request, 'auth.password_reset_requested', f'Reset link sent to {user.username}.', user=user)
        return Response({'detail': 'If an account with that email exists, a reset link has been sent.'})


class PasswordResetConfirmView(AuthThrottleMixin, APIView):
    """POST /api/auth/password-reset/confirm/ {uid, token, new_password, confirm_password}"""
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(data['uid'])), is_active=True)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, data['token']):
            raise ValidationError({'detail': 'This reset link is invalid or has expired.'})
        from .serializers import _check_password
        _check_password(data['new_password'], user, 'new_password')
        user.set_password(data['new_password'])
        user.save(update_fields=['password'])
        revoke_all_tokens(user)
        log_action(request, 'auth.password_reset', f'{user.username} reset their password.', user=user)
        return Response({'detail': 'Your password has been reset. You can now log in.'})


# =============================================================================
# Administrator: users, departments, audit logs, settings
# =============================================================================
class UserViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                  mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """/api/users/ - register and manage every account (administrator only).

    Filters: ?role=student|academic|industrial|admin  ?is_active=true|false  ?search=
    Accounts are deactivated rather than deleted so their records stay intact.
    """
    permission_classes = [IsAdministrator]

    def get_serializer_class(self):
        return UserSerializer if self.action in ('list', 'retrieve') else AdminUserSerializer

    def get_queryset(self):
        qs = USER_QS.all()
        p = self.request.query_params
        if p.get('role') in Role.values:
            qs = qs.filter(role=p['role'])
        if p.get('is_active') in ('true', 'false'):
            qs = qs.filter(is_active=p['is_active'] == 'true')
        if p.get('search'):
            s = p['search'].strip()
            qs = qs.filter(
                Q(username__icontains=s) | Q(email__icontains=s)
                | Q(student_profile__first_name__icontains=s) | Q(student_profile__last_name__icontains=s)
                | Q(student_profile__registration_number__icontains=s)
                | Q(academic_profile__first_name__icontains=s) | Q(academic_profile__last_name__icontains=s)
                | Q(academic_profile__staff_number__icontains=s)
                | Q(industrial_profile__first_name__icontains=s) | Q(industrial_profile__last_name__icontains=s)
            )
        return qs.order_by('role', 'username')

    def create(self, request, *args, **kwargs):
        serializer = AdminUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        log_action(request, 'user.create', f'Created {user.get_role_display()} account "{user.username}".')
        notify(user, 'Account created', 'An account has been created for you by the administrator.',
               Type.ACCOUNT)
        data = UserSerializer(USER_QS.get(pk=user.pk)).data
        if serializer.generated_password:
            data['temporary_password'] = serializer.generated_password
        return Response(data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        user = self.get_object()
        serializer = AdminUserSerializer(user, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        log_action(request, 'user.update', f'Updated account "{user.username}".')
        return Response(UserSerializer(USER_QS.get(pk=user.pk)).data)

    def _set_active(self, request, active):
        user = self.get_object()
        if user == request.user and not active:
            raise ValidationError({'detail': 'You cannot deactivate your own account.'})
        user.is_active = active
        user.save(update_fields=['is_active'])
        if not active:
            revoke_all_tokens(user)
        log_action(request, 'user.activate' if active else 'user.deactivate',
                   f'{"Activated" if active else "Deactivated"} account "{user.username}".')
        return Response(UserSerializer(USER_QS.get(pk=user.pk)).data)

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        return self._set_active(request, True)

    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        return self._set_active(request, False)

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """Set a new password (or generate a temporary one). The user is logged out everywhere."""
        user = self.get_object()
        serializer = AdminPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.get('new_password') or generate_temporary_password()
        from .serializers import _check_password
        _check_password(password, user, 'new_password')
        user.set_password(password)
        user.save(update_fields=['password'])
        revoke_all_tokens(user)
        log_action(request, 'user.password_reset_by_admin', f'Reset password for "{user.username}".')
        notify(user, 'Password reset', 'Your password was reset by the administrator.', Type.ACCOUNT)
        return Response({'detail': 'Password reset.', 'temporary_password': password})


class DepartmentViewSet(viewsets.ModelViewSet):
    """/api/departments/ - everyone can read (needed for registration); the administrator manages them."""
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAdministratorOrReadOnly()]

    def get_authenticators(self):
        # The public list must work without (or with an expired) token on the registration page.
        if self.request is not None and self.request.method == 'GET' and 'pk' not in self.kwargs:
            return []
        return super().get_authenticators()

    def get_queryset(self):
        return Department.objects.annotate(
            student_count=Count('students', distinct=True),
            supervisor_count=Count('academic_supervisors', distinct=True),
        )

    def perform_create(self, serializer):
        d = serializer.save()
        log_action(self.request, 'department.create', f'Created department {d}.')

    def perform_update(self, serializer):
        d = serializer.save()
        log_action(self.request, 'department.update', f'Updated department {d}.')

    def perform_destroy(self, instance):
        name = str(instance)
        instance.delete()
        log_action(self.request, 'department.delete', f'Deleted department {name}.')


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """/api/audit-logs/ - ?action= ?user= ?search= ?date_from= ?date_to=  (latest 500)."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdministrator]

    def get_queryset(self):
        qs = AuditLog.objects.select_related('user')
        p = self.request.query_params
        if p.get('action'):
            qs = qs.filter(action__startswith=p['action'])
        if p.get('user'):
            qs = qs.filter(user_id=p['user'])
        if p.get('search'):
            qs = qs.filter(Q(description__icontains=p['search']) | Q(user__username__icontains=p['search']))
        if parse_date(p.get('date_from') or ''):
            qs = qs.filter(timestamp__date__gte=parse_date(p['date_from']))
        if parse_date(p.get('date_to') or ''):
            qs = qs.filter(timestamp__date__lte=parse_date(p['date_to']))
        return qs

    def list(self, request, *args, **kwargs):
        rows = self.get_queryset()[:500]
        return Response(self.get_serializer(rows, many=True).data)


class SystemSettingView(APIView):
    """GET / PATCH /api/settings/ - administrator only."""
    permission_classes = [IsAdministrator]

    def get(self, request):
        return Response(SystemSettingSerializer(SystemSetting.load()).data)

    def patch(self, request):
        obj = SystemSetting.load()
        serializer = SystemSettingSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_by=request.user)
        log_action(request, 'settings.update', f'Updated system settings: {", ".join(request.data.keys())}.')
        return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def public_settings(request):
    """GET /api/settings/public/ - what the login and registration pages need."""
    s = SystemSetting.load()
    return Response({'institution_name': s.institution_name,
                     'allow_student_registration': s.allow_student_registration})
