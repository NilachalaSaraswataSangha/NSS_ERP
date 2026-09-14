"""
Family API router — Tier 4 read-only endpoints.

4 GET endpoints across 3 Family tables. No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Core:     families (list with filters, detail)
  - Members:  family members (relationships per family)
  - History:  family head history (per family)

Security:
  - Audit actor FKs excluded per API convention
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.helpers import DEFAULT_LIMIT, MAX_LIMIT, row_to_model, rows_to_models
from api.schemas.family import (
    FamilyGroupResponse,
    FamilyHeadHistoryResponse,
    FamilyMemberResponse,
)

router = APIRouter(prefix="/api/v1/family", tags=["family"])


# ── Shared SQL fragments ──────────────────────────────────────────────────

_FAMILY_SELECT = """
    SELECT fg.family_group_pk,
           fg.family_id,
           fg.family_name,
           fg.family_status_master_data_pk,
           st.value_code  AS status_code,
           st.value_name  AS status_name,
           fg.sakha_organization_pk,
           o.organization_name  AS sakha_name,
           o.organization_code  AS sakha_code,
           fg.formed_date,
           fg.remarks,
           fg.is_active
    FROM   nss.family_group fg
    JOIN   nss.master_data st
           ON st.master_data_pk = fg.family_status_master_data_pk
    JOIN   nss.organization o
           ON o.organization_pk = fg.sakha_organization_pk
"""

_MEMBER_SELECT = """
    SELECT fr.family_relationship_pk,
           fr.family_group_pk,
           fr.person_pk,
           p.person_id,
           p.first_name,
           p.middle_name,
           p.last_name,
           fr.relationship_type_master_data_pk,
           rt.value_code  AS relationship_type_code,
           rt.value_name  AS relationship_type_name,
           fr.effective_from,
           fr.effective_to,
           fr.is_current,
           fr.remarks
    FROM   nss.family_relationship fr
    JOIN   nss.person p
           ON p.person_pk = fr.person_pk
    JOIN   nss.master_data rt
           ON rt.master_data_pk = fr.relationship_type_master_data_pk
"""

_HEAD_SELECT = """
    SELECT fh.family_head_history_pk,
           fh.family_group_pk,
           fh.person_pk,
           p.person_id,
           p.first_name,
           p.middle_name,
           p.last_name,
           fh.effective_from,
           fh.effective_to,
           fh.remarks
    FROM   nss.family_head_history fh
    JOIN   nss.person p
           ON p.person_pk = fh.person_pk
"""


# ═══════════════════════════════════════════════════════════════════════════
# 1. FAMILIES (core read)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/families", response_model=list[FamilyGroupResponse])
def list_families(
    sakha_code: str | None = Query(
        None, description="Filter by Sakha organization_code (e.g. SKH1)"
    ),
    status_code: str | None = Query(
        None, description="Filter by status value_code"
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max rows"),
    offset: int = Query(0, ge=0, description="Rows to skip"),
    conn=Depends(get_connection),
) -> list[FamilyGroupResponse]:
    """
    List all active families with resolved status and Sakha context.

    Optionally filter by sakha_code or status_code. Supports pagination
    via limit/offset (default 100, max 500).
    """
    sql = _FAMILY_SELECT + " WHERE fg.is_active = TRUE"
    params: list = []

    if sakha_code is not None:
        sql += " AND o.organization_code = %s"
        params.append(sakha_code)
    if status_code is not None:
        sql += " AND st.value_code = %s"
        params.append(status_code)

    sql += " ORDER BY fg.family_name"
    sql += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return rows_to_models(cur, FamilyGroupResponse)


@router.get(
    "/families/{family_group_pk}",
    response_model=FamilyGroupResponse,
)
def get_family(
    family_group_pk: UUID,
    conn=Depends(get_connection),
) -> FamilyGroupResponse:
    """Get a single family by PK with resolved context."""
    sql = _FAMILY_SELECT + " WHERE fg.family_group_pk = %s AND fg.is_active = TRUE"

    with conn.cursor() as cur:
        cur.execute(sql, (str(family_group_pk),))
        result = row_to_model(cur, FamilyGroupResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Family not found")
        return result


# ═══════════════════════════════════════════════════════════════════════════
# 2. FAMILY MEMBERS (relationships)
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/families/{family_group_pk}/members",
    response_model=list[FamilyMemberResponse],
)
def list_family_members(
    family_group_pk: UUID,
    conn=Depends(get_connection),
) -> list[FamilyMemberResponse]:
    """
    List all current members of a family with resolved person and
    relationship type context. Returns 404 if the family does not exist.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.family_group
            WHERE  family_group_pk = %s AND is_active = TRUE
        """, (str(family_group_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Family not found")

    sql = (
        _MEMBER_SELECT
        + " WHERE fr.family_group_pk = %s AND fr.is_current = TRUE"
        + " ORDER BY rt.display_order, p.first_name"
    )

    with conn.cursor() as cur:
        cur.execute(sql, (str(family_group_pk),))
        return rows_to_models(cur, FamilyMemberResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 3. FAMILY HEAD HISTORY
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/families/{family_group_pk}/head-history",
    response_model=list[FamilyHeadHistoryResponse],
)
def list_family_head_history(
    family_group_pk: UUID,
    conn=Depends(get_connection),
) -> list[FamilyHeadHistoryResponse]:
    """
    List family head history (current and past). Returns 404 if
    the family does not exist.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.family_group
            WHERE  family_group_pk = %s AND is_active = TRUE
        """, (str(family_group_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Family not found")

    sql = (
        _HEAD_SELECT
        + " WHERE fh.family_group_pk = %s"
        + " ORDER BY fh.effective_from DESC"
    )

    with conn.cursor() as cur:
        cur.execute(sql, (str(family_group_pk),))
        return rows_to_models(cur, FamilyHeadHistoryResponse)
