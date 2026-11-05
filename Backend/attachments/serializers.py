from django.conf import settings
from django.urls import reverse
from rest_framework import serializers

from accounts.models import Role, User
from accounts.serializers import SupervisorBriefSerializer

from .access import js_round, visible_students
from .constants import ACADEMIC_ASSESSMENT_TYPES, CRITERIA, INDUSTRIAL_ASSESSMENT_TYPE
from .models import (
    Announcement, ApprovalStatus, Assessment, FinalReport, LogbookEntry, Placement, Visit,
)


def _name(user):
    return user.name if user else None


class ReasonSerializer(serializers.Serializer):
    """Body for reject actions - the student sees this reason."""
    comment = serializers.CharField(allow_blank=False, trim_whitespace=True)


class OptionalCommentSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default='')


# -----------------------------------------------------------------------------
class PlacementSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_adm_no = serializers.CharField(source='student.adm_no', read_only=True)
    industrial_supervisor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.INDUSTRIAL, is_active=True), required=False, allow_null=True)
    industrial_supervisor_name = serializers.SerializerMethodField()

    class Meta:
        model = Placement
        fields = ['id', 'student', 'student_name', 'student_adm_no', 'company', 'location', 'department',
                  'start_date', 'end_date', 'industrial_supervisor', 'industrial_supervisor_name', 'status',
                  'coordinator_comment', 'decided_at', 'created_at']
        read_only_fields = ['id', 'student', 'status', 'coordinator_comment', 'decided_at', 'created_at']

    def get_industrial_supervisor_name(self, obj):
        return _name(obj.industrial_supervisor)

    def validate(self, attrs):
        if attrs['end_date'] <= attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'End date must be after the start date.'})
        user = self.context['request'].user
        if self.instance is None and Placement.objects.filter(student=user).exists():
            raise serializers.ValidationError(
                'You already have a placement. Withdraw it first if you want to submit new details.')
        return attrs


# -----------------------------------------------------------------------------
class LogbookEntrySerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_adm_no = serializers.CharField(source='student.adm_no', read_only=True)

    class Meta:
        model = LogbookEntry
        fields = ['id', 'student', 'student_name', 'student_adm_no', 'week_no', 'week_start', 'hours_worked',
                  'activities', 'skills_learned', 'status', 'industrial_comment', 'academic_comment',
                  'reviewed_at', 'created_at']
        read_only_fields = ['id', 'student', 'status', 'industrial_comment', 'academic_comment', 'reviewed_at',
                            'created_at']
        extra_kwargs = {'skills_learned': {'required': False, 'allow_blank': True}}

    def validate(self, attrs):
        user = self.context['request'].user
        if not Placement.objects.filter(student=user, status=ApprovalStatus.APPROVED).exists():
            raise serializers.ValidationError('You can add logbook entries once your placement is approved.')
        if LogbookEntry.objects.filter(student=user, week_no=attrs['week_no']).exists():
            raise serializers.ValidationError({'week_no': f"Week {attrs['week_no']} already has an entry."})
        return attrs


# -----------------------------------------------------------------------------
class FinalReportSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_adm_no = serializers.CharField(source='student.adm_no', read_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = FinalReport
        fields = ['id', 'student', 'student_name', 'student_adm_no', 'title', 'summary', 'file', 'original_name',
                  'size', 'status', 'reviewed_at', 'submitted_at', 'download_url']
        read_only_fields = ['id', 'student', 'original_name', 'size', 'status', 'reviewed_at', 'submitted_at']
        # `file` is NOT declared by hand so the model's validators (pdf/doc/docx only, max size) still apply.
        extra_kwargs = {'file': {'write_only': True}}

    def get_download_url(self, obj):
        path = reverse('final-report-download', args=[obj.pk])
        request = self.context.get('request')
        return request.build_absolute_uri(path) if request else path

    def _remember_file_details(self, validated):
        upload = validated.get('file')
        if upload is not None:
            validated['original_name'] = upload.name[:255]
            validated['size'] = upload.size
        return validated

    def create(self, validated_data):
        return super().create(self._remember_file_details(validated_data))

    def update(self, instance, validated_data):
        return super().update(instance, self._remember_file_details(validated_data))


# -----------------------------------------------------------------------------
class VisitSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=Role.STUDENT))
    student_name = serializers.CharField(source='student.name', read_only=True)
    student_adm_no = serializers.CharField(source='student.adm_no', read_only=True)
    academic_name = serializers.CharField(source='academic.name', read_only=True)

    class Meta:
        model = Visit
        fields = ['id', 'student', 'student_name', 'student_adm_no', 'academic', 'academic_name', 'visit_date',
                  'mode', 'notes', 'status', 'created_at']
        read_only_fields = ['id', 'academic', 'status', 'created_at']
        extra_kwargs = {'notes': {'required': False, 'allow_blank': True}}

    def validate_student(self, student):
        if not visible_students(self.context['request'].user).filter(pk=student.pk).exists():
            raise serializers.ValidationError('This student is not assigned to you.')
        return student


# -----------------------------------------------------------------------------
class AssessmentSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=Role.STUDENT))
    student_name = serializers.CharField(source='student.name', read_only=True)
    assessor_name = serializers.CharField(source='assessor.name', read_only=True)
    marks = serializers.IntegerField(min_value=0, max_value=100, required=False)
    assessment_type = serializers.CharField(required=False)
    ratings = serializers.JSONField(required=False)

    class Meta:
        model = Assessment
        fields = ['id', 'student', 'student_name', 'assessor', 'assessor_name', 'assessor_role', 'assessment_type',
                  'marks', 'ratings', 'comment', 'created_at']
        read_only_fields = ['id', 'assessor', 'assessor_role', 'created_at']
        extra_kwargs = {'comment': {'required': False, 'allow_blank': True}}

    def validate_student(self, student):
        if not visible_students(self.context['request'].user).filter(pk=student.pk).exists():
            raise serializers.ValidationError('This student is not assigned to you.')
        return student

    def validate(self, attrs):
        role = self.context['request'].user.role
        if role == Role.ACADEMIC:
            if attrs.get('marks') is None:
                raise serializers.ValidationError({'marks': 'Marks are required.'})
            kind = attrs.get('assessment_type') or ACADEMIC_ASSESSMENT_TYPES[0]
            if kind not in ACADEMIC_ASSESSMENT_TYPES:
                raise serializers.ValidationError(
                    {'assessment_type': f'Choose one of: {", ".join(ACADEMIC_ASSESSMENT_TYPES)}.'})
            attrs['assessment_type'] = kind
            attrs['ratings'] = {}
        elif role == Role.INDUSTRIAL:
            ratings = attrs.get('ratings')
            if not isinstance(ratings, dict):
                raise serializers.ValidationError({'ratings': 'Rate every skill from 1 to 5.'})
            clean, total = {}, 0
            for criterion in CRITERIA:
                value = ratings.get(criterion)
                if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
                    raise serializers.ValidationError({'ratings': f'"{criterion}" must be a whole number from 1 to 5.'})
                clean[criterion] = value
                total += value
            attrs['ratings'] = clean
            attrs['marks'] = js_round(total * 100 / (len(CRITERIA) * 5))
            attrs['assessment_type'] = INDUSTRIAL_ASSESSMENT_TYPE
        return attrs


# -----------------------------------------------------------------------------
class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'body', 'author', 'author_name', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']

    def get_author_name(self, obj):
        return _name(obj.author)


# -----------------------------------------------------------------------------
class StudentSummarySerializer(serializers.Serializer):
    """One row per student (queryset must come from access.students_with_summary)."""

    def to_representation(self, s):
        academic = js_round(s.academic_avg)
        industrial = js_round(s.industrial_avg)
        available = [m for m in (academic, industrial) if m is not None]
        return {
            'id': s.pk,
            'name': s.name,
            'email': s.email,
            'phone': s.phone,
            'adm_no': s.adm_no,
            'course': s.course,
            'year': s.year,
            'academic_supervisor': SupervisorBriefSerializer(s.academic_supervisor).data
            if s.academic_supervisor else None,
            'industrial_supervisor': SupervisorBriefSerializer(s.industrial_supervisor).data
            if s.industrial_supervisor else None,
            'placement_status': s.placement_status or 'none',
            'placement_company': s.placement_company,
            'approved_hours': s.approved_hours,
            'logged_hours': s.logged_hours,
            'target_hours': settings.TARGET_HOURS,
            'report_status': s.report_status,
            'academic_marks': academic,
            'industrial_marks': industrial,
            'overall_marks': js_round(sum(available) / len(available)) if available else None,
            'date_joined': s.date_joined,
        }


class AssignSerializer(serializers.Serializer):
    academic_supervisor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.ACADEMIC, is_active=True), required=False, allow_null=True)
    industrial_supervisor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=Role.INDUSTRIAL, is_active=True), required=False, allow_null=True)
