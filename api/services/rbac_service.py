"""
NSS ERP — RBAC service.

Loads and evaluates role-based access control:
  - Load user roles, permissions, and scopes from the database
  - Check if a user has a specific permission
  - Check if a user's scope covers a given organization

Authority: SOL-ADMIN-004, SOL-AUTH-004,
           Tier 5 design decisions (2026-09-15)

RBAC Model (FROZEN):
  - 9 parallel roles (no hierarchy/inheritance)
  - Multi-role per user (user_role junction table)
  - Scope-on-assignment (admin_scope per user_role)
  - Composite permissions = union of all active role permissions
"""

from dataclasses import dataclass, field
from uuid import UUID

from fastapi import HTTPException, status


@dataclass
class ScopeInfo:
    """A single scope assignment (from admin_scope)."""
    user_role_pk: UUID
    role_code: str
    scope_level: str           # NSS-WIDE, KENDRA, ANCHALIKA, ZILLA, SAKHA,
                               # PATHA_CHAKRA, KENDRA_MAHILA_SANGHA
    organization_pk: UUID | None  # NULL for NSS-WIDE


@dataclass
class UserContext:
    """
    Complete auth + RBAC context for the current user.

    Built once per request from the JWT + database lookups.
    Passed to endpoint handlers and RBAC checks.
    """
    user_account_pk: UUID
    person_pk: UUID
    sangha_sevi_pk: UUID | None = None
    sangha_sevi_id: str = ""
    permissions: set[str] = field(default_factory=set)
    scopes: list[ScopeInfo] = field(default_factory=list)
    force_password_change: bool = False

    def has_permission(self, permission_code: str) -> bool:
        """Check if the user has a specific permission (union across all roles)."""
        return permission_code in self.permissions

    def has_any_permission(self, *permission_codes: str) -> bool:
        """Check if the user has any of the given permissions."""
        return bool(self.permissions & set(permission_codes))

    def has_scope_for_org(self, organization_pk: UUID | None) -> bool:
        """
        Check if any of the user's scopes cover a given organization.

        NSS-WIDE scope covers everything.
        Otherwise, the organization_pk must match one of the user's scopes.

        Compares as strings deliberately: psycopg2 returns admin_scope.
        organization_pk as a plain str (no register_uuid() call in this
        codebase — see api/database.py), while callers commonly pass a
        uuid.UUID (e.g. UUID(body.organization_pk)). A direct `==` between
        str and UUID is always False, which silently denied every
        in-scope request. Normalizing both sides to str avoids relying on
        the caller's type.
        """
        if organization_pk is None:
            return any(scope.scope_level == "NSS-WIDE" for scope in self.scopes)

        target = str(organization_pk)
        for scope in self.scopes:
            if scope.scope_level == "NSS-WIDE":
                return True
            if scope.organization_pk and str(scope.organization_pk) == target:
                return True
        return False

    def is_nss_wide(self) -> bool:
        """Check if the user has any NSS-WIDE scope."""
        return any(s.scope_level == "NSS-WIDE" for s in self.scopes)

    def is_super_admin(self) -> bool:
        """
        The sole blanket, all-scope authority (ADMIN-BR-043/077).

        Only the NSS_ERP_ADMIN role carries unrestricted, organization-wide
        reach. Every other role — including the other ``*_ADMIN`` roles — is
        scope-bounded even when it holds the same permission (ADMIN-BR-076).
        Callers gate any "manage anything" branch on this, never on a
        permission alone.
        """
        return any(s.role_code == "NSS_ERP_ADMIN" for s in self.scopes)

    @property
    def actor_pk(self) -> str | None:
        """Sangha Sevi PK as string for audit columns, or None."""
        return str(self.sangha_sevi_pk) if self.sangha_sevi_pk else None


def load_user_context(conn, user_account_pk: UUID) -> UserContext | None:
    """
    Load the full RBAC context for a user from the database.

    Performs two queries:
      1. user_account → basic info + force_password_change
      2. user_role + role_permission + admin_scope → permissions + scopes

    Returns None if user_account is not found or inactive.
    """
    with conn.cursor() as cur:
        # 1. Get user account basics
        cur.execute(
            """
            SELECT ua.user_account_pk,
                   ua.person_pk,
                   ua.force_password_change,
                   ss.sangha_sevi_id,
                   ss.sangha_sevi_pk
            FROM nss.user_account ua
            JOIN nss.person p ON p.person_pk = ua.person_pk
            LEFT JOIN nss.sangha_sevi ss ON ss.person_pk = ua.person_pk
                  AND ss.is_active = TRUE
            WHERE ua.user_account_pk = %s
              AND ua.is_active = TRUE
              AND ua.account_status = 'ACTIVE'
            """,
            (str(user_account_pk),),
        )
        row = cur.fetchone()
        if row is None:
            return None

        ua_pk, person_pk, force_pw, sevi_id, sevi_pk = row

        # 2. Get permissions (union across all active roles)
        cur.execute(
            """
            SELECT DISTINCT pm.permission_code
            FROM nss.user_role ur
            JOIN nss.role_permission rp
              ON rp.role_master_pk = ur.role_master_pk
             AND rp.is_active = TRUE
            JOIN nss.permission_master pm
              ON pm.permission_master_pk = rp.permission_master_pk
             AND pm.is_active = TRUE
            WHERE ur.user_account_pk = %s
              AND ur.is_active = TRUE
            """,
            (str(user_account_pk),),
        )
        permissions = {r[0] for r in cur.fetchall()}

        # 3. Get scopes (one per active user_role assignment)
        cur.execute(
            """
            SELECT ur.user_role_pk,
                   rm.role_code,
                   asc2.scope_level,
                   asc2.organization_pk
            FROM nss.user_role ur
            JOIN nss.role_master rm
              ON rm.role_master_pk = ur.role_master_pk
            LEFT JOIN nss.admin_scope asc2
              ON asc2.user_role_pk = ur.user_role_pk
             AND asc2.is_active = TRUE
            WHERE ur.user_account_pk = %s
              AND ur.is_active = TRUE
            """,
            (str(user_account_pk),),
        )
        scopes = []
        for s_row in cur.fetchall():
            ur_pk, role_code, scope_level, org_pk = s_row
            if scope_level:  # admin_scope exists for this role assignment
                scopes.append(ScopeInfo(
                    user_role_pk=ur_pk,
                    role_code=role_code,
                    scope_level=scope_level,
                    organization_pk=org_pk,
                ))

    return UserContext(
        user_account_pk=ua_pk,
        person_pk=person_pk,
        sangha_sevi_pk=sevi_pk,
        sangha_sevi_id=sevi_id or "",
        permissions=permissions,
        scopes=scopes,
        force_password_change=force_pw,
    )


# ── Scope-authority enforcement (ADMIN-BR-076/077/078) ──────────────────
# Every administrator is bounded to their own organizational scope. The sole
# blanket authority is the NSS_ERP_ADMIN role (equivalently, an NSS-WIDE
# scope). "Scope" is the recursive subtree of each organization the actor
# holds scope over — their org plus every descendant — so a Kendra-scoped
# admin reaches the whole tree through scope, not through a blanket bypass.
#
# These live here (not in a single router) because both the Administration
# and Claim-Approval routers must define "in scope" identically: what an
# admin can see (list filters) must equal what an admin can manage (write
# guards). Direct-org-pk matching (has_scope_for_org) is the old model and
# is retained only for the NSS-WIDE short-circuit inside these helpers.


def actor_scope_org_pks(cur, user: UserContext) -> set[str] | None:
    """
    Set of organization_pks the actor may act within (ADMIN-BR-076).

    Returns ``None`` to mean "all organizations", reserved for the sole
    global authority — the NSS_ERP_ADMIN role or an NSS-WIDE scope
    (ADMIN-BR-077). For a scope-bounded admin the set is the recursive
    subtree (each scoped organization + all its descendants). An admin with
    no organization-anchored scope resolves to the empty set.
    """
    if user.is_super_admin() or user.is_nss_wide():
        return None
    roots = [str(s.organization_pk) for s in user.scopes if s.organization_pk]
    if not roots:
        return set()
    placeholders = ",".join(["%s"] * len(roots))
    cur.execute(
        f"""
        WITH RECURSIVE subtree AS (
            SELECT organization_pk
            FROM nss.organization
            WHERE organization_pk IN ({placeholders})
            UNION ALL
            SELECT o.organization_pk
            FROM nss.organization o
            JOIN subtree s ON o.parent_organization_pk = s.organization_pk
        )
        SELECT organization_pk FROM subtree
        """,
        roots,
    )
    return {str(r[0]) for r in cur.fetchall()}


def org_in_scope(cur, user: UserContext, organization_pk) -> bool:
    """
    Subtree-aware replacement for ``UserContext.has_scope_for_org``.

    True when *organization_pk* falls within the actor's scope subtree, or
    the actor is the global authority. Unlike ``has_scope_for_org`` this
    walks the org hierarchy, so a Kendra admin covers every descendant Sakha.
    """
    allowed = actor_scope_org_pks(cur, user)
    if allowed is None:
        return True
    return organization_pk is not None and str(organization_pk) in allowed


def require_org_in_scope(cur, user: UserContext, organization_pk, action: str) -> None:
    """403 unless *organization_pk* falls within the actor's scope subtree."""
    if org_in_scope(cur, user, organization_pk):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"You can only {action} within your admin scope.",
    )


def require_person_in_scope(cur, user: UserContext, person_pk: str, action: str) -> None:
    """
    403 unless the person is reachable within the actor's scope (ADMIN-BR-076).

    A person is in scope when any of their active Sangha-Sevi organizations
    falls inside the actor's scope subtree. A person with no active Sangha
    Sevi has no organizational anchor and is therefore only reachable by the
    global authority (ADMIN-BR-077).
    """
    allowed = actor_scope_org_pks(cur, user)
    if allowed is None:
        return
    cur.execute(
        "SELECT organization_pk FROM nss.sangha_sevi "
        "WHERE person_pk = %s AND is_active = TRUE",
        (str(person_pk),),
    )
    person_orgs = {str(r[0]) for r in cur.fetchall() if r[0]}
    if person_orgs & allowed:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"You can only {action} within your admin scope.",
    )


def require_account_in_scope(cur, user: UserContext, user_account_pk, action: str) -> None:
    """
    403 unless the account's person is within the actor's scope (ADMIN-BR-076).

    Account-lifecycle operations (reset password, status change, delete) stay
    bounded to the actor's scope even for the global-authority exemption path,
    which ``require_person_in_scope`` short-circuits.
    """
    allowed = actor_scope_org_pks(cur, user)
    if allowed is None:
        return
    cur.execute(
        "SELECT person_pk FROM nss.user_account WHERE user_account_pk = %s",
        (str(user_account_pk),),
    )
    row = cur.fetchone()
    if row is None:
        # Non-existent account: leave the 404 to the caller's require_entity.
        return
    require_person_in_scope(cur, user, str(row[0]), action)
