"""
UI tests for family management (dashboard.html Family tab).

Family management lives only on the member dashboard (`dashboard.html`, tab
`family`) — the tree was moved out of admin.html per README. The coverage-gap
audit flagged the write flows here as untested:

  * Create-family modal      (`showCreateFamilyModal`)
  * Add-member modal          (`showAddMemberModal`)
  * Member-action confirms — Make Head / Assign Admin / Revoke Admin / Remove,
    all routed through the shared `#nss-dialog-*` confirm dialog.

These flows depend on the logged-in user's family state (whether they have a
family, are its head/admin, and the members present). The `admin_page` fixture
(SS1) may or may not have a family in a given fixture DB, so each test is
precondition-guarded: it navigates to the real Family tab and `pytest.skip`s
when the entry control isn't present, asserting against the real DOM otherwise.

Verified selectors (dashboard.html / dashboard.js / nss-dialog.js):
  * Family tab       : `.nav-item` "Family", `@click="switchTab('family')"`
  * create trigger   : "Create My Family" (empty state) / "Own Family" pill,
                       both `@click="showCreateFamilyModal = true; ..."`
  * create modal     : `<template x-if="showCreateFamilyModal">`; h3
                       "Create My Family"; name input placeholder "e.g. Panda
                       Paribara"; Sakha `select.nss-select`; datepicker
                       `nssDatePicker('createFamilyFormedDate')`
  * add trigger      : "Add" pill `@click="openAddMemberModal()"` (needs
                       canManageMembers)
  * add modal        : `<template x-if="showAddMemberModal">`; header "Add
                       Member to Family"; search `input.nss-search-input`
                       `x-model="addMemberSearch"`
  * member actions   : head-only kebab `.dropdown.dropdown-end`; "Make Head"
                       → `#nss-dialog-title` "Transfer Headship" (confirm
                       "Transfer"); "Assign Admin"/"Revoke Admin"/"Remove"
                       likewise

Requires a live server + Postgres (BASE_URL http://127.0.0.1:8001).
"""

import pytest
from playwright.sync_api import expect

from tests.ui.conftest import wait_for_alpine, click_nav_item

pytestmark = pytest.mark.ui


@pytest.fixture
def family_tab(admin_page, base_url):
    """admin_page (SS1) on the dashboard Family tab, Alpine ready."""
    admin_page.goto(f"{base_url}/dashboard")
    wait_for_alpine(admin_page)
    click_nav_item(admin_page, "Family")
    wait_for_alpine(admin_page)
    # The family tab body renders once (tree, member list, or empty state).
    expect(admin_page.locator("[x-show=\"tab === 'family'\"]").first) \
        .to_be_visible(timeout=10_000)
    return admin_page


# ── Create-family modal ─────────────────────────────────────────────────────


def test_create_family_modal_opens(family_tab):
    """
    "Create My Family" / "Own Family" opens the create-family modal with its
    name field, Sakha select, and the shared date picker.
    """
    page = family_tab
    trigger = page.get_by_role("button", name="Create My Family")
    if trigger.count() == 0:
        trigger = page.get_by_role("button", name="Own Family")
    if trigger.count() == 0:
        pytest.skip("no create-family entry (user already has a family, or no perm)")
    trigger.first.click()
    wait_for_alpine(page)
    # Modal is text-keyed (no id). The title is unique enough to anchor on.
    dialog = page.get_by_role("heading", name="Create My Family")
    expect(dialog).to_be_visible(timeout=10_000)
    expect(page.locator("input[placeholder*='Paribara']")).to_be_visible()
    expect(page.locator("select.nss-select").first).to_be_visible()
    # The formed-date field is the shared picker, located by its stable hook.
    expect(page.locator("[data-nss-dp='createFamilyFormedDate']")).to_be_visible()


# ── Add-member modal ────────────────────────────────────────────────────────


def test_add_member_modal_opens(family_tab):
    """The "Add" pill opens the add-member modal with the person search step."""
    page = family_tab
    trigger = page.get_by_role("button", name="Add", exact=True)
    if trigger.count() == 0:
        pytest.skip("no Add-member control (no family, or lacks canManageMembers)")
    trigger.first.click()
    wait_for_alpine(page)
    expect(page.get_by_role("heading", name="Add Member to Family")) \
        .to_be_visible(timeout=10_000)
    expect(page.locator("input[x-model='addMemberSearch']")).to_be_visible()


# ── Member-action confirm dialogs ───────────────────────────────────────────


@pytest.mark.parametrize(
    "action_link,dialog_title",
    [
        ("Make Head", "Transfer Headship"),
        ("Assign Admin", "Assign Admin"),
        ("Revoke Admin", "Revoke Admin"),
        ("Remove", "Remove Member"),
    ],
)
def test_member_action_opens_confirm_dialog(family_tab, action_link, dialog_title):
    """
    Each head/admin member action routes through the shared confirm dialog
    (`#nss-dialog-*`). The kebab menu only renders for the current head, so
    skip when the action isn't available in this fixture DB.
    """
    page = family_tab
    kebab = page.locator(".dropdown.dropdown-end")
    if kebab.count() == 0:
        pytest.skip("no head-only member-action menu (viewer is not family head)")
    kebab.first.click()
    link = page.get_by_role("link", name=action_link, exact=True)
    if link.count() == 0:
        pytest.skip(f"'{action_link}' not offered for the current member/role state")
    link.first.click()
    overlay = page.locator("#nss-dialog-overlay")
    expect(overlay).to_be_visible(timeout=10_000)
    expect(page.locator("#nss-dialog-title")).to_have_text(dialog_title)
    # Dismiss without acting — assert routing, not the mutation.
    page.locator("#nss-dialog-actions button", has_text="Cancel").first.click()
