# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

> This is a terse operating reference, not the deep doc — that's `docs/PROJECT_DOCUMENTATION.md`
> (code-verified architecture, tier-by-tier plan, directory detail, gotchas). Read that before
> proposing schema/module-layout changes. Don't append session-by-session narrative to this file;
> permanent decisions belong in `docs/00_Project_Governance/GDR/` (once ratified) or the relevant
> module's own SOLUTION doc.

## Setup

```bash
# macOS / Linux
python3 -m pip install -r requirements.txt

# Windows
py -m pip install -r requirements.txt
```

Create `api/.env` with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — the FastAPI
app requires all three DB credentials (no defaults for name/user/password). Optional:
`CORS_ORIGINS` (comma-separated allowed origins), `RATE_LIMIT` (default `60/minute`),
`DISABLE_DOCS` (disable Swagger/ReDoc).

## Database

Hand-written PostgreSQL DDL under `database/ddl/`, numeric folder order, executed via `psql` (no
migration tool for this track). Bootstrap sequence (full commands and rationale in
`database/scripts/README.md` and `docs/PROJECT_DOCUMENTATION.md` → Setup & running):

1. `00_create_database.sql` (superuser) — creates `nss_erp` DB + `nss_db_owner`/`nss_db_backend`
   roles, then set their passwords via `ALTER ROLE ... PASSWORD`.
2. `01_extensions.sql` (superuser) — installs pgcrypto/pg_trgm/btree_gin/postgis, creates the
   `nss` schema (all tables live under `nss.*`, not `public`; `search_path` is `nss, public`).
3. `database/scripts/02_build.sh`/`.ps1` (as `nss_db_owner`) — runs all implemented DDL+seed in
   phase order: `00_bootstrap` (RBAC, 3 tables, seeded 8 roles) → `01_foundation` (12 tables,
   seeded) → `02_organization` (3 tables, seeded). `03_person` is a superseded prototype — not
   run, don't build on it.
4. `database/scripts/03_validate.sh`/`.ps1` — row-count/FK integrity checks.
5. `database/scripts/04_grant_backend.sql` (as `nss_db_owner`) — grants `nss_db_backend`
   read-only `SELECT`, needed before the API can connect.

`.sh`/`.ps1` script pairs must stay operationally identical — shell-mechanics wrappers only,
never a place for platform-specific logic.

**Role naming convention:** `nss_db_*` = PostgreSQL infrastructure roles (lowercase);
`NSS_ERP_*` = application RBAC roles in `role_master` (uppercase) — separate security
boundaries.

**Deployment (Render.com):** `render.yaml` + `render_build.sh` (repo root) duplicate the same
DDL/seed sequence directly via `psql` as an idempotent Render build step — keep in sync with
`02_build.sh` if phase order changes. Points at an external Neon.dev Postgres instance (no
managed DB declared in `render.yaml` itself). Not yet run in production.

## Running the FastAPI API

```
# macOS / Linux
python3 -m uvicorn api.main:app --reload --port 8001
# Windows
py -m uvicorn api.main:app --reload --port 8001
```
Run from the **repository root** (not from `api/`). Requires `api/.env` with DB credentials.

Tier 0 endpoints (read-only, no authentication):
- `GET /api/v1/bootstrap/health` — liveness probe
- `GET /api/v1/bootstrap/roles` — 8 frozen roles
- `GET /api/v1/bootstrap/permissions` — empty by design
- `GET /api/v1/bootstrap/roles/{role_pk}/permissions` — empty (no mappings)

Tier 1 endpoints (`api/routers/foundation.py`, read-only, no authentication) — 17 endpoints
across 11 tables under `/api/v1/foundation`: master data (`/categories`, `/master-data`),
system config (`/settings`, `/sequences` — excludes `current_value`), geography (`/countries`,
`/states`, `/districts`, `/cities`, `/postal-codes`, `/postal-code-mappings`), and runtime
(`/documents`). `field_change_log` is deliberately not exposed — deferred to Tier 5 (needs
auth). Full contract: `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`.

Tier 2 endpoints (`api/routers/organization.py`, read-only, no authentication) — 6 endpoints
under `/api/v1/organization`: reference data (`/types`, `/statuses`), organization records
(`/organizations` with optional `type_code`/`status_code` filters, `/organizations/{organization_pk}`,
`/organizations/{organization_pk}/children`), and the self-referencing tree
(`/hierarchy`, via a `WITH RECURSIVE` CTE). Full contract:
`docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`.

Swagger UI at `/docs` (disable via `DISABLE_DOCS=true` in `api/.env`); Bootstrap Verification UI
at `/`, Foundation Verification UI at `/foundation`, Organization Verification UI at
`/organization` (all served from `frontend/` by FastAPI). The API connects as `nss_db_backend`
(SELECT-only).

## Frontend

`frontend/` — a Tier 0 Bootstrap Verification UI (`index.html`, served at `/`) plus a Tier 1
Foundation Verification UI (`foundation.html`, served at `/foundation`) plus a Tier 2
Organization Verification UI (`organization.html`, served at `/organization`); none of these are
an admin dashboard. Served as static files by FastAPI: Tailwind CSS + DaisyUI (CDN), Alpine.js
(CDN), vanilla `fetch()`. No React/Vue/Angular, no Node.js build step, no Django templates. See
`frontend/README.md` for the full file/function reference.

## Tests & lint

pytest is configured (`pytest.ini` at repo root, `tests/` package). Run from the repository
root:

```
pytest                    # all tests
pytest -m integration     # integration-marked tests (currently all of them)
pytest tests/test_organization.py                        # one file
pytest tests/test_bootstrap.py::TestHealth::test_health_returns_ok  # one test
```

Every test is an integration test — `tests/conftest.py`'s `client` fixture wraps
`fastapi.testclient.TestClient` against a real local PostgreSQL DB, nothing is mocked — so a
bootstrapped local database and `api/.env` are required first. `tests/test_bootstrap.py` (21
tests), `tests/test_foundation.py` (59 tests), `tests/test_organization.py` (51 tests), and
`tests/test_security.py` (8 tests — security headers, Cache-Control scoping, rate limiting
429, CORS) cover the Tier 0, Tier 1, Tier 2, and cross-tier security middleware respectively.
**139 tests total.** No lint/format tooling is configured yet — don't add one unilaterally.

## Architecture

**Repository layout:**
```
NSS_ERP/
├── api/                    FastAPI Tier 0 + Tier 1 + Tier 2 API (raw psycopg2, no ORM)
│   ├── middleware.py       Security headers + Cache-Control scoping
│   ├── routers/            bootstrap.py (Tier 0), foundation.py (Tier 1), organization.py (Tier 2)
│   └── schemas/            bootstrap.py, foundation.py, organization.py — Pydantic response models
├── frontend/               Web UI (Tailwind/DaisyUI + Alpine.js, served by FastAPI)
├── database/               Hand-written PostgreSQL DDL + seed + scripts
│   ├── ddl/                Table definitions (00_bootstrap, 01_foundation, 02_organization)
│   ├── seed/               Seed data (mirrors ddl/ folder order)
│   └── scripts/            DB creation, build, validate, grant scripts
├── tests/                  pytest integration tests (test_bootstrap.py, test_foundation.py,
│                             test_organization.py, test_security.py)
├── docs/                   All project documentation
├── BY-LAW/                 Source reference material
└── NSS LOGO/               Branding assets
```

`backend/` (the earlier Django prototype) was fully removed once the FastAPI direction was
adopted — it no longer exists on disk, only in Git history. `api/` (FastAPI, raw
psycopg2, no ORM/SQLAlchemy/migration tool) is the only API layer; authentication is deferred to
Tier 5 — Tiers 0-2 have no auth, no fake auth, no API keys. Security middleware
(`api/middleware.py`) provides security headers (X-Content-Type-Options, X-Frame-Options,
Referrer-Policy, Permissions-Policy), Cache-Control scoping (no-store on `/api/*` only), CORS
(configurable via `CORS_ORIGINS`), and rate limiting (SlowAPIMiddleware, default 60/minute).

**DB naming (SQL DDL track):** tables `snake_case`; internal PK suffix `_pk`; FKs reference
internal PKs, never business IDs; business/external identifiers use `_code` — **never `_id`**
(some newer SOLUTION-layer docs under `docs/03_Solution/modules/` use `_id` in examples; that's
a known, tracked inconsistency — trust the DDL, not every doc example). Audit columns:
`created_at/created_by_sangha_sevi_pk`, `updated_at/updated_by_sangha_sevi_pk`,
`deleted_at/deleted_by_sangha_sevi_pk`, `is_active` (soft delete — history is never
hard-deleted).

**Governance Baseline is frozen** (`docs/00_Project_Governance/{AUTH,GOV,GDR,STD}/`) — not an
active design discussion; don't redesign without an explicit governance decision.
`docs/01_Authoritative_References/` holds source-faithful transcripts of the NSS and Mahila
Sangha Bye-Laws (`REF-*`/`REF-MS-*`) — never paraphrase or "correct" these.

**Frozen project-wide principles:** Person ≠ Member · Family First Model · History Never
Deleted · Master Data Driven · By-Law Supremacy · Documentation First · Configuration Over
Hardcoding · Permanent Business Identifiers · Soft Delete + Audit Trail · Unified Body
Governance Model · One Person = One Membership = One Sangha Sevi ID.

**Documentation layout:** see `docs/README.md` for the index;
`docs/PROJECT_DOCUMENTATION.md` is the deep reference (architecture, tier plan, gotchas).

**Git branch policy:** `feature/<work>` → complete & verify → commit → merge into `develop` →
only then create the next feature branch. `main` advances only via a documented release: git
tag + release notes doc (`docs/05_Releases/vX.Y.Z.md`) + GitHub Release, never an ad-hoc branch
sync. Confirm the current branch before making changes — don't assume a rename/move succeeded
without verifying via `git status`/`git ls-files`.

**Two git remotes:** `personal` (`github.com/sandeeppanda22/NSS_ERP`, daily dev) → PR →
`org` (`github.com/NilachalaSaraswataSangha/NSS_ERP`, deploy source). `git fetch`/`push` to
either is commonly blocked in-sandbox by a domain-allowlist restriction — push manually from a
terminal if a sandboxed session can't.

**Approved tech-stack direction:** FastAPI/Uvicorn (sole backend framework — Django was tried as
an early prototype and fully removed) + Tailwind/DaisyUI/Alpine (no HTMX in Tier 0) + Flutter
mobile (unbuilt). See `docs/03_Solution/architecture/TECH_STACK_DECISIONS.md` (v1.3) and
`docs/PROJECT_DOCUMENTATION.md` → Architecture for full detail.
