"""
NSS ERP — Registration & Claim Approval tests.

Integration tests for:
  1. POST /api/v1/register — self-registration (claim-based flow)
  2. GET  /api/v1/admin/claims — list pending claims
  3. POST /api/v1/admin/claims/{pk}/approve — approve a claim
  4. POST /api/v1/admin/claims/{pk}/reject  — reject a claim

These tests run against local PostgreSQL.
The database must have Tier 0–5 DDL + seed data bootstrapped,
including the registration_claim table.

Test flow:
  - Register a new person → account is PENDING_APPROVAL
  - Verify login fails for PENDING_APPROVAL
  - Admin lists claims → sees the new claim
  - Admin approves → account ACTIVE, sangha_sevi created
  - Verify login succeeds after approval
  - Register another person, admin rejects → account stays PENDING

NOTE: cleanup is automatic via transaction rollback in conftest.py.
"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4


pytestmark = pytest.mark.integration


# ── Test constants ──────────────────────────────────────────────────────

TEST_PASSWORD = "TestReg1x"
TEST_FIRST_NAME = "RegTest"
TEST_LAST_NAME = "AutoCleanup"
TEST_DOB = "2000-01-15"
# Unique suffix per test run to avoid email collisions from leftover data
_RUN_ID = uuid4().hex[:8]
TEST_EMAIL_PREFIX = f"regtest_{_RUN_ID}_"


# ── Module-scoped fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_tokens(client, write_conn):
    """
    Get auth tokens for an admin user who has MEMBERSHIP_APPROVE
    and ADMIN_USER_MANAGE permissions.

    Finds the first active admin user with appropriate permissions.
    """
    cur = write_conn.cursor()

    # Find an admin with MEMBERSHIP_APPROVE permission
    cur.execute("""
        SELECT ua.user_account_pk, ss.sangha_sevi_id
        FROM nss.user_account ua
        JOIN nss.person p ON p.person_pk = ua.person_pk
        JOIN nss.sangha_sevi ss ON ss.person_pk = ua.person_pk AND ss.is_active = TRUE
        JOIN nss.user_role ur ON ur.user_account_pk = ua.user_account_pk AND ur.is_active = TRUE
        JOIN nss.role_permission rp ON rp.role_master_pk = ur.role_master_pk AND rp.is_active = TRUE
        JOIN nss.permission_master pm ON pm.permission_master_pk = rp.permission_master_pk
        WHERE ua.is_active = TRUE
          AND ua.account_status = 'ACTIVE'
          AND pm.permission_code IN ('MEMBERSHIP_APPROVE', 'ADMIN_USER_MANAGE')
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No admin user with MEMBERSHIP_APPROVE permission. Cannot run claim tests.")

    admin_pk, sevi_id = row

    # We need to know the admin's password — set a known one
    from api.services.auth_service import hash_password
    pw_hash = hash_password(TEST_PASSWORD)

    cur.execute("""
        UPDATE nss.user_account
        SET password_hash = %s, password_changed_at = NOW(),
            password_expires_at = NOW() + INTERVAL '365 days'
        WHERE user_account_pk = %s
    """, (pw_hash, str(admin_pk)))

    # Login
    response = client.post("/api/v1/auth/login", json={
        "login_id": sevi_id,
        "password": TEST_PASSWORD,
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.json()}")

    tokens = response.json()
    yield {
        "access_token": tokens["access_token"],
        "user_account_pk": str(admin_pk),
        "sangha_sevi_id": sevi_id,
    }


@pytest.fixture(scope="module")
def test_org_pk(write_conn, admin_tokens):
    """
    Get an organization PK that the admin has scope for.
    Falls back to any SAKHA_SANGHA org.

    Claim approval (compose_local_sakha_erp_id) requires the org to have a
    short_code assigned — the real 175-branch seed leaves short_code NULL
    (admin-assignable via UI), so tests that approve a claim against this
    org would otherwise 422. Assign a synthetic one here if missing, scoped
    to this test transaction only (rolled back by conftest's module
    SAVEPOINT) — mirrors test_claim_approval.py::sakha_orgs.
    """
    cur = write_conn.cursor()

    def _ensure_short_code(org_pk: str) -> str:
        cur.execute("SELECT short_code FROM nss.organization WHERE organization_pk = %s", (org_pk,))
        if not cur.fetchone()[0]:
            cur.execute(
                "UPDATE nss.organization SET short_code = 'TREG' WHERE organization_pk = %s",
                (org_pk,),
            )
        return org_pk

    # Get the admin's scoped org
    cur.execute("""
        SELECT asc2.organization_pk
        FROM nss.admin_scope asc2
        JOIN nss.user_role ur ON ur.user_role_pk = asc2.user_role_pk
        WHERE ur.user_account_pk = %s
          AND ur.is_active = TRUE
          AND asc2.is_active = TRUE
          AND asc2.organization_pk IS NOT NULL
        LIMIT 1
    """, (admin_tokens["user_account_pk"],))
    row = cur.fetchone()
    if row:
        return _ensure_short_code(str(row[0]))

    # Check if admin is NSS-WIDE scoped
    cur.execute("""
        SELECT asc2.scope_level
        FROM nss.admin_scope asc2
        JOIN nss.user_role ur ON ur.user_role_pk = asc2.user_role_pk
        WHERE ur.user_account_pk = %s
          AND ur.is_active = TRUE
          AND asc2.is_active = TRUE
          AND asc2.scope_level = 'NSS-WIDE'
        LIMIT 1
    """, (admin_tokens["user_account_pk"],))
    if cur.fetchone():
        # NSS-WIDE — pick any Sakha org
        cur.execute("""
            SELECT o.organization_pk
            FROM nss.organization o
            JOIN nss.master_data md ON md.master_data_pk = o.organization_type_master_data_pk
            WHERE md.value_code = 'SAKHA_SANGHA'
              AND o.is_active = TRUE
            LIMIT 1
        """)
        row = cur.fetchone()
        if row:
            return _ensure_short_code(str(row[0]))

    pytest.skip("No suitable organization found for claim tests.")


@pytest.fixture(scope="module")
def darshaka_type_pk(write_conn):
    """Get the master_data_pk for PROBATIONARY (Darshaka) membership type."""
    cur = write_conn.cursor()
    cur.execute("""
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = 'MEMBERSHIP_TYPE'
          AND md.value_code = 'PROBATIONARY'
          AND md.is_active = TRUE
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No PROBATIONARY membership type found.")
    return str(row[0])


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

    def test_register_darshaka_success(self, client, test_org_pk, darshaka_type_pk, gender_pk, write_conn):
        """Register a new Darshaka member — creates person + PENDING_APPROVAL account + claim."""
        response = client.post("/api/v1/register", json={
            "first_name": TEST_FIRST_NAME,
            "last_name": TEST_LAST_NAME,
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}darshaka@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D1",
        })
        assert response.status_code == 201, f"Registration failed: {response.json()}"
        data = response.json()

        assert "person_pk" in data
        assert "person_id" in data
        assert data["person_id"].startswith("P")
        assert "pending" in data["message"].lower() or "approval" in data["message"].lower()
        # No sangha_sevi_id in response (AUTH-BR-091)
        assert "sangha_sevi_id" not in data

        # Verify DB state via shared test connection
        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT user_account_pk, account_status FROM nss.user_account WHERE person_pk = %s",
                (data["person_pk"],),
            )
            ua_row = cur.fetchone()
            assert ua_row is not None
            assert ua_row[1] == "PENDING_APPROVAL"

            cur.execute(
                "SELECT registration_claim_pk, claim_status FROM nss.registration_claim WHERE person_pk = %s",
                (data["person_pk"],),
            )
            claim_row = cur.fetchone()
            assert claim_row is not None
            assert claim_row[1] == "PENDING"

    def test_register_no_membership(self, client, gender_pk, write_conn):
        """Register without membership claim — person + PENDING_APPROVAL account only."""
        response = client.post("/api/v1/register", json={
            "first_name": TEST_FIRST_NAME,
            "last_name": "NoMembership",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}nomember@test.example",
            "password": TEST_PASSWORD,
            "has_membership": False,
        })
        assert response.status_code == 201
        data = response.json()

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT user_account_pk, account_status FROM nss.user_account WHERE person_pk = %s",
                (data["person_pk"],),
            )
            ua_row = cur.fetchone()
            assert ua_row is not None
            assert ua_row[1] == "PENDING_APPROVAL"

            # No claim should exist
            cur.execute(
                "SELECT registration_claim_pk FROM nss.registration_claim WHERE person_pk = %s",
                (data["person_pk"],),
            )
            assert cur.fetchone() is None

    def test_register_missing_contact_fails(self, client):
        """Registration without mobile or email returns 422."""
        response = client.post("/api/v1/register", json={
            "first_name": "NoContact",
            "password": TEST_PASSWORD,
        })
        assert response.status_code == 422

    def test_register_nondarshaka_requires_local_sakha_number(self, client, test_org_pk, gender_pk, write_conn):
        """Non-Darshaka registration without Local Sakha Number returns 422."""
        # Get a non-Darshaka membership type
        cur = write_conn.cursor()
        cur.execute("""
            SELECT md.master_data_pk
            FROM nss.master_data md
            JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
            WHERE mc.category_code = 'MEMBERSHIP_TYPE'
              AND md.value_code != 'PROBATIONARY'
              AND md.is_active = TRUE
            LIMIT 1
        """)
        row = cur.fetchone()
        if row is None:
            pytest.skip("No non-Darshaka membership type found.")

        response = client.post("/api/v1/register", json={
            "first_name": "NonDarshaka",
            "last_name": "Test",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}nondark@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": str(row[0]),
            "organization_pk": test_org_pk,
            # No claimed_local_sakha_number
        })
        assert response.status_code == 422
        assert "Local Sakha Number" in response.json()["detail"]

    def test_register_darshaka_requires_local_sakha_number(self, client, test_org_pk, darshaka_type_pk, gender_pk):
        """Darshaka registration without Local Sakha Number also returns 422 (AUTH-BR-086 —
        Darshak members get a number in a separate namespace, not no number at all)."""
        response = client.post("/api/v1/register", json={
            "first_name": "DarshakaNoNumber",
            "last_name": "Test",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}darkno@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            # No claimed_local_sakha_number
        })
        assert response.status_code == 422
        assert "Local Sakha Number" in response.json()["detail"]

    def test_register_attending_as_darshak_requires_darshak_local_sakha_number(
        self, client, test_org_pk, darshaka_type_pk, gender_pk, write_conn
    ):
        """is_attending_as_darshak=True without darshak_local_sakha_number returns 422."""
        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT organization_pk FROM nss.organization "
                "WHERE organization_pk != %s AND organization_type_master_data_pk = "
                "(SELECT organization_type_master_data_pk FROM nss.organization WHERE organization_pk = %s) "
                "AND is_active = TRUE LIMIT 1",
                (test_org_pk, test_org_pk),
            )
            row = cur.fetchone()
            if row is None:
                pytest.skip("No second Sakha available for darshak attendance test.")
            other_org_pk = str(row[0])

        response = client.post("/api/v1/register", json={
            "first_name": "DarshakAttend",
            "last_name": "NoNumber",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}darkattend@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D2",
            "is_attending_as_darshak": True,
            "darshak_organization_pk": other_org_pk,
            # No darshak_local_sakha_number
        })
        assert response.status_code == 422
        assert "darshak_local_sakha_number" in response.json()["detail"]


# ── Login blocked for PENDING_APPROVAL ──────────────────────────────────
#
# TestPendingLoginBlocked::test_pending_account_cannot_login moved to
# tests/security/test_registration_security.py


# ── Claim Approval Tests ───────────────────────────────────────────────

class TestClaimApproval:
    """GET/POST /api/v1/admin/claims — list, approve, reject."""

    def test_list_pending_claims(self, client, admin_tokens):
        """Admin can list pending claims."""
        response = client.get(
            "/api/v1/admin/claims?claim_status=PENDING",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "claims" in data
        assert "total" in data

    def test_approve_claim(self, client, admin_tokens, test_org_pk, darshaka_type_pk, gender_pk, write_conn):
        """Admin approves a Darshaka claim → account ACTIVE, sangha_sevi + affiliation +
        Anumati Patra credential all created."""
        # 1. Register a new person with claim
        reg_resp = client.post("/api/v1/register", json={
            "first_name": "ApproveMe",
            "last_name": TEST_LAST_NAME,
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}approveme@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D3",
        })
        assert reg_resp.status_code == 201
        person_pk = reg_resp.json()["person_pk"]

        # Find the claim and user_account via shared test connection
        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT user_account_pk FROM nss.user_account WHERE person_pk = %s",
                (person_pk,),
            )
            ua_pk = str(cur.fetchone()[0])

            cur.execute(
                "SELECT registration_claim_pk FROM nss.registration_claim WHERE person_pk = %s AND claim_status = 'PENDING'",
                (person_pk,),
            )
            claim_pk = str(cur.fetchone()[0])

        # 2. Approve the claim
        approve_resp = client.post(
            f"/api/v1/admin/claims/{claim_pk}/approve",
            headers={
                "Authorization": f"Bearer {admin_tokens['access_token']}",
                "Content-Type": "application/json",
            },
            json={"admin_remarks": "Test approval"},
        )
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.json()}"
        approve_data = approve_resp.json()
        assert "sangha_sevi_id" in approve_data
        assert approve_data["sangha_sevi_id"] is not None

        # 3. Verify: account is now ACTIVE, claim is APPROVED, sangha_sevi exists
        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT account_status FROM nss.user_account WHERE user_account_pk = %s",
                (ua_pk,),
            )
            assert cur.fetchone()[0] == "ACTIVE"

            cur.execute(
                "SELECT claim_status FROM nss.registration_claim WHERE registration_claim_pk = %s",
                (claim_pk,),
            )
            assert cur.fetchone()[0] == "APPROVED"

            cur.execute(
                "SELECT sangha_sevi_pk FROM nss.sangha_sevi WHERE person_pk = %s AND is_active = TRUE",
                (person_pk,),
            )
            ss_row = cur.fetchone()
            assert ss_row is not None
            ss_pk = ss_row[0]

            # The home affiliation got a real, short_code-namespaced local
            # ID (MBR-030C) — not the old buggy fallback that just reused
            # the Sangha Sevi ID when no number was given.
            cur.execute(
                "SELECT local_sakha_erp_id FROM nss.membership_sakha_affiliation "
                "WHERE sangha_sevi_pk = %s AND organization_pk = %s",
                (ss_pk, test_org_pk),
            )
            aff_row = cur.fetchone()
            assert aff_row is not None
            assert aff_row[0] != approve_data["sangha_sevi_id"]
            assert aff_row[0].endswith("D3")

            # A mandatory Anumati Patra credential was issued (MBR-010/019A) —
            # claim_approval.py now calls issue_membership_credential(), which
            # it never did before this test was written.
            cur.execute(
                "SELECT document_number FROM nss.anumati_patra WHERE sangha_sevi_pk = %s",
                (ss_pk,),
            )
            credential_row = cur.fetchone()
            assert credential_row is not None
            assert credential_row[0]

    def test_approve_claim_composes_legacy_credential_number_with_current_fy(
        self, client, admin_tokens, test_org_pk, darshaka_type_pk, gender_pk, write_conn
    ):
        """A registrant-supplied legacy credential number is a plain sequence
        number (e.g. "789") — the registration form doesn't ask for the FY,
        so approve_claim must compose the full "<no>/<fy_start>/<fy_end>"
        Kendra Number itself, using the current financial year."""
        from datetime import date
        from api.helpers import financial_year_bounds

        reg_resp = client.post("/api/v1/register", json={
            "first_name": "LegacyCred",
            "last_name": TEST_LAST_NAME,
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}legacycred@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D9",
            "claimed_credential_document_number": "789",
        })
        assert reg_resp.status_code == 201
        person_pk = reg_resp.json()["person_pk"]

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT registration_claim_pk FROM nss.registration_claim WHERE person_pk = %s AND claim_status = 'PENDING'",
                (person_pk,),
            )
            claim_pk = str(cur.fetchone()[0])

        approve_resp = client.post(
            f"/api/v1/admin/claims/{claim_pk}/approve",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={},
        )
        assert approve_resp.status_code == 200, f"Approve failed: {approve_resp.json()}"

        fy_start, fy_end, _, _ = financial_year_bounds(date.today())
        expected_document_number = f"789/{fy_start}/{fy_end}"

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT document_number FROM nss.anumati_patra WHERE sangha_sevi_pk = "
                "(SELECT sangha_sevi_pk FROM nss.sangha_sevi WHERE person_pk = %s AND is_active = TRUE)",
                (person_pk,),
            )
            row = cur.fetchone()
            assert row is not None
            assert row[0] == expected_document_number, (
                f"Expected the plain number composed with the current FY "
                f"({expected_document_number!r}), got {row[0]!r}"
            )

    def test_reject_claim(self, client, admin_tokens, test_org_pk, darshaka_type_pk, gender_pk, write_conn):
        """Admin rejects a claim → claim REJECTED, account stays PENDING_APPROVAL."""
        # 1. Register
        reg_resp = client.post("/api/v1/register", json={
            "first_name": "RejectMe",
            "last_name": TEST_LAST_NAME,
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}rejectme@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D4",
        })
        assert reg_resp.status_code == 201
        person_pk = reg_resp.json()["person_pk"]

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT user_account_pk FROM nss.user_account WHERE person_pk = %s",
                (person_pk,),
            )
            ua_pk = str(cur.fetchone()[0])

            cur.execute(
                "SELECT registration_claim_pk FROM nss.registration_claim WHERE person_pk = %s AND claim_status = 'PENDING'",
                (person_pk,),
            )
            claim_pk = str(cur.fetchone()[0])

        # 2. Reject
        reject_resp = client.post(
            f"/api/v1/admin/claims/{claim_pk}/reject",
            headers={
                "Authorization": f"Bearer {admin_tokens['access_token']}",
                "Content-Type": "application/json",
            },
            json={"admin_remarks": "Test rejection — incorrect details"},
        )
        assert reject_resp.status_code == 200

        # 3. Verify: claim REJECTED, account still PENDING_APPROVAL
        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT claim_status FROM nss.registration_claim WHERE registration_claim_pk = %s",
                (claim_pk,),
            )
            assert cur.fetchone()[0] == "REJECTED"

            cur.execute(
                "SELECT account_status FROM nss.user_account WHERE user_account_pk = %s",
                (ua_pk,),
            )
            assert cur.fetchone()[0] == "PENDING_APPROVAL"

    def test_reject_without_remarks_fails(self, client, admin_tokens):
        """Rejection without admin_remarks returns 422."""
        # Use a fake UUID — the 422 should come from Pydantic validation before DB
        response = client.post(
            "/api/v1/admin/claims/00000000-0000-0000-0000-000000000000/reject",
            headers={
                "Authorization": f"Bearer {admin_tokens['access_token']}",
                "Content-Type": "application/json",
            },
            json={"admin_remarks": ""},
        )
        assert response.status_code == 422

    def test_approve_already_approved_fails(self, client, admin_tokens, write_conn):
        """Cannot approve a claim that is already APPROVED."""
        # Find any APPROVED claim in the DB (created by test_approve_claim above)
        with write_conn.cursor() as cur:
            cur.execute("""
                SELECT registration_claim_pk
                FROM nss.registration_claim
                WHERE claim_status = 'APPROVED'
                LIMIT 1
            """)
            row = cur.fetchone()
            if row is None:
                pytest.skip("No APPROVED claim found for double-approve test.")
            claim_pk = str(row[0])

        response = client.post(
            f"/api/v1/admin/claims/{claim_pk}/approve",
            headers={
                "Authorization": f"Bearer {admin_tokens['access_token']}",
                "Content-Type": "application/json",
            },
            json={},
        )
        assert response.status_code == 422
        assert "already" in response.json()["detail"].lower()

# ── Registration with address fields tests ───────────────────────────

class TestRegistrationWithAddress:
    """POST /api/v1/register — registration with address fields (city_village_name, geography FKs)."""

    @pytest.fixture(scope="class")
    def address_helpers(self, write_conn):
        """Get geography PKs for address testing."""
        cur = write_conn.cursor()
        # India
        cur.execute(
            "SELECT country_pk FROM nss.country WHERE country_code = 'IN' AND is_active = TRUE LIMIT 1"
        )
        row = cur.fetchone()
        country_pk = str(row[0]) if row else None

        # Odisha
        cur.execute(
            "SELECT state_pk FROM nss.state WHERE LOWER(state_name) LIKE '%odisha%' AND is_active = TRUE LIMIT 1"
        )
        row = cur.fetchone()
        state_pk = str(row[0]) if row else None

        # First district in Odisha
        district_pk = None
        if state_pk:
            cur.execute(
                "SELECT district_pk FROM nss.district WHERE state_pk = %s AND is_active = TRUE LIMIT 1",
                (state_pk,),
            )
            row = cur.fetchone()
            district_pk = str(row[0]) if row else None

        return {
            "country_pk": country_pk,
            "state_pk": state_pk,
            "district_pk": district_pk,
        }

    def test_register_with_city_village_name(
        self, client, test_org_pk, darshaka_type_pk, gender_pk, address_helpers, write_conn
    ):
        """Registration with city_village_name creates/finds the city_village record."""
        cv_name = f"TestVillage_{_RUN_ID}_addr"
        response = client.post("/api/v1/register", json={
            "first_name": "AddrTest",
            "last_name": "Village",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}addr_cv@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D5",
            "country_pk": address_helpers["country_pk"],
            "state_pk": address_helpers["state_pk"],
            "district_pk": address_helpers["district_pk"],
            "city_village_name": cv_name,
        })
        assert response.status_code == 201, f"Registration with address failed: {response.json()}"
        data = response.json()
        assert "person_pk" in data

        # Verify the city_village was created in the DB
        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT city_village_pk, city_village_name FROM nss.city_village WHERE LOWER(city_village_name) = LOWER(%s)",
                (cv_name,),
            )
            row = cur.fetchone()
            assert row is not None, f"city_village '{cv_name}' was not created."

            # Verify person has the city_village_pk set
            cur.execute(
                "SELECT city_village_pk FROM nss.person WHERE person_pk = %s",
                (data["person_pk"],),
            )
            person_row = cur.fetchone()
            assert person_row is not None
            assert str(person_row[0]) == str(row[0])

    def test_register_with_all_address_fields(
        self, client, test_org_pk, darshaka_type_pk, gender_pk, address_helpers
    ):
        """Registration with country, state, district PKs stores them on the person."""
        response = client.post("/api/v1/register", json={
            "first_name": "FullAddr",
            "last_name": "Test",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}full_addr@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D6",
            "country_pk": address_helpers["country_pk"],
            "state_pk": address_helpers["state_pk"],
            "district_pk": address_helpers["district_pk"],
        })
        assert response.status_code == 201
        data = response.json()
        assert "person_pk" in data

    def test_register_without_address_still_works(
        self, client, test_org_pk, darshaka_type_pk, gender_pk
    ):
        """Registration without any address fields works (address is optional)."""
        response = client.post("/api/v1/register", json={
            "first_name": "NoAddr",
            "last_name": "Test",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}no_addr@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D7",
        })
        assert response.status_code == 201

    def test_register_city_village_lookup_existing(
        self, client, test_org_pk, darshaka_type_pk, gender_pk, address_helpers, write_conn
    ):
        """If city_village already exists in the district, it is reused (not duplicated)."""
        cv_name = f"LookupVillage_{_RUN_ID}"
        district_pk = address_helpers["district_pk"]
        if not district_pk:
            pytest.skip("No district available for lookup test.")

        # Pre-create the city_village
        with write_conn.cursor() as cur:
            cv_code = cv_name.upper().replace(" ", "_")[:20]
            cur.execute("""
                INSERT INTO nss.city_village (district_pk, city_village_code, city_village_name, city_village_type)
                VALUES (%s, %s, %s, 'CITY')
                RETURNING city_village_pk
            """, (district_pk, cv_code, cv_name))
            existing_pk = str(cur.fetchone()[0])

        # Register with the same city_village_name — should reuse, not create new
        response = client.post("/api/v1/register", json={
            "first_name": "LookupTest",
            "last_name": "Reuse",
            "date_of_birth": TEST_DOB,
            "gender_master_data_pk": gender_pk,
            "email": f"{TEST_EMAIL_PREFIX}cv_lookup@test.example",
            "password": TEST_PASSWORD,
            "has_membership": True,
            "membership_type_master_data_pk": darshaka_type_pk,
            "organization_pk": test_org_pk,
            "claimed_local_sakha_number": "D8",
            "country_pk": address_helpers["country_pk"],
            "state_pk": address_helpers["state_pk"],
            "district_pk": district_pk,
            "city_village_name": cv_name,
        })
        assert response.status_code == 201
        data = response.json()

        # Verify the person points to the existing city_village, not a new one
        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT city_village_pk FROM nss.person WHERE person_pk = %s",
                (data["person_pk"],),
            )
            person_cv_pk = str(cur.fetchone()[0])
            assert person_cv_pk == existing_pk, (
                f"Expected reuse of city_village {existing_pk}, got new {person_cv_pk}"
            )
