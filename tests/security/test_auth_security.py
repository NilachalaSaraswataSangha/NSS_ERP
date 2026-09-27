"""
NSS ERP — Tier 5 Authentication security tests.

Security-focused subset extracted from tests/api/test_auth.py:
  1. GET  /api/v1/auth/me               — rejects garbage/expired tokens
  2. POST /api/v1/auth/change-password  — enforces password policy
  3. Account lockout after 5 failed login attempts

These tests run against local PostgreSQL.
The database must have Tier 0-5 DDL + seed data bootstrapped.

A test user is created in the database at the start of the module
and cleaned up at the end (via the conftest.py SAVEPOINT rollback).
"""

import pytest


pytestmark = pytest.mark.integration


# ── Test user constants ─────────────────────────────────────────────────

TEST_PASSWORD = "TestPass1"
TEST_NEW_PASSWORD = "NewPass2x"


# ── Module-scoped fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_user(write_conn):
    """
    Create a test user account linked to an existing person.

    Finds the first active person without a user_account,
    creates a user_account, and cleans up after the module.
    Returns dict with person_pk, user_account_pk, sangha_sevi_id.

    NOTE: cleanup is automatic via transaction rollback in conftest.py.
    """
    from api.services.auth_service import hash_password

    cur = write_conn.cursor()

    # Find an active person with a sangha_sevi record but no user_account
    cur.execute("""
        SELECT p.person_pk, ss.sangha_sevi_id
        FROM nss.person p
        JOIN nss.sangha_sevi ss ON ss.person_pk = p.person_pk AND ss.is_active = TRUE
        LEFT JOIN nss.user_account ua ON ua.person_pk = p.person_pk AND ua.is_active = TRUE
        WHERE p.is_active = TRUE
          AND ua.user_account_pk IS NULL
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No available person without a user account. Cannot run auth tests.")

    person_pk, sangha_sevi_id = row

    # Create user_account
    password_hash = hash_password(TEST_PASSWORD)
    cur.execute("""
        INSERT INTO nss.user_account (
            person_pk, password_hash, account_status,
            force_password_change, password_expires_at
        ) VALUES (%s, %s, 'ACTIVE', FALSE, NOW() + INTERVAL '365 days')
        RETURNING user_account_pk
    """, (str(person_pk), password_hash))
    user_account_pk = cur.fetchone()[0]

    info = {
        "person_pk": person_pk,
        "user_account_pk": user_account_pk,
        "sangha_sevi_id": sangha_sevi_id,
    }

    yield info
    # No manual cleanup needed — conftest SAVEPOINT handles rollback


# ── Login helper for authenticated tests ────────────────────────────────

def _login(client, test_user, password=TEST_PASSWORD):
    """Helper to login and return tokens."""
    response = client.post("/api/v1/auth/login", json={
        "login_id": test_user["sangha_sevi_id"],
        "password": password,
    })
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()


# ── Me tests ────────────────────────────────────────────────────────────

class TestMe:
    """GET /api/v1/auth/me"""

    def test_me_with_expired_token_fails(self, client):
        """GET /me with garbage token returns 401."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401


# ── Change password tests ───────────────────────────────────────────────

class TestChangePassword:
    """POST /api/v1/auth/change-password"""

    def test_change_password_policy_violation(self, client, test_user):
        """Password that violates policy returns 422."""
        tokens = _login(client, test_user)
        # Missing uppercase + too short
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "current_password": TEST_PASSWORD,
                "new_password": "short1",
            },
        )
        assert response.status_code == 422


# ── Lockout tests ───────────────────────────────────────────────────────

class TestLockout:
    """Account lockout after 5 failed attempts."""

    def test_lockout_after_five_failures(self, client, test_user, write_conn):
        """
        After 5 failed login attempts, the account is locked for 30 seconds.
        The 6th attempt should also fail with a lockout message.
        """
        # Exhaust attempts
        for i in range(5):
            client.post("/api/v1/auth/login", json={
                "login_id": test_user["sangha_sevi_id"],
                "password": "WrongPassword1",
            })

        # 6th attempt — should be locked
        response = client.post("/api/v1/auth/login", json={
            "login_id": test_user["sangha_sevi_id"],
            "password": "WrongPassword1",
        })
        assert response.status_code == 401
        assert "locked" in response.json()["detail"].lower()

        # Correct password also fails while locked
        response2 = client.post("/api/v1/auth/login", json={
            "login_id": test_user["sangha_sevi_id"],
            "password": TEST_PASSWORD,
        })
        assert response2.status_code == 401

        # Reset lockout for subsequent tests (use shared test connection)
        with write_conn.cursor() as cur:
            cur.execute("""
                UPDATE nss.user_account
                SET failed_login_attempts = 0, locked_until = NULL
                WHERE user_account_pk = %s
            """, (str(test_user["user_account_pk"]),))
