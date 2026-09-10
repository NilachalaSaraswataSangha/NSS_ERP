"""
Foundation API router — Tier 1 read-only endpoints.

17 GET endpoints across 11 Foundation tables. No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Master Data:      categories, master-data
  - System Config:    settings, sequences
  - Geographic:       countries, states, districts, cities, postal-codes,
                      postal-code-mappings
  - Runtime:          documents

field_change_log is intentionally excluded from Tier 1 — audit data
requires authentication. Deferred to Tier 5.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.schemas.foundation import (
    CategoryResponse,
    CityVillageResponse,
    CountryResponse,
    DistrictResponse,
    DocumentResponse,
    MasterDataResponse,
    PostalCodeMappingResponse,
    PostalCodeResponse,
    SequenceResponse,
    SettingResponse,
    StateResponse,
)

router = APIRouter(prefix="/api/v1/foundation", tags=["foundation"])


# ── helpers ────────────────────────────────────────────────────────────────

def _rows_to_models(cur, model_class):
    """Convert cursor results to a list of Pydantic models."""
    columns = [desc[0] for desc in cur.description]
    return [model_class(**dict(zip(columns, row))) for row in cur.fetchall()]


def _row_to_model(cur, model_class):
    """Convert a single cursor result to a Pydantic model, or None."""
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row is None:
        return None
    return model_class(**dict(zip(columns, row)))


# ═══════════════════════════════════════════════════════════════════════════
# 1. MASTER DATA SUBSYSTEM
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(conn=Depends(get_connection)) -> list[CategoryResponse]:
    """List all active master categories."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT master_category_pk, category_code, category_name,
                   description, display_order, is_active
            FROM   nss.master_category
            WHERE  is_active = TRUE
            ORDER BY display_order, category_name
        """)
        return _rows_to_models(cur, CategoryResponse)


@router.get("/categories/{master_category_pk}", response_model=CategoryResponse)
def get_category(
    master_category_pk: UUID,
    conn=Depends(get_connection),
) -> CategoryResponse:
    """Get a single master category by PK."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT master_category_pk, category_code, category_name,
                   description, display_order, is_active
            FROM   nss.master_category
            WHERE  master_category_pk = %s AND is_active = TRUE
        """, (str(master_category_pk),))
        result = _row_to_model(cur, CategoryResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return result


@router.get("/master-data", response_model=list[MasterDataResponse])
def list_master_data(
    category_code: str | None = Query(None, description="Filter by category code"),
    category_pk: UUID | None = Query(None, description="Filter by category PK"),
    conn=Depends(get_connection),
) -> list[MasterDataResponse]:
    """
    List all active master data values.

    Optionally filter by category_code or category_pk.
    If both are provided, category_pk takes precedence.
    """
    base_sql = """
        SELECT md.master_data_pk, md.master_category_pk,
               mc.category_code, mc.category_name,
               md.value_code, md.value_name,
               md.description, md.display_order, md.is_active
        FROM   nss.master_data md
        JOIN   nss.master_category mc
               ON mc.master_category_pk = md.master_category_pk
        WHERE  md.is_active = TRUE
          AND  mc.is_active = TRUE
    """
    params: list = []

    if category_pk is not None:
        base_sql += " AND md.master_category_pk = %s"
        params.append(str(category_pk))
    elif category_code is not None:
        base_sql += " AND mc.category_code = %s"
        params.append(category_code)

    base_sql += """
        ORDER BY mc.display_order, mc.category_name,
                 md.display_order, md.value_name
    """

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, MasterDataResponse)


@router.get("/master-data/{master_data_pk}", response_model=MasterDataResponse)
def get_master_data(
    master_data_pk: UUID,
    conn=Depends(get_connection),
) -> MasterDataResponse:
    """Get a single master data value by PK (with category context)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT md.master_data_pk, md.master_category_pk,
                   mc.category_code, mc.category_name,
                   md.value_code, md.value_name,
                   md.description, md.display_order, md.is_active
            FROM   nss.master_data md
            JOIN   nss.master_category mc
                   ON mc.master_category_pk = md.master_category_pk
            WHERE  md.master_data_pk = %s
              AND  md.is_active = TRUE
              AND  mc.is_active = TRUE
        """, (str(master_data_pk),))
        result = _row_to_model(cur, MasterDataResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Master data value not found")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# 2. SYSTEM CONFIGURATION SUBSYSTEM
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/settings", response_model=list[SettingResponse])
def list_settings(conn=Depends(get_connection)) -> list[SettingResponse]:
    """List all active system settings."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT system_setting_pk, setting_key, setting_value,
                   description, data_type, is_active
            FROM   nss.system_setting
            WHERE  is_active = TRUE
            ORDER BY setting_key
        """)
        return _rows_to_models(cur, SettingResponse)


@router.get("/settings/{setting_key}", response_model=SettingResponse)
def get_setting_by_key(
    setting_key: str,
    conn=Depends(get_connection),
) -> SettingResponse:
    """
    Get a single system setting by its business key.

    Settings are consumed by code using their key name
    (e.g., CURRENT_MEMBERSHIP_YEAR), not their UUID.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT system_setting_pk, setting_key, setting_value,
                   description, data_type, is_active
            FROM   nss.system_setting
            WHERE  setting_key = %s AND is_active = TRUE
        """, (setting_key,))
        result = _row_to_model(cur, SettingResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Setting not found")
        return result


@router.get("/sequences", response_model=list[SequenceResponse])
def list_sequences(conn=Depends(get_connection)) -> list[SequenceResponse]:
    """
    List all active ID sequence configurations.

    Infrastructure/verification endpoint. current_value is excluded —
    it's infrastructure state, not consumer data.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id_sequence_master_pk, sequence_code, sequence_name,
                   prefix, padding_length,
                   description, is_active
            FROM   nss.id_sequence_master
            WHERE  is_active = TRUE
            ORDER BY sequence_code
        """)
        return _rows_to_models(cur, SequenceResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 3. GEOGRAPHIC SUBSYSTEM
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/countries", response_model=list[CountryResponse])
def list_countries(conn=Depends(get_connection)) -> list[CountryResponse]:
    """List all active countries."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT country_pk, country_code, country_name,
                   display_order, is_active
            FROM   nss.country
            WHERE  is_active = TRUE
            ORDER BY display_order, country_name
        """)
        return _rows_to_models(cur, CountryResponse)


@router.get("/countries/{country_pk}", response_model=CountryResponse)
def get_country(
    country_pk: UUID,
    conn=Depends(get_connection),
) -> CountryResponse:
    """Get a single country by PK."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT country_pk, country_code, country_name,
                   display_order, is_active
            FROM   nss.country
            WHERE  country_pk = %s AND is_active = TRUE
        """, (str(country_pk),))
        result = _row_to_model(cur, CountryResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Country not found")
        return result


@router.get("/states", response_model=list[StateResponse])
def list_states(
    country_pk: UUID | None = Query(None, description="Filter by parent country"),
    conn=Depends(get_connection),
) -> list[StateResponse]:
    """
    List all active states/provinces.

    Optionally filter by parent country PK.
    """
    base_sql = """
        SELECT s.state_pk, s.country_pk,
               c.country_code, c.country_name,
               s.state_code, s.state_name,
               s.display_order, s.is_active
        FROM   nss.state s
        JOIN   nss.country c ON c.country_pk = s.country_pk
        WHERE  s.is_active = TRUE
          AND  c.is_active = TRUE
    """
    params: list = []

    if country_pk is not None:
        base_sql += " AND s.country_pk = %s"
        params.append(str(country_pk))

    base_sql += " ORDER BY c.display_order, s.display_order, s.state_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, StateResponse)


@router.get("/states/{state_pk}", response_model=StateResponse)
def get_state(
    state_pk: UUID,
    conn=Depends(get_connection),
) -> StateResponse:
    """Get a single state by PK (with country context)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT s.state_pk, s.country_pk,
                   c.country_code, c.country_name,
                   s.state_code, s.state_name,
                   s.display_order, s.is_active
            FROM   nss.state s
            JOIN   nss.country c ON c.country_pk = s.country_pk
            WHERE  s.state_pk = %s
              AND  s.is_active = TRUE
              AND  c.is_active = TRUE
        """, (str(state_pk),))
        result = _row_to_model(cur, StateResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="State not found")
        return result


@router.get("/districts", response_model=list[DistrictResponse])
def list_districts(
    state_pk: UUID | None = Query(None, description="Filter by parent state"),
    conn=Depends(get_connection),
) -> list[DistrictResponse]:
    """
    List all active districts.

    Optionally filter by parent state PK. Without filter, returns all
    active districts (~700+ for India alone).
    """
    base_sql = """
        SELECT d.district_pk, d.state_pk,
               s.state_name,
               d.district_code, d.district_name,
               d.display_order, d.is_active
        FROM   nss.district d
        JOIN   nss.state s ON s.state_pk = d.state_pk
        WHERE  d.is_active = TRUE
          AND  s.is_active = TRUE
    """
    params: list = []

    if state_pk is not None:
        base_sql += " AND d.state_pk = %s"
        params.append(str(state_pk))

    base_sql += " ORDER BY s.state_name, d.display_order, d.district_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, DistrictResponse)


@router.get("/districts/{district_pk}", response_model=DistrictResponse)
def get_district(
    district_pk: UUID,
    conn=Depends(get_connection),
) -> DistrictResponse:
    """Get a single district by PK (with state context)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT d.district_pk, d.state_pk,
                   s.state_name,
                   d.district_code, d.district_name,
                   d.display_order, d.is_active
            FROM   nss.district d
            JOIN   nss.state s ON s.state_pk = d.state_pk
            WHERE  d.district_pk = %s
              AND  d.is_active = TRUE
              AND  s.is_active = TRUE
        """, (str(district_pk),))
        result = _row_to_model(cur, DistrictResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="District not found")
        return result


@router.get("/cities", response_model=list[CityVillageResponse])
def list_cities(
    district_pk: UUID | None = Query(None, description="Filter by parent district"),
    conn=Depends(get_connection),
) -> list[CityVillageResponse]:
    """
    List all active cities/villages.

    Optionally filter by parent district PK.
    Currently returns empty — no seed data by design.
    """
    base_sql = """
        SELECT cv.city_village_pk, cv.district_pk,
               d.district_name,
               cv.city_village_code, cv.city_village_name,
               cv.city_village_type,
               cv.display_order, cv.is_active
        FROM   nss.city_village cv
        JOIN   nss.district d ON d.district_pk = cv.district_pk
        WHERE  cv.is_active = TRUE
          AND  d.is_active = TRUE
    """
    params: list = []

    if district_pk is not None:
        base_sql += " AND cv.district_pk = %s"
        params.append(str(district_pk))

    base_sql += " ORDER BY d.district_name, cv.display_order, cv.city_village_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, CityVillageResponse)


@router.get("/postal-codes", response_model=list[PostalCodeResponse])
def list_postal_codes(
    state_pk: UUID | None = Query(None, description="Filter by state"),
    country_pk: UUID | None = Query(None, description="Filter by country"),
    conn=Depends(get_connection),
) -> list[PostalCodeResponse]:
    """
    List all active postal codes.

    Optionally filter by state or country.
    """
    base_sql = """
        SELECT pc.postal_code_pk, pc.country_pk, pc.state_pk,
               s.state_name,
               pc.postal_code, pc.post_office_name, pc.is_active
        FROM   nss.postal_code pc
        JOIN   nss.state s ON s.state_pk = pc.state_pk
        WHERE  pc.is_active = TRUE
    """
    params: list = []

    if state_pk is not None:
        base_sql += " AND pc.state_pk = %s"
        params.append(str(state_pk))
    elif country_pk is not None:
        base_sql += " AND pc.country_pk = %s"
        params.append(str(country_pk))

    base_sql += " ORDER BY pc.postal_code"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, PostalCodeResponse)


@router.get("/postal-code-mappings", response_model=list[PostalCodeMappingResponse])
def list_postal_code_mappings(
    city_village_pk: UUID | None = Query(None, description="Filter by city/village"),
    postal_code_pk: UUID | None = Query(None, description="Filter by postal code"),
    conn=Depends(get_connection),
) -> list[PostalCodeMappingResponse]:
    """
    List city/village to postal code mappings.

    Pure junction table — no is_active, no soft-delete.
    Currently returns empty — no seed data by design.
    """
    base_sql = """
        SELECT m.city_village_postal_code_map_pk,
               m.city_village_pk, cv.city_village_name,
               m.postal_code_pk, pc.postal_code
        FROM   nss.city_village_postal_code_map m
        JOIN   nss.city_village cv ON cv.city_village_pk = m.city_village_pk
        JOIN   nss.postal_code pc ON pc.postal_code_pk = m.postal_code_pk
    """
    conditions: list[str] = []
    params: list = []

    if city_village_pk is not None:
        conditions.append("m.city_village_pk = %s")
        params.append(str(city_village_pk))
    if postal_code_pk is not None:
        conditions.append("m.postal_code_pk = %s")
        params.append(str(postal_code_pk))

    if conditions:
        base_sql += " WHERE " + " AND ".join(conditions)

    base_sql += " ORDER BY cv.city_village_name, pc.postal_code"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, PostalCodeMappingResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 4. RUNTIME TABLES (Intentionally Empty at Tier 1 Launch)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    document_type_code: str | None = Query(None, description="Filter by document type code"),
    conn=Depends(get_connection),
) -> list[DocumentResponse]:
    """
    List all active documents.

    Tier 1 exposes only currently useful fields. FK fields
    (person_pk, uploaded_by_sangha_sevi_pk) excluded — targets
    don't exist yet. Response shape revisited when consuming
    modules arrive.
    Currently returns empty — documents are runtime data.
    """
    base_sql = """
        SELECT document_master_pk, document_type_code,
               document_number, document_name, storage_path,
               file_size_bytes, mime_type, version, checksum,
               description, is_active
        FROM   nss.document_master
        WHERE  is_active = TRUE
    """
    params: list = []

    if document_type_code is not None:
        base_sql += " AND document_type_code = %s"
        params.append(document_type_code)

    base_sql += " ORDER BY document_type_code, document_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, DocumentResponse)
