# tests/

Structured test suite for the NSS ERP application. Tests are organised into
four categories under separate subdirectories.

## Directory Structure

```
tests/
├── conftest.py          # Shared fixtures: DB connection, SAVEPOINT rollback, TestClient
├── README.md            # This file
│
├── api/                 # API integration tests (FastAPI TestClient, no browser)
│   ├── test_admin.py         # Tier 5 — admin CRUD, roles, orgs (72 tests)
│   ├── test_audit.py         # Tier 5 — field-change-log viewer (4 tests)
│   ├── test_auth.py          # Tier 5 — login, refresh, logout, change-password (16 tests)
│   ├── test_bootstrap.py     # Tier 0 — health, roles, permissions (9 tests)
│   ├── test_claim_approval.py # Tier 5 — claim detail/edit/scope enforcement (11 tests)
│   ├── test_error_messages.py # Human-readable validation/integrity-error messages (15 tests)
│   ├── test_family.py        # Tier 4 — family list, detail, members (52 tests)
│   ├── test_family_ownership.py # Tier 5 — role-less-JWT ownership path: graph, add/remove
│   │                          #   member, admin assign/revoke, transfer-head (20 tests)
│   ├── test_forgot_password.py  # Tier 5 — forgot/reset password (6 tests)
│   ├── test_foundation.py    # Tier 1 — master data, config, geographic (45 tests)
│   ├── test_membership.py    # Tier 4 — membership list, search, affiliations (94 tests)
│   ├── test_organization.py  # Tier 2 — org types, hierarchy, children (58 tests)
│   ├── test_person.py        # Tier 3 — person list, detail, search (55 tests)
│   ├── test_registration.py  # Tier 5 — self-registration, claim approval (14 tests)
│   ├── test_sakha_branches.py # Tier 2 — 175 Sakha branch seed data (33 tests)
│   └── test_sorting.py       # Shared column-sort-whitelist helper (14 tests)
│
├── db/                  # Database integrity tests (direct SQL via write_conn)
│   └── test_data_integrity.py  # Cross-module entity smoke tests (23 tests)
│
├── security/            # Cross-tier security assertions (added after the api/db/ui split
│   │                     above; not a rename of anything)
│   ├── test_admin_security.py         # Admin endpoint auth/RBAC gating (17 tests)
│   ├── test_audit_security.py         # Audit endpoint auth/RBAC gating (4 tests)
│   ├── test_auth_security.py          # Auth endpoint auth gating (4 tests)
│   ├── test_forgot_password_security.py # Forgot-password rate-limit/anti-enumeration (6 tests)
│   ├── test_registration_security.py  # Registration endpoint gating (3 tests)
│   └── test_security_headers.py       # Headers, CSP, rate limiting, CORS, DEBUG_MODE (24 tests)
│
└── ui/                  # Browser UI tests (Playwright + Chromium, headless)
    ├── conftest.py              # Browser/page fixtures, login helpers
    │
    │   ── Numbered files run sequentially (DB state cascades) ──
    ├── test_ui_06_register_submit.py # Registration: membership claim, address, full submission
    ├── test_ui_07_admin_write.py    # Admin: claim approve, status change, role assign, password
    │
    │   ── Unnumbered files (independent, any order) ──
    ├── test_ui_login.py             # Login form, validation, force-password-change, redirect
    ├── test_ui_register.py          # Registration 3-step navigation, field validation
    ├── test_ui_dashboard.py         # Dashboard: all tabs, content rendering, edit profile,
    │                                #   admin tabs, family state, documents, logout (52 tests)
    ├── test_ui_forgot_password.py   # Forgot/reset password flow
    ├── test_ui_admin_users.py       # User list, search, filters, detail, INACTIVE styling
    ├── test_ui_admin_persons.py     # Create person form, mandatory fields
    ├── test_ui_admin_create_user.py # Create user account, reactivation
    ├── test_ui_admin_roles.py       # Role assignment modal, dropdowns
    ├── test_ui_admin_claims.py      # Registration claims tabs, detail view
    ├── test_ui_admin_status.py      # Status change modal (ACTIVE/LOCKED/INACTIVE)
    └── test_ui_admin_orgs.py        # Organizations tab, table
```

**Current grand total: 733 tests** (AST-counted `test_*` functions) — `tests/api/` (518, across
16 files), `tests/db/` (23), `tests/security/` (58), `tests/ui/` (134). This corrects a
previously-stated "620" that predated `test_error_messages.py`/`test_family_ownership.py`/
`test_sorting.py` (all new) and the growth of `test_admin.py` (38→72), `test_person.py`
(41→55), and `test_membership.py` (78→94) as their routers gained endpoints. The per-file
counts above also reflect
`tests/security/`'s extraction of auth-gating/401/403/RBAC assertions out of `test_admin.py`,
`test_auth.py`, `test_registration.py`, `test_forgot_password.py`, `test_foundation.py`, and
`test_audit.py` — that's a move, not lost coverage, plus `test_security_headers.py` is
genuinely new coverage. The old flat `tests/api/test_security.py` (8 tests) no longer exists,
fully absorbed into `tests/security/`. `pytest.ini` declares `integration`/`ui`/`db` markers
only — `tests/security/` files use `pytest.mark.integration`, same as `tests/api/`, so there's
no separate `security` marker.

## `conftest.py` — fixture architecture

The root `conftest.py` holds a **single session-scoped write-pool connection** (`_db_conn`,
via `api/database.py::get_write_pool()`) for the entire pytest run, wraps each test *module*
in a PostgreSQL `SAVEPOINT` (`_module_savepoint`, autouse), and overrides both `get_connection`
and `get_write_connection` FastAPI dependencies to yield that same connection. At the end of
each module, `ROLLBACK TO SAVEPOINT` undoes every INSERT/UPDATE/DELETE the module's tests
made. `_reset_rate_limiter` (autouse, function-scoped) resets `api.main.limiter`'s in-memory
storage before every test.

**Implication for anyone adding a test:** don't assume any row already exists — either create
what you need via `write_conn` inside a fixture, or `pytest.skip()` gracefully.

## Running

```bash
# ── All tests (API + DB + security + UI) ──────────────
pytest

# ── By category ───────────────────────────────────────
pytest tests/api/              # API integration tests only
pytest tests/db/               # database integrity tests only
pytest tests/security/         # cross-tier security assertions only
pytest tests/ui/               # UI browser tests only

# ── By marker ─────────────────────────────────────────
pytest -m integration          # tests/api/ + tests/db/ + tests/security/ (all carry this marker)
pytest -m db                   # database tests
pytest -m ui                   # UI tests

# ── Individual files ──────────────────────────────────
pytest tests/api/test_auth.py           # Tier 5 auth only
pytest tests/ui/test_ui_login.py        # Login UI only

# ── UI tests with visible browser ────────────────────
pytest tests/ui/ --headed               # watch the browser
pytest tests/ui/ --headed --slowmo 500  # slow down for debugging

# ── Single test ───────────────────────────────────────
pytest tests/api/test_bootstrap.py::TestHealth::test_health_returns_ok
```

## Prerequisites

### API & DB tests
- Local PostgreSQL running with nss schema bootstrapped
- `api/.env` configured with DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT,
  DB_WRITE_USER, DB_WRITE_PASSWORD, JWT_SECRET_KEY
- `pytest` and `httpx` installed

### UI tests (additional)
- Local server running: `python3 -m uvicorn api.main:app --port 8001`
- Playwright + Chromium installed:
  ```bash
  pip install pytest-playwright
  playwright install chromium
  ```
- Test admin account (SS1) bootstrapped via `scripts/bootstrap_admin.py`
- **Note:** SS1 has `force_password_change = TRUE` on first login.
  The test fixtures handle this automatically, changing the password
  to `NSSTest@1` on the first run.
- **Note:** UI tests run against the live database — they are NOT wrapped in
  SAVEPOINT rollback. Tests that create data should clean up after themselves
  or use test-specific identifiers.

## Related docs

- `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` — Tier 1 API contract
- `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md` — Tier 2 API contract
- `docs/03_Solution/api/PERSON_API_CONTRACT.md` — Tier 3 API contract
