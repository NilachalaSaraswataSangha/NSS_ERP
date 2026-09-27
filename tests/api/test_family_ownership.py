"""
Family authorization — the OWNERSHIP path.

Why this file exists separately from test_family.py
---------------------------------------------------
Every test in test_family.py authenticates through `authed_client`, an admin
token carrying FAMILY_VIEW/FAMILY_MANAGE. Those requests short-circuit on the
permission override in the very first line of each `_require_family_*` helper
and never touch an ownership check. A green test_family.py therefore proves
nothing about the rule the project actually depends on:

    an ordinary member holds NO role and therefore NO permissions, and reaches
    their own family purely through their RELATIONSHIP to it.

This file builds real role-less members — person + sangha_sevi + ACTIVE
user_account with no row in nss.user_role — mints genuine JWTs for them via
POST /api/v1/auth/login, and asserts the four properties that matter:

  1. A role-less member CAN read their own family.            (the regression)
  2. A role-less non-member CANNOT read that family.          (privacy)
  3. The head CAN add a member.                               (ownership write)
  4. A plain member (not head, not admin) CANNOT add a member. (the tightening)

Property 4 is the behaviour change the user asked for: add/remove used to
accept any current member of the family; it now requires head or family admin.

Authorization model under test (api/routers/family.py, section 0):

  | Action                              | Who                                |
  |-------------------------------------|------------------------------------|
  | View one family                     | current member, or FAMILY_VIEW     |
  | Add / remove member, create link    | head or family admin, or FAMILY_MANAGE |
  | Assign admin, transfer headship     | head only, or FAMILY_MANAGE        |
  | Browse ALL families                 | FAMILY_VIEW only                   |
"""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from api.main import app

# Password forced onto every throwaway account in this module. The rows are
# created inside the module savepoint and rolled back, so this never persists.
_MEMBER_PASSWORD = "FamilyOwner1x"

FAKE_PK = "00000000-0000-0000-0000-000000000000"


# ── Infrastructure ─────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def sakha_pk(write_conn):
    """PK of any active Sakha Sangha — families must be registered under one."""
    with write_conn.cursor() as cur:
        cur.execute("""
            SELECT o.organization_pk
            FROM   nss.organization o
            JOIN   nss.master_data md
                   ON md.master_data_pk = o.organization_type_master_data_pk
            JOIN   nss.master_category mc
                   ON mc.master_category_pk = md.master_category_pk
            WHERE  mc.category_code = 'ORGANIZATION_TYPE'
              AND  md.value_code = 'SAKHA_SANGHA'
              AND  o.is_active = TRUE
            LIMIT  1
        """)
        row = cur.fetchone()
    if row is None:
        pytest.skip("No active Sakha Sangha in the database.")
    return str(row[0])


@pytest.fixture(scope="module")
def make_roleless_member(write_conn, _override_deps):
    """
    Factory producing a genuinely role-less member: nss.person +
    nss.sangha_sevi + ACTIVE nss.user_account, and deliberately NO
    nss.user_role row.

    Returns a dict with `person_pk`, `sangha_sevi_id` and `client` — a
    TestClient carrying that member's own Bearer token.

    The token is real, minted through the login endpoint, so it carries
    exactly the permission set the RBAC service computes for someone with no
    role: the empty set. That is the whole point — a hand-built UserContext
    would let a bug in role resolution hide.

    Plain TestClient(app), not a `with` block: the `with` form fires the
    app's lifespan shutdown (close_pool()) on exit and would close the
    connection the whole session shares.
    """
    # Resolve the master data every sangha_sevi row needs, once. The
    # membership STATUS column points at the shared STATUS category (see
    # api.helpers.get_active_status_pk), not at a membership-specific one.
    with write_conn.cursor() as cur:
        cur.execute("""
            SELECT md.value_code, md.master_data_pk
            FROM   nss.master_data md
            JOIN   nss.master_category mc
                   ON mc.master_category_pk = md.master_category_pk
            WHERE  md.is_active = TRUE
              AND ((mc.category_code = 'MEMBERSHIP_TYPE' AND md.value_code = 'REGULAR')
                OR (mc.category_code = 'STATUS'          AND md.value_code = 'ACTIVE'))
        """)
        md = {code: str(pk) for code, pk in cur.fetchall()}
    for key in ("REGULAR", "ACTIVE"):
        if key not in md:
            pytest.skip(f"Master data {key} missing; cannot build a member.")

    from api.services.auth_service import hash_password

    password_hash = hash_password(_MEMBER_PASSWORD)
    created = []

    def _make(org_pk):
        suffix = uuid4().hex[:10].upper()
        with write_conn.cursor() as cur:
            cur.execute("""
                INSERT INTO nss.person (person_id, first_name, last_name, email)
                VALUES (%s, %s, %s, %s)
                RETURNING person_pk
            """, (
                f"TFO{suffix}",
                "TestFamilyOwner",
                suffix,
                f"tfo.{suffix.lower()}@example.test",
            ))
            person_pk = str(cur.fetchone()[0])

            sevi_id = f"TFO{suffix}"
            cur.execute("""
                INSERT INTO nss.sangha_sevi
                    (sangha_sevi_id, person_pk,
                     membership_type_master_data_pk,
                     membership_status_master_data_pk,
                     organization_pk, joining_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                sevi_id, person_pk, md["REGULAR"], md["ACTIVE"],
                org_pk, "2024-04-01",
            ))

            # ACTIVE account, no role. This is exactly what the claim-approval
            # flow produces for an ordinary member.
            cur.execute("""
                INSERT INTO nss.user_account
                    (person_pk, password_hash, account_status,
                     force_password_change, password_changed_at,
                     password_expires_at)
                VALUES (%s, %s, 'ACTIVE', FALSE,
                        NOW(), NOW() + INTERVAL '365 days')
            """, (person_pk, password_hash))

        login = TestClient(app)
        resp = login.post(
            "/api/v1/auth/login",
            json={"login_id": sevi_id, "password": _MEMBER_PASSWORD},
        )
        if resp.status_code != 200:
            pytest.skip(
                f"Role-less member login failed: {resp.status_code} {resp.text}"
            )
        token = resp.json()["access_token"]

        c = TestClient(app)
        c.headers.update({"Authorization": f"Bearer {token}"})

        member = {
            "person_pk": person_pk,
            "sangha_sevi_id": sevi_id,
            "client": c,
        }
        created.append(member)
        return member

    return _make


@pytest.fixture(scope="module")
def family_of_head(make_roleless_member, sakha_pk):
    """
    A family created by a role-less member via the public endpoint.

    Creating it through POST /families rather than raw SQL is deliberate: it
    proves self-service family creation works without FAMILY_MANAGE, and it
    lets the endpoint establish the SELF relationship and head_history rows
    the ownership helpers read.
    """
    head = make_roleless_member(sakha_pk)
    resp = head["client"].post(
        "/api/v1/family/families",
        json={
            "family_name": f"Ownership Test Paribara {uuid4().hex[:6]}",
            "sakha_organization_pk": sakha_pk,
        },
    )
    assert resp.status_code == 201, (
        "A role-less member must be able to create their own family "
        f"(self-service, no FAMILY_MANAGE). Got {resp.status_code}: {resp.text}"
    )
    return {"head": head, "family_pk": resp.json()["family_group_pk"]}


# ── 1. A role-less member can read their own family ────────────────────────

class TestRolelessMemberReadsOwnFamily:
    """
    The regression this whole change exists to prevent: gating the family
    reads on FAMILY_VIEW alone would 403 every ordinary member out of their
    own family tree, because no seeded role is a plain 'member' role and
    nothing in the registration or claim-approval flow grants one.
    """

    def test_member_holds_no_permissions(self, family_of_head):
        """
        Guard on the premise. If this member somehow acquired permissions,
        every other assertion in this file would pass through the override
        and prove nothing.
        """
        resp = family_of_head["head"]["client"].get("/api/v1/auth/me")
        assert resp.status_code == 200, resp.text
        perms = resp.json().get("permissions") or []
        assert perms == [], (
            "The test member must hold zero permissions for the ownership "
            f"path to be under test; got {perms}"
        )

    def test_head_can_read_own_family_detail(self, family_of_head):
        resp = family_of_head["head"]["client"].get(
            f"/api/v1/family/families/{family_of_head['family_pk']}"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["family_group_pk"] == family_of_head["family_pk"]

    def test_head_can_read_own_family_members(self, family_of_head):
        resp = family_of_head["head"]["client"].get(
            f"/api/v1/family/families/{family_of_head['family_pk']}/members"
        )
        assert resp.status_code == 200, resp.text
        pks = [m["person_pk"] for m in resp.json()]
        assert family_of_head["head"]["person_pk"] in pks

    def test_head_can_read_own_family_graph(self, family_of_head):
        """
        The graph endpoint takes viewer_person_pk as a query parameter — it
        derives kinship labels relative to a viewer. That parameter is NOT
        the authorization subject: authorization still comes from the token.
        """
        resp = family_of_head["head"]["client"].get(
            f"/api/v1/family/families/{family_of_head['family_pk']}/graph",
            params={"viewer_person_pk": family_of_head["head"]["person_pk"]},
        )
        assert resp.status_code == 200, resp.text

    def test_head_can_read_own_head_history(self, family_of_head):
        resp = family_of_head["head"]["client"].get(
            f"/api/v1/family/families/{family_of_head['family_pk']}/head-history"
        )
        assert resp.status_code == 200, resp.text
        current = [h for h in resp.json() if h.get("effective_to") is None]
        assert len(current) == 1
        assert current[0]["person_pk"] == family_of_head["head"]["person_pk"]

    def test_member_can_read_own_person_families(self, family_of_head):
        """The dashboard's entry point: 'which family am I in?'"""
        person_pk = family_of_head["head"]["person_pk"]
        resp = family_of_head["head"]["client"].get(
            f"/api/v1/family/person/{person_pk}/families"
        )
        assert resp.status_code == 200, resp.text
        assert any(
            f["family_group_pk"] == family_of_head["family_pk"]
            for f in resp.json()
        )


# ── 2. A role-less non-member cannot read that family ──────────────────────

class TestRolelessOutsiderIsRefused:
    """
    Ownership must cut both ways. The reads had NO ownership check before
    this change — they relied entirely on FAMILY_VIEW. Simply dropping that
    gate so members could get in would have let any authenticated member
    read EVERY family in the organisation.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def outsider(make_roleless_member, sakha_pk):
        return make_roleless_member(sakha_pk)

    def test_outsider_cannot_read_family_detail(self, outsider, family_of_head):
        resp = outsider["client"].get(
            f"/api/v1/family/families/{family_of_head['family_pk']}"
        )
        assert resp.status_code == 403, resp.text

    def test_outsider_cannot_read_family_members(self, outsider, family_of_head):
        resp = outsider["client"].get(
            f"/api/v1/family/families/{family_of_head['family_pk']}/members"
        )
        assert resp.status_code == 403, resp.text

    def test_outsider_cannot_read_another_persons_families(
        self, outsider, family_of_head
    ):
        resp = outsider["client"].get(
            "/api/v1/family/person/"
            f"{family_of_head['head']['person_pk']}/families"
        )
        assert resp.status_code == 403, resp.text

    def test_outsider_cannot_browse_all_families(self, outsider):
        """
        The org-level family browser stays permission-gated (FAMILY_VIEW).
        It is the one family endpoint with no ownership interpretation —
        'all families' is not anybody's own family.
        """
        resp = outsider["client"].get("/api/v1/family/families")
        assert resp.status_code == 403, resp.text

    def test_viewer_person_pk_does_not_bypass_the_gate(
        self, outsider, family_of_head
    ):
        """
        The graph endpoint takes viewer_person_pk as a query parameter. A
        caller-supplied parameter must never become the authorization subject:
        passing a genuine member's PK must not let an outsider in. The gate
        reads the token, not the query string.
        """
        resp = outsider["client"].get(
            f"/api/v1/family/families/{family_of_head['family_pk']}/graph",
            params={"viewer_person_pk": family_of_head["head"]["person_pk"]},
        )
        assert resp.status_code == 403, resp.text

    def test_nonexistent_family_still_404s_for_a_member(self, family_of_head):
        """
        404-before-403 ordering is preserved where require_entity already ran
        first, so a missing family does not leak its absence as a 403.
        """
        resp = family_of_head["head"]["client"].get(
            f"/api/v1/family/families/{FAKE_PK}/members"
        )
        assert resp.status_code == 404, resp.text


# ── 3 & 4. Writes: head/admin yes, plain member no ─────────────────────────

class TestMembershipWritesRequireHeadOrAdmin:
    """
    The tightening. Before this change add_family_member and
    create_family_link accepted ANY current member of the family, via an
    inlined raw-SQL check. The rule is now head or family admin.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def added_member(family_of_head, make_roleless_member, sakha_pk):
        """
        A plain member: added to the family by the head, so genuinely a
        current member — but neither head nor family admin.
        """
        plain = make_roleless_member(sakha_pk)
        resp = family_of_head["head"]["client"].post(
            f"/api/v1/family/families/{family_of_head['family_pk']}/members",
            json={
                "person_pk": plain["person_pk"],
                "relationship_type_code": "SON",
            },
        )
        # Property 3: the head — holding no permission at all — can write.
        assert resp.status_code == 201, (
            "The family head must be able to add a member without "
            f"FAMILY_MANAGE. Got {resp.status_code}: {resp.text}"
        )
        return plain

    def test_added_member_can_now_read_the_family(
        self, added_member, family_of_head
    ):
        """Ownership is live, not cached: membership grants read immediately."""
        resp = added_member["client"].get(
            f"/api/v1/family/families/{family_of_head['family_pk']}/members"
        )
        assert resp.status_code == 200, resp.text

    def test_plain_member_cannot_add_a_member(
        self, added_member, family_of_head, make_roleless_member, sakha_pk
    ):
        """
        THE tightening. A current member who is not head and not a family
        admin must be refused — this is exactly what used to be allowed.
        """
        outsider = make_roleless_member(sakha_pk)
        resp = added_member["client"].post(
            f"/api/v1/family/families/{family_of_head['family_pk']}/members",
            json={
                "person_pk": outsider["person_pk"],
                "relationship_type_code": "SON",
            },
        )
        assert resp.status_code == 403, (
            "A plain family member must NOT be able to add members. "
            f"Got {resp.status_code}: {resp.text}"
        )

    def test_plain_member_cannot_remove_a_member(
        self, added_member, family_of_head
    ):
        resp = added_member["client"].request(
            "DELETE",
            f"/api/v1/family/families/{family_of_head['family_pk']}/members",
            json={"person_pk": family_of_head["head"]["person_pk"]},
        )
        assert resp.status_code == 403, resp.text

    def test_outsider_cannot_add_a_member(
        self, family_of_head, make_roleless_member, sakha_pk
    ):
        stranger = make_roleless_member(sakha_pk)
        resp = stranger["client"].post(
            f"/api/v1/family/families/{family_of_head['family_pk']}/members",
            json={
                "person_pk": stranger["person_pk"],
                "relationship_type_code": "SON",
            },
        )
        assert resp.status_code == 403, resp.text


# ── 5. Head-only actions ───────────────────────────────────────────────────

class TestHeadOnlyActions:
    """
    Appointing family admins and transferring headship are head-only
    (FAM-046, FAM-050). A family admin — who CAN change membership — must
    not be able to appoint further admins or hand over the headship.
    """

    @staticmethod
    @pytest.fixture(scope="class")
    def family_with_admin(family_of_head, make_roleless_member, sakha_pk):
        """A second member, added then appointed family admin by the head."""
        admin = make_roleless_member(sakha_pk)
        fam = family_of_head["family_pk"]
        head_client = family_of_head["head"]["client"]

        add = head_client.post(
            f"/api/v1/family/families/{fam}/members",
            json={
                "person_pk": admin["person_pk"],
                "relationship_type_code": "SON",
            },
        )
        assert add.status_code == 201, add.text

        # Property: the head can appoint an admin with no permissions at all.
        appoint = head_client.post(
            f"/api/v1/family/families/{fam}/admins",
            json={"person_pk": admin["person_pk"]},
        )
        assert appoint.status_code in (200, 201), (
            "The family head must be able to appoint a family admin without "
            f"FAMILY_MANAGE. Got {appoint.status_code}: {appoint.text}"
        )
        return {"admin": admin, "family_pk": fam}

    def test_family_admin_can_add_a_member(
        self, family_with_admin, make_roleless_member, sakha_pk
    ):
        """A family admin holds the membership-changing authority."""
        newcomer = make_roleless_member(sakha_pk)
        resp = family_with_admin["admin"]["client"].post(
            f"/api/v1/family/families/{family_with_admin['family_pk']}/members",
            json={
                "person_pk": newcomer["person_pk"],
                "relationship_type_code": "DAUGHTER",
            },
        )
        assert resp.status_code == 201, (
            "A family admin must be able to add members. "
            f"Got {resp.status_code}: {resp.text}"
        )

    def test_family_admin_cannot_appoint_another_admin(
        self, family_with_admin, family_of_head
    ):
        resp = family_with_admin["admin"]["client"].post(
            f"/api/v1/family/families/{family_with_admin['family_pk']}/admins",
            json={"person_pk": family_of_head["head"]["person_pk"]},
        )
        assert resp.status_code == 403, (
            "Appointing family admins is head-only. "
            f"Got {resp.status_code}: {resp.text}"
        )

    def test_family_admin_cannot_transfer_headship(self, family_with_admin):
        resp = family_with_admin["admin"]["client"].post(
            f"/api/v1/family/families/{family_with_admin['family_pk']}"
            "/transfer-head",
            json={
                "person_pk": family_with_admin["admin"]["person_pk"],
                "remarks": "Attempted self-promotion",
            },
        )
        assert resp.status_code == 403, (
            "Transferring headship is head-only. "
            f"Got {resp.status_code}: {resp.text}"
        )

    def test_family_admin_can_still_read_the_family(self, family_with_admin):
        resp = family_with_admin["admin"]["client"].get(
            f"/api/v1/family/families/{family_with_admin['family_pk']}/admins"
        )
        assert resp.status_code == 200, resp.text
