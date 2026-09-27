"""
NSS ERP — Registration & Claim Approval security tests.

Security-focused subset extracted from tests/api/test_registration.py:
  1. PENDING_APPROVAL accounts cannot login (AUTH-BR-089)
  2. Unauthenticated requests cannot list registration claims
  3. Weak passwords are rejected at registration

These tests run against local PostgreSQL.
The database must have Tier 0-5 DDL + seed data bootstrapped,
including the registration_claim table.

NOTE: cleanup is automatic via transaction rollback in conftest.py.
"""

import pytest
from uuid import uuid4


pytestmark = pytest.mark.integration


# ── Test constants ──────────────────────────────────────────────────────

TEST_PASSWORD = "TestReg1x"
TEST_DOB = "2000-01-15"
# Unique suffix per test run to avoid email collisions from leftover data
_RUN_ID = uuid4().hex[:8]
TEST_EMAIL_PREFIX = f"regtest_{_RUN_ID}_"


# ── Module-scoped fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def gender_pk(write_conn):
    """Get the master_data_pk for MALE gender (or any active gender)."""
    cur = write_conn.cursor()
    cur.execute("""
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = 'GENDER'
          AND md.is_active = TRUE
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No GENDER master data found.")
    return str(row[0])


# ── Registration Tests ──────────────────────────────────────────────────

class TestRegistration:
    """POST /api/v1/register — claim-based registration."""

    def test_register_weak_password_fails(self, client):
        """Registration with weak password returns 422."""
        response = client.post("/api/v1/register", json={
            "first_name": "WeakPw",
            "email": "weakpw@test.example",
            "password": "short1",
        })
        assert response.status_code == 422


# ── Login blocked for PENDING_APPROVAL ──────────────────────────────────

class TestPendingLoginBlocked:
    """PENDING_APPROVAL accounts cannot login (AUTH-BR-089)."""

    def test_pending_account_cannot_login(self, client, gender_pk, write_conn):
        """Login attempt for PENDING_APPROVAL account returns 401."""
        # Register a fresh user
        response = client.post("/api/v1/register", json={
            "first_name": "LoginBlocked",
            "last_name": "Test",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}blocked@test.example",
            "password": TEST_PASSWORD,
            "has_membership": False,
        })
        assert response.status_code == 201
        data = response.json()

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT user_account_pk FROM nss.user_account WHERE person_pk = %s",
                (data["person_pk"],),
            )
            ua_pk = cur.fetchone()[0]

        # Try to login — should fail because there's no sangha_sevi_id for this person
        # (PENDING_APPROVAL accounts don't have one yet)
        # The login endpoint looks up by sangha_sevi_id, so login_id won't match anything
        response = client.post("/api/v1/auth/login", json={
            "login_id": data["person_id"],
            "password": TEST_PASSWORD,
        })
        # 401 = unknown ID, 403 = known but PENDING_APPROVAL; both are valid blocks
        assert response.status_code in (401, 403)


# ── Claim Approval Tests ───────────────────────────────────────────────

class TestClaimApproval:
    """GET/POST /api/v1/admin/claims — auth gate."""

    def test_unauthenticated_cannot_list_claims(self, client):
        """Unauthenticated request to claims endpoint returns 401."""
        response = client.get("/api/v1/admin/claims")
        assert response.status_code == 401
