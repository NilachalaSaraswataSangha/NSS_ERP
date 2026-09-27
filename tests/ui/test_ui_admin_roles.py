"""
UI tests for role assignment on the NSS ERP admin page.

Tests the role assignment modal, role dropdown options, scope hierarchy,
and the Role Assignments card in user detail view.

Fixtures used:
  - admin_page: pre-authenticated admin browser page (SS1)
  - base_url: http://localhost:8000
"""

import pytest
from playwright.sync_api import expect

from tests.ui.conftest import wait_for_alpine, click_nav_item


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EXPECTED_SCOPE_LEVELS = [
    "NSS-WIDE",
    "KENDRA",
    "ZILLA",
    "ANCHALIKA",
    "SAKHA",
    "PATHA_CHAKRA",
]


def _navigate_to_user_detail(admin_page, base_url):
    """Navigate to admin page, open Users tab, and view the first user."""
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    click_nav_item(admin_page, "User Accounts")
    admin_page.wait_for_timeout(500)

    # Click "View" on the first user row
    view_btn = admin_page.locator('button:has-text("View")').first
    view_btn.click()
    # Wait for detail view to load
    admin_page.locator('[x-show="activeTab === \'detail\'"]').wait_for(state="visible", timeout=10000)
    admin_page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAdminRoles:
    """Role assignment UI in admin user detail view."""

    def test_role_assignments_card_visible(self, admin_page, base_url):
        """User detail view should show a Role Assignments section."""
        _navigate_to_user_detail(admin_page, base_url)

        role_card = admin_page.locator(
            "text=Role Assignments"
        ).first
        expect(role_card).to_be_visible(timeout=5000)

    def test_assign_role_button_visible(self, admin_page, base_url):
        """An 'Assign Role' button should be present for admin users."""
        _navigate_to_user_detail(admin_page, base_url)

        assign_btn = admin_page.locator(
            ".btn-action.primary:has-text('Assign Role')"
        )
        expect(assign_btn).to_be_visible(timeout=5000)

    def test_role_modal_opens(self, admin_page, base_url):
        """Clicking 'Assign Role' should open the role assignment modal."""
        _navigate_to_user_detail(admin_page, base_url)

        assign_btn = admin_page.locator(
            ".btn-action.primary:has-text('Assign Role')"
        )
        assign_btn.click()
        admin_page.wait_for_timeout(500)

        # Modal uses <template x-if="showRoleModal"> — target the overlay inside
        modal = admin_page.locator('.modal-overlay:has(h3:has-text("Assign Role"))')
        expect(modal).to_be_visible(timeout=5000)

    def test_role_modal_has_role_dropdown(self, admin_page, base_url):
        """The role modal should contain a role dropdown with options."""
        _navigate_to_user_detail(admin_page, base_url)

        admin_page.locator(
            ".btn-action.primary:has-text('Assign Role')"
        ).click()
        admin_page.wait_for_timeout(500)

        role_select = admin_page.locator('select[x-model="roleForm.role_code"]')
        expect(role_select).to_be_visible(timeout=5000)

        # Should have at least one <option> beyond the default/placeholder
        options = role_select.locator("option")
        assert options.count() > 1, "Role dropdown should have selectable options"

    def test_role_modal_scope_dropdown(self, admin_page, base_url):
        """
        The scope dropdown should list the organizational hierarchy levels:
        NSS-WIDE, KENDRA, ZILLA, ANCHALIKA, SAKHA, PATHA_CHAKRA.
        """
        _navigate_to_user_detail(admin_page, base_url)

        admin_page.locator(
            ".btn-action.primary:has-text('Assign Role')"
        ).click()
        admin_page.wait_for_timeout(500)

        scope_select = admin_page.locator(
            'select[x-model="roleForm.scope_level"]'
        )
        expect(scope_select).to_be_visible(timeout=5000)

        options_text = scope_select.locator("option").all_text_contents()
        for level in EXPECTED_SCOPE_LEVELS:
            assert any(
                level in opt for opt in options_text
            ), f"Scope dropdown should contain '{level}'"

    def test_role_modal_cancel(self, admin_page, base_url):
        """Clicking Cancel in the role modal should close it."""
        _navigate_to_user_detail(admin_page, base_url)

        admin_page.locator(
            ".btn-action.primary:has-text('Assign Role')"
        ).click()
        admin_page.wait_for_timeout(500)

        modal = admin_page.locator('.modal-overlay:has(h3:has-text("Assign Role"))')
        expect(modal).to_be_visible(timeout=5000)

        # Click Cancel button inside the modal
        cancel_btn = modal.locator("button:has-text('Cancel')")
        cancel_btn.click()
        admin_page.wait_for_timeout(500)

        expect(modal).to_be_hidden(timeout=5000)
