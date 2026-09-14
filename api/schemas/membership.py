"""
Pydantic response models for the Membership API (Tier 4).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Three-tier identity model:
  - Sangha Sevi ID (SS1) — NSS-wide, permanent, on sangha_sevi
  - ERP Number / Local Sakha Number (ESS1192) — Sakha-scoped,
    auto-generated, on membership_sakha_affiliation
  - Kendra Number (345/2026/2027) — Kendra-wide, annual,
    on parichaya_patra.document_number

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class MemberResponse(BaseModel):
    """
    Sangha Sevi (member) with resolved person, type, status, and org context.

    Includes person name, membership type name, status name, and
    organization name via JOINs. Also includes the current active
    local_sakha_erp_id from membership_sakha_affiliation.
    """

    # Identity
    sangha_sevi_pk: UUID
    sangha_sevi_id: str

    # Person (resolved)
    person_pk: UUID
    person_id: str
    first_name: str
    middle_name: str | None
    last_name: str | None
    country_phone_code: str | None
    mobile_number: str | None
    email: str | None

    # Membership type (resolved from master_data)
    membership_type_master_data_pk: UUID
    membership_type_code: str
    membership_type_name: str

    # Status (resolved from master_data — unified STATUS)
    membership_status_master_data_pk: UUID
    status_code: str
    status_name: str

    # Current organization (resolved)
    organization_pk: UUID
    organization_name: str
    organization_code: str | None

    # Current Local Sakha ERP ID (from active affiliation)
    local_sakha_erp_id: str | None

    # Dates
    joining_date: date
    renewal_due_date: date | None

    remarks: str | None
    is_active: bool


class SakhaAffiliationResponse(BaseModel):
    """
    Sakha affiliation record — authoritative source of Local Sakha ERP ID.
    """

    membership_sakha_affiliation_pk: UUID
    sangha_sevi_pk: UUID

    # Organization (resolved)
    organization_pk: UUID
    organization_name: str
    organization_code: str | None

    local_sakha_erp_id: str
    effective_from: date
    effective_to: date | None
    affiliation_status: str
    source_event_type: str
    legacy_sakha_number: str | None


class ParichayaPatraResponse(BaseModel):
    """
    Parichaya Patra (Identity Card) with snapshot context.

    document_number = Kendra number (e.g., 345/2026/2027).
    affiliated_organization_name and local_sakha_erp_id are
    point-in-time snapshots of what was printed on the card.
    """

    parichaya_patra_pk: UUID
    sangha_sevi_pk: UUID
    document_number: str
    issue_date: date
    valid_from: date
    valid_to: date
    status: str

    # Snapshot: Sakha at issuance (resolved)
    affiliated_organization_pk: UUID | None
    affiliated_organization_name: str | None
    affiliated_organization_code: str | None

    # Snapshot: Local Sakha number at issuance
    local_sakha_erp_id: str | None

    document_reference: str | None
    remarks: str | None


class AnumatiPatraResponse(BaseModel):
    """
    Anumati Patra (Probationary Member Credential).
    """

    anumati_patra_pk: UUID
    sangha_sevi_pk: UUID
    document_number: str
    issue_date: date
    valid_from: date
    valid_to: date
    status: str
    document_reference: str | None
    remarks: str | None


class JourneyEventResponse(BaseModel):
    """
    Membership lifecycle journey event.
    """

    membership_journey_event_pk: UUID
    sangha_sevi_pk: UUID
    event_type: str
    event_date: date
    event_reference: str | None
    remarks: str | None
