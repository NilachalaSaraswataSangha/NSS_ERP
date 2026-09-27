"""
NSS ERP — UI tests for the Admin Create Person form (/admin).

Verifies person search, person selection, new person form toggle,
mandatory field validation, and gender dropdown on the Create tab.

Alpine.js app: adminApp()
Tab: activeTab = 'create'
"""

import pytest
from playwright.sync_api import expect
from tests.ui.conftest import wait_for_alpine, click_nav_item

pytestmark = pytest.mark.ui


# ── Helper ───────────────────────────────────────────────────────────


def _go_to_create_tab(admin_page, base_url):
    """Navigate to admin page and switch to the Create tab."""
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    click_nav_item(admin_page, "Create Person")
    admin_page.locator('[x-show="activeTab === \'create\'"]').wait_for(state="visible", timeout=5000)
    admin_page.wait_for_timeout(500)


def _get_create_tab(admin_page):
    """Return the scoped Create tab container locator."""
    return admin_page.locator('[x-show="activeTab === \'create\'"]')


def _search_person(admin_page, query: str):
    """Fill person search and click Search within the Create tab."""
    tab = _get_create_tab(admin_page)
    search_input = tab.locator('[x-model="personSearchQuery"]')
    search_input.fill(query)
    tab.locator('.btn-action.primary:has-text("Search")').click()
    admin_page.wait_for_timeout(1000)


# ── Create tab loads ─────────────────────────────────────────────────


def test_create_tab_loads(admin_page, base_url):
    """Switching to the Create tab shows the person search form."""
    _go_to_create_tab(admin_page, base_url)

    tab = _get_create_tab(admin_page)
    person_search = tab.locator('[x-model="personSearchQuery"]')
    expect(person_search).to_be_visible()


# ── Person search ────────────────────────────────────────────────────


def test_person_search_works(admin_page, base_url):
    """Typing a name and clicking Search returns person results."""
    _go_to_create_tab(admin_page, base_url)
    _search_person(admin_page, "Admin")

    tab = _get_create_tab(admin_page)
    results = tab.locator("table tbody tr")
    assert results.count() >= 1, "Person search should return at least one result"


# ── Person search minimum characters ────────────────────────────────


def test_person_search_min_chars(admin_page, base_url):
    """Searching with fewer than 2 characters shows an error or no results."""
    _go_to_create_tab(admin_page, base_url)

    tab = _get_create_tab(admin_page)
    search_input = tab.locator('[x-model="personSearchQuery"]')
    search_input.fill("A")

    # The Search button should be disabled when query < 2 chars
    search_btn = tab.locator('.btn-action.primary:has-text("Search")')
    is_disabled = search_btn.is_disabled()

    if is_disabled:
        assert True
    else:
        search_btn.click()
        admin_page.wait_for_timeout(500)
        results = tab.locator("table tbody tr")
        assert results.count() == 0, (
            "Single-character search should return no results"
        )


# ── Select existing person ───────────────────────────────────────────


def test_select_existing_person(admin_page, base_url):
    """Selecting a person from search results displays the selected person info."""
    _go_to_create_tab(admin_page, base_url)
    _search_person(admin_page, "Admin")

    tab = _get_create_tab(admin_page)
    select_btn = tab.locator('button:has-text("Select")').first
    expect(select_btn).to_be_visible(timeout=5000)
    select_btn.click()
    admin_page.wait_for_timeout(500)

    # After selection, createForm.person_pk is set → green display div appears
    # and the clearSelectedPerson() button becomes visible
    # (Scoped to avoid nssDatePicker's "Clear" button)
    clear_btn = tab.locator('button[\\@click="clearSelectedPerson()"]')
    expect(clear_btn).to_be_visible(timeout=5000)


# ── Clear selected person ────────────────────────────────────────────


def test_clear_selected_person(admin_page, base_url):
    """Clearing the selected person removes the selection display."""
    _go_to_create_tab(admin_page, base_url)
    _search_person(admin_page, "Admin")

    tab = _get_create_tab(admin_page)
    select_btn = tab.locator('button:has-text("Select")').first
    select_btn.click()
    admin_page.wait_for_timeout(500)

    clear_btn = tab.locator('button[\\@click="clearSelectedPerson()"]')
    expect(clear_btn).to_be_visible(timeout=5000)
    clear_btn.click()
    admin_page.wait_for_timeout(500)

    # Person search input should be visible again
    search_input = tab.locator('[x-model="personSearchQuery"]')
    expect(search_input).to_be_visible()


# ── New person form toggle ───────────────────────────────────────────


def test_new_person_form_toggle(admin_page, base_url):
    """Clicking 'Create New Person' button toggles the new person form."""
    _go_to_create_tab(admin_page, base_url)

    # Button text is dynamic: "▸ Create New Person" (rendered by x-text)
    toggle_btn = admin_page.locator('button:has-text("Create New Person")')
    expect(toggle_btn).to_be_visible(timeout=5000)
    toggle_btn.click()
    admin_page.wait_for_timeout(500)

    # New person form fields should be visible
    first_name = admin_page.locator('[x-model="newPersonForm.first_name"]')
    expect(first_name).to_be_visible(timeout=5000)

    last_name = admin_page.locator('[x-model="newPersonForm.last_name"]')
    expect(last_name).to_be_visible()


# ── Mandatory fields validation ──────────────────────────────────────


def test_new_person_mandatory_fields(admin_page, base_url):
    """Create Person button is disabled when mandatory fields are empty."""
    _go_to_create_tab(admin_page, base_url)

    # Open the new person form
    toggle_btn = admin_page.locator('button:has-text("Create New Person")')
    toggle_btn.click()
    admin_page.wait_for_timeout(500)

    # The Create Person submit button — disabled when required fields empty
    # Actual: :disabled="newPersonLoading || !first_name || !last_name || !dob || !gender || (!mobile && !email)"
    create_btn = admin_page.locator('.btn-action.primary:has-text("Create Person")')
    expect(create_btn).to_be_visible(timeout=5000)
    expect(create_btn).to_be_disabled()


# ── Gender dropdown ──────────────────────────────────────────────────


def test_new_person_form_has_gender_dropdown(admin_page, base_url):
    """Gender dropdown is present in the new person form and has options."""
    _go_to_create_tab(admin_page, base_url)

    # Open the new person form
    toggle_btn = admin_page.locator('button:has-text("Create New Person")')
    toggle_btn.click()
    admin_page.wait_for_timeout(500)

    gender_select = admin_page.locator('select[x-model="newPersonForm.gender_master_data_pk"]')
    expect(gender_select).to_be_visible(timeout=5000)

    # Wait for gender options to load (async from master data API)
    admin_page.wait_for_function(
        "document.querySelector('select[x-model=\"newPersonForm.gender_master_data_pk\"]').options.length > 1",
        timeout=10000
    )

    options = gender_select.locator("option")
    assert options.count() >= 2, "Gender dropdown should have at least one selectable option"
