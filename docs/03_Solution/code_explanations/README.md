# docs/03_Solution/code_explanations/

This folder holds **per-layer code explanations** — a "requirement + line-by-line" catalogue of
every source file in a given layer (API, Database, UI, Security, Testing). Each document exists
to answer "why does this file exist, and what exactly does its code do?" for every file it
covers.

Security audit reports (`TIER0_SECURITY_AUDIT.md` through `TIER4_SECURITY_AUDIT.md`, plus the
aggregate `SECURITY_AUDIT_TIER0_4.md`) are a different concern — findings and remediation status
from a security review, not code narration — and now live at `docs/03_Solution/security/` (see
that folder's own README).

This structure replaces an earlier, now-retired set of per-*tier* walkthroughs
(`TIER0_VERTICAL_SLICE.md`, `TIER1_FOUNDATION.md`, `SECURITY_HARDENING.md`) that interleaved the
same files' narration across multiple documents because each was written when a new tier or
cross-cutting concern landed. Organizing by layer instead means every source file has exactly one
home, and the same pattern extends cleanly as new layers are added in the future (e.g. a
`MOBILE_CODE_EXPLANATIONS.md` once a Flutter client exists).

## Files

- **`API_CODE_EXPLANATIONS.md`** (v1.5, Complete — updated: Tier 4 Family + Membership) — every
  file under `api/` except `api/middleware.py` (which lives in the Security doc, since it's exclusively
  security code): `config.py`, `database.py`, `main.py`, `helpers.py`, `routers/bootstrap.py`,
  `routers/foundation.py`, `routers/organization.py`, `routers/person.py`, `routers/family.py`,
  `routers/membership.py`, `schemas/bootstrap.py`, `schemas/foundation.py`,
  `schemas/organization.py`, `schemas/person.py`, `schemas/family.py`, `schemas/membership.py`,
  and the three package `__init__.py` markers.
- **`DATABASE_CODE_EXPLANATIONS.md`** (v1.2, Complete — updated: Tier 4 Family + Membership) —
  every hand-written SQL DDL/seed file and build/validate/grant script under `database/`
  (Bootstrap/Foundation/Organization/Person/Family/Membership — Person's
  `01_person_master_tables.sql` DDL/seed pair is the only remaining superseded file;
  `02_person.sql`/`03_person_address.sql` and all of `04_family/` and `05_membership/` are real,
  implemented DDL), full column-by-column detail for DDL, representative sampling (not verbatim
  row transcription) for large seed files.
- **`UI_CODE_EXPLANATIONS.md`** (v1.4, Complete — updated: Tier 4 Family, Membership) — every
  file under `frontend/` except binary assets: `index.html`, `foundation.html`,
  `organization.html`, `person.html`, `family.html`, `membership.html`, `assets/js/app.js`,
  `assets/js/foundation.js`, `assets/js/organization.js`, `assets/js/person.js`,
  `assets/js/family.js`, `assets/js/membership.js`, `assets/css/style.css`.
- **`SECURITY_CODE_EXPLANATIONS.md`** (v1.1, Complete — updated: Tier 3 Person) —
  `api/middleware.py` in full, plus the security-relevant slices of `api/config.py`
  (`CORS_ORIGINS`/`RATE_LIMIT`/`DISABLE_DOCS`) and `api/main.py` (the middleware-registration
  block), plus the SRI-pinned CDN assets in `frontend/` (now covering all 4 HTML pages). Family's
  and Membership's router registration and their pages' CDN blocks follow the identical pattern
  already documented here — no Family/Membership-specific update needed in this file.
- **`TESTING_CODE_EXPLANATIONS.md`** (v1.4, Complete — updated: Tier 4 Family + Membership) —
  every file under `tests/`: `conftest.py`, `test_bootstrap.py`, `test_foundation.py`,
  `test_organization.py`, `test_person.py`, `test_security.py`, `test_family.py`,
  `test_membership.py` (363 tests total).

Security audit reports for Tiers 0–4 (`TIER0_SECURITY_AUDIT.md` … `TIER4_SECURITY_AUDIT.md`, plus
the cross-tier `SECURITY_AUDIT_TIER0_4.md`) live at `docs/03_Solution/security/`, not in this
folder — see that folder's own README for the current index.

See `docs/PROJECT_DOCUMENTATION.md` for the code-verified current state and
`docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` for the Tier 1 API's formal contract. The same
`docs/03_Solution/api/` directory also holds `BOOTSTRAP_API_CONTRACT.md` (Tier 0),
`ORGANIZATION_API_CONTRACT.md` (Tier 2), `PERSON_API_CONTRACT.md` (Tier 3), and the new
cross-tier `API_CONTRACT.md` quick reference (Tiers 0–4, see that folder's README for detail).
