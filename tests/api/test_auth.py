"""
NSS ERP — Tier 5 Authentication API tests.

Integration tests for the auth endpoints:
  1. POST /api/v1/auth/login       — happy path + failure cases
  2. POST /api/v1/auth/refresh     — token refresh
  3. POST /api/v1/auth/logout      — stateless logout
  4. POST /api/v1/auth/change-password — password change
  5. GET  /api/v1/auth/me          — current user profile

These tests run against local PostgreSQL.
The database must have Tier 0–5 DDL + seed data bootstrapped.

A test user is created in the database at the start of the module
and cleaned up at the end. The test user is linked to an existing
person record (the first active person found in the database).
"""

import pytest
from fastapi.testclient import TestClient


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


# ── Login tests ─────────────────────────────────────────────────────────

class TestLogin:
    """POST /api/v1/auth/login"""

    def test_login_success(self, client, test_user):
        """Valid credentials return 200 with access + refresh tokens."""
        response = client.post("/api/v1/auth/login", json={
            "login_id": test_user["sangha_sevi_id"],
            "password": TEST_PASSWORD,
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert isinstance(data["force_password_change"], bool)

    def test_login_wrong_password(self, client, test_user):
        """Wrong password returns 401."""
        response = client.post("/api/v1/auth/login", json={
            "login_id": test_user["sangha_sevi_id"],
            "password": "WrongPassword1",
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_nonexistent_id(self, client):
        """Non-existent login_id returns 401 (no information leak)."""
        response = client.post("/api/v1/auth/login", json={
            "login_id": "NONEXISTENT_ID_99999",
            "password": "SomePass1",
        })
        assert response.status_code == 401
        assert "Invalid credentials" in response.json()["detail"]

    def test_login_missing_fields(self, client):
        """Missing required fields return 422."""
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 422

    def test_login_empty_password(self, client, test_user):
        """Empty password returns 422 (Pydantic min_length=1)."""
        response = client.post("/api/v1/auth/login", json={
            "login_id": test_user["sangha_sevi_id"],
            "password": "",
        })
        assert response.status_code == 422


# ── Login helper for authenticated tests ────────────────────────────────

def _login(client, test_user, password=TEST_PASSWORD):
    """Helper to login and return tokens."""
    response = client.post("/api/v1/auth/login", json={
        "login_id": test_user["sangha_sevi_id"],
        "password": password,
    })
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return response.json()


# ── Refresh tests ───────────────────────────────────────────────────────

class TestRefresh:
    """POST /api/v1/auth/refresh"""

    def test_refresh_success(self, client, test_user):
        """Valid refresh token returns a new access token."""
        tokens = _login(client, test_user)
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["refresh_token"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_refresh_invalid_token(self, client):
        """Invalid refresh token returns 401."""
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "not.a.valid.token",
        })
        assert response.status_code == 401

    def test_refresh_with_access_token_fails(self, client, test_user):
        """Using an access token as refresh token returns 401."""
        tokens = _login(client, test_user)
        response = client.post("/api/v1/auth/refresh", json={
            "refresh_token": tokens["access_token"],
        })
        assert response.status_code == 401


# ── Logout tests ────────────────────────────────────────────────────────

class TestLogout:
    """POST /api/v1/auth/logout"""

    def test_logout_success(self, client, test_user):
        """Authenticated logout returns success message."""
        tokens = _login(client, test_user)
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200
        assert "message" in response.json()

    def test_logout_without_token_fails(self, client):
        """Logout without Authorization header returns 401."""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 401


# ── Me tests ────────────────────────────────────────────────────────────

class TestMe:
    """GET /api/v1/auth/me"""

    def test_me_returns_profile(self, client, test_user):
        """Authenticated user gets their profile with RBAC context."""
        tokens = _login(client, test_user)
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user_account_pk"] == str(test_user["user_account_pk"])
        assert data["person_pk"] == str(test_user["person_pk"])
        assert data["sangha_sevi_id"] == test_user["sangha_sevi_id"]
        assert "permissions" in data
        assert "scopes" in data
        assert isinstance(data["permissions"], list)
        assert isinstance(data["scopes"], list)

    def test_me_without_token_fails(self, client):
        """GET /me without token returns 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


# ── Change password tests ───────────────────────────────────────────────

class TestChangePassword:
    """POST /api/v1/auth/change-password"""

    def test_change_password_success(self, client, test_user):
        """Valid password change returns success and new password works."""
        tokens = _login(client, test_user)

        # Change password
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "current_password": TEST_PASSWORD,
                "new_password": TEST_NEW_PASSWORD,
            },
        )
        assert response.status_code == 200
        assert "message" in response.json()

        # Verify new password works
        response2 = client.post("/api/v1/auth/login", json={
            "login_id": test_user["sangha_sevi_id"],
            "password": TEST_NEW_PASSWORD,
        })
        assert response2.status_code == 200

        # Restore original password for other tests
        tokens2 = response2.json()
        client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens2['access_token']}"},
            json={
                "current_password": TEST_NEW_PASSWORD,
                "new_password": TEST_PASSWORD,
            },
        )

    def test_change_password_wrong_current(self, client, test_user):
        """Wrong current password returns 401."""
        tokens = _login(client, test_user)
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "current_password": "WrongCurrent1",
                "new_password": TEST_NEW_PASSWORD,
            },
        )
        assert response.status_code == 401

    def test_change_password_same_as_current(self, client, test_user):
        """New password same as current returns 422."""
        tokens = _login(client, test_user)
        response = client.post(
            "/api/v1/auth/change-password",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            json={
                "current_password": TEST_PASSWORD,
                "new_password": TEST_PASSWORD,
            },
        )
        assert response.status_code == 422
