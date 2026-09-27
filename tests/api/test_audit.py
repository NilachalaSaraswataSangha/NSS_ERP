"""
NSS ERP — Tier 5 Audit API tests.

Integration tests for the authenticated audit-trail endpoint:
  GET /api/v1/audit/change-log  — requires the AUDIT_VIEW permission.

Also re-asserts the Tier 1 no-auth guard: /api/v1/foundation/change-log
must still NOT exist (audit data is reachable only via the authenticated
Tier 5 endpoint).

Security-focused checks (authentication + AUDIT_VIEW gate) now live in
tests/security/test_audit_security.py::TestChangeLogAuth.

These tests run against local PostgreSQL. The conftest module SAVEPOINT
rolls back all inserted rows.
"""

import pytest
from uuid import uuid4

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
def sample_change(write_conn):
    """Insert a deterministic field_change_log row to query against."""
    cur = write_conn.cursor()
    record_pk = str(uuid4())
    cur.execute("""
        INSERT INTO nss.field_change_log (
            table_name, record_pk, field_name,
            old_value, new_value, change_reason
        ) VALUES ('person', %s, 'first_name', 'Old', 'New', 'audit-unit-test')
        RETURNING field_change_log_pk
    """, (record_pk,))
    return {"field_change_log_pk": str(cur.fetchone()[0]), "record_pk": record_pk}


# ── Filtering + pagination ────────────────────────────────────────────────

class TestChangeLogQuery:
    """Filtering and pagination behaviour."""

    def test_filter_by_table_and_record(self, client, admin_headers, sample_change):
        """table_name + record_pk filters return the inserted row."""
        r = client.get(
            "/api/v1/audit/change-log",
            params={"table_name": "person", "record_pk": sample_change["record_pk"]},
            headers=admin_headers,
        )
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) == 1
        row = rows[0]
        assert row["table_name"] == "person"
        assert row["record_pk"] == sample_change["record_pk"]
        assert row["field_name"] == "first_name"
        assert row["old_value"] == "Old"
        assert row["new_value"] == "New"

    def test_pagination_limit(self, client, admin_headers, sample_change):
        """limit caps the number of returned rows."""
        r = client.get(
            "/api/v1/audit/change-log",
            params={"limit": 1},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert len(r.json()) <= 1

    def test_limit_over_max_rejected(self, client, admin_headers):
        """limit above MAX_LIMIT (500) is rejected by validation."""
        r = client.get(
            "/api/v1/audit/change-log",
            params={"limit": 10_000},
            headers=admin_headers,
        )
        assert r.status_code == 422


# ── Tier 1 guard still holds ──────────────────────────────────────────────

class TestFoundationChangeLogStillHidden:
    """The anonymous Tier 1 change-log endpoint must never exist."""

    def test_foundation_change_log_absent(self, client):
        r = client.get("/api/v1/foundation/change-log")
        assert r.status_code in (404, 405)
