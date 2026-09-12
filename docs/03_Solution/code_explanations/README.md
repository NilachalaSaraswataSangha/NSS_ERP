# docs/03_Solution/code_explanations/

Two kinds of documents live here:

1. **Per-layer code explanations** — a "requirement + line-by-line" catalogue of every source
   file in a given layer (API, Database, UI, Security, Testing). Each document exists to answer
   "why does this file exist, and what exactly does its code do?" for every file it covers.
2. **Security audit reports** (`TIER0_SECURITY_AUDIT.md`, `TIER1_SECURITY_AUDIT.md`,
   `TIER2_SECURITY_AUDIT.md`, `TIER3_SECURITY_AUDIT.md`) — a different concern: findings and
   remediation status from a security review, not code narration.

This structure replaces an earlier, now-retired set of per-*tier* walkthroughs
(`TIER0_VERTICAL_SLICE.md`, `TIER1_FOUNDATION.md`, `SECURITY_HARDENING.md`) that interleaved the
same files' narration across multiple documents because each was written when a new tier or
cross-cutting concern landed. Organizing by layer instead means every source file has exactly one
home, and the same pattern extends cleanly as new layers are added in the future (e.g. a
`MOBILE_CODE_EXPLANATIONS.md` once a Flutter client exists).

## Files

- **`API_CODE_EXPLANATIONS.md`** (v1.3, Complete — updated: Tier 3 Person) — every file
  under `api/` except `api/middleware.py` (which lives in the Security doc, since it's exclusively
  security code): `config.py`, `database.py`, `main.py`, `helpers.py`, `routers/bootstrap.py`,
  `routers/foundation.py`, `routers/organization.py`, `routers/person.py`, `schemas/bootstrap.py`,
  `schemas/foundation.py`, `schemas/organization.py`, `schemas/person.py`, and the three package
  `__init__.py` markers.
- **`DATABASE_CODE_EXPLANATIONS.md`** (v1.0, Complete) — every hand-written SQL DDL/seed file
  and build/validate/grant script under `database/` (Bootstrap/Foundation/Organization/Person —
  Person's `01_person_master_tables.sql` DDL/seed pair is the only remaining superseded file;
  `02_person.sql`/`03_person_address.sql` are real, implemented DDL), full
  column-by-column detail for DDL, representative sampling (not verbatim row transcription) for
  large seed files.
- **`UI_CODE_EXPLANATIONS.md`** (v1.3, Complete — updated: Tier 3 Person) — every file
  under `frontend/` except binary assets: `index.html`, `foundation.html`, `organization.html`,
  `person.html`, `assets/js/app.js`, `assets/js/foundation.js`, `assets/js/organization.js`,
  `assets/js/person.js`, `assets/css/style.css`.
- **`SECURITY_CODE_EXPLANATIONS.md`** (v1.1, Complete — updated: Tier 3 Person) —
  `api/middleware.py` in full, plus the security-relevant slices of `api/config.py`
  (`CORS_ORIGINS`/`RATE_LIMIT`/`DISABLE_DOCS`) and `api/main.py` (the middleware-registration
  block), plus the SRI-pinned CDN assets in `frontend/` (now covering all 4 HTML pages).
- **`TESTING_CODE_EXPLANATIONS.md`** (v1.2, Complete — updated: Tier 3 Person) — every
  file under `tests/`: `conftest.py`, `test_bootstrap.py`, `test_foundation.py`,
  `test_organization.py`, `test_person.py`, `test_security.py` (208 tests total).
- **`TIER0_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 0 code.
  10 checks passed; 1 fix applied (ConfigDict removal); 6 advisory items (4 resolved, 1 partial,
  1 N/A). No blocking vulnerabilities found.
- **`TIER1_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 1 code.
  9 checks passed; 6 advisory items (3 resolved, 1 partial, 1 advisory, 1 N/A).
  No blocking vulnerabilities found.
- **`TIER2_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 2 code.
  15 checks passed; 0 fixes required; 4 advisory items (pagination, CTE depth, filter logging,
  helper duplication). No blocking vulnerabilities found.
- **`TIER3_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 3 (Person)
  code. 18 checks passed; 0 fixes required; 3 of 5 advisory items resolved (pagination, search
  limit, helper deduplication), 2 awareness-only items retained (Aadhaar key management deferred
  to Tier 5+, filter value logging). No blocking vulnerabilities found — confirms defence-in-depth
  for Aadhaar (encrypted at rest, never selected by the API, never modelled in Pydantic, never
  rendered in the UI).

See `docs/PROJECT_DOCUMENTATION.md` for the code-verified current state and
`docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` for the Tier 1 API's formal contract. The same
`docs/03_Solution/api/` directory also holds `BOOTSTRAP_API_CONTRACT.md` (Tier 0),
`ORGANIZATION_API_CONTRACT.md` (Tier 2), and `PERSON_API_CONTRACT.md` (Tier 3) for the other
three API layers documented here.
