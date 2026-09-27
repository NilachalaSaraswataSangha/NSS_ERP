"""
NSS ERP — Claim Approval router coverage (api/routers/claim_approval.py).

This router previously had NO dedicated test file — its GET detail,
PATCH edit, and scope-enforcement paths were entirely untested (only
list/approve/reject happy-paths were covered indirectly via
tests/api/test_registration.py::TestClaimApproval). This file closes
that gap.

Endpoints covered here that were previously untested:
  GET   /api/v1/admin/claims/{pk}            — detail (found, 404, scope-denied)
  PATCH /api/v1/admin/claims/{pk}             — edit (success, non-pending, scope-denied)
  POST  /api/v1/admin/claims/{pk}/approve     — non-Darshaka new-SS path,
                                                 non-Darshaka existing-SS linking,
                                                 Darshak attendance affiliation,
                                                 scope-denied
  POST  /api/v1/admin/claims/{pk}/reject      — scope-denied

Auth-gating (401/unauthenticated) and other pure security assertions for
this router live in tests/security/ — this file focuses on business-logic
and scoping correctness for authenticated, permitted-but-out-of-scope
and in-scope admins.

NOTE: cleanup is automatic via transaction rollback in conftest.py.
"""

import pytest
from uuid import uuid4


pytestmark = pytest.mark.integration


# ── Test constants ──────────────────────────────────────────────────────

TEST_PASSWORD = "TestClaim1x"
SCOPED_PASSWORD = "ScopedClaim1x"
TEST_DOB = "2000-01-15"
_RUN_ID = uuid4().hex[:8]
TEST_EMAIL_PREFIX = f"claimtest_{_RUN_ID}_"


# ── Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def admin_tokens(client, write_conn):
    """NSS-WIDE admin with MEMBERSHIP_APPROVE / ADMIN_USER_MANAGE."""
    cur = write_conn.cursor()
    cur.execute("""
        SELECT ua.user_account_pk, ss.sangha_sevi_id
        FROM nss.user_account ua
        JOIN nss.person p ON p.person_pk = ua.person_pk
        JOIN nss.sangha_sevi ss ON ss.person_pk = ua.person_pk AND ss.is_active = TRUE
        JOIN nss.user_role ur ON ur.user_account_pk = ua.user_account_pk AND ur.is_active = TRUE
        JOIN nss.role_permission rp ON rp.role_master_pk = ur.role_master_pk AND rp.is_active = TRUE
        JOIN nss.permission_master pm ON pm.permission_master_pk = rp.permission_master_pk
        JOIN nss.admin_scope asc2 ON asc2.user_role_pk = ur.user_role_pk
                                   AND asc2.is_active = TRUE
                                   AND asc2.scope_level = 'NSS-WIDE'
        WHERE ua.is_active = TRUE
          AND ua.account_status = 'ACTIVE'
          AND pm.permission_code IN ('MEMBERSHIP_APPROVE', 'ADMIN_USER_MANAGE')
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No NSS-WIDE admin with MEMBERSHIP_APPROVE. Cannot run claim tests.")
    admin_pk, sevi_id = row

    from api.services.auth_service import hash_password
    cur.execute("""
        UPDATE nss.user_account
        SET password_hash = %s, password_changed_at = NOW(),
            password_expires_at = NOW() + INTERVAL '365 days'
        WHERE user_account_pk = %s
    """, (hash_password(TEST_PASSWORD), str(admin_pk)))

    response = client.post("/api/v1/auth/login", json={
        "login_id": sevi_id, "password": TEST_PASSWORD,
    })
    if response.status_code != 200:
        pytest.skip(f"Admin login failed: {response.json()}")

    return {
        "access_token": response.json()["access_token"],
        "user_account_pk": str(admin_pk),
    }


@pytest.fixture(scope="module")
def sakha_orgs(write_conn):
    """
    Two distinct active SAKHA_SANGHA orgs, for scope-boundary tests.

    Approval of a non-Darshaka claim requires the org to have a
    short_code assigned (compose_local_sakha_erp_id enforces this).
    In this dev DB NONE of the seeded SAKHA_SANGHA orgs have a
    short_code set yet (a real, separate operational gap — every
    non-Darshaka claim approval will 422 until an admin sets one via
    the org short-code endpoint). We assign synthetic short codes here,
    scoped to this test transaction only (rolled back by conftest's
    module SAVEPOINT), so this test doesn't depend on that being fixed.
    """
    cur = write_conn.cursor()
    cur.execute("""
        SELECT o.organization_pk, o.short_code
        FROM nss.organization o
        JOIN nss.master_data md ON md.master_data_pk = o.organization_type_master_data_pk
        WHERE md.value_code = 'SAKHA_SANGHA' AND o.is_active = TRUE
        ORDER BY o.created_at
        LIMIT 2
    """)
    rows = cur.fetchall()
    if len(rows) < 2:
        pytest.skip("Need at least two active SAKHA_SANGHA organizations for scope tests.")

    org_a, sc_a = str(rows[0][0]), rows[0][1]
    org_b, sc_b = str(rows[1][0]), rows[1][1]

    if not sc_a:
        cur.execute("UPDATE nss.organization SET short_code = 'TSTA' WHERE organization_pk = %s", (org_a,))
        sc_a = "TSTA"
    if not sc_b:
        cur.execute("UPDATE nss.organization SET short_code = 'TSTB' WHERE organization_pk = %s", (org_b,))
        sc_b = "TSTB"

    return {"org_a": org_a, "org_b": org_b}


@pytest.fixture(scope="module")
def scoped_admin_tokens(write_conn, client, sakha_orgs):
    """
    A SAKHA_ADMIN scoped ONLY to org_b (not org_a) — used to prove
    claim endpoints correctly deny access to out-of-scope organizations.
    """
    from api.services.auth_service import hash_password

    cur = write_conn.cursor()
    cur.execute("""
        SELECT p.person_pk, ss.sangha_sevi_id
        FROM nss.person p
        JOIN nss.sangha_sevi ss ON ss.person_pk = p.person_pk AND ss.is_active = TRUE
        LEFT JOIN nss.user_account ua ON ua.person_pk = p.person_pk AND ua.is_active = TRUE
        WHERE p.is_active = TRUE AND ua.user_account_pk IS NULL
        ORDER BY p.created_at
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No available person for scoped admin test user.")
    person_pk, sevi_id = row

    pw_hash = hash_password(SCOPED_PASSWORD)
    cur.execute("""
        INSERT INTO nss.user_account (
            person_pk, password_hash, account_status,
            force_password_change, password_expires_at
        ) VALUES (%s, %s, 'ACTIVE', FALSE, NOW() + INTERVAL '365 days')
        RETURNING user_account_pk
    """, (str(person_pk), pw_hash))
    ua_pk = cur.fetchone()[0]

    cur.execute(
        "SELECT role_master_pk FROM nss.role_master WHERE role_code = 'NSS_ERP_SAKHA_ADMIN' AND is_active = TRUE"
    )
    role_row = cur.fetchone()
    if role_row is None:
        pytest.skip("NSS_ERP_SAKHA_ADMIN role not found.")

    cur.execute("""
        INSERT INTO nss.user_role (user_account_pk, role_master_pk)
        VALUES (%s, %s) RETURNING user_role_pk
    """, (str(ua_pk), str(role_row[0])))
    ur_pk = cur.fetchone()[0]

    # Scope to org_b ONLY — org_a must be out of scope for this admin.
    cur.execute("""
        INSERT INTO nss.admin_scope (user_role_pk, scope_level, organization_pk)
        VALUES (%s, 'SAKHA', %s)
    """, (str(ur_pk), sakha_orgs["org_b"]))

    response = client.post("/api/v1/auth/login", json={
        "login_id": sevi_id, "password": SCOPED_PASSWORD,
    })
    if response.status_code != 200:
        pytest.skip(f"Scoped admin login failed: {response.json()}")

    return {"access_token": response.json()["access_token"]}


@pytest.fixture(scope="module")
def darshaka_type_pk(write_conn):
    cur = write_conn.cursor()
    cur.execute("""
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = 'MEMBERSHIP_TYPE' AND md.value_code = 'PROBATIONARY'
          AND md.is_active = TRUE
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No PROBATIONARY membership type found.")
    return str(row[0])


@pytest.fixture(scope="module")
def non_darshaka_type_pk(write_conn):
    cur = write_conn.cursor()
    cur.execute("""
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = 'MEMBERSHIP_TYPE' AND md.value_code != 'PROBATIONARY'
          AND md.is_active = TRUE
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No non-Darshaka membership type found.")
    return str(row[0])


@pytest.fixture(scope="module")
def gender_pk(write_conn):
    cur = write_conn.cursor()
    cur.execute("""
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = 'GENDER' AND md.is_active = TRUE
        LIMIT 1
    """)
    row = cur.fetchone()
    if row is None:
        pytest.skip("No GENDER master data found.")
    return str(row[0])


def _register(client, email_suffix, gender_pk, org_pk, membership_type_pk,
              local_sakha_number=None, darshak_org_pk=None, last_name="Test"):
    payload = {
        "first_name": "ClaimApproval",
        "last_name": last_name,
        "date_of_birth": TEST_DOB,
        "gender_master_data_pk": gender_pk,
        "email": f"{TEST_EMAIL_PREFIX}{email_suffix}@test.example",
        "password": TEST_PASSWORD,
        "has_membership": True,
        "membership_type_master_data_pk": membership_type_pk,
        "organization_pk": org_pk,
    }
    if local_sakha_number:
        payload["claimed_local_sakha_number"] = local_sakha_number
    if darshak_org_pk:
        payload["is_attending_as_darshak"] = True
        payload["darshak_organization_pk"] = darshak_org_pk
    resp = client.post("/api/v1/register", json=payload)
    assert resp.status_code == 201, f"Registration failed: {resp.json()}"
    return resp.json()


def _pending_claim_pk(write_conn, person_pk):
    with write_conn.cursor() as cur:
        cur.execute(
            "SELECT registration_claim_pk FROM nss.registration_claim "
            "WHERE person_pk = %s AND claim_status = 'PENDING'",
            (person_pk,),
        )
        return str(cur.fetchone()[0])


# ── GET /api/v1/admin/claims/{pk} — detail ──────────────────────────────

class TestClaimDetail:

    def test_get_claim_detail_success(self, client, admin_tokens, sakha_orgs,
                                       darshaka_type_pk, gender_pk, write_conn):
        person = _register(client, "detailok", gender_pk, sakha_orgs["org_a"], darshaka_type_pk)
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        resp = client.get(
            f"/api/v1/admin/claims/{claim_pk}",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["registration_claim_pk"] == claim_pk
        assert data["person_pk"] == person["person_pk"]
        assert data["claim_status"] == "PENDING"
        assert data["claimed_organization_pk"] == sakha_orgs["org_a"]

    def test_get_claim_detail_not_found(self, client, admin_tokens):
        resp = client.get(
            "/api/v1/admin/claims/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert resp.status_code == 404

    def test_get_claim_detail_scope_denied(self, client, scoped_admin_tokens, sakha_orgs,
                                            darshaka_type_pk, gender_pk, write_conn):
        """Admin scoped to org_b cannot view a claim filed against org_a."""
        person = _register(client, "detailscope", gender_pk, sakha_orgs["org_a"], darshaka_type_pk)
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        resp = client.get(
            f"/api/v1/admin/claims/{claim_pk}",
            headers={"Authorization": f"Bearer {scoped_admin_tokens['access_token']}"},
        )
        assert resp.status_code == 403


# ── PATCH /api/v1/admin/claims/{pk} — edit ──────────────────────────────

class TestUpdateClaim:

    def test_update_claim_success(self, client, admin_tokens, sakha_orgs,
                                   darshaka_type_pk, gender_pk, write_conn):
        person = _register(client, "editok", gender_pk, sakha_orgs["org_a"], darshaka_type_pk)
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        resp = client.patch(
            f"/api/v1/admin/claims/{claim_pk}",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={"first_name": "Edited", "admin_remarks_ignored": "n/a"},
        )
        assert resp.status_code == 200, f"Update failed: {resp.json()}"

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT first_name FROM nss.person WHERE person_pk = %s",
                (person["person_pk"],),
            )
            # helper title-cases input
            assert cur.fetchone()[0] == "Edited"

    def test_update_claim_not_pending_fails(self, client, admin_tokens, sakha_orgs,
                                             darshaka_type_pk, gender_pk, write_conn):
        person = _register(client, "editnotpending", gender_pk, sakha_orgs["org_a"], darshaka_type_pk)
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        # Approve it first so it's no longer PENDING
        approve_resp = client.post(
            f"/api/v1/admin/claims/{claim_pk}/approve",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={},
        )
        assert approve_resp.status_code == 200

        resp = client.patch(
            f"/api/v1/admin/claims/{claim_pk}",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={"first_name": "ShouldFail"},
        )
        assert resp.status_code == 422
        assert "cannot edit" in resp.json()["detail"].lower()

    def test_update_claim_scope_denied(self, client, scoped_admin_tokens, sakha_orgs,
                                        darshaka_type_pk, gender_pk, write_conn):
        person = _register(client, "editscope", gender_pk, sakha_orgs["org_a"], darshaka_type_pk)
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        resp = client.patch(
            f"/api/v1/admin/claims/{claim_pk}",
            headers={"Authorization": f"Bearer {scoped_admin_tokens['access_token']}"},
            json={"first_name": "ShouldBeDenied"},
        )
        assert resp.status_code == 403


# ── POST .../approve — non-Darshaka + Darshak-affiliation paths ────────

class TestApproveNonDarshakaAndDarshak:

    def test_approve_non_darshaka_creates_new_sangha_sevi(
        self, client, admin_tokens, sakha_orgs, non_darshaka_type_pk, gender_pk, write_conn
    ):
        """Non-Darshaka claim with a local sakha number and no prior SS record
        creates a brand-new sangha_sevi row on approval."""
        local_number = f"LN{uuid4().hex[:6]}"
        person = _register(
            client, "nondarshnew", gender_pk, sakha_orgs["org_a"], non_darshaka_type_pk,
            local_sakha_number=local_number,
        )
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        resp = client.post(
            f"/api/v1/admin/claims/{claim_pk}/approve",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={},
        )
        assert resp.status_code == 200, f"Approve failed: {resp.json()}"
        data = resp.json()
        assert data["sangha_sevi_id"] is not None

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT sangha_sevi_pk FROM nss.sangha_sevi WHERE person_pk = %s AND is_active = TRUE",
                (person["person_pk"],),
            )
            ss_row = cur.fetchone()
            assert ss_row is not None

            cur.execute(
                "SELECT membership_sakha_affiliation_pk FROM nss.membership_sakha_affiliation "
                "WHERE sangha_sevi_pk = %s AND organization_pk = %s",
                (str(ss_row[0]), sakha_orgs["org_a"]),
            )
            assert cur.fetchone() is not None

    def test_approve_non_darshaka_links_existing_sangha_sevi(
        self, client, admin_tokens, sakha_orgs, darshaka_type_pk, non_darshaka_type_pk,
        gender_pk, write_conn
    ):
        """If the claimant already has an active sangha_sevi record (e.g. from
        a prior Darshaka approval), a second non-Darshaka claim links to it
        instead of creating a duplicate SS row."""
        # First: approve a Darshaka claim to give this person an active SS record.
        person = _register(client, "existingss", gender_pk, sakha_orgs["org_a"], darshaka_type_pk)
        first_claim_pk = _pending_claim_pk(write_conn, person["person_pk"])
        first_approve = client.post(
            f"/api/v1/admin/claims/{first_claim_pk}/approve",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={},
        )
        assert first_approve.status_code == 200
        original_ss_id = first_approve.json()["sangha_sevi_id"]

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT sangha_sevi_pk FROM nss.sangha_sevi WHERE person_pk = %s AND is_active = TRUE",
                (person["person_pk"],),
            )
            ss_pk_before = str(cur.fetchone()[0])

            # Manually create a second PENDING claim for the SAME person against
            # a non-Darshaka membership type, to exercise the "existing SS" branch
            # of approve_claim without going through a second /register call
            # (registration doesn't allow re-registering the same active user).
            cur.execute(
                "SELECT user_account_pk FROM nss.user_account WHERE person_pk = %s",
                (person["person_pk"],),
            )
            ua_pk = str(cur.fetchone()[0])
            local_number = f"LN{uuid4().hex[:6]}"
            cur.execute(
                """
                INSERT INTO nss.registration_claim (
                    user_account_pk, person_pk, claimed_organization_pk,
                    claimed_membership_type_master_data_pk,
                    claimed_local_sakha_number, claim_status
                ) VALUES (%s, %s, %s, %s, %s, 'PENDING')
                RETURNING registration_claim_pk
                """,
                (ua_pk, person["person_pk"], sakha_orgs["org_a"], non_darshaka_type_pk, local_number),
            )
            second_claim_pk = str(cur.fetchone()[0])

        second_approve = client.post(
            f"/api/v1/admin/claims/{second_claim_pk}/approve",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={},
        )
        assert second_approve.status_code == 200, f"Second approve failed: {second_approve.json()}"
        assert second_approve.json()["sangha_sevi_id"] == original_ss_id, (
            "Approving a second claim for a person who already has an active "
            "sangha_sevi record must link to the existing record, not create a new one."
        )

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM nss.sangha_sevi WHERE person_pk = %s AND is_active = TRUE",
                (person["person_pk"],),
            )
            assert cur.fetchone()[0] == 1, "Must not create a duplicate active sangha_sevi row."

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "CONFIRMED BUG (found while writing this test, not yet fixed — needs an "
            "architecture decision before touching frozen DDL): approve_claim's darshak "
            "attendance INSERT (api/routers/claim_approval.py, 'Darshak attendance "
            "affiliation' block) targets nss.membership_sakha_affiliation with "
            "effective_to left NULL, using 'ON CONFLICT DO NOTHING' with no explicit "
            "conflict target. That silently matches the partial unique index "
            "uq_mem_sakha_aff_active ON (sangha_sevi_pk) WHERE effective_to IS NULL — "
            "'one active affiliation per member at any time', marked FROZEN per "
            "MEM-PENDING-001 / SOL-MEM-005 §27.1 in "
            "database/ddl/05_membership/06_membership_sakha_affiliation.sql. Since the "
            "primary affiliation (created first, same call) already holds that slot for "
            "this sangha_sevi_pk, the darshak-org INSERT always conflicts and is always "
            "silently dropped — the Darshak attendance-affiliation feature has never "
            "actually persisted a second affiliation row for ANY approval, in any "
            "environment, since this code was written. No exception, no log line "
            "(the code only logs on the primary-affiliation conflict, not this one) — "
            "it fails completely silently. Fixing this requires deciding whether the "
            "uniqueness should be (sangha_sevi_pk, organization_pk) instead of "
            "(sangha_sevi_pk) alone, or whether darshak affiliations need a distinct "
            "affiliation_status/type exempted from 'primary active' uniqueness — that's "
            "a frozen-constraint change needing sign-off, not a one-line code fix, so "
            "it is NOT changed here. Flip this to a plain assertion once the DDL "
            "decision is made and the fix lands."
        ),
    )
    def test_approve_darshak_creates_attendance_affiliation(
        self, client, admin_tokens, sakha_orgs, darshaka_type_pk, gender_pk, write_conn
    ):
        """Approving a claim with darshak_organization_pk set must create a
        SECOND membership_sakha_affiliation row at the darshak org, in
        addition to the primary affiliation at the claimed org."""
        person = _register(
            client, "darshakatt", gender_pk, sakha_orgs["org_a"], darshaka_type_pk,
            darshak_org_pk=sakha_orgs["org_b"],
        )
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        resp = client.post(
            f"/api/v1/admin/claims/{claim_pk}/approve",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={},
        )
        assert resp.status_code == 200, f"Approve failed: {resp.json()}"

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT sangha_sevi_pk FROM nss.sangha_sevi WHERE person_pk = %s AND is_active = TRUE",
                (person["person_pk"],),
            )
            ss_pk = str(cur.fetchone()[0])

            cur.execute(
                "SELECT organization_pk FROM nss.membership_sakha_affiliation WHERE sangha_sevi_pk = %s",
                (ss_pk,),
            )
            org_pks = {str(r[0]) for r in cur.fetchall()}
            assert sakha_orgs["org_a"] in org_pks, "Primary affiliation at claimed org missing."
            assert sakha_orgs["org_b"] in org_pks, "Darshak attendance affiliation at darshak org missing."


# ── Scope enforcement on approve/reject ─────────────────────────────────

class TestApproveRejectScopeDenied:

    def test_approve_scope_denied(self, client, scoped_admin_tokens, sakha_orgs,
                                   darshaka_type_pk, gender_pk, write_conn):
        person = _register(client, "approvescope", gender_pk, sakha_orgs["org_a"], darshaka_type_pk)
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        resp = client.post(
            f"/api/v1/admin/claims/{claim_pk}/approve",
            headers={"Authorization": f"Bearer {scoped_admin_tokens['access_token']}"},
            json={},
        )
        assert resp.status_code == 403

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT claim_status FROM nss.registration_claim WHERE registration_claim_pk = %s",
                (claim_pk,),
            )
            assert cur.fetchone()[0] == "PENDING", "Denied approval must not mutate claim status."

    def test_reject_scope_denied(self, client, scoped_admin_tokens, sakha_orgs,
                                  darshaka_type_pk, gender_pk, write_conn):
        person = _register(client, "rejectscope", gender_pk, sakha_orgs["org_a"], darshaka_type_pk)
        claim_pk = _pending_claim_pk(write_conn, person["person_pk"])

        resp = client.post(
            f"/api/v1/admin/claims/{claim_pk}/reject",
            headers={"Authorization": f"Bearer {scoped_admin_tokens['access_token']}"},
            json={"admin_remarks": "Attempted denial"},
        )
        assert resp.status_code == 403

        with write_conn.cursor() as cur:
            cur.execute(
                "SELECT claim_status FROM nss.registration_claim WHERE registration_claim_pk = %s",
                (claim_pk,),
            )
            assert cur.fetchone()[0] == "PENDING", "Denied rejection must not mutate claim status."
