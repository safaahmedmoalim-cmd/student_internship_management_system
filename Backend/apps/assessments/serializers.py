import json

from django.urls import reverse
from rest_framework import serializers

from apps.students.models import Student
from apps.students.serializers import StudentBriefSerializer
from apps.supervisors.access import visible_students

from .models import MAX_SCORE, Assessment


class CriteriaField(serializers.Field):
    """Accepts a JSON object, or a JSON string (multipart forms that also upload an evaluation form)."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except ValueError:
                raise serializers.ValidationError('Send the scores as a JSON object.')
        if not isinstance(data, dict):
            raise serializers.ValidationError('Send the scores as an object: {"criterion": score}.')
        return data

    def to_representation(self, value):
        return value


class AssessmentSerializer(serializers.ModelSerializer):
    student = StudentBriefSerializer(read_only=True)
    supervisor_name = serializers.CharField(source='supervisor.full_name', read_only=True)
    assessment_type_label = serializers.CharField(source='get_assessment_type_display', read_only=True)
    assessment_status_label = serializers.CharField(source='get_assessment_status_display', read_only=True)
    evaluation_form_url = serializers.SerializerMethodField()

    class Meta:
        model = Assessment
        fields = ['id', 'student', 'placement', 'supervisor', 'supervisor_name', 'supervisor_role', 'assessment_type',
                  'assessment_type_label', 'assessment_criteria', 'marks', 'comments', 'recommendations',
                  'evaluation_form_url', 'assessment_date', 'assessment_status', 'assessment_status_label',
                  'released_at', 'updated_at']
        read_only_fields = fields

    def get_evaluation_form_url(self, obj):
        return reverse('assessment-evaluation-form', args=[obj.pk]) if obj.evaluation_form else None


class AssessmentWriteSerializer(serializers.Serializer):
    """Supervisor records an assessment. `submit=false` saves a draft (In Progress); `submit=true`
    marks it Completed, after which only the administrator can re-open or release it."""
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all(), required=False)
    assessment_criteria = CriteriaField()
    comments = serializers.CharField(required=False, allow_blank=True, default='')
    recommendations = serializers.CharField(required=False, allow_blank=True, default='')
    evaluation_form = serializers.FileField(required=False, allow_null=True)
    submit = serializers.BooleanField(required=False, default=False)

    def validate_student(self, student):
        if not visible_students(self.context['request'].user).filter(pk=student.pk).exists():
            raise serializers.ValidationError('This student is not assigned to you.')
        return student

    def validate_evaluation_form(self, file):
        if file:
            from django.core.exceptions import ValidationError as DjangoValidationError

            from apps.common.validators import document_extension_validator, validate_upload_size
            try:
                document_extension_validator(file)
                validate_upload_size(file)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.messages)
        return file

    def validate(self, attrs):
        if self.instance is None and not attrs.get('student'):
            raise serializers.ValidationError({'student': 'Choose a student.'})
        a_type = Assessment.TYPE_FOR_ROLE[self.context['request'].user.role]
        expected = Assessment.CRITERIA[a_type]
        scores = attrs['assessment_criteria']
        missing = [c for c in expected if c not in scores]
        unknown = [c for c in scores if c not in expected]
        if missing or unknown:
            raise serializers.ValidationError({'assessment_criteria': (
                (f'Missing: {", ".join(missing)}. ' if missing else '') +
                (f'Unknown: {", ".join(unknown)}.' if unknown else '')).strip()})
        clean = {}
        for c in expected:
            v = scores[c]
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= MAX_SCORE:
                raise serializers.ValidationError(
                    {'assessment_criteria': f'"{c}" must be a whole number from 1 to {MAX_SCORE}.'})
            clean[c] = v
        attrs['assessment_criteria'] = clean
        attrs['assessment_type'] = a_type
        attrs['marks'] = Assessment.compute_marks(clean)
        return attrs
