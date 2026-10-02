"""
UI tests for admin user account creation on the NSS ERP admin page.

Tests the Create tab workflow: selecting a person, verifying the
credentials form appears, password requirements, and force-password-change
default state.

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

def _navigate_to_create_tab(admin_page, base_url):
    """Navigate to the admin page and open the Create tab."""
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    click_nav_item(admin_page, "Create Person")
    admin_page.locator('[x-show="activeTab === \'create\'"]').wait_for(state="visible", timeout=5000)
    admin_page.wait_for_timeout(500)


def _get_create_tab(admin_page):
    """Return the scoped Create tab container locator."""
    return admin_page.locator('[x-show="activeTab === \'create\'"]')


def _select_first_person(admin_page):
    """
    Trigger person selection in the Create tab, then skip Step 2 (Sangha
    Sevi) so the Step 3 credentials section becomes visible.

    Types a query, waits for results, clicks Select on the first result,
    then clicks "Skip for now" on Step 2 — the credentials form is gated
    on `createForm.person_pk && (createForm.sangha_sevi_pk ||
    createForm.sangha_sevi_skipped)`, so selecting a person alone isn't
    enough to reach it (the 3-step Person -> Sangha Sevi -> Account
    Credentials flow sequences Sangha Sevi creation as its own step).
    """
    tab = _get_create_tab(admin_page)
    search_input = tab.locator('[x-model="personSearchQuery"]')
    search_input.fill("Admin")

    # Click the Search button scoped to the Create tab
    tab.locator('.btn-action.primary:has-text("Search")').click()
    admin_page.wait_for_timeout(1000)

    # Click "Select" button on the first result row
    select_btn = tab.locator('button:has-text("Select")').first
    select_btn.click()
    admin_page.wait_for_timeout(500)

    # Skip Step 2 (Sangha Sevi) to reach Step 3 (Account Credentials)
    skip_btn = tab.locator('button:has-text("Skip for now")')
    if skip_btn.count() > 0:
        skip_btn.first.click()
        admin_page.wait_for_timeout(500)


# The Create tab now carries TWO buttons whose text contains "Create Account":
# the toolbar's "+ Create Account" (which opens the modal flow) and the inline
# form's submit button. `.btn-action.primary:has-text(...)` matches both and
# trips Playwright strict mode, so match the accessible name exactly — only the
# submit button is named precisely "Create Account".
def _create_account_submit(page):
    return page.get_by_role("button", name="Create Account", exact=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAdminCreateUser:
    """Account creation form on the admin Create tab."""

    def test_account_form_appears_after_person_selection(
        self, admin_page, base_url
    ):
        """
        After selecting a person, the account credentials section
        (password field, create-account button) should become visible.
        """
        _navigate_to_create_tab(admin_page, base_url)
        _select_first_person(admin_page)

        # The credentials container is gated on createForm.person_pk && canCreateAccounts
        password_field = admin_page.locator('[x-model="createForm.password"]')
        expect(password_field).to_be_visible(timeout=5000)

        create_btn = _create_account_submit(admin_page)
        expect(create_btn).to_be_visible()

    def test_account_create_requires_password(self, admin_page, base_url):
        """
        The Create Account button should be disabled (or the form
        should not submit) when the password field is empty.
        """
        _navigate_to_create_tab(admin_page, base_url)
        _select_first_person(admin_page)

        password_field = admin_page.locator('[x-model="createForm.password"]')
        expect(password_field).to_be_visible(timeout=5000)

        # Ensure the password field is empty
        password_field.fill("")
        admin_page.wait_for_timeout(300)

        create_btn = _create_account_submit(admin_page)
        # The button should be disabled or have a disabled attribute/class
        is_disabled = create_btn.is_disabled()
        has_disabled_class = "disabled" in (
            create_btn.get_attribute("class") or ""
        )
        assert is_disabled or has_disabled_class, (
            "Create Account button should be disabled when password is empty"
        )

    def test_force_password_change_default(self, admin_page, base_url):
        """
        The 'Force password change' checkbox should be checked by default
        when the credentials form appears.
        """
        _navigate_to_create_tab(admin_page, base_url)
        _select_first_person(admin_page)

        checkbox = admin_page.locator(
            '[x-model="createForm.force_password_change"]'
        )
        expect(checkbox).to_be_visible(timeout=5000)
        expect(checkbox).to_be_checked()
