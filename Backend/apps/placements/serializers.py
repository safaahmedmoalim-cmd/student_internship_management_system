from django.urls import reverse
from django.utils import timezone
from rest_framework import serializers

from apps.organizations.models import Organization
from apps.students.serializers import StudentBriefSerializer
from apps.supervisors.serializers import AcademicBriefSerializer, IndustrialBriefSerializer

from .models import AttachmentPeriod, Placement


class AttachmentPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttachmentPeriod
        fields = ['id', 'name', 'start_date', 'end_date', 'application_deadline', 'report_deadline', 'is_active']

    def validate(self, attrs):
        start = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start and end and end <= start:
            raise serializers.ValidationError({'end_date': 'End date must be after the start date.'})
        return attrs


class OrganizationBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'organization_name', 'address', 'county', 'contact_person', 'phone_number', 'email',
                  'industry_category', 'status']
        read_only_fields = fields


class PlacementSerializer(serializers.ModelSerializer):
    """Read representation used by every role."""
    student = StudentBriefSerializer(read_only=True)
    organization = OrganizationBriefSerializer(read_only=True)
    attachment_period_name = serializers.CharField(source='attachment_period.name', read_only=True, default=None)
    application_status_label = serializers.CharField(source='get_application_status_display', read_only=True)
    attachment_status_label = serializers.CharField(source='get_attachment_status_display', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    supporting_document_url = serializers.SerializerMethodField()
    assignment = serializers.SerializerMethodField()

    class Meta:
        model = Placement
        fields = ['id', 'student', 'organization', 'attachment_period', 'attachment_period_name', 'start_date',
                  'end_date', 'application_date', 'application_status', 'application_status_label',
                  'attachment_status', 'attachment_status_label', 'withdrawal_reason', 'approval_comments',
                  'reviewed_by_name', 'reviewed_at', 'supporting_document_url', 'assignment', 'updated_at']
        read_only_fields = fields

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by else None

    def get_supporting_document_url(self, obj):
        return reverse('placement-document', args=[obj.pk]) if obj.supporting_document else None

    def get_assignment(self, obj):
        a = obj.active_assignment()
        if not a:
            return None
        return {'id': a.id, 'assigned_date': a.assigned_date,
                'academic_supervisor': AcademicBriefSerializer(a.academic_supervisor).data,
                'industrial_supervisor': IndustrialBriefSerializer(a.industrial_supervisor).data}


class PlacementApplicationSerializer(serializers.Serializer):
    """Student submits (or corrects and resubmits) placement details - module 4.2.

    Pick an existing organization with `organization`, or type the organization's details;
    an organization that is not in the directory yet is added as "Pending Verification".
    Sent as multipart/form-data when a supporting document is attached.
    """
    organization = serializers.PrimaryKeyRelatedField(
        queryset=Organization.objects.exclude(status=Organization.Status.INACTIVE), required=False, allow_null=True)
    organization_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    county = serializers.CharField(max_length=100, required=False, allow_blank=True,
                                   help_text='Organization location (county)')
    contact_person = serializers.CharField(max_length=150, required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=30, required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    industry_category = serializers.CharField(max_length=120, required=False, allow_blank=True)
    attachment_period = serializers.PrimaryKeyRelatedField(
        queryset=AttachmentPeriod.objects.filter(is_active=True), required=False, allow_null=True)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    supporting_document = serializers.FileField(required=False, allow_null=True)

    ORG_FIELDS = ['organization_name', 'address', 'county', 'contact_person', 'phone_number', 'email']

    def validate_supporting_document(self, file):
        if file:
            from apps.common.validators import attachment_extension_validator, validate_upload_size
            from django.core.exceptions import ValidationError as DjangoValidationError
            try:
                attachment_extension_validator(file)
                validate_upload_size(file)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.messages)
        return file

    def validate(self, attrs):
        if attrs['end_date'] <= attrs['start_date']:
            raise serializers.ValidationError({'end_date': 'Completion date must be after the start date.'})
        period = attrs.get('attachment_period')
        if period and self.instance is None and period.application_deadline < timezone.localdate():
            raise serializers.ValidationError(
                {'attachment_period': f'The application deadline for {period.name} has passed.'})

        if not attrs.get('organization'):
            missing = {f: 'This field is required.' for f in self.ORG_FIELDS if not (attrs.get(f) or '').strip()}
            if missing:
                raise serializers.ValidationError(missing)
            name = ' '.join(attrs['organization_name'].split())
            existing = Organization.objects.filter(organization_name__iexact=name).first()
            if existing and existing.status == Organization.Status.INACTIVE:
                raise serializers.ValidationError(
                    {'organization_name': 'This organization is not accepting attachment students.'})
            attrs['organization_name'] = name
            attrs['_existing_org'] = existing
        return attrs

    def _resolve_organization(self, attrs):
        if attrs.get('organization'):
            return attrs['organization']
        if attrs.get('_existing_org'):
            return attrs['_existing_org']
        return Organization.objects.create(
            organization_name=attrs['organization_name'], address=attrs['address'], county=attrs['county'],
            contact_person=attrs['contact_person'], phone_number=attrs['phone_number'], email=attrs['email'],
            industry_category=attrs.get('industry_category', ''), status=Organization.Status.PENDING,
        )

    def save_for(self, student, instance=None):
        attrs = self.validated_data
        placement = instance or Placement(student=student)
        placement.organization = self._resolve_organization(attrs)
        placement.attachment_period = attrs.get('attachment_period')
        placement.start_date = attrs['start_date']
        placement.end_date = attrs['end_date']
        if attrs.get('supporting_document'):
            placement.supporting_document = attrs['supporting_document']
        placement.application_status = Placement.Status.PENDING
        placement.full_clean(exclude=['student'])
        placement.save()
        return placement


class DecisionSerializer(serializers.Serializer):
    comments = serializers.CharField(required=False, allow_blank=True, default='')


class RequiredReasonSerializer(serializers.Serializer):
    comments = serializers.CharField(allow_blank=False, trim_whitespace=True)


class WithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)


class AttachmentStatusSerializer(serializers.Serializer):
    attachment_status = serializers.ChoiceField(choices=Placement.AttachmentStatus.choices)
