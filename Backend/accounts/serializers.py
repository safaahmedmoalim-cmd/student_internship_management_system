from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import ROLE_REQUIRED_FIELDS, Role, User

ROLE_FIELDS = ['adm_no', 'course', 'year', 'staff_no', 'department', 'company', 'position', 'company_location']

# Fields a user may change on their own profile (identity fields stay locked).
EDITABLE_BY_ROLE = {
    Role.STUDENT: ['name', 'phone', 'course', 'year'],
    Role.ACADEMIC: ['name', 'phone', 'department'],
    Role.INDUSTRIAL: ['name', 'phone', 'company', 'position', 'company_location'],
    Role.COORDINATOR: ['name', 'phone'],
}


class SupervisorBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'department', 'company', 'position']


class UserSerializer(serializers.ModelSerializer):
    """What the frontend receives about a user."""

    role_label = serializers.CharField(source='get_role_display', read_only=True)
    academic_supervisor = SupervisorBriefSerializer(read_only=True)
    industrial_supervisor = SupervisorBriefSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'phone', 'role', 'role_label', *ROLE_FIELDS,
                  'academic_supervisor', 'industrial_supervisor', 'date_joined']
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    access_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['name', 'email', 'phone', 'role', 'password', 'confirm_password', 'access_code', *ROLE_FIELDS]
        extra_kwargs = {f: {'required': False, 'allow_blank': True, 'allow_null': True} for f in ROLE_FIELDS}
        extra_kwargs['phone'] = {'required': False, 'allow_blank': True}
        extra_kwargs['adm_no'] = {'required': False, 'allow_blank': True, 'allow_null': True, 'validators': []}
        extra_kwargs['email'] = {'validators': []}  # uniqueness is checked case-insensitively below
        extra_kwargs['role'] = {'required': True}   # the model has a default, but sign-up must choose one

    def validate_name(self, value):
        value = value.strip()
        if len(value) < 3:
            raise serializers.ValidationError('Please enter your full name.')
        return value

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate_adm_no(self, value):
        value = (value or '').strip()
        if value and User.objects.filter(adm_no__iexact=value).exists():
            raise serializers.ValidationError('That admission number is already registered.')
        return value or None

    def validate(self, attrs):
        role = attrs.get('role')
        errors = {}

        for field, label in ROLE_REQUIRED_FIELDS[role].items():
            if not (attrs.get(field) or '').strip():
                errors[field] = f'{label} is required.'

        if role == Role.COORDINATOR:
            expected = settings.COORDINATOR_ACCESS_CODE
            if not expected:
                errors['access_code'] = 'Coordinator self-registration is disabled. Ask an administrator.'
            elif (attrs.get('access_code') or '').strip() != expected:
                errors['access_code'] = 'Invalid coordinator access code.'

        if attrs['password'] != attrs['confirm_password']:
            errors['confirm_password'] = 'Passwords do not match.'
        else:
            probe = User(email=attrs.get('email', ''), name=attrs.get('name', ''))
            try:
                validate_password(attrs['password'], user=probe)
            except DjangoValidationError as exc:
                errors['password'] = list(exc.messages)

        if errors:
            raise serializers.ValidationError(errors)

        # Only keep the fields that belong to this role.
        allowed = set(ROLE_REQUIRED_FIELDS[role])
        for field in ROLE_FIELDS:
            if field not in allowed:
                attrs.pop(field, None)
        attrs.pop('confirm_password')
        attrs.pop('access_code', None)
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    role = serializers.ChoiceField(choices=Role.choices, required=False)

    def validate(self, attrs):
        email = attrs['email'].strip().lower()
        user = authenticate(request=self.context.get('request'), email=email, password=attrs['password'])
        if user is None:
            raise serializers.ValidationError('Incorrect email or password.')
        if not user.is_active:
            raise serializers.ValidationError('This account has been disabled.')
        role = attrs.get('role')
        if role and user.role != role:
            raise serializers.ValidationError(
                f'This email is registered as {user.get_role_display()}. Choose that role and try again.')
        attrs['user'] = user
        return attrs


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['name', 'phone', 'course', 'year', 'department', 'company', 'position', 'company_location']
        extra_kwargs = {f: {'required': False} for f in fields}

    def validate(self, attrs):
        allowed = set(EDITABLE_BY_ROLE[self.instance.role])
        ignored = [f for f in attrs if f not in allowed]
        for f in ignored:
            attrs.pop(f)
        return attrs


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
        try:
            validate_password(attrs['new_password'], user=self.context['request'].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'new_password': list(exc.messages)})
        return attrs
