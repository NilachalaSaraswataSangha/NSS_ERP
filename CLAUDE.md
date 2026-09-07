# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this
repository.

> This file is a concise reference, not a running log — don't append session-by-session
> narrative to it. If a decision needs to be recorded permanently, it belongs in
> `docs/00_Project_Governance/GDR/` (once ratified) or in the relevant module's own SOLUTION
> doc.

## Setup

```
pip install -r requirements.txt
```

Create `api/.env` with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` — the FastAPI
app requires all three DB credentials (no defaults for name/user/password).

## Database

Hand-written PostgreSQL DDL under `database/ddl/`, numeric folder order, executed via `psql`
(no migration tool for this track — see `database/README.md` for the exact commands and full
phase-by-phase execution table):

1. `00_bootstrap/*` — 3 RBAC tables (`role_master`, `permission_master`, `role_permission`),
   created before Foundation since they have no FK dependencies — **DDL implemented and
   committed**; seed data partial (`role_master`: 8 roles seeded; `permission_master`/
   `role_permission`: empty, blocked on the permission catalogue being frozen)
2. Extensions (`pgcrypto`, `pg_trgm`, `btree_gin`, `postgis`) — in `database/scripts/01_extensions.sql`
3. `01_foundation/*` — 12 tables (master data, sequences, geography) — **implemented, seeded**
4. `02_organization/*` — 3 tables (`organization_type_master`, `organization_status_master`,
   `organization`) — **implemented, seeded**
5. `03_person/*` — superseded prototype, will be rewritten; don't build on it
6. `database/seed/` mirrors the same folder order

`database/scripts/02_build.sh [DB_NAME] [DB_USER] [DB_HOST] [DB_PORT]` (`.ps1` equivalent for
Windows) runs all implemented DDL+seed end-to-end against a running Postgres instance
(Bootstrap RBAC, Foundation, Organization — not Person, which is superseded);
`database/scripts/03_validate.sh`/`.ps1` (same args) then checks row counts and FK integrity
across those same modules. `database/scripts/00_create_database.sql` is a one-time superuser
script that creates the `nss_erp` database and the `nss_db_owner`/`nss_db_backend` roles (both
created with `LOGIN`, no password — set one via `ALTER ROLE ... PASSWORD` before first use);
`database/scripts/01_extensions.sql` installs pgcrypto/pg_trgm/btree_gin/postgis in nss_erp and
creates the `nss` schema (also superuser) — all tables live under `nss.*`, not `public`; the
database's default `search_path` is `nss, public`. The 5-step bootstrap sequence is:
`00_create_database.sql` → set passwords → `01_extensions.sql` → `02_build.sh` → `03_validate.sh`
(see `database/scripts/README.md` for the full phase-by-phase execution table).
The old repo-root `validate_foundation.sh` (Foundation-only) has been replaced by these.

**Role naming convention:** `nss_db_*` = PostgreSQL infrastructure roles (lowercase);
`NSS_ERP_*` = application RBAC roles in `role_master` (uppercase). PostgreSQL `nss_db_owner`
owns the database/schema; ERP `NSS_ERP_ADMIN` is an application permission role assigned to
real users. These are separate security boundaries.

## Running the FastAPI API

```
uvicorn api.main:app --reload --port 8001
```
Run from the **repository root** (not from `api/`). Requires `api/.env` with DB credentials.

Tier 0 endpoints (read-only, no authentication):
- `GET /api/v1/bootstrap/health` — liveness probe
- `GET /api/v1/bootstrap/roles` — 8 frozen roles
- `GET /api/v1/bootstrap/permissions` — empty by design
- `GET /api/v1/bootstrap/roles/{role_pk}/permissions` — empty (no mappings)

Interactive docs at `http://localhost:8001/docs` (Swagger UI).

The API connects as `nss_db_backend` (SELECT-only). Run
`database/scripts/04_grant_backend.sql` as `nss_db_owner` to grant privileges.

## Tests & lint

No test framework or lint/format tooling is configured yet. Don't add one
unilaterally — raise it as an open question if it's blocking.

## Architecture

**Repository layout:**
```
NSS_ERP/
├── api/                    FastAPI Tier 0 API (raw psycopg2, no ORM)
├── database/               Hand-written PostgreSQL DDL + seed + scripts
│   ├── ddl/                Table definitions (00_bootstrap, 01_foundation, 02_organization)
│   ├── seed/               Seed data (mirrors ddl/ folder order)
│   └── scripts/            DB creation, build, validate, grant scripts
├── docs/                   All project documentation
├── BY-LAW/                 Source reference material
└── NSS LOGO/               Branding assets
```

The **Django prototype** (`backend/`) was removed in the `feature/fastapi-tier0` branch.
It is preserved in Git history but is no longer part of the active codebase. Django
authentication is superseded by the NSS ERP authentication architecture (Tier 5).

**API layer:** `api/` uses FastAPI with raw psycopg2 queries against `nss.*` tables — no ORM,
no SQLAlchemy, no migration tool. The API connects as `nss_db_backend` (read-only in Tier 0).
Authentication is deferred to Tier 5; Tier 0 has no auth, no fake auth, no API keys.

**DB naming (SQL DDL track):** tables `snake_case`; internal PK suffix `_pk`; FKs reference
internal PKs, never business IDs; business/external identifiers use `_code` — **never `_id`**
(some newer SOLUTION-layer docs under `docs/03_Solution/modules/` use `_id` in examples; that
contradicts the implemented DDL and is a known, tracked inconsistency — trust the DDL, not every
doc example). Audit columns: `created_at/created_by_sangha_sevi_pk`,
`updated_at/updated_by_sangha_sevi_pk`, `deleted_at/deleted_by_sangha_sevi_pk`, `is_active`
(soft delete — history is never hard-deleted).

**Governance Baseline is frozen** (`docs/00_Project_Governance/{AUTH,GOV,GDR,STD}/`) — AUTH vs
GOV separation, REF architecture, governance lifecycle, stable identifier model, GDR model, NSS
apex authority, parent-child org model, REF source-preservation rule are settled and not an
active design discussion. `docs/01_Authoritative_References/` holds source-faithful transcripts
of the NSS Bye-Law and Mahila Sangha Bye-Law (`REF-*`/`REF-MS-*`) — never paraphrase or
"correct" these, editorial notes only if explicitly marked as such.

**Frozen project-wide principles** (don't redesign around these without an explicit governance
decision): Person ≠ Member · Family First Model · History Never Deleted · Master Data Driven ·
By-Law Supremacy · Documentation First · Configuration Over Hardcoding · Permanent Business
Identifiers · Soft Delete + Audit Trail · Unified Body Governance Model · One Person = One
Membership = One Sangha Sevi ID.

**Documentation layout:**
```
docs/
├── PROJECT_DOCUMENTATION.md        ← deep, code-verified reference; read before proposing
│                                      schema/module-layout changes
├── 00_Project_Governance/{AUTH, GOV, GDR, STD}/
├── 01_Authoritative_References/NSS/ , MAHILA_SANGHA/   (source-faithful REF corpus)
├── 02_Requirements/                 (scaffolded, empty)
├── 03_Solution/modules/<module>/     (per-module design docs — overview/ERD/business-rules/
│                                      table-design)
├── 04_Testing/                      (scaffolded, empty)
└── 05_Releases/
```

**Git branch policy:** `feature/<work>` → complete & verify → commit → merge into `develop` →
only then create the next feature branch. `main` advances only via a documented tag+release
process, never ad-hoc branch sync. Confirm the current branch before making changes — don't
assume a rename/move succeeded without verifying via `git status`/`git ls-files`.

**Two git remotes:** `personal` (`github.com/sandeeppanda22/NSS_ERP`, daily dev) → PR →
`org` (`github.com/NilachalaSaraswataSangha/NSS_ERP`, deploy source). `git fetch`/`push` to
either is commonly blocked in-sandbox by a domain-allowlist restriction — push manually from a
terminal if a sandboxed session can't.

**Approved tech-stack direction** (`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md`) —
FastAPI/Uvicorn API layer + Tailwind/DaisyUI/HTMX/Alpine UI + Flutter mobile. The API layer
(`api/`) is implemented starting from Tier 0. The UI layer (`frontend/`, not yet created) will
be implemented after the API proves out the DB→API vertical slice.
