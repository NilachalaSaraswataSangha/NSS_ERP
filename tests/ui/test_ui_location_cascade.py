"""
UI tests for the shared location cascade (nss-location.js).

`NSSLocation.create()` backs the country → state → district → postal-code
dropdowns on register.html (unauthenticated `/api/v1/register/*` endpoints) and
in admin.html's org create/edit forms (authenticated `/api/v1/foundation/*`).
Only the country → state hop had any coverage; the district and postal-code
hops, and the reset semantics that keep a form from submitting a stale PIN
against a new state, had none.

The cascade takes the Alpine component as an explicit `ctx` argument and is
otherwise stateless, so it can be driven directly in the page with a stub
`fetchFn` that records the URLs it is asked for. That makes these tests
deterministic — they assert the cascade's contract, not whichever geography rows
happen to be seeded.

The regression these lock in particular: `_clearPostalCode()` must clear
`postal_code_value` (the key register.js and admin.js actually use), not only
the `postal_code_pk` this module was originally written against — otherwise a
PIN typed for one state survives a switch to another.

Requires a live server (BASE_URL http://127.0.0.1:8001) to serve the page; no
login and no geography data needed. Run with:
    python3 -m pytest tests/ui/test_ui_location_cascade.py
"""

import pytest
from playwright.sync_api import Page

pytestmark = pytest.mark.ui


# Builds a cascade whose fetchFn records calls and replies with canned rows, runs
# the requested method, and hands back the resulting ctx + call log.
_DRIVE = """
async ({ method, arg, form, basePath }) => {
    const calls = [];
    const fetchFn = (url) => {
        calls.push(url);
        let rows = [];
        if (url.includes('/countries')) rows = [{ country_pk: 1, country_name: 'India' }];
        if (url.includes('/states')) rows = [{ state_pk: 10, state_name: 'Odisha' }];
        if (url.includes('/districts')) rows = [{ district_pk: 100, district_name: 'Khordha' }];
        if (url.includes('/postal-codes')) rows = [{ postal_code_pk: 1000, postal_code: '751001' }];
        return Promise.resolve({ ok: true, json: () => Promise.resolve(rows) });
    };
    const cascade = NSSLocation.create({
        fetchFn,
        basePath,
        arrays: {
            countries: 'regCountries',
            states: 'regStates',
            districts: 'regDistricts',
            postalCodes: 'regPostalCodes',
        },
        form: 'form',
    });
    const ctx = {
        regCountries: ['stale'],
        regStates: ['stale'],
        regDistricts: ['stale'],
        regPostalCodes: ['stale'],
        form,
    };
    await cascade[method](ctx, arg);
    // onCountryChange/onStateChange kick off their loads without awaiting, so
    // give the microtask queue a turn before reading the result.
    await new Promise(r => setTimeout(r, 0));
    return {
        calls,
        form: ctx.form,
        countries: ctx.regCountries,
        states: ctx.regStates,
        districts: ctx.regDistricts,
        postalCodes: ctx.regPostalCodes,
    };
}
"""


def _full_form(**overrides):
    """A form carrying every cascade-owned field, populated with stale values."""
    form = {
        "country_pk": 1,
        "state_pk": 10,
        "district_pk": 100,
        "city_village_name": "Bhubaneswar",
        "postal_code_value": "751001",
    }
    form.update(overrides)
    return form


@pytest.fixture
def location_page(page: Page, base_url):
    """register.html loads nss-location.js and needs no authentication."""
    page.goto(f"{base_url}/register")
    page.wait_for_function("() => typeof NSSLocation !== 'undefined'", timeout=10_000)
    return page


def _drive(page, method, arg=None, form=None, base_path="/api/v1/register"):
    return page.evaluate(_DRIVE, {
        "method": method,
        "arg": arg,
        "form": form if form is not None else _full_form(),
        "basePath": base_path,
    })


# ── Loaders ─────────────────────────────────────────────────────────────────


class TestCascadeLoaders:

    def test_load_districts_queries_by_state_and_stores_rows(self, location_page):
        res = _drive(location_page, "loadDistricts", 10)
        assert res["calls"] == ["/api/v1/register/districts?state_pk=10"], res["calls"]
        assert res["districts"] == [{"district_pk": 100, "district_name": "Khordha"}]

    def test_load_postal_codes_queries_by_state_and_stores_rows(self, location_page):
        res = _drive(location_page, "loadPostalCodes", 10)
        assert res["calls"] == ["/api/v1/register/postal-codes?state_pk=10"], res["calls"]
        assert res["postalCodes"] == [{"postal_code_pk": 1000, "postal_code": "751001"}]

    @pytest.mark.parametrize("method,array", [
        ("loadDistricts", "districts"),
        ("loadPostalCodes", "postalCodes"),
        ("loadStates", "states"),
    ])
    def test_loader_clears_its_array_and_skips_the_call_without_a_parent(
        self, location_page, method, array
    ):
        """
        A cleared parent select must empty the child list rather than leave the
        previous state's rows on screen, and must not fire a request with an
        empty query param.
        """
        res = _drive(location_page, method, None)
        assert res["calls"] == [], f"{method} fired a request with no parent PK"
        assert res[array] == [], res[array]

    def test_load_states_also_clears_the_two_levels_below_it(self, location_page):
        """Changing country invalidates district and postal code as well."""
        res = _drive(location_page, "loadStates", 1)
        assert res["calls"] == ["/api/v1/register/states?country_pk=1"], res["calls"]
        assert res["states"] == [{"state_pk": 10, "state_name": "Odisha"}]
        assert res["districts"] == []
        assert res["postalCodes"] == []

    def test_base_path_defaults_to_foundation(self, location_page):
        """
        admin.js relies on the default; register.js overrides it because the
        person filling that page has no JWT yet.
        """
        res = location_page.evaluate(_DRIVE, {
            "method": "loadDistricts", "arg": 10,
            "form": _full_form(), "basePath": None,
        })
        assert res["calls"] == ["/api/v1/foundation/districts?state_pk=10"], res["calls"]


# ── Change handlers: reset semantics ────────────────────────────────────────


class TestCascadeResets:

    def test_country_change_clears_every_level_below(self, location_page):
        res = _drive(location_page, "onCountryChange")
        f = res["form"]
        assert f["state_pk"] == ""
        assert f["district_pk"] == ""
        assert f["city_village_name"] == ""
        assert f["postal_code_value"] == "", (
            "a PIN typed for the previous country survived the switch"
        )
        assert res["calls"] == ["/api/v1/register/states?country_pk=1"], res["calls"]

    def test_state_change_clears_district_city_and_postal_code(self, location_page):
        res = _drive(location_page, "onStateChange")
        f = res["form"]
        assert f["district_pk"] == ""
        assert f["city_village_name"] == ""
        assert f["postal_code_value"] == "", (
            "postal_code_value is the key both consumers use; clearing only "
            "postal_code_pk was the silent no-op that let a stale PIN submit"
        )

    def test_state_change_loads_districts_and_postal_codes(self, location_page):
        """One state change must populate BOTH child lists, not just districts."""
        res = _drive(location_page, "onStateChange")
        assert sorted(res["calls"]) == sorted([
            "/api/v1/register/districts?state_pk=10",
            "/api/v1/register/postal-codes?state_pk=10",
        ]), res["calls"]

    def test_state_change_with_no_state_selected_fires_nothing(self, location_page):
        res = _drive(location_page, "onStateChange", form=_full_form(state_pk=""))
        assert res["calls"] == []
        assert res["districts"] == []
        assert res["postalCodes"] == []

    def test_postal_code_pk_form_is_also_cleared(self, location_page):
        """
        The two supported key names are handled independently, so a form built
        around a postal_code_pk select is cleared too.
        """
        res = _drive(
            location_page, "onStateChange",
            form={"country_pk": 1, "state_pk": 10, "district_pk": 100,
                  "city_village_name": "X", "postal_code_pk": 1000},
        )
        assert res["form"]["postal_code_pk"] == ""

    def test_district_change_clears_only_the_city(self, location_page):
        """
        City/village is free text scoped to the district; the postal code is
        scoped to the state, so it must survive a district change.
        """
        res = _drive(location_page, "onDistrictChange")
        f = res["form"]
        assert f["city_village_name"] == ""
        assert f["district_pk"] == 100, "district_pk should not be reset by itself"
        assert f["postal_code_value"] == "751001", (
            "the postal code is state-scoped and should survive a district change"
        )
        assert res["calls"] == []
