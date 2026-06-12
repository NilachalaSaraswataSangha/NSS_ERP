from django.db import models


class OrganizationType(models.Model):

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

        db_table = "organization_type"

        ordering = ["name"]

    def __str__(self):

        return self.name

class Organization(models.Model):

    organization_type = models.ForeignKey(
        OrganizationType,
        on_delete=models.PROTECT,
        related_name="organizations"
    )

    code = models.CharField(
        max_length=50,
        unique=True
    )

    name = models.CharField(
        max_length=255
    )

    short_name = models.CharField(
        max_length=100,
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

        db_table = "organization"

        ordering = ["name"]

    def __str__(self):

        return self.name

class Address(models.Model):

    address_line_1 = models.CharField(
        max_length=255
    )

    address_line_2 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    city = models.CharField(
        max_length=100
    )

    district = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    state = models.CharField(
        max_length=100
    )

    postal_code = models.CharField(
        max_length=20
    )

    country = models.CharField(
        max_length=100,
        default="India"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    class Meta:

        db_table = "address"

        ordering = ["city"]

    def __str__(self):

        return (
            f"{self.address_line_1}, "
            f"{self.city}"
        )
    
class Person(models.Model):

    first_name = models.CharField(
        max_length=100
    )

    middle_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    last_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    gender = models.CharField(
        max_length=20
    )

    date_of_birth = models.DateField(
        blank=True,
        null=True
    )

    mobile_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    address = models.ForeignKey(
        Address,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="persons"
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

        db_table = "person"

        ordering = [
            "first_name",
            "last_name"
        ]

    def __str__(self):

        full_name = (
            f"{self.first_name} "
            f"{self.last_name or ''}"
        )

        return full_name.strip()