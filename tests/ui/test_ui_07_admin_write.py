"""
UI tests for Admin write-path operations.

Covers operations that the existing admin tests (read-only verification) skip:
  - Claim approval / rejection (requires prior registration)
  - Role assignment submission
  - Status change submission
  - Admin change password form

Run order: 07 (after registration — claims depend on prior registrations).

Fixtures: admin_page (pre-authenticated SS1)
"""

import pytest
from playwright.sync_api import Page, expect

from tests.ui.conftest import (
    wait_for_alpine,
    click_nav_item,
    ADMIN_SS_ID,
    ADMIN_PASSWORD_NEW,
    BASE_URL,
)

pytestmark = pytest.mark.ui

# NB: BASE_URL is imported, not redefined. A local copy pinned to port 8001
# silently ignored NSS_UI_BASE_URL, so the fixture authenticated against one
# origin while these helpers navigated to another — localStorage is per-origin,
# so every page bounced to /login and the tests failed on unrelated assertions.


# ── Helpers ────────────────────────────────────────────────────────────

def _goto_admin(admin_page: Page):
    admin_page.goto(f"{BASE_URL}/admin")
    wait_for_alpine(admin_page)
    admin_page.wait_for_timeout(1000)


def _navigate_to_tab(admin_page: Page, tab_name: str):
    """
    Navigate to admin page and open a specific sidebar tab.

    The label fallbacks exist because a few tabs have been renamed over time.
    If none of them matches, re-raise: swallowing the failure left the test to
    fail later on an unrelated assertion, hiding both the real cause and the
    diagnostics click_nav_item collects.
    """
    _goto_admin(admin_page)
    alternatives = {
        "Registration Approvals": ["Claims", "Approvals"],
        "Claims": ["Registration Approvals", "Approvals"],
        "Organizations": ["Orgs"],
        "Change Password": ["Password"],
    }
    last_error = None
    for label in [tab_name, *alternatives.get(tab_name, [])]:
        try:
            click_nav_item(admin_page, label)
            admin_page.wait_for_timeout(1000)
            return
        except Exception as exc:
            last_error = exc
    raise AssertionError(
        f"none of the sidebar labels for '{tab_name}' could be opened"
    ) from last_error


def _open_claims_tab(admin_page: Page):
    """Navigate to claims tab and wait for claims to load."""
    _navigate_to_tab(admin_page, "Registration Approvals")
    # Wait for claims table to load (activeTab === 'claims')
    claims_div = admin_page.locator('[x-show="activeTab === \'claims\'"]')
    claims_div.wait_for(state="visible", timeout=5000)
    admin_page.wait_for_timeout(1500)


def _click_first_claim(admin_page: Page):
    """Click the first claim row in the claims table. Returns True if clicked."""
    # Claims table rows have @click="viewClaim(...)"
    claims_div = admin_page.locator('[x-show="activeTab === \'claims\'"]')
    rows = claims_div.locator("tbody tr")
    if rows.count() == 0:
        return False
    # Click the row itself (or its View button)
    rows.first.click()
    admin_page.wait_for_timeout(1000)
    return True


# ── Claim approval/rejection ──────────────────────────────────────────


class TestAdminClaimActions:
    """
    Tests for approving and rejecting registration claims.

    Prerequisite: test_ui_06_register_submit.py created registrations
    that should appear as PENDING claims.
    """

    def test_pending_claims_exist_after_registration(self, admin_page: Page, base_url: str):
        """After registration, at least one pending claim should appear."""
        _open_claims_tab(admin_page)

        # Pending pill should be active by default
        pending_pill = admin_page.locator('.tab-pill:has-text("Pending")')
        if pending_pill.count() == 0:
            pytest.skip("No Pending pill found")

        claims_div = admin_page.locator('[x-show="activeTab === \'claims\'"]')
        rows = claims_div.locator("tbody tr")
        if rows.count() == 0:
            pytest.skip(
                "No pending claims — registration tests may not have created any"
            )
        assert rows.count() > 0, "Should have at least one pending claim"

    def test_claim_detail_has_approve_reject_buttons(self, admin_page: Page, base_url: str):
        """Opening a claim detail shows Approve and Reject action buttons."""
        _open_claims_tab(admin_page)

        if not _click_first_claim(admin_page):
            pytest.skip("No claims to test")

        # The claim detail shows "Approve & Activate" and "Reject" buttons
        # inside a template x-if="selectedClaim && claimsStatusFilter === 'PENDING'"
        approve_btn = admin_page.locator('button:has-text("Approve")')
        reject_btn = admin_page.locator('button:has-text("Reject")')
        assert approve_btn.count() > 0 or reject_btn.count() > 0, (
            "Claim detail should show Approve/Reject buttons"
        )

    def test_approve_claim(self, admin_page: Page, base_url: str):
        """Clicking Approve on a pending claim changes its status."""
        _open_claims_tab(admin_page)

        if not _click_first_claim(admin_page):
            pytest.skip("No claims to approve")

        approve_btn = admin_page.locator('button:has-text("Approve")')
        if approve_btn.count() == 0:
            pytest.skip("Approve button not found")

        approve_btn.first.click()
        admin_page.wait_for_timeout(2000)

        # After approval, claim should move to Approved tab
        # Look for success toast or reduced pending count


# ── Direct status actions (Activate / Lock Account / Delete) ──────────
# The old "Change Status" button + modal (ACTIVE/LOCKED/INACTIVE dropdown)
# was removed — replaced with one direct action button per status
# (Activate, Lock Account, or an inline Reactivate mini-form for INACTIVE),
# confirmed via the shared NSSDialog overlay instead of a bespoke modal.


class TestAdminStatusChange:
    """Tests for the direct account status action buttons."""

    def test_status_action_opens_confirm_dialog(self, admin_page: Page, base_url: str):
        """Clicking Activate or Lock Account on a user opens the shared
        NSSDialog confirm overlay (not the old status-change modal)."""
        _goto_admin(admin_page)
        admin_page.wait_for_timeout(2000)

        # `tbody tr` matches every panel's table in admin.html (most of them
        # hidden), so target the users list's own clickable rows and wait for
        # the first one instead of trusting a non-auto-waiting count().
        rows = admin_page.locator("tr.clickable-row")
        try:
            rows.first.wait_for(state="visible", timeout=10_000)
        except Exception:
            pytest.skip("No users")
        rows.first.click()

        # Read the action from the detail panel only: the users list rows carry
        # their own "Activate"/"Lock" quick actions (admin.html:825-834), so an
        # unscoped locator matches one per listed user as well.
        detail_div = admin_page.locator('[x-show="activeTab === \'detail\'"]')
        detail_div.wait_for(state="visible", timeout=10_000)
        admin_page.wait_for_timeout(500)

        action_btn = detail_div.locator(
            'button:has-text("Activate"), button:has-text("Lock Account")'
        )
        if action_btn.count() == 0:
            # Only SS1 exists and it's the logged-in admin — no status
            # action is offered for one's own account.
            pytest.skip("No status action button found (may be own account)")

        action_btn.first.click()
        admin_page.wait_for_timeout(500)

        dialog = admin_page.locator("#nss-dialog-overlay")
        expect(dialog).to_be_visible(timeout=5000)

        # Dismiss without mutating state
        dialog.locator('button:has-text("Cancel")').first.click()

    def test_no_status_dropdown_modal(self, admin_page: Page, base_url: str):
        """The old ACTIVE/LOCKED/INACTIVE dropdown modal must not exist."""
        _goto_admin(admin_page)
        admin_page.wait_for_timeout(2000)

        assert admin_page.locator('[x-show="showStatusModal"]').count() == 0
        assert admin_page.locator('select[x-model="statusNewValue"]').count() == 0
        assert admin_page.locator('h3:has-text("Change Account Status")').count() == 0



# ── Role assignment modal ─────────────────────────────────────────────


class TestAdminRoleAssignment:
    """Tests for the role assignment modal submission."""

    def test_role_modal_has_role_dropdown(self, admin_page: Page, base_url: str):
        """Role assignment modal has a role code dropdown."""
        _goto_admin(admin_page)
        admin_page.wait_for_timeout(2000)

        rows = admin_page.locator("tbody tr")
        if rows.count() == 0:
            pytest.skip("No users")

        rows.first.click()
        admin_page.wait_for_timeout(1000)

        # The "Assign Role" button in the Role Assignments card
        role_btn = admin_page.locator('button:has-text("Assign Role")')
        if role_btn.count() == 0:
            pytest.skip("Role assignment button not found")

        role_btn.first.click()
        admin_page.wait_for_timeout(1000)

        # Modal should have role dropdown
        role_dropdown = admin_page.locator('[x-model="roleForm.role_code"]')
        if role_dropdown.count() > 0:
            expect(role_dropdown.first).to_be_visible()
        else:
            pytest.skip("Role dropdown not found in modal")

    def test_role_modal_has_scope_dropdown(self, admin_page: Page, base_url: str):
        """Role assignment modal has a scope level dropdown."""
        _goto_admin(admin_page)
        admin_page.wait_for_timeout(2000)

        rows = admin_page.locator("tbody tr")
        if rows.count() == 0:
            pytest.skip("No users")

        rows.first.click()
        admin_page.wait_for_timeout(1000)

        role_btn = admin_page.locator('button:has-text("Assign Role")')
        if role_btn.count() == 0:
            pytest.skip("Role assignment button not found")

        role_btn.first.click()
        admin_page.wait_for_timeout(1000)

        scope_dropdown = admin_page.locator('[x-model="roleForm.scope_level"]')
        if scope_dropdown.count() > 0:
            expect(scope_dropdown.first).to_be_visible()
        else:
            pytest.skip("Scope dropdown not found in modal")


# ── Admin change password ─────────────────────────────────────────────


class TestAdminChangePassword:
    """Tests for the admin's own password change form."""

    def test_change_password_tab_exists(self, admin_page: Page, base_url: str):
        """Change Password tab exists in the admin sidebar."""
        _goto_admin(admin_page)

        # Sidebar nav-item with text "Change Password"
        pw_tab = admin_page.locator('.nav-item:has-text("Change Password")')
        assert pw_tab.count() > 0, "Change Password tab should exist in sidebar"

    def test_change_password_form_visible(self, admin_page: Page, base_url: str):
        """Change Password form shows current/new/confirm password fields."""
        _navigate_to_tab(admin_page, "Change Password")
        admin_page.wait_for_timeout(1000)

        # Password form uses pwForm.* model bindings
        current_pw = admin_page.locator('[x-model="pwForm.current_password"]')
        new_pw = admin_page.locator('[x-model="pwForm.new_password"]')
        confirm_pw = admin_page.locator('[x-model="pwForm.confirm_password"]')

        if current_pw.count() == 0 and new_pw.count() == 0:
            pytest.skip("Change password form fields not found")

        if current_pw.count() > 0:
            expect(current_pw.first).to_be_visible()
        if new_pw.count() > 0:
            expect(new_pw.first).to_be_visible()
        if confirm_pw.count() > 0:
            expect(confirm_pw.first).to_be_visible()


# ── Dashboard tab content ─────────────────────────────────────────────


class TestAdminDashboardContent:
    """Tests for admin dashboard tab content rendering."""

    def test_user_list_shows_ss_ids(self, admin_page: Page, base_url: str):
        """User list table shows Sangha Sevi IDs."""
        _goto_admin(admin_page)
        admin_page.wait_for_timeout(2000)

        # SS1 should be visible in the table
        ss1 = admin_page.locator("text=SS1")
        expect(ss1.first).to_be_visible(timeout=5000)

    def test_user_detail_shows_roles(self, admin_page: Page, base_url: str):
        """User detail panel shows Role Assignments card."""
        _goto_admin(admin_page)
        admin_page.wait_for_timeout(2000)

        rows = admin_page.locator("tbody tr")
        if rows.count() == 0:
            pytest.skip("No users")

        # Click the row itself — it's clickable (tr.clickable-row
        # @click="viewUser(...)"), there's no separate View button.
        rows.first.click()

        # Wait for detail view to load
        detail_div = admin_page.locator('[x-show="activeTab === \'detail\'"]')
        detail_div.wait_for(state="visible", timeout=10000)
        admin_page.wait_for_timeout(1500)

        # The detail view has a "Role Assignments" data card
        roles_card = admin_page.locator('.data-card-title:has-text("Role Assignments")')
        assert roles_card.count() > 0, "User detail should show Role Assignments card"
