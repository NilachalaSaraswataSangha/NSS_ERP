"""
UI tests for the shared NSS date picker (nssDatePicker).

Every date field in the app is the same component: the Alpine factory in
`frontend/assets/js/nss-datepicker.js` plus one canonical block of markup
that the same file injects into each `x-data="nssDatePicker(...)"` root on
DOMContentLoaded (before Alpine starts). Callsites declare only the model
path and a label.

Before this was shared, the input/popup markup was hand-copied at ten
callsites and had drifted: only the Create Person DOB field rendered the
validation error, register.html used a different input class, and some
copies were missing the Today/Clear footer. These tests lock the shared
behaviour in so the copies cannot silently diverge again.

The injector stamps `data-nss-dp="<model path>"` on each picker root, which
is the stable hook these tests (and the register/dashboard tests) locate by
— rather than substring-matching the x-data text, which breaks as soon as a
picker takes a second argument such as `{ maxToday: true }`.

Note on reachability: 9 of the 10 pickers sit inside Alpine
`<template x-if/x-for>` blocks, so they only enter the live DOM once their
tab/section is open. The browser tests below therefore assert completeness
for whatever pickers are *rendered*, plus targeted navigation tests for the
important ones; `TestNoHandwrittenMarkupInSource` covers all ten callsites
at the source level, including the ones no test navigates to.

Fixtures used:
  - page / base_url: unauthenticated pages (register)
  - admin_page: pre-authenticated admin browser page (SS1)
"""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

from tests.ui.conftest import wait_for_alpine, click_nav_item


pytestmark = pytest.mark.ui

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND = REPO_ROOT / "frontend"
PAGES_WITH_PICKERS = ["admin.html", "register.html", "dashboard.html"]

# Every part of the canonical markup that must be present in a picker.
REQUIRED_PARTS = {
    "text input": 'input[x-model="display"]',
    "calendar icon": ".nss-dp-icon",
    "popup": ".nss-cal-popup",
    "month/prev/next nav": "button.nss-cal-nav",
    "month select": "select.nss-cal-select",
    "year input": "input.nss-cal-year",
    "weekday header": ".nss-cal-weekdays",
    "day grid": ".nss-cal-days",
    "Today button": ".nss-cal-today-btn",
    "Clear button": ".nss-cal-clear",
    "error hint": ".nss-dp-error",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _picker(scope, model):
    return scope.locator(f'[data-nss-dp="{model}"]')


def _assert_shared_markup(scope, model):
    """The named picker must exist and carry the full canonical markup."""
    root = _picker(scope, model)
    assert root.count() > 0, (
        f"No picker found for model '{model}' — nssDatePickerExpand() did not "
        "reach it (it may be inside a <template> the injector failed to "
        "recurse into)"
    )
    root = root.first
    missing = [
        name for name, sel in REQUIRED_PARTS.items()
        if root.locator(sel).count() == 0
    ]
    assert not missing, (
        f"Picker '{model}' is missing shared markup: {missing}. "
        "It should be built by nssDatePickerExpand(), not hand-written."
    )


def _assert_all_rendered_pickers_complete(scope, where):
    """Whatever pickers are currently in the live DOM must all be complete."""
    roots = scope.locator("[data-nss-dp]")
    count = roots.count()
    assert count > 0, f"No date pickers rendered on {where}"
    for i in range(count):
        root = roots.nth(i)
        model = root.get_attribute("data-nss-dp")
        missing = [
            name for name, sel in REQUIRED_PARTS.items()
            if root.locator(sel).count() == 0
        ]
        assert not missing, (
            f"{where}: picker '{model}' is missing shared markup: {missing}"
        )


def _open_popup(page, scope, model):
    root = _picker(scope, model).first
    root.locator(".nss-dp-icon").click()
    popup = root.locator(".nss-cal-popup")
    popup.wait_for(state="visible", timeout=5000)
    return root, popup


def _set_month_year(page, popup, month_index, year):
    popup.locator("select.nss-cal-select").select_option(str(month_index))
    popup.locator("input.nss-cal-year").fill(str(year))
    page.wait_for_timeout(150)


def _open_create_person_form(admin_page, base_url):
    """Create Person tab, with the collapsible New Person form expanded."""
    admin_page.goto(f"{base_url}/admin")
    wait_for_alpine(admin_page)
    click_nav_item(admin_page, "Create Person")
    admin_page.wait_for_timeout(1000)

    toggle = admin_page.locator('button:has-text("Create New Person")')
    if toggle.count() > 0 and toggle.first.is_visible():
        toggle.first.click()
        admin_page.wait_for_timeout(400)


# ---------------------------------------------------------------------------
# Tests — source-level invariant (covers all ten callsites, no browser)
# ---------------------------------------------------------------------------

class TestNoHandwrittenMarkupInSource:
    """The calendar markup must exist in exactly one place: the shared
    nssDatePickerMarkup() in nss-datepicker.js. Any calendar markup back in
    an HTML page means a callsite has been hand-written again and will drift.

    This is the only check that covers all ten callsites, including pickers
    that no browser test navigates to.
    """

    CALENDAR_MARKERS = [
        "nss-cal-popup",
        "nss-cal-weekdays",
        "nss-cal-days",
        "calBlanks",
        "calDays",
        "nss-cal-today-btn",
    ]

    @pytest.mark.parametrize("filename", PAGES_WITH_PICKERS)
    def test_page_has_no_calendar_markup(self, filename):
        src = (FRONTEND / filename).read_text()
        found = [m for m in self.CALENDAR_MARKERS if m in src]
        assert not found, (
            f"{filename} contains hand-written calendar markup {found}. "
            "Date fields must declare only x-data=\"nssDatePicker(...)\" plus "
            "a label; the markup is injected by nss-datepicker.js."
        )

    @pytest.mark.parametrize("filename", PAGES_WITH_PICKERS)
    def test_every_picker_declares_only_a_label(self, filename):
        """Each picker root should be a declaration + label, nothing else."""
        src = (FRONTEND / filename).read_text()
        assert 'x-data="nssDatePicker(' in src, (
            f"{filename} is expected to contain at least one date picker"
        )
        # No picker should carry an input of its own any more.
        for line in src.splitlines():
            if 'x-data="nssDatePicker(' in line:
                assert 'x-model="display"' not in line, (
                    f"{filename}: picker declares its own input — "
                    "the shared markup supplies it"
                )

    def test_shared_source_owns_the_markup(self):
        """The shared component must still provide the full markup."""
        src = (FRONTEND / "assets" / "js" / "nss-datepicker.js").read_text()
        for marker in self.CALENDAR_MARKERS:
            assert marker in src, (
                f"nss-datepicker.js no longer emits '{marker}' — the shared "
                "calendar markup is incomplete"
            )
        assert "nssDatePickerExpand" in src
        assert "DOMContentLoaded" in src, (
            "The injector must run on DOMContentLoaded, before Alpine starts"
        )


# ---------------------------------------------------------------------------
# Tests — the shared markup reaches rendered callsites
# ---------------------------------------------------------------------------

class TestSharedMarkupInjection:
    """nssDatePickerExpand() must reach pickers inside Alpine templates.

    querySelectorAll does NOT descend into <template> content, so the
    injector recurses into template.content explicitly. A regression there
    would leave those fields as a bare label with no input at all.
    """

    def test_register_dob_built(self, page: Page, base_url):
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        _assert_shared_markup(page, "form.date_of_birth")

    def test_register_all_rendered_pickers_complete(self, page: Page, base_url):
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        _assert_all_rendered_pickers_complete(page, "register")

    def test_register_dob_keeps_page_input_class(self, page: Page, base_url):
        """register.html opts into .reg-input via data-dp-input-class, so the
        shared markup must honour the override instead of forcing
        .nss-dp-input."""
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        dob_input = _picker(page, "form.date_of_birth").first.locator(
            'input[x-model="display"]'
        )
        expect(dob_input).to_have_class("reg-input")

    def test_register_dob_has_exactly_one_popup(self, page: Page, base_url):
        """Two calendars in one picker is the signature of hand-written
        markup surviving alongside the injected copy."""
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        root = _picker(page, "form.date_of_birth").first
        assert root.locator(".nss-cal-popup").count() == 1

    def test_admin_create_person_dob_built(self, admin_page: Page, base_url):
        """A picker nested inside the Create Person tab template."""
        _open_create_person_form(admin_page, base_url)
        _assert_shared_markup(admin_page, "newPersonForm.date_of_birth")

    def test_admin_all_rendered_pickers_complete(self, admin_page: Page, base_url):
        _open_create_person_form(admin_page, base_url)
        _assert_all_rendered_pickers_complete(admin_page, "admin")

    def test_dashboard_profile_dob_built(self, admin_page: Page, base_url):
        """The edit-profile DOB picker, revealed by clicking Edit."""
        admin_page.goto(f"{base_url}/dashboard")
        wait_for_alpine(admin_page)
        admin_page.wait_for_timeout(1500)

        edit_btn = admin_page.locator("button:has-text('Edit')").first
        if edit_btn.count() == 0:
            pytest.skip("Edit profile button not available")
        edit_btn.click()
        admin_page.wait_for_timeout(600)

        _assert_shared_markup(admin_page, "profileForm.date_of_birth")


# ---------------------------------------------------------------------------
# Tests — calendar mechanics
# ---------------------------------------------------------------------------

class TestCalendarGrid:
    """Day count and leading-blank offset must track the selected month AND
    year — the behaviour the Create Person DOB field already had and which
    is now shared by every date field."""

    # (month_index, year, expected_days, expected_leading_blanks)
    GRID_CASES = [
        (1, 2024, 29, 4),   # Feb 2024 — leap year, 1st is a Thursday
        (1, 2023, 28, 3),   # Feb 2023 — non-leap, 1st is a Wednesday
        (8, 2025, 30, 1),   # Sep 2025 — 1st is a Monday
        (0, 2026, 31, 4),   # Jan 2026 — 1st is a Thursday
    ]

    @pytest.mark.parametrize("month,year,exp_days,exp_blanks", GRID_CASES)
    def test_grid_matches_month_and_year(
        self, page: Page, base_url, month, year, exp_days, exp_blanks
    ):
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        _root, popup = _open_popup(page, page, "form.date_of_birth")
        _set_month_year(page, popup, month, year)

        assert popup.locator(".nss-cal-day").count() == exp_days, (
            f"{year}-{month + 1:02d} should render {exp_days} days"
        )
        # Leading blanks are bare <span> placeholders before day 1; the day
        # cells themselves are <button>, so a child-span count isolates them.
        assert popup.locator(".nss-cal-days > span").count() == exp_blanks, (
            f"{year}-{month + 1:02d} should have {exp_blanks} leading blanks "
            "so day 1 lands under its real weekday"
        )

    def test_prev_next_month_wraps_year(self, page: Page, base_url):
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        _root, popup = _open_popup(page, page, "form.date_of_birth")
        _set_month_year(page, popup, 0, 2020)  # January 2020

        popup.locator("button.nss-cal-nav").first.click()  # prev -> Dec 2019
        page.wait_for_timeout(200)
        expect(popup.locator("select.nss-cal-select")).to_have_value("11")
        expect(popup.locator("input.nss-cal-year")).to_have_value("2019")

        popup.locator("button.nss-cal-nav").last.click()  # next -> Jan 2020
        page.wait_for_timeout(200)
        expect(popup.locator("select.nss-cal-select")).to_have_value("0")
        expect(popup.locator("input.nss-cal-year")).to_have_value("2020")


class TestDateSelection:
    """Picking a day writes DD/MM/YYYY to the visible input."""

    def test_select_day_fills_display(self, page: Page, base_url):
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        root, popup = _open_popup(page, page, "form.date_of_birth")
        _set_month_year(page, popup, 1, 2024)

        popup.locator(".nss-cal-day", has_text="29").first.click()
        page.wait_for_timeout(250)

        expect(root.locator('input[x-model="display"]')).to_have_value("29/02/2024")
        # Popup closes on selection.
        expect(popup).to_be_hidden(timeout=5000)

    def test_clear_button_empties_field(self, page: Page, base_url):
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        root, popup = _open_popup(page, page, "form.date_of_birth")
        _set_month_year(page, popup, 1, 2024)
        popup.locator(".nss-cal-day", has_text="15").first.click()
        page.wait_for_timeout(250)

        dob_input = root.locator('input[x-model="display"]')
        expect(dob_input).to_have_value("15/02/2024")

        root.locator(".nss-dp-icon").click()
        popup.wait_for(state="visible", timeout=5000)
        popup.locator(".nss-cal-clear").click()
        page.wait_for_timeout(250)
        expect(dob_input).to_have_value("")

    def test_typed_date_auto_slashes(self, page: Page, base_url):
        """onInput() inserts the DD/MM/ separators as digits are typed."""
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        dob_input = _picker(page, "form.date_of_birth").first.locator(
            'input[x-model="display"]'
        )
        dob_input.click()
        dob_input.type("15081990")
        page.wait_for_timeout(250)
        expect(dob_input).to_have_value("15/08/1990")


class TestValidationFeedback:
    """The shared markup always renders .nss-dp-error, so a rejected date
    explains itself. Previously only the Create Person DOB field did, and
    every other field silently refused the value with no visible reason."""

    def _type_dob(self, page, base_url, digits):
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        root = _picker(page, "form.date_of_birth").first
        dob_input = root.locator('input[x-model="display"]')
        dob_input.click()
        dob_input.type(digits)
        page.wait_for_timeout(300)
        return root

    def test_future_dob_shows_reason(self, page: Page, base_url):
        root = self._type_dob(page, base_url, "31122099")
        error = root.locator(".nss-dp-error")
        expect(error).to_be_visible(timeout=5000)
        assert "future" in (error.text_content() or "").lower(), (
            "A future date of birth should be rejected with a stated reason"
        )

    def test_impossible_date_shows_reason(self, page: Page, base_url):
        """31 February is a complete but non-existent date."""
        root = self._type_dob(page, base_url, "31021990")
        error = root.locator(".nss-dp-error")
        expect(error).to_be_visible(timeout=5000)
        assert "calendar" in (error.text_content() or "").lower()

    def test_out_of_range_month_shows_reason(self, page: Page, base_url):
        """Segment-level validation warns before the full date is typed."""
        root = self._type_dob(page, base_url, "0119")
        error = root.locator(".nss-dp-error")
        expect(error).to_be_visible(timeout=5000)
        assert "month" in (error.text_content() or "").lower()

    def test_valid_date_shows_no_error(self, page: Page, base_url):
        root = self._type_dob(page, base_url, "15081990")
        expect(root.locator(".nss-dp-error")).to_be_hidden()

    def test_non_dob_picker_allows_future_date(self, page: Page, base_url):
        """maxToday is opt-in. form.joining_date does not pass it, so a
        future joining date must be accepted without an error.

        Skips when the picker is not rendered — it lives inside
        <template x-if="form.has_membership"> + x-if="form.organization_pk",
        so it requires a membership claim with a Sakha selected.
        """
        page.goto(f"{base_url}/register")
        wait_for_alpine(page)
        root = _picker(page, "form.joining_date")
        if root.count() == 0:
            pytest.skip(
                "Joining-date picker not rendered — needs a membership claim "
                "with a Sakha selected (covered in test_ui_06_register_submit)"
            )

        joining_input = root.first.locator('input[x-model="display"]')
        joining_input.click()
        joining_input.type("31122099")
        page.wait_for_timeout(300)

        expect(root.first.locator(".nss-dp-error")).to_be_hidden()
        expect(joining_input).to_have_value("31/12/2099")


class TestAdminCreatePersonDatePicker:
    """The Create Person DOB field was the reference implementation — it must
    keep working now that its markup comes from the shared source."""

    def test_create_person_dob_grid_and_selection(self, admin_page: Page, base_url):
        _open_create_person_form(admin_page, base_url)

        model = "newPersonForm.date_of_birth"
        _assert_shared_markup(admin_page, model)
        root, popup = _open_popup(admin_page, admin_page, model)

        _set_month_year(admin_page, popup, 1, 2024)
        assert popup.locator(".nss-cal-day").count() == 29
        assert popup.locator(".nss-cal-days > span").count() == 4

        popup.locator(".nss-cal-day", has_text="29").first.click()
        admin_page.wait_for_timeout(250)
        expect(root.locator('input[x-model="display"]')).to_have_value("29/02/2024")

    def test_create_person_dob_rejects_future(self, admin_page: Page, base_url):
        """Create Person DOB passes maxToday, so a future date is refused
        with a visible reason."""
        _open_create_person_form(admin_page, base_url)

        root = _picker(admin_page, "newPersonForm.date_of_birth").first
        dob_input = root.locator('input[x-model="display"]')
        dob_input.click()
        dob_input.type("31122099")
        admin_page.wait_for_timeout(300)

        expect(root.locator(".nss-dp-error")).to_be_visible(timeout=5000)
