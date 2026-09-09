"""
NSS ERP — Tier 0 Bootstrap API tests.

Four integration tests corresponding to the four Tier 0 API contracts:
  1. GET /api/v1/bootstrap/health
  2. GET /api/v1/bootstrap/roles
  3. GET /api/v1/bootstrap/permissions
  4. GET /api/v1/bootstrap/roles/{role_pk}/permissions

These tests run against local PostgreSQL (not Neon).
The database must be bootstrapped with DDL + seed before running.
"""

import pytest


pytestmark = pytest.mark.integration


class TestHealth:
    """GET /api/v1/bootstrap/health"""

    def test_health_returns_ok(self, client):
        """Health endpoint returns 200 with status 'ok' when DB is reachable."""
        response = client.get("/api/v1/bootstrap/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"


class TestRoles:
    """GET /api/v1/bootstrap/roles"""

    def test_roles_returns_list(self, client):
        """Roles endpoint returns a non-empty list of active roles."""
        response = client.get("/api/v1/bootstrap/roles")
        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)
        assert len(roles) == 8, f"Expected 8 frozen roles, got {len(roles)}"

    def test_roles_have_required_fields(self, client):
        """Each role has the expected response fields."""
        response = client.get("/api/v1/bootstrap/roles")
        roles = response.json()
        required_fields = {
            "role_master_pk",
            "role_code",
            "role_name",
            "role_class",
            "scope_level",
            "display_order",
            "is_active",
        }
        for role in roles:
            assert required_fields.issubset(role.keys()), (
                f"Missing fields in role {role.get('role_code', '?')}: "
                f"{required_fields - role.keys()}"
            )
            assert role["is_active"] is True

    def test_roles_include_known_codes(self, client):
        """All 8 frozen role codes are present."""
        response = client.get("/api/v1/bootstrap/roles")
        codes = {r["role_code"] for r in response.json()}
        expected = {
            "NSS_ERP_ADMIN",
            "NSS_ERP_AUDITOR",
            "NSS_ERP_REPORT_VIEWER",
            "NSS_ERP_KENDRA_ADMIN",
            "NSS_ERP_ANCHALIKA_ADMIN",
            "NSS_ERP_ZILLA_ADMIN",
            "NSS_ERP_SAKHA_ADMIN",
            "NSS_ERP_PATHA_CHAKRA_ADMIN",
        }
        assert codes == expected, f"Role codes mismatch: {codes ^ expected}"

    def test_system_roles_have_nss_wide_scope(self, client):
        """SYSTEM-class roles have NSS-WIDE scope level."""
        response = client.get("/api/v1/bootstrap/roles")
        system_roles = [r for r in response.json() if r["role_class"] == "SYSTEM"]
        assert len(system_roles) == 3
        for role in system_roles:
            assert role["scope_level"] == "NSS-WIDE", (
                f"SYSTEM role {role['role_code']} has scope "
                f"'{role['scope_level']}', expected 'NSS-WIDE'"
            )


class TestPermissions:
    """GET /api/v1/bootstrap/permissions"""

    def test_permissions_returns_list(self, client):
        """Permissions endpoint returns 200 with a list (may be empty in Tier 0)."""
        response = client.get("/api/v1/bootstrap/permissions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestRolePermissions:
    """GET /api/v1/bootstrap/roles/{role_pk}/permissions"""

    def test_role_permissions_valid_role(self, client):
        """Requesting permissions for a valid role returns 200."""
        # First get a real role_pk
        roles_response = client.get("/api/v1/bootstrap/roles")
        roles = roles_response.json()
        assert len(roles) > 0, "No roles to test against"

        role_pk = roles[0]["role_master_pk"]
        response = client.get(f"/api/v1/bootstrap/roles/{role_pk}/permissions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_role_permissions_invalid_role(self, client):
        """Requesting permissions for a nonexistent role returns 404."""
        fake_pk = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/bootstrap/roles/{fake_pk}/permissions")
        assert response.status_code == 404

    def test_role_permissions_invalid_uuid(self, client):
        """Requesting permissions with a malformed UUID returns 422."""
        response = client.get("/api/v1/bootstrap/roles/not-a-uuid/permissions")
        assert response.status_code == 422
