from django.db import models
from foundation.models import Person

# Create your models here.

# Model 1 - FamilyGroup
class FamilyGroup(models.Model):

    family_id = models.CharField(
        max_length=30,
        unique=True
    )

    family_name = models.CharField(
        max_length=255
    )

    is_active = models.BooleanField(
        default=True
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

        db_table = "family_group"

        ordering = ["family_name"]

    def __str__(self):

        return (
            f"{self.family_name}"
        )

# Model 2 - FamilyMembership
class FamilyMembership(models.Model):

    RELATIONSHIP_CHOICES = [

        ("HEAD", "Head"),

        ("SPOUSE", "Spouse"),

        ("CHILD", "Child"),

        ("PARENT", "Parent"),

        ("SIBLING", "Sibling"),

        ("OTHER", "Other"),

    ]

    family = models.ForeignKey(
        FamilyGroup,
        on_delete=models.CASCADE,
        related_name="members"
    )

    person = models.ForeignKey(
        Person,
        on_delete=models.PROTECT,
        related_name="family_memberships"
    )

    relationship = models.CharField(
        max_length=20,
        choices=RELATIONSHIP_CHOICES
    )

    is_primary = models.BooleanField(
        default=False
    )

    start_date = models.DateField(
        null=True,
        blank=True
    )

    end_date = models.DateField(
        null=True,
        blank=True
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

        db_table = "family_membership"

        ordering = ["family"]

    def __str__(self):

        return (
            f"{self.person} - {self.relationship}"
        )