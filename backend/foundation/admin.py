from django.contrib import admin

from .models import (
    OrganizationType,
    Organization,
    Address,
    Person,
)

# Register your models here.

@admin.register(OrganizationType)
class OrganizationTypeAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )

    list_filter = (
        "is_active",
    )

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "organization_type",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )

    list_filter = (
        "organization_type",
        "is_active",
    )

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):

    list_display = (
        "address_line_1",
        "city",
        "state",
        "postal_code",
    )

    search_fields = (
        "address_line_1",
        "city",
    )

    list_filter = (
        "state",
    )

@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):

    list_display = (
        "first_name",
        "last_name",
        "gender",
        "mobile_number",
        "is_active",
    )

    search_fields = (
        "first_name",
        "last_name",
        "mobile_number",
        "email",
    )

    list_filter = (
        "gender",
        "is_active",
    )