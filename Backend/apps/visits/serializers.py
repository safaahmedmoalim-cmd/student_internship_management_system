from django.utils import timezone
from rest_framework import serializers

from apps.students.models import Student
from apps.students.serializers import StudentBriefSerializer
from apps.supervisors.access import visible_students
from apps.supervisors.models import AcademicSupervisor

from .models import SupervisionVisit


class SupervisionVisitSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), write_only=True)
    student_detail = StudentBriefSerializer(source='student', read_only=True)
    academic_supervisor = serializers.PrimaryKeyRelatedField(
        queryset=AcademicSupervisor.objects.all(), required=False,
        help_text="Administrator only; defaults to the student's academic supervisor.")
    academic_supervisor_name = serializers.CharField(source='academic_supervisor.full_name', read_only=True)
    organization_name = serializers.CharField(source='organization.organization_name', read_only=True, default=None)
    visit_type_label = serializers.CharField(source='get_visit_type_display', read_only=True)
    visit_status_label = serializers.CharField(source='get_visit_status_display', read_only=True)

    class Meta:
        model = SupervisionVisit
        fields = ['id', 'student', 'student_detail', 'academic_supervisor', 'academic_supervisor_name',
                  'organization', 'organization_name', 'visit_date', 'visit_type', 'visit_type_label',
                  'meeting_link', 'objectives', 'observations', 'recommendations', 'visit_status',
                  'visit_status_label', 'created_at', 'updated_at']
        read_only_fields = ['id', 'organization', 'observations', 'recommendations', 'visit_status',
                            'created_at', 'updated_at']
        extra_kwargs = {'meeting_link': {'required': False, 'allow_blank': True}}

    def validate_student(self, student):
        if not visible_students(self.context['request'].user).filter(pk=student.pk).exists():
            raise serializers.ValidationError('This student is not assigned to you.')
        return student

    def validate_visit_date(self, value):
        if self.instance is None and value < timezone.now():
            raise serializers.ValidationError('Choose a future date and time.')
        return value


class RescheduleSerializer(serializers.Serializer):
    visit_date = serializers.DateTimeField()
    reason = serializers.CharField(required=False, allow_blank=True, default='')

    def validate_visit_date(self, value):
        if value < timezone.now():
            raise serializers.ValidationError('Choose a future date and time.')
        return value


class VisitReportSerializer(serializers.Serializer):
    """Record what happened at a visit (marks it completed)."""
    observations = serializers.CharField()
    recommendations = serializers.CharField(required=False, allow_blank=True, default='')


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')
