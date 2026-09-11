"""
Organization API router — Tier 2 read-only endpoints.

6 GET endpoints across 3 Organization tables. No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Reference:   types, statuses
  - Core:        organizations (list, detail, children)
  - Navigation:  hierarchy (recursive CTE tree)

Organization depends on Foundation tables (country, state, district,
city_village, postal_code) for address resolution — these are LEFT
JOINed since address fields are nullable.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.schemas.organization import (
    OrganizationHierarchyNodeResponse,
    OrganizationResponse,
    OrganizationStatusResponse,
    OrganizationTypeResponse,
)

router = APIRouter(prefix="/api/v1/organization", tags=["organization"])


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


# ── Shared SQL fragment for the organization SELECT ──────────────────────

_ORG_SELECT = """
    SELECT o.organization_pk,
           o.organization_id,
           o.organization_name,
           o.organization_code,
           ot.organization_type_pk,
           ot.organization_type_code,
           ot.organization_type_name,
           os.organization_status_pk,
           os.organization_status_code,
           os.organization_status_name,
           o.parent_organization_pk,
           p.organization_name AS parent_organization_name,
           o.address_line_1,
           o.address_line_2,
           o.phone_number,
           o.mobile_number,
           o.email,
           o.org_email,
           o.website_url,
           o.org_website_url,
           o.youtube_channel_url,
           o.org_youtube_channel_url,
           o.district_pk,
           d.district_name,
           o.state_pk,
           s.state_name,
           o.country_pk,
           c.country_name,
           o.city_village_pk,
           cv.city_village_name,
           o.postal_code_pk,
           pc.postal_code,
           o.latitude,
           o.longitude,
           o.is_active
    FROM   nss.organization o
    JOIN   nss.organization_type_master ot
           ON ot.organization_type_pk = o.organization_type_pk
    JOIN   nss.organization_status_master os
           ON os.organization_status_pk = o.organization_status_pk
    LEFT JOIN nss.organization p
           ON p.organization_pk = o.parent_organization_pk
    LEFT JOIN nss.district d
           ON d.district_pk = o.district_pk
    LEFT JOIN nss.state s
           ON s.state_pk = o.state_pk
    LEFT JOIN nss.country c
           ON c.country_pk = o.country_pk
    LEFT JOIN nss.city_village cv
           ON cv.city_village_pk = o.city_village_pk
    LEFT JOIN nss.postal_code pc
           ON pc.postal_code_pk = o.postal_code_pk
"""


# ═══════════════════════════════════════════════════════════════════════════
# 1. REFERENCE DATA
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/types", response_model=list[OrganizationTypeResponse])
def list_organization_types(
    conn=Depends(get_connection),
) -> list[OrganizationTypeResponse]:
    """List all active organization types (8 frozen types)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT organization_type_pk, organization_type_code,
                   organization_type_name, description,
                   sort_order, is_active
            FROM   nss.organization_type_master
            WHERE  is_active = TRUE
            ORDER BY sort_order
        """)
        return _rows_to_models(cur, OrganizationTypeResponse)


@router.get("/statuses", response_model=list[OrganizationStatusResponse])
def list_organization_statuses(
    conn=Depends(get_connection),
) -> list[OrganizationStatusResponse]:
    """List all active organization lifecycle statuses (6 statuses)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT organization_status_pk, organization_status_code,
                   organization_status_name, description,
                   sort_order, is_active
            FROM   nss.organization_status_master
            WHERE  is_active = TRUE
            ORDER BY sort_order
        """)
        return _rows_to_models(cur, OrganizationStatusResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 2. ORGANIZATIONS (core CRUD-read)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    type_code: str | None = Query(None, description="Filter by organization type code"),
    status_code: str | None = Query(None, description="Filter by organization status code"),
    conn=Depends(get_connection),
) -> list[OrganizationResponse]:
    """
    List all active organizations with resolved type, status, and parent.

    Optionally filter by type_code or status_code.
    """
    sql = _ORG_SELECT + " WHERE o.is_active = TRUE"
    params: list = []

    if type_code is not None:
        sql += " AND ot.organization_type_code = %s"
        params.append(type_code)
    if status_code is not None:
        sql += " AND os.organization_status_code = %s"
        params.append(status_code)

    sql += " ORDER BY ot.sort_order, o.organization_name"

    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return _rows_to_models(cur, OrganizationResponse)


@router.get(
    "/organizations/{organization_pk}",
    response_model=OrganizationResponse,
)
def get_organization(
    organization_pk: UUID,
    conn=Depends(get_connection),
) -> OrganizationResponse:
    """Get a single organization by PK with full resolved context."""
    sql = _ORG_SELECT + " WHERE o.organization_pk = %s AND o.is_active = TRUE"

    with conn.cursor() as cur:
        cur.execute(sql, (str(organization_pk),))
        result = _row_to_model(cur, OrganizationResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        return result


@router.get(
    "/organizations/{organization_pk}/children",
    response_model=list[OrganizationResponse],
)
def list_organization_children(
    organization_pk: UUID,
    conn=Depends(get_connection),
) -> list[OrganizationResponse]:
    """
    List direct children of a given organization.

    Returns 404 if the parent organization_pk does not exist.
    Useful for navigating the organizational hierarchy one level at a time.
    """
    # Verify the parent exists
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.organization
            WHERE  organization_pk = %s AND is_active = TRUE
        """, (str(organization_pk),))
        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404, detail="Parent organization not found"
            )

    sql = (
        _ORG_SELECT
        + " WHERE o.parent_organization_pk = %s AND o.is_active = TRUE"
        + " ORDER BY ot.sort_order, o.organization_name"
    )

    with conn.cursor() as cur:
        cur.execute(sql, (str(organization_pk),))
        return _rows_to_models(cur, OrganizationResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 3. HIERARCHY (recursive CTE)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/hierarchy", response_model=list[OrganizationHierarchyNodeResponse])
def get_organization_hierarchy(
    conn=Depends(get_connection),
) -> list[OrganizationHierarchyNodeResponse]:
    """
    Return the full organizational hierarchy as a flat list with depth.

    Uses a recursive CTE starting from root nodes (parent = NULL).
    The UI reconstructs the tree using depth for indentation.
    """
    with conn.cursor() as cur:
        cur.execute("""
            WITH RECURSIVE org_tree AS (
                -- Anchor: root nodes (no parent)
                SELECT o.organization_pk,
                       o.organization_name,
                       o.organization_code,
                       ot.organization_type_code,
                       ot.organization_type_name,
                       os.organization_status_code,
                       os.organization_status_name,
                       o.parent_organization_pk,
                       0 AS depth,
                       o.is_active
                FROM   nss.organization o
                JOIN   nss.organization_type_master ot
                       ON ot.organization_type_pk = o.organization_type_pk
                JOIN   nss.organization_status_master os
                       ON os.organization_status_pk = o.organization_status_pk
                WHERE  o.parent_organization_pk IS NULL
                  AND  o.is_active = TRUE

                UNION ALL

                -- Recursive: children
                SELECT o.organization_pk,
                       o.organization_name,
                       o.organization_code,
                       ot.organization_type_code,
                       ot.organization_type_name,
                       os.organization_status_code,
                       os.organization_status_name,
                       o.parent_organization_pk,
                       t.depth + 1,
                       o.is_active
                FROM   nss.organization o
                JOIN   nss.organization_type_master ot
                       ON ot.organization_type_pk = o.organization_type_pk
                JOIN   nss.organization_status_master os
                       ON os.organization_status_pk = o.organization_status_pk
                JOIN   org_tree t
                       ON t.organization_pk = o.parent_organization_pk
                WHERE  o.is_active = TRUE
            )
            SELECT * FROM org_tree
            ORDER BY depth, organization_name
        """)
        return _rows_to_models(cur, OrganizationHierarchyNodeResponse)
