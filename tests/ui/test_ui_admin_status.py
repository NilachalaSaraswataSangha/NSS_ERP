"""
UI tests for account status changes and the organizations tab on
the NSS ERP admin page.

Tests the direct status-action buttons (Activate / Lock Account /
Reactivate / Delete Account) in user detail and the Organizations tab
loading/content.

The old "Change Status" button + modal (a dropdown of ACTIVE/LOCKED/
INACTIVE) was removed — INACTIVE is now reachable only via Delete Account
(a real soft-delete), never via a generic status dropdown, so a single
click always maps to one unambiguous action instead of "pick a status,
then confirm."

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

def _navigate_to_user_detail(admin_page, base_url):
    """Navigate to admin page, open Users tab, and view the first user."""
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    click_nav_item(admin_page, "User Accounts")
    admin_page.wait_for_timeout(500)

    # Rows are clickable (tr.clickable-row @click="viewUser(...)") — there
    # is no separate "View" button.
    row = admin_page.locator("tr.clickable-row").first
    row.click()
    # Wait for detail view to load
    admin_page.locator('[x-show="activeTab === \'detail\'"]').wait_for(state="visible", timeout=10000)
    admin_page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Tests — Direct status-action buttons (no modal)
# ---------------------------------------------------------------------------

class TestAdminStatusActions:
    """Direct Activate / Lock Account / Reactivate buttons in user detail."""

    def test_change_status_button_removed(self, admin_page, base_url):
        """The old generic "Change Status" button/modal must be gone."""
        _navigate_to_user_detail(admin_page, base_url)

        expect(admin_page.locator('button:has-text("Change Status")')).to_have_count(0)
        expect(admin_page.locator('h3:has-text("Change Account Status")')).to_have_count(0)
        expect(admin_page.locator('select[x-model="statusNewValue"]')).to_have_count(0)

    def test_status_action_button_matches_current_status(self, admin_page, base_url):
        """
        Exactly one direct status action is offered per status: Activate
        for LOCKED/PENDING_APPROVAL, Lock Account for ACTIVE, an inline
        Reactivate mini-form for INACTIVE. Delete Account is offered for
        every non-INACTIVE status alongside the status-specific action.
        """
        _navigate_to_user_detail(admin_page, base_url)

        # Scope to the detail view — the Users list row also carries an
        # account-status badge earlier in DOM order (hidden, not removed), so
        # an unscoped .first would silently rely on both referring to the
        # same (first) user rather than actually reading the detail panel.
        #
        # The badge-account-* class family (assets/css/badges.css, applied via
        # NSS.accountBadgeClass) is unique to user_account.account_status, so
        # it identifies the status badge without matching type/lifecycle
        # badges. It replaced the old .status-badge class, which was part of a
        # second, duplicate badge system that has been removed.
        detail_div = admin_page.locator('[x-show="activeTab === \'detail\'"]')
        status_badge = detail_div.locator('[class*="badge-account-"]').first
        status_text = (status_badge.text_content() or "").strip().upper()

        # Every status action must be read from the detail panel, never from
        # the page: the Users list row carries its own quick-action buttons
        # ("Activate", "Lock", "Reset PW", admin.html:825-834), so an unscoped
        # button:has-text("Activate") resolves to one per listed user plus the
        # detail button and trips Playwright strict mode. Scoping also makes
        # the assertion mean what it says — that *this* user's detail view
        # offers the action matching *this* user's status.
        def action(label):
            return detail_div.locator(f'button:has-text("{label}")')

        # Self-service guard: the destructive actions are wrapped in
        # x-if="selectedUser.user_account_pk !== currentUser?.user_account_pk"
        # (admin.html), so an admin is never offered Lock/Delete on their own
        # account. On a freshly bootstrapped DB SS1 is the only user, so the
        # first row IS the logged-in admin and none of these buttons render.
        # Skip rather than assert — same guard as test_ui_07_admin_write.py.
        if detail_div.locator(
            'button:has-text("Activate"), button:has-text("Lock Account"), '
            'button:has-text("Delete Account")'
        ).count() == 0 and status_text != "INACTIVE":
            pytest.skip(
                f"No status action offered for status '{status_text}' — the "
                "only user is the logged-in admin (own-account guard)."
            )

        if status_text in ("LOCKED", "PENDING_APPROVAL"):
            expect(action("Activate")).to_be_visible(timeout=5000)
            expect(action("Delete Account")).to_be_visible()
        elif status_text == "ACTIVE":
            expect(action("Lock Account")).to_be_visible(timeout=5000)
            expect(action("Delete Account")).to_be_visible()
        elif status_text == "INACTIVE":
            expect(detail_div.locator('input[x-model="reactivateForm.password"]')) \
                .to_be_visible(timeout=5000)
            expect(action("Reactivate")).to_be_visible()
            expect(action("Delete Account")).to_have_count(0)
        else:
            pytest.skip(f"Unexpected account status '{status_text}' — no matching action asserted.")

    def test_lock_account_shows_confirm_dialog_not_modal(self, admin_page, base_url):
        """Clicking Lock Account (on an ACTIVE user) opens the shared
        NSSDialog confirm overlay, not a bespoke status-change modal."""
        _navigate_to_user_detail(admin_page, base_url)

        lock_btn = admin_page.locator('button:has-text("Lock Account")').first
        if lock_btn.count() == 0:
            pytest.skip(
                "No Lock Account button — the first user is either not ACTIVE "
                "or is the logged-in admin (own-account guard hides it)."
            )
        lock_btn.click()

        dialog = admin_page.locator("#nss-dialog-overlay")
        expect(dialog).to_be_visible(timeout=5000)
        expect(admin_page.locator("#nss-dialog-title")).to_have_text("Lock Account")

        # Dismiss via Cancel so this test doesn't mutate shared admin fixture state.
        dialog.locator('button:has-text("Cancel")').click()
        expect(dialog).to_be_hidden(timeout=5000)


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
        """Organizations tab should render at least one org card.

        The tab is card-based (`.data-card` per org, not a table) — an
        unscoped `tbody tr` locator would silently match some *other*
        hidden tab's table instead of actually checking this one.
        """
        admin_page.goto(f"{base_url}/admin")
        wait_for_alpine(admin_page)
        click_nav_item(admin_page, "Organizations")
        admin_page.wait_for_timeout(500)

        orgs_div = admin_page.locator('[x-show="activeTab === \'organizations\'"]')
        # First .data-card-title is the "Organizations" section heading —
        # more than one means at least one org card rendered underneath it.
        org_titles = orgs_div.locator(".data-card-title")
        assert org_titles.count() > 1, "Organizations tab should have at least one org card"
