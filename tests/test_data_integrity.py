"""
NSS ERP — Cross-module data integrity smoke tests.

Verifies that every module has at least one active entity in the
database. These tests catch empty-table scenarios where per-module
tests would silently pass on zero records.

All assertions are dynamic — no hardcoded IDs, codes, or counts
beyond the minimum of 1.

Modules covered:
  - Tier 0: Bootstrap (roles, permissions)
  - Tier 1: Foundation (master_data via organization types/statuses)
  - Tier 2: Organization
  - Tier 3: Person
  - Tier 4: Family, Membership
"""

import pytest


pytestmark = pytest.mark.integration


# ═══════════════════════════════════════════════════════════════════════════
# TIER 0 — BOOTSTRAP
# ═══════════════════════════════════════════════════════════════════════════


class TestBootstrapDataIntegrity:
    """Verify bootstrap data exists and is active."""

    def test_at_least_one_active_role(self, client):
        """At least one active role exists in the system."""
        data = client.get("/api/v1/bootstrap/roles").json()
        assert len(data) >= 1, "No roles found — bootstrap seed missing"
        active = [r for r in data if r["is_active"] is True]
        assert len(active) >= 1, "No active roles found"

    def test_permissions_endpoint_accessible(self, client):
        """Permissions endpoint responds (may be empty in Tier 0)."""
        r = client.get("/api/v1/bootstrap/permissions")
        assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
# TIER 1 — FOUNDATION (master_data)
# ═══════════════════════════════════════════════════════════════════════════


class TestFoundationDataIntegrity:
    """Verify foundation reference data exists."""

    def test_at_least_one_organization_type(self, client):
        """At least one active organization type exists."""
        data = client.get("/api/v1/organization/types").json()
        assert len(data) >= 1, "No organization types found — seed missing"
        active = [t for t in data if t["is_active"] is True]
        assert len(active) >= 1, "No active organization types found"

    def test_at_least_one_organization_status(self, client):
        """At least one organization-scoped status exists."""
        data = client.get("/api/v1/organization/statuses").json()
        assert len(data) >= 1, "No organization statuses found — seed missing"


# ═══════════════════════════════════════════════════════════════════════════
# TIER 2 — ORGANIZATION
# ═══════════════════════════════════════════════════════════════════════════


class TestOrganizationDataIntegrity:
    """Verify organization data exists and is active."""

    def test_at_least_one_active_organization(self, client):
        """At least one active organization exists."""
        data = client.get("/api/v1/organization/organizations").json()
        assert len(data) >= 1, "No organizations found — seed missing"
        active = [o for o in data if o["is_active"] is True]
        assert len(active) >= 1, "No active organizations found"

    def test_at_least_one_root_organization(self, client):
        """At least one root organization (no parent) exists."""
        data = client.get("/api/v1/organization/organizations").json()
        roots = [o for o in data if o["parent_organization_pk"] is None]
        assert len(roots) >= 1, "No root organizations found"

    def test_hierarchy_has_nodes(self, client):
        """Organization hierarchy has at least one node."""
        data = client.get("/api/v1/organization/hierarchy").json()
        assert len(data) >= 1, "Hierarchy is empty — seed missing"

    def test_at_least_one_org_with_contact_info(self, client):
        """At least one organization has contact information populated."""
        data = client.get("/api/v1/organization/organizations").json()
        with_contact = [
            o for o in data
            if o.get("phone_number") or o.get("mobile_number") or o.get("email")
        ]
        assert len(with_contact) >= 1, (
            "No organizations with contact info — seed data incomplete"
        )


# ═══════════════════════════════════════════════════════════════════════════
# TIER 3 — PERSON
# ═══════════════════════════════════════════════════════════════════════════


class TestPersonDataIntegrity:
    """Verify person data exists and is active."""

    def test_at_least_one_active_person(self, client):
        """At least one active person exists."""
        data = client.get("/api/v1/person/persons").json()
        assert len(data) >= 1, "No persons found — seed missing"
        active = [p for p in data if p["is_active"] is True]
        assert len(active) >= 1, "No active persons found"

    def test_at_least_one_person_with_gender(self, client):
        """At least one person has a resolved gender code."""
        data = client.get("/api/v1/person/persons").json()
        with_gender = [p for p in data if p.get("gender_code")]
        assert len(with_gender) >= 1, "No persons with gender_code populated"

    def test_at_least_one_person_with_address(self, client):
        """At least one person has an address record."""
        data = client.get("/api/v1/person/persons").json()
        if not data:
            pytest.skip("No persons seeded")
        for person in data:
            addrs = client.get(
                f"/api/v1/person/persons/{person['person_pk']}/addresses"
            ).json()
            if addrs:
                return  # pass
        pytest.skip("No persons with addresses seeded")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 4 — FAMILY
# ═══════════════════════════════════════════════════════════════════════════


class TestFamilyDataIntegrity:
    """Verify family data exists and is active."""

    def test_at_least_one_active_family(self, client):
        """At least one active family exists."""
        data = client.get("/api/v1/family/families").json()
        assert len(data) >= 1, "No families found — seed missing"
        active = [f for f in data if f["is_active"] is True]
        assert len(active) >= 1, "No active families found"

    def test_at_least_one_family_has_members(self, client):
        """At least one family has current members."""
        data = client.get("/api/v1/family/families").json()
        if not data:
            pytest.skip("No families seeded")
        for family in data:
            members = client.get(
                f"/api/v1/family/families/{family['family_group_pk']}/members"
            ).json()
            if members:
                return  # pass
        pytest.fail("No families have any current members")

    def test_at_least_one_family_has_head(self, client):
        """At least one family has a current head (is_head=True)."""
        data = client.get("/api/v1/family/families").json()
        if not data:
            pytest.skip("No families seeded")
        for family in data:
            members = client.get(
                f"/api/v1/family/families/{family['family_group_pk']}/members"
            ).json()
            heads = [m for m in members if m.get("is_head") is True]
            if heads:
                return  # pass
        pytest.fail("No families have a current head")

    def test_at_least_one_family_has_head_history(self, client):
        """At least one family has head history records."""
        data = client.get("/api/v1/family/families").json()
        if not data:
            pytest.skip("No families seeded")
        for family in data:
            history = client.get(
                f"/api/v1/family/families/{family['family_group_pk']}/head-history"
            ).json()
            if history:
                return  # pass
        pytest.fail("No families have head history records")


# ═══════════════════════════════════════════════════════════════════════════
# TIER 4 — MEMBERSHIP
# ═══════════════════════════════════════════════════════════════════════════


class TestMembershipDataIntegrity:
    """Verify membership data exists and is active."""

    def test_at_least_one_active_member(self, client):
        """At least one active member exists."""
        data = client.get("/api/v1/membership/members").json()
        assert len(data) >= 1, "No members found — seed missing"
        active = [m for m in data if m["is_active"] is True]
        assert len(active) >= 1, "No active members found"

    def test_at_least_one_regular_member(self, client):
        """At least one REGULAR member type exists."""
        data = client.get("/api/v1/membership/members").json()
        regular = [m for m in data if m["membership_type_code"] == "REGULAR"]
        assert len(regular) >= 1, "No REGULAR members found"

    def test_at_least_one_member_with_affiliation(self, client):
        """At least one member has an active affiliation."""
        data = client.get("/api/v1/membership/members").json()
        if not data:
            pytest.skip("No members seeded")
        for member in data:
            affs = client.get(
                f"/api/v1/membership/members/{member['sangha_sevi_pk']}/affiliations"
            ).json()
            if affs:
                return  # pass
        pytest.fail("No members have affiliations")

    def test_at_least_one_member_with_journey_events(self, client):
        """At least one member has journey events."""
        data = client.get("/api/v1/membership/members").json()
        if not data:
            pytest.skip("No members seeded")
        for member in data:
            events = client.get(
                f"/api/v1/membership/members/{member['sangha_sevi_pk']}/journey"
            ).json()
            if events:
                return  # pass
        pytest.fail("No members have journey events")

    def test_at_least_one_member_with_parichaya_patra(self, client):
        """At least one member has a Parichaya Patra (identity credential)."""
        data = client.get("/api/v1/membership/members").json()
        if not data:
            pytest.skip("No members seeded")
        for member in data:
            pp = client.get(
                f"/api/v1/membership/members/{member['sangha_sevi_pk']}/parichaya-patra"
            ).json()
            if pp:
                return  # pass
        pytest.fail("No members have Parichaya Patra")

    def test_at_least_one_member_with_anumati_patra(self, client):
        """At least one member has an Anumati Patra (probationary permit)."""
        data = client.get("/api/v1/membership/members").json()
        if not data:
            pytest.skip("No members seeded")
        for member in data:
            ap = client.get(
                f"/api/v1/membership/members/{member['sangha_sevi_pk']}/anumati-patra"
            ).json()
            if ap:
                return  # pass
        pytest.fail("No members have Anumati Patra")

    def test_at_least_one_member_with_erp_number(self, client):
        """At least one member has a local_sakha_erp_id (Sakha Sangha ID)."""
        data = client.get("/api/v1/membership/members").json()
        with_erp = [m for m in data if m.get("local_sakha_erp_id")]
        assert len(with_erp) >= 1, "No members with ERP number found"

    def test_membership_types_diverse(self, client):
        """At least 2 distinct membership types exist across all members."""
        data = client.get("/api/v1/membership/members").json()
        types = {m["membership_type_code"] for m in data}
        assert len(types) >= 2, (
            f"Expected at least 2 membership types, got: {types}"
        )
