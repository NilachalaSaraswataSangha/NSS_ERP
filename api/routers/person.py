"""
Person API router — Tier 3 read-only endpoints.

4 GET endpoints across 2 Person tables. No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Core:       persons (list with filters, detail)
  - Addresses:  person addresses (per person)
  - Search:     trigram-based name/ID search

Security:
  - aadhaar_encrypted and aadhaar_hash are NEVER returned (PER-BR-081)
  - Only aadhaar_last4 is exposed for masked display
  - Audit actor FKs excluded per API convention
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.helpers import DEFAULT_LIMIT, MAX_LIMIT, row_to_model, rows_to_models
from api.schemas.person import (
    PersonAddressResponse,
    PersonResponse,
    PersonSummaryResponse,
)

router = APIRouter(prefix="/api/v1/person", tags=["person"])


# ── Shared SQL fragments ──────────────────────────────────────────────────

# Full person SELECT with resolved master-data names.
# LEFT JOINs on master_data: gender, marital_status, blood_group,
# emergency_relationship — all nullable FKs.
_PERSON_DETAIL_SELECT = """
    SELECT p.person_pk,
           p.person_id,
           p.first_name,
           p.middle_name,
           p.last_name,
           p.date_of_birth,
           p.date_of_death,
           p.gender_master_data_pk,
           g.value_code   AS gender_code,
           g.value_name   AS gender_name,
           p.marital_status_master_data_pk,
           ms.value_code  AS marital_status_code,
           ms.value_name  AS marital_status_name,
           p.blood_group_master_data_pk,
           bg.value_code  AS blood_group_code,
           bg.value_name  AS blood_group_name,
           p.country_phone_code,
           p.mobile_number,
           p.email,
           p.aadhaar_last4,
           p.photo_document_master_pk,
           p.emergency_contact_name,
           p.emergency_contact_phone,
           p.emergency_relationship_master_data_pk,
           er.value_code  AS emergency_relationship_code,
           er.value_name  AS emergency_relationship_name,
           p.remarks,
           p.is_active
    FROM   nss.person p
    LEFT JOIN nss.master_data g
           ON g.master_data_pk = p.gender_master_data_pk
    LEFT JOIN nss.master_data ms
           ON ms.master_data_pk = p.marital_status_master_data_pk
    LEFT JOIN nss.master_data bg
           ON bg.master_data_pk = p.blood_group_master_data_pk
    LEFT JOIN nss.master_data er
           ON er.master_data_pk = p.emergency_relationship_master_data_pk
"""

# Compact person SELECT for list/search results (no Aadhaar, emergency, photo).
_PERSON_SUMMARY_SELECT = """
    SELECT p.person_pk,
           p.person_id,
           p.first_name,
           p.middle_name,
           p.last_name,
           p.date_of_birth,
           p.date_of_death,
           g.value_code   AS gender_code,
           g.value_name   AS gender_name,
           ms.value_code  AS marital_status_code,
           ms.value_name  AS marital_status_name,
           bg.value_code  AS blood_group_code,
           bg.value_name  AS blood_group_name,
           p.country_phone_code,
           p.mobile_number,
           p.email,
           p.is_active
    FROM   nss.person p
    LEFT JOIN nss.master_data g
           ON g.master_data_pk = p.gender_master_data_pk
    LEFT JOIN nss.master_data ms
           ON ms.master_data_pk = p.marital_status_master_data_pk
    LEFT JOIN nss.master_data bg
           ON bg.master_data_pk = p.blood_group_master_data_pk
"""

# Address SELECT with resolved location context through the
# city_village_postal_code_map junction → city_village + postal_code
# + district + state + country geographic chain.
_ADDRESS_SELECT = """
    SELECT pa.person_address_pk,
           pa.person_pk,
           pa.address_type_master_data_pk,
           at.value_code  AS address_type_code,
           at.value_name  AS address_type_name,
           pa.address_line_1,
           pa.address_line_2,
           pa.landmark,
           pa.city_village_postal_code_map_pk,
           cv.city_village_name,
           pc.postal_code,
           d.district_name,
           s.state_name,
           c.country_name,
           pa.is_primary,
           pa.remarks,
           pa.is_active
    FROM   nss.person_address pa
    JOIN   nss.master_data at
           ON at.master_data_pk = pa.address_type_master_data_pk
    JOIN   nss.city_village_postal_code_map cvm
           ON cvm.city_village_postal_code_map_pk
              = pa.city_village_postal_code_map_pk
    LEFT JOIN nss.city_village cv
           ON cv.city_village_pk = cvm.city_village_pk
    LEFT JOIN nss.postal_code pc
           ON pc.postal_code_pk = cvm.postal_code_pk
    LEFT JOIN nss.district d
           ON d.district_pk = cv.district_pk
    LEFT JOIN nss.state s
           ON s.state_pk = d.state_pk
    LEFT JOIN nss.country c
           ON c.country_pk = s.country_pk
"""


# ═══════════════════════════════════════════════════════════════════════════
# 1. PERSONS (core read)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/persons", response_model=list[PersonSummaryResponse])
def list_persons(
    gender_code: str | None = Query(
        None, description="Filter by gender value_code (e.g. MALE, FEMALE)"
    ),
    marital_status_code: str | None = Query(
        None, description="Filter by marital status value_code"
    ),
    blood_group_code: str | None = Query(
        None, description="Filter by blood group value_code"
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    conn=Depends(get_connection),
) -> list[PersonSummaryResponse]:
    """
    List all active persons with resolved master-data context.

    Optionally filter by gender_code, marital_status_code, or
    blood_group_code. Returns a compact summary (no Aadhaar,
    emergency, or photo fields). Supports pagination via limit/offset
    (default 100, max 500).
    """
    sql = _PERSON_SUMMARY_SELECT + " WHERE p.is_active = TRUE"
    params: list = []

    if gender_code is not None:
        sql += " AND g.value_code = %s"
        params.append(gender_code)
    if marital_status_code is not None:
        sql += " AND ms.value_code = %s"
        params.append(marital_status_code)
    if blood_group_code is not None:
        sql += " AND bg.value_code = %s"
        params.append(blood_group_code)

    sql += " ORDER BY p.first_name, p.last_name"
    sql += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return rows_to_models(cur, PersonSummaryResponse)


@router.get(
    "/persons/{person_pk}",
    response_model=PersonResponse,
)
def get_person(
    person_pk: UUID,
    conn=Depends(get_connection),
) -> PersonResponse:
    """
    Get a single person by PK with full resolved context.

    Includes Aadhaar last-4 (masked), emergency contact, and photo
    FK. Never returns aadhaar_encrypted or aadhaar_hash.
    """
    sql = _PERSON_DETAIL_SELECT + " WHERE p.person_pk = %s AND p.is_active = TRUE"

    with conn.cursor() as cur:
        cur.execute(sql, (str(person_pk),))
        result = row_to_model(cur, PersonResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Person not found")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# 2. ADDRESSES
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/persons/{person_pk}/addresses",
    response_model=list[PersonAddressResponse],
)
def list_person_addresses(
    person_pk: UUID,
    conn=Depends(get_connection),
) -> list[PersonAddressResponse]:
    """
    List all active addresses for a given person.

    Resolves address type, city/village, postal code, district,
    state, and country names via JOINs. Returns 404 if the person
    does not exist.
    """
    # Verify the person exists
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.person
            WHERE  person_pk = %s AND is_active = TRUE
        """, (str(person_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Person not found")

    sql = (
        _ADDRESS_SELECT
        + " WHERE pa.person_pk = %s AND pa.is_active = TRUE"
        + " ORDER BY pa.is_primary DESC, at.value_name"
    )

    with conn.cursor() as cur:
        cur.execute(sql, (str(person_pk),))
        return rows_to_models(cur, PersonAddressResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 3. SEARCH
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/search", response_model=list[PersonSummaryResponse])
def search_persons(
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Search term — matches against first_name (trigram), "
        "last_name (trigram), person_id, or mobile_number",
    ),
    conn=Depends(get_connection),
) -> list[PersonSummaryResponse]:
    """
    Search active persons by name, person_id, or mobile number.

    Uses PostgreSQL trigram similarity (pg_trgm) on first_name for
    fuzzy matching. Also matches exact prefix on person_id and
    mobile_number. Results ordered by trigram similarity (best match
    first), limited to 50 results.
    """
    sql = (
        _PERSON_SUMMARY_SELECT
        + """
        WHERE p.is_active = TRUE
          AND (
              p.first_name %% %s
              OR p.last_name %% %s
              OR p.person_id ILIKE %s
              OR p.mobile_number ILIKE %s
          )
        ORDER BY similarity(p.first_name, %s) DESC,
                 p.first_name, p.last_name
        LIMIT 50
    """
    )

    prefix_pattern = f"{q}%"

    with conn.cursor() as cur:
        cur.execute(sql, (q, q, prefix_pattern, prefix_pattern, q))
        return rows_to_models(cur, PersonSummaryResponse)
