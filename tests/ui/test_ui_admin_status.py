"""
UI tests for account status changes and the organizations tab on
the NSS ERP admin page.

Tests the Change Account Status modal (options, cancel behaviour)
and the Organizations tab loading/content.

Fixtures used:
  - admin_page: pre-authenticated admin browser page (SS1)
  - base_url: http://localhost:8000
"""

import pytest
from playwright.sync_api import expect

from tests.ui.conftest import wait_for_alpine, click_nav_item, get_table_rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_STATUS_OPTIONS = {"ACTIVE", "LOCKED", "INACTIVE"}
INVALID_STATUS_OPTIONS = {"SUSPENDED", "DEACTIVATED"}


def _navigate_to_user_detail(admin_page, base_url):
    """Navigate to admin page, open Users tab, and view the first user."""
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    click_nav_item(admin_page, "User Accounts")
    admin_page.wait_for_timeout(500)

    view_btn = admin_page.locator('button:has-text("View")').first
    view_btn.click()
    # Wait for detail view to load
    admin_page.locator('[x-show="activeTab === \'detail\'"]').wait_for(state="visible", timeout=10000)
    admin_page.wait_for_timeout(500)


def _open_status_modal(admin_page):
    """Click the Change Status button in user detail to open the modal."""
    status_btn = admin_page.locator('button:has-text("Change Status")').first
    if status_btn.count() == 0:
        status_btn = admin_page.locator('button:has-text("Change Account Status")').first
    status_btn.click()
    admin_page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Tests — Status Modal
# ---------------------------------------------------------------------------

class TestAdminStatusModal:
    """Account status change modal in admin user detail."""

    def test_status_modal_opens(self, admin_page, base_url):
        """Clicking Change Status in user detail should open the modal."""
        _navigate_to_user_detail(admin_page, base_url)
        _open_status_modal(admin_page)

        modal = admin_page.locator('.modal-overlay:has(h3:has-text("Change Account Status"))')
        expect(modal).to_be_visible(timeout=5000)

        # Modal title
        title = modal.locator("text=Change Account Status")
        expect(title).to_be_visible()

    def test_status_modal_has_correct_options(self, admin_page, base_url):
        """
        Status dropdown should have ACTIVE, LOCKED, INACTIVE and must
        NOT have SUSPENDED or DEACTIVATED.
        """
        _navigate_to_user_detail(admin_page, base_url)
        _open_status_modal(admin_page)

        status_select = admin_page.locator(
            'select[x-model="statusNewValue"]'
        )
        expect(status_select).to_be_visible(timeout=5000)

        options = status_select.locator("option")
        option_values = []
        for i in range(options.count()):
            val = options.nth(i).get_attribute("value") or ""
            text = options.nth(i).text_content() or ""
            option_values.append(val.strip().upper())
            option_values.append(text.strip().upper())

        for valid in VALID_STATUS_OPTIONS:
            assert any(
                valid in v for v in option_values
            ), f"Status dropdown should contain '{valid}'"

        for invalid in INVALID_STATUS_OPTIONS:
            assert not any(
                invalid in v for v in option_values
            ), f"Status dropdown should NOT contain '{invalid}'"

    def test_status_modal_cancel(self, admin_page, base_url):
        """Cancel should close the status modal without changes."""
        _navigate_to_user_detail(admin_page, base_url)
        _open_status_modal(admin_page)

        modal = admin_page.locator('.modal-overlay:has(h3:has-text("Change Account Status"))')
        expect(modal).to_be_visible(timeout=5000)

        cancel_btn = modal.locator("button:has-text('Cancel')")
        cancel_btn.click()
        admin_page.wait_for_timeout(500)

        expect(modal).to_be_hidden(timeout=5000)


# ---------------------------------------------------------------------------
# Tests — Organizations Tab
# ---------------------------------------------------------------------------

class TestAdminOrganizationsTab:
    """Organizations tab on the admin page."""

    def test_organizations_tab_loads(self, admin_page, base_url):
        """Switching to the organizations tab should show the org list."""
        admin_page.goto(f"{base_url}/admin")
        wait_for_alpine(admin_page)
        click_nav_item(admin_page, "Organizations")
        admin_page.wait_for_timeout(500)

        # Verify organizations content is visible
        org_content = admin_page.locator("text=Organizations").first
        expect(org_content).to_be_visible(timeout=5000)

    def test_organizations_table_has_data(self, admin_page, base_url):
        """Organization table should have at least one row of data."""
        admin_page.goto(f"{base_url}/admin")
        wait_for_alpine(admin_page)
        click_nav_item(admin_page, "Organizations")
        admin_page.wait_for_timeout(500)

        rows = admin_page.locator("tbody tr")
        assert rows.count() > 0, "Organizations table should have at least one row"
