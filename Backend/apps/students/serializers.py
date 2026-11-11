from rest_framework import serializers

from .models import Student


class StudentProfileSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.department_name', read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'registration_number', 'first_name', 'last_name', 'full_name', 'phone_number',
                  'department', 'department_name', 'academic_year']
        extra_kwargs = {'registration_number': {'validators': []}}  # checked case-insensitively below

    def validate_registration_number(self, value):
        value = value.strip().upper()
        qs = Student.objects.filter(registration_number__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('This registration number is already registered.')
        return value

    def validate_first_name(self, value):
        return value.strip()

    def validate_last_name(self, value):
        return value.strip()


class StudentBriefSerializer(serializers.ModelSerializer):
    """Compact student reference embedded in other records."""
    full_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    department_name = serializers.CharField(source='department.department_name', read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'registration_number', 'full_name', 'email', 'phone_number', 'department_name',
                  'academic_year']
        read_only_fields = fields
