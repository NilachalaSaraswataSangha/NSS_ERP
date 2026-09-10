# docs/03_Solution/architecture/code_explanations/

Line-by-line "how this vertical slice actually works" walkthroughs, one per completed tier —
distinct from `FOUNDATION_API_CONTRACT.md` and the other `architecture/` docs one level up,
which specify the *contract/design*, not the implementation narrative.

## Files

- **`TIER0_VERTICAL_SLICE.md`** (v2.0, release v0.6.0, **FROZEN**) — Full walkthrough of the
  Tier 0 Bootstrap RBAC vertical slice: 3 DB tables, 8 seeded roles, 4 read-only API endpoints
  (`api/routers/bootstrap.py`), 1 verification UI (`frontend/index.html`), 9 pytest integration
  tests (`tests/test_bootstrap.py`). Moved here from this folder's parent directory — same
  content, new location.
- **`TIER1_FOUNDATION.md`** (v2.0, release v0.7.0, **FROZEN**) — Same style walkthrough for Tier
  1 Foundation: 11 Pydantic schemas (`api/schemas/foundation.py`), 17 read-only endpoints
  (`api/routers/foundation.py`), a 4-tab verification UI (`frontend/foundation.html` +
  `assets/js/foundation.js`), and 47 pytest integration tests across 13 classes
  (`tests/test_foundation.py`), including 2 contract-enforcement/security-regression tests. Only
  covers the API/UI/test layers — Foundation's DDL/seed (12 tables) was done in an earlier
  phase, see `database/README.md`.
- **`TIER1_SECURITY_AUDIT.md`** (v1.0, **Complete**) — Security audit scoped to all Tier 1 code
  (`api/schemas/foundation.py`, `api/routers/foundation.py`, the `api/main.py` router
  registration, `frontend/foundation.html`, `frontend/assets/js/foundation.js`,
  `tests/test_foundation.py`). 9 checks passed (SQL injection, credential/`.env` leakage,
  error/stack-trace leakage, XSS, audit-data exposure, infrastructure-state leak,
  `nss_db_backend` privilege scope, connection-leak safety); 6 advisory, non-blocking
  deployment-hardening notes (no CORS middleware, no rate limiting, no pagination,
  `psycopg2-binary` vs. source `psycopg2` for prod, no security headers, no CDN Subresource
  Integrity hashes). No blocking vulnerabilities found.

See `docs/PROJECT_DOCUMENTATION.md` for the code-verified current state and
`docs/03_Solution/architecture/FOUNDATION_API_CONTRACT.md` for the Tier 1 API's formal contract.
