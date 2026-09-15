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
    FamilyGraphMemberResponse,
    FamilyGroupResponse,
    FamilyHeadHistoryResponse,
    FamilyMemberResponse,
    FamilySakhaAlignmentResponse,
    MemberSakhaInfo,
    PersonMembershipSummaryResponse,
    SakhaAffiliationCount,
)
from api.services.family_graph import Step, build_family_graph

router = APIRouter(prefix="/api/v1/family", tags=["family"])


# ── Shared SQL fragments ──────────────────────────────────────────────────

_FAMILY_SELECT = """
    WITH family_majority AS (
        SELECT fr.family_group_pk,
               aff.organization_pk        AS sakha_pk,
               COUNT(*)                    AS cnt,
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
    )
    SELECT fg.family_group_pk,
           fg.family_id,
           fg.family_name,
           fg.family_status_master_data_pk,
           st.value_code  AS status_code,
           st.value_name  AS status_name,
           COALESCE(fmj.sakha_pk, fg.sakha_organization_pk)
               AS sakha_organization_pk,
           COALESCE(eo.organization_name, o.organization_name)
               AS sakha_name,
           COALESCE(eo.organization_code, o.organization_code)
               AS sakha_code,
           fg.formed_date,
           fg.remarks,
           fg.is_active
    FROM   nss.family_group fg
    JOIN   nss.master_data st
           ON st.master_data_pk = fg.family_status_master_data_pk
    JOIN   nss.organization o
           ON o.organization_pk = fg.sakha_organization_pk
    LEFT JOIN family_majority fmj
           ON fmj.family_group_pk = fg.family_group_pk AND fmj.rn = 1
    LEFT JOIN nss.organization eo
           ON eo.organization_pk = fmj.sakha_pk
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
           CASE WHEN fhh.family_head_history_pk IS NOT NULL
                THEN TRUE ELSE FALSE
           END AS is_head,
           fr.remarks
    FROM   nss.family_relationship fr
    JOIN   nss.person p
           ON p.person_pk = fr.person_pk
    JOIN   nss.master_data rt
           ON rt.master_data_pk = fr.relationship_type_master_data_pk
    LEFT JOIN nss.family_head_history fhh
           ON fhh.family_group_pk = fr.family_group_pk
          AND fhh.person_pk = fr.person_pk
          AND fhh.effective_to IS NULL
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
        sql += " AND COALESCE(eo.organization_code, o.organization_code) = %s"
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


# ═══════════════════════════════════════════════════════════════════════════
# 4. FAMILY GRAPH (dynamic relationship computation)
# ═══════════════════════════════════════════════════════════════════════════

_GRAPH_PERSONS_SQL = """
    SELECT DISTINCT p.person_pk,
           p.person_id,
           p.first_name,
           p.middle_name,
           p.last_name,
           g.value_code AS gender_code
    FROM   nss.family_link fl
    JOIN   nss.person p
           ON p.person_pk IN (fl.person_a_pk, fl.person_b_pk)
    LEFT JOIN nss.master_data g
           ON g.master_data_pk = p.gender_master_data_pk
    WHERE  fl.family_group_pk = %s
      AND  fl.is_current = TRUE
"""

_GRAPH_LINKS_SQL = """
    SELECT fl.person_a_pk,
           fl.person_b_pk,
           fl.link_type
    FROM   nss.family_link fl
    WHERE  fl.family_group_pk = %s
      AND  fl.is_current = TRUE
"""


@router.get(
    "/families/{family_group_pk}/graph",
    response_model=list[FamilyGraphMemberResponse],
)
def get_family_graph(
    family_group_pk: UUID,
    viewer_person_pk: UUID = Query(
        ..., description="Person PK of the logged-in viewer"
    ),
    conn=Depends(get_connection),
) -> list[FamilyGraphMemberResponse]:
    """
    Compute family relationships dynamically relative to a viewer.

    Uses the ``family_link`` graph (direct PARENT_OF / SPOUSE_OF edges)
    to derive all kinship labels via BFS traversal.  No static
    relationship codes are needed — labels adapt automatically when
    the viewer changes.
    """
    # Verify family exists
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM nss.family_group
            WHERE  family_group_pk = %s AND is_active = TRUE
        """, (str(family_group_pk),))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Family not found")

    # Fetch graph data
    with conn.cursor() as cur:
        cur.execute(_GRAPH_PERSONS_SQL, (str(family_group_pk),))
        cols = [desc[0] for desc in cur.description]
        person_rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    with conn.cursor() as cur:
        cur.execute(_GRAPH_LINKS_SQL, (str(family_group_pk),))
        cols = [desc[0] for desc in cur.description]
        link_rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    if not person_rows or not link_rows:
        return []

    # Build graph and compute
    graph = build_family_graph(person_rows, link_rows)
    computed = graph.compute_relationships(viewer_person_pk)

    # Look up current head
    with conn.cursor() as cur:
        cur.execute("""
            SELECT person_pk FROM nss.family_head_history
            WHERE  family_group_pk = %s AND effective_to IS NULL
        """, (str(family_group_pk),))
        head_row = cur.fetchone()
        head_pk = str(head_row[0]) if head_row else None

    # Build response — include spouse_person_pk and parent_person_pks from graph adjacency
    results = []
    for member in computed:
        member_pk = UUID(member["person_pk"])
        # Find spouse via SPOUSE edge in adjacency
        spouse_pk = None
        parent_pks = []
        for neighbor_pk, step in graph.adjacency.get(member_pk, []):
            if step == Step.SPOUSE:
                spouse_pk = neighbor_pk
            elif step == Step.UP:
                parent_pks.append(str(neighbor_pk))

        results.append(FamilyGraphMemberResponse(
            person_pk=member["person_pk"],
            person_id=member["person_id"],
            first_name=member["first_name"],
            middle_name=member["middle_name"],
            last_name=member["last_name"],
            gender_code=member["gender_code"],
            relationship_label=member["relationship_label"],
            generation=member["generation"],
            is_head=(member["person_pk"] == head_pk),
            spouse_person_pk=str(spouse_pk) if spouse_pk else None,
            parent_person_pks=parent_pks,
        ))

    return results


# ═══════════════════════════════════════════════════════════════════════════
# 5. SAKHA ALIGNMENT (FAM-036 majority rule)
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/families/{family_group_pk}/sakha-alignment",
    response_model=FamilySakhaAlignmentResponse,
)
def get_family_sakha_alignment(
    family_group_pk: UUID,
    conn=Depends(get_connection),
) -> FamilySakhaAlignmentResponse:
    """
    Compute Sakha alignment for a family.

    The family's effective Sakha is dynamically computed from the
    majority of its members' active affiliations (FAM-036).  When
    no members have affiliations the stored registration Sakha is
    used as fallback.

    Returns the effective Sakha, per-Sakha member counts, and
    per-member affiliation info with mismatch flags (member at a
    different Sakha than the family's effective Sakha).
    """
    # 1. Fetch the family with its assigned Sakha
    sql = _FAMILY_SELECT + " WHERE fg.family_group_pk = %s AND fg.is_active = TRUE"
    with conn.cursor() as cur:
        cur.execute(sql, (str(family_group_pk),))
        family = row_to_model(cur, FamilyGroupResponse)
        if family is None:
            raise HTTPException(status_code=404, detail="Family not found")

    # 2. Get all current family members (persons)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT fr.person_pk,
                   p.person_id,
                   p.first_name,
                   p.middle_name,
                   p.last_name
            FROM   nss.family_relationship fr
            JOIN   nss.person p ON p.person_pk = fr.person_pk
            WHERE  fr.family_group_pk = %s
              AND  fr.is_current = TRUE
            ORDER BY p.first_name
        """, (str(family_group_pk),))
        cols = [desc[0] for desc in cur.description]
        member_rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    if not member_rows:
        return FamilySakhaAlignmentResponse(
            family_group_pk=family.family_group_pk,
            family_name=family.family_name,
            assigned_sakha_pk=family.sakha_organization_pk,
            assigned_sakha_name=family.sakha_name,
            assigned_sakha_code=family.sakha_code or "",
        )

    # 3. For each member, look up their active Sakha affiliation
    person_pks = [str(m["person_pk"]) for m in member_rows]
    placeholders = ",".join(["%s"] * len(person_pks))

    with conn.cursor() as cur:
        cur.execute(f"""
            SELECT ss.person_pk,
                   aff.organization_pk  AS affiliated_sakha_pk,
                   o.organization_name  AS affiliated_sakha_name,
                   o.organization_code  AS affiliated_sakha_code
            FROM   nss.sangha_sevi ss
            JOIN   nss.membership_sakha_affiliation aff
                   ON aff.sangha_sevi_pk = ss.sangha_sevi_pk
                  AND aff.effective_to IS NULL
            JOIN   nss.organization o
                   ON o.organization_pk = aff.organization_pk
            WHERE  ss.person_pk IN ({placeholders})
              AND  ss.is_active = TRUE
        """, tuple(person_pks))
        cols = [desc[0] for desc in cur.description]
        aff_rows = {str(row[0]): dict(zip(cols, row)) for row in cur.fetchall()}

    # 4. Build per-member info
    members_info = []
    sakha_counts: dict[str, dict] = {}  # org_pk → {name, code, count}

    for m in member_rows:
        pk = str(m["person_pk"])
        aff = aff_rows.get(pk)
        has_membership = aff is not None

        affiliated_sakha_pk = None
        affiliated_sakha_name = None
        affiliated_sakha_code = None
        is_home = None

        if aff:
            affiliated_sakha_pk = aff["affiliated_sakha_pk"]
            affiliated_sakha_name = aff["affiliated_sakha_name"]
            affiliated_sakha_code = aff["affiliated_sakha_code"]
            is_home = (
                str(affiliated_sakha_pk) == str(family.sakha_organization_pk)
            )

            # Count per Sakha
            aff_pk_str = str(affiliated_sakha_pk)
            if aff_pk_str not in sakha_counts:
                sakha_counts[aff_pk_str] = {
                    "organization_pk": affiliated_sakha_pk,
                    "organization_name": affiliated_sakha_name,
                    "organization_code": affiliated_sakha_code,
                    "member_count": 0,
                }
            sakha_counts[aff_pk_str]["member_count"] += 1

        members_info.append(MemberSakhaInfo(
            person_pk=m["person_pk"],
            person_id=m["person_id"],
            first_name=m["first_name"],
            middle_name=m.get("middle_name"),
            last_name=m.get("last_name"),
            affiliated_sakha_pk=affiliated_sakha_pk,
            affiliated_sakha_name=affiliated_sakha_name,
            affiliated_sakha_code=affiliated_sakha_code,
            is_home_sakha=is_home,
            has_membership=has_membership,
        ))

    # 5. Compute majority Sakha
    affiliations = sorted(
        sakha_counts.values(),
        key=lambda x: x["member_count"],
        reverse=True,
    )

    majority_sakha_pk = None
    majority_sakha_name = None
    majority_sakha_code = None
    is_aligned = True

    if affiliations:
        top = affiliations[0]
        majority_sakha_pk = top["organization_pk"]
        majority_sakha_name = top["organization_name"]
        majority_sakha_code = top["organization_code"]
        is_aligned = (
            str(majority_sakha_pk) == str(family.sakha_organization_pk)
        )

    return FamilySakhaAlignmentResponse(
        family_group_pk=family.family_group_pk,
        family_name=family.family_name,
        assigned_sakha_pk=family.sakha_organization_pk,
        assigned_sakha_name=family.sakha_name,
        assigned_sakha_code=family.sakha_code or "",
        majority_sakha_pk=majority_sakha_pk,
        majority_sakha_name=majority_sakha_name,
        majority_sakha_code=majority_sakha_code,
        is_aligned=is_aligned,
        total_members=len(member_rows),
        members_with_affiliation=len(aff_rows),
        affiliations=[
            SakhaAffiliationCount(**a) for a in affiliations
        ],
        members=members_info,
    )


# ═══════════════════════════════════════════════════════════════════════════
# 6. PERSON MEMBERSHIP SUMMARY (for family tree Selected Person panel)
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/person/{person_pk}/membership-summary",
    response_model=PersonMembershipSummaryResponse,
)
def get_person_membership_summary(
    person_pk: UUID,
    conn=Depends(get_connection),
) -> PersonMembershipSummaryResponse:
    """
    Lightweight membership snapshot for a person, used by the family
    tree's Selected Person panel.

    Bridges person_pk (family context) to sangha_sevi (membership context).
    Returns sangha_sevi_id, membership type/status, current sakha
    affiliation, and latest Parichaya Patra number.

    Returns empty fields (not 404) if the person has no membership record.
    """
    # Look up sangha_sevi by person_pk
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ss.sangha_sevi_pk,
                   ss.sangha_sevi_id,
                   mt.value_code  AS membership_type_code,
                   mt.value_name  AS membership_type_name,
                   ms.value_code  AS status_code,
                   ms.value_name  AS status_name,
                   o.organization_name,
                   aff.local_sakha_erp_id
            FROM   nss.sangha_sevi ss
            JOIN   nss.master_data mt
                   ON mt.master_data_pk = ss.membership_type_master_data_pk
            JOIN   nss.master_data ms
                   ON ms.master_data_pk = ss.membership_status_master_data_pk
            JOIN   nss.organization o
                   ON o.organization_pk = ss.organization_pk
            LEFT JOIN nss.membership_sakha_affiliation aff
                   ON aff.sangha_sevi_pk = ss.sangha_sevi_pk
                  AND aff.effective_to IS NULL
            WHERE  ss.person_pk = %s
              AND  ss.is_active = TRUE
            LIMIT  1
        """, (str(person_pk),))
        cols = [desc[0] for desc in cur.description]
        row = cur.fetchone()

    if not row:
        return PersonMembershipSummaryResponse()

    member = dict(zip(cols, row))
    sangha_sevi_pk = member["sangha_sevi_pk"]

    # Fetch latest Parichaya Patra
    pp_number = None
    pp_status = None
    pp_valid_to = None
    with conn.cursor() as cur:
        cur.execute("""
            SELECT pp.document_number,
                   pp.status,
                   pp.valid_to
            FROM   nss.parichaya_patra pp
            WHERE  pp.sangha_sevi_pk = %s
            ORDER BY pp.valid_from DESC
            LIMIT  1
        """, (str(sangha_sevi_pk),))
        pp_row = cur.fetchone()
        if pp_row:
            pp_number, pp_status, pp_valid_to = pp_row

    # Fetch latest Anumati Patra (Darshaka / non-Associate only per MBR-019A/B)
    ap_number = None
    ap_status = None
    ap_valid_to = None
    if member["membership_type_code"] != "ASSOCIATE":
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ap.document_number,
                       ap.status,
                       ap.valid_to
                FROM   nss.anumati_patra ap
                WHERE  ap.sangha_sevi_pk = %s
                ORDER BY ap.valid_from DESC
                LIMIT  1
            """, (str(sangha_sevi_pk),))
            ap_row = cur.fetchone()
            if ap_row:
                ap_number, ap_status, ap_valid_to = ap_row

    return PersonMembershipSummaryResponse(
        sangha_sevi_id=member["sangha_sevi_id"],
        sangha_sevi_pk=sangha_sevi_pk,
        membership_type_code=member["membership_type_code"],
        membership_type_name=member["membership_type_name"],
        status_code=member["status_code"],
        status_name=member["status_name"],
        organization_name=member["organization_name"],
        local_sakha_erp_id=member["local_sakha_erp_id"],
        parichaya_patra_number=pp_number,
        parichaya_patra_status=pp_status,
        parichaya_patra_valid_to=pp_valid_to,
        anumati_patra_number=ap_number,
        anumati_patra_status=ap_status,
        anumati_patra_valid_to=ap_valid_to,
    )
