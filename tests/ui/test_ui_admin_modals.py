"""
UI tests for the Administration modals and confirm dialogs (admin.html).

Covers the admin write-path surfaces the coverage-gap audit flagged as
untested:

  * Create Account / Restore Access modal  (`showCreateAccountModal`)
  * Reset Password modal                   (`showResetModal`)
  * Revoke Role  → shared confirm dialog    (`#nss-dialog-*`)
  * Claim reject → inline remarks gate       (`adminRemarks` required)

Two of these open only after a table row is selected, and one needs a PENDING
registration claim to exist. Rather than seed state (and couple the test to a
particular fixture DB), each such test is precondition-guarded: it navigates to
the real tab and `pytest.skip`s when the required row/claim is absent. What it
asserts, it asserts against the real DOM — modal container `.modal-overlay >
.modal-card` (nodes live inside `<template x-if>`, so present only while open),
and the shared confirm dialog's stable `#nss-dialog-*` ids.

Verified selectors (admin.html / admin.js / nss-dialog.js):
  * users tab      : `.nav-item` "User Accounts"; rows `tr.clickable-row`
                     `@click="viewUser(pk)"`; "+ Create Account" button
  * reset modal    : h3 "Reset Password"; input `x-model="resetForm.new_password"`
  * create modal   : search input `x-model="cazSearch"`
  * revoke         : "Revoke" button → `NSSDialog.confirm` → `#nss-dialog-title`
                     "Revoke Role"
  * claim reject   : claims tab default filter PENDING; rows `viewClaim(pk)`;
                     textarea `x-model="adminRemarks"`; "Reject" `:disabled`
                     until remarks non-empty

Requires a live server + Postgres (BASE_URL http://127.0.0.1:8001).
"""

import pytest
from playwright.sync_api import expect

from tests.ui.conftest import wait_for_alpine, click_nav_item

pytestmark = pytest.mark.ui


@pytest.fixture
def admin_console(admin_page, base_url):
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    return admin_page


def _open_users_tab(page):
    click_nav_item(page, "User Accounts")
    wait_for_alpine(page)
    expect(page.locator("h2.data-card-title", has_text="User Accounts").first) \
        .to_be_visible(timeout=10_000)


def _select_first_user(page):
    """Open the first user's detail view, or skip if the table is empty."""
    _open_users_tab(page)
    # NB: conftest.get_table_rows() returns a COUNT, not a row list — use the
    # locator directly so .first is a real element handle. count() does not
    # auto-wait, and the users table is fetched after Alpine init, so wait for
    # the first row before deciding the DB is empty.
    rows = page.locator(".admin-table tbody tr.clickable-row")
    try:
        rows.first.wait_for(state="visible", timeout=10_000)
    except Exception:
        pytest.skip("no user accounts in the fixture DB to select")
    rows.first.click()
    wait_for_alpine(page)


def _select_user_with_action(page, action_name, exact=False, max_rows=12):
    """
    Open the detail view of the first user that actually offers `action_name`.

    Taking row 0 blindly makes these tests skip whenever the top row happens to
    be a PENDING_APPROVAL account (no Reset Password) or a user with no role
    assignment (no Revoke) — a silent loss of coverage while real data exists
    further down the list. Walk the rows instead and only skip when none
    qualifies.
    """
    _open_users_tab(page)
    rows = page.locator(".admin-table tbody tr.clickable-row")
    try:
        rows.first.wait_for(state="visible", timeout=10_000)
    except Exception:
        pytest.skip("no user accounts in the fixture DB to select")

    total = min(rows.count(), max_rows)
    # The users detail view is `activeTab === 'detail'`; its "← Back to list"
    # anchor is the first .back-link in admin.html and the stable signal that
    # the detail render (an extra fetch) has actually landed — wait_for_alpine
    # alone returns too early and the action buttons look absent.
    back = page.locator("a.back-link").first
    for i in range(total):
        rows.nth(i).click()
        try:
            back.wait_for(state="visible", timeout=10_000)
        except Exception:
            continue
        wait_for_alpine(page)
        trigger = page.get_by_role("button", name=action_name, exact=exact)
        try:
            trigger.first.wait_for(state="visible", timeout=2_000)
            return trigger
        except Exception:
            pass
        back.click()
        wait_for_alpine(page)
        rows.first.wait_for(state="visible", timeout=10_000)
    pytest.skip(f"no user account in the first {total} rows offers '{action_name}'")


# ── Create Account / Restore Access ────────────────────────────────────────


def test_create_account_modal_opens(admin_console):
    """"+ Create Account" opens the account modal with its search step."""
    page = admin_console
    _open_users_tab(page)
    trigger = page.get_by_role("button", name="Create Account")
    if trigger.count() == 0:
        pytest.skip("current admin lacks canCreateAccounts (no + Create Account)")
    trigger.first.click()
    modal = page.locator(".modal-overlay .modal-card")
    expect(modal).to_be_visible(timeout=10_000)
    # Step 1 is a person search; the search input is the stable inner hook.
    expect(modal.locator("input[x-model='cazSearch']")).to_be_visible()


# ── Reset Password ──────────────────────────────────────────────────────────


def test_reset_password_modal_opens(admin_console):
    """Selecting a user then "Reset Password" opens the reset modal."""
    page = admin_console
    trigger = _select_user_with_action(page, "Reset Password")
    trigger.first.click()
    modal = page.locator(".modal-overlay .modal-card")
    expect(modal).to_be_visible(timeout=10_000)
    expect(modal.get_by_role("heading", name="Reset Password")).to_be_visible()
    expect(modal.locator("input[x-model='resetForm.new_password']")).to_be_visible()


# ── Revoke Role → shared confirm dialog ────────────────────────────────────


def test_revoke_role_opens_shared_confirm_dialog(admin_console):
    """"Revoke" on a role assignment routes through the shared #nss-dialog."""
    page = admin_console
    revoke = _select_user_with_action(page, "Revoke", exact=True)
    revoke.first.click()
    overlay = page.locator("#nss-dialog-overlay")
    expect(overlay).to_be_visible(timeout=10_000)
    expect(page.locator("#nss-dialog-title")).to_have_text("Revoke Role")
    # Dismiss without acting — this test asserts routing, not the DELETE.
    page.locator("#nss-dialog-actions button", has_text="Cancel").first.click()


# ── Claim reject: remarks are mandatory ────────────────────────────────────


def test_claim_reject_requires_remarks(admin_console):
    """
    The claim "Reject" button stays disabled until Admin Remarks are entered
    (`:disabled="... || !adminRemarks.trim()"`). This locks the "no silent
    rejection" business rule in at the UI.
    """
    page = admin_console
    click_nav_item(page, "Registration Approvals")
    wait_for_alpine(page)
    # Default filter is PENDING. `.admin-table tbody tr` matches every panel's
    # table (most of them hidden), so target the claims row's own "View →"
    # button — the only one in admin.html — which is unique to this table.
    rows = page.locator("button.btn-action", has_text="View →")
    try:
        rows.first.wait_for(state="visible", timeout=10_000)
    except Exception:
        pytest.skip("no pending registration claims in the fixture DB")
    rows.first.click()
    wait_for_alpine(page)

    reject = page.get_by_role("button", name="Reject", exact=True)
    remarks = page.locator("textarea[x-model='adminRemarks']")
    if reject.count() == 0 or remarks.count() == 0:
        pytest.skip("selected claim is not PENDING (no reject-with-remarks pane)")

    expect(reject.first).to_be_disabled()
    remarks.first.fill("Duplicate of an existing active membership.")
    expect(reject.first).to_be_enabled()
