from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, viewsets

from apps.accounts.audit import log_action
from apps.accounts.models import Role
from apps.accounts.permissions import IsAdministratorOrReadOnly
from apps.notifications.services import Type, notify

from .models import Announcement


class AnnouncementSerializer(serializers.ModelSerializer):
    administrator_name = serializers.CharField(source='administrator.full_name', read_only=True, default=None)
    target_audience_label = serializers.CharField(source='get_target_audience_display', read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Announcement
        fields = ['id', 'title', 'message', 'target_audience', 'target_audience_label', 'publication_date',
                  'expiry_date', 'is_expired', 'administrator_name']
        read_only_fields = ['id']
        extra_kwargs = {'publication_date': {'required': False}}

    def validate(self, attrs):
        pub = attrs.get('publication_date') or getattr(self.instance, 'publication_date', None) or timezone.now()
        expiry = attrs.get('expiry_date', getattr(self.instance, 'expiry_date', None))
        if expiry and expiry < timezone.localdate(pub):
            raise serializers.ValidationError({'expiry_date': 'The expiry date must be after the publication date.'})
        return attrs


class AnnouncementViewSet(viewsets.ModelViewSet):
    """/api/announcements/ - module 4.9. Everyone reads what is addressed to them; the administrator
    publishes to all users or to one group and sees every announcement (including expired/scheduled)."""
    serializer_class = AnnouncementSerializer
    permission_classes = [IsAdministratorOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.role == Role.ADMIN:
            qs = Announcement.objects.select_related('administrator')
            audience = self.request.query_params.get('audience')
            if audience in Announcement.Audience.values:
                qs = qs.filter(target_audience=audience)
            return qs
        return Announcement.visible_to(user).select_related('administrator')

    def perform_create(self, serializer):
        a = serializer.save(administrator=self.request.user)
        log_action(self.request, 'announcement.publish', f'Published "{a.title}" to {a.get_target_audience_display()}.')
        users = get_user_model().objects.filter(is_active=True).exclude(pk=self.request.user.pk)
        if a.target_audience != Announcement.Audience.ALL:
            users = users.filter(role=a.target_audience)
        else:
            users = users.filter(~Q(role=Role.ADMIN))
        notify(users, f'New announcement: {a.title}', a.message[:300], Type.ANNOUNCEMENT, '/announcements')

    def perform_update(self, serializer):
        a = serializer.save()
        log_action(self.request, 'announcement.update', f'Updated announcement "{a.title}".')

    def perform_destroy(self, instance):
        log_action(self.request, 'announcement.delete', f'Deleted announcement "{instance.title}".')
        instance.delete()
