"""
NSS ERP — Tier 5 Audit security tests.

Security-focused subset extracted from tests/api/test_audit.py and
tests/api/test_foundation.py:
  1. GET /api/v1/audit/change-log — authentication + AUDIT_VIEW gate
  2. GET /api/v1/foundation/change-log — must never exist (Tier 1
     anonymous change-log guard)

These tests run against local PostgreSQL. The conftest module SAVEPOINT
rolls back all inserted rows.
"""

import pytest

pytestmark = pytest.mark.integration


ADMIN_PASSWORD = "AuditAdmin1"


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def audit_admin(write_conn):
    """
    Create a user with NSS_ERP_ADMIN + NSS-WIDE scope, which grants
    AUDIT_VIEW per the seeded role→permission map.
    """
    from api.services.auth_service import hash_password

    cur = write_conn.cursor()
    cur.execute("""
        SELECT p.person_pk, ss.sangha_sevi_id
        FROM nss.person p
        JOIN nss.sangha_sevi ss ON ss.person_pk = p.person_pk AND ss.is_active = TRUE
        LEFT JOIN nss.user_account ua
               ON ua.person_pk = p.person_pk AND ua.is_active = TRUE
        WHERE p.is_active = TRUE
          AND ua.user_account_pk IS NULL
        ORDER BY p.created_at
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No available person for audit admin test user.")
    person_pk, sangha_sevi_id = row

    cur.execute("""
        INSERT INTO nss.user_account (
            person_pk, password_hash, account_status,
            force_password_change, password_expires_at
        ) VALUES (%s, %s, 'ACTIVE', FALSE, NOW() + INTERVAL '365 days')
        RETURNING user_account_pk
    """, (str(person_pk), hash_password(ADMIN_PASSWORD)))
    user_account_pk = cur.fetchone()[0]

    cur.execute(
        "SELECT role_master_pk FROM nss.role_master "
        "WHERE role_code = 'NSS_ERP_ADMIN' AND is_active = TRUE"
    )
    role_row = cur.fetchone()
    if role_row is None:
        pytest.skip("NSS_ERP_ADMIN role not found in database.")

    cur.execute("""
        INSERT INTO nss.user_role (user_account_pk, role_master_pk)
        VALUES (%s, %s) RETURNING user_role_pk
    """, (str(user_account_pk), str(role_row[0])))
    user_role_pk = cur.fetchone()[0]

    cur.execute("""
        INSERT INTO nss.admin_scope (user_role_pk, scope_level, organization_pk)
        VALUES (%s, 'NSS-WIDE', NULL)
    """, (str(user_role_pk),))

    return {
        "person_pk": person_pk,
        "sangha_sevi_id": sangha_sevi_id,
        "user_account_pk": user_account_pk,
    }


@pytest.fixture(scope="module")
def admin_headers(client, audit_admin):
    """Authorization header for a user holding AUDIT_VIEW."""
    resp = client.post("/api/v1/auth/login", json={
        "login_id": audit_admin["sangha_sevi_id"],
        "password": ADMIN_PASSWORD,
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture(scope="module")
def norole_headers(client, write_conn, audit_admin):
    """
    Authorization header for an authenticated user with NO roles — hence
    no AUDIT_VIEW — used to prove the permission gate returns 403.
    """
    from api.services.auth_service import hash_password

    cur = write_conn.cursor()
    cur.execute("""
        SELECT p.person_pk, ss.sangha_sevi_id
        FROM nss.person p
        JOIN nss.sangha_sevi ss ON ss.person_pk = p.person_pk AND ss.is_active = TRUE
        LEFT JOIN nss.user_account ua
               ON ua.person_pk = p.person_pk AND ua.is_active = TRUE
        WHERE p.is_active = TRUE
          AND ua.user_account_pk IS NULL
          AND p.person_pk <> %s
        ORDER BY p.created_at
        LIMIT 1
    """, (str(audit_admin["person_pk"]),))
    row = cur.fetchone()
    if row is None:
        pytest.skip("No available person for no-role test user.")
    person_pk, sangha_sevi_id = row

    cur.execute("""
        INSERT INTO nss.user_account (
            person_pk, password_hash, account_status,
            force_password_change, password_expires_at
        ) VALUES (%s, %s, 'ACTIVE', FALSE, NOW() + INTERVAL '365 days')
    """, (str(person_pk), hash_password(ADMIN_PASSWORD)))

    resp = client.post("/api/v1/auth/login", json={
        "login_id": sangha_sevi_id,
        "password": ADMIN_PASSWORD,
    })
    assert resp.status_code == 200, f"No-role login failed: {resp.json()}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Auth / permission gate ───────────────────────────────────────────────

class TestChangeLogAuth:
    """GET /api/v1/audit/change-log — authentication + AUDIT_VIEW gate."""

    def test_requires_authentication(self, client):
        """No token → 401."""
        r = client.get("/api/v1/audit/change-log")
        assert r.status_code == 401

    def test_forbidden_without_permission(self, client, norole_headers):
        """Authenticated but no AUDIT_VIEW → 403."""
        r = client.get("/api/v1/audit/change-log", headers=norole_headers)
        assert r.status_code == 403

    def test_admin_can_read(self, client, admin_headers):
        """AUDIT_VIEW holder → 200 with a JSON list."""
        r = client.get("/api/v1/audit/change-log", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ── Tier 1 guard still holds ──────────────────────────────────────────────

class TestChangeLogNotExposed:
    """Verify that field_change_log has NO anonymous endpoint in Tier 1."""

    def test_change_log_endpoint_returns_404(self, client):
        """
        /api/v1/foundation/change-log must NOT exist.

        Audit data is deferred to Tier 5 authenticated API.
        If this test fails, someone added an anonymous audit endpoint.
        """
        r = client.get("/api/v1/foundation/change-log")
        assert r.status_code in (404, 405), (
            f"change-log endpoint should not exist in Tier 1, "
            f"got status {r.status_code}"
        )
