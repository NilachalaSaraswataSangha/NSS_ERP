"""
NSS ERP — Shared API helpers.

Cursor-to-Pydantic conversion functions used by all routers.
Extracted from per-router duplicates to ensure a single point of
maintenance for any future security hardening (e.g. column sanitisation).

Pagination constants are also centralised here so all list endpoints
share the same defaults and validation ranges.

Shared DB helpers:
  - next_id()                    — atomic ID sequence increment
  - get_system_setting()         — nss.system_setting value lookup
  - resolve_or_create_city_village() — lookup/create city_village record
  - get_active_status_pk()       — ACTIVE status master_data PK lookup
  - log_audit()                  — centralized audit trail (system_event_log)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

import psycopg2.errors

logger = logging.getLogger(__name__)


# ── Pagination defaults ──────────────────────────────────────────────────

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


# ── Sorting ──────────────────────────────────────────────────────────────
#
# Click-to-sort on a table header sends sort_by/sort_dir. For a paginated
# endpoint the sort MUST happen in SQL: sorting one page client-side
# reorders only the rows already fetched, which shows the user "A–Z" while
# actually giving them A–Z within page 3. That is wrong, not merely
# partial, so ordering belongs in the query.
#
# ORDER BY cannot be a bound parameter — it is part of the statement, not
# a value. So the column has to be interpolated, and the ONLY safe way to
# do that is to never let a caller-supplied string reach the SQL. Each
# endpoint declares a whitelist mapping the public field name to a fixed
# SQL expression it controls; anything not in that map is rejected. No
# caller input is ever concatenated into the statement.

SORT_ASC = "asc"
SORT_DESC = "desc"


def natural_sort_key(column: str) -> list[str]:
    """
    SQL terms that order 'prefix + trailing digits' IDs the way a person
    reads them: SS2 before SS10, AMSAS9 before AMSAS100.

    Plain text collation gets this backwards ('AMSAS100' < 'AMSAS9'
    because '1' < '9'), and every business identifier in this system has
    that shape — person_id P7, sangha_sevi_id SS10,
    local_sakha_erp_id AMSAS9456831. It also keeps SQL ordering
    consistent with the frontend's client-side sort, which is
    numeric-aware; otherwise the same column would order differently
    depending on which table you were looking at.

    Returns two terms: the non-numeric stem, then the trailing number as
    an integer. The regexp yields '' for a value with no trailing digits,
    so NULLIF guards the cast.

    `column` must be a literal chosen by this codebase, never caller
    input — see the module note above.
    """
    return [
        f"regexp_replace({column}, '[0-9]+$', '')",
        f"NULLIF(regexp_replace({column}, '^.*?([0-9]*)$', '\\1'), '')::bigint",
    ]


def build_order_by(
    sort_by: str | None,
    sort_dir: str | None,
    allowed: dict[str, str | list[str]],
    default: str,
) -> str:
    """
    Build a validated ORDER BY clause for a list endpoint.

    Args:
        sort_by:  public field name from the query string, or None
        sort_dir: "asc" | "desc" (case-insensitive), or None
        allowed:  {public field name: SQL term, or list of SQL terms}.
                  Terms are author-controlled — build them with
                  natural_sort_key() or write them literally. NEVER put
                  caller input in here. A list is used rather than a
                  comma-joined string because real expressions contain
                  commas of their own (CONCAT_WS(' ', a, b)), which a
                  split would shred into invalid SQL.
        default:  full ORDER BY body used when sort_by is absent, e.g.
                  "ua.created_at DESC".

    Returns:
        The clause body WITHOUT the leading "ORDER BY".

    Raises:
        HTTPException 422 with a readable message naming the sortable
        columns, so an unknown field is a normal validation failure
        rather than a 500.

    NULLS LAST is applied in both directions to match the frontend rule
    that a blank cell sinks to the bottom — a missing value is not the
    smallest value. A stable tiebreaker is appended so rows with equal
    keys keep a fixed relative order across pages; without it, the same
    row can appear on two pages or on none.
    """
    if not sort_by:
        return default

    expression = allowed.get(sort_by)
    if expression is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"'{sort_by}' is not a sortable column here. "
                f"Sortable columns are: {', '.join(sorted(allowed))}."
            ),
        )

    direction = "DESC" if (sort_dir or "").lower() == SORT_DESC else "ASC"

    terms = [expression] if isinstance(expression, str) else list(expression)
    ordered = ", ".join(f"{term} {direction} NULLS LAST" for term in terms)
    return f"{ordered}, {default}"


# ── Cursor → Pydantic helpers ────────────────────────────────────────────

def rows_to_models(cur, model_class):
    """Convert cursor results to a list of Pydantic models."""
    columns = [desc[0] for desc in cur.description]
    return [model_class(**dict(zip(columns, row))) for row in cur.fetchall()]


def row_to_model(cur, model_class):
    """Convert a single cursor result to a Pydantic model, or None."""
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row is None:
        return None
    return model_class(**dict(zip(columns, row)))


# ── ID sequence generation ───────────────────────────────────────────────

def next_id(cur, sequence_code: str, *, actor_pk: str | None = None) -> str:
    """
    Atomically increment id_sequence_master and return the new business ID.

    Uses UPDATE ... RETURNING to prevent race conditions.
    Returns: prefix + next_value (e.g. "P3", "SS12", "SAKHA-005").

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (id_sequence_master has no audit-actor column; the DB
    audit trigger records changes automatically).

    Raises HTTPException 500 if the sequence_code does not exist.
    """
    cur.execute(
        """
        UPDATE nss.id_sequence_master
        SET current_value = current_value + 1,
            updated_at = NOW()
        WHERE sequence_code = %s
        RETURNING prefix, current_value
        """,
        (sequence_code,),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ID sequence '{sequence_code}' not found.",
        )
    return f"{row[0]}{row[1]}"


def peek_next_id(cur, sequence_code: str) -> str | None:
    """
    Return the business ID that *next_id* WOULD mint next — without
    consuming (incrementing) the sequence.

    This is a read-only preview: it reads the current counter and returns
    ``prefix + (current_value + 1)``, exactly matching next_id's own
    format (which likewise applies no zero-padding). Used by the Create
    Organization form to show "what the org code will be if submitted";
    the authoritative value is only ever minted on submit via next_id, so
    a preview never burns a number and concurrent creates simply mean the
    real value may differ from a stale preview.

    Returns None if the sequence_code does not exist (so callers can treat
    "no sequence for this type" as "no previewable code" rather than error).
    """
    cur.execute(
        """
        SELECT prefix, current_value + 1
        FROM nss.id_sequence_master
        WHERE sequence_code = %s
        """,
        (sequence_code,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return f"{row[0]}{row[1]}"


# ── System settings ─────────────────────────────────────────────────────

def get_system_setting(cur, setting_key: str) -> str | None:
    """
    Return the active nss.system_setting value for *setting_key*, or None.

    Callers that cannot safely proceed without the value must treat None as a
    configuration error and fail — see compose_local_sakha_erp_id(), where a
    missing marker would silently compose an ID into the wrong namespace.
    """
    cur.execute(
        """
        SELECT setting_value
        FROM   nss.system_setting
        WHERE  setting_key = %s AND is_active = TRUE
        """,
        (setting_key,),
    )
    row = cur.fetchone()
    return row[0] if row else None


# ── Local Sakha ERP ID composition ──────────────────────────────────────

# MBR-030C — Tier 2 local numbering is namespace-separated by membership
# state. The marker that separates the two namespaces is configuration, not
# code: it lives in nss.system_setting so an admin can change it through
# System Settings without a deploy, and so it appears in exactly one place.
DARSHAK_LOCAL_ID_MARKER_SETTING = "MEMBERSHIP_DARSHAK_LOCAL_ID_MARKER"

# The Bye-Law membership type whose local numbers live in the Darshak
# namespace. PROBATIONARY is the authoritative stored code (MBR-006);
# "Darshak" is a UI label only and is never a stored membership type
# (MBR-007), so the namespace decision keys off the official code.
PROBATIONARY_MEMBERSHIP_TYPE_CODE = "PROBATIONARY"


def is_probationary_membership_type(cur, membership_type_pk: str | None) -> bool:
    """
    True when *membership_type_pk* resolves to the PROBATIONARY membership type.

    Used to choose the local-number namespace (MBR-030C). Returns False for a
    NULL/unknown PK: callers use this only to *add* the Darshak marker, and the
    conservative direction is to compose in the Regular namespace, where the
    existing uniqueness constraint will still reject a genuine duplicate.
    """
    if not membership_type_pk:
        return False
    cur.execute(
        "SELECT value_code FROM nss.master_data WHERE master_data_pk = %s",
        (str(membership_type_pk),),
    )
    row = cur.fetchone()
    return bool(row) and row[0] == PROBATIONARY_MEMBERSHIP_TYPE_CODE


def compose_local_sakha_erp_id(
    cur, org_pk: str, local_number: str, *, is_darshak: bool = False
) -> str:
    """
    Build a Tier 2 Local Sakha ERP ID (MBR-030, MBR-030C).

        Regular / Associate:    <short_code><local_number>          ESS000123
        Darshak / Probationary: <short_code><marker><local_number>  ESSD000045

    Looks up the short_code for the given organization PK.
    If short_code is NULL (not yet assigned by admin), raises 422
    so the caller knows to assign it first.

    When *is_darshak* is true the namespace marker is read from
    nss.system_setting (DARSHAK_LOCAL_ID_MARKER_SETTING). A missing or blank
    marker raises 500 rather than defaulting: composing without the marker
    would place a Darshak identifier inside the Regular namespace, where it
    could collide with a Regular member's number and be indistinguishable
    from one afterwards. Failing loudly is the safe direction.

    Because the marker is part of the string, ESS000001 and ESSD000001 are
    distinct values — the two namespaces coexist under the existing
    uq_mem_sakha_aff_local_id constraint with no schema change.
    """
    cur.execute(
        "SELECT short_code, organization_name FROM nss.organization WHERE organization_pk = %s",
        (str(org_pk),),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{org_pk}' not found.",
        )
    short_code, org_name = row[0], row[1]
    if not short_code:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Organization '{org_name}' does not have a short_code assigned yet. "
                "An admin must set the short_code before members can be enrolled."
            ),
        )
    num = str(local_number).strip()
    if not num:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Local Sakha number is required for non-Darshaka members.",
        )

    marker = ""
    if is_darshak:
        marker = (get_system_setting(cur, DARSHAK_LOCAL_ID_MARKER_SETTING) or "").strip()
        if not marker:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Darshak local-number namespace marker is not configured. "
                    f"Set the '{DARSHAK_LOCAL_ID_MARKER_SETTING}' system setting "
                    "before enrolling Darshak/Probationary members."
                ),
            )

    return f"{short_code}{marker}{num}"


# ── Sakha-only membership guard (API mirror of MBR-038A trigger) ─────────

def require_sakha_organization(cur, organization_pk: str) -> None:
    """
    Enforce MBR-038A at the API layer: a Member's organizational
    association must reference an organization of type SAKHA_SANGHA.

    This mirrors the database triggers in
    05_membership/14_sakha_only_membership_trigger.sql. The DB is the
    airtight backstop; this helper exists so callers get a clean 422 that
    names the problem instead of a raw trigger exception surfacing as 500.

    The single system-account exception (is_system_account = TRUE, the
    seeded SS1 → Kendra) is deliberately NOT reachable here: the API never
    creates the system account, so every member created through these
    endpoints must be tied to a Sakha, with no exception.

    Raises: HTTPException 422 if organization_pk is not a SAKHA_SANGHA.
    """
    if organization_pk is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                "A membership must be tied to a Sakha Sangha (MBR-038A). "
                "No organization was supplied."
            ),
        )

    cur.execute(
        """
        SELECT md.value_code, o.organization_name
        FROM nss.organization o
        JOIN nss.master_data md
            ON md.master_data_pk = o.organization_type_master_data_pk
        WHERE o.organization_pk = %s
        """,
        (str(organization_pk),),
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="The specified organization does not exist.",
        )

    org_type_code, org_name = row
    if org_type_code != "SAKHA_SANGHA":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"A member can only be associated with a Sakha Sangha "
                f"(MBR-038A). '{org_name}' is of type {org_type_code}, "
                "not SAKHA_SANGHA."
            ),
        )


def resolve_kumari_sevak_parent_sakha(
    cur,
    *,
    user,
    organization_type_code: str,
    requested_parent_pk: str | None,
) -> str:
    """
    Resolve/validate the parent Sakha for a KUMARI_SANGHA/SEVAK_SANGHA
    create-or-update (ORG-BR-101/102).

    - NSS-wide NSS_ERP_ADMIN: requested_parent_pk must be supplied by the
      caller (any active Sakha is legal); returned unchanged.
    - NSS_ERP_SAKHA_ADMIN scoped to exactly one Sakha: that Sakha is
      auto-selected and returned, overriding/ignoring a mismatched
      requested_parent_pk is rejected rather than silently overridden.
    - NSS_ERP_SAKHA_ADMIN scoped to more than one Sakha: if the caller
      didn't specify a Sakha, auto-select the one (and only one) of their
      scoped Sakhas that currently lacks an active organization of this
      type; otherwise require an explicit, in-scope selection.
    - A Sakha admin may never act on a Sakha outside their own admin_scope.

    Raises HTTPException (403/422) on any authority or selection failure.
    """
    is_nss_admin = any(s.role_code == "NSS_ERP_ADMIN" for s in user.scopes)
    if is_nss_admin:
        if not requested_parent_pk:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="parent_organization_pk (the target Sakha) is required.",
            )
        return requested_parent_pk

    scoped_sakha_pks = sorted({
        str(s.organization_pk)
        for s in user.scopes
        if s.role_code == "NSS_ERP_SAKHA_ADMIN" and s.organization_pk
    })

    if not scoped_sakha_pks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Only NSS_ERP_ADMIN or the Sakha's own NSS_ERP_SAKHA_ADMIN "
                "may create or update a Kumari/Sevak Sangha (ORG-BR-101)."
            ),
        )

    if requested_parent_pk:
        if str(requested_parent_pk) not in scoped_sakha_pks:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "A Sakha admin may only act on a Sakha within their own "
                    "admin_scope (ORG-BR-101)."
                ),
            )
        return requested_parent_pk

    if len(scoped_sakha_pks) == 1:
        return scoped_sakha_pks[0]

    # Multiple scoped Sakhas, no explicit selection: auto-select the one
    # (and only one) that lacks an active org of this type (ORG-BR-102).
    cur.execute(
        """
        SELECT o.parent_organization_pk
        FROM nss.organization o
        JOIN nss.master_data md ON md.master_data_pk = o.organization_type_master_data_pk
        WHERE o.parent_organization_pk = ANY(%s::uuid[])
          AND md.value_code = %s
          AND o.is_active = TRUE
        """,
        (scoped_sakha_pks, organization_type_code),
    )
    already_has = {str(r[0]) for r in cur.fetchall()}
    lacking = [pk for pk in scoped_sakha_pks if pk not in already_has]

    if len(lacking) == 1:
        return lacking[0]

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=(
            "You administer more than one Sakha and it isn't unambiguous "
            "which one this applies to — specify parent_organization_pk "
            f"explicitly (ORG-BR-102). Your Sakhas: {', '.join(scoped_sakha_pks)}."
        ),
    )


def resolve_scoped_sakha(
    cur,
    *,
    user,
    requested_organization_pk: str | None,
) -> str:
    """
    Resolve/validate the Sakha an admin is attaching a member-scoped record
    to (Sangha Sevi, a user's membership, etc.) using the standard
    scope-select pattern — the member-attach analogue of
    resolve_kumari_sevak_parent_sakha, but WITHOUT any one-per-Sakha
    cardinality (a Sakha holds many members, so there is nothing to
    auto-disambiguate for a multi-Sakha admin):

      - NSS-wide admin: requested_organization_pk is mandatory (any active
        Sakha is legal); returned unchanged.
      - Admin scoped to exactly one Sakha: that Sakha is auto-selected; a
        mismatched explicit pick is rejected, never silently overridden.
      - Admin scoped to more than one Sakha: an in-scope explicit pick is
        required.

    Authorization mirrors UserContext.has_scope_for_org (exact-match, NOT
    hierarchical): the eligible Sakhas are exactly the caller's SAKHA-level
    scopes, plus every Sakha for an NSS-wide caller. The type check
    (SAKHA_SANGHA) is still the caller's responsibility via
    require_sakha_organization — this helper only settles *which* Sakha.

    Returns the resolved organization_pk (str). Raises HTTPException
    (403/422) on any authority or selection failure.
    """
    if user.is_nss_wide():
        if not requested_organization_pk:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="organization_pk (the target Sakha) is required.",
            )
        return str(requested_organization_pk)

    scoped_sakha_pks = sorted({
        str(s.organization_pk)
        for s in user.scopes
        if s.scope_level == "SAKHA" and s.organization_pk
    })

    if not scoped_sakha_pks:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You are not scoped to any Sakha, so no target Sakha can be "
                "resolved. Supply organization_pk for a Sakha within your scope."
            ),
        )

    if requested_organization_pk:
        if str(requested_organization_pk) not in scoped_sakha_pks:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You may only act on a Sakha within your own admin_scope."
                ),
            )
        return str(requested_organization_pk)

    if len(scoped_sakha_pks) == 1:
        return scoped_sakha_pks[0]

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=(
            "You are scoped to more than one Sakha — specify organization_pk "
            f"explicitly. Your Sakhas: {', '.join(scoped_sakha_pks)}."
        ),
    )


# ── Sakha affiliation insert (single owner for the uniqueness rule) ──────

def insert_sakha_affiliation(
    cur,
    *,
    sangha_sevi_pk: str,
    organization_pk: str,
    local_number: str,
    effective_from,
    is_darshak: bool = False,
) -> str:
    """
    Insert a nss.membership_sakha_affiliation row for a member's local number.

    Single owner for this write — create_user() and create_sangha_sevi() both
    route through here so the composition rule and the duplicate-number
    response stay identical.

    *is_darshak* selects the Darshak/Probationary local-number namespace
    (MBR-030C); see compose_local_sakha_erp_id().

    Enforces MBR-038A (Sakha-only) via require_sakha_organization() before the
    insert, mirroring the DB trigger so a non-Sakha org yields a clean 422
    rather than a raw trigger exception.

    nss.membership_sakha_affiliation carries
        CONSTRAINT uq_mem_sakha_aff_local_id UNIQUE (organization_pk, local_sakha_erp_id)
    Without handling, a reused number raises psycopg2.errors.UniqueViolation,
    which escapes as an unhandled 500 with no usable `detail` — the caller sees
    only "Failed (500)". This converts it to a 409 naming the number and Sakha.

    The INSERT runs inside a SAVEPOINT. That matters: once PostgreSQL raises
    inside a transaction, the whole transaction is aborted and every later
    statement fails with InFailedSqlTransaction. Rolling back to the savepoint
    leaves the connection usable, so the caller can still raise a clean
    HTTPException (and so test suites sharing one connection do not cascade).

    Returns: membership_sakha_affiliation_pk as a string.
    Raises: HTTPException 409 if the number is already taken in that Sakha,
            HTTPException 422 if organization_pk is not a SAKHA_SANGHA.
    """
    require_sakha_organization(cur, organization_pk)

    composed_id = compose_local_sakha_erp_id(
        cur, organization_pk, local_number, is_darshak=is_darshak
    )

    cur.execute("SAVEPOINT sakha_affiliation_insert")
    try:
        cur.execute(
            """
            INSERT INTO nss.membership_sakha_affiliation (
                sangha_sevi_pk, organization_pk,
                local_sakha_erp_id, effective_from,
                affiliation_status, source_event_type
            ) VALUES (%s, %s, %s, %s, 'ACTIVE', 'ENROLLMENT')
            RETURNING membership_sakha_affiliation_pk
            """,
            (str(sangha_sevi_pk), str(organization_pk), composed_id, effective_from),
        )
        aff_pk = cur.fetchone()[0]
    except psycopg2.errors.UniqueViolation:
        cur.execute("ROLLBACK TO SAVEPOINT sakha_affiliation_insert")
        cur.execute(
            "SELECT organization_name FROM nss.organization WHERE organization_pk = %s",
            (str(organization_pk),),
        )
        row = cur.fetchone()
        sakha_name = row[0] if row and row[0] else "this Sakha"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Local Sakha number '{str(local_number).strip()}' is already "
                f"assigned to another member of {sakha_name} "
                f"(ID {composed_id}). Local numbers are never reassigned — "
                "please use a different number."
            ),
        )
    cur.execute("RELEASE SAVEPOINT sakha_affiliation_insert")
    return str(aff_pk)


# ── City/Village lookup or create ────────────────────────────────────────

def resolve_or_create_city_village(cur, name: str, district_pk: str, *, actor_pk: str | None = None) -> str:
    """
    Resolve a city/village by name + district, creating it if not found.

    Lookup is case-insensitive. On create, generates a code from the
    uppercase name (max 20 chars) and defaults city_village_type to 'CITY'.

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (the DB audit trigger records the actor automatically).

    Returns: city_village_pk as a string.
    """
    cv_name = name.strip()
    cur.execute(
        """
        SELECT city_village_pk FROM nss.city_village
        WHERE LOWER(city_village_name) = LOWER(%s)
          AND district_pk = %s
          AND is_active = TRUE
        LIMIT 1
        """,
        (cv_name, district_pk),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    # Create new city_village record
    cv_code = cv_name.upper().replace(" ", "_")[:20]
    cur.execute(
        """
        INSERT INTO nss.city_village (
            district_pk, city_village_code, city_village_name,
            city_village_type
        ) VALUES (%s, %s, %s, 'CITY')
        RETURNING city_village_pk
        """,
        (district_pk, cv_code, cv_name),
    )
    return str(cur.fetchone()[0])


# ── Postal code lookup or create ────────────────────────────────────────

def resolve_or_create_postal_code(cur, postal_code_value: str, state_pk: str, country_pk: str, *, actor_pk: str | None = None) -> str:
    """
    Resolve a postal code by value + state, creating it if not found.

    Lookup is exact match. On create, inserts a new postal_code row
    linked to the given state and country.

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (the DB audit trigger records the actor automatically).

    Returns: postal_code_pk as a string.
    """
    code = postal_code_value.strip()
    cur.execute(
        """
        SELECT postal_code_pk FROM nss.postal_code
        WHERE postal_code = %s
          AND state_pk = %s
          AND is_active = TRUE
        LIMIT 1
        """,
        (code, state_pk),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])

    # Create new postal_code record
    cur.execute(
        """
        INSERT INTO nss.postal_code (
            country_pk, state_pk, postal_code
        ) VALUES (%s, %s, %s)
        RETURNING postal_code_pk
        """,
        (country_pk, state_pk, code),
    )
    return str(cur.fetchone()[0])


# ── ACTIVE status master_data PK ────────────────────────────────────────

def get_active_status_pk(cur) -> str:
    """
    Look up the master_data_pk for STATUS / ACTIVE.

    Returns: master_data_pk as a string.
    Raises HTTPException 500 if not found (seed data problem).
    """
    cur.execute(
        """
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = 'STATUS'
          AND md.value_code = 'ACTIVE'
          AND md.is_active = TRUE
        LIMIT 1
        """,
    )
    row = cur.fetchone()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ACTIVE status not found in master_data.",
        )
    return str(row[0])


# ── Centralized audit trail ─────────────────────────────────────────────

def log_audit(
    cur,
    *,
    action: str,
    table_name: str,
    record_pk: str,
    actor_pk: str | None = None,
    actor_user_account_pk: str | None = None,
    module: str | None = None,
    summary: str | None = None,
    detail: dict[str, Any] | None = None,
    is_success: bool | None = True,
) -> None:
    """
    Insert one row into ``nss.system_event_log``.

    This is the single entry-point for all audit logging.  Every
    authenticated write operation (INSERT, UPDATE, soft-DELETE, APPROVE,
    REJECT, STATUS_CHANGE, PASSWORD_CHANGE, etc.) should call this
    immediately after the business SQL succeeds.

    Parameters
    ----------
    cur : psycopg2 cursor (must be inside an open transaction)
    action : verb — CREATE, UPDATE, DELETE, APPROVE, REJECT,
             STATUS_CHANGE, PASSWORD_CHANGE, LOGIN, etc.
    table_name : affected table, e.g. ``'person'``, ``'sangha_sevi'``
    record_pk : PK of the affected row (as string UUID)
    actor_pk : ``sangha_sevi_pk`` of the person performing the action
    actor_user_account_pk : ``user_account_pk`` — useful for login events
               or when sangha_sevi doesn't exist yet
    module : functional area, e.g. ``'admin'``, ``'auth'``,
             ``'claim_approval'``, ``'family'``, ``'registration'``
    summary : one-line human description
    detail : optional dict (stored as JSONB) — changed fields,
             before/after values, request context, etc.
    is_success : True (default), False, or None
    """
    try:
        cur.execute(
            """
            INSERT INTO nss.system_event_log
                (action, table_name, record_pk,
                 actor_sangha_sevi_pk, actor_user_account_pk,
                 module, summary, detail, is_success)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                action,
                table_name,
                record_pk,
                actor_pk,
                actor_user_account_pk,
                module,
                summary,
                json.dumps(detail) if detail else None,
                is_success,
            ),
        )
    except Exception:
        # Audit logging must NEVER break the business transaction.
        # Log the failure and continue.
        logger.exception("Failed to write audit log: action=%s table=%s record=%s", action, table_name, record_pk)


# ── Entity existence check ─────────────────────────────────────────────

def require_entity(
    cur,
    table: str,
    pk_value: str,
    *,
    label: str = "Record",
    pk_column: str | None = None,
    status_code: int = 404,
) -> None:
    """
    Assert that an active row exists in ``nss.<table>``.

    By convention, PK column = ``<table>_pk``.  Override with *pk_column*
    when the table name doesn't match (e.g. ``master_data``).

    Raises HTTPException(<status_code>) if not found.
    """
    col = pk_column or f"{table}_pk"
    # Using format for table/column identifiers is safe here — the caller
    # controls these values (never user input).
    cur.execute(
        f"SELECT 1 FROM nss.{table} WHERE {col} = %s AND is_active = TRUE",
        (str(pk_value),),
    )
    if cur.fetchone() is None:
        raise HTTPException(
            status_code=status_code,
            detail=f"{label} not found.",
        )


# ── Duplicate contact check ────────────────────────────────────────────

def check_duplicate_contact(
    cur,
    *,
    mobile_number: str | None = None,
    country_phone_code: str | None = None,
    email: str | None = None,
    exclude_person_pk: str | None = None,
) -> None:
    """
    Raise HTTP 409 if a person with the same mobile or email already exists.

    *exclude_person_pk* is used for UPDATE flows (don't conflict with self).
    """
    if mobile_number and country_phone_code:
        sql = (
            "SELECT person_pk FROM nss.person "
            "WHERE country_phone_code = %s AND mobile_number = %s AND is_active = TRUE"
        )
        params: list = [country_phone_code, mobile_number]
        if exclude_person_pk:
            sql += " AND person_pk != %s"
            params.append(exclude_person_pk)
        cur.execute(sql, params)
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A person with this mobile number already exists.",
            )

    if email:
        sql = (
            "SELECT person_pk FROM nss.person "
            "WHERE LOWER(email) = LOWER(%s) AND is_active = TRUE"
        )
        params = [email]
        if exclude_person_pk:
            sql += " AND person_pk != %s"
            params.append(exclude_person_pk)
        cur.execute(sql, params)
        if cur.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A person with this email already exists.",
            )


# ── Password history ───────────────────────────────────────────────────

def record_password_history(
    cur,
    user_account_pk: str,
    password_hash: str,
    reason: str = "CHANGE",
    *,
    actor_pk: str | None = None,
) -> None:
    """
    Insert a row into ``nss.password_history``.

    *actor_pk* is accepted for call-site compatibility but not written
    to the table (the DB audit trigger records the actor automatically).
    """
    cur.execute(
        """
        INSERT INTO nss.password_history (
            user_account_pk, password_hash, changed_reason
        ) VALUES (%s, %s, %s)
        """,
        (str(user_account_pk), password_hash, reason),
    )


# ── Password validate + hash + expiry ──────────────────────────────────

def validate_and_hash_password(password: str) -> tuple[str, datetime]:
    """
    Validate password against policy, hash it, compute expiry.

    Returns ``(password_hash, password_expires_at)``.
    Raises HTTPException 422 if policy violations exist.
    """
    from api.services.auth_service import hash_password, validate_password_policy
    from api.config import settings

    violations = validate_password_policy(password)
    if violations:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=violations,
        )
    pw_hash = hash_password(password)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.PASSWORD_EXPIRY_DAYS
    )
    return pw_hash, expires_at
