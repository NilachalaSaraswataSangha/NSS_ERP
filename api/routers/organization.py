"""
Organization API router — Tier 2 read-only endpoints.

6 GET endpoints across the organization table plus Foundation
master_data (for type/status). No authentication.
nss_db_backend connects with SELECT-only privileges.

Endpoint groups:
  - Reference:   types, statuses (from master_data)
  - Core:        organizations (list, detail, children)
  - Navigation:  hierarchy (recursive CTE tree)

Organization type values are stored in Foundation master_data
under category ORGANIZATION_TYPE. Status values use the unified
ERP-wide STATUS category (shared across all modules).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.helpers import DEFAULT_LIMIT, MAX_LIMIT, row_to_model, rows_to_models
from api.schemas.organization import (
    OrgChildStatsResponse,
    OrganizationHierarchyNodeResponse,
    OrganizationResponse,
    OrganizationTypeResponse,
    StatusResponse,
)

router = APIRouter(prefix="/api/v1/organization", tags=["organization"])


# ── Shared SQL fragment for the organization SELECT ──────────────────────

_ORG_SELECT = """
    SELECT o.organization_pk,
           o.organization_id,
           o.organization_name,
           o.organization_code,
           ot.master_data_pk   AS organization_type_pk,
           ot.value_code       AS organization_type_code,
           ot.value_name       AS organization_type_name,
           os.master_data_pk   AS status_pk,
           os.value_code       AS status_code,
           os.value_name       AS status_name,
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
    JOIN   nss.master_data ot
           ON ot.master_data_pk = o.organization_type_master_data_pk
    JOIN   nss.master_data os
           ON os.master_data_pk = o.status_master_data_pk
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
    """List all active organization types (10 frozen types from master_data)."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT md.master_data_pk  AS organization_type_pk,
                   md.value_code      AS organization_type_code,
                   md.value_name      AS organization_type_name,
                   md.description,
                   md.display_order   AS sort_order,
                   md.is_active
            FROM   nss.master_data md
            JOIN   nss.master_category mc
                   ON mc.master_category_pk = md.master_category_pk
            WHERE  mc.category_code = 'ORGANIZATION_TYPE'
              AND  md.is_active = TRUE
            ORDER BY md.display_order
        """)
        return rows_to_models(cur, OrganizationTypeResponse)


@router.get("/statuses", response_model=list[StatusResponse])
def list_statuses(
    conn=Depends(get_connection),
) -> list[StatusResponse]:
    """List active lifecycle statuses applicable to the Organization module."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT md.master_data_pk  AS status_pk,
                   md.value_code      AS status_code,
                   md.value_name      AS status_name,
                   md.description,
                   md.display_order   AS sort_order,
                   md.is_active
            FROM   nss.master_data md
            JOIN   nss.master_category mc
                   ON mc.master_category_pk = md.master_category_pk
            WHERE  mc.category_code = 'STATUS'
              AND  md.is_active = TRUE
              AND  ('ORGANIZATION' = ANY(md.applicable_modules)
                    OR md.applicable_modules IS NULL)
            ORDER BY md.display_order
        """)
        return rows_to_models(cur, StatusResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 2. ORGANIZATIONS (core CRUD-read)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/organizations", response_model=list[OrganizationResponse])
def list_organizations(
    type_code: str | None = Query(None, description="Filter by organization type code"),
    status_code: str | None = Query(None, description="Filter by status code"),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    conn=Depends(get_connection),
) -> list[OrganizationResponse]:
    """
    List all active organizations with resolved type, status, and parent.

    Optionally filter by type_code or status_code. Supports pagination
    via limit/offset (default 100, max 500).
    """
    sql = _ORG_SELECT + " WHERE o.is_active = TRUE"
    params: list = []

    if type_code is not None:
        sql += " AND ot.value_code = %s"
        params.append(type_code)
    if status_code is not None:
        sql += " AND os.value_code = %s"
        params.append(status_code)

    sql += " ORDER BY ot.display_order, o.organization_name"
    sql += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        return rows_to_models(cur, OrganizationResponse)


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
        result = row_to_model(cur, OrganizationResponse)
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
        + " ORDER BY ot.display_order, o.organization_name"
    )

    with conn.cursor() as cur:
        cur.execute(sql, (str(organization_pk),))
        return rows_to_models(cur, OrganizationResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 3. CHILDREN STATS (aggregate counts per child org)
# ═══════════════════════════════════════════════════════════════════════════


_CHILDREN_STATS_SQL = """
    WITH RECURSIVE org_tree AS (
        -- Anchor: direct children of the requested parent
        SELECT o.organization_pk,
               o.organization_pk   AS root_child_pk,
               o.organization_name,
               o.organization_code,
               ot.value_code       AS organization_type_code
        FROM   nss.organization o
        JOIN   nss.master_data ot
               ON ot.master_data_pk = o.organization_type_master_data_pk
        WHERE  o.parent_organization_pk = %s
          AND  o.is_active = TRUE

        UNION ALL

        -- Recursive: descendants (capped at depth 10)
        SELECT o.organization_pk,
               t.root_child_pk,
               o.organization_name,
               o.organization_code,
               ot.value_code
        FROM   nss.organization o
        JOIN   nss.master_data ot
               ON ot.master_data_pk = o.organization_type_master_data_pk
        JOIN   org_tree t
               ON t.organization_pk = o.parent_organization_pk
        WHERE  o.is_active = TRUE
    ),
    -- Sakha PKs grouped by which direct child they belong to
    sakha_pks AS (
        SELECT root_child_pk, organization_pk AS sakha_pk
        FROM   org_tree
        WHERE  organization_type_code = 'SAKHA_SANGHA'
    ),
    -- Family majority CTE (dynamic Sakha — FAM-036)
    family_majority AS (
        SELECT fr.family_group_pk,
               aff.organization_pk  AS sakha_pk,
               COUNT(*)             AS cnt,
               ROW_NUMBER() OVER (
                   PARTITION BY fr.family_group_pk
                   ORDER BY COUNT(*) DESC
               ) AS rn
        FROM   nss.family_relationship fr
        JOIN   nss.sangha_sevi ss
               ON ss.person_pk = fr.person_pk AND ss.is_active = TRUE
        JOIN   nss.membership_sakha_affiliation aff
               ON aff.sangha_sevi_pk = ss.sangha_sevi_pk
              AND aff.effective_to IS NULL
        WHERE  fr.is_current = TRUE
        GROUP BY fr.family_group_pk, aff.organization_pk
    ),
    -- Each family's effective Sakha
    family_effective AS (
        SELECT fg.family_group_pk,
               COALESCE(fm.sakha_pk, fg.sakha_organization_pk)
                   AS effective_sakha_pk
        FROM   nss.family_group fg
        LEFT JOIN family_majority fm
               ON fm.family_group_pk = fg.family_group_pk AND fm.rn = 1
        WHERE  fg.is_active = TRUE
    ),
    -- Family count per root_child
    family_counts AS (
        SELECT sp.root_child_pk,
               COUNT(DISTINCT fe.family_group_pk) AS family_count
        FROM   sakha_pks sp
        JOIN   family_effective fe
               ON fe.effective_sakha_pk = sp.sakha_pk
        GROUP BY sp.root_child_pk
    ),
    -- Member count per root_child (active affiliations)
    member_counts AS (
        SELECT sp.root_child_pk,
               COUNT(DISTINCT ss.sangha_sevi_pk) AS member_count
        FROM   sakha_pks sp
        JOIN   nss.membership_sakha_affiliation aff
               ON aff.organization_pk = sp.sakha_pk
              AND aff.effective_to IS NULL
        JOIN   nss.sangha_sevi ss
               ON ss.sangha_sevi_pk = aff.sangha_sevi_pk
              AND ss.is_active = TRUE
        GROUP BY sp.root_child_pk
    ),
    -- Person count per root_child (persons in families under effective Sakha)
    person_counts AS (
        SELECT sp.root_child_pk,
               COUNT(DISTINCT fr.person_pk) AS person_count
        FROM   sakha_pks sp
        JOIN   family_effective fe
               ON fe.effective_sakha_pk = sp.sakha_pk
        JOIN   nss.family_relationship fr
               ON fr.family_group_pk = fe.family_group_pk
              AND fr.is_current = TRUE
        GROUP BY sp.root_child_pk
    )
    SELECT ot.root_child_pk        AS organization_pk,
           ot.organization_name,
           ot.organization_code,
           ot.organization_type_code,
           COALESCE(fc.family_count, 0)  AS family_count,
           COALESCE(mc.member_count, 0)  AS member_count,
           COALESCE(pc.person_count, 0)  AS person_count
    FROM   org_tree ot
    LEFT JOIN family_counts fc   ON fc.root_child_pk = ot.root_child_pk
    LEFT JOIN member_counts mc   ON mc.root_child_pk = ot.root_child_pk
    LEFT JOIN person_counts pc   ON pc.root_child_pk = ot.root_child_pk
    WHERE  ot.organization_pk = ot.root_child_pk
    ORDER BY ot.organization_name
"""


@router.get(
    "/organizations/{organization_pk}/children-stats",
    response_model=list[OrgChildStatsResponse],
)
def list_children_stats(
    organization_pk: UUID,
    conn=Depends(get_connection),
) -> list[OrgChildStatsResponse]:
    """
    Aggregate statistics for each direct child of an organization.

    For each child org, recursively finds all descendant Sakhas and
    counts families (dynamic majority rule), members (active
    affiliations), and persons (family members).

    Used by the org admin sidebar to display inline counts on each
    drill-down card.
    """
    # Verify parent exists
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.organization
            WHERE  organization_pk = %s AND is_active = TRUE
        """, (str(organization_pk),))
        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404, detail="Parent organization not found"
            )

    with conn.cursor() as cur:
        cur.execute(_CHILDREN_STATS_SQL, (str(organization_pk),))
        return rows_to_models(cur, OrgChildStatsResponse)


# ═══════════════════════════════════════════════════════════════════════════
# 4. HIERARCHY (recursive CTE)
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/hierarchy", response_model=list[OrganizationHierarchyNodeResponse])
def get_organization_hierarchy(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT, description="Max rows to return"),
    offset: int = Query(0, ge=0, description="Number of rows to skip"),
    conn=Depends(get_connection),
) -> list[OrganizationHierarchyNodeResponse]:
    """
    Return the full organizational hierarchy as a flat list with depth.

    Uses a recursive CTE starting from root nodes (parent = NULL).
    Depth is capped at 10 levels as a defence-in-depth guard against
    circular parent references. Supports pagination via limit/offset.
    The UI reconstructs the tree using depth for indentation.
    """
    with conn.cursor() as cur:
        cur.execute("""
            WITH RECURSIVE org_tree AS (
                -- Anchor: root nodes (no parent)
                SELECT o.organization_pk,
                       o.organization_name,
                       o.organization_code,
                       ot.value_code  AS organization_type_code,
                       ot.value_name  AS organization_type_name,
                       os.value_code  AS status_code,
                       os.value_name  AS status_name,
                       o.parent_organization_pk,
                       0 AS depth,
                       o.is_active
                FROM   nss.organization o
                JOIN   nss.master_data ot
                       ON ot.master_data_pk = o.organization_type_master_data_pk
                JOIN   nss.master_data os
                       ON os.master_data_pk = o.status_master_data_pk
                WHERE  o.parent_organization_pk IS NULL
                  AND  o.is_active = TRUE

                UNION ALL

                -- Recursive: children (depth capped at 10)
                SELECT o.organization_pk,
                       o.organization_name,
                       o.organization_code,
                       ot.value_code  AS organization_type_code,
                       ot.value_name  AS organization_type_name,
                       os.value_code  AS status_code,
                       os.value_name  AS status_name,
                       o.parent_organization_pk,
                       t.depth + 1,
                       o.is_active
                FROM   nss.organization o
                JOIN   nss.master_data ot
                       ON ot.master_data_pk = o.organization_type_master_data_pk
                JOIN   nss.master_data os
                       ON os.master_data_pk = o.status_master_data_pk
                JOIN   org_tree t
                       ON t.organization_pk = o.parent_organization_pk
                WHERE  o.is_active = TRUE
                  AND  t.depth < 10
            )
            SELECT * FROM org_tree
            ORDER BY depth, organization_name
            LIMIT %s OFFSET %s
        """, (limit, offset))
        return rows_to_models(cur, OrganizationHierarchyNodeResponse)
