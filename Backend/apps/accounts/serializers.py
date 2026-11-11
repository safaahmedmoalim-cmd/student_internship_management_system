from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.crypto import get_random_string
from rest_framework import serializers

from apps.students.serializers import StudentProfileSerializer
from apps.supervisors.serializers import AcademicProfileSerializer, IndustrialProfileSerializer

from .models import AuditLog, Department, Role, SystemSetting, User

PROFILE_SERIALIZERS = {
    Role.STUDENT: StudentProfileSerializer,
    Role.ACADEMIC: AcademicProfileSerializer,
    Role.INDUSTRIAL: IndustrialProfileSerializer,
}

# Profile fields a user may change on their own (identity fields such as registration
# number, staff number, department and organization are managed by the administrator).
SELF_EDITABLE_PROFILE_FIELDS = {
    Role.STUDENT: ['first_name', 'last_name', 'phone_number'],
    Role.ACADEMIC: ['first_name', 'last_name', 'phone_number'],
    Role.INDUSTRIAL: ['first_name', 'last_name', 'phone_number', 'job_title'],
}


def generate_temporary_password():
    """12 characters with upper, lower and digits - passes the password validators."""
    while True:
        pw = get_random_string(12, 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789')
        if any(c.isdigit() for c in pw) and any(c.isupper() for c in pw) and any(c.islower() for c in pw):
            return pw


def _check_password(password, user, field='password'):
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({field: list(exc.messages)})


def _unique_ci(model_field, value, instance, message):
    qs = User.objects.filter(**{f'{model_field}__iexact': value})
    if instance is not None:
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise serializers.ValidationError(message)
    return value


# -----------------------------------------------------------------------------
# Reading users
# -----------------------------------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'role_label', 'full_name', 'is_active', 'date_joined',
                  'last_login', 'profile']
        read_only_fields = fields

    def get_profile(self, user):
        cls = PROFILE_SERIALIZERS.get(user.role)
        profile = user.profile
        return cls(profile).data if cls and profile else None


# -----------------------------------------------------------------------------
# Self-service
# -----------------------------------------------------------------------------
class StudentRegistrationSerializer(serializers.Serializer):
    """Workflow 5.1 - a student creates their own account."""
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    registration_number = serializers.CharField(max_length=40)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    department = serializers.PrimaryKeyRelatedField(queryset=Department.objects.all())
    academic_year = serializers.CharField(max_length=10)

    def validate_username(self, value):
        value = value.strip()
        UnicodeUsernameValidator()(value)
        return _unique_ci('username', value, None, 'This username is taken.')

    def validate_email(self, value):
        return _unique_ci('email', value.strip().lower(), None, 'An account with this email already exists.')

    def validate(self, attrs):
        if not SystemSetting.load().allow_student_registration:
            raise serializers.ValidationError('Student self-registration is currently closed. '
                                              'Please contact the administrator.')
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        _check_password(attrs['password'], User(username=attrs['username'], email=attrs['email']))
        profile_fields = ['registration_number', 'first_name', 'last_name', 'phone_number', 'department',
                          'academic_year']
        profile_data = {f: attrs[f] for f in profile_fields if f in attrs}
        profile_data['department'] = attrs['department'].pk
        profile = StudentProfileSerializer(data=profile_data)
        if not profile.is_valid():
            raise serializers.ValidationError(profile.errors)
        attrs['_profile'] = profile
        return attrs

    @transaction.atomic
    def create(self, validated):
        user = User.objects.create_user(username=validated['username'], email=validated['email'],
                                        password=validated['password'], role=Role.STUDENT)
        validated['_profile'].save(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(help_text='Username or email address')
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, attrs):
        user = authenticate(request=self.context.get('request'), username=attrs['username'],
                            password=attrs['password'])
        if user is None:
            raise serializers.ValidationError(
                'Incorrect username/email or password, or the account has been deactivated.')
        attrs['user'] = user
        return attrs


class ProfileUpdateSerializer(serializers.Serializer):
    """PATCH /auth/me/ - email plus the role's self-editable profile fields."""
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=80, required=False)
    last_name = serializers.CharField(max_length=80, required=False)
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    job_title = serializers.CharField(max_length=120, required=False)

    def validate_email(self, value):
        return _unique_ci('email', value.strip().lower(), self.instance, 'An account with this email already exists.')

    @transaction.atomic
    def update(self, user, validated):
        if 'email' in validated:
            user.email = validated['email']
            user.save(update_fields=['email'])
        profile = user.profile
        allowed = SELF_EDITABLE_PROFILE_FIELDS.get(user.role, [])
        changed = [f for f in allowed if f in validated]
        if profile and changed:
            for f in changed:
                setattr(profile, f, validated[f].strip())
            profile.save(update_fields=changed)
        return user


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        if not self.context['request'].user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'New passwords do not match.'})
        _check_password(attrs['new_password'], self.context['request'].user, 'new_password')
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return attrs


# -----------------------------------------------------------------------------
# Administrator: user management
# -----------------------------------------------------------------------------
class AdminUserSerializer(serializers.ModelSerializer):
    """Create / edit any account. `profile` holds the role-specific fields, e.g. for a student:
    {"registration_number", "first_name", "last_name", "phone_number", "department", "academic_year"}.
    Leave `password` empty when creating to generate a temporary one (returned once)."""

    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    profile = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'is_active', 'password', 'profile']
        extra_kwargs = {'username': {'validators': []}, 'email': {'validators': []}}

    def validate_username(self, value):
        value = value.strip()
        return _unique_ci('username', value, self.instance, 'This username is taken.')

    def validate_email(self, value):
        return _unique_ci('email', value.strip().lower(), self.instance, 'An account with this email already exists.')

    def validate(self, attrs):
        instance = self.instance
        role = attrs.get('role') or (instance.role if instance else None)
        if instance is not None and 'role' in attrs and attrs['role'] != instance.role:
            raise serializers.ValidationError({'role': 'The role of an existing account cannot be changed.'})
        if role is None:
            raise serializers.ValidationError({'role': 'Choose a role.'})

        profile_data = attrs.pop('profile', None)
        cls = PROFILE_SERIALIZERS.get(role)
        self._profile_serializer = None
        if cls:
            existing = instance.profile if instance else None
            if existing is None and profile_data is None:
                raise serializers.ValidationError({'profile': f'Profile details are required for a {Role(role).label}.'})
            if profile_data is not None:
                ps = cls(existing, data=profile_data, partial=existing is not None)
                if not ps.is_valid():
                    raise serializers.ValidationError({'profile': ps.errors})
                self._profile_serializer = ps

        password = attrs.get('password')
        if password:
            probe = instance or User(username=attrs.get('username', ''), email=attrs.get('email', ''))
            _check_password(password, probe)
        return attrs

    @transaction.atomic
    def create(self, validated):
        password = validated.pop('password', '')
        self.generated_password = None
        if not password:
            password = self.generated_password = generate_temporary_password()
        user = User.objects.create_user(password=password, **validated)
        if self._profile_serializer:
            self._profile_serializer.save(user=user)
        return user

    @transaction.atomic
    def update(self, user, validated):
        password = validated.pop('password', '')
        for field, value in validated.items():
            setattr(user, field, value)
        if password:
            user.set_password(password)
        user.save()
        if self._profile_serializer:
            self._profile_serializer.save()
        return user


class AdminPasswordResetSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=False, allow_blank=True,
                                         help_text='Leave empty to generate a temporary password.')


class DepartmentSerializer(serializers.ModelSerializer):
    student_count = serializers.IntegerField(read_only=True)
    supervisor_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ['id', 'department_name', 'department_code', 'description', 'student_count', 'supervisor_count']


class AuditLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'username', 'action', 'description', 'timestamp', 'ip_address']
        read_only_fields = fields


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = ['institution_name', 'allow_student_registration', 'required_logbook_weeks', 'updated_at']
        read_only_fields = ['updated_at']
