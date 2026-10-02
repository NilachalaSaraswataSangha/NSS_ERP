"""
NSS ERP — Tier 1 Foundation API tests.

Integration tests for the 17 Foundation GET endpoints across 11 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Endpoint groups tested:
  1. Master Data:   categories, master-data
  2. System Config: settings, sequences
  3. Geographic:    countries, states, districts, cities,
                    postal-codes, postal-code-mappings
  4. Runtime:       documents

field_change_log is intentionally not exposed in Tier 1 (deferred to
Tier 5 authenticated audit API).
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/foundation"


# Foundation read endpoints are RBAC-gated (FOUNDATION_VIEW) as of Tier 5.
# Authenticate this whole module as an admin; the standalone /foundation
# page is retired in favour of admin.html's Reference Data / Geography tabs.
@pytest.fixture(scope="module")
def client(authed_client):
    return authed_client


# ═══════════════════════════════════════════════════════════════════════════
# 1. MASTER DATA SUBSYSTEM
# ═══════════════════════════════════════════════════════════════════════════


class TestCategories:
    """GET /api/v1/foundation/categories  +  categories/{pk}"""

    def test_list_returns_200(self, client):
        """Categories list returns 200 with a non-empty list."""
        r = client.get(f"{BASE}/categories")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected seeded categories"

    def test_list_has_required_fields(self, client):
        """Each category has the expected response fields."""
        r = client.get(f"{BASE}/categories")
        required = {
            "master_category_pk", "category_code", "category_name",
            "description", "display_order", "is_active",
        }
        for cat in r.json():
            assert required.issubset(cat.keys()), (
                f"Missing fields in category {cat.get('category_code', '?')}: "
                f"{required - cat.keys()}"
            )
            assert cat["is_active"] is True

    def test_list_all_active(self, client):
        """All returned categories have is_active=True."""
        for cat in client.get(f"{BASE}/categories").json():
            assert cat["is_active"] is True

    def test_detail_valid_pk(self, client):
        """Fetching a category by valid PK returns 200."""
        cats = client.get(f"{BASE}/categories").json()
        pk = cats[0]["master_category_pk"]
        r = client.get(f"{BASE}/categories/{pk}")
        assert r.status_code == 200
        assert r.json()["master_category_pk"] == pk

    def test_detail_fake_pk_returns_404(self, client):
        """Fetching a nonexistent category returns 404."""
        fake = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"{BASE}/categories/{fake}").status_code == 404

    def test_detail_bad_uuid_returns_422(self, client):
        """Malformed UUID returns 422."""
        assert client.get(f"{BASE}/categories/not-a-uuid").status_code == 422


class TestMasterData:
    """GET /api/v1/foundation/master-data  +  master-data/{pk}"""

    def test_list_returns_200(self, client):
        """Master data list returns 200 with a non-empty list."""
        r = client.get(f"{BASE}/master-data")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected seeded master data values"

    def test_list_has_required_fields(self, client):
        """Each master data value has expected fields including JOINed category context."""
        r = client.get(f"{BASE}/master-data")
        required = {
            "master_data_pk", "master_category_pk",
            "category_code", "category_name",
            "value_code", "value_name",
            "description", "display_order", "is_active",
        }
        for md in r.json():
            assert required.issubset(md.keys()), (
                f"Missing fields in master data {md.get('value_code', '?')}: "
                f"{required - md.keys()}"
            )

    def test_filter_by_category_code(self, client):
        """Filtering by category_code returns only matching values."""
        # Get a known category code
        cats = client.get(f"{BASE}/categories").json()
        code = cats[0]["category_code"]
        r = client.get(f"{BASE}/master-data", params={"category_code": code})
        assert r.status_code == 200
        for md in r.json():
            assert md["category_code"] == code

    def test_filter_by_category_pk(self, client):
        """Filtering by category_pk returns only matching values."""
        cats = client.get(f"{BASE}/categories").json()
        pk = cats[0]["master_category_pk"]
        r = client.get(f"{BASE}/master-data", params={"category_pk": pk})
        assert r.status_code == 200
        for md in r.json():
            assert md["master_category_pk"] == pk

    def test_filter_nonexistent_category_returns_empty(self, client):
        """Filtering by a category code with no values returns empty list."""
        r = client.get(f"{BASE}/master-data", params={"category_code": "ZZZZZZZ_FAKE"})
        assert r.status_code == 200
        assert r.json() == []

    def test_detail_valid_pk(self, client):
        """Fetching a master data value by valid PK returns 200."""
        items = client.get(f"{BASE}/master-data").json()
        pk = items[0]["master_data_pk"]
        r = client.get(f"{BASE}/master-data/{pk}")
        assert r.status_code == 200
        assert r.json()["master_data_pk"] == pk

    def test_detail_fake_pk_returns_404(self, client):
        fake = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"{BASE}/master-data/{fake}").status_code == 404

    def test_detail_bad_uuid_returns_422(self, client):
        assert client.get(f"{BASE}/master-data/not-a-uuid").status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# 2. SYSTEM CONFIGURATION SUBSYSTEM
# ═══════════════════════════════════════════════════════════════════════════


class TestSettings:
    """GET /api/v1/foundation/settings  +  settings/{key}"""

    def test_list_returns_200(self, client):
        """Settings list returns 200 with a non-empty list."""
        r = client.get(f"{BASE}/settings")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected seeded system settings"

    def test_list_has_required_fields(self, client):
        """Each setting has the expected response fields."""
        required = {
            "system_setting_pk", "setting_key", "setting_value",
            "description", "data_type", "is_active",
        }
        for s in client.get(f"{BASE}/settings").json():
            assert required.issubset(s.keys()), (
                f"Missing fields in setting {s.get('setting_key', '?')}: "
                f"{required - s.keys()}"
            )

    def test_lookup_by_key(self, client):
        """Looking up a setting by its business key returns 200."""
        settings = client.get(f"{BASE}/settings").json()
        key = settings[0]["setting_key"]
        r = client.get(f"{BASE}/settings/{key}")
        assert r.status_code == 200
        assert r.json()["setting_key"] == key

    def test_lookup_nonexistent_key_returns_404(self, client):
        """Looking up a nonexistent setting key returns 404."""
        assert client.get(f"{BASE}/settings/ZZZZZ_FAKE_KEY").status_code == 404


class TestSequences:
    """GET /api/v1/foundation/sequences"""

    def test_list_returns_200(self, client):
        """Sequences list returns 200 with a non-empty list."""
        r = client.get(f"{BASE}/sequences")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected seeded ID sequences"

    def test_list_has_required_fields(self, client):
        """Each sequence has expected fields (current_value excluded)."""
        required = {
            "id_sequence_master_pk", "sequence_code", "sequence_name",
            "prefix", "padding_length", "description", "is_active",
        }
        for seq in client.get(f"{BASE}/sequences").json():
            assert required.issubset(seq.keys()), (
                f"Missing fields in sequence {seq.get('sequence_code', '?')}: "
                f"{required - seq.keys()}"
            )

    def test_current_value_not_exposed(self, client):
        """current_value is infrastructure state — must NOT be in the response."""
        for seq in client.get(f"{BASE}/sequences").json():
            assert "current_value" not in seq, (
                f"current_value leaked in sequence {seq.get('sequence_code', '?')}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 3. GEOGRAPHIC SUBSYSTEM
# ═══════════════════════════════════════════════════════════════════════════


class TestCountries:
    """GET /api/v1/foundation/countries  +  countries/{pk}"""

    def test_list_returns_200(self, client):
        r = client.get(f"{BASE}/countries")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected seeded countries"

    def test_list_has_required_fields(self, client):
        required = {
            "country_pk", "country_code", "country_name",
            "display_order", "is_active",
        }
        for c in client.get(f"{BASE}/countries").json():
            assert required.issubset(c.keys())

    def test_detail_valid_pk(self, client):
        countries = client.get(f"{BASE}/countries").json()
        pk = countries[0]["country_pk"]
        r = client.get(f"{BASE}/countries/{pk}")
        assert r.status_code == 200
        assert r.json()["country_pk"] == pk

    def test_detail_fake_pk_returns_404(self, client):
        fake = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"{BASE}/countries/{fake}").status_code == 404

    def test_detail_bad_uuid_returns_422(self, client):
        assert client.get(f"{BASE}/countries/not-a-uuid").status_code == 422


class TestStates:
    """GET /api/v1/foundation/states  +  states/{pk}"""

    def test_list_returns_200(self, client):
        r = client.get(f"{BASE}/states")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0, "Expected seeded states"

    def test_list_has_joined_country_fields(self, client):
        """Each state includes country_code and country_name via JOIN."""
        required = {
            "state_pk", "country_pk", "country_code", "country_name",
            "state_code", "state_name", "display_order", "is_active",
        }
        for s in client.get(f"{BASE}/states").json():
            assert required.issubset(s.keys())

    def test_filter_by_country_pk(self, client):
        """Filtering by country_pk returns only states in that country."""
        countries = client.get(f"{BASE}/countries").json()
        cpk = countries[0]["country_pk"]
        r = client.get(f"{BASE}/states", params={"country_pk": cpk})
        assert r.status_code == 200
        for s in r.json():
            assert s["country_pk"] == cpk

    def test_detail_valid_pk(self, client):
        states = client.get(f"{BASE}/states").json()
        pk = states[0]["state_pk"]
        r = client.get(f"{BASE}/states/{pk}")
        assert r.status_code == 200
        assert r.json()["state_pk"] == pk

    def test_detail_fake_pk_returns_404(self, client):
        fake = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"{BASE}/states/{fake}").status_code == 404


class TestDistricts:
    """GET /api/v1/foundation/districts  +  districts/{pk}"""

    def test_list_returns_200(self, client):
        r = client.get(f"{BASE}/districts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) > 0, "Expected seeded districts"

    def test_list_has_joined_state_name(self, client):
        """Each district includes state_name via JOIN."""
        required = {
            "district_pk", "state_pk", "state_name",
            "district_code", "district_name",
            "display_order", "is_active",
        }
        for d in client.get(f"{BASE}/districts").json():
            assert required.issubset(d.keys())

    def test_filter_by_state_pk(self, client):
        """Filtering by state_pk returns only districts in that state."""
        states = client.get(f"{BASE}/states").json()
        spk = states[0]["state_pk"]
        r = client.get(f"{BASE}/districts", params={"state_pk": spk})
        assert r.status_code == 200
        for d in r.json():
            assert d["state_pk"] == spk

    def test_detail_valid_pk(self, client):
        districts = client.get(f"{BASE}/districts").json()
        pk = districts[0]["district_pk"]
        r = client.get(f"{BASE}/districts/{pk}")
        assert r.status_code == 200
        assert r.json()["district_pk"] == pk

    def test_detail_fake_pk_returns_404(self, client):
        fake = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"{BASE}/districts/{fake}").status_code == 404


class TestCities:
    """GET /api/v1/foundation/cities — intentionally empty at Tier 1."""

    def test_list_returns_200(self, client):
        """Cities endpoint returns 200 (empty list — no seed data by design)."""
        r = client.get(f"{BASE}/cities")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_district_pk_returns_200(self, client):
        """Filtering by district_pk returns 200 even when empty."""
        districts = client.get(f"{BASE}/districts").json()
        dpk = districts[0]["district_pk"]
        r = client.get(f"{BASE}/cities", params={"district_pk": dpk})
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestPostalCodes:
    """GET /api/v1/foundation/postal-codes"""

    def test_list_returns_200(self, client):
        r = client.get(f"{BASE}/postal-codes")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_has_required_fields(self, client):
        """If postal codes are seeded, verify response shape."""
        data = client.get(f"{BASE}/postal-codes").json()
        if len(data) > 0:
            required = {
                "postal_code_pk", "country_pk", "state_pk",
                "state_name", "postal_code", "is_active",
            }
            for pc in data:
                assert required.issubset(pc.keys())

    def test_no_office_level_fields(self, client):
        """
        Simplified Geography Model (2026-10-02): nss.post_office is retired,
        so no office-level field may leak back into the PIN payload.
        """
        data = client.get(f"{BASE}/postal-codes").json()
        if len(data) == 0:
            pytest.skip("No postal codes seeded")
        for pc in data:
            assert "post_office_name" not in pc
            assert "office_count" not in pc

    def test_filter_by_country_pk(self, client):
        """Filtering by country_pk returns 200."""
        countries = client.get(f"{BASE}/countries").json()
        cpk = countries[0]["country_pk"]
        r = client.get(f"{BASE}/postal-codes", params={"country_pk": cpk})
        assert r.status_code == 200
        for pc in r.json():
            assert pc["country_pk"] == cpk

    def test_filter_by_state_pk(self, client):
        """Filtering by state_pk returns 200."""
        states = client.get(f"{BASE}/states").json()
        spk = states[0]["state_pk"]
        r = client.get(f"{BASE}/postal-codes", params={"state_pk": spk})
        assert r.status_code == 200
        for pc in r.json():
            assert pc["state_pk"] == spk

    # ── PIN uniqueness + ?q= (Simplified Geography Model, 2026-10-02) ──
    #
    # nss.postal_code is now unique on postal_code ALONE — one row per PIN
    # globally, carrying a pre-resolved dominant state. There is no
    # office-level detail any more, so ?q= matches the PIN digits only.

    def test_pin_is_globally_unique(self, client):
        """No PIN appears twice across the whole list."""
        data = client.get(f"{BASE}/postal-codes").json()
        if len(data) == 0:
            pytest.skip("No postal codes seeded")
        pins = [pc["postal_code"] for pc in data]
        assert len(pins) == len(set(pins))

    def test_q_matches_pin_prefix(self, client):
        """?q= on PIN digits returns only PINs starting with those digits."""
        data = client.get(f"{BASE}/postal-codes").json()
        if len(data) == 0:
            pytest.skip("No postal codes seeded")
        prefix = data[0]["postal_code"][:3]
        r = client.get(f"{BASE}/postal-codes", params={"q": prefix})
        assert r.status_code == 200
        returned = r.json()
        assert len(returned) > 0
        # ?q= is now a pure PIN-prefix match — every row must start with it.
        assert all(pc["postal_code"].startswith(prefix) for pc in returned)

    def test_q_below_min_length_rejected(self, client):
        """?q= enforces a 2-character minimum."""
        r = client.get(f"{BASE}/postal-codes", params={"q": "a"})
        assert r.status_code == 422

    # ── district scoping resolves through city_village (2026-10-02) ──
    #
    # postal_code has no district_pk of its own (a PIN is a state-scoped
    # postal unit, not a revenue-district one). "PINs in district X" is
    # answered through nss.city_village, which is now the geography anchor
    # and carries BOTH district_pk and postal_code_pk directly. The old
    # coverage gap (751006 etc. invisible under Khordha) is closed by the
    # 673k-row all-India city_village seed rather than by nss.post_office.

    @staticmethod
    def _district_with_pins(client):
        """A (district, pins) pair that actually has postal codes."""
        districts = client.get(f"{BASE}/districts").json()
        for d in districts[:25]:
            r = client.get(
                f"{BASE}/postal-codes", params={"district_pk": d["district_pk"]}
            )
            assert r.status_code == 200
            pins = r.json()
            if pins:
                return d, pins
        return None

    def test_district_filter_returns_pins(self, client):
        """A district with anchored city/village rows returns its PINs."""
        found = self._district_with_pins(client)
        if not found:
            pytest.skip("No district resolves to postal codes")
        _, pins = found
        assert len(pins) > 0

    def test_district_filtered_pins_are_unique(self, client):
        """
        The EXISTS-based district filter must not fan out: a PIN with many
        city_village rows in the district still appears exactly once.
        """
        found = self._district_with_pins(client)
        if not found:
            pytest.skip("No district resolves to postal codes")
        _, pins = found
        values = [p["postal_code"] for p in pins]
        assert len(values) == len(set(values))

    def test_district_filtered_pins_have_a_city_village_in_that_district(self, client):
        """
        Every PIN returned for a district genuinely has a city/village row
        anchored to both that district and that PIN — the exact join the
        filter uses, verified from the other direction via /cities.
        """
        found = self._district_with_pins(client)
        if not found:
            pytest.skip("No district resolves to postal codes")
        district, pins = found
        cities = client.get(
            f"{BASE}/cities", params={"district_pk": district["district_pk"]}
        ).json()
        city_pin_pks = {
            c["postal_code_pk"] for c in cities if c.get("postal_code_pk")
        }
        if not city_pin_pks:
            pytest.skip("District has no city/village rows with a resolved PIN")
        for pc in pins[:25]:
            assert pc["postal_code_pk"] in city_pin_pks, (
                f"PIN {pc['postal_code']} was returned for district "
                f"{district.get('district_name')} but no city/village row in "
                f"that district is anchored to it"
            )


class TestPostalCodeMappings:
    """GET /api/v1/foundation/postal-code-mappings — empty at Tier 1."""

    def test_list_returns_200(self, client):
        """Mappings endpoint returns 200 (empty — no city/village data yet)."""
        r = client.get(f"{BASE}/postal-code-mappings")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ═══════════════════════════════════════════════════════════════════════════
# 4. RUNTIME TABLES
# ═══════════════════════════════════════════════════════════════════════════


class TestDocuments:
    """GET /api/v1/foundation/documents — intentionally empty at Tier 1."""

    def test_list_returns_200(self, client):
        """Documents endpoint returns 200 (empty — runtime data)."""
        r = client.get(f"{BASE}/documents")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_type_code_returns_200(self, client):
        """Filtering by document_type_code returns 200 even when empty."""
        r = client.get(f"{BASE}/documents", params={"document_type_code": "PHOTO"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ═══════════════════════════════════════════════════════════════════════════
# 5. CHANGE-LOG NOT EXPOSED (Contract Verification)
# ═══════════════════════════════════════════════════════════════════════════
#
# TestChangeLogNotExposed::test_change_log_endpoint_returns_404 moved to
# tests/security/test_audit_security.py


# ═══════════════════════════════════════════════════════════════════════════
# UI ROUTES
#
# TestFoundationUI (the standalone /foundation page) removed: the page is
# retired in favour of admin.html's authenticated Reference Data / Geography
# tabs (Tier-1 parity).
# ═══════════════════════════════════════════════════════════════════════════
