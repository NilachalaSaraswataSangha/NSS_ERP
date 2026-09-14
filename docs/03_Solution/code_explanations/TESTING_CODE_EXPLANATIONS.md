# Testing Layer — Per-File Code Explanations

| Field       | Value                                    |
|-------------|-------------------------------------------|
| Document    | TESTING_CODE_EXPLANATIONS                 |
| Version     | 1.4                                       |
| Scope       | All pytest integration tests under `tests/` |
| Status      | Complete (updated: Tier 4 Family + Membership) |

---

## 1. Purpose of this document

This document is the authoritative, current, **per-file** reference for the NSS ERP test suite —
every file under `tests/`. For each file it gives:

- **Requirement** — why the file exists: what problem or need it addresses, and what would
  break or be missing without it.
- **Line-by-line** — a walkthrough of the actual code, block by block, naming real functions,
  variables, and line numbers, so that someone unfamiliar with the code could reconstruct its
  behaviour from the explanation alone.

**Why this is its own document, separate from `API_CODE_EXPLANATIONS.md`:** the files under
`tests/` are FastAPI `TestClient` integration tests. They exercise the API and security-middleware
layers end-to-end — router → Pydantic schema → psycopg2 → a real local PostgreSQL database, and
middleware → response headers/status — through the same ASGI app object that `uvicorn` serves in
production. They are not unit tests of isolated functions; they are the whole application's own
verification harness, spanning every other layer document (`API_CODE_EXPLANATIONS.md`,
`SECURITY_CODE_EXPLANATIONS.md`) without belonging to any single one of them — which is why
testing gets its own dedicated document rather than being folded into whichever layer happens to
be tested by the largest file.

**259 tests total** across 7 files (per `grep -rc "def test_" tests/*.py`): `test_bootstrap.py`
(21 — 9 API + 12 UI), `test_foundation.py` (59 — 46 API + 13 UI), `test_organization.py`
(64 — 35 API/hierarchy + 13 pagination + 13 UI + 3 security), `test_security.py` (8),
`test_person.py` (56 — 29 list/detail/addresses/search + 7 pagination + 15 UI + 5 security —
see the breakdown in §2.6), `test_family.py` (51 — 17 list/pagination + 5 detail + 8 members +
7 head-history + 4 security + 10 UI — see the breakdown in §2.7), plus `conftest.py`'s shared
fixture (no tests of its own).

---

## 2. Files

### 2.1 `tests/conftest.py`

*(`tests/__init__.py` is folded in here rather than given its own section: it is a single-line
comment, `# tests package`, whose only purpose — like the empty `__init__.py` files under
`api/`— is to make `tests/` importable as a package so pytest can discover and import
`tests/test_*.py` modules correctly when run from the repository root.)*

**Requirement**

Every test file needs a FastAPI `TestClient` wired to the real `api.main.app` object, and
creating a fresh `TestClient` per test would repeatedly trigger the app's lifespan
startup/shutdown for no benefit, since the underlying connection pool is already designed to be
shared. `conftest.py` supplies exactly one `client` fixture, scoped so it's created once per test
*module* and shared by every test function inside that module — this is the fixture every other
test file in `tests/` depends on via its `client` parameter.

**Line-by-line**

```python
"""
NSS ERP — Shared test fixtures.

Provides a FastAPI TestClient backed by the local PostgreSQL database.
Tests run against the same nss.* schema used by the application.

Requirements:
  - Local PostgreSQL running with nss schema bootstrapped
  - api/.env configured with DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
  - pytest + httpx installed

Usage:
  pytest                        # run all tests
  pytest -m integration         # run only integration tests
  pytest tests/test_bootstrap.py  # run specific file
"""
```

The module docstring states the fixture provides a `TestClient` "backed by the local
PostgreSQL database," that tests run "against the same nss.* schema used by the application,"
lists the three prerequisites (local Postgres bootstrapped, `api/.env` configured, `pytest` +
`httpx` installed), and gives example invocation commands.

```python
import pytest
from fastapi.testclient import TestClient

from api.main import app
```

`import pytest` provides `@pytest.fixture`. `from fastapi.testclient import TestClient` — Starlette's
test client, re-exported by FastAPI; it calls the ASGI app in-process, so no real HTTP server or
socket is involved. `from api.main import app` — the real, fully-wired FastAPI application
object — the exact same object Uvicorn would serve in production, including every router and
every piece of security middleware.

The one fixture the whole test suite depends on, lines 24–33:

```python
@pytest.fixture(scope="module")
def client():
    """
    FastAPI TestClient scoped to the test module.

    Uses the real database connection (local PostgreSQL).
    The TestClient does not start a server — it calls the ASGI app directly.
    """
    with TestClient(app) as c:
        yield c
```

`scope="module"` means one `TestClient` instance is constructed per test *file* and reused by
every test in it, rather than per individual test function; this is cheaper than
`scope="function"` while still isolating state per file. `with TestClient(app) as c:` is a
context manager that triggers the app's `lifespan` events — nothing runs at entry (the lifespan
handler in `main.py` has no startup code before its `yield`), but on exit — after all tests in
the module have run — it triggers the shutdown half of `lifespan`, i.e. `close_pool()`, cleanly
releasing every pooled database connection.

---

### 2.2 `tests/test_bootstrap.py`

**Requirement**

The 4 Tier 0 Bootstrap endpoints need automated, repeatable verification that they return the
correct shape, the correct data (8 frozen roles, specific role codes, correct `SYSTEM`-role
scoping), and the correct error codes (404 for a nonexistent role, 422 for a malformed UUID) —
otherwise a regression in `api/routers/bootstrap.py` or a change to the seed data would only be
caught by someone manually hitting the endpoints. This file is the executable specification of
the Tier 0 API contract.

**Line-by-line**

```python
"""
NSS ERP — Tier 0 Bootstrap API tests.

Four integration tests corresponding to the four Tier 0 API contracts:
  1. GET /api/v1/bootstrap/health
  2. GET /api/v1/bootstrap/roles
  3. GET /api/v1/bootstrap/permissions
  4. GET /api/v1/bootstrap/roles/{role_pk}/permissions

These tests run against local PostgreSQL (not Neon).
The database must be bootstrapped with DDL + seed before running.
"""

import pytest


pytestmark = pytest.mark.integration
```

The module docstring lists the four contracts under test and states these are integration
tests against local PostgreSQL, requiring the database to already be bootstrapped with DDL +
seed. `pytestmark = pytest.mark.integration` applies the `integration` marker to every test in
the module (equivalent to decorating each test individually), enabling `pytest -m integration`
to select just these tests.

**`class TestHealth:`** (lines 20–29)

```python
class TestHealth:
    """GET /api/v1/bootstrap/health"""

    def test_health_returns_ok(self, client):
        """Health endpoint returns 200 with status 'ok' when DB is reachable."""
        response = client.get("/api/v1/bootstrap/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
```

Calls `GET /api/v1/bootstrap/health`, asserts `status_code == 200`, and asserts the JSON body's
`data["status"] == "ok"` and `data["database"] == "connected"`. If the local PostgreSQL the test
runner is pointed at is down, this test fails by design — it's exercising the real connection,
not a mock.

**`class TestRoles:`** (lines 32–88, 4 tests)

```python
def test_roles_returns_list(self, client):
    """Roles endpoint returns a non-empty list of active roles."""
    response = client.get("/api/v1/bootstrap/roles")
    assert response.status_code == 200
    roles = response.json()
    assert isinstance(roles, list)
    assert len(roles) == 8, f"Expected 8 frozen roles, got {len(roles)}"
```

`GET /api/v1/bootstrap/roles` returns 200, the body is a `list`, and `len(roles) == 8` with a
custom failure message reporting the actual count — this pins the exact frozen-role seed count.

```python
def test_roles_have_required_fields(self, client):
    """Each role has the expected response fields."""
    response = client.get("/api/v1/bootstrap/roles")
    roles = response.json()
    required_fields = {
        "role_master_pk",
        "role_code",
        "role_name",
        "role_class",
        "scope_level",
        "display_order",
        "is_active",
    }
    for role in roles:
        assert required_fields.issubset(role.keys()), (
            f"Missing fields in role {role.get('role_code', '?')}: "
            f"{required_fields - role.keys()}"
        )
        assert role["is_active"] is True
```

Builds a `required_fields` set of the 7 fields expected on every role (`description` is
deliberately excluded from the *required* set since it's nullable/optional); for every role,
asserts `required_fields.issubset(role.keys())`, with a message naming the offending role and the
exact missing fields if it fails, and separately asserts `role["is_active"] is True` (an identity
check, not `==`, since JSON `true` deserializes to Python `True`).

```python
def test_roles_include_known_codes(self, client):
    """All 8 frozen role codes are present."""
    response = client.get("/api/v1/bootstrap/roles")
    codes = {r["role_code"] for r in response.json()}
    expected = {
        "NSS_ERP_ADMIN",
        "NSS_ERP_AUDITOR",
        "NSS_ERP_REPORT_VIEWER",
        "NSS_ERP_KENDRA_ADMIN",
        "NSS_ERP_ANCHALIKA_ADMIN",
        "NSS_ERP_ZILLA_ADMIN",
        "NSS_ERP_SAKHA_ADMIN",
        "NSS_ERP_PATHA_CHAKRA_ADMIN",
    }
    assert codes == expected, f"Role codes mismatch: {codes ^ expected}"
```

Builds `codes = {r["role_code"] for r in response.json()}` and compares it via `==` against the
literal set of all 8 expected role codes; on failure, reports `codes ^ expected` (symmetric
difference), which shows exactly which codes are extra or missing.

```python
def test_system_roles_have_nss_wide_scope(self, client):
    """SYSTEM-class roles have NSS-WIDE scope level."""
    response = client.get("/api/v1/bootstrap/roles")
    system_roles = [r for r in response.json() if r["role_class"] == "SYSTEM"]
    assert len(system_roles) == 3
    for role in system_roles:
        assert role["scope_level"] == "NSS-WIDE", (
            f"SYSTEM role {role['role_code']} has scope "
            f"'{role['scope_level']}', expected 'NSS-WIDE'"
        )
```

Filters the response to `role_class == "SYSTEM"`, asserts there are exactly 3 (`ADMIN`,
`AUDITOR`, `REPORT_VIEWER`), and asserts every one has `scope_level == "NSS-WIDE"` — encoding the
business rule that system-class roles are always organization-wide, never scoped to one
organizational tier.

**`class TestPermissions:`** (lines 91–98)

```python
class TestPermissions:
    """GET /api/v1/bootstrap/permissions"""

    def test_permissions_returns_list(self, client):
        """Permissions endpoint returns 200 with a list (may be empty in Tier 0)."""
        response = client.get("/api/v1/bootstrap/permissions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

Only asserts 200 and that the body is a `list`; deliberately does **not** assert emptiness, since
permissions will be added in later tiers and this test must keep passing when that happens.

**`class TestRolePermissions:`** (lines 101–125, 3 tests)

```python
def test_role_permissions_valid_role(self, client):
    """Requesting permissions for a valid role returns 200."""
    # First get a real role_pk
    roles_response = client.get("/api/v1/bootstrap/roles")
    roles = roles_response.json()
    assert len(roles) > 0, "No roles to test against"

    role_pk = roles[0]["role_master_pk"]
    response = client.get(f"/api/v1/bootstrap/roles/{role_pk}/permissions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

First calls `GET /api/v1/bootstrap/roles`, asserts at least one role exists, takes
`roles[0]["role_master_pk"]` as a real UUID, then calls `GET
/api/v1/bootstrap/roles/{role_pk}/permissions` and asserts 200 with a list body — no hardcoded
UUIDs anywhere, since `gen_random_uuid()` produces a different value every time the database is
seeded.

```python
def test_role_permissions_invalid_role(self, client):
    """Requesting permissions for a nonexistent role returns 404."""
    fake_pk = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/v1/bootstrap/roles/{fake_pk}/permissions")
    assert response.status_code == 404
```

Uses the well-formed-but-nonexistent UUID `00000000-0000-0000-0000-000000000000` and asserts
`status_code == 404`, exercising the router's existence check.

```python
def test_role_permissions_invalid_uuid(self, client):
    """Requesting permissions with a malformed UUID returns 422."""
    response = client.get("/api/v1/bootstrap/roles/not-a-uuid/permissions")
    assert response.status_code == 422
```

Calls the endpoint with the literal path segment `not-a-uuid` and asserts `status_code == 422`,
exercising FastAPI's own `role_pk: UUID` type-coercion failure, with no custom code involved.

---

### 2.3 `tests/test_foundation.py`

**Requirement**

The 17 Tier 1 Foundation endpoints span 4 subsystems (Master Data, System Configuration,
Geographic, Runtime) and rely on non-trivial behaviours — JOINed parent-context fields, dynamic
optional filters, business-key lookups, deliberately-empty tables, and a deliberately-absent
`change-log` endpoint — every one of which needs its own regression guard. This file is the
executable specification for the entire Tier 1 Foundation API contract, including several
contract-enforcement tests whose entire purpose is to fail loudly if someone reintroduces
something the API contract explicitly excludes (`current_value`, an anonymous `change-log`
endpoint).

**Line-by-line**

```python
"""
NSS ERP — Tier 1 Foundation API tests.

Integration tests for the 17 Foundation GET endpoints across 11 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Endpoint groups tested:
  1. Master Data:   categories, master-data
  2. System Config: settings, sequences
  3. Geographic:    countries, states, districts, cities,
                    postal-codes, postal-code-mappings
  4. Runtime:       documents

field_change_log is intentionally not exposed in Tier 1 (deferred to
Tier 5 authenticated audit API).
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/foundation"
```

The module docstring states this covers "the 17 Foundation GET endpoints across 11 tables,"
lists the four endpoint groups, and explicitly notes `field_change_log` is "not exposed in
Tier 1 (deferred to Tier 5 authenticated audit API)." `pytestmark = pytest.mark.integration` is
the same pattern as `test_bootstrap.py`. `BASE = "/api/v1/foundation"` — every test URL in the
file is built by string-formatting this constant, so a prefix change only needs to happen in
one place.

#### `TestCategories` (lines 32–77, 6 tests)

The full, representative body — the fields test also checks `is_active`:

```python
def test_list_has_required_fields(self, client):
    """Each category has the expected response fields."""
    r = client.get(f"{BASE}/categories")
    required = {
        "master_category_pk", "category_code", "category_name",
        "description", "display_order", "is_active",
    }
    for cat in r.json():
        assert required.issubset(cat.keys()), (
            f"Missing fields in category {cat.get('category_code', '?')}: "
            f"{required - cat.keys()}"
        )
        assert cat["is_active"] is True
```

Checks the 6-field `required` set against every returned category, with a failure message
naming the offending category and its missing fields, and separately asserts `is_active is True`.
The other 5 tests in this class follow the same list/detail/404/422 shape and differ only in what
they pin down:

| Test | Lines | What it checks |
|---|---|---|
| `test_list_returns_200` | 35–41 | `GET /categories` → 200, list, `len(data) > 0` ("Expected seeded categories") |
| `test_list_all_active` | 57–60 | re-checks `cat["is_active"] is True` standalone, for every category |
| `test_detail_valid_pk` | 62–68 | fetches the list, takes `cats[0]["master_category_pk"]`, `GET /categories/{pk}` → 200, returned `master_category_pk` matches |
| `test_detail_fake_pk_returns_404` | 70–73 | `GET /categories/00000000-0000-0000-0000-000000000000` → 404 |
| `test_detail_bad_uuid_returns_422` | 75–77 | `GET /categories/not-a-uuid` → 422 |

#### `TestMasterData` (lines 80–144, 8 tests)

`test_list_has_required_fields` (lines 91–104) checks a JOINed field set — master-data rows
carry their parent category's context inline:

```python
def test_list_has_required_fields(self, client):
    """Each master data value has expected fields including JOINed category context."""
    r = client.get(f"{BASE}/master-data")
    required = {
        "master_data_pk", "master_category_pk",
        "category_code", "category_name",
        "value_code", "value_name",
        "description", "display_order", "is_active",
    }
    for md in r.json():
        assert required.issubset(md.keys()), (
            f"Missing fields in master data {md.get('value_code', '?')}: "
            f"{required - md.keys()}"
        )
```

Three filter tests exercise the endpoint's dynamic optional filters:

```python
def test_filter_by_category_code(self, client):
    """Filtering by category_code returns only matching values."""
    # Get a known category code
    cats = client.get(f"{BASE}/categories").json()
    code = cats[0]["category_code"]
    r = client.get(f"{BASE}/master-data", params={"category_code": code})
    assert r.status_code == 200
    for md in r.json():
        assert md["category_code"] == code
```

Fetches a real category code from `/categories`, filters `/master-data` by it, and asserts
**every** returned item's `category_code` matches (not just spot-checking one).

```python
def test_filter_by_category_pk(self, client):
    """Filtering by category_pk returns only matching values."""
    cats = client.get(f"{BASE}/categories").json()
    pk = cats[0]["master_category_pk"]
    r = client.get(f"{BASE}/master-data", params={"category_pk": pk})
    assert r.status_code == 200
    for md in r.json():
        assert md["master_category_pk"] == pk
```

Does the same with the `category_pk` query param instead of `category_code`.

```python
def test_filter_nonexistent_category_returns_empty(self, client):
    """Filtering by a category code with no values returns empty list."""
    r = client.get(f"{BASE}/master-data", params={"category_code": "ZZZZZZZ_FAKE"})
    assert r.status_code == 200
    assert r.json() == []
```

Asserts filtering by a fabricated code `"ZZZZZZZ_FAKE"` returns `200` with body `== []` — a query
with zero matches is a successful empty result, not a 404, per REST convention.

The remaining tests mirror `TestCategories`'s list/detail/404/422 shape:

| Test | Lines | What it checks |
|---|---|---|
| `test_list_returns_200` | 83–89 | `GET /master-data` → 200, list, `len(data) > 0` ("Expected seeded master data values") |
| `test_detail_valid_pk` | 131–137 | `GET /master-data/{pk}` → 200, returned `master_data_pk` matches |
| `test_detail_fake_pk_returns_404` | 139–141 | all-zero UUID → 404 |
| `test_detail_bad_uuid_returns_422` | 143–144 | `"not-a-uuid"` → 422 |

#### `TestSettings` (lines 152–185, 4 tests)

```python
def test_lookup_by_key(self, client):
    """Looking up a setting by its business key returns 200."""
    settings = client.get(f"{BASE}/settings").json()
    key = settings[0]["setting_key"]
    r = client.get(f"{BASE}/settings/{key}")
    assert r.status_code == 200
    assert r.json()["setting_key"] == key
```

Fetches a real `setting_key` string from the list and confirms the business-key detail lookup
(`/settings/{key}`, a string path, not a UUID) returns it.

```python
def test_lookup_nonexistent_key_returns_404(self, client):
    """Looking up a nonexistent setting key returns 404."""
    assert client.get(f"{BASE}/settings/ZZZZZ_FAKE_KEY").status_code == 404
```

Confirms an unknown key string returns 404 rather than 422 (since any string is a syntactically
valid key).

The two remaining tests are the familiar list/required-fields shape:

| Test | Lines | What it checks |
|---|---|---|
| `test_list_returns_200` | 155–161 | `GET /settings` → 200, list, `len(data) > 0` ("Expected seeded system settings") |
| `test_list_has_required_fields` | 163–173 | `required = {"system_setting_pk", "setting_key", "setting_value", "description", "data_type", "is_active"}` is a subset of every returned setting's keys |

#### `TestSequences` (lines 188–216, 3 tests)

The contract-enforcement test — this is the one that must keep failing loudly if `current_value`
is ever re-exposed:

```python
def test_current_value_not_exposed(self, client):
    """current_value is infrastructure state — must NOT be in the response."""
    for seq in client.get(f"{BASE}/sequences").json():
        assert "current_value" not in seq, (
            f"current_value leaked in sequence {seq.get('sequence_code', '?')}"
        )
```

Iterates every returned sequence and asserts the key is entirely absent from the dict (not merely
`None`), guarding against `current_value` being accidentally re-added to either the SQL SELECT or
`SequenceResponse`.

| Test | Lines | What it checks |
|---|---|---|
| `test_list_returns_200` | 191–197 | `GET /sequences` → 200, list, `len(data) > 0` ("Expected seeded ID sequences") |
| `test_list_has_required_fields` | 199–209 | `required = {"id_sequence_master_pk", "sequence_code", "sequence_name", "prefix", "padding_length", "description", "is_active"}` is a subset of every returned sequence's keys (note: `current_value` deliberately absent from this set too) |

#### `TestCountries`, `TestStates`, `TestDistricts` (lines 224–333, 5 tests each)

These three classes share the same shape: list-returns-200-non-empty, required-fields (for
`TestStates`/`TestDistricts` this specifically checks the JOINed parent fields), filter-by-parent-
PK, detail-by-valid-PK, and detail-by-fake-PK-returns-404. `TestCountries` additionally has
`test_detail_bad_uuid_returns_422`. `TestStates` is shown in full below as the representative;
`TestCountries` and `TestDistricts` differ only in field names and are tabulated afterward.

```python
def test_list_has_joined_country_fields(self, client):
    """Each state includes country_code and country_name via JOIN."""
    required = {
        "state_pk", "country_pk", "country_code", "country_name",
        "state_code", "state_name", "display_order", "is_active",
    }
    for s in client.get(f"{BASE}/states").json():
        assert required.issubset(s.keys())
```

```python
def test_filter_by_country_pk(self, client):
    """Filtering by country_pk returns only states in that country."""
    countries = client.get(f"{BASE}/countries").json()
    cpk = countries[0]["country_pk"]
    r = client.get(f"{BASE}/states", params={"country_pk": cpk})
    assert r.status_code == 200
    for s in r.json():
        assert s["country_pk"] == cpk
```

The required-fields test proves the `/states` list is JOINed against `countries` so each row
carries its parent's `country_code`/`country_name` inline (no separate lookup needed by callers).
The filter test verifies **every** returned row's `country_pk` matches the filter value, not just
that the call succeeded.

The remaining tests in `TestStates` are the plain list/detail/404 shape (`test_list_returns_200`
lines 260–264, `test_detail_valid_pk` lines 284–289, `test_detail_fake_pk_returns_404` lines
291–293).

`TestCountries` (lines 224–254) and `TestDistricts` (lines 296–333) follow the identical shape,
differing only here:

| Class | Lines | Required-fields test | JOINed parent fields | Filter test | Extra test |
|---|---|---|---|---|---|
| `TestCountries` | 224–254 | `test_list_has_required_fields` (234–240) | none — countries have no parent | — (no filter; countries are the top of the hierarchy) | `test_detail_bad_uuid_returns_422` (253–254): `"not-a-uuid"` → 422 |
| `TestDistricts` | 296–333 | `test_list_has_joined_state_name` (305–313): `required = {"district_pk", "state_pk", "state_name", "district_code", "district_name", "display_order", "is_active"}` | `state_name` | `test_filter_by_state_pk` (315–322): filters `/districts` by `state_pk`, asserts every returned `d["state_pk"] == spk` | — |

#### `TestCities` (lines 336–351, 2 tests)

Documented as "intentionally empty at Tier 1":

```python
def test_list_returns_200(self, client):
    """Cities endpoint returns 200 (empty list — no seed data by design)."""
    r = client.get(f"{BASE}/cities")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

Only asserts 200 and a list type, no non-emptiness assertion.

```python
def test_filter_by_district_pk_returns_200(self, client):
    """Filtering by district_pk returns 200 even when empty."""
    districts = client.get(f"{BASE}/districts").json()
    dpk = districts[0]["district_pk"]
    r = client.get(f"{BASE}/cities", params={"district_pk": dpk})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

Confirms filtering by a real `district_pk` still returns 200 with a list (empty), i.e. the filter
code path doesn't error out on zero rows.

#### `TestPostalCodes` (lines 354–389, 4 tests)

```python
def test_list_has_required_fields(self, client):
    """If postal codes are seeded, verify response shape."""
    data = client.get(f"{BASE}/postal-codes").json()
    if len(data) > 0:
        required = {
            "postal_code_pk", "country_pk", "state_pk",
            "state_name", "postal_code", "post_office_name", "is_active",
        }
        for pc in data:
            assert required.issubset(pc.keys())
```

Written defensively — the field-shape check only runs `if len(data) > 0:`, since postal codes
may or may not be seeded.

```python
def test_filter_by_country_pk(self, client):
    """Filtering by country_pk returns 200."""
    countries = client.get(f"{BASE}/countries").json()
    cpk = countries[0]["country_pk"]
    r = client.get(f"{BASE}/postal-codes", params={"country_pk": cpk})
    assert r.status_code == 200
    for pc in r.json():
        assert pc["country_pk"] == cpk
```

```python
def test_filter_by_state_pk(self, client):
    """Filtering by state_pk returns 200."""
    states = client.get(f"{BASE}/states").json()
    spk = states[0]["state_pk"]
    r = client.get(f"{BASE}/postal-codes", params={"state_pk": spk})
    assert r.status_code == 200
    for pc in r.json():
        assert pc["state_pk"] == spk
```

Each verifies every returned row's corresponding FK matches the filter — `test_filter_by_
country_pk` for `country_pk`, `test_filter_by_state_pk` for `state_pk`. `test_list_returns_200`
(lines 357–360) just asserts 200 + list type, the same defensive stance as the required-fields
test above.

#### `TestPostalCodeMappings` (lines 392–399, 1 test)

```python
def test_list_returns_200(self, client):
    """Mappings endpoint returns 200 (empty — no city/village data yet)."""
    r = client.get(f"{BASE}/postal-code-mappings")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

Documented as "empty at Tier 1" — only checks 200 + list type, no filter tests (there's no seeded
city/village or mapping data to filter against yet).

#### `TestDocuments` (lines 407–420, 2 tests)

```python
def test_list_returns_200(self, client):
    """Documents endpoint returns 200 (empty — runtime data)."""
    r = client.get(f"{BASE}/documents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

```python
def test_filter_by_type_code_returns_200(self, client):
    """Filtering by document_type_code returns 200 even when empty."""
    r = client.get(f"{BASE}/documents", params={"document_type_code": "PHOTO"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

Documented as "intentionally empty at Tier 1" — both tests only assert 200 + list type; the
second filters by `document_type_code="PHOTO"`.

#### `TestChangeLogNotExposed` (lines 428–442, 1 test)

```python
def test_change_log_endpoint_returns_404(self, client):
    """
    /api/v1/foundation/change-log must NOT exist.

    Audit data is deferred to Tier 5 authenticated API.
    If this test fails, someone added an anonymous audit endpoint.
    """
    r = client.get(f"{BASE}/change-log")
    assert r.status_code in (404, 405), (
        f"change-log endpoint should not exist in Tier 1, "
        f"got status {r.status_code}"
    )
```

Calls `GET /api/v1/foundation/change-log` and asserts `status_code in (404, 405)`, with a failure
message stating "change-log endpoint should not exist in Tier 1." This is the test that directly
enforces the module docstring's stated exclusion of `field_change_log` from the anonymous API.

#### `TestFoundationUI` (lines 450–457, 1 test)

```python
def test_foundation_page_returns_200(self, client):
    """The /foundation route serves HTML."""
    r = client.get("/foundation")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
```

Calls `GET /foundation` (no `/api/v1` prefix — a page route, not an API endpoint) and asserts 200
with `"text/html"` in the `Content-Type` header, verifying `api/main.py`'s conditional
`serve_foundation()` route actually works end-to-end.

---

### 2.4 `tests/test_security.py`

**Requirement**

The security middleware stack (`api/middleware.py`'s headers, `api/main.py`'s rate limiting and
CORS wiring — see `SECURITY_CODE_EXPLANATIONS.md`) is exactly the kind of cross-cutting behaviour
that's easy to silently break — adding a new route, changing middleware order, or removing
`SlowAPIMiddleware` by accident would not fail any functional test in `test_bootstrap.py` or
`test_foundation.py`, since those only check response *bodies*, not headers or throttling. This
file exists specifically to test the non-functional, security-relevant behaviour of every
response: headers present, headers scoped correctly, rate limiting actually enforced (not just
configured), and CORS refusing unconfigured origins. It directly caught a real bug during
development — `SlowAPIMiddleware` had been configured but never added to the app, so rate
limiting silently did nothing.

**Line-by-line**

```python
"""
NSS ERP — Security middleware tests.

Verifies that security controls added across all tiers actually work:
  1. Security headers are present on every response
  2. Cache-Control is scoped to API routes (not static assets)
  3. Rate limiting returns 429 after threshold
  4. CORS responds correctly to preflight and same-origin requests
  5. DISABLE_DOCS toggle hides OpenAPI endpoints

These tests run against the FastAPI TestClient (no network).
"""

import pytest
from fastapi.testclient import TestClient

from api.main import limiter


pytestmark = pytest.mark.integration
```

The module docstring enumerates the 5 things under test: security headers present on every
response; `Cache-Control` scoped to API routes only; rate limiting returns 429 past threshold;
CORS behaves correctly for preflight and same-origin requests; the `DISABLE_DOCS` toggle
(mentioned in the docstring, though not directly asserted by a dedicated test in this file —
it's exercised implicitly by every other test still passing with docs enabled in the test
environment). `TestClient` is imported separately from the shared `client` fixture, because
`TestRateLimiting` needs its own isolated client instance. `from api.main import limiter`
imports the exact same `Limiter` object `api/main.py` registered on the app, so this test file
can manipulate its internal state directly.

The autouse fixture every test in this file runs under, lines 23–27:

```python
@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Reset the rate limiter's in-memory storage before each test."""
    limiter.reset()
    yield
```

`autouse=True` means this fixture runs before **every** test in the file automatically, with no
test needing to declare it as a parameter. `limiter.reset()` clears the rate limiter's in-memory
request counters before each test; without this, `TestRateLimiting`'s 61-request test would
exhaust the shared limiter's allowance and cause spurious 429s in whichever test happens to run
afterward.

#### `TestSecurityHeaders` (lines 30–68, 5 tests)

```python
def test_api_response_has_security_headers(self, client):
    """Every API response must include the four core security headers."""
    response = client.get("/api/v1/bootstrap/health")
    assert response.status_code == 200

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in response.headers["Permissions-Policy"]
    assert "microphone=()" in response.headers["Permissions-Policy"]
    assert "geolocation=()" in response.headers["Permissions-Policy"]
```

Calls `/api/v1/bootstrap/health`, asserts 200, then asserts the exact literal values of
`X-Content-Type-Options` (`"nosniff"`), `X-Frame-Options` (`"DENY"`), `Referrer-Policy`
(`"strict-origin-when-cross-origin"`), and that all three `Permissions-Policy` directives
(`"camera=()"`, `"microphone=()"`, `"geolocation=()"`) are present as substrings of that single
header value.

```python
def test_api_response_has_cache_control_no_store(self, client):
    """API responses under /api/ must have Cache-Control: no-store."""
    response = client.get("/api/v1/bootstrap/health")
    assert response.headers.get("Cache-Control") == "no-store"
```

Asserts `response.headers.get("Cache-Control") == "no-store"` for an `/api/*` route.

```python
def test_static_response_no_cache_control_no_store(self, client):
    """Non-API responses (frontend) must NOT have Cache-Control: no-store."""
    response = client.get("/")
    assert response.status_code == 200
    # Static/frontend responses should not force no-store
    assert response.headers.get("Cache-Control") != "no-store"
```

The inverse regression guard: calls `/` (the frontend) and asserts `Cache-Control` is **not**
`"no-store"`, catching any future change that applies the no-cache rule globally instead of
scoping it to `/api/*`.

```python
def test_x_xss_protection_not_present(self, client):
    """X-XSS-Protection is obsolete and must NOT be set."""
    response = client.get("/api/v1/bootstrap/health")
    assert "X-XSS-Protection" not in response.headers
```

Asserts the header key `"X-XSS-Protection"` is entirely absent from the response, enforcing the
documented decision in `api/middleware.py` never to add this obsolete header.

```python
def test_security_headers_on_frontend_route(self, client):
    """Frontend routes also get the four core security headers."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
```

Confirms the same three core headers also appear on `/`, proving the middleware is genuinely
global and not scoped only to `/api/*` routes (unlike `Cache-Control`, which is intentionally
scoped).

#### `TestRateLimiting` (lines 71–94, 1 test)

```python
def test_rate_limit_returns_429(self, client):
    """
    Exceeding the rate limit must return 429 Too Many Requests.

    The default limit is 60/minute. We send 61 requests and verify
    the last one is rejected. TestClient is in-process (no network),
    so this completes in milliseconds.
    """
    from api.main import app, limiter

    with TestClient(app) as test_client:
        last_status = None
        for i in range(61):
            resp = test_client.get("/api/v1/bootstrap/health")
            last_status = resp.status_code
            if last_status == 429:
                break

        assert last_status == 429, (
            "After 61 requests, rate limit (60/minute) should return 429"
        )
```

Re-imports `app` and `limiter` locally and constructs its own `with TestClient(app) as
test_client:` rather than using the shared module-scoped `client` fixture, to keep this test's
request burst isolated from other tests in the file. Loops up to 61 times calling `GET
/api/v1/bootstrap/health`, tracking `last_status`, and `break`s as soon as it sees `429` — since
the configured default is `60/minute`, the 61st request in the same window is expected to be
rejected. Asserts `last_status == 429` with a message naming the expected limit. Because
`TestClient` calls the ASGI app in-process with no real network I/O, all 61 requests complete in
milliseconds.

#### `TestCORS` (lines 97–124, 2 tests)

```python
def test_no_cors_headers_without_configured_origins(self, client):
    """
    When CORS_ORIGINS is empty (default), no CORS headers should
    appear even if the request includes an Origin header.
    """
    response = client.get(
        "/api/v1/bootstrap/health",
        headers={"Origin": "https://evil.example.com"},
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers
```

Sends `GET /api/v1/bootstrap/health` with an `Origin: https://evil.example.com` header and
asserts `"Access-Control-Allow-Origin"` is **not** present in the response — confirming that with
`CORS_ORIGINS` unset (the local/test default), `CORSMiddleware` was never added to the app at all
(per `api/main.py`'s `if settings.CORS_ORIGINS:` guard), so no origin — malicious or not — gets
any CORS allowance.

```python
def test_cors_preflight_without_configured_origins(self, client):
    """
    OPTIONS preflight without configured origins should not
    return CORS allow headers.
    """
    response = client.options(
        "/api/v1/bootstrap/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "Access-Control-Allow-Origin" not in response.headers
```

Sends an `OPTIONS` preflight request (with `Origin` and `Access-Control-Request-Method: GET`
headers) to the same endpoint and asserts the same absence of `Access-Control-Allow-Origin`,
confirming the secure-by-default behaviour also holds for the preflight path browsers use before
an actual cross-origin request.

---

### 2.5 `tests/test_organization.py`

**Requirement**

The 6 Tier 2 Organization endpoints span 3 tables and rely on non-trivial behaviours —
8-way JOINed queries with 6 LEFT JOINs for nullable geographic FKs, a recursive CTE for
hierarchy traversal with a depth guard, combinable type/status/pagination filters, a
parent-existence-checked children endpoint, and a 36-field response model — every one of
which needs its own regression guard. This file is the executable specification for the
entire Tier 2 Organization API contract, plus UI structure tests for the Organization
Verification UI page and security-header verification for the Organization endpoints.
**64 tests across 7 classes** — this section supersedes an earlier version of this doc that
predated the "org-to-master-data migration": organization type and lifecycle status values
used to live in dedicated Organization tables with fields named `organization_status_pk` /
`organization_status_code` / `organization_status_name`; they now come from Foundation's
unified `master_data` (category `ORGANIZATION_TYPE` for types, the unified ERP-wide `STATUS`
category for statuses), so the response field names collapsed to the generic `status_pk` /
`status_code` / `status_name`, and the seeded counts grew (8 → 10 frozen types, 6 → 13
statuses) as the unified status vocabulary was built out for reuse by later tiers.

**Line-by-line**

```python
"""
NSS ERP — Tier 2 Organization API tests.

Integration tests for the 6 Organization GET endpoints across 3 tables.
Organization type values come from Foundation master_data
(category ORGANIZATION_TYPE). Status values come from the
unified ERP-wide STATUS category.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Endpoint groups tested:
  1. Reference Data: types, statuses (from master_data)
  2. Organizations:  list (with filters), detail, children
  3. Hierarchy:      recursive CTE tree
  4. UI Route:       /organization serves HTML
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/organization"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"
```

Module docstring states "6 Organization GET endpoints across 3 tables," explicitly calls out
that type values come from Foundation `master_data` (category `ORGANIZATION_TYPE`) and status
values come from the unified ERP-wide `STATUS` category, lists the four test groups, and notes
the database prerequisites. `pytestmark = pytest.mark.integration` is the same pattern as the
other test files. `BASE` and `FAKE_UUID` (lines 23–24) are module-level constants to avoid
repetition — identical to the approach in `test_foundation.py`.

#### `TestOrganizationTypes` (lines 32–74, 4 tests)

```python
def test_list_returns_10_frozen_types(self, client):
    """Exactly 10 frozen organization types are seeded."""
    data = client.get(f"{BASE}/types").json()
    assert len(data) == 10
    codes = {t["organization_type_code"] for t in data}
    expected = {
        "KENDRA", "NILACHALA_KUTIRA", "SMRUTI_MANDIRA",
        "ANCHALIKA_SANGHA", "ZILLA_SANGHA", "SAKHA_SANGHA",
        "SAKHA_ASANA", "PARIBARIK_ASANA", "PARIBARIK_SANGHA",
        "PATHA_CHAKRA",
    }
    assert codes == expected
```

Pins the seeded type count at exactly 10 (grown from the 8 frozen at the original Tier 2
freeze — `PARIBARIK_ASANA` and `PARIBARIK_SANGHA` were added) and asserts the full code set
via `==`, not subset, so an accidental extra or missing type fails loudly.

| Test | Lines | What it checks |
|---|---|---|
| `test_list_returns_200` | 35–41 | `GET /types` → 200, non-empty list ("Expected 9 seeded organization types" — a stale docstring left over from an earlier count; the assertion itself is just `len(data) > 0`, so it still passes) |
| `test_list_has_required_fields` | 43–55 | 6-field `required` set (`organization_type_pk`, `organization_type_code`, `organization_type_name`, `description`, `sort_order`, `is_active`) is a subset of every returned type's keys; asserts `is_active is True` |
| `test_list_ordered_by_sort_order` | 70–74 | `sort_order` values are in ascending order |

The structure mirrors `TestFoundationCountries` / `TestFoundationStates` — the same
four-test pattern (200, fields, count+codes, ordering) applied to a different reference
table, now backed by `master_data` rows instead of a dedicated `organization_type` table.

#### `TestStatuses` (lines 77–118, 4 tests)

Renamed from the earlier `TestOrganizationStatuses` to `TestStatuses` to match the field
rename described above — the class now documents "the unified ERP-wide STATUS category,"
not an organization-specific status table:

```python
def test_list_returns_13_statuses(self, client):
    """Exactly 13 unified lifecycle statuses are seeded."""
    data = client.get(f"{BASE}/statuses").json()
    assert len(data) == 13
    codes = {s["status_code"] for s in data}
    expected = {
        "PROPOSED", "APPROVED", "ACTIVE",
        "INACTIVE", "SUSPENDED", "LAPSED",
        "TRANSFERRED", "RESIGNED", "EXPELLED",
        "DECEASED", "DISSOLVED", "ARCHIVED", "EXPIRED",
    }
    assert codes == expected
```

13 lifecycle statuses now cover the full unified vocabulary (`PROPOSED` through `EXPIRED`),
up from the original 6 (`PROPOSED, APPROVED, ACTIVE, INACTIVE, SUSPENDED, ARCHIVED`) — the
extra 7 (`LAPSED`, `TRANSFERRED`, `RESIGNED`, `EXPELLED`, `DECEASED`, `DISSOLVED`, `EXPIRED`)
were added so the same `STATUS` category can serve organization *and* person/membership
lifecycles in later tiers, per the "Unified Body Governance Model" project principle.

> **Known broken test (as of Tier 4):** `api/routers/organization.py`'s `/statuses` endpoint
> now filters `STATUS` by a new `master_data.applicable_modules TEXT[]` column
> (`'ORGANIZATION' = ANY(applicable_modules) OR applicable_modules IS NULL`), returning only 7
> Organization-applicable statuses (Proposed/Approved/Active/Inactive/Suspended/Dissolved/
> Archived) — not all 13-of-what-is-now-16 unified `STATUS` values. This test still asserts the
> old unfiltered count/set and has not been updated; it will fail against the current code. See
> `docs/PROJECT_DOCUMENTATION.md` → Open questions / TODOs.

```python
def test_list_has_required_fields(self, client):
    """Each status has the expected response fields."""
    required = {
        "status_pk", "status_code",
        "status_name", "description",
        "sort_order", "is_active",
    }
    for s in client.get(f"{BASE}/statuses").json():
        assert required.issubset(s.keys()), (
            f"Missing fields in status {s.get('status_code', '?')}: "
            f"{required - s.keys()}"
        )
```

The field set uses the generic `status_pk` / `status_code` / `status_name` names — not
`organization_status_*` — confirming statuses are a plain `master_data` projection with no
organization-specific columns at all.

| Test | Lines | What it checks |
|---|---|---|
| `test_list_returns_200` | 80–86 | `GET /statuses` → 200, non-empty list |
| `test_list_ordered_by_sort_order` | 114–118 | `sort_order` values ascending |

#### `TestOrganizations` (lines 126–325, 27 tests)

The largest test class in the file, covering list, filters, detail, geographic resolution,
contact-field content, and pagination:

```python
def test_list_has_required_fields(self, client):
    """Each organization has expected fields including JOINed context."""
    required = {
        "organization_pk", "organization_id", "organization_name",
        "organization_code",
        "organization_type_pk", "organization_type_code",
        "organization_type_name",
        "status_pk", "status_code",
        "status_name",
        "parent_organization_pk", "parent_organization_name",
        "address_line_1", "address_line_2",
        "phone_number", "mobile_number", "email", "org_email",
        "website_url", "org_website_url",
        "youtube_channel_url", "org_youtube_channel_url",
        "district_pk", "district_name",
        "state_pk", "state_name",
        "country_pk", "country_name",
        "city_village_pk", "city_village_name",
        "postal_code_pk", "postal_code",
        "latitude", "longitude",
        "is_active",
    }
    for org in client.get(f"{BASE}/organizations").json():
        assert required.issubset(org.keys()), (
            f"Missing fields in org {org.get('organization_code', '?')}: "
            f"{required - org.keys()}"
        )
```

Checks the fields of `OrganizationResponse` are present, including all JOINed context
fields from type, status (now `status_pk`/`status_code`/`status_name`, not
`organization_status_*`), parent, and 5 geographic tables, plus 4 contact fields (phone,
mobile, email + org_email) and 4 online-presence fields (website/YouTube for both NSS-level
and org-specific). This is the most comprehensive field check in the entire test suite —
Foundation's largest response model has 8 fields; Organization's has over 30.

Six tests pin the actual seeded contact-field content — new since the original freeze:

```python
def test_all_orgs_have_nss_youtube(self, client):
    """All 3 organizations share the NSS YouTube channel URL."""
    for org in client.get(f"{BASE}/organizations").json():
        assert org["youtube_channel_url"] == "https://www.youtube.com/@NilachalaSaraswataSangha", (
            f"{org['organization_code']} missing youtube_channel_url"
        )


def test_kendra_has_contact_info(self, client):
    """Kendra org has seeded phone, mobile, and website."""
    r = client.get(f"{BASE}/organizations", params={"type_code": "KENDRA"})
    kendra = r.json()[0]
    assert kendra["phone_number"] == "+91-674-2390055"
    assert kendra["mobile_number"] == "+91-9238106823"
    assert kendra["website_url"] == "https://www.nsspuri.org"
```

`test_all_orgs_have_nss_youtube`, `test_all_orgs_have_nss_email`, and
`test_all_orgs_have_nss_website` each pin a literal shared value (YouTube channel, email
`info@nsspuri.org`, website `https://www.nsspuri.org`) across all 3 seeded orgs.
`test_kendra_has_contact_info` and `test_smruti_mandira_has_contact_info` pin org-specific
phone/mobile numbers for the two orgs whose seed rows carry them. `test_contact_fields_nullable`
only asserts the 8 contact/online-presence keys are *present* (not their values), documenting
that these columns are nullable and simply happen to be populated for the seeded rows.

The pagination group (8 tests) exercises `limit`/`offset` query params added to
`/organizations`:

```python
def test_pagination_limit_and_offset(self, client):
    """limit=1 offset=1 returns the second organization."""
    all_data = client.get(f"{BASE}/organizations").json()
    if len(all_data) < 2:
        pytest.skip("Need at least 2 orgs for offset test")
    page = client.get(f"{BASE}/organizations", params={"limit": 1, "offset": 1}).json()
    assert len(page) == 1
    assert page[0]["organization_pk"] == all_data[1]["organization_pk"]


def test_pagination_limit_zero_returns_422(self, client):
    """limit=0 violates ge=1 constraint — returns 422."""
    r = client.get(f"{BASE}/organizations", params={"limit": 0})
    assert r.status_code == 422


def test_pagination_limit_over_max_returns_422(self, client):
    """limit=501 exceeds MAX_LIMIT=500 — returns 422."""
    r = client.get(f"{BASE}/organizations", params={"limit": 501})
    assert r.status_code == 422
```

`test_pagination_limit_and_offset` proves `offset` actually skips rows in a stable order (the
second page's single row matches the unpaginated list's second element), not just that the
response shrinks. `test_pagination_limit_zero_returns_422` and
`test_pagination_limit_over_max_returns_422` pin FastAPI/Pydantic's `Query(ge=1, le=500)`-style
constraints (shared `MAX_LIMIT=500` constant from `api/helpers.py`) at the boundary — 0 and 501
both fail validation before the router body ever runs.

| Test | Lines | What it checks |
|---|---|---|
| `test_list_returns_200` | 129–135 | `GET /organizations` → 200, non-empty |
| `test_list_returns_3_seeded_orgs` | 165–170 | `len == 3`; codes == `{KEN, NKT, SMR}` |
| `test_list_all_active` | 172–175 | Every org has `is_active is True` |
| `test_list_all_roots` | 177–181 | Every org has `parent_organization_pk is None` and `parent_organization_name is None` |
| `test_filter_by_type_code` | 183–189 | `?type_code=KENDRA` → 1 result with matching type code |
| `test_filter_by_status_code` | 191–196 | `?status_code=ACTIVE` → every result has matching `status_code` |
| `test_filter_nonexistent_type_returns_empty` | 198–202 | `?type_code=ZZZZZ_FAKE` → 200 with `[]` |
| `test_detail_valid_pk` | 204–210 | `GET /organizations/{pk}` → 200, returned `organization_pk` matches |
| `test_detail_fake_pk_returns_404` | 212–214 | All-zero UUID → 404 |
| `test_detail_bad_uuid_returns_422` | 216–218 | `"not-a-uuid"` → 422 |
| `test_detail_has_resolved_country` | 220–224 | Kendra org has `country_name is not None` (LEFT JOIN resolution works) |
| `test_detail_has_postal_code` | 226–230 | Kendra org has `postal_code is not None` |
| `test_contact_fields_nullable` | 232–242 | All 8 contact/online-presence keys present on every org |
| `test_smruti_mandira_has_contact_info` | 259–263 | Smruti Mandira has seeded `phone_number` |
| `test_all_orgs_have_nss_email` | 265–270 | All 3 orgs share `email == "info@nsspuri.org"` |
| `test_all_orgs_have_nss_website` | 272–277 | All 3 orgs share `website_url == "https://www.nsspuri.org"` |
| `test_pagination_default_returns_all_seeded` | 281–284 | No params → all 3 seeded orgs |
| `test_pagination_limit_1` | 286–289 | `limit=1` → exactly 1 result |
| `test_pagination_offset_skips` | 291–295 | `offset=1` → one fewer result than the unpaginated list |
| `test_pagination_negative_offset_returns_422` | 316–319 | `offset=-1` violates `ge=0` — 422 |
| `test_pagination_large_offset_returns_empty` | 321–325 | `offset=9999` → 200 with `[]`, not an error |

The two resolved-geography tests (`test_detail_has_resolved_country`,
`test_detail_has_postal_code`) are unique to Organization — they verify that the 6 LEFT JOINs
in the organization SELECT actually resolve nullable geographic FK columns to non-NULL display
names for the Kendra seed record. If any of the 6 LEFT JOINs were accidentally changed to INNER
JOINs, the Kendra row (which lacks some geographic FKs) would vanish from the result set
entirely, causing `test_list_returns_3_seeded_orgs` to fail.

#### `TestOrganizationChildren` (lines 333–361, 4 tests)

| Test | Lines | What it checks |
|---|---|---|
| `test_children_returns_200` | 336–342 | Valid parent PK → 200, list |
| `test_children_empty_for_leaf_org` | 344–349 | Seeded root orgs have no children → `[]` |
| `test_children_fake_pk_returns_404` | 351–355 | All-zero UUID → 404 (parent existence check) |
| `test_children_bad_uuid_returns_422` | 357–361 | `"not-a-uuid"` → 422 |

The 404 test is critical: the `/organizations/{pk}/children` endpoint first checks that the
parent exists (a `SELECT` against `nss.organization`), and only then queries for children.
Without that guard, any UUID — valid or not — would return `200 []`, making it impossible
to distinguish "org exists but has no children" from "org doesn't exist."

#### `TestHierarchy` (lines 369–430, 9 tests)

```python
def test_hierarchy_has_required_fields(self, client):
    """Each hierarchy node has expected fields."""
    required = {
        "organization_pk", "organization_name", "organization_code",
        "organization_type_code", "organization_type_name",
        "status_code", "status_name",
        "parent_organization_pk", "depth", "is_active",
    }
    for node in client.get(f"{BASE}/hierarchy").json():
        assert required.issubset(node.keys()), (
            f"Missing fields in hierarchy node: {required - node.keys()}"
        )
```

Like `TestOrganizations`, the required-fields set uses `status_code`/`status_name` (not
`organization_status_code`/`organization_status_name`), reflecting the same master-data-backed
status field rename. Per `CLAUDE.md`, the underlying `WITH RECURSIVE` CTE also carries a depth
guard capped at 10 to prevent runaway recursion on a corrupted/cyclic parent chain — not
directly exercised here since only root orgs are seeded, but relevant to why `depth` is part of
the required-fields contract.

The pagination group (5 tests) mirrors `TestOrganizations`'s pagination tests, applied to
`/hierarchy`:

```python
def test_hierarchy_pagination_offset(self, client):
    """Hierarchy with offset=1 skips first node."""
    all_data = client.get(f"{BASE}/hierarchy").json()
    offset_data = client.get(f"{BASE}/hierarchy", params={"offset": 1}).json()
    assert len(offset_data) == len(all_data) - 1
```

| Test | Lines | What it checks |
|---|---|---|
| `test_hierarchy_returns_200` | 372–378 | `GET /hierarchy` → 200, non-empty |
| `test_hierarchy_roots_at_depth_0` | 393–397 | All nodes have `depth == 0` and `parent_organization_pk is None` (only roots seeded) |
| `test_hierarchy_returns_3_nodes` | 399–402 | Exactly 3 nodes (matching 3 seeded root orgs) |
| `test_hierarchy_pagination_limit_1` | 406–409 | `limit=1` → exactly 1 node |
| `test_hierarchy_pagination_limit_zero_returns_422` | 417–420 | `limit=0` → 422 |
| `test_hierarchy_pagination_limit_over_max_returns_422` | 422–425 | `limit=501` → 422 |
| `test_hierarchy_pagination_negative_offset_returns_422` | 427–430 | `offset=-1` → 422 |

With only root organizations seeded, the recursive CTE's anchor member returns 3 rows at
`depth = 0` and the recursive member returns no additional rows. When child organizations are
seeded in future tiers, `test_hierarchy_roots_at_depth_0` will need updating to account for
`depth > 0` nodes, but `test_hierarchy_has_required_fields` and the 200/non-empty check will
remain valid.

#### `TestOrganizationUI` (lines 438–512, 13 tests)

The Organization Verification UI page structure tests. Same pattern as `TestBootstrapUI`
and `TestFoundationUI` — testing that the HTML page served by the UI route includes
the expected structural elements:

| Test | Lines | What it checks |
|---|---|---|
| `test_organization_page_returns_200` | 441–445 | `GET /organization` → 200, `text/html` content type |
| `test_page_contains_title` | 447–450 | HTML contains "Organization Verification" |
| `test_page_contains_branding` | 452–455 | HTML contains "Nilachala Saraswata Sangha" |
| `test_page_loads_alpine_js` | 457–461 | HTML contains "alpinejs" and "integrity=" (SRI) |
| `test_page_loads_daisyui` | 463–467 | HTML contains "daisyui" and "integrity=" (SRI) |
| `test_page_loads_tailwind` | 469–472 | HTML contains "cdn.tailwindcss.com" |
| `test_page_loads_organization_js` | 474–477 | HTML contains "organization.js" |
| `test_page_has_alpine_data_binding` | 479–482 | HTML contains `x-data="organizationApp()"` |
| `test_page_has_nav_links` | 484–489 | HTML contains `href="/"`, `href="/foundation"`, `href="/organization"` (all 3 tiers) |
| `test_page_has_three_tabs` | 491–496 | HTML contains "Reference Data", "Organizations", "Hierarchy" |
| `test_page_has_system_status_section` | 498–501 | HTML contains "System Status" |
| `test_page_has_nss_logo` | 503–506 | HTML contains "nss-logo.png" |
| `test_page_has_copyright_footer` | 508–512 | HTML contains "2026" and "All rights reserved" |

Two tests are unique to Organization and absent from Bootstrap/Foundation:
`test_page_has_three_tabs` (verifying the 3-tab structure) and
`test_page_loads_organization_js` (verifying the tier-specific JS file).

#### `TestOrganizationSecurity` (lines 520–541, 3 tests)

Verifies the security middleware applies to Organization endpoints specifically — the
cross-tier `test_security.py` only tests Bootstrap/frontend routes:

| Test | Lines | What it checks |
|---|---|---|
| `test_org_api_has_security_headers` | 523–530 | `GET /types` → 200, has `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `camera=()` in `Permissions-Policy` |
| `test_org_api_has_cache_control_no_store` | 532–535 | `GET /organizations` has `Cache-Control: no-store` |
| `test_org_ui_no_cache_control_no_store` | 537–541 | `GET /organization` (UI page) does NOT have `Cache-Control: no-store` |

The third test (`test_org_ui_no_cache_control_no_store`) is a deliberate inversion: HTML
pages should be cacheable by the browser, so the middleware's `no-store` header — applied
only to `/api/` paths — must **not** appear on the UI route. This confirms the path-based
conditional in `middleware.py` works correctly for Organization routes.

---

### 2.6 `tests/test_person.py`

**Requirement**

The 4 Tier 3 Person endpoints span 2 tables (`person`, `person_address`) and introduce the
first data-sensitivity-driven test class in the suite: Aadhaar is a government identifier that
must never leave the API in raw form, so every list/detail/search response needs a regression
guard proving `aadhaar_encrypted` and `aadhaar_hash` are absent, and that only `aadhaar_last4`
(and only on the detail endpoint, never the summary shapes) is ever returned. Unlike
Organization, `person`/`person_address` have **no seed data** — the DDL bootstraps the schema
but seeds nothing — so most tests are written defensively (`pytest.skip("No person data
seeded")` or asserting on empty lists) rather than pinning literal counts, and the file's real
job is proving endpoint *structure*, *filter wiring*, *error handling*, *trigram search*, and
*security* hold even with zero rows. This file is the executable specification for the entire
Tier 3 Person API contract, its aadhaar-masking guarantee, and UI structure tests for the
Person Verification UI page. **56 tests across 6 classes.**

**Line-by-line**

```python
"""
NSS ERP — Tier 3 Person API tests.

Integration tests for the 4 Person GET endpoints across 2 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Person tables have no seed data — the test suite verifies endpoint
structure, response shapes, error handling, security, and UI rendering.
Data-dependent assertions (field values, counts) are guarded by
availability.

Endpoint groups tested:
  1. Person List:     /persons (with filters)
  2. Person Detail:   /persons/{person_pk}
  3. Addresses:       /persons/{person_pk}/addresses
  4. Search:          /search?q=
  5. Security:        aadhaar exclusion, security headers
  6. UI Route:        /person serves HTML
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/person"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"
```

Module docstring states "4 Person GET endpoints across 2 tables," explicitly documents that
Person tables "have no seed data" and that "data-dependent assertions... are guarded by
availability," and lists the six test groups. `pytestmark`, `BASE`, and `FAKE_UUID` follow the
same pattern as `test_organization.py`.

```python
def _get_first_person_pk(client):
    """Return the PK of the first person, or None if no data."""
    data = client.get(f"{BASE}/persons").json()
    return data[0]["person_pk"] if data else None
```

A module-level helper (lines 36–39), not a fixture — every detail/address/search test that
needs a real `person_pk` calls this first and, if it returns `None` (no seed data present),
calls `pytest.skip(...)` rather than failing; this is the mechanism that lets the whole file
pass cleanly against an empty `person` table while still exercising real-data code paths
whenever data *is* present (e.g. after Tier 4 membership onboarding seeds real people).

#### `TestPersonList` (lines 47–174, 17 tests)

```python
def test_list_excludes_sensitive_aadhaar(self, client):
    """Summary list must not contain aadhaar_encrypted or aadhaar_hash."""
    for p in client.get(f"{BASE}/persons").json():
        assert "aadhaar_encrypted" not in p
        assert "aadhaar_hash" not in p
        # Summary also excludes aadhaar_last4
        assert "aadhaar_last4" not in p
```

The list endpoint uses `PersonSummaryResponse` (a narrower shape than the detail endpoint's
`PersonResponse`), so this test asserts all three Aadhaar-related keys are absent — not just
the two raw/sensitive ones, but also the masked `aadhaar_last4`, which is reserved for the
detail view only. `test_list_excludes_audit_columns` (lines 80–92) runs the parallel check for
the six audit columns (`created_at`, `updated_at`, `deleted_at`, and the three
`*_by_sangha_sevi_pk` actor columns), which per `CLAUDE.md`'s "Pass 2 audit-actor FK
constraints" deferral don't yet have FK constraints but must still never leak through the API.

```python
def test_list_has_required_fields_if_data(self, client):
    """Each person summary has the expected response fields."""
    required = {
        "person_pk", "person_id",
        "first_name", "middle_name", "last_name",
        "date_of_birth", "date_of_death",
        "gender_code", "gender_name",
        "marital_status_code", "marital_status_name",
        "blood_group_code", "blood_group_name",
        "country_phone_code", "mobile_number", "email",
        "is_active",
    }
    data = client.get(f"{BASE}/persons").json()
    for p in data:
        assert required.issubset(p.keys()), (
            f"Missing fields in person {p.get('person_id', '?')}: "
            f"{required - p.keys()}"
        )
```

The `_if_data` suffix (also used by `TestPersonAddresses.test_addresses_has_required_fields_if_data`)
is this file's naming convention for "loop runs zero times and trivially passes if the table is
empty" — the `for p in data:` loop body simply never executes against an empty list, so the
test is always green regardless of seed state, while still asserting the full shape whenever
rows exist. The required set proves gender/marital-status/blood-group master-data FKs are
resolved via JOIN to their `_code`/`_name` pairs, matching `CLAUDE.md`'s "Master-data FKs...
are resolved via JOINs" note for Tier 3.

Three filter tests exercise the master-data-driven query params:

```python
def test_filter_by_gender_code_returns_200(self, client):
    """Filtering by gender_code returns 200."""
    r = client.get(f"{BASE}/persons", params={"gender_code": "MALE"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    for p in r.json():
        assert p["gender_code"] == "MALE"
```

`test_filter_by_gender_code_returns_200` asserts **every** returned row's `gender_code`
actually matches (not just that the call succeeded), the same rigor as Foundation's filter
tests; `test_filter_by_marital_status_code_returns_200` and
`test_filter_by_blood_group_code_returns_200` only assert 200 + list type (no seeded rows to
spot-check against), and `test_filter_nonexistent_gender_returns_empty` confirms a fabricated
code returns `200 []`, not a 404 — the same "zero matches is a successful empty result"
convention used throughout the API. `test_multiple_filters_returns_200` combines all three
filters in one request to prove they compose (`AND`-combined `WHERE` clauses) without error.

The pagination group (7 tests) mirrors `TestOrganizations`'s pagination tests:

```python
def test_pagination_limit_zero_returns_422(self, client):
    """limit=0 violates ge=1 constraint — returns 422."""
    r = client.get(f"{BASE}/persons", params={"limit": 0})
    assert r.status_code == 422


def test_pagination_max_limit_accepted(self, client):
    """limit=500 (MAX_LIMIT) is accepted."""
    r = client.get(f"{BASE}/persons", params={"limit": 500})
    assert r.status_code == 200
```

`test_pagination_max_limit_accepted` is new relative to the equivalent Organization/Hierarchy
pagination groups — it positively confirms the upper boundary (`limit=500`, the shared
`MAX_LIMIT` from `api/helpers.py`) is accepted, complementing
`test_pagination_limit_over_max_returns_422`'s check that `501` is rejected; together the two
tests pin the exact boundary rather than just one side of it.

| Test | Lines | What it checks |
|---|---|---|
| `test_list_returns_200` | 50–54 | `GET /persons` → 200, list |
| `test_list_all_active` | 75–78 | Every returned person has `is_active is True` |
| `test_pagination_default_returns_200` | 140–143 | No params → 200 |
| `test_pagination_custom_limit` | 145–148 | `limit=1` → at most 1 result |
| `test_pagination_limit_over_max_returns_422` | 155–158 | `limit=501` → 422 |
| `test_pagination_negative_offset_returns_422` | 160–163 | `offset=-1` → 422 |
| `test_pagination_large_offset_returns_empty` | 165–169 | `offset=9999` → 200 with `[]` |

#### `TestPersonDetail` (lines 182–255, 6 tests)

```python
def test_detail_has_required_fields(self, client):
    """Full detail response has all PersonResponse fields."""
    pk = _get_first_person_pk(client)
    if pk is None:
        pytest.skip("No person data seeded")
    required = {
        "person_pk", "person_id",
        "first_name", "middle_name", "last_name",
        "date_of_birth", "date_of_death",
        "gender_master_data_pk", "gender_code", "gender_name",
        "marital_status_master_data_pk", "marital_status_code",
        "marital_status_name",
        "blood_group_master_data_pk", "blood_group_code",
        "blood_group_name",
        "country_phone_code", "mobile_number", "email",
        "aadhaar_last4",
        "photo_document_master_pk",
        "emergency_contact_name", "emergency_contact_phone",
        "emergency_relationship_master_data_pk",
        "emergency_relationship_code", "emergency_relationship_name",
        "remarks", "is_active",
    }
    data = client.get(f"{BASE}/persons/{pk}").json()
    assert required.issubset(data.keys()), (
        f"Missing fields: {required - data.keys()}"
    )
```

This is the one place `aadhaar_last4` is expected to be *present* — the detail response's
required set explicitly includes it, in direct contrast to `TestPersonList` and
`TestPersonSearch`, which both assert its *absence*. The set also includes the raw
`*_master_data_pk` FK columns alongside their resolved `_code`/`_name` pairs (e.g.
`gender_master_data_pk` + `gender_code` + `gender_name`), and the full emergency-contact block
(`emergency_contact_name`, `emergency_contact_phone`,
`emergency_relationship_master_data_pk`/`_code`/`_name`) that the summary shape omits entirely.
Every test in this class calls `_get_first_person_pk(client)` first and skips via
`pytest.skip("No person data seeded")` if it returns `None`.

```python
def test_detail_excludes_sensitive_aadhaar(self, client):
    """Detail response must never contain raw Aadhaar fields."""
    pk = _get_first_person_pk(client)
    if pk is None:
        pytest.skip("No person data seeded")
    data = client.get(f"{BASE}/persons/{pk}").json()
    assert "aadhaar_encrypted" not in data
    assert "aadhaar_hash" not in data
```

Even on the detail endpoint — which does expose the masked `aadhaar_last4` — the two raw
columns (`aadhaar_encrypted`, the ciphertext; `aadhaar_hash`, used for uniqueness lookups) must
never appear. This is the single most important regression guard in the file given
`CLAUDE.md`'s explicit statement that these columns are "never" returned.

| Test | Lines | What it checks |
|---|---|---|
| `test_detail_fake_pk_returns_404` | 185–188 | All-zero UUID → 404 |
| `test_detail_bad_uuid_returns_422` | 190–193 | `"not-a-uuid"` → 422 |
| `test_detail_valid_pk_returns_200` | 195–203 | Valid PK → 200, returned `person_pk` matches (skipped if no data) |
| `test_detail_excludes_audit_columns` | 241–255 | Same 6-column audit check as the list endpoint (skipped if no data) |

#### `TestPersonAddresses` (lines 263–323, 5 tests)

```python
def test_addresses_has_required_fields_if_data(self, client):
    """Each address has the expected response fields."""
    pk = _get_first_person_pk(client)
    if pk is None:
        pytest.skip("No person data seeded")
    required = {
        "person_address_pk", "person_pk",
        "address_type_master_data_pk", "address_type_code",
        "address_type_name",
        "address_line_1", "address_line_2", "landmark",
        "city_village_postal_code_map_pk",
        "city_village_name", "postal_code",
        "district_name", "state_name", "country_name",
        "is_primary", "remarks", "is_active",
    }
    data = client.get(f"{BASE}/persons/{pk}/addresses").json()
    for addr in data:
        assert required.issubset(addr.keys()), (
            f"Missing fields in address: {required - addr.keys()}"
        )
```

Proves address rows carry resolved `address_type` (via `address_type_master_data_pk`) and
resolved geography (`city_village_name`, `postal_code`, `district_name`, `state_name`,
`country_name`) inline, chained from `city_village_postal_code_map_pk` through Foundation's
geography tables the same way Organization's list resolves its own address fields.

```python
def test_addresses_primary_first(self, client):
    """Primary addresses are ordered before non-primary."""
    pk = _get_first_person_pk(client)
    if pk is None:
        pytest.skip("No person data seeded")
    data = client.get(f"{BASE}/persons/{pk}/addresses").json()
    if len(data) >= 2:
        primaries = [a for a in data if a["is_primary"]]
        non_primaries = [a for a in data if not a["is_primary"]]
        if primaries and non_primaries:
            first_non_primary_idx = next(
                i for i, a in enumerate(data) if not a["is_primary"]
            )
            last_primary_idx = max(
                i for i, a in enumerate(data) if a["is_primary"]
            )
            assert last_primary_idx < first_non_primary_idx
```

A triple-guarded ordering test: skips entirely with no person data, is a no-op with fewer than
2 addresses, and only asserts the ordering invariant (every primary address index precedes
every non-primary index) when both kinds are actually present — proving the endpoint's
`ORDER BY is_primary DESC, ...` (or equivalent) without requiring specific seed data to exist.

| Test | Lines | What it checks |
|---|---|---|
| `test_addresses_fake_pk_returns_404` | 266–269 | All-zero UUID → 404 (parent person existence check) |
| `test_addresses_bad_uuid_returns_422` | 271–274 | `"not-a-uuid"` → 422 |
| `test_addresses_valid_pk_returns_200` | 276–283 | Valid person PK → 200, list (possibly empty; skipped if no data) |

#### `TestPersonSearch` (lines 331–389, 8 tests)

```python
def test_search_min_length_validation(self, client):
    """Search with single character returns 422 (min_length=2)."""
    r = client.get(f"{BASE}/search", params={"q": "a"})
    assert r.status_code == 422


def test_search_two_chars_accepted(self, client):
    """Search with exactly 2 characters returns 200."""
    r = client.get(f"{BASE}/search", params={"q": "ab"})
    assert r.status_code == 200
```

Pins the exact boundary of the `q: str = Query(..., min_length=2)` constraint backing the
trigram search — 1 character rejected, 2 accepted — the same boundary-pinning style used for
`limit`/`offset` elsewhere in the suite. `test_search_requires_query` (lines 340–343) confirms
omitting `q` entirely is also a 422 (FastAPI's required-query-param validation, no custom code
involved).

```python
def test_search_returns_summary_fields(self, client):
    """Search results use PersonSummaryResponse shape."""
    r = client.get(f"{BASE}/search", params={"q": "test"})
    for p in r.json():
        assert "person_pk" in p
        assert "person_id" in p
        assert "first_name" in p
        assert "is_active" in p
        # Summary: no aadhaar, no emergency
        assert "aadhaar_encrypted" not in p
        assert "aadhaar_hash" not in p
        assert "aadhaar_last4" not in p
```

Confirms `/search` returns the same narrow `PersonSummaryResponse` shape as `/persons` — not
the full detail shape — including the same three-way Aadhaar exclusion (`aadhaar_last4`
included) as `TestPersonList.test_list_excludes_sensitive_aadhaar`.
`test_search_excludes_audit_columns` (lines 368–377) runs the matching audit-column check.
`test_search_max_50_results` (lines 385–389) asserts `len(r.json()) <= 50`, pinning the
search endpoint's result cap (distinct from the `limit`/`offset` pagination used by `/persons`
— search has no `offset`, just a hard cap).

| Test | Lines | What it checks |
|---|---|---|
| `test_search_returns_200` | 334–338 | `?q=test` → 200, list |
| `test_search_nonexistent_returns_empty` | 379–383 | `?q=zzzxxyynomatch` → 200 with `[]` |

#### `TestPersonSecurity` (lines 397–429, 5 tests)

```python
def test_person_api_has_security_headers(self, client):
    """Person API responses include the four core security headers."""
    r = client.get(f"{BASE}/persons")
    assert r.status_code == 200
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "camera=()" in r.headers["Permissions-Policy"]


def test_404_has_security_headers(self, client):
    """Even 404 responses get security headers."""
    r = client.get(f"{BASE}/persons/{FAKE_UUID}")
    assert r.status_code == 404
    assert r.headers["X-Content-Type-Options"] == "nosniff"
```

Same four-header pattern as `TestOrganizationSecurity`, plus two tests unique to this class:
`test_search_has_security_headers` (lines 420–423), confirming the headers apply to `/search`
specifically, and `test_404_has_security_headers` — proving the security middleware runs even
on error responses, i.e. it wraps the whole ASGI call chain rather than only successful
handler returns.

| Test | Lines | What it checks |
|---|---|---|
| `test_person_api_has_cache_control_no_store` | 409–412 | `GET /persons` has `Cache-Control: no-store` |
| `test_person_ui_no_cache_control_no_store` | 414–418 | `GET /person` (UI page) does NOT have `Cache-Control: no-store` |

#### `TestPersonUI` (lines 437–521, 15 tests)

The Person Verification UI page structure tests, following the same pattern as
`TestOrganizationUI`, plus two tests unique to Person's data-sensitivity requirements:

```python
def test_page_has_aadhaar_masking(self, client):
    """Page template contains the Aadhaar masking pattern."""
    html = client.get("/person").text
    assert "XXXX XXXX" in html


def test_page_has_search_input(self, client):
    """Page contains a search input for trigram search."""
    html = client.get("/person").text
    assert "trigram" in html.lower()
```

`test_page_has_aadhaar_masking` proves the frontend template itself contains the `XXXX XXXX`
masking pattern used to display Aadhaar values (defense in depth alongside the API-layer
exclusion tests), and `test_page_has_search_input` confirms the page documents its search box
as trigram-backed. `test_page_has_nav_links` (lines 483–489) checks all **four** tier nav links
(`/`, `/foundation`, `/organization`, `/person`) — one more than Organization's three, since
Person is the newest tier. `test_page_has_two_tabs` (lines 491–495) checks for "Persons" and
"Search" (Person's UI has 2 tabs, vs. Organization's 3).

| Test | Lines | What it checks |
|---|---|---|
| `test_person_page_returns_200` | 440–444 | `GET /person` → 200, `text/html` content type |
| `test_page_contains_title` | 446–449 | HTML contains "Person Verification" |
| `test_page_contains_branding` | 451–454 | HTML contains "Nilachala Saraswata Sangha" |
| `test_page_loads_alpine_js` | 456–460 | HTML contains "alpinejs" and "integrity=" (SRI) |
| `test_page_loads_daisyui` | 462–466 | HTML contains "daisyui" and "integrity=" (SRI) |
| `test_page_loads_tailwind` | 468–471 | HTML contains "cdn.tailwindcss.com" |
| `test_page_loads_person_js` | 473–476 | HTML contains "person.js" |
| `test_page_has_alpine_data_binding` | 478–481 | HTML contains `x-data="personApp()"` |
| `test_page_has_system_status_section` | 497–500 | HTML contains "System Status" |
| `test_page_has_nss_logo` | 502–505 | HTML contains "nss-logo.png" |
| `test_page_has_copyright_footer` | 507–511 | HTML contains "2026" and "All rights reserved" |

---

### 2.7 `tests/test_family.py`

**Requirement**

The 4 Tier 4 Family endpoints span 3 tables (`family_group`, `family_relationship`,
`family_head_history`) and — unlike Person — **do** have seed data (one family, "Mishra
Paribara," with 3 current members and 1 head-history record; see
`database/seed/04_family/README.md`), so this file can pin literal counts and field values
directly rather than writing everything defensively. It is nonetheless still guarded with
`pytest.skip("No family data seeded")` wherever a test needs a real `family_group_pk`, so the
suite stays green if it's ever run against a database bootstrapped without the Tier 4
verification seed. This file is the executable specification for the Family API contract, its
`is_current`/`is_active` filtering behaviour, and the Family Verification UI's structure.
**51 tests across 6 classes.**

**Line-by-line**

```python
"""
NSS ERP — Tier 4 Family API tests.

Integration tests for the 4 Family GET endpoints across 3 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Seed data: 1 family (F1 Mishra), 3 members (P1 Ramesh HEAD, P2
Priyanka WIFE, P4 Debasis SON), head history (P1 since 2010).

Endpoint groups tested:
  1. Family List:       /families (with filters)
  2. Family Detail:     /families/{family_group_pk}
  3. Family Members:    /families/{family_group_pk}/members
  4. Head History:      /families/{family_group_pk}/head-history
  5. Security:          security headers, cache control
  6. UI Route:          /family serves HTML
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/family"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"
```

Module docstring states "4 Family GET endpoints across 3 tables" and lists the six test groups —
same shape as `test_person.py`'s and `test_organization.py`'s docstrings. Note the docstring's
own seed-data summary (P1 Ramesh HEAD, P2 Priyanka WIFE, P4 Debasis SON) doesn't quite match the
actual seed file's data (P1 Ramesh FATHER, P2 Sushma SPOUSE, P3 Aniket SON — see
`database/seed/04_family/README.md`) — a stale docstring comment, not a functional issue, since
none of the tests below hardcode "Priyanka" or "P4"; they assert on relationship *type* codes
(`HEAD`... actually `FATHER` per the seed) and counts, which do match the real data.
`pytestmark`, `BASE`, `FAKE_UUID` follow the same convention as every other tier's test file.

```python
def _get_first_family_pk(client):
    """Return the PK of the first family, or None if no data."""
    data = client.get(f"{BASE}/families").json()
    return data[0]["family_group_pk"] if data else None
```

A module-level helper, same `_get_first_*_pk` pattern as `test_person.py`'s
`_get_first_person_pk` and `test_organization.py`'s equivalent — every detail/members/head-history
test calls this first and skips if it returns `None`.

#### `TestFamilyList` (lines 45–166, 17 tests)

```python
def test_seeded_family_has_correct_data(self, client):
    """Seeded family F1 has expected name and status."""
    data = client.get(f"{BASE}/families").json()
    mishra = [f for f in data if f["family_id"] == "F1"]
    if not mishra:
        pytest.skip("F1 Mishra family not seeded")
    f = mishra[0]
    assert f["family_name"] == "Mishra"
    assert f["status_code"] == "ACTIVE"
```

Unlike Person, this test pins a literal expected value (`family_name == "Mishra"`) rather than
just structure — the seed data is deterministic, so the test can assert on it directly, still
wrapped in a `pytest.skip` guard for a database bootstrapped without the seed. (The assertion
checks for the surname "Mishra" as a substring match against the full seeded `family_name`,
"Mishra Paribara" — read literally, `f["family_name"] == "Mishra"` would only pass if the seed
value were exactly "Mishra"; in practice this couples the test tightly to whatever the seed file
currently sets `family_name` to.)

`test_filter_by_sakha_code`/`test_filter_by_status_code`/`test_multiple_filters` exercise
`sakha_code`/`status_code` exactly like `test_organization.py`'s `type_code`/`status_code`
filter tests — both independently combinable, verified by asserting the returned rows' own
`status_code` field matches the filter value. The remaining 10 tests are the standard
pagination contract suite (`limit=0` → 422, `limit=501` → 422, `offset=-1` → 422, `limit=500`
accepted, over-range offset → empty list not error) — byte-for-byte the same pattern
`test_person.py`'s `TestPersonList` and `test_organization.py`'s equivalent already establish
for every paginated list endpoint in the API.

#### `TestFamilyDetail` (lines 174–227, 5 tests)

```python
def test_detail_fake_pk_returns_404(self, client):
    """Fetching a nonexistent family returns 404."""
    r = client.get(f"{BASE}/families/{FAKE_UUID}")
    assert r.status_code == 404
```

The standard fake-UUID-404 / malformed-UUID-422 / valid-PK-200 / required-fields /
audit-column-exclusion quintet used by every detail endpoint's test class across the suite.

#### `TestFamilyMembers` (lines 235–317, 8 tests)

```python
def test_members_seeded_count(self, client):
    """F1 Mishra family has 3 seeded members."""
    pk = _get_first_family_pk(client)
    if pk is None:
        pytest.skip("No family data seeded")
    data = client.get(f"{BASE}/families/{pk}/members").json()
    assert len(data) == 3, f"Expected 3 members, got {len(data)}"
```

```python
def test_members_has_head_relationship(self, client):
    """F1 Mishra has a HEAD relationship (Ramesh)."""
    pk = _get_first_family_pk(client)
    if pk is None:
        pytest.skip("No family data seeded")
    data = client.get(f"{BASE}/families/{pk}/members").json()
    heads = [m for m in data if m["relationship_type_code"] == "HEAD"]
    assert len(heads) == 1, "Expected exactly 1 HEAD"
```

Two data-pinned tests unique to this endpoint group: an exact seeded-count assertion (`== 3`,
not `>= 1`) and a filter-in-Python assertion that exactly one member carries relationship type
code `HEAD`. Read against the actual seed file (`database/seed/04_family/01_tier4_verification_family.sql`),
Ramesh Mishra (`P1`) is actually seeded with relationship type `FATHER`, not `HEAD` — so as
written, `test_members_has_head_relationship` would find zero `HEAD` rows (not one) against the
real seed data and fail on `assert len(heads) == 1`, unless a `HEAD` relationship-type row is
present in some other seed path this file doesn't otherwise account for. `test_members_fake_pk_
returns_404`/`test_members_bad_uuid_returns_422` verify the endpoint's "verify parent exists,
then fetch children" 404 behaviour (see `API_CODE_EXPLANATIONS.md` §2.13), and
`test_members_all_current` asserts every returned row has `is_current: true` — proving the
router's `WHERE fr.is_current = TRUE` filter is actually applied, not just documented.

#### `TestFamilyHeadHistory` (lines 324–392, 7 tests)

```python
def test_head_history_current_head_has_no_end_date(self, client):
    """Current head should have effective_to=None."""
    pk = _get_first_family_pk(client)
    if pk is None:
        pytest.skip("No family data seeded")
    data = client.get(f"{BASE}/families/{pk}/head-history").json()
    current = [h for h in data if h["effective_to"] is None]
    assert len(current) >= 1, "Expected at least 1 current head"
```

The one test that directly exercises the "current head is the row with `effective_to IS NULL`"
convention documented in `API_CODE_EXPLANATIONS.md` §2.13 and enforced at the DDL level by
`uq_family_head_current` (a partial unique index guaranteeing **at most** one such row per
family) — this test only checks **at least** one, which is the correct client-observable
half of that guarantee (the uniqueness half is a database-level invariant, not something an
API integration test needs to re-verify). The remaining 6 tests are the same
404/422/200/required-fields/seeded-count/audit-exclusion pattern as every other sub-resource
list endpoint in the suite.

#### `TestFamilySecurity` (lines 400–427, 4 tests)

```python
def test_family_ui_no_cache_control_no_store(self, client):
    """Family UI page does NOT have Cache-Control: no-store."""
    r = client.get("/family")
    assert r.status_code == 200
    assert r.headers.get("Cache-Control") != "no-store"
```

The same cross-tier security contract verified for every other module in `test_security.py` and
re-verified per-module here: `/api/v1/family/*` responses carry the four core security headers
and `Cache-Control: no-store`, while the `/family` UI page itself does *not* get `no-store`
(HTML pages are cacheable; API JSON responses are not) — and even a 404 response still carries
the security headers, proving `add_security_headers` runs regardless of the eventual status
code.

#### `TestFamilyUI` (lines 435–489, 10 tests)

```python
def test_page_has_nav_links(self, client):
    """Page navigation includes links to tier UIs."""
    html = client.get("/family").text
    assert 'href="/"' in html
    assert 'href="/family"' in html
    assert 'href="/membership"' in html
```

The standard UI-structure smoke-test suite (title, branding, Alpine.js/DaisyUI CDN references,
`family.js` script tag, `x-data="familyApp()"` binding, nav links, NSS logo, copyright footer) —
identical in shape to `TestPersonUI`/`TestOrganizationUI`, just re-pointed at `/family` and
`familyApp()`. The nav-link assertion checking for `/membership` (rather than stopping at
`/person`) is this file's one piece of evidence that the six-tier nav bar (§UI_CODE_EXPLANATIONS
§2.12) was already in place when this test file was written.

---

### 2.8 `tests/test_membership.py`

**Requirement**

The 7 Tier 4 Membership endpoints span 5 tables (`sangha_sevi`, `membership_sakha_affiliation`,
`parichaya_patra`, `anumati_patra`, `membership_journey_event`) and are the executable
specification for the module's central non-obvious concept: the **three-tier identity model**
(Sangha Sevi ID / Local Sakha ERP Number / Kendra Number). Unlike Person, Membership *does* have
real seed data (5 members — see `database/seed/05_membership/README.md`), so most tests pin
literal seeded values (`SS1` is Regular, `SS3` was transferred, etc.) rather than defensively
skipping on empty tables — the file's job is proving the three-tier identity resolves correctly
across every endpoint, that trigram/prefix search covers all three tiers plus name/mobile/email,
and that the transfer/Kumari-transition/Associate-has-no-Anumati-Patra business rules encoded in
the seed data are actually visible through the API. **99 tests across 9 classes** — the largest
test file in the repository.

**Line-by-line**

```python
"""
NSS ERP — Tier 4 Membership API tests.

Integration tests for the 7 Membership GET endpoints across 5 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Seed data: 5 members (SS1 Ramesh Regular, SS2 Aniket Probationary,
SS3 Suresh Transferred Regular, SS4 Debasis Associate, SS5 Smita
Kumari-transition Regular). Historical Anumati Patras for SS1/SS3.
Transfer: SS3 SKH1→SKH2.

Three-tier identity model:
  - Sangha Sevi ID (SS1) — NSS-wide, permanent
  - ERP Number / Local Sakha Number (ESS1192) — Sakha-scoped, auto-generated
  - Kendra Number (345/2026/2027) — Kendra-wide, annual
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/membership"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"
```

The module docstring states "7 Membership GET endpoints across 5 tables," summarizes the 5 seeded
members and their roles in one line each, and restates the three-tier identity model — the same
three lines that appear in `api/routers/membership.py`'s own docstring and
`API_CONTRACT.md` §8, kept in sync across all three so a reader lands on the same mental model
regardless of which file they open first.

```python
def _get_first_member_pk(client):
    """Return the PK of the first member, or None if no data."""
    data = client.get(f"{BASE}/members").json()
    return data[0]["sangha_sevi_pk"] if data else None


def _get_member_by_id(client, sangha_sevi_id):
    """Return the member dict matching the given sangha_sevi_id, or None."""
    data = client.get(f"{BASE}/members").json()
    matches = [m for m in data if m["sangha_sevi_id"] == sangha_sevi_id]
    return matches[0] if matches else None
```

Two module-level helpers. `_get_first_member_pk` is the same `pytest.skip`-if-empty pattern used
by every other tier's "get any valid PK" helper. `_get_member_by_id` is new — Membership is the
first module where individual seeded rows have known, permanent business identifiers (`SS1`
through `SS5`) worth looking up by name rather than by position, since so many tests need to
assert something specific about *this particular member* (e.g. "SS3 was transferred," "SS4 is
Associate"). Nearly every test that depends on a specific seeded member calls this helper and
`pytest.skip(f"{id} not seeded")` if it returns `None` — the same availability-guard discipline
as `test_person.py`, applied to named rows instead of "any row."

#### `TestMemberList` (lines 62–213, 20 tests)

```python
def test_list_has_required_fields_if_data(self, client):
    """Each member has the expected response fields."""
    required = {
        "sangha_sevi_pk", "sangha_sevi_id",
        "person_pk", "person_id",
        "first_name", "middle_name", "last_name",
        "membership_type_master_data_pk",
        "membership_type_code", "membership_type_name",
        "membership_status_master_data_pk",
        "status_code", "status_name",
        "organization_pk", "organization_name", "organization_code",
        "local_sakha_erp_id",
        "joining_date", "renewal_due_date",
        "remarks", "is_active",
    }
    for m in client.get(f"{BASE}/members").json():
        assert required.issubset(m.keys()), (
            f"Missing fields in member {m.get('sangha_sevi_id', '?')}: "
            f"{required - m.keys()}"
        )
```

Proves `MemberResponse` carries both Tier 1 (`sangha_sevi_id`) and Tier 2 (`local_sakha_erp_id`)
identity fields plus resolved person/type/status/organization context — the same "one big
resolved row" shape `_MEMBER_SELECT` builds via five JOINs in the router. This exact required-set
is repeated verbatim in `TestMemberDetail.test_detail_has_required_fields`, since both endpoints
share `MemberResponse`.

```python
def test_seeded_member_ss1_is_regular(self, client):
    """SS1 (Ramesh) is a Regular member."""
    m = _get_member_by_id(client, "SS1")
    if m is None:
        pytest.skip("SS1 not seeded")
    assert m["membership_type_code"] == "REGULAR"
    assert m["status_code"] == "ACTIVE"
```

Three near-identical tests (`test_seeded_member_ss1_is_regular`, `_ss2_is_probationary`,
`_ss4_is_associate`) each pin one seeded member's `membership_type_code`, directly verifying the
seed file's own claims (`SS1`/`SS3` Regular, `SS2`/`SS5` Probationary, `SS4` Associate) actually
surface through the API — not just that the INSERT succeeded, but that the type/status JOINs
resolve to the right `master_data` row.

```python
def test_filter_by_type_code(self, client):
    """Filtering by type_code returns only matching members."""
    r = client.get(f"{BASE}/members", params={"type_code": "REGULAR"})
    assert r.status_code == 200
    for m in r.json():
        assert m["membership_type_code"] == "REGULAR"
```

Three independent filters (`type_code`, `status_code`, `org_code`) each get their own
every-row-matches test, the same rigor as Organization's/Person's filter tests, plus
`test_filter_nonexistent_type_returns_empty` (fabricated code → `200 []`, not 404) and
`test_multiple_filters` (all three combined in one request, proving `AND`-composition). The
pagination group (6 tests: custom limit, `limit=0`→422, `limit=501`→422, `offset=-1`→422,
`offset=9999`→`200 []`, `limit=500`→200) is identical in shape to every other tier's pagination
suite — Membership reuses the same `DEFAULT_LIMIT`/`MAX_LIMIT` constants from `api/helpers.py`.

| Test | What it checks |
|---|---|
| `test_list_returns_200` | `GET /members` → 200, list |
| `test_list_all_active` | Every returned member has `is_active is True` |
| `test_list_excludes_audit_columns` | 6 audit columns absent from every row |
| `test_list_returns_seeded_members` | At least 5 seeded members exist |
| `test_members_have_local_sakha_erp_id` | At least 1 member has a non-null `local_sakha_erp_id` |

#### `TestMemberDetail` (lines 221–281, 5 tests)

Same 404/422/200/required-fields/audit-exclusion pattern as every other tier's detail endpoint
(`test_detail_fake_pk_returns_404`, `test_detail_bad_uuid_returns_422`,
`test_detail_valid_pk_returns_200`, `test_detail_has_required_fields`,
`test_detail_excludes_audit_columns`) — no Membership-specific behaviour here beyond reusing
`MemberResponse`'s field set from `TestMemberList`.

#### `TestMemberSearch` (lines 288–434, 16 tests)

```python
def test_search_by_erp_number(self, client):
    """Searching by ERP Number prefix finds the member."""
    members = client.get(f"{BASE}/members").json()
    erp_members = [m for m in members if m["local_sakha_erp_id"]]
    if not erp_members:
        pytest.skip("No members with ERP numbers seeded")
    erp_id = erp_members[0]["local_sakha_erp_id"]
    data = client.get(f"{BASE}/search", params={"q": erp_id[:3]}).json()
    erp_ids = [m["local_sakha_erp_id"] for m in data]
    assert erp_id in erp_ids, (
        f"Expected {erp_id} in search results, got: {erp_ids}"
    )
```

This is the largest class in the file, and the only one to directly exercise all **three**
identity tiers as independent search paths: `test_search_by_sangha_sevi_id` (Tier 1 prefix),
`test_search_by_erp_number` (Tier 2 prefix, shown above — discovers a real seeded ERP number
first rather than hardcoding one, so the test survives seed-data changes), and
`test_search_by_kendra_number` (Tier 3 prefix, fetched via a nested call to the Parichaya Patra
sub-endpoint for SS1 before extracting the prefix before the first `/`) — plus
`test_search_by_person_id`, `test_search_by_name_trigram`, `test_search_by_mobile_number`, and
`test_search_by_email` covering the four non-tiered match paths. Together these seven tests are
the executable proof of `api/routers/membership.py::search_members`'s WHERE clause, field by
field.

```python
def test_search_by_email(self, client):
    """Searching by email prefix finds the member."""
    # P1 (SS1) has email 'ramesh.mishra@example.com'
    data = client.get(f"{BASE}/search", params={"q": "ramesh.mishra"}).json()
    ids = [r["sangha_sevi_id"] for r in data]
    assert "SS1" in ids, f"Expected SS1 when searching by email prefix, got: {ids}"
```

Notably searches `"ramesh.mishra"` — a string containing a `.` — which exercises the router's
`re.split(r'[.@]', q)[0]` email-prefix handling (splits to `"ramesh"` for the trigram comparison
while still using the full string for the `ILIKE` email-prefix match) without asserting on the
split logic directly; the test only cares that the end-to-end result still finds `SS1`.

| Test | What it checks |
|---|---|
| `test_search_requires_q` | Omitting `q` → 422 |
| `test_search_q_too_short_returns_422` | `q="A"` (1 char) → 422 |
| `test_search_returns_200` | `q="SS"` → 200, list |
| `test_search_nonexistent_returns_empty` | `q="ZZZZNOTEXIST99"` → `200 []` |
| `test_search_max_50_results` | `len(results) <= 50` |
| `test_search_returns_member_response_fields` | Search results use full `MemberResponse` shape |
| `test_search_excludes_audit_columns` | Audit columns absent |
| `test_search_only_returns_active_members` | Every result has `is_active is True` |
| `test_search_has_security_headers` | `/search` carries the four core headers + `Cache-Control: no-store` |

#### `TestMemberAffiliations` (lines 442–513, 7 tests)

```python
def test_transferred_member_has_archived_and_active(self, client):
    """SS3 should have one ARCHIVED and one ACTIVE affiliation."""
    m = _get_member_by_id(client, "SS3")
    if m is None:
        pytest.skip("SS3 not seeded")
    data = client.get(f"{BASE}/members/{m['sangha_sevi_pk']}/affiliations").json()
    statuses = {a["affiliation_status"] for a in data}
    assert "ARCHIVED" in statuses, "Expected ARCHIVED affiliation for transfer"
    assert "ACTIVE" in statuses, "Expected ACTIVE affiliation at new Sakha"
```

Beyond the standard 404/422/200/required-fields/audit-exclusion set, this class has two tests
specific to the seeded transfer scenario: `test_transferred_member_has_multiple_affiliations`
(SS3 has ≥2 affiliation rows) and the one above, which confirms the *specific* status split the
DDL's `chk_mem_sakha_aff_status_consistency` constraint guarantees — the old Sakha's row is
`ARCHIVED` (closed, `effective_to` set) and the new Sakha's row is `ACTIVE` (open-ended) — proving
`membership_sakha_affiliation`'s "current + history via row closure" design (see
`database/ddl/05_membership/README.md`) is both stored correctly and visible through the API.

#### `TestParichayaPatra` (lines 521–607, 8 tests)

```python
def test_probationary_has_no_parichaya_patra(self, client):
    """SS2 (Probationary) should have no Parichaya Patra."""
    m = _get_member_by_id(client, "SS2")
    if m is None:
        pytest.skip("SS2 not seeded")
    data = client.get(
        f"{BASE}/members/{m['sangha_sevi_pk']}/parichaya-patra"
    ).json()
    assert len(data) == 0, "Probationary member should not have PP"
```

`test_regular_member_has_parichaya_patra` (SS1, ≥1 record) and this test are a matched pair
proving the business rule "only Regular/Associate members receive a Parichaya Patra" is a fact
about the *seed data*, not something the API enforces — the endpoint itself has no type-based
filtering; it simply returns whatever `parichaya_patra` rows exist for the given
`sangha_sevi_pk`. `test_pp_document_number_is_kendra_number` only asserts `"/" in doc` — a loose
format check (Kendra numbers are `<seq>/<FY start>/<FY end>`), deliberately not over-specified
against the exact seeded value so the test survives future seed changes.

#### `TestAnumatiPatra` (lines 615–712, 9 tests)

```python
def test_regular_member_has_historical_expired_ap(self, client):
    """SS1 (Regular, was Probationary) has EXPIRED Anumati Patra."""
    m = _get_member_by_id(client, "SS1")
    if m is None:
        pytest.skip("SS1 not seeded")
    data = client.get(
        f"{BASE}/members/{m['sangha_sevi_pk']}/anumati-patra"
    ).json()
    expired = [ap for ap in data if ap["status"] == "EXPIRED"]
    assert len(expired) >= 1, (
        "Expected EXPIRED AP for SS1 (was probationary before Regular)"
    )
```

`test_regular_member_has_historical_expired_ap` and `test_ss3_has_historical_expired_ap` are
this class's most conceptually important tests: they prove Anumati Patra history survives
promotion to Regular — a member who has since been promoted still has their old, `EXPIRED`
credential retrievable, not deleted, consistent with the project's frozen "History Never
Deleted" principle. `test_probationary_has_anumati_patra` (SS2, ≥1 `ACTIVE` record) and
`test_ap_document_number_format` (`doc.startswith("AP/")`) round out the seed-specific
assertions; the remaining four tests (`_fake_pk_404`, `_bad_uuid_422`, `_valid_pk_200`,
`_has_required_fields`, `_excludes_audit_columns`) follow the standard sub-resource pattern.

#### `TestJourneyEvents` (lines 720–807, 9 tests)

```python
def test_kumari_transition_has_event(self, client):
    """SS5 (Smita, Kumari→Membership) has KUMARI_TRANSITION event."""
    m = _get_member_by_id(client, "SS5")
    if m is None:
        pytest.skip("SS5 not seeded")
    data = client.get(f"{BASE}/members/{m['sangha_sevi_pk']}/journey").json()
    event_types = {e["event_type"] for e in data}
    assert "KUMARI_TRANSITION" in event_types, (
        f"Expected KUMARI_TRANSITION event for SS5, got: {event_types}"
    )
```

`test_transferred_member_has_transfer_event` (SS3, `TRANSFER` in `event_types`) and this test
each pin one seeded member's lifecycle narrative to a specific `event_type` string —
`membership_journey_event.event_type` is a free-form `VARCHAR`, not an FK to `master_data` (see
`database/ddl/05_membership/README.md`), so these tests are the only guard that the *application
layer's* event-type vocabulary (`TRANSFER`, `KUMARI_TRANSITION`, `MEMBERSHIP_CREATED`,
`REGULAR_ENROLMENT`, `ASSOCIATE_ENROLMENT`, …) stays consistent between seed data and any future
consumer. `test_journey_events_ordered_by_date` asserts `dates == sorted(dates)` only when
`len(data) >= 2`, confirming the router's `ORDER BY mje.event_date ASC` without requiring a
specific event count.

#### `TestMembershipSecurity` (lines 815–848, 5 tests)

The same four-header-plus-cache-control contract verified per-module throughout the suite
(`test_membership_api_has_security_headers`, `test_membership_api_has_cache_control_no_store`,
`test_membership_ui_no_cache_control_no_store`, `test_404_has_security_headers`), plus one test
unique to Membership's deeper URL nesting:

```python
def test_sub_endpoints_have_security_headers(self, client):
    """Sub-resource 404s also get security headers."""
    r = client.get(f"{BASE}/members/{FAKE_UUID}/affiliations")
    assert r.status_code == 404
    assert r.headers["X-Content-Type-Options"] == "nosniff"
```

Membership is the first module with four distinct sub-resource routes hanging off a single
detail PK (`/affiliations`, `/parichaya-patra`, `/anumati-patra`, `/journey`); this test spot-checks
one of them to confirm `add_security_headers` wraps sub-resource 404s too, not just the top-level
`/members` and `/members/{pk}` routes.

#### `TestMembershipUI` (lines 856–967, 20 tests)

The standard UI-structure smoke-test suite (title, branding, Alpine.js/DaisyUI CDN references,
`membership.js` script tag, `x-data="membershipApp()"` binding, nav links, NSS logo, copyright
footer, tab bar) plus several Membership-specific assertions:

```python
def test_page_has_three_tier_legend(self, client):
    """Page contains the three-tier identity legend."""
    html = client.get("/membership").text
    assert "Sangha Sevi ID" in html
    assert "Sakha Sangha ID" in html


def test_page_has_darshaka_filter(self, client):
    """Page type filter includes Darshaka (not Probationary)."""
    html = client.get("/membership").text
    assert "Darshaka" in html


def test_anumati_patra_hidden_for_associate(self, client):
    """Anumati Patra section is conditionally hidden for Associate members."""
    html = client.get("/membership").text
    assert "membership_type_code !== 'ASSOCIATE'" in html
```

`test_page_has_three_tier_legend` and `test_page_has_sakha_sangha_id_label` both guard the
three-tier identity legend and the "Sakha Sangha ID" UI-label convention (see
`frontend/README.md`'s `membership.html` section) — the database column is `local_sakha_erp_id`,
but the UI never shows that name to a user. `test_page_has_darshaka_filter` guards the
`typeDisplayName()` UI convention that displays `PROBATIONARY` as "Darshaka" (MBR-007).
`test_anumati_patra_hidden_for_associate` is a literal substring match on the Alpine `x-show`
directive itself (`membership_type_code !== 'ASSOCIATE'`) — a white-box assertion that the
conditional-hide logic exists in the template at all, complementing
`TestAnumatiPatra.test_ap_has_required_fields`'s black-box proof that Associate members' API
responses are empty. `test_search_auto_selects_single_result` inspects
`assets/js/membership.js` directly (not the HTML) for the `searchResults.length === 1` /
`selectMember` auto-select pattern shared with `person.js`.

| Test | What it checks |
|---|---|
| `test_membership_page_returns_200` | `GET /membership` → 200, `text/html` |
| `test_page_contains_title` / `_branding` | "Membership" / "Nilachala Saraswata Sangha" in HTML |
| `test_page_loads_alpine_js` / `_daisyui` / `_membership_js` | CDN + script tag references |
| `test_page_has_alpine_data_binding` | `x-data="membershipApp()"` |
| `test_page_has_nav_links` | Links to `/`, `/family`, `/membership` |
| `test_page_has_tab_bar` | `switchTab('members')` / `switchTab('search')` |
| `test_page_has_search_tab_content` / `_search_detail_panel` | "Member Search" heading; ≥2 "Member Detail" headings (one per tab) |
| `test_page_has_person_id_column` | "Person ID" column present |
| `test_page_has_nss_logo` / `_copyright_footer` | Logo + "All rights reserved" |

---

## 3. Cross-references

- **`docs/03_Solution/code_explanations/API_CODE_EXPLANATIONS.md`** — the
  routers/schemas that `test_bootstrap.py`, `test_foundation.py`, `test_organization.py`,
  `test_person.py`, and `test_membership.py` exercise.
- **`docs/03_Solution/api/API_CONTRACT.md`** — the Tier 4 Membership API contract (§8) that
  `test_membership.py` is the executable specification for, including the three-tier identity
  model and the full search-fields table.
- **`database/ddl/05_membership/README.md`** and
  **`database/seed/05_membership/README.md`** — the table design and seed-data reference
  that many `test_membership.py` assertions (transfer, Kumari transition, Associate-has-no-AP)
  are directly checking against.
- **`docs/03_Solution/code_explanations/SECURITY_CODE_EXPLANATIONS.md`** — the
  middleware that `test_security.py` exercises and that `test_organization.py`'s
  `TestOrganizationSecurity` class and `test_person.py`'s `TestPersonSecurity` class each
  verify per-tier.
- **`docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`** — the Tier 1 Foundation API
  contract that `test_foundation.py` is the executable specification for.
- **`docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`** — the Tier 2 Organization API
  contract that `test_organization.py` is the executable specification for.
- **`docs/03_Solution/code_explanations/TIER0_SECURITY_AUDIT.md`** and
  **`TIER1_SECURITY_AUDIT.md`** — the security audit verdicts, not retired by this document.
