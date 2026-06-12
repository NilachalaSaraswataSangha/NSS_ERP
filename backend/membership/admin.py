from django.contrib import admin

from .models import (
    MembershipType,
    MembershipStatus,
    SanghaSevi,
)


@admin.register(MembershipType)
class MembershipTypeAdmin(admin.ModelAdmin):

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


@admin.register(MembershipStatus)
class MembershipStatusAdmin(admin.ModelAdmin):

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


@admin.register(SanghaSevi)
class SanghaSeviAdmin(admin.ModelAdmin):

    list_display = (
        "sangha_sevi_id",
        "person",
        "organization",
        "membership_type",
        "membership_status",
    )

    search_fields = (
        "sangha_sevi_id",
    )

    list_filter = (
        "membership_type",
        "membership_status",
    )