from django.db import models
from django.db.models.functions import Lower


class Organization(models.Model):
    """Table 6 - organizations. Host organizations offering attachment opportunities."""

    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        PENDING = 'pending', 'Pending Verification'   # added by a student, not yet checked by the administrator
        INACTIVE = 'inactive', 'Inactive'

    organization_name = models.CharField(max_length=200)
    address = models.CharField(max_length=255)
    county = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField()
    industry_category = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organizations'
        ordering = ['organization_name']
        constraints = [
            models.UniqueConstraint(Lower('organization_name'), name='unique_organization_name_ci'),
        ]

    def __str__(self):
        return self.organization_name
