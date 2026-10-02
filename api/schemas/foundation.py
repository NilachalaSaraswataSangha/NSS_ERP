"""
Pydantic response models for the Foundation API (Tier 1).

All models exclude audit columns (created_at, updated_at, deleted_at)
per the project's API convention established in Tier 0.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


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
    applicable_modules: list[str] | None
    display_order: int
    is_active: bool


class CreateMasterDataRequest(BaseModel):
    """POST /api/v1/foundation/master-data — add a value to a category."""

    category_code: str = Field(..., min_length=1, description="Parent category code, e.g. DOCUMENT_TYPE")
    value_code: str = Field(..., min_length=1, max_length=50, description="Unique code within the category")
    value_name: str = Field(..., min_length=1, max_length=150)
    description: str | None = Field(None)
    display_order: int = Field(0, ge=0)
    applicable_modules: list[str] | None = Field(None, description="NULL = applies to all modules")


class UpdateMasterDataRequest(BaseModel):
    """PATCH /api/v1/foundation/master-data/{master_data_pk} — edit a value."""

    value_name: str | None = Field(None, min_length=1, max_length=150)
    description: str | None = Field(None)
    display_order: int | None = Field(None, ge=0)
    applicable_modules: list[str] | None = Field(None)


# ---------------------------------------------------------------------------
# Festival Reference Calendar Subsystem (SOL-ARCH-013)
# ---------------------------------------------------------------------------

class FestivalMasterResponse(BaseModel):
    """A festival/occasion that can carry authoritative calendar dates."""

    festival_master_pk: UUID
    festival_code: str
    festival_name: str
    festival_name_odia: str | None
    lunar_basis: str | None
    is_erp_reference_date: bool
    description: str | None
    display_order: int
    is_active: bool


class FestivalCalendarDateResponse(BaseModel):
    """
    A single festival/year observed-date row, with festival context via
    JOIN so the admin calendar screen can render without a second call.
    """

    festival_calendar_date_pk: UUID
    festival_master_pk: UUID
    festival_code: str
    festival_name: str
    calendar_year: int
    observed_date: date
    is_confirmed: bool
    source_reference: str | None
    remarks: str | None
    is_active: bool


class CreateFestivalCalendarDateRequest(BaseModel):
    """
    POST /api/v1/foundation/festival-calendar-dates — record an observed
    date for a festival/year. Requires FOUNDATION_CALENDAR_MANAGE.

    observed_date is always administrator-entered data (almanac/panchang,
    Kendra Sangha circular) — never computed (SOL-ARCH-013 §3).
    """

    festival_code: str = Field(..., min_length=1, description="e.g. DOLA_PURNIMA")
    calendar_year: int = Field(..., ge=1900, le=2200)
    observed_date: date
    is_confirmed: bool = Field(False, description="TRUE only once confirmed by the Kendra Sangha")
    source_reference: str | None = Field(None, max_length=200)
    remarks: str | None = None


class UpdateFestivalCalendarDateRequest(BaseModel):
    """
    PATCH /api/v1/foundation/festival-calendar-dates/{pk} — correct or
    confirm an existing row. Requires FOUNDATION_CALENDAR_MANAGE.
    """

    observed_date: date | None = None
    is_confirmed: bool | None = None
    source_reference: str | None = Field(None, max_length=200)
    remarks: str | None = None


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


class UpdateSettingRequest(BaseModel):
    """PATCH /api/v1/foundation/settings/{setting_key} — edit an existing setting."""

    setting_value: str = Field(..., min_length=1, description="New value; validated against the setting's data_type")
    description: str | None = Field(None, max_length=500)


class CreateSettingRequest(BaseModel):
    """POST /api/v1/foundation/settings — add a new setting."""

    setting_key: str = Field(..., min_length=1, max_length=100, description="Unique business key, e.g. CURRENT_MEMBERSHIP_YEAR")
    setting_value: str = Field(..., min_length=1)
    data_type: str = Field("STRING", description="STRING | INTEGER | BOOLEAN | DATE | JSON")
    description: str | None = Field(None, max_length=500)


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


class CreateSequenceRequest(BaseModel):
    """POST /api/v1/foundation/sequences — add a new ID sequence."""

    sequence_code: str = Field(..., min_length=1, max_length=50, description="Unique code, e.g. SAKHA")
    sequence_name: str = Field(..., min_length=1, max_length=100, description="Unique display name")
    prefix: str = Field(..., min_length=1, max_length=20, description="Identifier prefix, e.g. SKH")
    padding_length: int = Field(8, ge=0, le=12, description="Zero-pad width for the numeric part (0-12)")
    description: str | None = Field(None)


class UpdateSequenceRequest(BaseModel):
    """PATCH /api/v1/foundation/sequences/{sequence_code} — edit a sequence's config."""

    sequence_name: str | None = Field(None, min_length=1, max_length=100)
    prefix: str | None = Field(None, min_length=1, max_length=20)
    padding_length: int | None = Field(None, ge=0, le=12)
    description: str | None = Field(None)


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
    district_pk: UUID | None
    district_name: str | None
    city_village_code: str
    city_village_name: str
    city_village_type: str
    postal_code_pk: UUID | None
    postal_code: str | None
    display_order: int
    is_active: bool


class PostalCodeResponse(BaseModel):
    """
    Postal code with parent state context.

    Simplified Geography Model (2026-10-02): nss.post_office is retired.
    A PIN is now a single globally-unique, state-scoped row — there is
    no office-level detail (post_office_name / office_count are gone).
    country_pk is still returned for the frontend's cascade, but it is
    derived from state.country_pk, not stored on postal_code.
    """

    postal_code_pk: UUID
    country_pk: UUID
    state_pk: UUID
    state_name: str
    postal_code: str
    is_active: bool


class PostalCodeMappingResponse(BaseModel):
    """
    City/village to postal code mapping.

    SOL-ARCH-010 Amendment (2026-10-01): the former M:N junction
    table is retired. This now reads the direct
    nss.city_village.postal_code_pk FK, so each row is simply a
    city/village that has a resolved PIN (no separate mapping PK).
    """

    city_village_pk: UUID
    city_village_name: str
    postal_code_pk: UUID
    postal_code: str


class SakhaPostalCodeResponse(BaseModel):
    """
    Sakha Sangha branch linked to a postal code via
    organization.postal_code_pk. Surfaces the PIN ↔ Sakha
    relationship on the Geography page.
    """

    organization_pk: UUID
    organization_name: str
    organization_code: str | None
    postal_code_pk: UUID
    postal_code: str
    state_pk: UUID
    state_name: str


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
