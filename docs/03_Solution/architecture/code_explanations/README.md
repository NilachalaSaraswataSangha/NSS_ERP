# docs/03_Solution/architecture/code_explanations/

Two kinds of documents live here:

1. **Per-layer code explanations** — a "requirement + line-by-line" catalogue of every source
   file in a given layer (API, Database, UI, Security, Testing). Each document exists to answer
   "why does this file exist, and what exactly does its code do?" for every file it covers.
2. **Security audit reports** (`TIER0_SECURITY_AUDIT.md`, `TIER1_SECURITY_AUDIT.md`) — a
   different concern: findings and remediation status from a security review, not code
   narration.

This structure replaces an earlier, now-retired set of per-*tier* walkthroughs
(`TIER0_VERTICAL_SLICE.md`, `TIER1_FOUNDATION.md`, `SECURITY_HARDENING.md`) that interleaved the
same files' narration across multiple documents because each was written when a new tier or
cross-cutting concern landed. Organizing by layer instead means every source file has exactly one
home, and the same pattern extends cleanly as new layers are added in the future (e.g. a
`MOBILE_CODE_EXPLANATIONS.md` once a Flutter client exists).

## Files

- **`API_CODE_EXPLANATIONS.md`** (v1.0, Complete) — every file under `api/` except
  `api/middleware.py` (which lives in the Security doc, since it's exclusively security code):
  `config.py`, `database.py`, `main.py`, `routers/bootstrap.py`, `routers/foundation.py`,
  `schemas/bootstrap.py`, `schemas/foundation.py`, and the three package `__init__.py` markers.
- **`DATABASE_CODE_EXPLANATIONS.md`** (v1.0, Complete) — every hand-written SQL DDL/seed file
  and build/validate/grant script under `database/` (41 files: 5 scripts, 21 DDL files across
  Bootstrap/Foundation/Organization/the superseded Person prototype, 15 seed files), full
  column-by-column detail for DDL, representative sampling (not verbatim row transcription) for
  large seed files.
- **`UI_CODE_EXPLANATIONS.md`** (v1.0, Complete) — every file under `frontend/` except binary
  assets: `index.html`, `foundation.html`, `assets/js/app.js`, `assets/js/foundation.js`,
  `assets/css/style.css`.
- **`SECURITY_CODE_EXPLANATIONS.md`** (v1.0, Complete) — `api/middleware.py` in full, plus the
  security-relevant slices of `api/config.py` (`CORS_ORIGINS`/`RATE_LIMIT`/`DISABLE_DOCS`) and
  `api/main.py` (the middleware-registration block), plus the SRI-pinned CDN assets in
  `frontend/`.
- **`TESTING_CODE_EXPLANATIONS.md`** (v1.0, Complete) — every file under `tests/`:
  `conftest.py`, `test_bootstrap.py`, `test_foundation.py`, `test_security.py` (64 tests total).
- **`TIER0_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 0 code.
  10 checks passed; 1 fix applied (ConfigDict removal); 6 advisory items (4 resolved, 1 partial,
  1 N/A). No blocking vulnerabilities found.
- **`TIER1_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 1 code.
  9 checks passed; 6 advisory items (3 resolved, 1 partial, 1 advisory, 1 N/A).
  No blocking vulnerabilities found.

See `docs/PROJECT_DOCUMENTATION.md` for the code-verified current state and
`docs/03_Solution/architecture/FOUNDATION_API_CONTRACT.md` for the Tier 1 API's formal contract.
