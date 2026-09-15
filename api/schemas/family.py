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
    is_head: bool
    remarks: str | None


class FamilyGraphMemberResponse(BaseModel):
    """
    Family member with dynamically computed relationship label.

    The label is derived via graph traversal relative to the viewer,
    not stored statically.  Generation is computed from the path.
    spouse_person_pk links to the person's spouse (if any) within
    the family graph.
    """

    person_pk: UUID
    person_id: str
    first_name: str
    middle_name: str | None
    last_name: str | None
    gender_code: str | None
    relationship_label: str
    generation: int
    is_head: bool
    spouse_person_pk: UUID | None = None
    parent_person_pks: list[str] = []


class PersonMembershipSummaryResponse(BaseModel):
    """
    Lightweight membership snapshot for the Selected Person panel.

    Fetched by person_pk — bridges family tree (person-based)
    to membership (sangha_sevi-based).
    """

    sangha_sevi_id: str | None = None
    sangha_sevi_pk: UUID | None = None
    membership_type_code: str | None = None
    membership_type_name: str | None = None
    status_code: str | None = None
    status_name: str | None = None
    organization_name: str | None = None
    local_sakha_erp_id: str | None = None
    parichaya_patra_number: str | None = None
    parichaya_patra_status: str | None = None
    parichaya_patra_valid_to: date | None = None
    anumati_patra_number: str | None = None
    anumati_patra_status: str | None = None
    anumati_patra_valid_to: date | None = None


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


# ── Sakha Alignment (FAM-036 majority rule) ──────────────────────────

class SakhaAffiliationCount(BaseModel):
    """Per-Sakha member count within a family."""

    organization_pk: UUID
    organization_name: str
    organization_code: str
    member_count: int


class MemberSakhaInfo(BaseModel):
    """Per-member Sakha affiliation within a family."""

    person_pk: UUID
    person_id: str
    first_name: str
    middle_name: str | None
    last_name: str | None
    affiliated_sakha_pk: UUID | None = None
    affiliated_sakha_name: str | None = None
    affiliated_sakha_code: str | None = None
    is_home_sakha: bool | None = None      # matches family's effective (majority) Sakha?
    has_membership: bool = False


class FamilySakhaAlignmentResponse(BaseModel):
    """
    Sakha alignment analysis for a family.

    The family's effective Sakha is dynamically computed from the
    majority of its members' active affiliations (FAM-036).  The
    ``assigned_sakha_*`` fields reflect this effective (computed)
    Sakha — which equals the majority when affiliations exist, or
    falls back to the registration Sakha stored on ``family_group``.

    ``is_aligned`` is always True by design — the family follows
    the majority automatically.  Per-member ``is_home_sakha`` flags
    still indicate individual mismatches.
    """

    family_group_pk: UUID
    family_name: str

    # Effective Sakha (computed majority, fallback to stored registration)
    assigned_sakha_pk: UUID
    assigned_sakha_name: str
    assigned_sakha_code: str

    # Computed majority (same as assigned when affiliations exist)
    majority_sakha_pk: UUID | None = None
    majority_sakha_name: str | None = None
    majority_sakha_code: str | None = None

    is_aligned: bool = True   # always True — family follows majority
    total_members: int = 0
    members_with_affiliation: int = 0

    affiliations: list[SakhaAffiliationCount] = []
    members: list[MemberSakhaInfo] = []
