from django.db.models import Count, Q
from rest_framework import viewsets

from apps.accounts.audit import log_action
from apps.accounts.models import Role
from apps.accounts.permissions import IsAdministratorOrReadOnly

from .models import Organization
from .serializers import OrganizationSerializer


class OrganizationViewSet(viewsets.ModelViewSet):
    """/api/organizations/ - host organization directory (module 4.3).

    The administrator registers and manages organizations; other users only read active ones
    (students pick from this list when applying). Filters: ?status= ?county= ?search=
    """
    serializer_class = OrganizationSerializer
    permission_classes = [IsAdministratorOrReadOnly]

    def get_queryset(self):
        qs = Organization.objects.annotate(
            placement_count=Count('placements', distinct=True),
            supervisor_count=Count('industrial_supervisors', distinct=True),
        )
        user = self.request.user
        if user.role != Role.ADMIN:
            qs = qs.filter(status=Organization.Status.ACTIVE)
        p = self.request.query_params
        if p.get('status') in Organization.Status.values:
            qs = qs.filter(status=p['status'])
        if p.get('county'):
            qs = qs.filter(county__iexact=p['county'])
        if p.get('search'):
            s = p['search']
            qs = qs.filter(Q(organization_name__icontains=s) | Q(industry_category__icontains=s)
                           | Q(county__icontains=s))
        return qs

    def perform_create(self, serializer):
        org = serializer.save()
        log_action(self.request, 'organization.create', f'Registered organization "{org}".')

    def perform_update(self, serializer):
        org = serializer.save()
        log_action(self.request, 'organization.update', f'Updated organization "{org}" (status {org.status}).')

    def perform_destroy(self, instance):
        name = str(instance)
        instance.delete()
        log_action(self.request, 'organization.delete', f'Deleted organization "{name}".')
