"""
Pydantic response models for the Person API (Tier 3).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Sensitive fields excluded per PER-BR-081:
  - aadhaar_encrypted (BYTEA)  — never exposed
  - aadhaar_hash (VARCHAR)     — never exposed
Only aadhaar_last4 is returned for masked display.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class PersonResponse(BaseModel):
    """
    Person with resolved master-data context.

    Includes gender_name, marital_status_name, blood_group_name, and
    emergency_relationship_name via JOINs so the UI can display full
    context in a single API call.
    """

    # Identity
    person_pk: UUID
    person_id: str

    # Demographics
    first_name: str
    middle_name: str | None
    last_name: str | None
    date_of_birth: date | None
    date_of_death: date | None

    # Gender (resolved)
    gender_master_data_pk: UUID | None
    gender_code: str | None
    gender_name: str | None

    # Marital status (resolved)
    marital_status_master_data_pk: UUID | None
    marital_status_code: str | None
    marital_status_name: str | None

    # Blood group (resolved)
    blood_group_master_data_pk: UUID | None
    blood_group_code: str | None
    blood_group_name: str | None

    # Contact
    country_phone_code: str | None
    mobile_number: str | None
    email: str | None

    # Sensitive identity — masked display only
    aadhaar_last4: str | None

    # Photo
    photo_document_master_pk: UUID | None

    # Emergency contact (resolved)
    emergency_contact_name: str | None
    emergency_contact_phone: str | None
    emergency_relationship_master_data_pk: UUID | None
    emergency_relationship_code: str | None
    emergency_relationship_name: str | None

    # Other
    remarks: str | None

    # Lifecycle
    is_active: bool


class PersonSummaryResponse(BaseModel):
    """
    Lightweight Person summary for list/search results.

    Omits Aadhaar, emergency contact, and photo details to keep
    list payloads compact.
    """

    person_pk: UUID
    person_id: str
    first_name: str
    middle_name: str | None
    last_name: str | None
    date_of_birth: date | None
    date_of_death: date | None
    gender_code: str | None
    gender_name: str | None
    marital_status_code: str | None
    marital_status_name: str | None
    blood_group_code: str | None
    blood_group_name: str | None
    country_phone_code: str | None
    mobile_number: str | None
    email: str | None
    is_active: bool


class PersonAddressResponse(BaseModel):
    """
    Person address with resolved location context.

    Resolves address_type via master_data and location via the
    city_village_postal_code_map junction → city_village + postal_code
    + district + state + country chain.
    """

    person_address_pk: UUID
    person_pk: UUID

    # Address type (resolved)
    address_type_master_data_pk: UUID
    address_type_code: str
    address_type_name: str

    # Address fields
    address_line_1: str
    address_line_2: str | None
    landmark: str | None

    # Location (resolved through junction and geographic chain)
    city_village_postal_code_map_pk: UUID
    city_village_name: str | None
    postal_code: str | None
    district_name: str | None
    state_name: str | None
    country_name: str | None

    is_primary: bool
    remarks: str | None
    is_active: bool
