"""
Pydantic response models for the Foundation API (Tier 1).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""

from uuid import UUID

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Master Data Subsystem
# ---------------------------------------------------------------------------

class CategoryResponse(BaseModel):
    """Master category — a logical group of related master values."""

    master_category_pk: UUID
    category_code: str
    category_name: str
    description: str | None
    display_order: int
    is_active: bool


class MasterDataResponse(BaseModel):
    """
    Master data value with parent category context.

    Includes category_code and category_name via JOIN so the UI can
    display master data with its category context in a single API call.
    """

    master_data_pk: UUID
    master_category_pk: UUID
    category_code: str
    category_name: str
    value_code: str
    value_name: str
    description: str | None
    display_order: int
    is_active: bool


# ---------------------------------------------------------------------------
# System Configuration Subsystem
# ---------------------------------------------------------------------------

class SettingResponse(BaseModel):
    """System-wide configurable setting."""

    system_setting_pk: UUID
    setting_key: str
    setting_value: str
    description: str | None
    data_type: str
    is_active: bool


class SequenceResponse(BaseModel):
    """
    ID sequence configuration for generating business identifiers.

    Infrastructure/verification endpoint. current_value is excluded —
    it's infrastructure state, not consumer data.
    """

    id_sequence_master_pk: UUID
    sequence_code: str
    sequence_name: str
    prefix: str
    padding_length: int
    description: str | None
    is_active: bool


# ---------------------------------------------------------------------------
# Geographic Subsystem
# ---------------------------------------------------------------------------

class CountryResponse(BaseModel):
    """Country reference record."""

    country_pk: UUID
    country_code: str
    country_name: str
    display_order: int
    is_active: bool


class StateResponse(BaseModel):
    """
    State/province with parent country context.

    Includes country_code and country_name via JOIN.
    """

    state_pk: UUID
    country_pk: UUID
    country_code: str
    country_name: str
    state_code: str
    state_name: str
    display_order: int
    is_active: bool


class DistrictResponse(BaseModel):
    """
    District with parent state context.

    Includes state_name via JOIN. Does not include country fields —
    resolve via the state's country_pk if needed.
    """

    district_pk: UUID
    state_pk: UUID
    state_name: str
    district_code: str
    district_name: str
    display_order: int
    is_active: bool


class CityVillageResponse(BaseModel):
    """City/village with parent district context."""

    city_village_pk: UUID
    district_pk: UUID
    district_name: str
    city_village_code: str
    city_village_name: str
    city_village_type: str
    display_order: int
    is_active: bool


class PostalCodeResponse(BaseModel):
    """Postal code with parent state context."""

    postal_code_pk: UUID
    country_pk: UUID
    state_pk: UUID
    state_name: str
    postal_code: str
    post_office_name: str | None
    is_active: bool


class PostalCodeMappingResponse(BaseModel):
    """
    City/village to postal code mapping (M:N junction).

    Pure junction table — no is_active, no soft-delete.
    Includes display fields from both sides via JOIN.
    """

    city_village_postal_code_map_pk: UUID
    city_village_pk: UUID
    city_village_name: str
    postal_code_pk: UUID
    postal_code: str


# ---------------------------------------------------------------------------
# Runtime Tables (Intentionally Empty at Tier 1 Launch)
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    """
    Document master record.

    Tier 1 exposes only the currently useful fields. FK fields
    (person_pk, uploaded_by_sangha_sevi_pk) are excluded — their
    targets don't exist yet. The response shape will be revisited
    when consuming modules arrive; no assumption is made here about
    the final representation.
    """

    document_master_pk: UUID
    document_type_code: str
    document_number: str | None
    document_name: str
    storage_path: str
    file_size_bytes: int | None
    mime_type: str | None
    version: int
    checksum: str | None
    description: str | None
    is_active: bool
