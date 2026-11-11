from rest_framework import serializers

from apps.organizations.models import Organization
from apps.placements.models import Placement
from apps.students.serializers import StudentBriefSerializer

from .models import AcademicSupervisor, IndustrialSupervisor, SupervisorAssignment


class AcademicProfileSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.department_name', read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = AcademicSupervisor
        fields = ['id', 'staff_number', 'first_name', 'last_name', 'full_name', 'phone_number', 'department',
                  'department_name']
        extra_kwargs = {'staff_number': {'validators': []}}

    def validate_staff_number(self, value):
        value = value.strip().upper()
        qs = AcademicSupervisor.objects.filter(staff_number__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('This staff number is already registered.')
        return value


class IndustrialProfileSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all())
    organization_name = serializers.CharField(source='organization.organization_name', read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = IndustrialSupervisor
        fields = ['id', 'organization', 'organization_name', 'employee_number', 'first_name', 'last_name',
                  'full_name', 'phone_number', 'job_title']
        extra_kwargs = {'employee_number': {'required': False, 'allow_blank': True}}


class AcademicBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    department_name = serializers.CharField(source='department.department_name', read_only=True)

    class Meta:
        model = AcademicSupervisor
        fields = ['id', 'user_id', 'staff_number', 'full_name', 'email', 'phone_number', 'department_name']
        read_only_fields = fields


class IndustrialBriefSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    organization_name = serializers.CharField(source='organization.organization_name', read_only=True)

    class Meta:
        model = IndustrialSupervisor
        fields = ['id', 'user_id', 'organization', 'organization_name', 'full_name', 'email', 'phone_number',
                  'job_title']
        read_only_fields = fields


class SupervisorAssignmentSerializer(serializers.ModelSerializer):
    placement = serializers.PrimaryKeyRelatedField(queryset=Placement.objects.select_related('student', 'organization'))
    academic_supervisor = serializers.PrimaryKeyRelatedField(
        queryset=AcademicSupervisor.objects.filter(user__is_active=True))
    industrial_supervisor = serializers.PrimaryKeyRelatedField(
        queryset=IndustrialSupervisor.objects.filter(user__is_active=True))
    student_detail = StudentBriefSerializer(source='student', read_only=True)
    academic_detail = AcademicBriefSerializer(source='academic_supervisor', read_only=True)
    industrial_detail = IndustrialBriefSerializer(source='industrial_supervisor', read_only=True)
    organization_name = serializers.CharField(source='placement.organization.organization_name', read_only=True)

    class Meta:
        model = SupervisorAssignment
        fields = ['id', 'placement', 'student', 'student_detail', 'organization_name', 'academic_supervisor',
                  'academic_detail', 'industrial_supervisor', 'industrial_detail', 'assigned_date',
                  'assignment_status']
        read_only_fields = ['id', 'student', 'assigned_date', 'assignment_status']
        validators = []  # replacing an active assignment is handled by the view

    def validate(self, attrs):
        placement = attrs['placement']
        if not placement.is_running:
            raise serializers.ValidationError(
                {'placement': 'Supervisors can only be assigned to an approved, unfinished placement.'})
        industrial = attrs['industrial_supervisor']
        if industrial.organization_id != placement.organization_id:
            raise serializers.ValidationError(
                {'industrial_supervisor': f'The industrial supervisor must work at '
                                          f'{placement.organization.organization_name}.'})
        attrs['student'] = placement.student
        return attrs
