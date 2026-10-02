# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Terse operating reference. The deep doc is `docs/PROJECT_DOCUMENTATION.md` (architecture, tier plan,
> directory detail, gotchas) — read it before proposing schema/module-layout changes. Per-area detail:
> `api/README.md`, `database/README.md`, `frontend/README.md`, `tests/README.md`. Don't append
> session-by-session narrative here; permanent decisions belong in `docs/00_Project_Governance/GDR/`
> (once ratified) or the relevant module's SOLUTION doc. For what is uncommitted, run `git status` —
> Tier 5 (Authentication + Administration) lives on `feature/tier5-authentication-administration`,
> not yet merged to `develop`/`main`, no release tag.

## Commands

Run everything from the **repository root**.

```bash
python3 -m pip install -r requirements.txt            # Windows: py -m pip ...
python3 -m uvicorn api.main:app --reload --port 8001  # run API + frontend (Swagger at /docs)

pytest                                   # all tests (api + db + security + ui)
pytest -m integration                    # tests/api + tests/db + tests/security
pytest -m ui                             # tests/ui (Playwright; needs browsers + running app)
pytest tests/api/test_organization.py    # one file
pytest tests/api/test_bootstrap.py::TestHealth::test_health_returns_ok   # one test

npm install && npm run css:build         # only after editing Tailwind/DaisyUI classes (css:watch for dev)
```

No lint/format tooling is configured — don't add one unilaterally. Every `tests/api|db|security`
test is a real integration test (nothing mocked): it needs a bootstrapped local DB and `api/.env`.

## Setup

`api/.env` needs `DB_NAME`/`DB_USER`/`DB_PASSWORD` (no defaults), `DB_HOST`, `DB_PORT`; for Tier 5
also `DB_WRITE_USER`/`DB_WRITE_PASSWORD` and `JWT_SECRET_KEY` (`Settings.validate_auth()` raises
otherwise; Tier 0-4 reads start without them). `database/scripts/06_setup_env.sh` (superuser)
sets all three role passwords and generates a working `api/.env`. All optional variables
(CORS, rate limit, pool sizes, `DEBUG_MODE`, CSP): `docs/PROJECT_DOCUMENTATION.md` → Configuration.
CSP `script-src` has no `'unsafe-inline'`, so the frontend must not use inline event handlers.

## Database

Hand-written PostgreSQL DDL in `database/ddl/` (numeric folder order), run with `psql`; no
migration tool, no ORM. All tables live in schema `nss` (`search_path` = `nss, public`). Bootstrap:

1. `database/scripts/00_create_database.sql` (superuser) — DB + roles `nss_db_owner`,
   `nss_db_backend`, `nss_db_writer`; set passwords with `ALTER ROLE`.
2. `01_extensions.sql` (superuser) — pgcrypto/pg_trgm/btree_gin/postgis, `nss` schema.
3. `02_build.sh`/`.ps1` (as `nss_db_owner`) — all DDL + seed in phase order (phase/table
   inventory: `database/README.md`), grants `nss_db_backend` read-only and
   `nss_db_writer` SELECT/INSERT/UPDATE on all `nss` tables (incl. future ones; no DELETE, no
   DDL), and seeds the admin superuser via `scripts/bootstrap_admin.py` (needs a runtime Argon2
   hash; default login `SS1`/`P1`, password `Admin@123`; INSERT-only with `WHERE NOT EXISTS`,
   never resets an existing password).
4. `03_validate.sh`/`.ps1` — row-count/FK checks. Minimums are stale (only WARN, never fail)
   and Family/Membership/`system_event_log`/`credential_sequence_counter` are unchecked.

A fresh build seeds **no demo Person/Family/Membership data** — only reference data, 175 real
Sakha branches and the one admin. Real data arrives via `POST /api/v1/register` → admin
`POST /api/v1/admin/claims/{pk}/approve`.

- `.sh`/`.ps1` script pairs must stay operationally identical (shell wrappers only).
- **`render_build.sh` (repo root) duplicates the build sequence for Render/Neon** — keep it in
  sync with `02_build.sh`. Known drift: header says v2.1 vs v2.4, no `postgis`, a Phase 13 failure
  only warns, `render.yaml` still says "Tier 0" and declares an unused `DATABASE_URL`, and
  `npm install` in a `runtime: python` service is untested.
- `nss_db_*` = PostgreSQL roles (lowercase); `NSS_ERP_*` = application RBAC roles in
  `role_master` (uppercase) — separate security boundaries.
- Naming: tables `snake_case`; internal PK `_pk`; FKs reference PKs, never business IDs; business
  IDs `_id` (`person_id`, `sangha_sevi_id`), codes `_code`. Business IDs are unpadded (`P1`,
  `SS1`, `SKH1`, `F1`). Audit columns `created_/updated_/deleted_at` + `*_by_sangha_sevi_pk` +
  `is_active` (soft delete; history is never hard-deleted).

## Architecture

FastAPI + raw psycopg2 (`api/`), static Tailwind/DaisyUI/Alpine frontend served by the same app
(`frontend/`). Routers → `api/schemas/` (Pydantic) with shared logic in `api/helpers.py` and
`api/services/` (`family_graph.py` BFS, `auth_service.py` Argon2/JWT, `rbac_service.py`
permission + admin-scope loading). 11 routers; endpoint inventory: `docs/03_Solution/api/API_CONTRACT.md`.

**Two DB pools** (`api/database.py`): `get_connection` = `nss_db_backend` (SELECT-only) for reads;
`get_write_connection` = `nss_db_writer` for every write endpoint. `tests/conftest.py` overrides
both to yield one session-scoped writer connection, wrapping each test module in a `SAVEPOINT`
rolled back at teardown — that is what lets the suite pass on a seed-less DB.

**Auth model is per-router, not uniform** — check before adding an endpoint:
- `bootstrap.py` — the only unauthenticated router (plus the public `registration.py` endpoints).
- `foundation`/`organization`/`person`/`membership` list endpoints — `require_permission("<MODULE>_VIEW")`
  (`api/dependencies/rbac.py`); Foundation writes need `FOUNDATION_MANAGE`.
- Person/Membership detail + sub-resources — `get_current_user` + `require_self_or_permission()`
  (a person may view their own record).
- `family.py` — all 16 endpoints use an ownership model (`_require_family_view/manage/head`,
  reached via `family_relationship`/`family_admin`), with `FAMILY_VIEW`/`FAMILY_MANAGE` as admin
  override. Deliberate; not a missing gate.
- `admin.py`/`claim_approval.py` — permission gates plus **admin scope** (`admin_scope` subtree,
  ADMIN-BR-076/077): scoped admins only touch organizations/persons/accounts inside their own
  subtree; `NSS_ERP_ADMIN`/NSS-WIDE is global. Permission alone never confers global reach.
- `audit.py` — `AUDIT_VIEW`, read pool only. `field_change_log` is deliberately **not** under
  `/foundation` (enforced by a test).

**Shared code — no duplicates (standing rule).** SQL/Python/UI logic needed twice goes into one
helper — check `api/helpers.py` (catalogued in `api/README.md`) before writing new SQL/
helpers. Non-obvious ones: `FAMILY_MAJORITY_CTE_SQL` (FAM-036 "effective Sakha" majority rule,
shared by organization stats and all family reads), `next_id()` (atomic `id_sequence_master`
counter; ignores `padding_length`), `next_credential_document_number()` (Kendra/Anumati numbers
via `credential_sequence_counter`), and the `fetch_*()` reference-data functions that the public
`registration.py` endpoints reuse.

**Audit has two write paths:** the DB trigger `fn_audit_trigger()` (attached to `nss.*` tables
except `system_event_log`/`field_change_log`, runs after Phase 13 so admin-bootstrap rows are
unaudited) reads session variables set by `api/helpers.py::log_audit()`, which also writes
`system_event_log` explicitly — duplicate rows of different shape exist, and the actor session
variables are set on the read-pool connection in `api/dependencies/auth.py`, so the write pool may
not carry the actor. Both unresolved.

**Middleware** (`api/middleware.py`): security headers, `no-store` on `/api/*`, 86400s cache on
`/assets/*`, CORS (GET/POST/PATCH/DELETE), SlowAPI rate limiting, CSP.

**Frontend:** pages `login`/`register`/`dashboard`/`admin` (the six Tier 0-4 verification pages are
deleted; their features live in `admin.html`/`dashboard.html`). Shared: `nss-config.js` (display
names e.g. `PROBATIONARY` → "Darshaka", badge maps), `badges.css` (never redefine badge classes
inline), `auth.js` (JWT + authed fetch), `nss-layout.js`, `org-dashboard.js` (one Alpine component
for six org-type layouts). `api/main.py::_serve_page()` rewrites `/assets/*.js|css` references to
`?v=<content hash>` per request — never hand-maintain `?v=`. `tailwind.min.css` is a **committed,
generated** file: rebuild it after changing any Tailwind/DaisyUI class in HTML or JS.

**Governance is frozen** (`docs/00_Project_Governance/{AUTH,GOV,GDR,STD}/`) — don't redesign without
an explicit decision. `docs/01_Authoritative_References/` holds source-faithful Bye-Law
transcripts — never paraphrase or "correct". Frozen principles: Person ≠ Member · Family First ·
History Never Deleted · Master Data Driven · By-Law Supremacy · Documentation First ·
Configuration Over Hardcoding · Permanent Business Identifiers · Soft Delete + Audit Trail ·
Unified Body Governance · One Person = One Membership = One Sangha Sevi ID.

**Domain decisions to remember:** three-tier member identity — Sangha Sevi ID (`sangha_sevi`,
NSS-wide), Local Sakha Number (`membership_sakha_affiliation.local_sakha_erp_id`, per Sakha,
archived on transfer never reassigned), Kendra Number (`parichaya_patra.document_number`, annual,
e.g. `345/2024/2025`). Associate members get a Parichaya Patra but no Anumati Patra. Self-
registration creates `person` + `user_account(PENDING_APPROVAL)` only; `sangha_sevi` is created on
admin approval. ORG-BR-099: Anchalika/Zilla/Patha Chakra may carry country/state/district but never
a premises address (DB-trigger enforced). Member search is 7-field, person search 4-field, trigram
threshold 0.45 with `re.split(r'[.@]', q)[0]` for email-shaped input.

## Git

`feature/<work>` → verify → commit → merge into `develop` → only then branch again. `main` advances
only via a documented release (tag + `docs/05_Releases/vX.Y.Z.md` + GitHub Release). Verify the
branch with `git status` before changes. Remotes: `personal` (daily dev) → PR → `org` (deploy
source); pushes are often blocked in-sandbox, so push from a terminal. Never add a `Co-Authored-By`
trailer to commits.

## Open items

- `frontend/forgot-password.html` doesn't exist, so the guarded `/forgot-password` route in
  `api/main.py` is never registered; forgot-password OTPs are never delivered
  (`api/routers/auth.py` TODO) — only visible via `otp_debug`.
- `/children-stats` and `/stats` recursive CTEs have no depth cap (`/hierarchy` caps at 10).
- `/person/{pk}/membership-summary` has no test coverage.
- `claim_approval.py::approve_claim()` and `admin.py::update_status()` each independently
  auto-provision a `sangha_sevi` — no shared helper.
- Pass 2 audit-actor FKs (`*_by_sangha_sevi_pk`) are still unconstrained on all tables.
- Deferred to later tiers: mobile/email verification, Organization contact-format CHECKs,
  inactive-person search, i18n, Governance (Tier 6), Kumari (Tier 8), Sevak/Mahila (Tier 9).
- `PERSON_VIEW_SENSITIVE` is seeded but unwired; Aadhaar masking is unconditional.
