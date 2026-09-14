"""
NSS ERP — Tier 4 Family API tests.

Integration tests for the 4 Family GET endpoints across 3 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Seed data: 1 family (F1 Mishra), 3 members (P1 Ramesh HEAD, P2
Priyanka WIFE, P4 Debasis SON), head history (P1 since 2010).

Endpoint groups tested:
  1. Family List:       /families (with filters)
  2. Family Detail:     /families/{family_group_pk}
  3. Family Members:    /families/{family_group_pk}/members
  4. Head History:      /families/{family_group_pk}/head-history
  5. Security:          security headers, cache control
  6. UI Route:          /family serves HTML
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/family"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ═══════════════════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════════════════


def _get_first_family_pk(client):
    """Return the PK of the first family, or None if no data."""
    data = client.get(f"{BASE}/families").json()
    return data[0]["family_group_pk"] if data else None


# ═══════════════════════════════════════════════════════════════════════════
# 1. FAMILY LIST
# ═══════════════════════════════════════════════════════════════════════════


class TestFamilyList:
    """GET /api/v1/family/families"""

    def test_list_returns_200(self, client):
        """Family list endpoint returns 200."""
        r = client.get(f"{BASE}/families")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_has_required_fields_if_data(self, client):
        """Each family has the expected response fields."""
        required = {
            "family_group_pk", "family_id", "family_name",
            "family_status_master_data_pk", "status_code", "status_name",
            "sakha_organization_pk", "sakha_name", "sakha_code",
            "formed_date", "remarks", "is_active",
        }
        for f in client.get(f"{BASE}/families").json():
            assert required.issubset(f.keys()), (
                f"Missing fields in family {f.get('family_id', '?')}: "
                f"{required - f.keys()}"
            )

    def test_list_all_active(self, client):
        """All returned families have is_active=True."""
        for f in client.get(f"{BASE}/families").json():
            assert f["is_active"] is True

    def test_list_excludes_audit_columns(self, client):
        """Audit columns must never appear in the response."""
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        for f in client.get(f"{BASE}/families").json():
            assert audit_cols.isdisjoint(f.keys()), (
                f"Audit columns leaked in family {f.get('family_id', '?')}: "
                f"{audit_cols & f.keys()}"
            )

    def test_list_returns_seeded_families(self, client):
        """At least 1 seeded family exists (F1 Mishra)."""
        data = client.get(f"{BASE}/families").json()
        assert len(data) >= 1, "Expected at least 1 seeded family"

    def test_seeded_family_has_correct_data(self, client):
        """Seeded family F1 has expected name and status."""
        data = client.get(f"{BASE}/families").json()
        mishra = [f for f in data if f["family_id"] == "F1"]
        if not mishra:
            pytest.skip("F1 Mishra family not seeded")
        f = mishra[0]
        assert f["family_name"] == "Mishra"
        assert f["status_code"] == "ACTIVE"

    def test_filter_by_sakha_code(self, client):
        """Filtering by sakha_code returns 200."""
        r = client.get(f"{BASE}/families", params={"sakha_code": "SKH1"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_status_code(self, client):
        """Filtering by status_code returns 200."""
        r = client.get(f"{BASE}/families", params={"status_code": "ACTIVE"})
        assert r.status_code == 200
        for f in r.json():
            assert f["status_code"] == "ACTIVE"

    def test_filter_nonexistent_sakha_returns_empty(self, client):
        """Filtering by a nonexistent sakha code returns empty list."""
        r = client.get(f"{BASE}/families", params={"sakha_code": "ZZZZZ_FAKE"})
        assert r.status_code == 200
        assert r.json() == []

    def test_multiple_filters(self, client):
        """Combining sakha_code + status_code returns 200."""
        r = client.get(f"{BASE}/families", params={
            "sakha_code": "SKH1",
            "status_code": "ACTIVE",
        })
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    # ── Pagination ──────────────────────────────────────────────────────

    def test_pagination_default_returns_200(self, client):
        """Default limit/offset returns 200."""
        r = client.get(f"{BASE}/families")
        assert r.status_code == 200

    def test_pagination_custom_limit(self, client):
        """limit=1 returns at most 1 family."""
        data = client.get(f"{BASE}/families", params={"limit": 1}).json()
        assert len(data) <= 1

    def test_pagination_limit_zero_returns_422(self, client):
        """limit=0 violates ge=1 constraint — returns 422."""
        r = client.get(f"{BASE}/families", params={"limit": 0})
        assert r.status_code == 422

    def test_pagination_limit_over_max_returns_422(self, client):
        """limit=501 exceeds MAX_LIMIT=500 — returns 422."""
        r = client.get(f"{BASE}/families", params={"limit": 501})
        assert r.status_code == 422

    def test_pagination_negative_offset_returns_422(self, client):
        """offset=-1 violates ge=0 constraint — returns 422."""
        r = client.get(f"{BASE}/families", params={"offset": -1})
        assert r.status_code == 422

    def test_pagination_large_offset_returns_empty(self, client):
        """offset beyond total count returns empty list, not error."""
        r = client.get(f"{BASE}/families", params={"offset": 9999})
        assert r.status_code == 200
        assert r.json() == []

    def test_pagination_max_limit_accepted(self, client):
        """limit=500 (MAX_LIMIT) is accepted."""
        r = client.get(f"{BASE}/families", params={"limit": 500})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 2. FAMILY DETAIL
# ═══════════════════════════════════════════════════════════════════════════


class TestFamilyDetail:
    """GET /api/v1/family/families/{family_group_pk}"""

    def test_detail_fake_pk_returns_404(self, client):
        """Fetching a nonexistent family returns 404."""
        r = client.get(f"{BASE}/families/{FAKE_UUID}")
        assert r.status_code == 404

    def test_detail_bad_uuid_returns_422(self, client):
        """Malformed UUID returns 422."""
        r = client.get(f"{BASE}/families/not-a-uuid")
        assert r.status_code == 422

    def test_detail_valid_pk_returns_200(self, client):
        """Fetching a family by valid PK returns 200 with full fields."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        r = client.get(f"{BASE}/families/{pk}")
        assert r.status_code == 200
        data = r.json()
        assert data["family_group_pk"] == pk

    def test_detail_has_required_fields(self, client):
        """Detail response has all FamilyGroupResponse fields."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        required = {
            "family_group_pk", "family_id", "family_name",
            "family_status_master_data_pk", "status_code", "status_name",
            "sakha_organization_pk", "sakha_name", "sakha_code",
            "formed_date", "remarks", "is_active",
        }
        data = client.get(f"{BASE}/families/{pk}").json()
        assert required.issubset(data.keys()), (
            f"Missing fields: {required - data.keys()}"
        )

    def test_detail_excludes_audit_columns(self, client):
        """Audit columns must never appear in detail response."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        data = client.get(f"{BASE}/families/{pk}").json()
        assert audit_cols.isdisjoint(data.keys()), (
            f"Audit columns leaked: {audit_cols & data.keys()}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. FAMILY MEMBERS
# ═══════════════════════════════════════════════════════════════════════════


class TestFamilyMembers:
    """GET /api/v1/family/families/{family_group_pk}/members"""

    def test_members_fake_pk_returns_404(self, client):
        """Members of a nonexistent family returns 404."""
        r = client.get(f"{BASE}/families/{FAKE_UUID}/members")
        assert r.status_code == 404

    def test_members_bad_uuid_returns_422(self, client):
        """Malformed UUID in members route returns 422."""
        r = client.get(f"{BASE}/families/not-a-uuid/members")
        assert r.status_code == 422

    def test_members_valid_pk_returns_200(self, client):
        """Members for a valid family returns 200."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        r = client.get(f"{BASE}/families/{pk}/members")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_members_has_required_fields_if_data(self, client):
        """Each family member has the expected response fields."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        required = {
            "family_relationship_pk", "family_group_pk",
            "person_pk", "person_id",
            "first_name", "middle_name", "last_name",
            "relationship_type_master_data_pk",
            "relationship_type_code", "relationship_type_name",
            "effective_from", "effective_to",
            "is_current", "remarks",
        }
        data = client.get(f"{BASE}/families/{pk}/members").json()
        for m in data:
            assert required.issubset(m.keys()), (
                f"Missing fields in member: {required - m.keys()}"
            )

    def test_members_all_current(self, client):
        """All returned members have is_current=True (current filter)."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        for m in client.get(f"{BASE}/families/{pk}/members").json():
            assert m["is_current"] is True

    def test_members_seeded_count(self, client):
        """F1 Mishra family has 3 seeded members."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/members").json()
        assert len(data) == 3, f"Expected 3 members, got {len(data)}"

    def test_members_has_head_relationship(self, client):
        """F1 Mishra has a HEAD relationship (Ramesh)."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/members").json()
        heads = [m for m in data if m["relationship_type_code"] == "HEAD"]
        assert len(heads) == 1, "Expected exactly 1 HEAD"

    def test_members_excludes_audit_columns(self, client):
        """Audit columns must not appear in member responses."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        for m in client.get(f"{BASE}/families/{pk}/members").json():
            assert audit_cols.isdisjoint(m.keys()), (
                f"Audit columns leaked: {audit_cols & m.keys()}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 4. HEAD HISTORY
# ═══════════════════════════════════════════════════════════════════════════


class TestFamilyHeadHistory:
    """GET /api/v1/family/families/{family_group_pk}/head-history"""

    def test_head_history_fake_pk_returns_404(self, client):
        """Head history of a nonexistent family returns 404."""
        r = client.get(f"{BASE}/families/{FAKE_UUID}/head-history")
        assert r.status_code == 404

    def test_head_history_bad_uuid_returns_422(self, client):
        """Malformed UUID in head-history route returns 422."""
        r = client.get(f"{BASE}/families/not-a-uuid/head-history")
        assert r.status_code == 422

    def test_head_history_valid_pk_returns_200(self, client):
        """Head history for a valid family returns 200."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        r = client.get(f"{BASE}/families/{pk}/head-history")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_head_history_has_required_fields(self, client):
        """Each head history record has the expected fields."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        required = {
            "family_head_history_pk", "family_group_pk",
            "person_pk", "person_id",
            "first_name", "middle_name", "last_name",
            "effective_from", "effective_to", "remarks",
        }
        data = client.get(f"{BASE}/families/{pk}/head-history").json()
        for h in data:
            assert required.issubset(h.keys()), (
                f"Missing fields in head history: {required - h.keys()}"
            )

    def test_head_history_seeded_count(self, client):
        """F1 Mishra has 1 head history record (P1 Ramesh since 2010)."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/head-history").json()
        assert len(data) >= 1, "Expected at least 1 head history record"

    def test_head_history_current_head_has_no_end_date(self, client):
        """Current head should have effective_to=None."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/head-history").json()
        current = [h for h in data if h["effective_to"] is None]
        assert len(current) >= 1, "Expected at least 1 current head"

    def test_head_history_excludes_audit_columns(self, client):
        """Audit columns must not appear in head history."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        for h in client.get(f"{BASE}/families/{pk}/head-history").json():
            assert audit_cols.isdisjoint(h.keys())


# ═══════════════════════════════════════════════════════════════════════════
# 5. SECURITY — Family endpoints
# ═══════════════════════════════════════════════════════════════════════════


class TestFamilySecurity:
    """Verify security middleware applies to Family endpoints."""

    def test_family_api_has_security_headers(self, client):
        """Family API responses include the four core security headers."""
        r = client.get(f"{BASE}/families")
        assert r.status_code == 200
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"
        assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in r.headers["Permissions-Policy"]

    def test_family_api_has_cache_control_no_store(self, client):
        """Family API responses have Cache-Control: no-store."""
        r = client.get(f"{BASE}/families")
        assert r.headers.get("Cache-Control") == "no-store"

    def test_family_ui_no_cache_control_no_store(self, client):
        """Family UI page does NOT have Cache-Control: no-store."""
        r = client.get("/family")
        assert r.status_code == 200
        assert r.headers.get("Cache-Control") != "no-store"

    def test_404_has_security_headers(self, client):
        """Even 404 responses get security headers."""
        r = client.get(f"{BASE}/families/{FAKE_UUID}")
        assert r.status_code == 404
        assert r.headers["X-Content-Type-Options"] == "nosniff"


# ═══════════════════════════════════════════════════════════════════════════
# 6. UI ROUTE
# ═══════════════════════════════════════════════════════════════════════════


class TestFamilyUI:
    """GET /family — serves the verification UI page."""

    def test_family_page_returns_200(self, client):
        """The /family route serves HTML."""
        r = client.get("/family")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_page_contains_title(self, client):
        """Page title includes 'Family'."""
        html = client.get("/family").text
        assert "Family" in html

    def test_page_contains_branding(self, client):
        """Page contains the correct organization name (not 'ERP')."""
        html = client.get("/family").text
        assert "Nilachala Saraswata Sangha" in html

    def test_page_loads_alpine_js(self, client):
        """Page includes Alpine.js CDN script."""
        html = client.get("/family").text
        assert "alpinejs" in html

    def test_page_loads_daisyui(self, client):
        """Page includes DaisyUI CSS."""
        html = client.get("/family").text
        assert "daisyui" in html

    def test_page_loads_family_js(self, client):
        """Page includes the family.js Alpine component."""
        html = client.get("/family").text
        assert "family.js" in html

    def test_page_has_alpine_data_binding(self, client):
        """Page has x-data binding to familyApp()."""
        html = client.get("/family").text
        assert 'x-data="familyApp()"' in html

    def test_page_has_nav_links(self, client):
        """Page navigation includes links to tier UIs."""
        html = client.get("/family").text
        assert 'href="/"' in html
        assert 'href="/family"' in html
        assert 'href="/membership"' in html

    def test_page_has_nss_logo(self, client):
        """Page references the NSS logo image."""
        html = client.get("/family").text
        assert "nss-logo.png" in html

    def test_page_has_copyright_footer(self, client):
        """Page has a copyright footer."""
        html = client.get("/family").text
        assert "All rights reserved" in html
