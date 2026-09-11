"""
NSS ERP — Tier 3 Person API tests.

Integration tests for the 4 Person GET endpoints across 2 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Person tables have no seed data — the test suite verifies endpoint
structure, response shapes, error handling, security, and UI rendering.
Data-dependent assertions (field values, counts) are guarded by
availability.

Endpoint groups tested:
  1. Person List:     /persons (with filters)
  2. Person Detail:   /persons/{person_pk}
  3. Addresses:       /persons/{person_pk}/addresses
  4. Search:          /search?q=
  5. Security:        aadhaar exclusion, security headers
  6. UI Route:        /person serves HTML
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/person"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"


# ═══════════════════════════════════════════════════════════════════════════
# helpers
# ═══════════════════════════════════════════════════════════════════════════


def _get_first_person_pk(client):
    """Return the PK of the first person, or None if no data."""
    data = client.get(f"{BASE}/persons").json()
    return data[0]["person_pk"] if data else None


# ═══════════════════════════════════════════════════════════════════════════
# 1. PERSON LIST
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonList:
    """GET /api/v1/person/persons"""

    def test_list_returns_200(self, client):
        """Person list endpoint returns 200."""
        r = client.get(f"{BASE}/persons")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_has_required_fields_if_data(self, client):
        """Each person summary has the expected response fields."""
        required = {
            "person_pk", "person_id",
            "first_name", "middle_name", "last_name",
            "date_of_birth", "date_of_death",
            "gender_code", "gender_name",
            "marital_status_code", "marital_status_name",
            "blood_group_code", "blood_group_name",
            "country_phone_code", "mobile_number", "email",
            "is_active",
        }
        data = client.get(f"{BASE}/persons").json()
        for p in data:
            assert required.issubset(p.keys()), (
                f"Missing fields in person {p.get('person_id', '?')}: "
                f"{required - p.keys()}"
            )

    def test_list_all_active(self, client):
        """All returned persons have is_active=True."""
        for p in client.get(f"{BASE}/persons").json():
            assert p["is_active"] is True

    def test_list_excludes_audit_columns(self, client):
        """Audit columns must never appear in the response."""
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        for p in client.get(f"{BASE}/persons").json():
            assert audit_cols.isdisjoint(p.keys()), (
                f"Audit columns leaked in person {p.get('person_id', '?')}: "
                f"{audit_cols & p.keys()}"
            )

    def test_list_excludes_sensitive_aadhaar(self, client):
        """Summary list must not contain aadhaar_encrypted or aadhaar_hash."""
        for p in client.get(f"{BASE}/persons").json():
            assert "aadhaar_encrypted" not in p
            assert "aadhaar_hash" not in p
            # Summary also excludes aadhaar_last4
            assert "aadhaar_last4" not in p

    def test_filter_by_gender_code_returns_200(self, client):
        """Filtering by gender_code returns 200."""
        r = client.get(f"{BASE}/persons", params={"gender_code": "MALE"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        for p in r.json():
            assert p["gender_code"] == "MALE"

    def test_filter_by_marital_status_code_returns_200(self, client):
        """Filtering by marital_status_code returns 200."""
        r = client.get(f"{BASE}/persons", params={"marital_status_code": "MARRIED"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_blood_group_code_returns_200(self, client):
        """Filtering by blood_group_code returns 200."""
        r = client.get(f"{BASE}/persons", params={"blood_group_code": "O_POSITIVE"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_nonexistent_gender_returns_empty(self, client):
        """Filtering by a nonexistent gender code returns empty list."""
        r = client.get(f"{BASE}/persons", params={"gender_code": "ZZZZZ_FAKE"})
        assert r.status_code == 200
        assert r.json() == []

    def test_multiple_filters_returns_200(self, client):
        """Combining multiple filters returns 200."""
        r = client.get(f"{BASE}/persons", params={
            "gender_code": "MALE",
            "marital_status_code": "MARRIED",
            "blood_group_code": "O_POSITIVE",
        })
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    # ── Pagination ──────────────────────────────────────────────────────

    def test_pagination_default_returns_200(self, client):
        """Default limit/offset returns 200."""
        r = client.get(f"{BASE}/persons")
        assert r.status_code == 200

    def test_pagination_custom_limit(self, client):
        """limit=1 returns at most 1 person."""
        data = client.get(f"{BASE}/persons", params={"limit": 1}).json()
        assert len(data) <= 1

    def test_pagination_limit_zero_returns_422(self, client):
        """limit=0 violates ge=1 constraint — returns 422."""
        r = client.get(f"{BASE}/persons", params={"limit": 0})
        assert r.status_code == 422

    def test_pagination_limit_over_max_returns_422(self, client):
        """limit=501 exceeds MAX_LIMIT=500 — returns 422."""
        r = client.get(f"{BASE}/persons", params={"limit": 501})
        assert r.status_code == 422

    def test_pagination_negative_offset_returns_422(self, client):
        """offset=-1 violates ge=0 constraint — returns 422."""
        r = client.get(f"{BASE}/persons", params={"offset": -1})
        assert r.status_code == 422

    def test_pagination_large_offset_returns_empty(self, client):
        """offset beyond total count returns empty list, not error."""
        r = client.get(f"{BASE}/persons", params={"offset": 9999})
        assert r.status_code == 200
        assert r.json() == []

    def test_pagination_max_limit_accepted(self, client):
        """limit=500 (MAX_LIMIT) is accepted."""
        r = client.get(f"{BASE}/persons", params={"limit": 500})
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# 2. PERSON DETAIL
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonDetail:
    """GET /api/v1/person/persons/{person_pk}"""

    def test_detail_fake_pk_returns_404(self, client):
        """Fetching a nonexistent person returns 404."""
        r = client.get(f"{BASE}/persons/{FAKE_UUID}")
        assert r.status_code == 404

    def test_detail_bad_uuid_returns_422(self, client):
        """Malformed UUID returns 422."""
        r = client.get(f"{BASE}/persons/not-a-uuid")
        assert r.status_code == 422

    def test_detail_valid_pk_returns_200(self, client):
        """Fetching a person by valid PK returns 200 with full fields."""
        pk = _get_first_person_pk(client)
        if pk is None:
            pytest.skip("No person data seeded")
        r = client.get(f"{BASE}/persons/{pk}")
        assert r.status_code == 200
        data = r.json()
        assert data["person_pk"] == pk

    def test_detail_has_required_fields(self, client):
        """Full detail response has all PersonResponse fields."""
        pk = _get_first_person_pk(client)
        if pk is None:
            pytest.skip("No person data seeded")
        required = {
            "person_pk", "person_id",
            "first_name", "middle_name", "last_name",
            "date_of_birth", "date_of_death",
            "gender_master_data_pk", "gender_code", "gender_name",
            "marital_status_master_data_pk", "marital_status_code",
            "marital_status_name",
            "blood_group_master_data_pk", "blood_group_code",
            "blood_group_name",
            "country_phone_code", "mobile_number", "email",
            "aadhaar_last4",
            "photo_document_master_pk",
            "emergency_contact_name", "emergency_contact_phone",
            "emergency_relationship_master_data_pk",
            "emergency_relationship_code", "emergency_relationship_name",
            "remarks", "is_active",
        }
        data = client.get(f"{BASE}/persons/{pk}").json()
        assert required.issubset(data.keys()), (
            f"Missing fields: {required - data.keys()}"
        )

    def test_detail_excludes_sensitive_aadhaar(self, client):
        """Detail response must never contain raw Aadhaar fields."""
        pk = _get_first_person_pk(client)
        if pk is None:
            pytest.skip("No person data seeded")
        data = client.get(f"{BASE}/persons/{pk}").json()
        assert "aadhaar_encrypted" not in data
        assert "aadhaar_hash" not in data

    def test_detail_excludes_audit_columns(self, client):
        """Audit columns must never appear in detail response."""
        pk = _get_first_person_pk(client)
        if pk is None:
            pytest.skip("No person data seeded")
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        data = client.get(f"{BASE}/persons/{pk}").json()
        assert audit_cols.isdisjoint(data.keys()), (
            f"Audit columns leaked: {audit_cols & data.keys()}"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 3. ADDRESSES
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonAddresses:
    """GET /api/v1/person/persons/{person_pk}/addresses"""

    def test_addresses_fake_pk_returns_404(self, client):
        """Addresses for a nonexistent person returns 404."""
        r = client.get(f"{BASE}/persons/{FAKE_UUID}/addresses")
        assert r.status_code == 404

    def test_addresses_bad_uuid_returns_422(self, client):
        """Malformed UUID in addresses route returns 422."""
        r = client.get(f"{BASE}/persons/not-a-uuid/addresses")
        assert r.status_code == 422

    def test_addresses_valid_pk_returns_200(self, client):
        """Addresses for a valid person returns 200 (possibly empty)."""
        pk = _get_first_person_pk(client)
        if pk is None:
            pytest.skip("No person data seeded")
        r = client.get(f"{BASE}/persons/{pk}/addresses")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_addresses_has_required_fields_if_data(self, client):
        """Each address has the expected response fields."""
        pk = _get_first_person_pk(client)
        if pk is None:
            pytest.skip("No person data seeded")
        required = {
            "person_address_pk", "person_pk",
            "address_type_master_data_pk", "address_type_code",
            "address_type_name",
            "address_line_1", "address_line_2", "landmark",
            "city_village_postal_code_map_pk",
            "city_village_name", "postal_code",
            "district_name", "state_name", "country_name",
            "is_primary", "remarks", "is_active",
        }
        data = client.get(f"{BASE}/persons/{pk}/addresses").json()
        for addr in data:
            assert required.issubset(addr.keys()), (
                f"Missing fields in address: {required - addr.keys()}"
            )

    def test_addresses_primary_first(self, client):
        """Primary addresses are ordered before non-primary."""
        pk = _get_first_person_pk(client)
        if pk is None:
            pytest.skip("No person data seeded")
        data = client.get(f"{BASE}/persons/{pk}/addresses").json()
        if len(data) >= 2:
            # Primary addresses come first in the ordering
            primaries = [a for a in data if a["is_primary"]]
            non_primaries = [a for a in data if not a["is_primary"]]
            if primaries and non_primaries:
                first_non_primary_idx = next(
                    i for i, a in enumerate(data) if not a["is_primary"]
                )
                last_primary_idx = max(
                    i for i, a in enumerate(data) if a["is_primary"]
                )
                assert last_primary_idx < first_non_primary_idx


# ═══════════════════════════════════════════════════════════════════════════
# 4. SEARCH
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonSearch:
    """GET /api/v1/person/search?q="""

    def test_search_returns_200(self, client):
        """Search with a valid query returns 200."""
        r = client.get(f"{BASE}/search", params={"q": "test"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_search_requires_query(self, client):
        """Search without q parameter returns 422."""
        r = client.get(f"{BASE}/search")
        assert r.status_code == 422

    def test_search_min_length_validation(self, client):
        """Search with single character returns 422 (min_length=2)."""
        r = client.get(f"{BASE}/search", params={"q": "a"})
        assert r.status_code == 422

    def test_search_two_chars_accepted(self, client):
        """Search with exactly 2 characters returns 200."""
        r = client.get(f"{BASE}/search", params={"q": "ab"})
        assert r.status_code == 200

    def test_search_returns_summary_fields(self, client):
        """Search results use PersonSummaryResponse shape."""
        r = client.get(f"{BASE}/search", params={"q": "test"})
        for p in r.json():
            assert "person_pk" in p
            assert "person_id" in p
            assert "first_name" in p
            assert "is_active" in p
            # Summary: no aadhaar, no emergency
            assert "aadhaar_encrypted" not in p
            assert "aadhaar_hash" not in p
            assert "aadhaar_last4" not in p

    def test_search_excludes_audit_columns(self, client):
        """Search results must not contain audit columns."""
        audit_cols = {
            "created_at", "updated_at", "deleted_at",
            "created_by_sangha_sevi_pk",
            "updated_by_sangha_sevi_pk",
            "deleted_by_sangha_sevi_pk",
        }
        for p in client.get(f"{BASE}/search", params={"q": "test"}).json():
            assert audit_cols.isdisjoint(p.keys())

    def test_search_nonexistent_returns_empty(self, client):
        """Search for a name that cannot exist returns empty list."""
        r = client.get(f"{BASE}/search", params={"q": "zzzxxyynomatch"})
        assert r.status_code == 200
        assert r.json() == []

    def test_search_max_50_results(self, client):
        """Search results are capped at 50."""
        r = client.get(f"{BASE}/search", params={"q": "aa"})
        assert r.status_code == 200
        assert len(r.json()) <= 50


# ═══════════════════════════════════════════════════════════════════════════
# 5. SECURITY — Person endpoints
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonSecurity:
    """Verify security middleware and data protection on Person endpoints."""

    def test_person_api_has_security_headers(self, client):
        """Person API responses include the four core security headers."""
        r = client.get(f"{BASE}/persons")
        assert r.status_code == 200
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"
        assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
        assert "camera=()" in r.headers["Permissions-Policy"]

    def test_person_api_has_cache_control_no_store(self, client):
        """Person API responses have Cache-Control: no-store."""
        r = client.get(f"{BASE}/persons")
        assert r.headers.get("Cache-Control") == "no-store"

    def test_person_ui_no_cache_control_no_store(self, client):
        """Person UI page does NOT have Cache-Control: no-store."""
        r = client.get("/person")
        assert r.status_code == 200
        assert r.headers.get("Cache-Control") != "no-store"

    def test_search_has_security_headers(self, client):
        """Search endpoint also gets security headers."""
        r = client.get(f"{BASE}/search", params={"q": "test"})
        assert r.headers["X-Content-Type-Options"] == "nosniff"

    def test_404_has_security_headers(self, client):
        """Even 404 responses get security headers."""
        r = client.get(f"{BASE}/persons/{FAKE_UUID}")
        assert r.status_code == 404
        assert r.headers["X-Content-Type-Options"] == "nosniff"


# ═══════════════════════════════════════════════════════════════════════════
# 6. UI ROUTE
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonUI:
    """GET /person — serves the verification UI page."""

    def test_person_page_returns_200(self, client):
        """The /person route serves HTML."""
        r = client.get("/person")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_page_contains_title(self, client):
        """Page title includes 'Person Verification'."""
        html = client.get("/person").text
        assert "Person Verification" in html

    def test_page_contains_branding(self, client):
        """Page contains the correct organization name (not 'ERP')."""
        html = client.get("/person").text
        assert "Nilachala Saraswata Sangha" in html

    def test_page_loads_alpine_js(self, client):
        """Page includes Alpine.js CDN script with SRI hash."""
        html = client.get("/person").text
        assert "alpinejs" in html
        assert "integrity=" in html

    def test_page_loads_daisyui(self, client):
        """Page includes DaisyUI CSS with SRI hash."""
        html = client.get("/person").text
        assert "daisyui" in html
        assert "integrity=" in html

    def test_page_loads_tailwind(self, client):
        """Page includes Tailwind CSS Play CDN."""
        html = client.get("/person").text
        assert "cdn.tailwindcss.com" in html

    def test_page_loads_person_js(self, client):
        """Page includes the person.js Alpine component."""
        html = client.get("/person").text
        assert "person.js" in html

    def test_page_has_alpine_data_binding(self, client):
        """Page has x-data binding to personApp()."""
        html = client.get("/person").text
        assert 'x-data="personApp()"' in html

    def test_page_has_nav_links(self, client):
        """Page navigation includes links to all four tier UIs."""
        html = client.get("/person").text
        assert 'href="/"' in html
        assert 'href="/foundation"' in html
        assert 'href="/organization"' in html
        assert 'href="/person"' in html

    def test_page_has_two_tabs(self, client):
        """Page contains the two expected tab labels."""
        html = client.get("/person").text
        assert "Persons" in html
        assert "Search" in html

    def test_page_has_system_status_section(self, client):
        """Page includes the System Status health check section."""
        html = client.get("/person").text
        assert "System Status" in html

    def test_page_has_nss_logo(self, client):
        """Page references the NSS logo image."""
        html = client.get("/person").text
        assert "nss-logo.png" in html

    def test_page_has_copyright_footer(self, client):
        """Page has a copyright footer."""
        html = client.get("/person").text
        assert "2026" in html
        assert "All rights reserved" in html

    def test_page_has_aadhaar_masking(self, client):
        """Page template contains the Aadhaar masking pattern."""
        html = client.get("/person").text
        assert "XXXX XXXX" in html

    def test_page_has_search_input(self, client):
        """Page contains a search input for trigram search."""
        html = client.get("/person").text
        assert "trigram" in html.lower()
