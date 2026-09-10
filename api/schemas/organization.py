"""
Pydantic response models for the Organization API (Tier 2).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""

from uuid import UUID

from pydantic import BaseModel


class OrganizationTypeResponse(BaseModel):
    """Organization type from nss.organization_type_master."""

    organization_type_pk: UUID
    organization_type_code: str
    organization_type_name: str
    description: str | None
    sort_order: int
    is_active: bool


class OrganizationStatusResponse(BaseModel):
    """Organization lifecycle status from nss.organization_status_master."""

    organization_status_pk: UUID
    organization_status_code: str
    organization_status_name: str
    description: str | None
    sort_order: int
    is_active: bool


class OrganizationResponse(BaseModel):
    """
    Organization with resolved type, status, and parent context.

    Includes type_name, status_name, and parent_name via JOINs so the
    UI can display the full context in a single API call. Geographic FK
    names (country, state, district) are also resolved where present.
    """

    organization_pk: UUID
    organization_id: str | None
    organization_name: str
    organization_code: str | None

    # Classification (resolved)
    organization_type_pk: UUID
    organization_type_code: str
    organization_type_name: str

    # Lifecycle (resolved)
    organization_status_pk: UUID
    organization_status_code: str
    organization_status_name: str

    # Hierarchy
    parent_organization_pk: UUID | None
    parent_organization_name: str | None

    # Inline address
    address_line_1: str | None
    address_line_2: str | None

    # Geographic context (resolved names)
    district_pk: UUID | None
    district_name: str | None
    state_pk: UUID | None
    state_name: str | None
    country_pk: UUID | None
    country_name: str | None
    city_village_pk: UUID | None
    city_village_name: str | None
    postal_code_pk: UUID | None
    postal_code: str | None

    # Coordinates
    latitude: float | None
    longitude: float | None

    is_active: bool


class OrganizationHierarchyNodeResponse(BaseModel):
    """
    Organization node in a hierarchical tree.

    Includes depth and path for rendering the full tree.
    Children are not nested — the tree is returned flat with
    depth/path fields for the UI to reconstruct the hierarchy.
    """

    organization_pk: UUID
    organization_name: str
    organization_code: str | None
    organization_type_code: str
    organization_type_name: str
    organization_status_code: str
    organization_status_name: str
    parent_organization_pk: UUID | None
    depth: int
    is_active: bool
