# tests/

pytest integration tests for the FastAPI application. Configured via `pytest.ini` (repo root):
`testpaths = tests`, `python_files = test_*.py`, custom marker `integration` (all tests carry
it). Every test in this folder is a **real integration test, not a unit test** —
`conftest.py`'s `client` fixture wraps `fastapi.testclient.TestClient(app)` against a real local
PostgreSQL database (nothing mocked), so a bootstrapped database and `api/.env` are prerequisites
for running any of them (see repo-root `README.md` → Getting Started).

## Files

| File | Tests | Covers |
|------|-------|--------|
| `conftest.py` | — | Module-scoped `client` fixture (`TestClient(app)` from `api.main`) shared by every test module |
| `test_bootstrap.py` | 21 | Tier 0 — `/api/v1/bootstrap/{health,roles,permissions,roles/{pk}/permissions}` (`TestHealth`, `TestRoles`, `TestPermissions`, `TestRolePermissions`), plus `TestBootstrapUI` (12 page-structure checks for `/`) |
| `test_foundation.py` | 59 | Tier 1 — all 17 `/api/v1/foundation/*` endpoints across 13 classes, including 2 contract-guard regression tests (`sequences.current_value` never exposed; `/change-log` 404s/405s, not real data) and `TestFoundationUI` (13 page-structure checks for `/foundation`) |
| `test_organization.py` | 51 | Tier 2 — all 6 `/api/v1/organization/*` endpoints across 7 classes: `TestOrganizationTypes` (4), `TestOrganizationStatuses` (4), `TestOrganizations` (17, incl. contact/online-presence field assertions), `TestOrganizationChildren` (4), `TestHierarchy` (4), `TestOrganizationUI` (13 page-structure checks for `/organization`), `TestOrganizationSecurity` (3) |
| `test_security.py` | 8 | Cross-tier security middleware — 5 header/`Cache-Control` assertions (`TestSecurityHeaders`), 1 rate-limit 429 test (`TestRateLimiting`, resets `api.main.limiter` via an autouse fixture between tests), 2 CORS tests under the default unconfigured `CORS_ORIGINS` (`TestCORS`) |

**139 tests total.**

## Running

```bash
pytest                    # all tests
pytest -m integration     # integration-marked tests (currently all of them)
pytest tests/test_bootstrap.py    # Tier 0 only
pytest tests/test_foundation.py   # Tier 1 only
pytest tests/test_organization.py # Tier 2 only
pytest tests/test_security.py     # security middleware only
```

`pytest` and `httpx` (required by `TestClient` at import time) are pinned in
`requirements.txt`.

## Related docs

- `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` — Tier 1 API contract
- `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md` — Tier 2 API contract
- `docs/03_Solution/code_explanations/` — line-by-line implementation walkthroughs
  and security audit reports for everything these tests cover
