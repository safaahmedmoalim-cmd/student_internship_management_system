from rest_framework import serializers

from .models import Organization


class OrganizationSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source='get_status_display', read_only=True)
    placement_count = serializers.IntegerField(read_only=True)
    supervisor_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = ['id', 'organization_name', 'address', 'county', 'contact_person', 'phone_number', 'email',
                  'industry_category', 'status', 'status_label', 'placement_count', 'supervisor_count',
                  'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_organization_name(self, value):
        value = ' '.join(value.split())
        qs = Organization.objects.filter(organization_name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('An organization with this name already exists.')
        return value
