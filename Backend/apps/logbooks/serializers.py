from datetime import timedelta

from django.urls import reverse
from rest_framework import serializers

from apps.students.models import Student
from apps.students.serializers import StudentBriefSerializer
from apps.supervisors.access import visible_students

from .models import Attendance, Logbook, LogbookReview


class LogbookReviewSerializer(serializers.ModelSerializer):
    supervisor_name = serializers.CharField(source='supervisor.full_name', read_only=True)
    supervisor_role_label = serializers.CharField(source='get_supervisor_role_display', read_only=True)
    review_status_label = serializers.CharField(source='get_review_status_display', read_only=True)

    class Meta:
        model = LogbookReview
        fields = ['id', 'supervisor', 'supervisor_name', 'supervisor_role', 'supervisor_role_label',
                  'review_status', 'review_status_label', 'comments', 'review_date']
        read_only_fields = fields


class LogbookSerializer(serializers.ModelSerializer):
    student = StudentBriefSerializer(read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    reviews = LogbookReviewSerializer(many=True, read_only=True)
    attachment_url = serializers.SerializerMethodField()
    attachment_name = serializers.SerializerMethodField()

    class Meta:
        model = Logbook
        fields = ['id', 'student', 'placement', 'week_number', 'start_date', 'end_date', 'activities',
                  'skills_acquired', 'challenges', 'solutions', 'attachment_url', 'attachment_name',
                  'submission_date', 'status', 'status_label', 'reviews', 'updated_at']
        read_only_fields = fields

    def get_attachment_url(self, obj):
        return reverse('logbook-attachment', args=[obj.pk]) if obj.attachment else None

    def get_attachment_name(self, obj):
        return obj.attachment.name.rsplit('/', 1)[-1] if obj.attachment else None


class LogbookWriteSerializer(serializers.ModelSerializer):
    """Student creates or corrects a weekly entry (module 4.5). multipart/form-data when attaching a file."""

    class Meta:
        model = Logbook
        fields = ['week_number', 'start_date', 'end_date', 'activities', 'skills_acquired', 'challenges',
                  'solutions', 'attachment']
        extra_kwargs = {f: {'required': False, 'allow_blank': True}
                        for f in ['skills_acquired', 'challenges', 'solutions']}
        extra_kwargs['attachment'] = {'required': False, 'allow_null': True}

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end:
            if end < start:
                raise serializers.ValidationError({'end_date': 'Week ending date cannot be before the starting date.'})
            if end - start > timedelta(days=6):
                raise serializers.ValidationError({'end_date': 'A logbook entry covers at most one week (7 days).'})
        placement = self.context['placement']
        if start and start < placement.start_date - timedelta(days=6):
            raise serializers.ValidationError({'start_date': 'This week is before your attachment started.'})
        week = attrs.get('week_number', getattr(self.instance, 'week_number', None))
        clash = Logbook.objects.filter(placement=placement, week_number=week)
        if self.instance:
            clash = clash.exclude(pk=self.instance.pk)
        if clash.exists():
            raise serializers.ValidationError({'week_number': f'You already have an entry for week {week}.'})
        return attrs


class ReviewDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[LogbookReview.Status.APPROVED, LogbookReview.Status.REJECTED])
    comments = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, attrs):
        if attrs['decision'] == LogbookReview.Status.REJECTED and not attrs['comments'].strip():
            raise serializers.ValidationError({'comments': 'Explain what the student must correct.'})
        return attrs


# -----------------------------------------------------------------------------
class AttendanceSerializer(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())
    student_name = serializers.CharField(source='student.full_name', read_only=True)
    registration_number = serializers.CharField(source='student.registration_number', read_only=True)
    attendance_status_label = serializers.CharField(source='get_attendance_status_display', read_only=True)
    recorded_by_name = serializers.CharField(source='recorded_by.full_name', read_only=True, default=None)

    class Meta:
        model = Attendance
        fields = ['id', 'student', 'student_name', 'registration_number', 'attendance_date', 'attendance_status',
                  'attendance_status_label', 'remarks', 'recorded_by_name', 'created_at']
        read_only_fields = ['id', 'created_at']
        validators = []  # (student, date) uniqueness is handled as an update in the view

    def validate_student(self, student):
        if not visible_students(self.context['request'].user).filter(pk=student.pk).exists():
            raise serializers.ValidationError('This student is not assigned to you.')
        return student


class AttendanceBulkItemSerializer(serializers.Serializer):
    student = serializers.IntegerField()
    attendance_status = serializers.ChoiceField(choices=Attendance.Status.choices)
    remarks = serializers.CharField(required=False, allow_blank=True, default='', max_length=255)


class AttendanceBulkSerializer(serializers.Serializer):
    attendance_date = serializers.DateField()
    records = AttendanceBulkItemSerializer(many=True)
