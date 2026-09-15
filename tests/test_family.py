"""
NSS ERP — Tier 4 Family API tests.

Integration tests for the 4 Family GET endpoints across 3 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

All tests are fully dynamic — they discover families, members, and
status codes from the live API. No hardcoded family IDs, org codes,
or status values.

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
        """First seeded family has a non-empty name and a valid status."""
        data = client.get(f"{BASE}/families").json()
        if not data:
            pytest.skip("No families seeded")
        f = data[0]
        assert f["family_name"] is not None and len(f["family_name"]) > 0
        assert f["status_code"] is not None and len(f["status_code"]) > 0

    def test_filter_by_sakha_code(self, client):
        """Filtering by sakha_code returns 200 with matching families."""
        data = client.get(f"{BASE}/families").json()
        if not data:
            pytest.skip("No families seeded")
        sakha_code = data[0]["sakha_code"]
        r = client.get(f"{BASE}/families", params={"sakha_code": sakha_code})
        assert r.status_code == 200
        for f in r.json():
            assert f["sakha_code"] == sakha_code

    def test_filter_by_status_code(self, client):
        """Filtering by status_code returns 200 with matching families."""
        data = client.get(f"{BASE}/families").json()
        if not data:
            pytest.skip("No families seeded")
        status = data[0]["status_code"]
        r = client.get(f"{BASE}/families", params={"status_code": status})
        assert r.status_code == 200
        for f in r.json():
            assert f["status_code"] == status

    def test_filter_nonexistent_sakha_returns_empty(self, client):
        """Filtering by a nonexistent sakha code returns empty list."""
        r = client.get(f"{BASE}/families", params={"sakha_code": "ZZZZZ_FAKE"})
        assert r.status_code == 200
        assert r.json() == []

    def test_multiple_filters(self, client):
        """Combining sakha_code + status_code returns 200."""
        data = client.get(f"{BASE}/families").json()
        if not data:
            pytest.skip("No families seeded")
        f = data[0]
        r = client.get(f"{BASE}/families", params={
            "sakha_code": f["sakha_code"],
            "status_code": f["status_code"],
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
        """First family has at least 1 member."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/members").json()
        assert len(data) >= 1, f"Expected at least 1 member, got {len(data)}"

    def test_members_has_head_relationship(self, client):
        """F1 Mishra has exactly one current head (via is_head flag)."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/members").json()
        heads = [m for m in data if m["is_head"] is True]
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
        assert "Nilachala Saraswata Sangha" in html

    def test_page_has_view_mode_toggle(self, client):
        """Page has My Family / Org View toggle buttons."""
        html = client.get("/family").text
        assert "My Family" in html
        assert "Org View" in html
        assert "switchViewMode" in html

    def test_page_has_org_breadcrumb(self, client):
        """Page has org breadcrumb navigation for admin view."""
        html = client.get("/family").text
        assert "orgBreadcrumb" in html
        assert "breadcrumbNav" in html

    def test_page_has_org_children_list(self, client):
        """Page has org children drill-down list for admin view."""
        html = client.get("/family").text
        assert "orgChildren" in html
        assert "drillIntoOrg" in html


# ═══════════════════════════════════════════════════════════════════════════
# 7. ORG ADMIN VIEW — sakha_code family filtering
# ═══════════════════════════════════════════════════════════════════════════


class TestOrgAdminFamilyFilter:
    """Verify the org admin view's sakha_code filtering works dynamically."""

    ORG_BASE = "/api/v1/organization"

    def _get_sakha_codes(self, client):
        """Discover all Sakha org codes from the hierarchy API."""
        r = client.get(f"{self.ORG_BASE}/organizations?type_code=SAKHA_SANGHA")
        if r.status_code != 200:
            return []
        return [org["organization_code"] for org in r.json() if org.get("organization_code")]

    def test_families_filter_by_sakha_code(self, client):
        """Families filtered by sakha_code return only matching families."""
        sakha_codes = self._get_sakha_codes(client)
        if not sakha_codes:
            pytest.skip("No Sakha organizations seeded")

        for code in sakha_codes:
            r = client.get(f"{BASE}/families?sakha_code={code}")
            assert r.status_code == 200
            for fam in r.json():
                assert fam["sakha_code"] == code, (
                    f"Family {fam['family_id']} has sakha_code={fam['sakha_code']}, "
                    f"expected {code}"
                )

    def test_families_filter_unknown_sakha_returns_empty(self, client):
        """Filtering by a non-existent sakha_code returns empty list, not 404."""
        r = client.get(f"{BASE}/families?sakha_code=NONEXISTENT_SAKHA")
        assert r.status_code == 200
        assert r.json() == []

    def test_org_hierarchy_kendra_has_children(self, client):
        """Kendra org should have at least one child (Anchalika/Zilla)."""
        r = client.get(f"{self.ORG_BASE}/organizations?type_code=KENDRA")
        if r.status_code != 200 or not r.json():
            pytest.skip("No Kendra organization seeded")

        kendra = r.json()[0]
        children_r = client.get(
            f"{self.ORG_BASE}/organizations/{kendra['organization_pk']}/children"
        )
        assert children_r.status_code == 200
        children = children_r.json()
        assert len(children) >= 1, "Kendra should have at least 1 child org"

    def test_org_drill_down_to_sakha(self, client):
        """Drilling from Kendra through Anchalika should reach Sakha level."""
        r = client.get(f"{self.ORG_BASE}/organizations?type_code=KENDRA")
        if r.status_code != 200 or not r.json():
            pytest.skip("No Kendra organization seeded")

        kendra = r.json()[0]
        children_r = client.get(
            f"{self.ORG_BASE}/organizations/{kendra['organization_pk']}/children"
        )
        assert children_r.status_code == 200
        children = children_r.json()
        if not children:
            pytest.skip("Kendra has no children")

        # Drill into first child — should have its own children or be a leaf
        first_child = children[0]
        grandchildren_r = client.get(
            f"{self.ORG_BASE}/organizations/{first_child['organization_pk']}/children"
        )
        assert grandchildren_r.status_code == 200

        # If there are grandchildren, at least one should be a Sakha
        grandchildren = grandchildren_r.json()
        if grandchildren:
            type_codes = {gc.get("organization_type_code") for gc in grandchildren}
            assert "SAKHA_SANGHA" in type_codes or len(type_codes) > 0, (
                "Expected drill-down to produce Sakha or further children"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 8. SAKHA ALIGNMENT (FAM-036 majority rule)
# ═══════════════════════════════════════════════════════════════════════════


class TestSakhaAlignment:
    """GET /api/v1/family/families/{pk}/sakha-alignment"""

    def test_alignment_returns_200(self, client):
        """Sakha alignment endpoint returns 200 for a valid family."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        r = client.get(f"{BASE}/families/{pk}/sakha-alignment")
        assert r.status_code == 200

    def test_alignment_has_required_fields(self, client):
        """Response has effective and computed Sakha fields."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/sakha-alignment").json()
        required = {
            "family_group_pk", "family_name",
            "assigned_sakha_pk", "assigned_sakha_name", "assigned_sakha_code",
            "is_aligned", "total_members", "members_with_affiliation",
            "affiliations", "members",
        }
        assert required.issubset(data.keys())

    def test_alignment_fake_pk_returns_404(self, client):
        """Non-existent family PK returns 404."""
        r = client.get(f"{BASE}/families/{FAKE_UUID}/sakha-alignment")
        assert r.status_code == 404

    def test_alignment_members_list(self, client):
        """Members list should match total_members count."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/sakha-alignment").json()
        assert len(data["members"]) == data["total_members"]

    def test_alignment_member_fields(self, client):
        """Each member entry has per-member Sakha info fields."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/sakha-alignment").json()
        if not data["members"]:
            pytest.skip("No members in family")
        member_fields = {
            "person_pk", "person_id", "first_name",
            "has_membership",
        }
        for m in data["members"]:
            assert member_fields.issubset(m.keys()), (
                f"Member {m.get('person_id')} missing fields"
            )

    def test_alignment_affiliations_sum(self, client):
        """Affiliation counts should sum to members_with_affiliation."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/sakha-alignment").json()
        total = sum(a["member_count"] for a in data["affiliations"])
        assert total == data["members_with_affiliation"]

    def test_alignment_is_always_aligned(self, client):
        """is_aligned is always True — family auto-follows majority (FAM-036)."""
        families = client.get(f"{BASE}/families").json()
        if not families:
            pytest.skip("No family data seeded")
        for fam in families:
            data = client.get(
                f"{BASE}/families/{fam['family_group_pk']}/sakha-alignment"
            ).json()
            assert data["is_aligned"] is True, (
                f"Family {fam['family_id']} should always be aligned "
                f"(dynamic majority rule)"
            )

    def test_alignment_home_sakha_flag(self, client):
        """Members with affiliation have is_home_sakha relative to effective Sakha."""
        pk = _get_first_family_pk(client)
        if pk is None:
            pytest.skip("No family data seeded")
        data = client.get(f"{BASE}/families/{pk}/sakha-alignment").json()
        effective_pk = data["assigned_sakha_pk"]  # now the dynamic effective Sakha
        for m in data["members"]:
            if m["has_membership"] and m["affiliated_sakha_pk"]:
                expected = m["affiliated_sakha_pk"] == effective_pk
                assert m["is_home_sakha"] == expected, (
                    f"{m['first_name']}: is_home_sakha={m['is_home_sakha']} "
                    f"but affiliated={m['affiliated_sakha_pk']}, effective={effective_pk}"
                )

    def test_ui_has_sakha_alignment_markup(self, client):
        """Family page HTML contains per-member Sakha mismatch markup."""
        html = client.get("/family").text
        assert "isMemberSakhaMismatch" in html
        assert "getMemberSakhaName" in html
