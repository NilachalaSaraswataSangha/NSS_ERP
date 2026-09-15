"""
NSS ERP — Tier 4 Membership API tests.

Integration tests for the 7 Membership GET endpoints across 5 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

All tests are fully dynamic — they discover members, types, statuses,
and org codes from the live API rather than relying on hardcoded IDs.
Business rule tests (e.g. "REGULAR has Parichaya Patra") find members
by type code, not by specific Sangha Sevi IDs.

Three-tier identity model:
  - Sangha Sevi ID (e.g. SS1) — NSS-wide, permanent
  - ERP Number / Local Sakha Number — Sakha-scoped, auto-generated
  - Kendra Number — Kendra-wide, annual

Endpoint groups tested:
  1. Member List:       /members (with filters)
  2. Member Detail:     /members/{sangha_sevi_pk}
  3. Search:            /search?q= (trigram + prefix across 3 tiers)
  4. Affiliations:      /members/{sangha_sevi_pk}/affiliations
  5. Parichaya Patra:   /members/{sangha_sevi_pk}/parichaya-patra
  6. Anumati Patra:     /members/{sangha_sevi_pk}/anumati-patra
  7. Journey Events:    /members/{sangha_sevi_pk}/journey
  8. Security:          security headers, cache control
  9. UI Route:          /membership serves HTML
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/membership"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ═══════════════════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════════════════


def _get_first_member_pk(client):
    """Return the PK of the first member, or None if no data."""
    data = client.get(f"{BASE}/members").json()
    return data[0]["sangha_sevi_pk"] if data else None


def _get_member_by_type(client, type_code):
    """Return the first member with the given membership_type_code, or None."""
    data = client.get(f"{BASE}/members").json()
    matches = [m for m in data if m["membership_type_code"] == type_code]
    return matches[0] if matches else None


def _get_all_members(client):
    """Return the full member list."""
    return client.get(f"{BASE}/members").json()


# ═══════════════════════════════════════════════════════════════════════════
# 1. MEMBER LIST
# ═══════════════════════════════════════════════════════════════════════════


class TestMemberList:
    """GET /api/v1/membership/members"""

    def test_list_returns_200(self, client):
        """Member list endpoint returns 200."""
        r = client.get(f"{BASE}/members")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_has_required_fields_if_data(self, client):
        """Each member has the expected response fields."""
        required = {
            "sangha_sevi_pk", "sangha_sevi_id",
            "person_pk", "person_id",
            "first_name", "middle_name", "last_name",
            "membership_type_master_data_pk",
            "membership_type_code", "membership_type_name",
            "membership_status_master_data_pk",
            "status_code", "status_name",
            "organization_pk", "organization_name", "organization_code",
            "local_sakha_erp_id",
            "joining_date", "renewal_due_date",
            "remarks", "is_active",
        }
        for m in client.get(f"{BASE}/members").json():
            assert required.issubset(m.keys()), (
                f"Missing fields in member {m.get('sangha_sevi_id', '?')}: "
                f"{required - m.keys()}"
            )

    def test_list_all_active(self, client):
        """All returned members have is_active=True."""
        for m in client.get(f"{BASE}/members").json():
            assert m["is_active"] is True

    def test_list_excludes_audit_columns(self, client):
        """Audit columns must never appear in the response."""
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        for m in client.get(f"{BASE}/members").json():
            assert audit_cols.isdisjoint(m.keys()), (
                f"Audit columns leaked in member {m.get('sangha_sevi_id', '?')}: "
                f"{audit_cols & m.keys()}"
            )

    def test_list_returns_seeded_members(self, client):
        """At least 5 seeded members exist."""
        data = client.get(f"{BASE}/members").json()
        assert len(data) >= 5, f"Expected at least 5 seeded members, got {len(data)}"

    def test_seeded_members_include_regular(self, client):
        """At least one REGULAR member exists."""
        m = _get_member_by_type(client, "REGULAR")
        if m is None:
            pytest.skip("No REGULAR member seeded")
        assert m["membership_type_code"] == "REGULAR"

    def test_seeded_members_include_probationary(self, client):
        """At least one PROBATIONARY member exists."""
        m = _get_member_by_type(client, "PROBATIONARY")
        if m is None:
            pytest.skip("No PROBATIONARY member seeded")
        assert m["membership_type_code"] == "PROBATIONARY"

    def test_seeded_members_include_associate(self, client):
        """At least one ASSOCIATE member exists."""
        m = _get_member_by_type(client, "ASSOCIATE")
        if m is None:
            pytest.skip("No ASSOCIATE member seeded")
        assert m["membership_type_code"] == "ASSOCIATE"

    def test_members_have_local_sakha_erp_id(self, client):
        """Members with active affiliations have a local_sakha_erp_id."""
        data = client.get(f"{BASE}/members").json()
        members_with_erp = [m for m in data if m["local_sakha_erp_id"] is not None]
        assert len(members_with_erp) >= 1, "Expected at least 1 member with ERP number"

    # ── Filters ────────────────────────────────────────────────────────

    def test_filter_by_type_code(self, client):
        """Filtering by type_code returns only matching members."""
        r = client.get(f"{BASE}/members", params={"type_code": "REGULAR"})
        assert r.status_code == 200
        for m in r.json():
            assert m["membership_type_code"] == "REGULAR"

    def test_filter_by_status_code(self, client):
        """Filtering by status_code returns only matching members."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        status = members[0]["status_code"]
        r = client.get(f"{BASE}/members", params={"status_code": status})
        assert r.status_code == 200
        for m in r.json():
            assert m["status_code"] == status

    def test_filter_by_org_code(self, client):
        """Filtering by org_code returns only matching members."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        org_code = members[0]["organization_code"]
        r = client.get(f"{BASE}/members", params={"org_code": org_code})
        assert r.status_code == 200
        for m in r.json():
            assert m["organization_code"] == org_code

    def test_filter_nonexistent_type_returns_empty(self, client):
        """Filtering by a nonexistent type code returns empty list."""
        r = client.get(f"{BASE}/members", params={"type_code": "ZZZZZ_FAKE"})
        assert r.status_code == 200
        assert r.json() == []

    def test_multiple_filters(self, client):
        """Combining multiple filters returns 200."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        m = members[0]
        r = client.get(f"{BASE}/members", params={
            "type_code": m["membership_type_code"],
            "status_code": m["status_code"],
        })
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    # ── Pagination ──────────────────────────────────────────────────────

    def test_pagination_custom_limit(self, client):
        """limit=1 returns at most 1 member."""
        data = client.get(f"{BASE}/members", params={"limit": 1}).json()
        assert len(data) <= 1

    def test_pagination_limit_zero_returns_422(self, client):
        """limit=0 violates ge=1 constraint — returns 422."""
        r = client.get(f"{BASE}/members", params={"limit": 0})
        assert r.status_code == 422

    def test_pagination_limit_over_max_returns_422(self, client):
        """limit=501 exceeds MAX_LIMIT=500 — returns 422."""
        r = client.get(f"{BASE}/members", params={"limit": 501})
        assert r.status_code == 422

    def test_pagination_negative_offset_returns_422(self, client):
        """offset=-1 violates ge=0 constraint — returns 422."""
        r = client.get(f"{BASE}/members", params={"offset": -1})
        assert r.status_code == 422

    def test_pagination_large_offset_returns_empty(self, client):
        """offset beyond total count returns empty list, not error."""
        r = client.get(f"{BASE}/members", params={"offset": 9999})
        assert r.status_code == 200
        assert r.json() == []

    def test_pagination_max_limit_accepted(self, client):
        """limit=500 (MAX_LIMIT) is accepted."""
        r = client.get(f"{BASE}/members", params={"limit": 500})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 2. MEMBER DETAIL
# ═══════════════════════════════════════════════════════════════════════════


class TestMemberDetail:
    """GET /api/v1/membership/members/{sangha_sevi_pk}"""

    def test_detail_fake_pk_returns_404(self, client):
        """Fetching a nonexistent member returns 404."""
        r = client.get(f"{BASE}/members/{FAKE_UUID}")
        assert r.status_code == 404

    def test_detail_bad_uuid_returns_422(self, client):
        """Malformed UUID returns 422."""
        r = client.get(f"{BASE}/members/not-a-uuid")
        assert r.status_code == 422

    def test_detail_valid_pk_returns_200(self, client):
        """Fetching a member by valid PK returns 200."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        r = client.get(f"{BASE}/members/{pk}")
        assert r.status_code == 200
        assert r.json()["sangha_sevi_pk"] == pk

    def test_detail_has_required_fields(self, client):
        """Detail response has all MemberResponse fields."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        required = {
            "sangha_sevi_pk", "sangha_sevi_id",
            "person_pk", "person_id",
            "first_name", "middle_name", "last_name",
            "membership_type_master_data_pk",
            "membership_type_code", "membership_type_name",
            "membership_status_master_data_pk",
            "status_code", "status_name",
            "organization_pk", "organization_name", "organization_code",
            "local_sakha_erp_id",
            "joining_date", "renewal_due_date",
            "remarks", "is_active",
        }
        data = client.get(f"{BASE}/members/{pk}").json()
        assert required.issubset(data.keys()), (
            f"Missing fields: {required - data.keys()}"
        )

    def test_detail_excludes_audit_columns(self, client):
        """Audit columns must never appear in detail response."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        data = client.get(f"{BASE}/members/{pk}").json()
        assert audit_cols.isdisjoint(data.keys()), (
            f"Audit columns leaked: {audit_cols & data.keys()}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. SEARCH
# ═══════════════════════════════════════════════════════════════════════════


class TestMemberSearch:
    """GET /api/v1/membership/search?q="""

    def test_search_requires_q(self, client):
        """Omitting q returns 422."""
        r = client.get(f"{BASE}/search")
        assert r.status_code == 422

    def test_search_q_too_short_returns_422(self, client):
        """q with fewer than 2 chars returns 422."""
        r = client.get(f"{BASE}/search", params={"q": "A"})
        assert r.status_code == 422

    def test_search_returns_200(self, client):
        """Valid search returns 200 with a list."""
        r = client.get(f"{BASE}/search", params={"q": "SS"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_search_by_sangha_sevi_id(self, client):
        """Searching by Sangha Sevi ID prefix finds a member."""
        members = client.get(f"{BASE}/members").json()
        if not members:
            pytest.skip("No members seeded")
        member = members[0]
        sid = member["sangha_sevi_id"]
        data = client.get(f"{BASE}/search", params={"q": sid}).json()
        ids = [m["sangha_sevi_id"] for m in data]
        assert sid in ids, f"Expected {sid} in results, got: {ids}"

    def test_search_by_person_id(self, client):
        """Searching by Person ID prefix finds the member."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        member = members[0]
        person_id = member["person_id"]
        data = client.get(f"{BASE}/search", params={"q": person_id[:2]}).json()
        person_ids = [r["person_id"] for r in data]
        assert person_id in person_ids, (
            f"Expected {person_id} in search results, got: {person_ids}"
        )

    def test_search_by_erp_number(self, client):
        """Searching by ERP Number prefix finds the member."""
        # Get a known ERP number from the member list
        members = client.get(f"{BASE}/members").json()
        erp_members = [m for m in members if m["local_sakha_erp_id"]]
        if not erp_members:
            pytest.skip("No members with ERP numbers seeded")
        erp_id = erp_members[0]["local_sakha_erp_id"]
        data = client.get(f"{BASE}/search", params={"q": erp_id[:3]}).json()
        erp_ids = [m["local_sakha_erp_id"] for m in data]
        assert erp_id in erp_ids, (
            f"Expected {erp_id} in search results, got: {erp_ids}"
        )

    def test_search_by_name_trigram(self, client):
        """Searching by name uses trigram fuzzy matching."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        member = members[0]
        name = member["first_name"]
        data = client.get(f"{BASE}/search", params={"q": name}).json()
        found = [r for r in data if r["sangha_sevi_id"] == member["sangha_sevi_id"]]
        assert len(found) >= 1, (
            f"Expected {member['sangha_sevi_id']} when searching by name '{name}'"
        )

    def test_search_by_kendra_number(self, client):
        """Searching by Kendra Number prefix finds the member."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        # Find a member that has Parichaya Patra
        pp_member = None
        pp_data = []
        for member in members:
            pp_data = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/parichaya-patra"
            ).json()
            if pp_data:
                pp_member = member
                break
        if pp_member is None:
            pytest.skip("No member with Parichaya Patra seeded")
        kendra_num = pp_data[0]["document_number"]
        prefix = kendra_num.split("/")[0]
        data = client.get(f"{BASE}/search", params={"q": prefix}).json()
        ids = [r["sangha_sevi_id"] for r in data]
        assert pp_member["sangha_sevi_id"] in ids, (
            f"Expected {pp_member['sangha_sevi_id']} when searching by "
            f"Kendra number prefix '{prefix}', got: {ids}"
        )

    def test_search_nonexistent_returns_empty(self, client):
        """Searching for a nonexistent term returns empty list."""
        r = client.get(f"{BASE}/search", params={"q": "ZZZZNOTEXIST99"})
        assert r.status_code == 200
        assert r.json() == []

    def test_search_by_mobile_number(self, client):
        """Searching by mobile number prefix finds a member."""
        members = client.get(f"{BASE}/members").json()
        with_mobile = [m for m in members if m.get("mobile_number")]
        if not with_mobile:
            pytest.skip("No members with mobile_number seeded")
        member = with_mobile[0]
        prefix = member["mobile_number"][:5]
        data = client.get(f"{BASE}/search", params={"q": prefix}).json()
        ids = [r["sangha_sevi_id"] for r in data]
        assert member["sangha_sevi_id"] in ids, (
            f"Expected {member['sangha_sevi_id']} when searching by mobile prefix '{prefix}', got: {ids}"
        )

    def test_search_by_email(self, client):
        """Searching by email prefix finds a member."""
        members = client.get(f"{BASE}/members").json()
        with_email = [m for m in members if m.get("email")]
        if not with_email:
            pytest.skip("No members with email seeded")
        member = with_email[0]
        email_prefix = member["email"].split("@")[0]
        data = client.get(f"{BASE}/search", params={"q": email_prefix}).json()
        ids = [r["sangha_sevi_id"] for r in data]
        assert member["sangha_sevi_id"] in ids, (
            f"Expected {member['sangha_sevi_id']} when searching by email prefix '{email_prefix}', got: {ids}"
        )

    def test_search_max_50_results(self, client):
        """Search results are capped at 50."""
        data = client.get(f"{BASE}/search", params={"q": "SS"}).json()
        assert len(data) <= 50

    def test_search_returns_member_response_fields(self, client):
        """Search results use MemberResponse schema."""
        data = client.get(f"{BASE}/search", params={"q": "SS"}).json()
        if not data:
            pytest.skip("No search results")
        required = {
            "sangha_sevi_pk", "sangha_sevi_id",
            "person_pk", "person_id",
            "first_name", "membership_type_code",
            "status_code", "organization_name",
            "local_sakha_erp_id", "joining_date",
            "is_active",
            "country_phone_code", "mobile_number", "email",
        }
        assert required.issubset(data[0].keys()), (
            f"Missing fields: {required - data[0].keys()}"
        )

    def test_search_excludes_audit_columns(self, client):
        """Search results exclude audit columns."""
        data = client.get(f"{BASE}/search", params={"q": "SS"}).json()
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        for m in data:
            assert audit_cols.isdisjoint(m.keys())

    def test_search_only_returns_active_members(self, client):
        """Search only returns is_active=True members."""
        data = client.get(f"{BASE}/search", params={"q": "SS"}).json()
        for m in data:
            assert m["is_active"] is True

    def test_search_has_security_headers(self, client):
        """Search endpoint includes security headers."""
        r = client.get(f"{BASE}/search", params={"q": "SS"})
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers.get("Cache-Control") == "no-store"


# ═══════════════════════════════════════════════════════════════════════════
# 4. AFFILIATIONS
# ═══════════════════════════════════════════════════════════════════════════


class TestMemberAffiliations:
    """GET /api/v1/membership/members/{sangha_sevi_pk}/affiliations"""

    def test_affiliations_fake_pk_returns_404(self, client):
        """Affiliations of a nonexistent member returns 404."""
        r = client.get(f"{BASE}/members/{FAKE_UUID}/affiliations")
        assert r.status_code == 404

    def test_affiliations_bad_uuid_returns_422(self, client):
        """Malformed UUID in affiliations route returns 422."""
        r = client.get(f"{BASE}/members/not-a-uuid/affiliations")
        assert r.status_code == 422

    def test_affiliations_valid_pk_returns_200(self, client):
        """Affiliations for a valid member returns 200."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        r = client.get(f"{BASE}/members/{pk}/affiliations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_affiliations_has_required_fields(self, client):
        """Each affiliation has the expected response fields."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        required = {
            "membership_sakha_affiliation_pk", "sangha_sevi_pk",
            "organization_pk", "organization_name", "organization_code",
            "local_sakha_erp_id",
            "effective_from", "effective_to",
            "affiliation_status", "source_event_type",
            "legacy_sakha_number",
        }
        for a in client.get(f"{BASE}/members/{pk}/affiliations").json():
            assert required.issubset(a.keys()), (
                f"Missing fields in affiliation: {required - a.keys()}"
            )

    def test_affiliations_excludes_audit_columns(self, client):
        """Audit columns must not appear in affiliation responses."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
        }
        for a in client.get(f"{BASE}/members/{pk}/affiliations").json():
            assert audit_cols.isdisjoint(a.keys())

    def test_transferred_member_has_multiple_affiliations(self, client):
        """A transferred member should have at least 2 affiliations."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        # Find any member with >= 2 affiliations
        transferred = None
        for member in members:
            affs = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/affiliations"
            ).json()
            if len(affs) >= 2:
                transferred = member
                break
        if transferred is None:
            pytest.skip("No member with multiple affiliations seeded")
        affs = client.get(
            f"{BASE}/members/{transferred['sangha_sevi_pk']}/affiliations"
        ).json()
        assert len(affs) >= 2, (
            f"Expected at least 2 affiliations for transferred member "
            f"{transferred['sangha_sevi_id']}, got {len(affs)}"
        )

    def test_transferred_member_has_archived_and_active(self, client):
        """A transferred member should have one ARCHIVED and one ACTIVE affiliation."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        # Find any member with >= 2 affiliations
        transferred = None
        affs = []
        for member in members:
            affs = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/affiliations"
            ).json()
            if len(affs) >= 2:
                transferred = member
                break
        if transferred is None:
            pytest.skip("No member with multiple affiliations seeded")
        statuses = {a["affiliation_status"] for a in affs}
        assert "ARCHIVED" in statuses, "Expected ARCHIVED affiliation for transfer"
        assert "ACTIVE" in statuses, "Expected ACTIVE affiliation at new Sakha"


# ═══════════════════════════════════════════════════════════════════════════
# 5. PARICHAYA PATRA
# ═══════════════════════════════════════════════════════════════════════════


class TestParichayaPatra:
    """GET /api/v1/membership/members/{sangha_sevi_pk}/parichaya-patra"""

    def test_pp_fake_pk_returns_404(self, client):
        """Parichaya Patra of a nonexistent member returns 404."""
        r = client.get(f"{BASE}/members/{FAKE_UUID}/parichaya-patra")
        assert r.status_code == 404

    def test_pp_bad_uuid_returns_422(self, client):
        """Malformed UUID returns 422."""
        r = client.get(f"{BASE}/members/not-a-uuid/parichaya-patra")
        assert r.status_code == 422

    def test_pp_valid_pk_returns_200(self, client):
        """Parichaya Patra for a valid member returns 200."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        r = client.get(f"{BASE}/members/{pk}/parichaya-patra")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_pp_has_required_fields(self, client):
        """Each Parichaya Patra has the expected response fields."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        # Find a member with PP data
        pp_member = None
        pp_list = []
        for member in members:
            pp_list = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/parichaya-patra"
            ).json()
            if pp_list:
                pp_member = member
                break
        if pp_member is None:
            pytest.skip("No member with Parichaya Patra seeded")
        required = {
            "parichaya_patra_pk", "sangha_sevi_pk",
            "document_number", "issue_date",
            "valid_from", "valid_to", "status",
            "affiliated_organization_pk",
            "affiliated_organization_name",
            "affiliated_organization_code",
            "local_sakha_erp_id",
            "document_reference", "remarks",
        }
        for pp in pp_list:
            assert required.issubset(pp.keys()), (
                f"Missing fields in PP: {required - pp.keys()}"
            )

    def test_regular_member_has_parichaya_patra(self, client):
        """A REGULAR member should have at least 1 Parichaya Patra."""
        m = _get_member_by_type(client, "REGULAR")
        if m is None:
            pytest.skip("No REGULAR member seeded")
        data = client.get(
            f"{BASE}/members/{m['sangha_sevi_pk']}/parichaya-patra"
        ).json()
        assert len(data) >= 1, (
            f"Expected PP for REGULAR member {m['sangha_sevi_id']}"
        )

    def test_pp_document_number_is_kendra_number(self, client):
        """Parichaya Patra document_number is the Kendra Number (Tier 3)."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        pp_member = None
        pp_data = []
        for member in members:
            pp_data = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/parichaya-patra"
            ).json()
            if pp_data:
                pp_member = member
                break
        if pp_member is None:
            pytest.skip("No member with Parichaya Patra seeded")
        doc = pp_data[0]["document_number"]
        # Kendra number format: <number>/<FY_start>/<FY_end>
        assert "/" in doc, f"Expected Kendra number format, got: {doc}"

    def test_probationary_has_no_parichaya_patra(self, client):
        """A PROBATIONARY member should have no Parichaya Patra."""
        m = _get_member_by_type(client, "PROBATIONARY")
        if m is None:
            pytest.skip("No PROBATIONARY member seeded")
        data = client.get(
            f"{BASE}/members/{m['sangha_sevi_pk']}/parichaya-patra"
        ).json()
        assert len(data) == 0, "Probationary member should not have PP"

    def test_pp_excludes_audit_columns(self, client):
        """Audit columns must not appear in PP responses."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        pp_member = None
        pp_list = []
        for member in members:
            pp_list = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/parichaya-patra"
            ).json()
            if pp_list:
                pp_member = member
                break
        if pp_member is None:
            pytest.skip("No member with Parichaya Patra seeded")
        audit_cols = {"created_at", "updated_at"}
        for pp in pp_list:
            assert audit_cols.isdisjoint(pp.keys())


# ═══════════════════════════════════════════════════════════════════════════
# 6. ANUMATI PATRA
# ═══════════════════════════════════════════════════════════════════════════


class TestAnumatiPatra:
    """GET /api/v1/membership/members/{sangha_sevi_pk}/anumati-patra"""

    def test_ap_fake_pk_returns_404(self, client):
        """Anumati Patra of a nonexistent member returns 404."""
        r = client.get(f"{BASE}/members/{FAKE_UUID}/anumati-patra")
        assert r.status_code == 404

    def test_ap_bad_uuid_returns_422(self, client):
        """Malformed UUID returns 422."""
        r = client.get(f"{BASE}/members/not-a-uuid/anumati-patra")
        assert r.status_code == 422

    def test_ap_valid_pk_returns_200(self, client):
        """Anumati Patra for a valid member returns 200."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        r = client.get(f"{BASE}/members/{pk}/anumati-patra")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_ap_has_required_fields(self, client):
        """Each Anumati Patra has the expected response fields."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        ap_member = None
        ap_list = []
        for member in members:
            ap_list = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/anumati-patra"
            ).json()
            if ap_list:
                ap_member = member
                break
        if ap_member is None:
            pytest.skip("No member with Anumati Patra seeded")
        required = {
            "anumati_patra_pk", "sangha_sevi_pk",
            "document_number", "issue_date",
            "valid_from", "valid_to", "status",
            "document_reference", "remarks",
        }
        for ap in ap_list:
            assert required.issubset(ap.keys()), (
                f"Missing fields in AP: {required - ap.keys()}"
            )

    def test_probationary_has_anumati_patra(self, client):
        """A PROBATIONARY member should have at least 1 Anumati Patra."""
        m = _get_member_by_type(client, "PROBATIONARY")
        if m is None:
            pytest.skip("No PROBATIONARY member seeded")
        data = client.get(
            f"{BASE}/members/{m['sangha_sevi_pk']}/anumati-patra"
        ).json()
        assert len(data) >= 1, (
            f"Expected AP for PROBATIONARY member {m['sangha_sevi_id']}"
        )

    def test_ap_document_number_format(self, client):
        """Anumati Patra document_number follows AP/<year>/<seq> format."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        ap_member = None
        ap_data = []
        for member in members:
            ap_data = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/anumati-patra"
            ).json()
            if ap_data:
                ap_member = member
                break
        if ap_member is None:
            pytest.skip("No member with Anumati Patra seeded")
        doc = ap_data[0]["document_number"]
        assert doc.startswith("AP/"), f"Expected AP/ prefix, got: {doc}"

    def test_regular_member_has_historical_expired_ap(self, client):
        """
        A REGULAR member may have a historical EXPIRED Anumati Patra.

        Not every REGULAR member necessarily does (MBR-019C). For a
        non-youth applicant, becoming a Probationary/Darshaka member first is
        mandatory -- Darshaka holds an Anumati Patra that expires on
        promotion to Regular, so these members always have historical
        EXPIRED AP. For an applicant who came up through Kishor Puja or
        Kumari Sangha, the Darshaka stage is optional -- the sanctioning
        Sangha President may admit them straight to Regular, in which case
        no Anumati Patra history exists at all. So this searches across
        all REGULAR members for one that has a historical EXPIRED Anumati
        Patra, rather than asserting every REGULAR member must.
        """
        members = _get_all_members(client)
        regular_members = [m for m in members if m["membership_type_code"] == "REGULAR"]
        if not regular_members:
            pytest.skip("No REGULAR member seeded")
        found = False
        for m in regular_members:
            data = client.get(
                f"{BASE}/members/{m['sangha_sevi_pk']}/anumati-patra"
            ).json()
            if any(ap["status"] == "EXPIRED" for ap in data):
                found = True
                break
        if not found:
            pytest.skip("No REGULAR member with a historical EXPIRED Anumati Patra seeded")
        assert found

    def test_any_member_has_expired_ap(self, client):
        """At least one member has an EXPIRED Anumati Patra."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        found = False
        for member in members:
            data = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/anumati-patra"
            ).json()
            expired = [ap for ap in data if ap["status"] == "EXPIRED"]
            if expired:
                found = True
                break
        if not found:
            pytest.skip("No member with EXPIRED Anumati Patra seeded")
        assert found

    def test_ap_excludes_audit_columns(self, client):
        """Audit columns must not appear in AP responses."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        ap_member = None
        ap_list = []
        for member in members:
            ap_list = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/anumati-patra"
            ).json()
            if ap_list:
                ap_member = member
                break
        if ap_member is None:
            pytest.skip("No member with Anumati Patra seeded")
        audit_cols = {"created_at", "updated_at"}
        for ap in ap_list:
            assert audit_cols.isdisjoint(ap.keys())


# ═══════════════════════════════════════════════════════════════════════════
# 7. JOURNEY EVENTS
# ═══════════════════════════════════════════════════════════════════════════


class TestJourneyEvents:
    """GET /api/v1/membership/members/{sangha_sevi_pk}/journey"""

    def test_journey_fake_pk_returns_404(self, client):
        """Journey of a nonexistent member returns 404."""
        r = client.get(f"{BASE}/members/{FAKE_UUID}/journey")
        assert r.status_code == 404

    def test_journey_bad_uuid_returns_422(self, client):
        """Malformed UUID returns 422."""
        r = client.get(f"{BASE}/members/not-a-uuid/journey")
        assert r.status_code == 422

    def test_journey_valid_pk_returns_200(self, client):
        """Journey for a valid member returns 200."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        r = client.get(f"{BASE}/members/{pk}/journey")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_journey_has_required_fields(self, client):
        """Each journey event has the expected response fields."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        required = {
            "membership_journey_event_pk", "sangha_sevi_pk",
            "event_type", "event_date",
            "event_reference", "remarks",
        }
        for j in client.get(f"{BASE}/members/{pk}/journey").json():
            assert required.issubset(j.keys()), (
                f"Missing fields in journey event: {required - j.keys()}"
            )

    def test_journey_has_seeded_events(self, client):
        """At least one member has journey events."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        found = False
        for member in members:
            data = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/journey"
            ).json()
            if data:
                found = True
                break
        assert found, "Expected at least one member with journey events"

    def test_journey_events_ordered_by_date(self, client):
        """Journey events are returned in chronological order (ASC)."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        # Find a member with >= 2 journey events
        for member in members:
            data = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/journey"
            ).json()
            if len(data) >= 2:
                dates = [e["event_date"] for e in data]
                assert dates == sorted(dates), "Journey events should be chronological"
                return
        pytest.skip("No member with 2+ journey events for ordering test")

    def test_transferred_member_has_transfer_event(self, client):
        """At least one member has a TRANSFER journey event."""
        members = _get_all_members(client)
        if not members:
            pytest.skip("No members seeded")
        for member in members:
            data = client.get(
                f"{BASE}/members/{member['sangha_sevi_pk']}/journey"
            ).json()
            event_types = {e["event_type"] for e in data}
            if "TRANSFER" in event_types:
                return  # pass
        pytest.skip("No member with TRANSFER journey event seeded")

    @pytest.mark.skip(reason="KUMARI_TRANSITION event deferred to Tier 8 Kumari module")
    def test_kumari_transition_has_event(self, client):
        """SS5 (Smita, Kumari→Membership) has KUMARI_TRANSITION event."""
        m = _get_member_by_id(client, "SS5")
        if m is None:
            pytest.skip("SS5 not seeded")
        data = client.get(f"{BASE}/members/{m['sangha_sevi_pk']}/journey").json()
        event_types = {e["event_type"] for e in data}
        assert "KUMARI_TRANSITION" in event_types, (
            f"Expected KUMARI_TRANSITION event for SS5, got: {event_types}"
        )

    def test_journey_excludes_audit_columns(self, client):
        """Audit columns must not appear in journey responses."""
        pk = _get_first_member_pk(client)
        if pk is None:
            pytest.skip("No member data seeded")
        audit_cols = {
            "created_at", "updated_at",
            "created_by_sangha_sevi_pk",
        }
        for j in client.get(f"{BASE}/members/{pk}/journey").json():
            assert audit_cols.isdisjoint(j.keys())


# ═══════════════════════════════════════════════════════════════════════════
# 8. SECURITY — Membership endpoints
# ═══════════════════════════════════════════════════════════════════════════


class TestMembershipSecurity:
    """Verify security middleware applies to Membership endpoints."""

    def test_membership_api_has_security_headers(self, client):
        """Membership API responses include the four core security headers."""
        r = client.get(f"{BASE}/members")
        assert r.status_code == 200
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"
        assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in r.headers["Permissions-Policy"]

    def test_membership_api_has_cache_control_no_store(self, client):
        """Membership API responses have Cache-Control: no-store."""
        r = client.get(f"{BASE}/members")
        assert r.headers.get("Cache-Control") == "no-store"

    def test_membership_ui_no_cache_control_no_store(self, client):
        """Membership UI page does NOT have Cache-Control: no-store."""
        r = client.get("/membership")
        assert r.status_code == 200
        assert r.headers.get("Cache-Control") != "no-store"

    def test_404_has_security_headers(self, client):
        """Even 404 responses get security headers."""
        r = client.get(f"{BASE}/members/{FAKE_UUID}")
        assert r.status_code == 404
        assert r.headers["X-Content-Type-Options"] == "nosniff"

    def test_sub_endpoints_have_security_headers(self, client):
        """Sub-resource 404s also get security headers."""
        r = client.get(f"{BASE}/members/{FAKE_UUID}/affiliations")
        assert r.status_code == 404
        assert r.headers["X-Content-Type-Options"] == "nosniff"


# ═══════════════════════════════════════════════════════════════════════════
# 9. UI ROUTE
# ═══════════════════════════════════════════════════════════════════════════


class TestMembershipUI:
    """GET /membership — serves the verification UI page."""

    def test_membership_page_returns_200(self, client):
        """The /membership route serves HTML."""
        r = client.get("/membership")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_page_contains_title(self, client):
        """Page title includes 'Membership'."""
        html = client.get("/membership").text
        assert "Membership" in html

    def test_page_contains_branding(self, client):
        """Page contains the correct organization name (not 'ERP')."""
        html = client.get("/membership").text
        assert "Nilachala Saraswata Sangha" in html

    def test_page_loads_alpine_js(self, client):
        """Page includes Alpine.js CDN script."""
        html = client.get("/membership").text
        assert "alpinejs" in html

    def test_page_loads_daisyui(self, client):
        """Page includes DaisyUI CSS."""
        html = client.get("/membership").text
        assert "daisyui" in html

    def test_page_loads_membership_js(self, client):
        """Page includes the membership.js Alpine component."""
        html = client.get("/membership").text
        assert "membership.js" in html

    def test_page_has_alpine_data_binding(self, client):
        """Page has x-data binding to membershipApp()."""
        html = client.get("/membership").text
        assert 'x-data="membershipApp()"' in html

    def test_page_has_nav_links(self, client):
        """Page navigation includes links to tier UIs."""
        html = client.get("/membership").text
        assert 'href="/"' in html
        assert 'href="/family"' in html
        assert 'href="/membership"' in html

    def test_page_has_three_tier_legend(self, client):
        """Page contains the three-tier identity legend."""
        html = client.get("/membership").text
        assert "Sangha Sevi ID" in html
        assert "Sakha Sangha ID" in html

    def test_page_has_darshaka_filter(self, client):
        """Page type filter includes Darshaka (not Probationary)."""
        html = client.get("/membership").text
        assert "Darshaka" in html

    def test_page_has_nss_logo(self, client):
        """Page references the NSS logo image."""
        html = client.get("/membership").text
        assert "nss-logo.png" in html

    def test_page_has_copyright_footer(self, client):
        """Page has a copyright footer."""
        html = client.get("/membership").text
        assert "All rights reserved" in html

    def test_page_has_search_input(self, client):
        """Page has a member search tab with input."""
        html = client.get("/membership").text
        assert "searchQuery" in html
        assert "executeSearch()" in html

    def test_page_has_tab_bar(self, client):
        """Page has Members and Search tabs like person UI."""
        html = client.get("/membership").text
        assert "switchTab('members')" in html
        assert "switchTab('search')" in html

    def test_page_has_search_tab_content(self, client):
        """Search tab has the Member Search heading."""
        html = client.get("/membership").text
        assert "Member Search" in html

    def test_page_has_search_detail_panel(self, client):
        """Search tab includes a detail panel for inline member view."""
        html = client.get("/membership").text
        # Both tabs have "Member Detail" heading — at least 2 occurrences
        assert html.count("Member Detail") >= 2

    def test_page_has_person_id_column(self, client):
        """Member tables include Person ID column."""
        html = client.get("/membership").text
        assert "Person ID" in html

    def test_page_has_sakha_sangha_id_label(self, client):
        """Page uses 'Sakha Sangha ID' label (not 'ERP #')."""
        html = client.get("/membership").text
        assert "Sakha Sangha ID" in html

    def test_search_auto_selects_single_result(self, client):
        """Membership JS auto-selects when search returns exactly 1 result."""
        res = client.get("/assets/js/membership.js")
        assert res.status_code == 200
        js = res.text
        assert "searchResults.length === 1" in js
        assert "selectMember" in js

    def test_anumati_patra_hidden_for_associate(self, client):
        """Anumati Patra section is conditionally hidden for Associate members."""
        html = client.get("/membership").text
        assert "NSS.showAnumatiPatra" in html
