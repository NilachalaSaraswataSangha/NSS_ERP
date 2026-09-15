"""
Membership API router — Tier 4 read-only endpoints.

7 GET endpoints across 5 Membership tables. No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Core:          members (list with filters, detail)
  - Search:        trigram + prefix across all 3 identity tiers + name
  - Affiliations:  sakha affiliation history (per member)
  - Credentials:   parichaya patra, anumati patra (per member)
  - Timeline:      journey events (per member)

Three-tier identity model:
  - Sangha Sevi ID (SS1) — permanent NSS-wide (sangha_sevi)
  - ERP Number / Local Sakha Number (ESS1192) — Sakha-scoped,
    auto-generated (membership_sakha_affiliation)
  - Kendra Number (345/2026/2027) — annual per FY
    (parichaya_patra.document_number)

Security:
  - Audit actor FKs excluded per API convention
"""

import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.helpers import DEFAULT_LIMIT, MAX_LIMIT, row_to_model, rows_to_models
from api.schemas.membership import (
    AnumatiPatraResponse,
    JourneyEventResponse,
    MemberResponse,
    ParichayaPatraResponse,
    SakhaAffiliationResponse,
)

router = APIRouter(prefix="/api/v1/membership", tags=["membership"])


# ── Shared SQL fragments ──────────────────────────────────────────────────

# Member list/detail with resolved person, type, status, org, and
# current active local_sakha_erp_id (LEFT JOIN on active affiliation).
_MEMBER_SELECT = """
    SELECT ss.sangha_sevi_pk,
           ss.sangha_sevi_id,
           ss.person_pk,
           p.person_id,
           p.first_name,
           p.middle_name,
           p.last_name,
           p.country_phone_code,
           p.mobile_number,
           p.email,
           ss.membership_type_master_data_pk,
           mt.value_code  AS membership_type_code,
           mt.value_name  AS membership_type_name,
           ss.membership_status_master_data_pk,
           ms.value_code  AS status_code,
           ms.value_name  AS status_name,
           ss.organization_pk,
           o.organization_name,
           o.organization_code,
           aff.local_sakha_erp_id,
           ss.joining_date,
           ss.renewal_due_date,
           ss.remarks,
           ss.is_active
    FROM   nss.sangha_sevi ss
    JOIN   nss.person p
           ON p.person_pk = ss.person_pk
    JOIN   nss.master_data mt
           ON mt.master_data_pk = ss.membership_type_master_data_pk
    JOIN   nss.master_data ms
           ON ms.master_data_pk = ss.membership_status_master_data_pk
    JOIN   nss.organization o
           ON o.organization_pk = ss.organization_pk
    LEFT JOIN nss.membership_sakha_affiliation aff
           ON aff.sangha_sevi_pk = ss.sangha_sevi_pk
          AND aff.effective_to IS NULL
"""


# ═══════════════════════════════════════════════════════════════════════════
# 1. MEMBERS (core read)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/members", response_model=list[MemberResponse])
def list_members(
    type_code: str | None = Query(
        None, description="Filter by membership type (REGULAR, PROBATIONARY, etc.)"
    ),
    status_code: str | None = Query(
        None, description="Filter by status value_code"
    ),
    org_code: str | None = Query(
        None, description="Filter by organization_code (e.g. SKH1)"
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max rows"),
    offset: int = Query(0, ge=0, description="Rows to skip"),
    conn=Depends(get_connection),
) -> list[MemberResponse]:
    """
    List all active members with resolved person, type, status,
    organization, and current local_sakha_erp_id.

    Optionally filter by type_code, status_code, or org_code.
    Supports pagination via limit/offset (default 100, max 500).
    """
    sql = _MEMBER_SELECT + " WHERE ss.is_active = TRUE"
    params: list = []

    if type_code is not None:
        sql += " AND mt.value_code = %s"
        params.append(type_code)
    if status_code is not None:
        sql += " AND ms.value_code = %s"
        params.append(status_code)
    if org_code is not None:
        sql += " AND o.organization_code = %s"
        params.append(org_code)

    sql += " ORDER BY p.first_name, p.last_name"
    sql += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return rows_to_models(cur, MemberResponse)


@router.get(
    "/members/{sangha_sevi_pk}",
    response_model=MemberResponse,
)
def get_member(
    sangha_sevi_pk: UUID,
    conn=Depends(get_connection),
) -> MemberResponse:
    """Get a single member by PK with full resolved context."""
    sql = _MEMBER_SELECT + " WHERE ss.sangha_sevi_pk = %s AND ss.is_active = TRUE"

    with conn.cursor() as cur:
        cur.execute(sql, (str(sangha_sevi_pk),))
        result = row_to_model(cur, MemberResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Member not found")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# 2. SEARCH
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/search", response_model=list[MemberResponse])
def search_members(
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
        description="Search term — matches against Sangha Sevi ID (prefix), "
        "Person ID (prefix), ERP Number (prefix), name (trigram), "
        "mobile number (prefix), email (prefix), "
        "or Kendra Number (prefix)",
    ),
    conn=Depends(get_connection),
) -> list[MemberResponse]:
    """
    Search active members across all three identity tiers plus name,
    mobile number, and email.

    Uses PostgreSQL trigram similarity (pg_trgm) on first_name and
    last_name for fuzzy matching. If the query contains '.' or '@'
    (email-like), trigram runs on the portion before the first
    separator to avoid false positives (e.g. "aniket.mishra" uses
    "aniket" for name matching, full string for email prefix).
    Also matches exact prefix on sangha_sevi_id, person_id,
    local_sakha_erp_id, mobile_number, email, and parichaya_patra
    document_number (Kendra Number). Results ordered by trigram
    similarity (best match first), limited to 50 results.
    """
    # For trigram: strip email-like suffix so "aniket.mishra" → "aniket"
    name_q = re.split(r'[.@]', q)[0] if ('.' in q or '@' in q) else q

    sql = (
        _MEMBER_SELECT
        + """
        WHERE ss.is_active = TRUE
          AND (
              ss.sangha_sevi_id ILIKE %s
              OR p.person_id ILIKE %s
              OR aff.local_sakha_erp_id ILIKE %s
              OR similarity(p.first_name, %s) > 0.45
              OR similarity(p.last_name, %s) > 0.45
              OR p.mobile_number ILIKE %s
              OR p.email ILIKE %s
              OR EXISTS (
                  SELECT 1 FROM nss.parichaya_patra pp
                  WHERE  pp.sangha_sevi_pk = ss.sangha_sevi_pk
                    AND  pp.document_number ILIKE %s
              )
          )
        ORDER BY similarity(p.first_name, %s) DESC,
                 p.first_name, p.last_name
        LIMIT 50
    """
    )

    prefix_pattern = f"{q}%"

    with conn.cursor() as cur:
        cur.execute(sql, (
            prefix_pattern, prefix_pattern, prefix_pattern,
            name_q, name_q,
            prefix_pattern, prefix_pattern, prefix_pattern,
            name_q,
        ))
        return rows_to_models(cur, MemberResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 3. SAKHA AFFILIATIONS
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/members/{sangha_sevi_pk}/affiliations",
    response_model=list[SakhaAffiliationResponse],
)
def list_member_affiliations(
    sangha_sevi_pk: UUID,
    conn=Depends(get_connection),
) -> list[SakhaAffiliationResponse]:
    """
    List all sakha affiliations for a member (current and historical).
    Returns 404 if the member does not exist.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.sangha_sevi
            WHERE  sangha_sevi_pk = %s AND is_active = TRUE
        """, (str(sangha_sevi_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Member not found")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT msa.membership_sakha_affiliation_pk,
                   msa.sangha_sevi_pk,
                   msa.organization_pk,
                   o.organization_name,
                   o.organization_code,
                   msa.local_sakha_erp_id,
                   msa.effective_from,
                   msa.effective_to,
                   msa.affiliation_status,
                   msa.source_event_type,
                   msa.legacy_sakha_number
            FROM   nss.membership_sakha_affiliation msa
            JOIN   nss.organization o
                   ON o.organization_pk = msa.organization_pk
            WHERE  msa.sangha_sevi_pk = %s
            ORDER BY msa.effective_from DESC
        """, (str(sangha_sevi_pk),))
        return rows_to_models(cur, SakhaAffiliationResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 4. PARICHAYA PATRA (Identity Cards)
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/members/{sangha_sevi_pk}/parichaya-patra",
    response_model=list[ParichayaPatraResponse],
)
def list_member_parichaya_patra(
    sangha_sevi_pk: UUID,
    conn=Depends(get_connection),
) -> list[ParichayaPatraResponse]:
    """
    List all Parichaya Patra records for a member (current and historical).
    Includes point-in-time snapshot of affiliated Sakha and local number.
    Returns 404 if the member does not exist.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.sangha_sevi
            WHERE  sangha_sevi_pk = %s AND is_active = TRUE
        """, (str(sangha_sevi_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Member not found")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT pp.parichaya_patra_pk,
                   pp.sangha_sevi_pk,
                   pp.document_number,
                   pp.issue_date,
                   pp.valid_from,
                   pp.valid_to,
                   pp.status,
                   pp.affiliated_organization_pk,
                   o.organization_name  AS affiliated_organization_name,
                   o.organization_code  AS affiliated_organization_code,
                   pp.local_sakha_erp_id,
                   pp.document_reference,
                   pp.remarks
            FROM   nss.parichaya_patra pp
            LEFT JOIN nss.organization o
                   ON o.organization_pk = pp.affiliated_organization_pk
            WHERE  pp.sangha_sevi_pk = %s
            ORDER BY pp.valid_from DESC
        """, (str(sangha_sevi_pk),))
        return rows_to_models(cur, ParichayaPatraResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 5. ANUMATI PATRA (Probationary Credentials)
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/members/{sangha_sevi_pk}/anumati-patra",
    response_model=list[AnumatiPatraResponse],
)
def list_member_anumati_patra(
    sangha_sevi_pk: UUID,
    conn=Depends(get_connection),
) -> list[AnumatiPatraResponse]:
    """
    List all Anumati Patra records for a member.
    Returns 404 if the member does not exist.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.sangha_sevi
            WHERE  sangha_sevi_pk = %s AND is_active = TRUE
        """, (str(sangha_sevi_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Member not found")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT ap.anumati_patra_pk,
                   ap.sangha_sevi_pk,
                   ap.document_number,
                   ap.issue_date,
                   ap.valid_from,
                   ap.valid_to,
                   ap.status,
                   ap.document_reference,
                   ap.remarks
            FROM   nss.anumati_patra ap
            WHERE  ap.sangha_sevi_pk = %s
            ORDER BY ap.valid_from DESC
        """, (str(sangha_sevi_pk),))
        return rows_to_models(cur, AnumatiPatraResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 6. JOURNEY EVENTS (lifecycle timeline)
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/members/{sangha_sevi_pk}/journey",
    response_model=list[JourneyEventResponse],
)
def list_member_journey(
    sangha_sevi_pk: UUID,
    conn=Depends(get_connection),
) -> list[JourneyEventResponse]:
    """
    List all journey events for a member in chronological order.
    Returns 404 if the member does not exist.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.sangha_sevi
            WHERE  sangha_sevi_pk = %s AND is_active = TRUE
        """, (str(sangha_sevi_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Member not found")

    with conn.cursor() as cur:
        cur.execute("""
            SELECT mje.membership_journey_event_pk,
                   mje.sangha_sevi_pk,
                   mje.event_type,
                   mje.event_date,
                   mje.event_reference,
                   mje.remarks
            FROM   nss.membership_journey_event mje
            WHERE  mje.sangha_sevi_pk = %s
            ORDER BY mje.event_date ASC
        """, (str(sangha_sevi_pk),))
        return rows_to_models(cur, JourneyEventResponse)
