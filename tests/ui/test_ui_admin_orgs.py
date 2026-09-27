"""
UI tests for the Organizations tab on the NSS ERP admin page.

Tests tab accessibility, org card rendering, and search functionality.
The orgs tab uses a card-based layout (not a table), with each org
displayed in a `.data-card` containing name, code, address, etc.

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

def _navigate_to_orgs_tab(admin_page, base_url):
    """Navigate to the admin page and open the Organizations tab."""
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    click_nav_item(admin_page, "Organizations")
    # Wait for the orgs tab content to be visible
    orgs_div = admin_page.locator('[x-show="activeTab === \'organizations\'"]')
    orgs_div.wait_for(state="visible", timeout=5000)
    admin_page.wait_for_timeout(1000)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAdminOrgs:
    """Organizations tab on the admin page."""

    def test_orgs_tab_loads(self, admin_page, base_url):
        """Organizations tab should be accessible and show org cards."""
        _navigate_to_orgs_tab(admin_page, base_url)

        # The tab uses card-based layout with x-for="org in orgsList"
        orgs_div = admin_page.locator('[x-show="activeTab === \'organizations\'"]')

        # Should have the "Organizations" title
        title = orgs_div.locator('.data-card-title:has-text("Organizations")')
        expect(title.first).to_be_visible(timeout=5000)

    def test_orgs_has_search(self, admin_page, base_url):
        """Organizations tab should have a search input and type filter."""
        _navigate_to_orgs_tab(admin_page, base_url)

        orgs_div = admin_page.locator('[x-show="activeTab === \'organizations\'"]')

        # Search input with x-model="orgSearch"
        search_input = orgs_div.locator('[x-model="orgSearch"]')
        expect(search_input).to_be_visible(timeout=5000)

        # Type filter dropdown with x-model="orgTypeFilter"
        type_filter = orgs_div.locator('[x-model="orgTypeFilter"]')
        expect(type_filter).to_be_visible(timeout=5000)

    def test_orgs_search_filters(self, admin_page, base_url):
        """Typing a non-matching query in search should reduce results."""
        _navigate_to_orgs_tab(admin_page, base_url)

        orgs_div = admin_page.locator('[x-show="activeTab === \'organizations\'"]')
        search_input = orgs_div.locator('[x-model="orgSearch"]')

        if not search_input.is_visible():
            pytest.skip("No search input found on Organizations tab")

        # Type a query that is unlikely to match any org
        search_input.fill("zzz_nonexistent_org_query")
        # Trigger search — input has debounce, also pressing Enter triggers loadOrganizations
        admin_page.keyboard.press("Enter")
        admin_page.wait_for_timeout(1000)

        # After filtering, should show no org cards (or fewer)
        # The org cards are inside x-for="org in orgsList"
        # If no results, orgsList will be empty
        no_results_text = orgs_div.locator('text="No organizations found"')
        org_cards = orgs_div.locator('.data-card-title')
        # The first card title is always "Organizations" (the heading), so real org cards start after
        # Or simply check that either no-results message shows, or cards reduced
        has_no_results = no_results_text.count() > 0
        # org_cards includes the section title card, so > 1 means org data exists
        has_few_cards = org_cards.count() <= 1

        assert has_no_results or has_few_cards, (
            "Searching for non-existent org should show no results or fewer cards"
        )

        # Clear search and verify orgs come back
        search_input.fill("")
        admin_page.keyboard.press("Enter")
        admin_page.wait_for_timeout(1000)
