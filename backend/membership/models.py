from django.db import models

from foundation.models import (
    Person,
    Organization
)

# Create your models here.

# Model 1 - MembershipType
class MembershipType(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "membership_type"

        ordering = ["name"]

    def __str__(self):

        return self.name
    
# Model 2 - MembershipStatus
class MembershipStatus(models.Model):

    code = models.CharField(
        max_length=50,
        unique=True
    )

    name = models.CharField(
        max_length=100
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    is_active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "membership_status"

        ordering = ["name"]

    def __str__(self):

        return self.name
    

# Model 3 - SanghaSevi
class SanghaSevi(models.Model):

    sangha_sevi_id = models.CharField(
        max_length=30,
        unique=True
    )

    person = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        related_name="membership"
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        related_name="members"
    )

    membership_type = models.ForeignKey(
        MembershipType,
        on_delete=models.PROTECT
    )

    membership_status = models.ForeignKey(
        MembershipStatus,
        on_delete=models.PROTECT
    )

    joining_date = models.DateField()

    renewal_due_date = models.DateField(
        blank=True,
        null=True
    )

    remarks = models.TextField(
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "sangha_sevi"

        ordering = ["sangha_sevi_id"]

    def __str__(self):

        return (
            f"{self.sangha_sevi_id}"
        )