# Testing Layer — Per-File Code Explanations

| Field       | Value                                    |
|-------------|-------------------------------------------|
| Document    | TESTING_CODE_EXPLANATIONS                 |
| Version     | 1.1                                       |
| Scope       | All pytest integration tests under `tests/` |
| Status      | Complete (updated: Tier 2 Organization)   |

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

**64 tests total** across 4 files: `test_bootstrap.py` (12 — 9 API + 12 UI), `test_foundation.py`
(47 — 34 API + 13 UI), `test_organization.py` (48 — 29 API + 15 UI + 3 security + 1 hierarchy
endpoint), `test_security.py` (8), plus `conftest.py`'s shared fixture (no tests of its own).

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
hierarchy traversal, combinable type/status filters, parent-existence-checked children
endpoint, and a 27-field response model — every one of which needs its own regression guard.
This file is the executable specification for the entire Tier 2 Organization API contract,
plus UI structure tests for the Organization Verification UI page and security-header
verification for the Organization endpoints.

**Line-by-line**

```python
"""
NSS ERP — Tier 2 Organization API tests.

Integration tests for the 6 Organization GET endpoints across 3 tables.
Runs against local PostgreSQL (not Neon). The database must be
bootstrapped with DDL + seed before running.

Endpoint groups tested:
  1. Reference Data: types, statuses
  2. Organizations:  list (with filters), detail, children
  3. Hierarchy:      recursive CTE tree
  4. UI Route:       /organization serves HTML
"""

import pytest


pytestmark = pytest.mark.integration

BASE = "/api/v1/organization"
FAKE_UUID = "00000000-0000-0000-0000-000000000000"
```

Module docstring states "6 Organization GET endpoints across 3 tables," lists the four
test groups, and notes the database prerequisites. `pytestmark = pytest.mark.integration`
is the same pattern as the other test files. `BASE` and `FAKE_UUID` are module-level
constants to avoid repetition — identical to the approach in `test_foundation.py`.

#### `TestOrganizationTypes` (lines 29–70, 4 tests)

| Test | What it checks |
|---|---|
| `test_list_returns_200` | `GET /types` → 200, non-empty list |
| `test_list_has_required_fields` | 6-field `required` set (`organization_type_pk`, `organization_type_code`, `organization_type_name`, `description`, `sort_order`, `is_active`) is a subset of every returned type's keys; asserts `is_active is True` |
| `test_list_returns_8_frozen_types` | Exactly 8 types; codes == `{KENDRA, NILACHALA_KUTIRA, SMRUTI_MANDIRA, ANCHALIKA_SANGHA, ZILLA_SANGHA, SAKHA_SANGHA, SAKHA_ASANA, PATHA_CHAKRA}` |
| `test_list_ordered_by_sort_order` | `sort_order` values are in ascending order |

The structure mirrors `TestFoundationCountries` / `TestFoundationStates` — the same
four-test pattern (200, fields, count+codes, ordering) applied to a different reference
table.

#### `TestOrganizationStatuses` (lines 73–112, 4 tests)

Same shape as `TestOrganizationTypes`:

| Test | What it checks |
|---|---|
| `test_list_returns_200` | `GET /statuses` → 200, non-empty list |
| `test_list_has_required_fields` | 6-field required set check; asserts `is_active` |
| `test_list_returns_6_statuses` | Exactly 6; codes == `{PROPOSED, APPROVED, ACTIVE, INACTIVE, SUSPENDED, ARCHIVED}` |
| `test_list_ordered_by_sort_order` | `sort_order` values ascending |

#### `TestOrganizations` (lines 120–221, 14 tests)

The largest test class in the file, covering list, filters, detail, and geographic
resolution:

```python
def test_list_has_required_fields(self, client):
    """Each organization has expected fields including JOINed context."""
    required = {
        "organization_pk", "organization_id", "organization_name",
        "organization_code",
        "organization_type_pk", "organization_type_code",
        "organization_type_name",
        "organization_status_pk", "organization_status_code",
        "organization_status_name",
        "parent_organization_pk", "parent_organization_name",
        "address_line_1", "address_line_2",
        "district_pk", "district_name",
        "state_pk", "state_name",
        "country_pk", "country_name",
        "city_village_pk", "city_village_name",
        "postal_code_pk", "postal_code",
        "latitude", "longitude",
        "is_active",
    }
    for org in client.get(f"{BASE}/organizations").json():
        assert required.issubset(org.keys())
```

Checks all 27 fields of `OrganizationResponse` are present, including all JOINed context
fields from type, status, parent, and 5 geographic tables. This is the most comprehensive
field check in the entire test suite — Foundation's largest response model has 8 fields;
Organization's has 27.

| Test | What it checks |
|---|---|
| `test_list_returns_200` | `GET /organizations` → 200, non-empty |
| `test_list_has_required_fields` | 27-field required set check |
| `test_list_returns_3_seeded_orgs` | `len == 3`; codes == `{KEN, NKT, SMR}` |
| `test_list_all_active` | Every org has `is_active is True` |
| `test_list_all_roots` | Every org has `parent_organization_pk is None` and `parent_organization_name is None` |
| `test_filter_by_type_code` | `?type_code=KENDRA` → 1 result with matching type code |
| `test_filter_by_status_code` | `?status_code=ACTIVE` → every result has matching status code |
| `test_filter_nonexistent_type_returns_empty` | `?type_code=ZZZZZ_FAKE` → 200 with `[]` |
| `test_detail_valid_pk` | `GET /organizations/{pk}` → 200, returned `organization_pk` matches |
| `test_detail_fake_pk_returns_404` | All-zero UUID → 404 |
| `test_detail_bad_uuid_returns_422` | `"not-a-uuid"` → 422 |
| `test_detail_has_resolved_country` | Kendra org has `country_name is not None` (LEFT JOIN resolution works) |
| `test_detail_has_postal_code` | Kendra org has `postal_code is not None` |

The last two tests (`test_detail_has_resolved_country`, `test_detail_has_postal_code`) are
unique to Organization — they verify that the 6 LEFT JOINs in `_ORG_SELECT` actually resolve
nullable geographic FK columns to non-NULL display names for the Kendra seed record. If any
of the 6 LEFT JOINs were accidentally changed to INNER JOINs, the Kendra row (which lacks
some geographic FKs) would vanish from the result set entirely, causing `test_list_returns_3_seeded_orgs`
to fail.

#### `TestOrganizationChildren` (lines 229–257, 4 tests)

| Test | What it checks |
|---|---|
| `test_children_returns_200` | Valid parent PK → 200, list |
| `test_children_empty_for_leaf_org` | Seeded root orgs have no children → `[]` |
| `test_children_fake_pk_returns_404` | All-zero UUID → 404 (parent existence check) |
| `test_children_bad_uuid_returns_422` | `"not-a-uuid"` → 422 |

The 404 test is critical: the `/organizations/{pk}/children` endpoint first checks that the
parent exists (a `SELECT` against `nss.organization`), and only then queries for children.
Without that guard, any UUID — valid or not — would return `200 []`, making it impossible
to distinguish "org exists but has no children" from "org doesn't exist."

#### `TestHierarchy` (lines 265–298, 4 tests)

| Test | What it checks |
|---|---|
| `test_hierarchy_returns_200` | `GET /hierarchy` → 200, non-empty |
| `test_hierarchy_has_required_fields` | 10-field required set (`organization_pk`, `organization_name`, `organization_code`, `organization_type_code`, `organization_type_name`, `organization_status_code`, `organization_status_name`, `parent_organization_pk`, `depth`, `is_active`) |
| `test_hierarchy_roots_at_depth_0` | All nodes have `depth == 0` and `parent_organization_pk is None` (only roots seeded) |
| `test_hierarchy_returns_3_nodes` | Exactly 3 nodes (matching 3 seeded root orgs) |

With only root organizations seeded, the recursive CTE's anchor member returns 3 rows at
`depth = 0` and the recursive member returns no additional rows. When child organizations
are seeded in future tiers, `test_hierarchy_roots_at_depth_0` will need updating to account
for `depth > 0` nodes, but `test_hierarchy_has_required_fields` and the 200/non-empty check
will remain valid.

#### `TestOrganizationUI` (lines 306–380, 15 tests)

The Organization Verification UI page structure tests. Same pattern as `TestBootstrapUI`
and `TestFoundationUI` — testing that the HTML page served by the UI route includes
the expected structural elements:

| Test | What it checks |
|---|---|
| `test_organization_page_returns_200` | `GET /organization` → 200, `text/html` content type |
| `test_page_contains_title` | HTML contains "Organization Verification" |
| `test_page_contains_branding` | HTML contains "Nilachala Saraswata Sangha" |
| `test_page_loads_alpine_js` | HTML contains "alpinejs" and "integrity=" (SRI) |
| `test_page_loads_daisyui` | HTML contains "daisyui" and "integrity=" (SRI) |
| `test_page_loads_tailwind` | HTML contains "cdn.tailwindcss.com" |
| `test_page_loads_organization_js` | HTML contains "organization.js" |
| `test_page_has_alpine_data_binding` | HTML contains `x-data="organizationApp()"` |
| `test_page_has_nav_links` | HTML contains `href="/"`, `href="/foundation"`, `href="/organization"` (all 3 tiers) |
| `test_page_has_three_tabs` | HTML contains "Reference Data", "Organizations", "Hierarchy" |
| `test_page_has_system_status_section` | HTML contains "System Status" |
| `test_page_has_nss_logo` | HTML contains "nss-logo.png" |
| `test_page_has_copyright_footer` | HTML contains "2026" and "All rights reserved" |

Two tests are unique to Organization and absent from Bootstrap/Foundation:
`test_page_has_three_tabs` (verifying the 3-tab structure) and
`test_page_loads_organization_js` (verifying the tier-specific JS file).

#### `TestOrganizationSecurity` (lines 388–409, 3 tests)

Verifies the security middleware applies to Organization endpoints specifically — the
cross-tier `test_security.py` only tests Bootstrap/frontend routes:

| Test | What it checks |
|---|---|
| `test_org_api_has_security_headers` | `GET /types` → 200, has `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `camera=()` in `Permissions-Policy` |
| `test_org_api_has_cache_control_no_store` | `GET /organizations` has `Cache-Control: no-store` |
| `test_org_ui_no_cache_control_no_store` | `GET /organization` (UI page) does NOT have `Cache-Control: no-store` |

The third test (`test_org_ui_no_cache_control_no_store`) is a deliberate inversion: HTML
pages should be cacheable by the browser, so the middleware's `no-store` header — applied
only to `/api/` paths — must **not** appear on the UI route. This confirms the path-based
conditional in `middleware.py` works correctly for Organization routes.

---

## 3. Cross-references

- **`docs/03_Solution/architecture/code_explanations/API_CODE_EXPLANATIONS.md`** — the
  routers/schemas that `test_bootstrap.py`, `test_foundation.py`, and `test_organization.py` exercise.
- **`docs/03_Solution/architecture/code_explanations/SECURITY_CODE_EXPLANATIONS.md`** — the
  middleware that `test_security.py` exercises and that `test_organization.py`'s `TestOrganizationSecurity` class verifies per-tier.
- **`docs/03_Solution/architecture/FOUNDATION_API_CONTRACT.md`** — the Tier 1 Foundation API
  contract that `test_foundation.py` is the executable specification for.
- **`docs/03_Solution/architecture/code_explanations/TIER0_SECURITY_AUDIT.md`** and
  **`TIER1_SECURITY_AUDIT.md`** — the security audit verdicts, not retired by this document.
