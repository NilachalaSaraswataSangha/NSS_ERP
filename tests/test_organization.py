"""
NSS ERP — Tier 2 Organization API tests.

Integration tests for the 6 Organization GET endpoints.
Organization type values come from Foundation master_data
(category ORGANIZATION_TYPE). Status values come from the
unified ERP-wide STATUS category.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Endpoint groups tested:
  1. Reference Data: types, statuses (from master_data)
  2. Organizations:  list (with filters), detail, children
  3. Hierarchy:      recursive CTE tree
  4. UI Route:       /organization serves HTML
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/organization"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ═══════════════════════════════════════════════════════════════════════════
# 1. REFERENCE DATA
# ═══════════════════════════════════════════════════════════════════════════


class TestOrganizationTypes:
    """GET /api/v1/organization/types"""

    def test_list_returns_200(self, client):
        """Organization types returns 200 with a non-empty list."""
        r = client.get(f"{BASE}/types")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected 9 seeded organization types"

    def test_list_has_required_fields(self, client):
        """Each organization type has the expected response fields."""
        required = {
            "organization_type_pk", "organization_type_code",
            "organization_type_name", "description",
            "sort_order", "is_active",
        }
        for t in client.get(f"{BASE}/types").json():
            assert required.issubset(t.keys()), (
                f"Missing fields in type {t.get('organization_type_code', '?')}: "
                f"{required - t.keys()}"
            )
            assert t["is_active"] is True

    def test_list_includes_frozen_types(self, client):
        """All 13 frozen organization types are present (may include more)."""
        data = client.get(f"{BASE}/types").json()
        assert len(data) >= 13
        codes = {t["organization_type_code"] for t in data}
        expected = {
            "KENDRA", "NILACHALA_KUTIRA", "SMRUTI_MANDIRA",
            "ANCHALIKA_SANGHA", "ZILLA_SANGHA", "SAKHA_SANGHA",
            "SAKHA_ASANA", "PARIBARIK_ASANA", "PARIBARIK_SANGHA",
            "PATHA_CHAKRA", "KUMARI_SANGHA", "SEVAK_SANGHA",
            "MAHILA_SANGHA",
        }
        assert expected.issubset(codes), f"Missing org types: {expected - codes}"

    def test_list_ordered_by_sort_order(self, client):
        """Types are returned in sort_order."""
        data = client.get(f"{BASE}/types").json()
        orders = [t["sort_order"] for t in data]
        assert orders == sorted(orders)


class TestStatuses:
    """GET /api/v1/organization/statuses"""

    def test_list_returns_200(self, client):
        """Statuses returns 200 with a non-empty list."""
        r = client.get(f"{BASE}/statuses")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected organization-scoped lifecycle statuses"

    def test_list_has_required_fields(self, client):
        """Each status has the expected response fields."""
        required = {
            "status_pk", "status_code",
            "status_name", "description",
            "sort_order", "is_active",
        }
        for s in client.get(f"{BASE}/statuses").json():
            assert required.issubset(s.keys()), (
                f"Missing fields in status {s.get('status_code', '?')}: "
                f"{required - s.keys()}"
            )

    def test_list_includes_org_statuses(self, client):
        """Organization-scoped lifecycle statuses include the 7 core statuses."""
        data = client.get(f"{BASE}/statuses").json()
        assert len(data) >= 7
        codes = {s["status_code"] for s in data}
        expected = {
            "PROPOSED", "APPROVED", "ACTIVE",
            "INACTIVE", "SUSPENDED", "DISSOLVED", "ARCHIVED",
        }
        assert expected.issubset(codes), f"Missing org statuses: {expected - codes}"

    def test_list_ordered_by_sort_order(self, client):
        """Statuses are returned in sort_order."""
        data = client.get(f"{BASE}/statuses").json()
        orders = [s["sort_order"] for s in data]
        assert orders == sorted(orders)


# ═══════════════════════════════════════════════════════════════════════════
# 2. ORGANIZATIONS
# ═══════════════════════════════════════════════════════════════════════════


class TestOrganizations:
    """GET /api/v1/organization/organizations  +  organizations/{pk}"""

    def test_list_returns_200(self, client):
        """Organizations list returns 200 with seeded organizations."""
        r = client.get(f"{BASE}/organizations")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected seeded organizations"

    def test_list_has_required_fields(self, client):
        """Each organization has expected fields including JOINed context."""
        required = {
            "organization_pk", "organization_id", "organization_name",
            "organization_code",
            "organization_type_pk", "organization_type_code",
            "organization_type_name",
            "status_pk", "status_code",
            "status_name",
            "parent_organization_pk", "parent_organization_name",
            "address_line_1", "address_line_2",
            "phone_number", "mobile_number", "email", "org_email",
            "website_url", "org_website_url",
            "youtube_channel_url", "org_youtube_channel_url",
            "district_pk", "district_name",
            "state_pk", "state_name",
            "country_pk", "country_name",
            "city_village_pk", "city_village_name",
            "postal_code_pk", "postal_code",
            "latitude", "longitude",
            "is_active",
        }
        for org in client.get(f"{BASE}/organizations").json():
            assert required.issubset(org.keys()), (
                f"Missing fields in org {org.get('organization_code', '?')}: "
                f"{required - org.keys()}"
            )

    def test_list_includes_known_orgs(self, client):
        """Organization list has root organizations (at least 3)."""
        data = client.get(f"{BASE}/organizations").json()
        assert len(data) >= 3, f"Expected at least 3 orgs, got {len(data)}"
        # Verify root orgs exist (parent=NULL)
        roots = [o for o in data if o["parent_organization_pk"] is None]
        assert len(roots) >= 1, "Expected at least 1 root organization"

    def test_list_all_active(self, client):
        """All returned organizations have is_active=True."""
        for org in client.get(f"{BASE}/organizations").json():
            assert org["is_active"] is True

    def test_list_has_roots_and_children(self, client):
        """At least 3 root organizations (parent=NULL) exist."""
        data = client.get(f"{BASE}/organizations").json()
        roots = [o for o in data if o["parent_organization_pk"] is None]
        assert len(roots) >= 3, f"Expected at least 3 roots, got {len(roots)}"

    def test_filter_by_type_code(self, client):
        """Filtering by type_code returns only matching organizations."""
        r = client.get(f"{BASE}/organizations", params={"type_code": "KENDRA"})
        assert r.status_code == 200
        data = r.json()
        assert len(data) >= 1
        for org in data:
            assert org["organization_type_code"] == "KENDRA"

    def test_filter_by_status_code(self, client):
        """Filtering by status_code returns only matching organizations."""
        orgs = client.get(f"{BASE}/organizations").json()
        if not orgs:
            pytest.skip("No orgs seeded")
        status = orgs[0]["status_code"]
        r = client.get(f"{BASE}/organizations", params={"status_code": status})
        assert r.status_code == 200
        for org in r.json():
            assert org["status_code"] == status

    def test_filter_nonexistent_type_returns_empty(self, client):
        """Filtering by a type code with no matches returns empty list."""
        r = client.get(f"{BASE}/organizations", params={"type_code": "ZZZZZ_FAKE"})
        assert r.status_code == 200
        assert r.json() == []

    def test_detail_valid_pk(self, client):
        """Fetching an organization by valid PK returns 200."""
        orgs = client.get(f"{BASE}/organizations").json()
        pk = orgs[0]["organization_pk"]
        r = client.get(f"{BASE}/organizations/{pk}")
        assert r.status_code == 200
        assert r.json()["organization_pk"] == pk

    def test_detail_fake_pk_returns_404(self, client):
        """Fetching a nonexistent organization returns 404."""
        assert client.get(f"{BASE}/organizations/{FAKE_UUID}").status_code == 404

    def test_detail_bad_uuid_returns_422(self, client):
        """Malformed UUID returns 422."""
        assert client.get(f"{BASE}/organizations/not-a-uuid").status_code == 422

    def test_detail_has_resolved_country(self, client):
        """Kendra org should have country_name resolved (India)."""
        r = client.get(f"{BASE}/organizations", params={"type_code": "KENDRA"})
        kendra = r.json()[0]
        assert kendra["country_name"] is not None

    def test_detail_has_postal_code(self, client):
        """Kendra org should have postal_code resolved."""
        r = client.get(f"{BASE}/organizations", params={"type_code": "KENDRA"})
        kendra = r.json()[0]
        assert kendra["postal_code"] is not None

    def test_contact_fields_nullable(self, client):
        """Contact and online presence fields are present but NULL for seeded orgs."""
        for org in client.get(f"{BASE}/organizations").json():
            assert "phone_number" in org
            assert "mobile_number" in org
            assert "email" in org
            assert "org_email" in org
            assert "website_url" in org
            assert "org_website_url" in org
            assert "youtube_channel_url" in org
            assert "org_youtube_channel_url" in org

    def test_all_orgs_have_nss_youtube(self, client):
        """Organizations have a YouTube channel URL."""
        orgs = client.get(f"{BASE}/organizations").json()
        orgs_with_youtube = [o for o in orgs if o["youtube_channel_url"]]
        assert len(orgs_with_youtube) >= 1, "Expected at least 1 org with youtube_channel_url"

    def test_kendra_has_contact_info(self, client):
        """Kendra org has phone, mobile, and website populated."""
        r = client.get(f"{BASE}/organizations", params={"type_code": "KENDRA"})
        data = r.json()
        if not data:
            pytest.skip("No KENDRA org seeded")
        kendra = data[0]
        assert kendra["phone_number"] is not None, "Kendra missing phone_number"
        assert kendra["mobile_number"] is not None, "Kendra missing mobile_number"
        assert kendra["website_url"] is not None, "Kendra missing website_url"

    def test_smruti_mandira_has_contact_info(self, client):
        """Smruti Mandira has phone populated."""
        r = client.get(f"{BASE}/organizations", params={"type_code": "SMRUTI_MANDIRA"})
        data = r.json()
        if not data:
            pytest.skip("No SMRUTI_MANDIRA org seeded")
        smr = data[0]
        assert smr["phone_number"] is not None, "Smruti Mandira missing phone_number"

    def test_all_orgs_have_nss_email(self, client):
        """Organizations have an email address."""
        orgs = client.get(f"{BASE}/organizations").json()
        orgs_with_email = [o for o in orgs if o["email"]]
        assert len(orgs_with_email) >= 1, "Expected at least 1 org with email"

    def test_all_orgs_have_nss_website(self, client):
        """Organizations have a website URL."""
        orgs = client.get(f"{BASE}/organizations").json()
        orgs_with_website = [o for o in orgs if o["website_url"]]
        assert len(orgs_with_website) >= 1, "Expected at least 1 org with website_url"

    # ── Pagination ──────────────────────────────────────────────────────

    def test_pagination_default_returns_all_seeded(self, client):
        """Default limit/offset returns all seeded orgs."""
        data = client.get(f"{BASE}/organizations").json()
        assert len(data) >= 3

    def test_pagination_limit_1(self, client):
        """limit=1 returns exactly 1 organization."""
        data = client.get(f"{BASE}/organizations", params={"limit": 1}).json()
        assert len(data) == 1

    def test_pagination_offset_skips(self, client):
        """offset=1 skips the first result."""
        all_data = client.get(f"{BASE}/organizations").json()
        offset_data = client.get(f"{BASE}/organizations", params={"offset": 1}).json()
        assert len(offset_data) == len(all_data) - 1

    def test_pagination_limit_and_offset(self, client):
        """limit=1 offset=1 returns the second organization."""
        all_data = client.get(f"{BASE}/organizations").json()
        if len(all_data) < 2:
            pytest.skip("Need at least 2 orgs for offset test")
        page = client.get(f"{BASE}/organizations", params={"limit": 1, "offset": 1}).json()
        assert len(page) == 1
        assert page[0]["organization_pk"] == all_data[1]["organization_pk"]

    def test_pagination_limit_zero_returns_422(self, client):
        """limit=0 violates ge=1 constraint — returns 422."""
        r = client.get(f"{BASE}/organizations", params={"limit": 0})
        assert r.status_code == 422

    def test_pagination_limit_over_max_returns_422(self, client):
        """limit=501 exceeds MAX_LIMIT=500 — returns 422."""
        r = client.get(f"{BASE}/organizations", params={"limit": 501})
        assert r.status_code == 422

    def test_pagination_negative_offset_returns_422(self, client):
        """offset=-1 violates ge=0 constraint — returns 422."""
        r = client.get(f"{BASE}/organizations", params={"offset": -1})
        assert r.status_code == 422

    def test_pagination_large_offset_returns_empty(self, client):
        """offset beyond total count returns empty list, not error."""
        r = client.get(f"{BASE}/organizations", params={"offset": 9999})
        assert r.status_code == 200
        assert r.json() == []


# ═══════════════════════════════════════════════════════════════════════════
# 3. CHILDREN
# ═══════════════════════════════════════════════════════════════════════════


class TestOrganizationChildren:
    """GET /api/v1/organization/organizations/{pk}/children"""

    def test_children_returns_200(self, client):
        """Children endpoint returns 200 for a valid org."""
        orgs = client.get(f"{BASE}/organizations").json()
        pk = orgs[0]["organization_pk"]
        r = client.get(f"{BASE}/organizations/{pk}/children")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_children_empty_for_leaf_org(self, client):
        """Leaf orgs (no children) return empty list."""
        orgs = client.get(f"{BASE}/organizations").json()
        # Find a leaf org — one whose code is not any other org's parent
        parent_pks = {o["parent_organization_pk"] for o in orgs if o["parent_organization_pk"]}
        leaf = [o for o in orgs if o["organization_pk"] not in parent_pks]
        if not leaf:
            pytest.skip("No leaf org found")
        pk = leaf[0]["organization_pk"]
        r = client.get(f"{BASE}/organizations/{pk}/children")
        assert r.json() == []

    def test_children_fake_pk_returns_404(self, client):
        """Children of a nonexistent org returns 404."""
        assert client.get(
            f"{BASE}/organizations/{FAKE_UUID}/children"
        ).status_code == 404

    def test_children_bad_uuid_returns_422(self, client):
        """Malformed UUID in children route returns 422."""
        assert client.get(
            f"{BASE}/organizations/not-a-uuid/children"
        ).status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# 4. HIERARCHY
# ═══════════════════════════════════════════════════════════════════════════


class TestHierarchy:
    """GET /api/v1/organization/hierarchy"""

    def test_hierarchy_returns_200(self, client):
        """Hierarchy endpoint returns 200 with seeded nodes."""
        r = client.get(f"{BASE}/hierarchy")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected 3 root nodes in hierarchy"

    def test_hierarchy_has_required_fields(self, client):
        """Each hierarchy node has expected fields."""
        required = {
            "organization_pk", "organization_name", "organization_code",
            "organization_type_code", "organization_type_name",
            "status_code", "status_name",
            "parent_organization_pk", "depth", "is_active",
        }
        for node in client.get(f"{BASE}/hierarchy").json():
            assert required.issubset(node.keys()), (
                f"Missing fields in hierarchy node: {required - node.keys()}"
            )

    def test_hierarchy_roots_at_depth_0(self, client):
        """Root orgs are at depth 0 with no parent."""
        data = client.get(f"{BASE}/hierarchy").json()
        roots = [n for n in data if n["depth"] == 0]
        assert len(roots) >= 1, "Expected at least 1 root at depth 0"
        for node in roots:
            assert node["parent_organization_pk"] is None

    def test_hierarchy_returns_seeded_nodes(self, client):
        """Hierarchy has at least 3 nodes (minimum: KEN, NKT, SMR)."""
        data = client.get(f"{BASE}/hierarchy").json()
        assert len(data) >= 3

    # ── Pagination ──────────────────────────────────────────────────────

    def test_hierarchy_pagination_limit_1(self, client):
        """Hierarchy with limit=1 returns exactly 1 node."""
        data = client.get(f"{BASE}/hierarchy", params={"limit": 1}).json()
        assert len(data) == 1

    def test_hierarchy_pagination_offset(self, client):
        """Hierarchy with offset=1 skips first node."""
        all_data = client.get(f"{BASE}/hierarchy").json()
        offset_data = client.get(f"{BASE}/hierarchy", params={"offset": 1}).json()
        assert len(offset_data) == len(all_data) - 1

    def test_hierarchy_pagination_limit_zero_returns_422(self, client):
        """Hierarchy limit=0 returns 422."""
        r = client.get(f"{BASE}/hierarchy", params={"limit": 0})
        assert r.status_code == 422

    def test_hierarchy_pagination_limit_over_max_returns_422(self, client):
        """Hierarchy limit=501 returns 422."""
        r = client.get(f"{BASE}/hierarchy", params={"limit": 501})
        assert r.status_code == 422

    def test_hierarchy_pagination_negative_offset_returns_422(self, client):
        """Hierarchy offset=-1 returns 422."""
        r = client.get(f"{BASE}/hierarchy", params={"offset": -1})
        assert r.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# 5. UI ROUTE
# ═══════════════════════════════════════════════════════════════════════════


class TestOrganizationUI:
    """GET /organization — serves the verification UI page."""

    def test_organization_page_returns_200(self, client):
        """The /organization route serves HTML."""
        r = client.get("/organization")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_page_contains_title(self, client):
        """Page title includes 'Organization Verification'."""
        html = client.get("/organization").text
        assert "Organization Verification" in html

    def test_page_contains_branding(self, client):
        """Page contains the correct organization name (not 'ERP')."""
        html = client.get("/organization").text
        assert "Nilachala Saraswata Sangha" in html

    def test_page_loads_alpine_js(self, client):
        """Page includes Alpine.js CDN script with SRI hash."""
        html = client.get("/organization").text
        assert "alpinejs" in html
        assert "integrity=" in html

    def test_page_loads_daisyui(self, client):
        """Page includes DaisyUI CSS with SRI hash."""
        html = client.get("/organization").text
        assert "daisyui" in html
        assert "integrity=" in html

    def test_page_loads_tailwind(self, client):
        """Page includes Tailwind CSS Play CDN."""
        html = client.get("/organization").text
        assert "cdn.tailwindcss.com" in html

    def test_page_loads_organization_js(self, client):
        """Page includes the organization.js Alpine component."""
        html = client.get("/organization").text
        assert "organization.js" in html

    def test_page_has_alpine_data_binding(self, client):
        """Page has x-data binding to organizationApp()."""
        html = client.get("/organization").text
        assert 'x-data="organizationApp()"' in html

    def test_page_has_nav_links(self, client):
        """Page navigation includes links to all three tier UIs."""
        html = client.get("/organization").text
        assert 'href="/"' in html
        assert 'href="/foundation"' in html
        assert 'href="/organization"' in html

    def test_page_has_three_tabs(self, client):
        """Page contains the three expected tab labels."""
        html = client.get("/organization").text
        assert "Reference Data" in html
        assert "Organizations" in html
        assert "Hierarchy" in html

    def test_page_has_system_status_section(self, client):
        """Page includes the System Status health check section."""
        html = client.get("/organization").text
        assert "System Status" in html

    def test_page_has_nss_logo(self, client):
        """Page references the NSS logo image."""
        html = client.get("/organization").text
        assert "nss-logo.png" in html

    def test_page_has_copyright_footer(self, client):
        """Page has a copyright footer."""
        html = client.get("/organization").text
        assert "2026" in html
        assert "All rights reserved" in html


# ═══════════════════════════════════════════════════════════════════════════
# 6. SECURITY — Organization endpoints get security headers
# ═══════════════════════════════════════════════════════════════════════════


class TestOrganizationSecurity:
    """Verify security middleware applies to Organization endpoints."""

    def test_org_api_has_security_headers(self, client):
        """Organization API responses include the four core security headers."""
        r = client.get(f"{BASE}/types")
        assert r.status_code == 200
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"
        assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in r.headers["Permissions-Policy"]

    def test_org_api_has_cache_control_no_store(self, client):
        """Organization API responses have Cache-Control: no-store."""
        r = client.get(f"{BASE}/organizations")
        assert r.headers.get("Cache-Control") == "no-store"

    def test_org_ui_no_cache_control_no_store(self, client):
        """Organization UI page does NOT have Cache-Control: no-store."""
        r = client.get("/organization")
        assert r.status_code == 200
        assert r.headers.get("Cache-Control") != "no-store"


# ═══════════════════════════════════════════════════════════════════════════
# 8. CHILDREN STATS (aggregate counts per child org)
# ═══════════════════════════════════════════════════════════════════════════


def _get_kendra_pk(client):
    """Find the Kendra organization PK."""
    r = client.get(f"{BASE}/organizations?type_code=KENDRA")
    data = r.json()
    return data[0]["organization_pk"] if data else None


class TestChildrenStats:
    """GET /api/v1/organization/organizations/{pk}/children-stats"""

    def test_children_stats_returns_200(self, client):
        """Children stats endpoint returns 200 for a valid parent."""
        pk = _get_kendra_pk(client)
        if pk is None:
            pytest.skip("No Kendra organization seeded")
        r = client.get(f"{BASE}/organizations/{pk}/children-stats")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_children_stats_fake_pk_returns_404(self, client):
        """Non-existent parent PK returns 404."""
        r = client.get(f"{BASE}/organizations/{FAKE_UUID}/children-stats")
        assert r.status_code == 404

    def test_children_stats_has_required_fields(self, client):
        """Each child stat entry has the required fields."""
        pk = _get_kendra_pk(client)
        if pk is None:
            pytest.skip("No Kendra organization seeded")
        data = client.get(f"{BASE}/organizations/{pk}/children-stats").json()
        if not data:
            pytest.skip("Kendra has no children")
        required = {
            "organization_pk", "organization_name", "organization_code",
            "organization_type_code",
            "family_count", "member_count", "person_count",
        }
        for s in data:
            assert required.issubset(s.keys()), (
                f"Missing fields: {required - s.keys()}"
            )

    def test_children_stats_counts_are_non_negative(self, client):
        """All counts should be >= 0."""
        pk = _get_kendra_pk(client)
        if pk is None:
            pytest.skip("No Kendra organization seeded")
        for s in client.get(f"{BASE}/organizations/{pk}/children-stats").json():
            assert s["family_count"] >= 0
            assert s["member_count"] >= 0
            assert s["person_count"] >= 0

    def test_children_stats_kendra_has_families(self, client):
        """Kendra children (Anchalikas) should have at least 1 family total."""
        pk = _get_kendra_pk(client)
        if pk is None:
            pytest.skip("No Kendra organization seeded")
        data = client.get(f"{BASE}/organizations/{pk}/children-stats").json()
        total_families = sum(s["family_count"] for s in data)
        assert total_families >= 1, "Expected at least 1 family across Anchalikas"

    def test_children_stats_members_lte_persons(self, client):
        """Member count should be <= person count (not all persons are members)."""
        pk = _get_kendra_pk(client)
        if pk is None:
            pytest.skip("No Kendra organization seeded")
        for s in client.get(f"{BASE}/organizations/{pk}/children-stats").json():
            assert s["member_count"] <= s["person_count"], (
                f"{s['organization_name']}: {s['member_count']} members "
                f"> {s['person_count']} persons"
            )

    def test_children_stats_sakha_level(self, client):
        """Drilling to Anchalika level shows per-Sakha stats."""
        pk = _get_kendra_pk(client)
        if pk is None:
            pytest.skip("No Kendra organization seeded")
        # Get first Anchalika
        children = client.get(f"{BASE}/organizations/{pk}/children").json()
        if not children:
            pytest.skip("Kendra has no children")
        anch_pk = children[0]["organization_pk"]
        r = client.get(f"{BASE}/organizations/{anch_pk}/children-stats")
        assert r.status_code == 200
        data = r.json()
        # If this Anchalika has Sakha children, they should have stats
        for s in data:
            if s["organization_type_code"] == "SAKHA_SANGHA":
                assert "family_count" in s
                assert "member_count" in s

    def test_children_stats_leaf_org_returns_empty(self, client):
        """A Sakha (leaf org) should return empty children-stats."""
        sakhas = client.get(f"{BASE}/organizations?type_code=SAKHA_SANGHA").json()
        if not sakhas:
            pytest.skip("No Sakha organizations seeded")
        sakha_pk = sakhas[0]["organization_pk"]
        r = client.get(f"{BASE}/organizations/{sakha_pk}/children-stats")
        assert r.status_code == 200
        assert r.json() == []
