"""
Pydantic response models for the Family API (Tier 4).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class FamilyGroupResponse(BaseModel):
    """
    Family group with resolved status and Sakha context.

    Includes status_name and sakha_name via JOINs so the UI
    can display full context in a single API call.
    """

    family_group_pk: UUID
    family_id: str
    family_name: str

    # Status (resolved from master_data — unified STATUS category)
    family_status_master_data_pk: UUID
    status_code: str
    status_name: str

    # Sakha (resolved from organization)
    sakha_organization_pk: UUID
    sakha_name: str
    sakha_code: str | None

    formed_date: date | None
    remarks: str | None
    is_active: bool


class FamilyMemberResponse(BaseModel):
    """
    Family member (relationship) with resolved person and type context.

    Joins person for name display and master_data for relationship type.
    """

    family_relationship_pk: UUID
    family_group_pk: UUID

    # Person (resolved)
    person_pk: UUID
    person_id: str
    first_name: str
    middle_name: str | None
    last_name: str | None

    # Relationship type (resolved from master_data)
    relationship_type_master_data_pk: UUID
    relationship_type_code: str
    relationship_type_name: str

    effective_from: date
    effective_to: date | None
    is_current: bool
    remarks: str | None


class FamilyHeadHistoryResponse(BaseModel):
    """
    Family head assignment record with resolved person context.
    """

    family_head_history_pk: UUID
    family_group_pk: UUID

    # Person (resolved)
    person_pk: UUID
    person_id: str
    first_name: str
    middle_name: str | None
    last_name: str | None

    effective_from: date
    effective_to: date | None
    remarks: str | None
