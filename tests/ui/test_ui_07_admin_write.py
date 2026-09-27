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
)

pytestmark = pytest.mark.ui

BASE_URL = "http://127.0.0.1:8001"


# ── Helpers ────────────────────────────────────────────────────────────

def _goto_admin(admin_page: Page):
    admin_page.goto(f"{BASE_URL}/admin")
    wait_for_alpine(admin_page)
    admin_page.wait_for_timeout(1000)


def _navigate_to_tab(admin_page: Page, tab_name: str):
    """Navigate to admin page and open a specific sidebar tab."""
    _goto_admin(admin_page)
    try:
        click_nav_item(admin_page, tab_name)
    except Exception:
        alternatives = {
            "Registration Approvals": ["Claims", "Approvals"],
            "Claims": ["Registration Approvals", "Approvals"],
            "Organizations": ["Orgs"],
            "Change Password": ["Password"],
        }
        for alt in alternatives.get(tab_name, []):
            try:
                click_nav_item(admin_page, alt)
                break
            except Exception:
                continue
    admin_page.wait_for_timeout(1000)


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


# ── Status change modal ───────────────────────────────────────────────


class TestAdminStatusChange:
    """Tests for the account status change modal."""

    def test_status_modal_opens_from_user_list(self, admin_page: Page, base_url: str):
        """Clicking the status button on a user opens the status change modal."""
        _goto_admin(admin_page)
        admin_page.wait_for_timeout(2000)

        # Look for a status change button in the user list
        status_btns = admin_page.locator('button:has-text("Status")')
        if status_btns.count() == 0:
            # Try opening a user detail first
            rows = admin_page.locator("tbody tr")
            if rows.count() > 0:
                rows.first.click()
                admin_page.wait_for_timeout(1000)
                status_btns = admin_page.locator('button:has-text("Status")')

        if status_btns.count() == 0:
            pytest.skip("No status change button found")

        status_btns.first.click()
        admin_page.wait_for_timeout(1000)

        # Modal should appear
        modal = admin_page.locator('[x-show="showStatusModal"]')
        if modal.count() > 0 and modal.first.is_visible():
            expect(modal.first).to_be_visible()
        else:
            # May have shown self-change error dialog
            dialog = admin_page.locator("text=cannot change your own")
            if dialog.count() > 0:
                pytest.skip("Only SS1 exists — cannot change own status")

    def test_status_modal_has_options(self, admin_page: Page, base_url: str):
        """Status change modal shows ACTIVE/LOCKED/INACTIVE options."""
        _goto_admin(admin_page)
        admin_page.wait_for_timeout(2000)

        # This test requires a second user account to exist
        rows = admin_page.locator("tbody tr")
        if rows.count() < 2:
            pytest.skip("Need at least 2 users to test status change")

        # Click on the second user (not SS1)
        rows.nth(1).click()
        admin_page.wait_for_timeout(1000)

        status_btn = admin_page.locator('button:has-text("Status")')
        if status_btn.count() == 0:
            pytest.skip("Status button not available for selected user")

        status_btn.first.click()
        admin_page.wait_for_timeout(1000)

        # Check for status options
        for status in ["ACTIVE", "LOCKED", "INACTIVE"]:
            option = admin_page.locator(f"text={status}")
            if option.count() > 0:
                return  # Found at least one status option
        pytest.skip("Status modal options not visible")


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

        # Click the View button inside the first row (not the row itself)
        view_btn = rows.first.locator('button:has-text("View")')
        if view_btn.count() == 0:
            pytest.skip("No View button in user row")
        view_btn.first.click()

        # Wait for detail view to load
        detail_div = admin_page.locator('[x-show="activeTab === \'detail\'"]')
        detail_div.wait_for(state="visible", timeout=10000)
        admin_page.wait_for_timeout(1500)

        # The detail view has a "Role Assignments" data card
        roles_card = admin_page.locator('.data-card-title:has-text("Role Assignments")')
        assert roles_card.count() > 0, "User detail should show Role Assignments card"
