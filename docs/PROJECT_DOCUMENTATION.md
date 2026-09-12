# NSS ERP — Project Documentation

> Comprehensive, code-verified documentation for the NSS ERP repository. This is the deep
> reference; `CLAUDE.md` is the terse AI-agent operating memory, and `README.md` is the
> public-facing project pitch. Where they disagree with what's actually in the code, this
> document (and the code itself) wins.

---

## Overview

NSS ERP is an in-development Enterprise Resource Planning system for **Nilachala Saraswata
Sangha (NSS)**, a religious/spiritual organization. It is not a generic corporate ERP — its
data model is built around NSS's own statutory structure (Kendra → Anchalika/Zilla →
Sakha), its membership system (Sangha Sevi ID), and organizational concepts like Family,
Governance, Attendance, Mahila Sangha, Kumari Sangha, Kishor Puja, Sevak Sangha, and Founder &
Heritage.

The project follows a **Constitution First → Governance → Requirements → Solution →
Implementation** philosophy, and for delivery, **Database First → API First → UI First**: raw
SQL schema is designed and frozen before API endpoints/schemas are written, and API endpoints
before UI. That philosophy is visible directly in the repo — the `person` and `organization`
modules both started as hand-written SQL DDL that predated any API-layer consumption; Tier 2 has
since caught Organization up with a read-only API (`api/routers/organization.py` — see
Architecture and Key Workflow #4 below), and Tier 3 has done the same for Person
(`api/routers/person.py` — see Key Workflow #5 below, though it is implemented on an unmerged
feature branch, not yet released), though several of both modules' own design decisions
remain open (see Gotchas).

The codebase today is an early-stage skeleton: a Tier 0 + Tier 1 + Tier 2 + Tier 3 FastAPI
application (`api/`) exposing 4 read-only bootstrap-RBAC endpoints plus 17 read-only Foundation
endpoints plus 6 read-only Organization endpoints plus 4 read-only Person endpoints (no ORM, no
auth, raw `psycopg2` against `nss.*`) behind
a cross-tier security middleware stack (security headers, opt-in CORS, rate limiting — see
Architecture below), a growing raw-SQL PostgreSQL schema (Bootstrap RBAC: 3
tables; Foundation: 12 tables; Organization: 1 table; Person: 2 tables — 18 tables implemented,
plus one superseded Person prototype file (`01_person_master_tables.sql`); see the `database/`
detail below), a `tests/` pytest
suite (208 integration tests against a real local Postgres), and an extensive, mature
governance/documentation corpus that is significantly ahead of the code. Solution-layer design
documentation (`docs/03_Solution/modules/`) is complete or near-complete across 22 module
folders — with zero corresponding API/SQL work beyond the Tier 0/1/2/3 endpoints
(Bootstrap/Foundation/Organization/Person) and the Foundation/Organization/Person DDL noted
above. A Django prototype (`backend/`) previously existed
covering `foundation`, `authentication`, `family`, `membership`, and `heritage`, but was fully
archived and removed (`chore: archive and remove Django prototype`) once the FastAPI direction
was adopted — `backend/` has been fully removed from the repository (the directory no longer exists on disk).
`docs/03_Solution/database/DATABASE_DESIGN_STANDARDS.md` states an `_id` business-identifier
convention that contradicts the project's actual frozen `_code`-only convention — see
Conventions & gotchas. `programmes_events` is the one module not tagged SOURCE ALIGNED (still
DRAFT, not frozen), though its cross-module reconciliation is complete.

## Architecture

```
Browser
   │
   ▼
Security middleware (api/middleware.py + api/main.py) — rate limiting → CORS (if configured) →
security headers
   │
   ├──→ GET /              FastAPI (api/main.py) → FileResponse(frontend/index.html)
   ├──→ GET /foundation     FastAPI (api/main.py) → FileResponse(frontend/foundation.html)
   ├──→ GET /organization   FastAPI (api/main.py) → FileResponse(frontend/organization.html)
   ├──→ GET /assets/*       FastAPI StaticFiles mount → frontend/assets/
   ├──→ GET /api/v1/bootstrap/...   FastAPI (api/routers/bootstrap.py)
   ├──→ GET /api/v1/foundation/...  FastAPI (api/routers/foundation.py)
   └──→ GET /api/v1/organization/... FastAPI (api/routers/organization.py)
                                │
                                ▼
                    psycopg2 connection pool (api/database.py) — raw SQL, no ORM
                                │
                                ▼
                    PostgreSQL (nss.* schema, hand-written DDL under database/ddl/)
```

- **Security middleware:** registered in `api/main.py`, in order (comments there call out that
  order matters — outermost registered last runs first): (1) `SlowAPIMiddleware` — global rate
  limiting via a module-level `Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])`
  (default `60/minute`, no per-route `@limiter.limit(...)` decorators, so every route shares one
  limit); (2) `CORSMiddleware` — only added `if settings.CORS_ORIGINS:` (comma-separated env var,
  default empty ⇒ middleware never registered at all, `allow_methods=["GET"]`,
  `allow_credentials=True`, never `allow_origins=["*"]`); (3) `api/middleware.py`'s
  `add_security_headers` — an `app.middleware("http")` function that sets
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: strict-origin-when-cross-origin`, and
  `Permissions-Policy: camera=(), microphone=(), geolocation=()` on every response, plus
  `Cache-Control: no-store` scoped to paths starting `/api/` only (not on `/`, `/foundation`, or
  `/assets/*`). Deliberately omits `X-XSS-Protection` (obsolete), CSP (deferred — Tailwind Play
  CDN's inline styles conflict with a strict policy), and HSTS (left to Render's edge TLS). Full
  line-by-line walkthrough: `docs/03_Solution/code_explanations/SECURITY_CODE_EXPLANATIONS.md`.
- **Web/API layer:** FastAPI (`api/`), the only web/API layer in the codebase — the earlier
  Django prototype (`backend/`) has been fully removed. `api/main.py` builds the `FastAPI` app,
  includes four routers (`api/routers/bootstrap.py`, prefix `/api/v1/bootstrap`;
  `api/routers/foundation.py`, prefix `/api/v1/foundation`; `api/routers/organization.py`,
  prefix `/api/v1/organization`; and `api/routers/person.py`, prefix `/api/v1/person`), and (if
  `frontend/` exists on disk)
  mounts `frontend/assets/` at `/assets` and serves `frontend/index.html` via an explicit
  `GET /` route, plus `frontend/foundation.html` via `GET /foundation`,
  `frontend/organization.html` via `GET /organization`, and `frontend/person.html` via
  `GET /person`, each only if that file exists —
  mounting at `/assets` rather than `/` avoids shadowing FastAPI's own `/docs` (Swagger UI) and
  `/openapi.json`. Swagger UI/ReDoc/OpenAPI schema can be disabled via `DISABLE_DOCS` in
  `api/.env`. The security middleware stack above is registered; there is still no auth
  middleware.
- **Frontend layer:** `frontend/` — four single-page views built with Tailwind CSS + DaisyUI
  (CDN, pinned to `4.12.14` with SRI `integrity`/`crossorigin`) and Alpine.js (CDN, pinned to
  `3.14.8` with SRI), no build step, no framework: a Tier 0 "Bootstrap Verification UI"
  (`index.html`), a Tier 1 "Foundation Verification UI" (`foundation.html`), a Tier 2
  "Organization Verification UI" (`organization.html`), and a Tier 3 "Person Verification UI"
  (`person.html`), none an admin dashboard.
  `frontend/assets/js/app.js` defines `bootstrapApp()`, fetching
  `/api/v1/bootstrap/{health,roles,permissions}` in parallel on load and driving 4 UI sections
  (system status, RBAC roles, permissions, an interactive role→permissions drill-down).
  `frontend/assets/js/foundation.js` defines `foundationApp()`, lazily fetching from
  `/api/v1/foundation/*` per tab across a 4-tab layout (Master Data, System Config, Geographic
  drill-down, Runtime Tables). `frontend/assets/js/organization.js` defines `organizationApp()`,
  lazily fetching from `/api/v1/organization/*` per tab across a 3-tab layout (Reference Data,
  Organizations with click-to-drill-down children, Hierarchy tree). `frontend/assets/js/person.js`
  defines `personApp()`, fetching from `/api/v1/person/*` across a 2-tab layout (Persons with
  filter/detail/addresses drill-down, debounced trigram Search). See `frontend/README.md` for
  the full file/function/state reference. Served entirely by FastAPI — same-origin, so the
  frontend itself needs no CORS;
  `CORSMiddleware` above exists for *other* (cross-origin) API consumers, and is a no-op locally
  since `CORS_ORIGINS` defaults to empty.
- **Data layer:** a single track — **hand-written PostgreSQL DDL** under `database/ddl/`,
  following the project's own UUID-`_pk` + business-`_code` convention (see Conventions &
  Gotchas). This is the "real" schema per the governance/standards docs, and it is now consumed
  — read-only — by the FastAPI Tier 0, Tier 1, Tier 2, and Tier 3 endpoints via raw parameterized
  SQL (no ORM). `organization` has a read-only API (`api/routers/organization.py`); `person` now
  does too (`api/routers/person.py`, unreleased — see "Current position" above).
- **Test layer:** `tests/` — pytest, configured via `pytest.ini` (repo root). `tests/conftest.py`
  wraps `fastapi.testclient.TestClient(app)` against a **real** local PostgreSQL DB (nothing
  mocked); all tests carry the custom `integration` marker. `test_bootstrap.py` (21 tests, 5
  classes) and `test_foundation.py` (59 tests, 13 classes) cover every implemented endpoint,
  plus two contract-guard regression tests (`sequences.current_value` never exposed;
  `/api/v1/foundation/change-log` returns 404/405, not real data); `test_organization.py` (64
  tests, 7 classes) covers every Organization endpoint (types, statuses, organizations
  list/detail/children, hierarchy) plus contact/online-presence fields, `limit`/`offset`
  pagination on both `/organizations` and `/hierarchy`, and a UI/security suite;
  `test_person.py` (56 tests, 6 classes: `TestPersonList`, `TestPersonDetail`,
  `TestPersonAddresses`, `TestPersonSearch`, `TestPersonSecurity`, `TestPersonUI`) covers every
  Person endpoint including the pg_trgm `/search` fuzzy match, guarantees `aadhaar_encrypted`/
  `aadhaar_hash` are never returned, and is skip-guarded wherever it needs an actual seeded row
  (Person has no seed data — see Key Workflow #3); `test_security.py` (8 tests,
  3 classes) covers the security middleware — 5 header/Cache-Control assertions, 1 rate-limit
  429 test (loops requests against `/api/v1/bootstrap/health` until the default `60/minute`
  limit trips, resetting `limiter.reset()` via an autouse fixture between tests), and 2 CORS
  tests (both asserting *absence* of `Access-Control-Allow-Origin` under the default empty
  `CORS_ORIGINS`). **208 tests total.**
- **Auth:** none. Tier 0 is explicitly read-only, unauthenticated, by design — RBAC/JWT/OTP
  enforcement is deferred to a later tier, even though
  `docs/00_Project_Governance/STD/05_security_standards.md` specifies a full RBAC +
  Row-Level-Security model as the eventual target.
- **Governance/documentation layer:** a large, independently-maintained set of governance
  standards (`docs/00_Project_Governance/`) and authoritative legal reference documents
  (`docs/01_Authoritative_References/`) that define the rules the eventual system must follow.
  This layer is far more mature than the code.

**Approved future direction (SOLUTION layer, partially implemented in code):**
`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md` (v1.3) is the authoritative technology
decision record — FastAPI/Uvicorn is now the sole backend framework (the earlier Django
prototype was implemented, then fully archived and removed as part of v1.3's
Django-to-FastAPI migration) + Tailwind/DaisyUI/Alpine.js UI + Flutter mobile. The FastAPI half is
now partially wired up (Tier 0 bootstrap endpoints), and the Tailwind/DaisyUI/Alpine.js web UI
direction now has a first real implementation (`frontend/`'s Tier 0 Bootstrap Verification UI,
not yet the full admin dashboard the mockups describe); the Flutter mobile client remains
unbuilt, and `render.yaml`/`render_build.sh` declare a Render.com + Neon.dev deployment that has
not yet run in production. **Mobile strategy:** the app's own
mobile client is Flutter, targeting Android + iOS from day one (Hive/Drift for offline local
storage, syncing via a Dart background isolate, FCM for push). The web app itself still uses
IndexedDB/Service-Worker offline support for on-site event registration in the browser — a
parallel, not exclusive, path to the Flutter app.
`docs/03_Solution/architecture/DEVELOPER_REFERENCE_GUIDE.md` is a companion per-module "which
doc to read before coding" matrix across the REF→AUTH→GOV→REQ→SOLUTION→CODE chain. Treat
everything in this "Architecture" section above as the current CODE-layer reality and the Tech
Stack Decisions doc as the approved target for what's not yet built — don't assume one from the
other.

**Pre-DDL architecture gates (all FROZEN):**
`docs/03_Solution/architecture/IMPLEMENTATION_DEPENDENCY_ORDER.md` (`IMPLEMENTATION-TIER-001`,
12-tier build order across 22 modules) → `FK_DEPENDENCY_GRAPH.md` ("Gate 8" — physical FK
dependency graph across 86 frozen tables, topologically sorted into 8 depths with zero cycles,
resolves the audit-actor circular-dependency problem via a two-pass DDL strategy) →
`DDL_CREATION_ORDER.md` ("Gate 9" — the exact numbered `CREATE TABLE` sequence for all 86
tables plus the Pass-2 deferred-constraint list). Tiers 1-2 (Foundation, Person + Organization)
of the 12-tier order are executed — 16 tables live under `database/ddl/01_foundation/`/
`database/ddl/02_organization/`/`database/ddl/03_person/` and their matching seed folders;
Tiers 3-12 remain unimplemented. Note: `IMPLEMENTATION_DEPENDENCY_ORDER.md`'s own closing
status section (§79) reflects Tier 1 completion but hasn't been updated for Tier 2. **Tier-
numbering divergence:** the frozen 12-tier plan's Tier 2 bundles Person + Organization together,
but the actual implementation sequence (and every other doc — `CLAUDE.md`, the code-explanation
docs, `docs/03_Solution/api/`) splits them into separate vertical slices numbered "Tier 2
(Organization)" and "Tier 3 (Person)" — see Gotchas for the full note; don't assume "Tier 3"
means the same thing in `IMPLEMENTATION_DEPENDENCY_ORDER.md` (where it means Heritage) as it
does everywhere else in this codebase's own vocabulary (where it means Person).

**`BOOTSTRAP_ARCHITECTURE.md`** (`SOL-ARCH-011`, FROZEN) defines a "Phase 0" that sits *before*
Tier 1: `role_master`/`permission_master`/`role_permission` have zero FK dependencies, so they
are created and seeded before Foundation — resolving the same audit-actor circular dependency
via the same two-pass strategy. It establishes `nss_db_owner` (PostgreSQL DDL owner) as
distinct from `NSS_ERP_ADMIN` (an ERP RBAC role, a `role_master` row) — the two are explicitly not
equivalent, and `NSS_ERP_ADMIN` never bypasses RBAC checks. DDL for all 3 tables exists under
`database/ddl/00_bootstrap/` and is **implemented and committed** (`feat(bootstrap): Phase 0
Bootstrap RBAC DDL and seed data`); seed data is partial (`role_master`: 8 roles;
`permission_master`/`role_permission`: empty, pending the permission catalogue). Ownership of
the 3 tables remains with Administration — "Bootstrap" is a DDL-sequencing label, not a new
module (see Gotchas).

## Tier-wise Implementation Plan

The system is built **vertically by tier**: each tier completes DB → API → UI before the
next tier begins. This is distinct from the DDL depth order (which is an internal database
concern within each tier's DB phase).

**Authority:** `docs/03_Solution/architecture/IMPLEMENTATION_DEPENDENCY_ORDER.md`
(`SOL-ARCH-008`, `IMPLEMENTATION-TIER-001`)

### Tier sequence

| Tier | Modules | Focus |
|-----:|---------|-------|
| 0 | Bootstrap | PostgreSQL bootstrap (database, roles, extensions, `nss` schema) + initial RBAC tables |
| 1 | Foundation | Common master/reference infrastructure (master_data, geography, sequences, settings) |
| 2 | Person + Organization | People identity (Sangha Sevi ID) and organizational hierarchy (Kendra → Anchalika/Zilla → Sakha) |
| 3 | Heritage | Founder biography, teachings, objectives, historical milestones, office bearers |
| 4 | Family + Membership | Family groups, membership types (Probationary/Regular/Associate), Sakha affiliation, local IDs, transfer |
| 5 | Authentication + Administration + Audit | User accounts, RBAC enforcement, organizational scopes, audit trail |
| 6 | Attendance + Governance + Assets & Property | Sangha Puja attendance, governance positions, immovable/movable property |
| 7 | Programme & Events | Event types, instances, sessions, registration (Janmotsaba, Rasoutsaba, etc.) |
| 8 | Kumari + Kishor + Sevak | Youth participation domains (Kumari/Kishor IDs, Seva architecture, Dina-Lipi, Niyam Panchak) |
| 9 | Mahila | Mahila-specific operations (not a separate membership category — Mahila Puja is Sangha Puja with majority women) |
| 10 | Publications + UPBS | Publication catalogue/operations, UPBS operational integration |
| 11 | Finance | Financial transactions (Pranami, event fees, publication sales, property income) — deliberately late, references upstream domains |
| 12 | Reports + Backup & Technical | Reporting, analytics, backup/restore, technical administration |

### Vertical slice per tier

Each tier follows the same internal sequence:

```
Database
  ├── Review frozen table design
  ├── DDL (CREATE TABLE in dependency-depth order)
  ├── Constraints + indexes
  ├── Seed data
  └── DB validation
       │
       ▼
API
  ├── Design + schemas
  ├── Endpoints
  └── Authorization
       │
       ▼
UI
  ├── Pages + forms
  ├── Tables + lists
  └── API integration
       │
       ▼
Integration test → freeze tier → next tier
```

### Key architectural facts per tier

**Tier 0 (Bootstrap):** PostgreSQL `nss_db_owner` role (database-level DDL owner) is distinct
from ERP `NSS_ERP_ADMIN` role (application RBAC row in `role_master`). Bootstrap RBAC tables
(`role_master`, `permission_master`, `role_permission`) are owned by the Administration
module — "Bootstrap" is a DDL-sequencing label, not a new module. Permission catalogue is
not yet frozen.

**Tier 0 — RBAC role model (frozen):** The 8 frozen ERP roles (3 SYSTEM + 5 ORGANIZATIONAL)
are **parallel entries in `role_master`** — there is no role hierarchy or inheritance. A user
may hold **multiple roles simultaneously** (`user_role` is a junction table, 1:N from
`user_account`, N:1 to `role_master`). Scope attaches to the **role assignment** (via
`admin_scope`), not to the person globally — the same person can therefore hold different
roles with different organizational scopes. Governance position (President, Secretary, etc.)
is never used as a permission mechanism; role assignment is explicit and independent.
`NSS_ERP_ADMIN` and the 5 organizational admin roles (`NSS_ERP_KENDRA_ADMIN`,
`NSS_ERP_ANCHALIKA_ADMIN`, `NSS_ERP_ZILLA_ADMIN`, `NSS_ERP_SAKHA_ADMIN`,
`NSS_ERP_PATHA_CHAKRA_ADMIN`) initially share the same permission set — the only distinction is
scope, not permissions; each organizational role is never a prerequisite for, and never
automatically grants, another. Eligibility differs per role: `NSS_ERP_ADMIN` may go to any NSS
member with a valid Parichay Patra when system-wide administration is authorized (Governing Body
membership is not required); each organizational role typically goes to that unit's Governing
Body members or another authorized individual (`05_administration_table_design.md` §8.11, v1.2.0).
The Administration UI may present
a **composite administrative view** joining member identity, governance, roles, scope, and
organization — this is a read-model / presentation concern, never a denormalized table
(SOL-ADMIN-001 §63).

**Implementation principle — cross-platform wrappers (frozen):** The SQL DDL, seed data,
FastAPI application, and UI are **identical across platforms**. `.sh` (macOS/Linux) and `.ps1`
(Windows) scripts are developer/operational wrappers only — they must not contain different
business logic, database statements, or schema definitions. Platform-specific behaviour is
limited to shell mechanics (variable substitution, exit codes, colour output).

**Tier 2 (Person + Organization):** Person is the central human identity. The global Sangha
Sevi ID (e.g. `SS000001`) is permanent, unique across NSS, never changes, never reused.
Organization hierarchy: Kendra → Anchalika/Zilla → Sakha → Sakha Asana → Patha Chakra.
Nilachala Kutira and Smruti Mandira are separate roots, not children of Kendra. Organization
stores location inline (country, city_village, postal_code FKs + lat/long), no separate
`organization_address` table.

**Tier 4 (Family + Membership):** Membership is not the same as Sakha affiliation.
`membership_sakha_affiliation` carries effective-dated Sakha assignment. Transfer: old local
ID archived, new local ID issued, global Sangha Sevi ID unchanged. Local ID format:
`<3-5 char org code><8 digit sequence>` (e.g. `ESS00000123`).

**Tier 5 (Auth + Admin + Audit):** Effective access = User + Role + Permission +
Organizational Scope. Audit is separate from change history — `field_change_log` (Foundation)
handles field-level change tracking; `audit_master`/`system_event_log` handle security and
system events.

**Tier 6 (Attendance):** Membership Sakha ≠ Attendance Sakha. A member affiliated with
Sakha A can attend Sangha at Sakha B — the attendance record identifies the actual Sakha
where attendance occurred. Weekly Sangha Puja is owned by Attendance, not Programme & Events.
Attendance types: REGULAR, DARSHAK, VISITOR.

**Tier 6 (Assets & Property):** Legal owner, registered holder, and custodian are distinct
concepts. Covers acquisition, disposal, custody, maintenance, valuation, depreciation,
insurance, statutory obligations, restricted property.

**Tier 7 (Programme & Events):** Common structure: Programme Type → Event → Event Instance
→ Event Day → Event Session, plus Registration. Finance owns actual event financial
transactions. Attendance remains Attendance-owned.

**Tier 8 (Kumari/Kishor/Sevak):** These are not adult Membership categories. Kumari and
Kishor have separate identity/participation domains. Sevak architecture: Seva → Seva Head →
Application → Recommendation → Approval. Guardian model for minors includes
`guardian_sangha_sevi_pk`.

**Tier 11 (Finance):** Financial year 1 April – 31 March. Finance owns all actual
transactions. Other modules reference Finance — they do not create competing transaction
ledgers.

### Current position

Tier 0 (Bootstrap), Tier 1 (Foundation), Tier 2 (Organization), and Tier 3 (Person) DB phases
are all **implemented**. `database/ddl/03_person/02_person.sql` (`person`, 28 columns) and
`03_person_address.sql` (`person_address`) are real, implemented DDL — following the same
Foundation `master_data` pattern as Organization (gender/marital_status/blood_group/
address_type resolve through `master_data`, not dedicated per-domain master tables). Only
`01_person_master_tables.sql` (the original per-domain gender/marital_status/address_type
master tables) remains superseded — its data now lives in Foundation's `master_data` seed.
Tier 0's API phase is **implemented** (4 read-only bootstrap-RBAC endpoints in
`api/routers/bootstrap.py`). Tier 1's API phase (Foundation) is **implemented** — 17 read-only
endpoints across 11 tables in `api/routers/foundation.py`, with a matching Foundation
Verification UI (`frontend/foundation.html`) and 59 pytest integration tests — merged to `main`
and tagged as v0.7.0. Tier 2's API phase (Organization) is **implemented** — 6 read-only
endpoints (reference data, organizations list/detail/children with `limit`/`offset` pagination,
a recursive-CTE `/hierarchy`, also paginated) in `api/routers/organization.py`, with a matching
Organization Verification UI (`frontend/organization.html`) — merged to `main` and tagged as
v0.8.0. Tier 3's API phase (Person) is **implemented but not yet released** — 4 read-only
endpoints (`/persons` list with gender/marital-status/blood-group filters + pagination,
`/persons/{person_pk}` detail, `/persons/{person_pk}/addresses`, `/search?q=` pg_trgm fuzzy
search) in `api/routers/person.py`, a matching Person Verification UI (`frontend/person.html`),
and a combined 208 pytest integration tests across all four tiers (21 bootstrap + 59 foundation +
64 organization + 56 person + 8 security) — `tests/test_organization.py` grew from 51 to 64 with
new pagination/security-header/contact-field tests and `tests/test_person.py` added 56 —
currently on `feature/tier3-person-module`, not yet merged to `develop`/`main` or tagged. All
other API phases and all other UI phases remain **unimplemented** across the remaining tiers.

### Database schema

All application tables live in the `nss` schema (`CREATE SCHEMA nss`). The `public` schema
is reserved for PostgreSQL extensions (pgcrypto, pg_trgm, btree_gin, postgis). The database
default `search_path` is set to `nss, public`. All DDL uses explicit `nss.` prefix on table
names, FK references, and index targets.

## Directory structure

```
NSS_ERP/
├── api/                          FastAPI application (Tier 0 Bootstrap + Tier 1 Foundation +
│                                   Tier 2 Organization + Tier 3 Person endpoints, see below)
├── frontend/                      Tier 0 Bootstrap + Tier 1 Foundation + Tier 2 Organization +
│                                   Tier 3 Person Verification UIs, served as static files by
│                                   FastAPI (see below)
├── backend/                      Empty — the earlier Django prototype was archived and removed
├── database/
│   ├── ddl/                     Hand-written PostgreSQL schema, numbered by module
│   ├── seed/                    Reference/lookup data matching the DDL
│   └── scripts/                 Executable bootstrap/build/validate/grant scripts (see below)
├── tests/                        pytest integration tests (test_bootstrap.py,
│                                   test_foundation.py, test_organization.py, test_person.py,
│                                   test_security.py, conftest.py) — see Setup & running
├── docs/
│   ├── PROJECT_DOCUMENTATION.md This file
│   ├── 00_Project_Governance/   AUTH/ GOV/ GDR/ STD/ — governance framework + engineering standards
│   ├── 01_Authoritative_References/
│   │   ├── NSS/            Source-faithful transcription of NSS's Constitution & Bye-Laws (see detail below)
│   │   └── MAHILA_SANGHA/  Source-faithful transcription of Mahila Sangha's own Bye-Law (see detail below)
│   ├── 02_Requirements/         Scaffolded only — business/functional/non_functional/traceability subfolders, no content yet
│   ├── 03_Solution/             Per-module design docs — 22 module folders (organization,
│   │                            person, membership, family, attendance, heritage, kumari,
│   │                            kishor, mahila, sevak, foundation, administration,
│   │                            authentication, governance, publications, reports, upbs,
│   │                            audit, backup_technical, finance, programmes_events,
│   │                            assets_property) + architecture/ui/infrastructure/standards/
│   │                            database/security/code_explanations content populated (see
│   │                            detail below); `docs/03_Solution/api/` now holds 4 read-only
│   │                            API contract docs (Bootstrap/Foundation/Organization/Person —
│   │                            consolidated here, moved out of `architecture/`; see detail
│   │                            below), distinct from the real, implemented root-level `api/`
│   │                            code folder
│   ├── 04_Testing/              Scaffolded only — unit/integration/api/ui/database/security/acceptance subfolders, no content yet
│   └── 05_Releases/             Release notes, v0.1.0 → v0.8.0
├── BY-LAW/                       Original source PDFs/docx of the NSS and Mahila Sangha Bye-Laws — the primary source both `docs/01_Authoritative_References/NSS/` and `.../MAHILA_SANGHA/` are transcribed from
├── render.yaml                    Render.com Infrastructure-as-Code — free-tier web service
│                                   (`uvicorn api.main:app`); does not provision a database — DB
│                                   env vars point to an externally-managed Neon.dev instance
├── render_build.sh                 Render build hook — installs deps, runs DB bootstrap
│                                   (idempotent — skips DDL/seed if already bootstrapped)
├── requirements.txt              Python dependencies (pip, not pinned to a venv tool)
├── pytest.ini                     pytest config — `testpaths = tests`, `integration` marker
├── CLAUDE.md                     AI-agent operating memory/context (terse, instruction-oriented)
└── README.md                     Project pitch / high-level status
```

`database/scripts/` holds the executable bootstrap/build/validate/grant scripts
(`00_create_database.sql`, `01_extensions.sql`, `02_build.sh`/`.ps1`, `03_validate.sh`/`.ps1`,
`04_grant_backend.sql`) that replaced the old repo-root `validate_foundation.sh` (deleted) — see
the `database/` detail below.

### `api/` — FastAPI application detail

```
api/
├── main.py             FastAPI app entry point — builds `app`, registers the security
│                       middleware stack (rate limiting, opt-in CORS, security headers — see
│                       Architecture above), includes all four routers, mounts
│                       `frontend/assets/` at `/assets` and serves `frontend/index.html` at `/`,
│                       `frontend/foundation.html` at `/foundation`,
│                       `frontend/organization.html` at `/organization`, and
│                       `frontend/person.html` at `/person` (all skipped if the
│                       respective file/dir doesn't exist — API-only mode still works), disables
│                       `/docs`/`/redoc`/`/openapi.json` if `DISABLE_DOCS` is set, closes the DB
│                       pool on shutdown. Run with:
│                       `python3 -m uvicorn api.main:app --reload --port 8001` (from repo root)
├── config.py           Settings: DB_NAME/DB_USER/DB_PASSWORD (required), DB_HOST (default
│                       localhost), DB_PORT (default 5432), API_PORT (default 8001),
│                       DISABLE_DOCS (default false), CORS_ORIGINS (comma-separated, default
│                       empty ⇒ CORS middleware not registered), RATE_LIMIT (default
│                       `60/minute`) — read from `api/.env` via python-dotenv;
│                       `Settings.validate()` raises if any required var is missing
├── database.py         psycopg2 `SimpleConnectionPool` (1-5 conns), connects as `nss_db_backend`
│                       (read-only); `get_connection()` is a FastAPI generator dependency;
│                       `check_connection()` backs the /health endpoint
├── middleware.py       `add_security_headers(request, call_next)` — sets
│                       `X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy`/
│                       `Permissions-Policy` on every response, plus `Cache-Control: no-store`
│                       scoped to `/api/*` only; registered in `main.py` via
│                       `app.middleware("http")`
├── helpers.py          Shared cursor→Pydantic conversion (`rows_to_models`, `row_to_model`) and
│                       pagination constants (`DEFAULT_LIMIT = 100`, `MAX_LIMIT = 500`) used by
│                       every router — extracted from per-router duplicates when Tier 3 (Person)
│                       landed so limit/offset validation stays consistent everywhere
├── routers/
│   ├── bootstrap.py    4 endpoints under `/api/v1/bootstrap` — no auth, no ORM, raw
│   │                   parameterized SQL against `nss.role_master`/`permission_master`/
│   │                   `role_permission` (see Key workflows below)
│   ├── foundation.py   17 endpoints under `/api/v1/foundation` across 11 tables — master data
│   │                   (`/categories`, `/master-data`), system config (`/settings`,
│   │                   `/sequences`), geography (`/countries`→`/states`→`/districts`→`/cities`,
│   │                   `/postal-codes`, `/postal-code-mappings`), runtime (`/documents`);
│   │                   `field_change_log` deliberately not exposed (deferred to Tier 5 — needs
│   │                   auth); see Key workflows below and
│   │                   `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`
│   ├── organization.py 6 endpoints under `/api/v1/organization` across `nss.organization` plus
│   │                   Foundation's `master_data` — reference (`/types`, `/statuses`, both
│   │                   querying `master_data` filtered by `master_category.category_code`
│   │                   `ORGANIZATION_TYPE`/`STATUS` — 10 types, 13 statuses), core
│   │                   (`/organizations` with optional `type_code`/`status_code` filters plus
│   │                   `limit`/`offset` pagination, `/organizations/{organization_pk}`,
│   │                   `/organizations/{organization_pk}/children`), navigation (`/hierarchy`,
│   │                   a `WITH RECURSIVE org_tree` CTE returning a flat depth-annotated list,
│   │                   also paginated); all four organization-shaped endpoints share one SQL
│   │                   fragment (`_ORG_SELECT`) that LEFT JOINs the self-referencing parent plus
│   │                   Foundation's district/state/country/city_village/postal_code tables; see
│   │                   Key workflows below and
│   │                   `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`
│   └── person.py       4 endpoints under `/api/v1/person` across `nss.person` +
│                       `nss.person_address` plus Foundation's `master_data` — core (`/persons`
│                       list with optional `gender_code`/`marital_status_code`/
│                       `blood_group_code` filters + `limit`/`offset` pagination,
│                       `/persons/{person_pk}` detail), addresses
│                       (`/persons/{person_pk}/addresses`, 404 if the person doesn't exist),
│                       search (`/search?q=` — `pg_trgm` similarity on `first_name`/`last_name`
│                       plus `ILIKE` prefix match on `person_id`/`mobile_number`, ordered by
│                       similarity, capped at 50 results); `aadhaar_encrypted`/`aadhaar_hash` are
│                       never returned (PER-BR-081) — only `aadhaar_last4` is exposed for masked
│                       display; see `docs/03_Solution/api/PERSON_API_CONTRACT.md`
└── schemas/
    ├── bootstrap.py    Pydantic response models (RoleResponse, PermissionResponse,
    │                    HealthResponse); audit columns deliberately excluded from the contract
    ├── foundation.py   11 plain Pydantic models (no `from_attributes`, raw psycopg2 dicts) —
    │                    one per exposed table/view; excludes audit columns plus
    │                    `current_value` (sequences) and unimplemented FK columns (documents)
    ├── organization.py 4 plain Pydantic models (no `from_attributes`, raw psycopg2 dicts) —
    │                    OrganizationTypeResponse, StatusResponse (renamed from
    │                    `OrganizationStatusResponse` now that it backs the unified,
    │                    cross-module `STATUS` master-data category rather than an
    │                    organization-only status table),
    │                    OrganizationResponse (full contact/online-presence fields — nullable
    │                    `phone_number`/`mobile_number`/`org_email`/`org_website_url`/
    │                    `org_youtube_channel_url`; required `email`/`website_url`/
    │                    `youtube_channel_url` with NSS-wide DB defaults — plus resolved
    │                    type/status/parent names and Foundation geography names),
    │                    OrganizationHierarchyNodeResponse (leaner, no contact/geography fields,
    │                    matching `/hierarchy`'s narrower SQL); excludes audit columns
    └── person.py       3 plain Pydantic models (no `from_attributes`, raw psycopg2 dicts) —
                         PersonResponse (full detail: demographics + resolved gender/
                         marital_status/blood_group/emergency_relationship names, masked
                         `aadhaar_last4` only, photo FK), PersonSummaryResponse (list/search —
                         omits Aadhaar, emergency contact, photo), PersonAddressResponse
                         (resolved address_type plus city_village/postal_code/district/state/
                         country chain via the `city_village_postal_code_map` junction);
                         excludes audit columns
```

This is the only API layer in the codebase. `backend/` (the earlier Django prototype
covering `foundation`, `authentication`, `family`, `membership`, `heritage`) was fully archived
and removed once the FastAPI direction was adopted; the directory is now empty. Modules
referenced elsewhere in the project's roadmap (`mahila`, `kumari`, `kishor`, `sevak`,
`publications`, `upbs`, `reports`, `administration`) **do not exist yet** in either `api/` or
any other code form — they are planned, not scaffolded.

### `frontend/` — Bootstrap + Foundation + Organization + Person Verification UIs detail

```
frontend/
├── index.html          Tier 0 Bootstrap Verification UI entry point — a centred System Status
│                        card above a responsive grid (1 column mobile, 2 tablet/`md`, 3
│                        desktop/`xl`) of RBAC Roles / Permissions / Role Permissions cards;
│                        Alpine.js directives bound to `bootstrapApp()` (declared via `x-data`);
│                        nav bar links to `/foundation`, `/organization`, and `/person`
├── foundation.html      Tier 1 Foundation Verification UI entry point — same System Status card,
│                        then a 4-tab layout (`foundationApp()`, tabs `tabs-boxed`): Master Data
│                        (categories + filterable master-data table), System Config (settings +
│                        ID sequences, `current_value` deliberately not shown), Geographic
│                        (country→state→district→city/village drill-down + postal codes),
│                        Runtime Tables (document_master; notes `field_change_log` exists in the
│                        DB but isn't exposed until Tier 5/auth); nav bar links to `/`,
│                        `/organization`, and `/person`
├── organization.html    Tier 2 Organization Verification UI entry point — same System Status
│                        card, then a 3-tab layout (`organizationApp()`, tabs `tabs-boxed`):
│                        Reference Data (org types + statuses), Organizations (list filterable by
│                        `type_code`/`status_code`, click-to-drill-down into a selected org's
│                        `/children`), Hierarchy (the flat recursive-CTE result rendered as an
│                        indented tree via `depthIndent(depth)`); nav bar links to `/`,
│                        `/foundation`, and `/person`
├── person.html          Tier 3 Person Verification UI entry point — same System Status card,
│                        then a 2-tab layout (`personApp()`, tabs `tabs-boxed`): Persons (list
│                        filterable by `gender_code`/`marital_status_code`/`blood_group_code`,
│                        click-to-drill-down into a selected person's full detail + resolved
│                        addresses), Search (debounced `pg_trgm` fuzzy search against `/search`);
│                        masked Aadhaar (`aadhaar_last4` only) shown in the detail panel; nav bar
│                        links to `/`, `/foundation`, and `/organization`
├── assets/
│   ├── css/style.css   One rule: hides `[x-cloak]` elements until Alpine.js initializes
│   ├── img/nss-logo.png NSS logo, copied from `NSS LOGO/logooo.png`
│   ├── js/app.js        Defines `bootstrapApp()` — Alpine data component with health/roles/
│   │                    permissions/selectedRole state and fetch methods against
│   │                    `/api/v1/bootstrap/*` (relative paths, `API_BASE = "/api/v1/bootstrap"`)
│   ├── js/foundation.js Defines `foundationApp()` — Alpine data component, `FND_API =
│   │                    "/api/v1/foundation"`; lazily loads each tab's data on first visit
│   │                    (`loadMasterTab()`/`loadConfigTab()`/`loadGeoTab()`/`loadRuntimeTab()`),
│   │                    toggle-deselect on country/state/district selection
│   ├── js/organization.js Defines `organizationApp()` — Alpine data component, `ORG_API =
│   │                       "/api/v1/organization"`; lazily loads each tab's data on first visit
│   │                       (`loadReferenceTab()`/`loadOrganizationsTab()`/`loadHierarchyTab()`);
│   │                       `selectOrganization()` toggles a row and fetches its `/children`;
│   │                       `filterOrganizations()` re-fetches on `type_code`/`status_code` change
│   └── js/person.js     Defines `personApp()` — Alpine data component, `PERSON_API =
│                        "/api/v1/person"`; `fetchFilterOptions()` uses `Promise.allSettled` (the
│                        only such usage in the codebase) since gender/marital-status/blood-group
│                        options come from three independent Foundation `master_data` queries;
│                        `selectPerson()` fetches detail + addresses in parallel with asymmetric
│                        failure handling; `selectPersonByPk()` bridges search results into the
│                        detail panel; `executeSearch()` is debounced (the only debounced fetch in
│                        the codebase) against `/search?q=`
└── README.md            Full file/function/state-property reference for all four pages — see it
                          directly for detail rather than duplicating it here
```

None of the four pages is an admin dashboard — all are Tier-scoped verification UIs proving the
database→API→frontend chain end to end for their tier. Tech stack is Tailwind CSS + DaisyUI +
Alpine.js, all via CDN (DaisyUI/Alpine.js pinned with SRI hashes; Tailwind's Play CDN JIT
compiler can't be SRI-pinned — see Architecture above) — no Node.js build step, no framework, no
Django templates. Served entirely by FastAPI (see `api/` detail above); no separate frontend
server is needed since all four pages are same-origin with the API. Every fetch method across
`app.js`, `foundation.js`, `organization.js`, and `person.js` follows the same
pattern: set loading/error state → try/fetch/parse → catch sets an error flag (never exposes
raw error text to the UI) → finally clears loading. Authentication UI is deferred to Tier 5 — by
design, Tiers 0-3 have no login, session, or credentials anywhere in this folder.

### `docs/01_Authoritative_References/NSS/` detail

Source-faithful transcription of the official NSS Bye-Law (`BY-LAW/NSS/NSS BYE-LAW.pdf`,
cross-checked against `BY-LAW/NSS/NSS_Bye_Law.docx`), organized by legal section:

```
NSS/
├── SECTION-A_PRELIMINARY_AND_GENERAL_PROVISIONS/   REF-001 — Name, Registered Office, Preamble, Objects, Memorandum of Association
├── SECTION-B_MEMBERSHIPS/                          REF-002 — Probationary/Regular/Associate Members, Cessation
├── SECTION-C_CONSTITUTION_OF_THE_KENDRA_SANGHA/    REF-003-C…009 — Governing Body, its Functions, and all 6 office-bearer duties;
│                                                    plus the two 1975 amendment Resolutions (REF-003-C(i)(2)-1975-01,
│                                                    REF-003-C(i)(8)-1975-02), filed adjacent to the clauses they amend
├── SECTION-D_ADVISORY_BOARD/                       REF-003-D
├── SECTION-E_GENERAL_BODY/                         REF-003-E
├── SECTION-F_FUNDS_OF_THE_KENDRA_SANGHA/           REF-003-F[A] (Funds), REF-003-F[b] (Maintenance), REF-003-F[c] (Utilisation) — 3 documents
├── SECTION-G_ACCOUNTS_AND_AUDIT/                   REF-003-G
├── SECTION-H_POWER_TO_AMEND/                       REF-003-H
└── SECTION-I_DISSOLUTION/                          REF-003-I
```

**No "Section J" exists in the source Bye-Law.** The Bye-Law's statutory sections end at
Section I (Dissolution); the two 1975 Resolutions that follow in the source text are explicit
amendments to Section C (inserting sub-clauses into Functions of the Governing Body and Duties
of the Secretary/Parichalak), not a standalone section. The content is filed as the two Section
C amendment documents above, not under an invented Section J.

Each REF document's clause-level numbering (numerals, letters, roman numerals) matches the
source exactly. `REF-001` additionally preserves the Memorandum of Association's
founding-members table (9 names + addresses), witnesses table, and the source's three distinct
certification/signature blocks (Memorandum, post-Dissolution, and post-Resolution) as separate,
non-deduplicated content, since all three appear separately in the source.

### `docs/01_Authoritative_References/MAHILA_SANGHA/` detail

Source-faithful transcription of the Nilachala Saraswata Mahila Sangha's own Constitution &
Bye-Law (`BY-LAW/NSS - Mahila Sangha/NSS Mahila Sangha By-Law.pdf`, cross-checked against
`BY-LAW/NSS - Mahila Sangha/NSS_Mahila_Sangha_Bye_Law.docx`) — a sibling folder to `NSS/`, not
nested under it, since Mahila Sangha is a separately registered entity with its own Bye-Law.
Uses a dedicated `REF-MS-XXX` identifier family (distinct from NSS's `REF-00X` family):

```
MAHILA_SANGHA/
├── SECTION-A_MEMORANDUM_AND_REGISTRATION/  REF-MS-MOA — Certificate of Registration, Memorandum, founding Governing Body + signatories + witnesses, historical 1989-1991 roster
├── SECTION-B_AIMS_AND_OBJECTS/             REF-MS-1
├── SECTION-C_MEMBERSHIP/                   REF-MS-2
├── SECTION-D_ENROLMENT_PROCEDURE/          REF-MS-3
├── SECTION-E_CESSATION_OF_MEMBERSHIP/      REF-MS-4
├── SECTION-F_CONSTITUTION_OF_THE_SANGHA/   REF-MS-5
├── SECTION-G_GOVERNING_BODY/               REF-MS-6(i)…6(viii) — Constitution, Powers & Duties, and all 6 office-bearer duties
├── SECTION-H_FUNDS/                        REF-MS-7(i)/(ii)/(iii) — Comprising/Maintenance/Utilisation, 3 documents mirroring NSS's own Funds-section split
├── SECTION-I_LEGAL_REPRESENTATION/         REF-MS-8
├── SECTION-J_AUDIT/                        REF-MS-9
├── SECTION-K_DISPUTE_SETTLEMENT/           REF-MS-10
├── SECTION-L_POWER_TO_AMEND/               REF-MS-11
└── SECTION-M_DISSOLUTION/                  REF-MS-12
```

22 documents total, all verified against source with clause numbering (numerals/letters/roman
numerals) preserved exactly as printed, including source quirks (no labeled "b)" sub-item in
Clause 6(ii); Clause 8 has no heading title at all — title assigned editorially). Every
REF-MS document's "Related Governance" section cites `AUTH-001` as the source defining the
`REF-MS` identifier family — `AUTH-001` defines it via `AUTH-ID-002A` and the Appendix B family
mapping, backed by `GDR-002`.

### `database/` detail

```
database/
├── scripts/              00_create_database.sql (superuser, postgres DB: creates nss_erp
│                         database + nss_db_owner/nss_db_backend roles, both LOGIN, no password,
│                         via dblink),
│                         01_extensions.sql (superuser, nss_erp: pgcrypto/pg_trgm/btree_gin/postgis,
│                         nss schema),
│                         02_build.sh/.ps1 (runs all implemented DDL+seed in phase order),
│                         03_validate.sh/.ps1 (row-count/FK integrity checks),
│                         04_grant_backend.sql (grants nss_db_backend read-only SELECT on all
│                         nss.* tables, for the FastAPI API layer) — replaced the old repo-root
│                         validate_foundation.sh; see scripts/README.md for the full
│                         database-to-running-API sequence and phase-by-phase execution table
├── ddl/
│   ├── 00_bootstrap/     Implemented, committed — 3 tables: role_master,
│   │                     permission_master, role_permission (RBAC definitions, created
│   │                     before Foundation — zero FK dependencies; SOL-ARCH-011). Owned by
│   │                     Administration; see Gotchas for the role-catalogue discrepancy
│   ├── 01_foundation/    Implemented — 12 tables across 12 DDL files (02_master_category.sql
│   │                     … 13_city_village_postal_code_map.sql; extensions moved to scripts/):
│   │                     master_category, system_setting, id_sequence_master, country,
│   │                     document_master, field_change_log, master_data, state, district,
│   │                     city_village, postal_code, city_village_postal_code_map. Supersedes
│   │                     an older prototype (see `database/README.md` Superseded Artifacts)
│   ├── 02_organization/  Implemented — 1 table: organization (self-referencing
│   │                     hierarchy, address inline, no `organization_address` table). The
│   │                     former `organization_type_master`/`organization_status_master` tables
│   │                     were retired — organization type and status are now rows in
│   │                     Foundation's generic `master_data` (categories `ORGANIZATION_TYPE`,
│   │                     `STATUS`), referenced via `organization_type_master_data_pk`/
│   │                     `status_master_data_pk`. This diverges from the frozen generic
│   │                     3-table structure; `organization_code` naming/width/nullability and
│   │                     the seeded type codes also don't yet match two separate frozen/design
│   │                     specs — see Gotchas
│   └── 03_person/        person_master_tables.sql (gender/marital_status/address_type masters), person.sql, person_address.sql — superseded prototype (uses per-domain masters, not the `master_data` pattern implemented in `01_foundation/`); will be replaced (see `feature/person-ddl`)
└── seed/
    ├── 00_bootstrap/     `role_master`: 8 roles seeded (3 SYSTEM + 5 ORGANIZATIONAL,
    │                     matching SOL-ADMIN-004 §8.7 frozen catalogue);
    │                     `permission_master`/`role_permission`: empty, pending the permission
    │                     catalogue
    ├── 01_foundation/    Implemented — 8 seed files: 13 master categories, 82 master data
    │                     values (GENDER/MARITAL_STATUS/ADDRESS_TYPE/DOCUMENT_TYPE/
    │                     MEMBERSHIP_TYPE/STATUS/RELATIONSHIP_TYPE/ORGANIZATION_TYPE/BLOOD_GROUP — `STATUS`
    │                     is a unified, cross-module category replacing the former
    │                     `MEMBERSHIP_STATUS`, now 13 values; `ORGANIZATION_TYPE` moved here
    │                     from Organization, now 10 values), 11 ID sequences (PERSON
    │                     zero-padded to 10 digits — see Gotchas; includes 2 new sequences,
    │                     `PARIBARIK_ASANA`/`PARIBARIK_SANGHA`, added for the 2 new organization
    │                     types), 5 countries, 112
    │                     states, ~770 districts (India only), 4 system settings, 2 postal
    │                     codes (minimal bootstrap set — full postal code data is a future task)
    ├── 02_organization/  Implemented — 3 unique named
    │                     organizations (Kendra, Nilachala Kutira, Smruti Mandira); organization
    │                     type (10 values) and status (13 values) seed data now lives in
    │                     `01_foundation/` `master_data`, not here
    └── 03_person/        gender/marital_status/address_type seed rows — superseded prototype, seeds tables that don't exist in the new pattern
```

### `docs/03_Solution/` detail

```
03_Solution/
├── modules/
│   ├── organization/     01_module_overview/02_erd/03_lifecycle/04_business_rules/05_table_design (v1.1.0, GOVERNANCE ALIGNED); walks back the ANCHALIKA/ZILLA/SAKHA/PATHA_CHAKRA type-to-type parent matrix to an OPEN item — only the generic apex + self-referencing 3-table structure is frozen. Implemented in SQL, matching that generic structure — but the implemented `organization_code` column (VARCHAR(10), nullable) doesn't match `ORG-PENDING-001`'s frozen `organization_short_code` spec (VARCHAR(5), NOT NULL), and seeded type codes (`ANCHALIKA_SANGHA` etc.) don't match this doc's short forms (`ANCHALIKA` etc.) — see Gotchas
│   ├── person/            same pattern + README.md, v1.0.0 SOURCE ALIGNED, 5 files — **1 table** (`person` only — `document_master` is Foundation-owned); docs name the business identifier `person_id`, conflicting with the implemented DDL's `person_code` (see Gotchas); address/Aadhaar/photo/blood-group explicitly left OPEN despite `person_address` already existing in SQL
│   ├── membership/         01-05 overview/erd/lifecycle/business_rules/table_design, all DRAFT — no corresponding API/backend code exists yet (see Gotchas)
│   ├── family/             5 files, frozen 4-table design — no corresponding API/backend code exists yet (see Gotchas)
│   ├── attendance/         6 files (business_rules/table_design/review_workflow at slots 04/05/06, FROZEN) + DARSHAK_BUSINESS_RULE.md (see below) — zero corresponding backend code
│   ├── heritage/           01-05 overview/erd/lifecycle/business_rules/table_design, v1.0.0 SOURCE ALIGNED — 8 tables designed (founder_master + teachings/objectives/milestones/publications/office-bearers + 2 lookup masters); zero implementation exists (no API/backend code) for any of the 8 designed tables
│   ├── kumari/             01-05 overview/erd/lifecycle/business_rules/table_design, v1.0.0 SOURCE ALIGNED (document-Status DRAFT) — KM000001 ID format
│   ├── kishor/            01-05 overview/erd/lifecycle/business_rules/table_design, v1.0.0 SOURCE ALIGNED (document-Status DRAFT) — KH000001 ID format + frozen v2.1 Guardian Model (Guardian must independently qualify via `sangha_sevi` identity)
│   ├── mahila/             01-05 overview/erd/lifecycle/business_rules/table_design, v2.1.0 — one body, two names (Mahila Governing Body = Mahila Parichalana Mandali); freezes the Mandali term at 2 years (MAH-040)
│   ├── sevak/              01-06 core sequence (only 06_table_design FROZEN, rest DRAFT/consolidation-in-progress) + sangha/, seva/, events/ subdocs; core SEV-001..040
│   ├── foundation/         01-04 overview/erd/business_rules/table_design, v1.0.0 SOURCE ALIGNED — describes 10 tables: the original 8 (master_category, master_data, system_setting, id_sequence_master, country, state, district, city_village) plus `document_master` and `field_change_log`, Foundation-owned shared infrastructure (`DOC-ARCH-001`, `CROSS_MODULE_PRINCIPLES.md`). **Implemented in SQL** — all 10 designed tables have DDL under `database/ddl/01_foundation/`, plus 2 more the design doc doesn't describe yet (`postal_code`, `city_village_postal_code_map`) — see Gotchas
│   ├── administration/     10 files (5 RBAC/Bootstrap docs + 1 Bootstrap RBAC column-level design + 4 Correspondence Register docs) — v1.0.0/v1.2.0 SOURCE ALIGNED — **8 Administration-owned tables**: the 5 RBAC tables (role_master, permission_master, role_permission, user_role, admin_scope — the first 3 also sequenced as "Phase 0 Bootstrap RBAC," `SOL-BOOT-001`/`SOL-ARCH-011`, DDL implemented and committed) plus 3 Correspondence Register tables (correspondence, correspondence_document, correspondence_finance_reference — `CORR-DECISION-003`); `user_account`/`password_history` are exclusively Authentication-owned per the Table Ownership Declaration. **Filename collision:** `06_bootstrap_rbac_table_design.md` and `06_correspondence_register_erd.md` share the same number — see Gotchas
│   ├── authentication/     Solution-layer "Authentication & Security", 5 files — v1.0.0 SOURCE ALIGNED — ERD still shows 7 tables, but exclusive ownership is only `user_account`+`password_history`; the other 5 RBAC tables are exclusively Administration-owned and appear here only for evaluation, not management. Argon2/JWT/session/Aadhaar-encryption/RLS as principles. No corresponding API/backend implementation exists yet for any of this module's tables
│   ├── governance/         Solution-layer ERP module, distinct from docs/00_Project_Governance/, 5 files — v1.0.0 SOURCE ALIGNED — Unified Body Governance Model (body_type_master, body_master, position_master, body_member_assignment, acting_position_assignment) + election entities (election, election_nomination, election_vote, election_result), 9 tables. **Freezes the Mahila Parichalana Mandali term at 3 years** (`04_governance_business_rules.md` GOV-BR-036) **and, per `03_governance_lifecycle.md`, a formal consensus→election→election-table reconstitution process** — both directly conflicting with mahila/'s own frozen **2-year** term (MAH-040) and its consensus-only reconstitution process; unreconciled, see Gotchas/Open questions. No corresponding API/backend implementation exists yet
│   ├── publications/       7 files (overview/erd/business_rules/table_design/functional_design/ui_workflow/notification_purchase_design), v1.0.0 SOURCE ALIGNED + USER REQUIREMENTS — zero new tables, reuses Heritage's nss_publication/publication_type_master/publication_language_master
│   ├── upbs/               01-04, v1.0.0 SOURCE ALIGNED — 7 tables (upbs_event, upbs_registration, delegate_card, prasad_patra, accommodation_allocation, camp_master, guest_reference); Day 1/2/3 ops + volunteer structure explicitly PENDING
│   ├── reports/            01-04, v1.0.0 SOURCE ALIGNED — 5 metadata/configuration-only tables (report_category_master, report_definition, report_filter_definition, dashboard, dashboard_widget); consumes but never duplicates other modules' data
│   ├── audit/              01-04, v1.0.0 SOURCE ALIGNED — 2 tables (audit_master, system_event_log)
│   ├── backup_technical/   01-04, v1.0.0 SOURCE ALIGNED — 2 tables (backup_master, restore_history)
│   ├── finance/            01-05 design/erd/business_rules/table_design/lifecycle, v1.0.0 SOURCE ALIGNED (ERD tagged DRAFT — LOGICAL DESIGN) — 7 tables (financial_year, financial_scope, fund_master, financial_transaction, financial_receipt, financial_payment, financial_transfer); derives from REF-003-F[A]/[b]/[c] and REF-MS-7(i)-(iii); Financial Scope Independence principle (FIN-ARCH-001) keeps Financial Scope distinct from Organization; correctly follows the project's `_code` business-identifier convention (contrast with the `_id`/`_code` conflict below); business rules FIN-BR-001–068
│   ├── programmes_events/  Module #21, 01-05 overview/erd/lifecycle/business_rules/table_design, v0.1.0 DRAFT — the one module NOT tagged SOURCE ALIGNED; "ARCHITECTURALLY JUSTIFIED" per its cross-module review but "FORMAL MODULE FREEZE PENDING." Programme Type → Event Instance two-level model (Organization ≠ Event Location; Patha Chakra = Organization Type, not Event/Programme Type). **7 candidate common tables**: `programme_type`, `event`, `event_day`, `event_session`, `event_registration`, `event_location`, `event_history` — all cross-module reconciliation gates closed (`SOL-EVT-007`) but still none frozen DDL. Backed by 7 cross-module architecture docs — see `architecture/` below.
│   └── assets_property/    Module #22, 01-05 overview/erd/lifecycle/business_rules/table_design, v1.0.0 DRAFT — SOURCE ALIGNED. Manages the physical/administrative record of NSS movable/immovable property and assets: `Property`/`Asset` as primary entities plus `Custodianship`, `Statutory Record`, `Maintenance Record`. 7 tables: `property`, `asset`, `custodianship`, `property_statutory_record`, `maintenance_record`, `property_document`, `asset_document`. 74 business rules (`AP-001`–`AP-074`: 24 CONSTITUTIONAL, 32 ERP, 13 CROSS-MODULE, 5 PENDING). Depends only on Foundation + Person + Organization (no hard FK to Finance); sits at Tier 6 per `IMPLEMENTATION_DEPENDENCY_ORDER.md`.
├── api/                   Consolidated read-only API contract docs, one per implemented tier —
│                          moved out of `architecture/` into this dedicated folder (was
│                          scattered there previously; see the Gotcha on this move below)
│   ├── README.md
│   ├── BOOTSTRAP_API_CONTRACT.md      v1.0, DRAFT — Tier 0 Bootstrap RBAC read-only API
│   │                                   contract: 4 endpoints (`health`, `roles`,
│   │                                   `permissions`, `roles/{pk}/permissions`) over 3 tables
│   │                                   (`role_master`/`permission_master`/`role_permission`)
│   ├── FOUNDATION_API_CONTRACT.md     v1.1, DRAFT — Tier 1 Foundation read-only API
│   │                                   contract: 17 endpoints across 11 tables, conventions
│   │                                   (query-param filtering, hierarchical drill-down, code
│   │                                   lookups, no pagination in Tier 1), full endpoint
│   │                                   catalogue with example responses, response-schema
│   │                                   summary, error table, implementation file map
│   └── ORGANIZATION_API_CONTRACT.md   v1.0, DRAFT — Tier 2 Organization read-only API
│                                       contract: 6 endpoints (`types`, `statuses`,
│                                       `organizations` list/detail/children, `hierarchy`) over 3
│                                       tables, carrying forward Tier 0/1's conventions plus the
│                                       recursive-CTE `/hierarchy` pattern
├── standards/
│   └── lifecycle/         SOL-LIFE-001 (PARTICIPATION_LIFECYCLE_RULES.md), SOL-LIFE-002 (PERSON_LIFECYCLE_RULES.md), both FROZEN v1.0.0 — a SOLUTION-layer standards path distinct from the governance-layer docs/00_Project_Governance/STD/, not yet cross-referenced from either README or from the Sevak/Mahila/Kumari module docs that should cite SOL-LIFE-001 (see Gotchas)
├── architecture/
│   ├── README.md
│   ├── TECH_STACK_DECISIONS.md        v1.3 — approved SOLUTION-layer tech decision; Django-to-FastAPI
│   │                                   migration (FastAPI is now the sole backend framework, no ORM);
│   │                                   Mobile Strategy (`TECH-MOB-001`, FROZEN — Flutter Android+iOS
│   │                                   replaces PWA-first/Capacitor) — see Architecture section above
│   ├── DEVELOPER_REFERENCE_GUIDE.md   per-module "which doc to read before coding" matrix
│   ├── PROGRAMME_EVENT_DOMAIN_MODEL.md         (`SOL-EVT-001`) — domain model for Programmes & Events, feeding the `programmes_events` module
│   ├── EVENT_ENTITY_RECONCILIATION.md          (`SOL-EVT-002`) — reconciles that domain model against UPBS/Kishor/Sevak/Mahila/Finance/Attendance's own event-shaped entities
│   ├── MODULE_DEPENDENCY_MAP.md                (`SOL-ARCH-007`) — dependency map (hard FK/runtime/domain integrations), PROPOSED not frozen (v0.1.0); its §3 inventory table now lists all 22 modules (incl. Assets & Property), matching its own status footer — the prior 21-vs-22 inconsistency was fixed by commit `1d96fb1`
│   ├── IMPLEMENTATION_DEPENDENCY_ORDER.md      (`SOL-ARCH-008`), `IMPLEMENTATION-TIER-001` — 12-tier build order across all 22 modules, FROZEN (Assets & Property in Tier 6). §79's DRAFT/v0.1.0/21-modules status text was fixed by commit `1d96fb1` (now reads FROZEN/v1.0.0/22-modules) — but §79 still says `PHYSICAL DDL: FOUNDATION TIER 1 COMPLETE` / `NEXT: TIER 2`, not reflecting that Tier 2 Organization DDL is now also implemented (see "Current position" above)
│   ├── PROGRAMMES_EVENTS_CROSS_MODULE_REVIEW.md (`SOL-EVT-006`), v1.1.0, FROZEN — final compatibility review for Module #21 against every other module; no hard conflicts; open ownership/migration-strategy risks it originally flagged were resolved by the file below
│   ├── CROSS_MODULE_PRINCIPLES.md              (`ARCH-CROSS-001`), v1.1.0, FROZEN — project-wide principles: one-owner-per-table, cross-module reference not duplication, Finance sole-owner of financial transactions, `DOC-ARCH-001` (document_master + field_change_log → Foundation), Correspondence Register decision. Carries 3 explicitly PENDING (not frozen) DDL-phase design notes: org short code, local Sakha number format, Visitor vs. Approved Darshak threshold
│   ├── FK_DEPENDENCY_GRAPH.md                  (`SOL-ARCH-009`), FROZEN — physical FK dependency graph ("Gate 8") across 86 frozen tables, topologically sorted into 8 depths, zero cycles; resolves the audit-actor circular-dependency problem via a two-pass DDL strategy
│   ├── DDL_CREATION_ORDER.md                   (`SOL-ARCH-010`), FROZEN — the exact numbered `CREATE TABLE` sequence for all 86 tables ("Gate 9") plus the Pass-2 deferred-constraint list
│   ├── BOOTSTRAP_ARCHITECTURE.md               (`SOL-ARCH-011`), FROZEN — Phase 0: creates/seeds `role_master`/`permission_master`/`role_permission` (zero FK deps) before Foundation; defines `nss_db_owner` (PostgreSQL DDL owner) ≠ `NSS_ERP_ADMIN` (ERP RBAC role); does not change SOL-ARCH-010's depth/sequence or claim table ownership (stays with Administration). Permission catalogue, bootstrap-admin Sangha Sevi identity, and MFA-controlled DB access (future `SOL-ARCH-012`) remain PENDING
│   └── PROGRAMMES_EVENTS_RECONCILIATION_DECISIONS.md (`SOL-EVT-007`), FROZEN — closes all 7 P&E cross-module reconciliation gates; freezes `P&E-ARCH-001`/`002`; candidate table set settled at 7
├── code_explanations/      Per-layer "requirement + line-by-line" code catalogues — moved out
│                          of `architecture/code_explanations/` into this dedicated top-level
│                          folder (one level up, out of `architecture/`; see the Gotcha on this
│                          move below):
│                          API_CODE_EXPLANATIONS.md, DATABASE_CODE_EXPLANATIONS.md,
│                          UI_CODE_EXPLANATIONS.md, SECURITY_CODE_EXPLANATIONS.md,
│                          TESTING_CODE_EXPLANATIONS.md (updated for Tier 3
│                          Person) — plus four security audit reports:
│                          TIER0_SECURITY_AUDIT.md (v1.1, Complete — 10 passed, 1 fix applied, 6
│                          advisory [4 resolved/1 partial/1 N/A]), TIER1_SECURITY_AUDIT.md (v1.1,
│                          Complete — 9 passed, 6 advisory [3 resolved/1 partial/1 advisory/1
│                          N/A]), TIER2_SECURITY_AUDIT.md (Tier 2 Organization), and
│                          TIER3_SECURITY_AUDIT.md (Tier 3 Person); see
│                          code_explanations/README.md
├── database/
│   └── DATABASE_DESIGN_STANDARDS.md   (`SOL-DB-001`, DRAFT — SOURCE ALIGNED Consolidation) — cross-module DB conventions consolidated from module table-design docs: `_pk` UUID PK convention, audit columns, soft-delete, master-data architecture (generic `master_category`/`master_data` vs domain masters), module ownership boundaries (one owning module per table), cross-module FK principles, DDL build order sketch. **States a `_id` business-identifier convention (`person_id`, `organization_id`, `sangha_sevi_id`) that contradicts the project's already-frozen `_code`-only convention** — see Gotchas/Open questions
├── security/
│   └── SECURITY_ARCHITECTURE.md       (`SOL-SEC-001`, DRAFT — SOURCE ALIGNED Cross-Reference) — routing map only, no new rules: STD-05 (policy) → Authentication (identity/credentials) → Administration (RBAC) → Audit (logging) → per-module business rules (column-level sensitive-data handling); explicitly does not duplicate any rule already defined elsewhere
├── infrastructure/
│   └── DEPLOYMENT_SYNC_PLAN.md        Deployment/repository-sync plan
└── ui/
    ├── README.md
    └── mockups/           13 static HTML screens (Tailwind CSS + DaisyUI via CDN, no build step) + README.md; visual targets for Phase 4, not functional prototypes
```

`docs/03_Solution/api/` and `docs/03_Solution/code_explanations/` are both distinct from the
real, implemented FastAPI code at the root-level `api/` — the former holds request/response
contracts, the latter holds line-by-line narration of the same code; neither is the code itself.

`docs/03_Solution/modules/attendance/DARSHAK_BUSINESS_RULE.md` records an ERP implementation
decision (not derived from the Bye-Law): an earlier project Rule Book used "Darshak" as an
informal membership tier, but the actual Bye-Law (`REF-002`) has no such category — only
Probationary/Regular/Associate. "Darshak" is corrected to mean, operationally, either a
Probationary Member or a Regular Member visiting from another Sakha; it may appear as a UI
display label (dashboards, attendance screens) but must never be a `membership_type_master`
value in the database.

**Doc/code gap.** Membership, family, attendance, heritage, kumari, kishor, mahila, sevak,
administration, audit, authentication (Solution-layer), backup_technical, governance
(Solution-layer), publications, reports, upbs, finance, programmes_events, person, and
assets_property all have Solution-layer design docs describing schemas richer than what exists
in code — none has any corresponding API/backend implementation at all (Person's DDL exists but
has no API — see Key Workflow #3). **Foundation and Organization are now the exceptions**:
Foundation's Solution-layer design (10 tables described) is not just implemented in SQL (12
tables, see above) but also has a full read-only API (`api/routers/foundation.py`, 17 endpoints)
and verification UI (`frontend/foundation.html`); Organization's Solution-layer design (3 tables)
is **no longer** matched 1:1 in SQL — only 1 physical table (`organization`) remains, with type/
status now sourced from Foundation's `master_data` (see Key Workflow #4 and Gotchas) — but it
still has a full read-only API
(`api/routers/organization.py`, 6 endpoints) and verification UI
(`frontend/organization.html`) — both are complete DB→API→UI vertical slices, released as
v0.7.0 (Foundation) and v0.8.0 (Organization). The only other implemented API surface in the codebase is the Tier 0
bootstrap-RBAC router (`api/routers/bootstrap.py`), which isn't one of the 22 Solution-layer
modules listed above. Don't assume any other Solution-layer doc describes currently running
code.

## Setup & running

Setup is documented in `database/README.md` and `database/scripts/README.md`; the steps below
summarize the full sequence from a clean machine to a running API.

1. **Python dependencies** (repo root):
   ```
   python3 -m pip install -r requirements.txt   # macOS/Linux
   py -m pip install -r requirements.txt         # Windows
   ```
   `requirements.txt` lists FastAPI, Uvicorn, psycopg2-binary, Pydantic, python-dotenv,
   `slowapi`/`limits`/`wrapt` (rate limiting), and their transitive dependencies (Starlette,
   anyio, click, h11, idna, colorama, etc.) — no Django. It's plain UTF-8 text (a prior
   UTF-16LE Windows-migration artifact was fixed).

2. **Database (raw-SQL track):** the bootstrap sequence is documented in
   `database/scripts/README.md`:
   1. `00_create_database.sql` (as superuser on `postgres` DB) — creates `nss_erp` database and
      `nss_db_owner`/`nss_db_backend` roles (both `LOGIN`, no password).
   2. Set passwords: `ALTER ROLE nss_db_owner PASSWORD '...'; ALTER ROLE nss_db_backend PASSWORD '...';`
   3. `01_extensions.sql` (as superuser on `nss_erp`) — installs pgcrypto, pg_trgm, btree_gin,
      postgis; creates `nss` schema owned by `nss_db_owner`.
   4. `02_build.sh` / `.ps1` (as `nss_db_owner`) — runs all implemented DDL + seed in phase order
      (Bootstrap RBAC → Foundation → Organization). Prompts once for the `PGPASSWORD` if not
      already set in the environment.
   5. `03_validate.sh` / `.ps1` (as `nss_db_owner`) — post-build checks (table existence, row
      counts, unique constraints, FK integrity).
   6. `04_grant_backend.sql` (as `nss_db_owner`) — grants `nss_db_backend` read-only `SELECT` on
      all `nss.*` tables (plus future tables via `ALTER DEFAULT PRIVILEGES`), for the API layer.

   The build covers 18 tables across 4 modules (3 Bootstrap RBAC + 12 Foundation + 1
   Organization + 2 Person); only `03_person/01_person_master_tables.sql` is superseded (its
   seed data now lives in Foundation's `master_data`) and is skipped — `02_person.sql`/
   `03_person_address.sql` are real, built DDL. Cross-platform:
   `.sh` and `.ps1` wrappers are operationally identical — same SQL, same execution order, same
   password-prompt behavior. This raw-SQL schema **is** now consumed — read-only — by the
   FastAPI Tier 0 endpoints, so this step is required before starting the API.

3. **API environment file:** create `api/.env` (read via `python-dotenv`'s `load_dotenv()` at
   `api/config.py:16-17`, which resolves the path as `Path(__file__).resolve().parent / ".env"`
   — i.e. `api/.env`, not a repo-root `.env`) with:
   ```
   DB_NAME=nss_erp
   DB_USER=nss_db_backend
   DB_PASSWORD=...       # the password you set for nss_db_backend in step 2
   DB_HOST=localhost
   DB_PORT=5432
   ```
   `DB_NAME`, `DB_USER`, `DB_PASSWORD` are required with no defaults — `Settings.validate()`
   (`api/config.py:32-45`) raises `RuntimeError` listing any that are missing. `DB_HOST`
   defaults to `localhost`, `DB_PORT` to `5432` if omitted.

4. **Start the API** (from the **repository root**, not from `api/`):
   ```
   python3 -m uvicorn api.main:app --reload --port 8001   # macOS/Linux
   py -m uvicorn api.main:app --reload --port 8001         # Windows
   ```
   Swagger UI: `http://localhost:8001/docs` (disable via `DISABLE_DOCS=true`/`1`/`yes` in
   `api/.env`, which also disables `/redoc` and `/openapi.json`). Bootstrap Verification UI:
   `http://localhost:8001/`; Foundation Verification UI: `http://localhost:8001/foundation`;
   Organization Verification UI: `http://localhost:8001/organization`; Person Verification UI:
   `http://localhost:8001/person`
   (all four served from `frontend/`, each skipped automatically if its file doesn't exist).
   Tier 0 endpoints (read-only, no authentication):
   `GET /api/v1/bootstrap/health`, `GET /api/v1/bootstrap/roles`,
   `GET /api/v1/bootstrap/permissions`, `GET /api/v1/bootstrap/roles/{role_pk}/permissions`.
   Tier 1 endpoints (read-only, no authentication) — 17 endpoints under `/api/v1/foundation/*`;
   see `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` for the full catalogue.
   Tier 2 endpoints (read-only, no authentication) — 6 endpoints under `/api/v1/organization/*`
   (`/types`, `/statuses`, `/organizations`, `/organizations/{organization_pk}`,
   `/organizations/{organization_pk}/children`, `/hierarchy`); see
   `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md` for the full catalogue.
   Tier 3 endpoints (read-only, no authentication) — 4 endpoints under `/api/v1/person/*`
   (`/persons`, `/persons/{person_pk}`, `/persons/{person_pk}/addresses`, `/search`); see
   `docs/03_Solution/api/PERSON_API_CONTRACT.md` for the full catalogue.

5. **Run the tests** (from the repository root, once the database is built per step 2 and
   `api/.env` per step 3):
   ```
   pytest                    # all tests (208)
   pytest -m integration     # integration-marked tests (currently all of them)
   pytest tests/test_bootstrap.py     # Tier 0 only (21 tests)
   pytest tests/test_foundation.py    # Tier 1 only (59 tests)
   pytest tests/test_organization.py  # Tier 2 only (64 tests)
   pytest tests/test_person.py        # Tier 3 only (56 tests)
   pytest tests/test_security.py      # cross-tier security middleware only (8 tests)
   ```
   Configured via `pytest.ini` (repo root: `testpaths = tests`, `integration` marker).
   `tests/conftest.py`'s `client` fixture wraps `fastapi.testclient.TestClient(app)` against the
   **real** local Postgres DB set up in step 2 — nothing is mocked, so these are true
   integration tests, not unit tests. `pytest` and `httpx` (required by `TestClient` at import
   time) are pinned in `requirements.txt`. No lint/format tooling is configured yet.

**Deployment (Render.com):** `render.yaml` (repo root) is Render's Infrastructure-as-Code
manifest — defines a single free-tier web service running `uvicorn api.main:app --host 0.0.0.0
--port $PORT`. It does **not** define a managed Render Postgres database service:
`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` (plus an apparently-unused
`DATABASE_URL` — `api/config.py` only reads the five individual vars, never a connection-string
env var) are declared as `sync: false` env vars that must be set manually in the Render
dashboard, pointing at an external Neon.dev PostgreSQL instance (per `TECH_STACK_DECISIONS.md`
§1/§6) — not provisioned by this file. `render_build.sh` runs on every deploy: installs
`requirements.txt`, then checks whether `nss.role_master` already exists on that Neon database —
if not, it creates the `nss` schema, best-effort installs `pgcrypto`/`pg_trgm`/
`btree_gin` (some may be unavailable on Neon's free tier; `postgis` isn't attempted), and runs
the same DDL+seed phases as `database/scripts/02_build.sh` (Bootstrap RBAC → Foundation →
Organization) directly via `psql`. This makes deploys idempotent — a redeploy with an
already-bootstrapped database skips DDL/seed entirely. Neither file has run in production yet
as of this writing; treat them as declared-but-unverified infrastructure.

## Configuration

| Setting | Source | Notes |
|---|---|---|
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | `api/.env` (not committed, no `.env.example`) | Required, no defaults — `Settings.validate()` raises `RuntimeError` if any is missing (`api/config.py:32-45`) |
| `DB_HOST` | `api/.env` | Defaults to `localhost` if unset (`api/config.py:26`) |
| `DB_PORT` | `api/.env` | Defaults to `5432` if unset (`api/config.py:27`) |
| `API_PORT` | `api/.env` | Defaults to `8001` (`api/config.py:30`) — defined but currently unread; the actual port is hardcoded in the `uvicorn` run command instead, so the two can silently drift if one changes without the other |
| `DISABLE_DOCS` | `api/.env` | Defaults to `false`; when truthy (`1`/`true`/`yes`), disables `/docs`, `/redoc`, and `/openapi.json` on the FastAPI app (`api/main.py`) |
| `CORS_ORIGINS` | `api/.env` | Comma-separated allowed origins; defaults to empty, in which case `CORSMiddleware` is never registered at all (no CORS headers on any response) |
| `RATE_LIMIT` | `api/.env` | Defaults to `"60/minute"` (a `slowapi`/`limits`-style rate spec); applied globally via `SlowAPIMiddleware`, not per-route |

No other configuration surface (feature flags, external service credentials, `SECRET_KEY`,
`DEBUG`, `ALLOWED_HOSTS`, etc.) exists in the code — Tier 0 has no auth/session layer at all.

## Key workflows

### 1. Health check → DB connectivity
`GET /api/v1/bootstrap/health` (`api/routers/bootstrap.py:27-39`) calls `check_connection()`
(`api/database.py:63-80`), which grabs a connection from the `psycopg2` pool, runs `SELECT 1`,
and returns it — swallowing all exceptions so no credentials/error detail ever leak to the
client. The endpoint returns `{"status": "ok"/"degraded", "database": "connected"/
"unreachable"}`. This is the only endpoint that doesn't use the `Depends(get_connection)`
pattern the other three use.

### 2. Roles / permissions lookup
`GET /api/v1/bootstrap/roles` (`api/routers/bootstrap.py:42-68`) runs
`SELECT role_master_pk, role_code, role_name, role_class, scope_level, description,
display_order, is_active FROM nss.role_master WHERE is_active = TRUE ORDER BY display_order`
via `Depends(get_connection)`, returning the 8 frozen roles as `RoleResponse` models.
`GET /api/v1/bootstrap/permissions` mirrors this against `nss.permission_master` (currently
empty — the permission catalogue isn't frozen yet).
`GET /api/v1/bootstrap/roles/{role_pk}/permissions` (`api/routers/bootstrap.py:100-152`) first
verifies the role exists and is active (404 if not), then joins `nss.role_permission` to
`nss.permission_master` for that role (currently always empty — no role-permission mappings
exist yet). All three endpoints are unauthenticated, read-only, and connect as `nss_db_backend`
— they exist to verify the RBAC schema is queryable, not to enforce RBAC yet.

### 3. Person business-ID generation (SQL-schema track, not yet wired to any write path)
`database/ddl/01_foundation/04_id_sequence_master.sql` defines an `id_sequence_master` table —
a registry of `{sequence_code, prefix, current_value, padding_length}` rows, seeded with **11**
sequences (`database/seed/01_foundation/03_id_sequence_master.sql`): `PERSON`→`P` (padding
**10** — first code is `P0000000001`, 11 characters), `SANGHA_SEVI`→`SS`, `ANCHALIKA`→`ANC`,
`ZILLA`→`ZL`, `SAKHA`→`SKH`, `SAKHA_ASANA`→`SA`, `PATHA_CHAKRA`→`PC`, `PARIBARIK_ASANA`→`PA`,
`PARIBARIK_SANGHA`→`PS`, `FAMILY`→`F`,
`DOCUMENT`→`DOC` (all padding 8 except `PERSON`, and `PARIBARIK_ASANA`/`PARIBARIK_SANGHA` at 5/3
respectively). The org-type-specific prefixes now cover **10** organization types, 2 more
(`PARIBARIK_ASANA`/`PARIBARIK_SANGHA`) than the Organization module's frozen 8-type inventory
(see Gotchas). This produces IDs for the `person.person_id` column
(`database/ddl/03_person/02_person.sql`, real implemented DDL as of Tier 3 —
`person_id VARCHAR(20) NOT NULL UNIQUE`, `uq_person_id`) — the column name now matches the
Person module design doc (`docs/03_Solution/modules/person/05_person_table_design.md`, v1.0.0
SOURCE ALIGNED), resolving the earlier `person_code`/`person_id` naming disagreement. Person has
**no seed data** (`database/scripts/03_validate.sh` checks table existence and zero row counts,
not FK integrity against seeded rows) — `tests/test_person.py` is skip-guarded wherever it needs
an actual row (via a `_get_first_person_pk`-style helper), since nothing populates `person_id`
values without a write endpoint. **No SQL function or trigger and no API code currently
implements the increment/format logic** — Tier 3's API is read-only (see workflow 5 below), so
this table remains pure configuration waiting on Tier 5/write-endpoint implementation.

### 4. Organization — hierarchy, reference data, contact fields (DB + API implemented, Tier 2)
`docs/03_Solution/modules/organization/01_organization_module_overview.md` through
`05_organization_table_design.md` (v1.1.0, GOVERNANCE ALIGNED) specify a self-referencing
`organization` table plus `organization_type_master` and `organization_status_master` — three
tables only, address inline on `organization` (no separate `organization_address` table).
**The specific Kendra → Anchalika/Zilla → Sakha → Patha_Chakra type-to-type parent matrix is
explicitly NOT frozen** — the business rules doc's §22 "Rules Explicitly Not Assumed" lists
both the exact parent-compatibility matrix and the exact `organization_type_master` seed values
as open items; only the generic apex + self-referencing structure is frozen. **As implemented,
this 3-table design has been superseded**: `database/ddl/02_organization/` now defines only the
`organization` table itself. The former `organization_type_master`/`organization_status_master`
tables were retired and their rows migrated into Foundation's generic `master_data` (categories
`ORGANIZATION_TYPE`, `STATUS`), matching the project's frozen "Master Data Driven" principle but
no longer matching this module's own frozen v1.1.0 table design. Anyone picking up further
organization work should treat the design docs as the historical target, not the current
physical schema — see Gotchas for the full reconciliation status (this diverges from
`FK_DEPENDENCY_GRAPH.md`, `DDL_CREATION_ORDER.md`, and the Governance Baseline's naming/master-
data-catalogue docs too, none of which have been reconciled with this migration).

**API now implemented.** `api/routers/organization.py` (prefix `/api/v1/organization`) exposes 6
read-only GET endpoints — the same raw-`psycopg2`/`Depends(get_connection)` pattern as Tier 0/1.
Grouped by theme:
- **Reference:** `/types`, `/statuses` — both now query Foundation's `nss.master_data` joined to
  `nss.master_category`, filtered by `category_code = 'ORGANIZATION_TYPE'` (10 active values) /
  `'STATUS'` (13 active values, a unified cross-module category replacing the former
  per-module `MEMBERSHIP_STATUS`/`ORGANIZATION_STATUS` split) respectively — no longer the
  dedicated `organization_type_master`/`organization_status_master` tables. The response model
  for `/statuses` was renamed `StatusResponse` (from `OrganizationStatusResponse`) to reflect
  that it's no longer organization-specific.
- **Core:** `/organizations` (optional `type_code`/`status_code` filters),
  `/organizations/{organization_pk}` (404 if missing),
  `/organizations/{organization_pk}/children` (404 if the parent itself doesn't exist, then
  direct children only) — all three share one SQL fragment (`_ORG_SELECT`) that joins
  `organization` to `master_data` (via `organization_type_master_data_pk`/
  `status_master_data_pk`) for type/status and LEFT JOINs the self-referencing parent plus
  Foundation's `district`/`state`/`country`/`city_village`/`postal_code` tables (address fields
  are nullable, hence LEFT JOIN).
- **Navigation:** `/hierarchy` — a `WITH RECURSIVE org_tree` CTE (anchor:
  `parent_organization_pk IS NULL`; recursive leg joins `t.organization_pk =
  o.parent_organization_pk`, tracking `depth`), returned as a flat list ordered by `depth,
  organization_name` — the UI (`frontend/assets/js/organization.js`'s `depthIndent(depth)`)
  reconstructs the indented tree client-side rather than receiving nested JSON.

`OrganizationResponse` (`api/schemas/organization.py`) additionally resolves 8 contact/
online-presence columns recently added to the DDL: `phone_number`/`mobile_number` (nullable),
`email` (required, DB default `info@nsspuri.org`)/`org_email` (nullable), `website_url`
(required, DB default `https://www.nsspuri.org`)/`org_website_url` (nullable), and
`youtube_channel_url` (required, DB default
`https://www.youtube.com/@NilachalaSaraswataSangha`)/`org_youtube_channel_url` (nullable) — the
NSS-wide defaults are always populated, the org-specific overrides are always nullable.
`OrganizationHierarchyNodeResponse` is deliberately leaner (no contact/geography fields) to match
`/hierarchy`'s narrower SQL. Full contract in `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`;
line-by-line walkthrough in `docs/03_Solution/code_explanations/API_CODE_EXPLANATIONS.md`.
Verified via 64 pytest integration tests (`tests/test_organization.py`, 7 classes) plus a
dedicated security audit (`docs/03_Solution/code_explanations/TIER2_SECURITY_AUDIT.md`).
Consumed by `frontend/organization.html`'s 3-tab UI (see `frontend/` detail above). Merged to
`main` and released as v0.8.0 (see "Current position" above).

**Two freezes live outside this module's own doc set, not inside it:** (1) the business rules
doc's freeze of exactly **8 organization types** — `KENDRA`, `NILACHALA_KUTIRA`,
`SMRUTI_MANDIRA` (unique, fixed business code) plus `ANCHALIKA`, `ZILLA`, `SAKHA`,
`SAKHA_ASANA`, `PATHA_CHAKRA` (multiple, sequence-generated — `ANC`/`ZL`/`SKH`/`SA`/`PC`) — a
type *inventory* freeze, distinct from the still-open type-to-type parent matrix above. **As
seeded, this is now 10 types, not 8**: `database/seed/01_foundation/02_master_data.sql`'s
`ORGANIZATION_TYPE` category adds `PARIBARIK_ASANA`/`PARIBARIK_SANGHA` (with matching new
`PARIBARIK_ASANA`/`PARIBARIK_SANGHA` sequences in `id_sequence_master`), neither of which is
part of the frozen 8-type inventory — a further divergence not yet reconciled (see Gotchas); (2)
`ORG-PENDING-001`, an `organization_short_code` column (`VARCHAR(5)`, `UNIQUE`, `NOT NULL`)
frozen in `docs/03_Solution/architecture/CROSS_MODULE_PRINCIPLES.md` §20.1. **As implemented,
this column does not match that spec**: `database/ddl/02_organization/03_organization.sql`
defines it as `organization_code`, `VARCHAR(10)`, `UNIQUE`, **nullable** (comment: "3-5 chars,
unique") — different name, wider column, and nullable rather than required. Separately, the
seeded `ORGANIZATION_TYPE` `master_data` rows (`database/seed/01_foundation/02_master_data.sql`
— formerly `database/seed/02_organization/01_organization_type_master.sql`, retired by this
migration) use `ANCHALIKA_SANGHA`/`ZILLA_SANGHA`/`SAKHA_SANGHA` as
business codes, not the short forms (`ANCHALIKA`/`ZILLA`/`SAKHA`) this module's own
business-rules doc uses (`SAKHA_ASANA`/`PATHA_CHAKRA` do match). See Gotchas and Open questions
for both — neither discrepancy blocks the read-only API above, which simply exposes whatever the
DDL/master_data actually define.

### 5. Person — demographics, addresses, trigram search (DB + API implemented, Tier 3, not yet released)
`docs/03_Solution/modules/person/01_person_module_overview.md` through
`05_person_table_design.md` specify the Person module design. **As implemented**,
`database/ddl/03_person/02_person.sql` defines `nss.person` (28 columns) and
`03_person_address.sql` defines `nss.person_address` — following the same Foundation
`master_data` pattern established by the Organization migration: gender, marital_status, and
blood_group all resolve through `nss.master_data` (categories `GENDER`, `MARITAL_STATUS`,
`BLOOD_GROUP`) rather than dedicated per-domain master tables, and `person_address.address_type`
resolves through `master_data` category `ADDRESS_TYPE`. Only `01_person_master_tables.sql` (the
original per-domain gender/marital_status/address_type master tables) is superseded — its seed
data now lives in Foundation's `master_data` seed (see `database/README.md`). `person` includes
DB-level format validation CHECK constraints from day one (mobile, email, country phone code,
Aadhaar last-4, emergency phone) even though Tier 3 has no write endpoints yet — these are
schema-level safety nets, not currently reachable via the read-only API.

**API implemented.** `api/routers/person.py` (304 lines, prefix `/api/v1/person`) exposes 4
read-only GET endpoints — the same raw-`psycopg2`/`Depends(get_connection)` pattern as the
other tiers, and the first router to consume the newly-extracted `api/helpers.py` shared
`rows_to_models`/`row_to_model`/pagination-constant functions (Organization's router was
refactored to use the same helpers in the same change). Grouped by theme:
- **Core:** `/persons` (optional `gender_code`/`marital_status_code`/`blood_group_code`
  filters, `limit`/`offset` pagination) returns the compact `PersonSummaryResponse` shape (no
  Aadhaar/emergency/photo fields); `/persons/{person_pk}` returns the full `PersonResponse`
  shape (404 if missing). Both share `_PERSON_SUMMARY_SELECT`/`_PERSON_DETAIL_SELECT`, which
  LEFT JOIN `nss.master_data` three/four times respectively to resolve gender, marital status,
  blood group, and (detail only) emergency-contact relationship names.
- **Addresses:** `/persons/{person_pk}/addresses` (404 if the person itself doesn't exist, then
  all active addresses) — `_ADDRESS_SELECT` resolves address type via `master_data` and location
  through the `city_village_postal_code_map` junction into `city_village`/`postal_code`/
  `district`/`state`/`country`.
- **Search:** `/search?q=` — PostgreSQL trigram similarity (`pg_trgm`, the `%%` operator) against
  `first_name`/`last_name`, combined with `ILIKE` prefix matching on `person_id`/
  `mobile_number`, ordered by `similarity(p.first_name, %s) DESC`, capped at 50 results.

**Security (PER-BR-081):** `aadhaar_encrypted` (BYTEA) and `aadhaar_hash` (VARCHAR) are never
returned by any endpoint or exposed in any Pydantic model — only `aadhaar_last4` is returned for
masked display. `api/schemas/person.py` (141 lines) defines `PersonResponse` (full detail),
`PersonSummaryResponse` (list/search — omits Aadhaar, emergency contact, photo), and
`PersonAddressResponse`, all plain Pydantic models excluding audit columns, matching the
convention established in Tier 0.

A matching Person Verification UI (`frontend/person.html` + `frontend/assets/js/person.js`,
`personApp()`) and 56 pytest integration tests (`tests/test_person.py`, 6 classes) exist, plus a
dedicated security audit (`docs/03_Solution/code_explanations/TIER3_SECURITY_AUDIT.md`). This
work is currently on `feature/tier3-person-module` — **not yet merged to `develop`/`main` or
tagged as a release** (contrast with Tier 2 Organization, tagged v0.8.0). See "Current position"
above and `docs/03_Solution/api/PERSON_API_CONTRACT.md` for the formal contract.

### 6. Foundation API — master data, geography, config, runtime (implemented, Tier 1)
`api/routers/foundation.py` (526 lines, prefix `/api/v1/foundation`) exposes 17 read-only GET
endpoints across 11 of the 12 Foundation tables — the same raw-`psycopg2`/`Depends(get_connection)`
pattern as Tier 0, plus new Tier-1 conventions (query-param filtering instead of nested paths,
e.g. `?category_code=`/`?country_pk=`; hierarchical drill-down Country→State→District→
City/Village; no pagination). Grouped by theme:
- **Master data:** `/categories`, `/categories/{pk}`, `/master-data` (optional `category_code`/
  `category_pk` filter), `/master-data/{pk}` — `nss.master_category`/`nss.master_data`.
- **System config:** `/settings`, `/settings/{setting_key}` (business-key lookup, not PK),
  `/sequences` (excludes `current_value` — no detail-by-pk endpoint) — `nss.system_setting`/
  `nss.id_sequence_master`.
- **Geographic:** `/countries`, `/states` (optional `country_pk`), `/districts` (optional
  `state_pk`), `/cities` (optional `district_pk`, currently empty — no seed data),
  `/postal-codes` (optional `state_pk` or `country_pk`), `/postal-code-mappings` (pure M:N
  junction, no `is_active`, currently empty) — plus each entity's `/{pk}` detail route.
- **Runtime:** `/documents` (optional `document_type_code`, currently empty — no seed data;
  excludes the unimplemented `person_pk`/`uploaded_by_sangha_sevi_pk` FKs).

`nss.field_change_log` is the one Foundation table **deliberately not exposed** — deferred to
Tier 5 once auth exists (`tests/test_foundation.py::TestChangeLogNotExposed` guards this by
asserting `/api/v1/foundation/change-log` 404s/405s). All list endpoints filter
`WHERE is_active = TRUE` (except the junction table, which has no such column); all detail
endpoints 404 on missing/inactive rows; malformed UUIDs 422 via Pydantic/FastAPI path-param
validation. Full contract, example responses, and the 11 response-schema fields (incl. every
deliberately-excluded column) are in
`docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`; a line-by-line implementation
walkthrough is in `docs/03_Solution/code_explanations/API_CODE_EXPLANATIONS.md`.
Verified via 59 pytest integration tests (`tests/test_foundation.py`, 13 classes) plus a
dedicated security audit (`code_explanations/TIER1_SECURITY_AUDIT.md`) with no blocking
findings. Consumed by `frontend/foundation.html`'s 4-tab UI (see `frontend/` detail above).

### 7. Security middleware — headers, CORS, rate limiting (cross-tier, implemented)
Applies to every route across all four routers plus the static frontend — see the Architecture
diagram above for exact registration order (`SlowAPIMiddleware` → `CORSMiddleware` if configured
→ `add_security_headers`). Three independent, individually-toggleable concerns:
- **Security headers** (`api/middleware.py`) — always on, no config: 4 headers on every
  response, plus `Cache-Control: no-store` scoped to `/api/*` only (so `/`, `/foundation`,
  `/organization`, `/person`, and `/assets/*` remain normally cacheable).
- **CORS** — off by default (`CORS_ORIGINS` empty); when set, `CORSMiddleware` allows only the
  listed origins, `GET` only, credentials allowed, never a wildcard origin.
- **Rate limiting** — on by default (`RATE_LIMIT="60/minute"`), keyed per client IP
  (`get_remote_address`), enforced globally (no route currently opts in to a different limit).
`tests/test_security.py` verifies all three (8 tests, 3 classes) — including a real bug it
caught during development: an earlier version of the middleware configured the `Limiter` but
never registered `SlowAPIMiddleware`, so the limit was defined but never enforced.
`tests/test_organization.py::TestOrganizationSecurity` (3 tests) and
`tests/test_person.py::TestPersonSecurity` (5 tests) separately re-verify the
same headers/`Cache-Control` behavior against the Organization and Person routers and UIs. Full
walkthrough: `docs/03_Solution/code_explanations/SECURITY_CODE_EXPLANATIONS.md`;
test walkthrough: `TESTING_CODE_EXPLANATIONS.md`; audit
verdicts: `TIER0_SECURITY_AUDIT.md`/`TIER1_SECURITY_AUDIT.md`/`TIER2_SECURITY_AUDIT.md`/
`TIER3_SECURITY_AUDIT.md` in the
same directory.

## Conventions & gotchas

- **`_pk` vs business identifier suffix — actual convention differs from some docs.** The SQL
  DDL consistently uses `<entity>_pk` (UUID) for internal surrogate keys and `<entity>_code`
  (e.g. `organization_code`, `country_code`, `sequence_code`) — never `_id` — for business/
  external identifiers, with one frozen exception: `person.person_id` (see Key Workflow #3) is
  itself named `_id`, matching the Person module's own design doc, not the `_code` pattern.
  `CLAUDE.md` correctly documents this. Some newer
  SOLUTION-layer module docs (e.g. `DATABASE_DESIGN_STANDARDS.md`)
  use `_id` in their own examples instead — that's a doc-side inconsistency, not a convention
  change; follow `_code` for new DDL.
- **Person now has a read-only API too, on an unmerged feature branch.** `api/routers/person.py`
  (Tier 3) reads `person`/`person_address` — the Tier 0 bootstrap-RBAC endpoints, the Tier 2
  Organization endpoints, and the Tier 3 Person endpoints (`api/routers/person.py`, see Key
  Workflow #5) are the DB-backed data exposed today. All three remain deliberately read-only;
  the earlier Django ORM track that once described a second, unreconciled version of these
  tables has been fully removed (see Architecture and Key Workflow #3/#4/#5 above). Note Tier 3
  is implemented but **not yet merged/released** — see "Current position" above.
- **`backend/` is empty.** The Django prototype (`config`, `authentication`, `dashboard`,
  `foundation`, `family`, `membership`, `governance`, `attendance`, `heritage` apps, templates,
  static files, `manage.py`) was fully archived and removed once the FastAPI direction was
  adopted. Nothing in this repo references it anymore except historical git commits.
- **`api/` has security middleware but still no auth; four routers registered.** `api/main.py`
  includes `api/routers/bootstrap.py` (Tier 0), `api/routers/foundation.py` (Tier 1),
  `api/routers/organization.py` (Tier 2), and `api/routers/person.py` (Tier 3), plus
  the cross-tier security middleware stack (rate limiting, opt-in CORS, security headers — see
  Architecture and Key Workflow #7 above). All four tiers remain deliberately read-only and
  unauthenticated — the new middleware hardens the transport/response layer, it does not add
  request-level identity or permission checks.
- **Governance/standards docs are far ahead of the code.** `docs/00_Project_Governance/STD/`
  (naming conventions, audit standards, security standards, master data catalog) describes a
  mature target architecture (RBAC tables, RLS, full audit trail with `*_by_sangha_sevi_pk`
  columns, etc.) that the current `api/` code does not yet implement — Tier 0 has zero
  auth/RBAC enforcement by design (deferred to a later tier). Treat the STD docs as the
  destination, not the current state.
- **Person module docs vs. Organization module docs.** Both are now implemented in SQL+API, and
  both diverge from their own frozen SOLUTION-layer design docs in ways that haven't been
  reconciled — don't confuse "documented" with "built as documented" for either. Person's design
  (`docs/03_Solution/modules/person/`, v1.0.0 SOURCE ALIGNED) is implemented as
  `database/ddl/03_person/02_person.sql` (`person`, 28 columns) and `03_person_address.sql`
  (`person_address`) — the `person_id`/`person_code` naming disagreement flagged in earlier
  passes of this doc is **now resolved**: the implemented DDL uses `person_id`, matching the
  design doc (see Key Workflow #3). What the design doc does *not* anticipate is the
  Foundation-`master_data` pattern: gender/marital_status/blood_group/address_type resolve
  through `nss.master_data` rather than the doc's own dedicated per-domain master tables — the
  same "Master Data Driven" migration already applied to Organization (see the
  `organization_type_master`/`organization_status_master` Gotcha below) was applied to Person's
  DDL from the start, so Person's frozen design docs and its implemented DDL diverge on table
  count/shape the same way Organization's do. Person's design used to describe a second table,
  `document_master`, but that was reassigned to Foundation (`DOC-ARCH-001` — see the Gotcha
  below). Organization's generic 3-table structure **is no longer** implemented in SQL — only the
  `organization` table remains, with type/status now sourced from Foundation's `master_data` (see
  the frozen-design-vs-implementation Gotcha below); separately, the implemented
  `organization_code` column doesn't match the frozen `ORG-PENDING-001` spec
  (`organization_short_code`, `VARCHAR(5)`, `NOT NULL` vs. the actual `VARCHAR(10)`, nullable
  `organization_code`), and the seeded organization-type codes don't match the design docs' short
  forms — see Key Workflow #4.
- **Tier-numbering divergence: "Tier 3" means different things in different docs.** The frozen
  12-tier build order (`IMPLEMENTATION_DEPENDENCY_ORDER.md`, `IMPLEMENTATION-TIER-001`) bundles
  Person + Organization together as a single "Tier 2," and reserves "Tier 3" for Heritage (see
  the Tier sequence table above). The actual implementation sequence — and every doc written
  since, including `CLAUDE.md`, this document's own "Current position"/Key Workflow numbering,
  the `docs/03_Solution/code_explanations/` per-layer docs, and `docs/03_Solution/api/` contract
  docs — treats Organization and Person as two separate vertical slices, calling them "Tier 2
  (Organization)" and "Tier 3 (Person)" respectively. This is a naming collision, not a contract
  violation: the frozen 12-tier *dependency order* (Foundation → Person/Organization → Heritage →
  ...) is still being honored, only the *implementation-sequence labels* diverge from it. Needs a
  human governance decision to reconcile (rename the frozen plan's tiers, or rename the
  implementation-sequence labels) — not a doc edit here.
- **`organization_type_master`/`organization_status_master` retirement contradicts multiple
  frozen/governance-aligned documents — needs a human governance decision, not a doc edit here.**
  A migration removed the dedicated `organization_type_master`/`organization_status_master`
  tables and replaced them with rows in Foundation's generic `master_data` (categories
  `ORGANIZATION_TYPE`, 10 values; `STATUS`, a renamed/unified `MEMBERSHIP_STATUS`, now 13 values
  shared across modules) — matching the project's frozen "Master Data Driven" principle, but
  leaving several other frozen documents now factually wrong about the physical schema, and none
  of them has been reconciled:
  - `docs/03_Solution/architecture/FK_DEPENDENCY_GRAPH.md` (`SOL-ARCH-009`, FROZEN) still lists
    both tables as nodes in its 86-table physical FK dependency graph.
  - `docs/03_Solution/architecture/DDL_CREATION_ORDER.md` (`SOL-ARCH-010`, FROZEN) still lists
    both tables in its numbered `CREATE TABLE` sequence.
  - `docs/03_Solution/modules/organization/` design docs (v1.1.0, GOVERNANCE ALIGNED) still
    describe a 3-table Organization design (`organization_type_master`,
    `organization_status_master`, `organization`) as the frozen physical schema.
  - `docs/03_Solution/database/DATABASE_DESIGN_STANDARDS.md` (`SOL-DB-001`, DRAFT — already
    tracked elsewhere in this section as having other stale/contradicted claims) references both
    tables as worked examples.
  - `docs/00_Project_Governance/STD/02_naming_conventions.md` and
    `03_master_data_catalog.md` (Governance Baseline, FROZEN) both reference both tables by name.
  Per this project's own convention that the Governance Baseline is frozen and not to be
  redesigned without an explicit governance decision, none of the above have been edited to
  match the new implementation, and the new implementation hasn't been rolled back to match
  them either. This is flagged here only — a human governance decision is needed on whether the
  frozen 3-table design should be amended to match the `master_data` implementation, or the
  implementation should be reverted to the frozen 3-table design. See also Key Workflow #4 and
  Open questions / TODOs.
- **`.env` loading tolerates a Windows BOM.** `api/config.py:17` calls
  `load_dotenv(_env_path, encoding="utf-8-sig")` rather than plain UTF-8 — some Windows editors
  save `api/.env` with a UTF-8 BOM, which previously caused `DB_NAME` (the first key) to be
  silently misread and `Settings.validate()` to report it missing. Mirrors the earlier
  `requirements.txt` UTF-16LE fix noted in Setup & running above — a recurring Windows-encoding
  class of bug in this repo.
- **pytest is now configured — no longer "no tests."** `pytest.ini` (repo root) + `tests/`
  package: `test_bootstrap.py` (21 tests, 5 classes), `test_foundation.py` (59 tests, 13
  classes), `test_organization.py` (64 tests, 7 classes), `test_person.py` (56 tests, 6
  classes), and `test_security.py` (8 tests, 3 classes) — **208 total**, all marked
  `integration`.
  `tests/conftest.py`'s `client` fixture wraps
  `fastapi.testclient.TestClient` against a **real** local Postgres DB — nothing is mocked, so
  a bootstrapped database + `api/.env` are prerequisites for running them. `pytest` and `httpx`
  (required by `TestClient` at import time) are pinned in `requirements.txt`. No lint/format
  tooling is configured yet.
- **Git remotes.** `git remote -v` shows two remotes: `personal`
  (`github.com/sandeeppanda22/NSS_ERP`, daily dev) and `org`
  (`github.com/NilachalaSaraswataSangha/NSS_ERP`, the production/deploy target).
  `docs/03_Solution/architecture/TECH_STACK_DECISIONS.md` §6 uses the `org` alias consistently
  in its Production remote and Flow rows.
- **Second "standards" location.** `docs/03_Solution/standards/lifecycle/` (`SOL-LIFE-001`/
  `PARTICIPATION_LIFECYCLE_RULES.md`, `SOL-LIFE-002`/`PERSON_LIFECYCLE_RULES.md`) is a distinct
  path from the pre-existing governance-layer `docs/00_Project_Governance/STD/` — both are
  legitimately different layers (SOLUTION vs. GOV per the lifecycle described in `CLAUDE.md`).
  It has its own `README.md` explaining the two documents and their relationship, but neither
  `STD/README.md` nor any top-level doc cross-references the other standards location, and the
  Sevak/Mahila/Kumari module business-rules docs don't yet cite `SOL-LIFE-001` even though its
  own text says they should reference it rather than duplicate its rules.
- **`docs/03_Solution/modules/foundation/` describes more tables than one might expect for
  "Foundation."** It covers 10 tables: the original 8 master data/geography/sequence tables
  plus `document_master` and `field_change_log`. The implemented `database/ddl/01_foundation/`
  has 12 tables, 2 more than this design doc describes (`postal_code`,
  `city_village_postal_code_map`) — implementation is ahead of the design doc for those two,
  see the Foundation Gotcha below.
- **`document_master` is Foundation-owned; RBAC table ownership is split between Authentication
  and Administration** (`CROSS_MODULE_PRINCIPLES.md`, `ARCH-CROSS-001`, FROZEN). `DOC-ARCH-001`
  establishes Foundation as the sole owner of a common `document_master` document registry
  (Person, Heritage, and Publications are consumers via FK, not owners) and a Foundation-owned
  `field_change_log` table for business-significant field-level change tracking, distinct from
  each module's own `_history` tables. Separately, a Table Ownership Declaration makes
  `user_account`/`password_history` exclusively Authentication-owned and the 5 RBAC tables
  (`role_master`, `permission_master`, `role_permission`, `user_role`, `admin_scope`)
  exclusively Administration-owned — both modules may FK to the other's tables but neither
  co-owns them. `role_master`/`permission_master`/`role_permission` are additionally sequenced
  as "Phase 0 Bootstrap RBAC" (`SOL-BOOT-001`, `BOOTSTRAP_ARCHITECTURE.md`/`SOL-ARCH-011`) —
  created before Foundation for DDL-ordering reasons; ownership doesn't change. This document
  also carries 3 explicitly **PENDING — DDL phase** design notes
  (not covered by its own FROZEN status): `ORG-PENDING-001` (organization short code, 3–5
  letters), `MEM-PENDING-001` (local Sakha number format, plus a proposed three-level Sangha
  Sevi → Sakha Affiliation → Local Number identity chain — the current
  `membership_transfer_history.old_local_sakha_number`/`new_local_sakha_number` VARCHAR fields
  are documented as insufficient for it), and `ATT-PENDING-001` (Visitor vs. Approved Darshak
  threshold — classified as an ERP operational refinement, not source-derived; no counter
  column planned, the threshold is meant to be derivable from existing attendance records).
- **Administration owns a Correspondence Register** (`CORR-DECISION-003`, `CORR-ARCH-001`/
  `002`, all FROZEN) — a generic inward/outward official-communication register
  (`correspondence`, `correspondence_document`, `correspondence_finance_reference`). Explicitly
  not a generic application/workflow engine and not an owner of the underlying business matter
  (membership renewals, property matters, governance decisions stay with their respective
  modules) or of financial transactions (Finance remains sole owner per `FIN-ARCH-001`; the
  Finance link is a reference-only M:N junction). One rule (`CORR-BR-018`, the
  `relationship_type` candidate values) is explicitly PENDING until Finance's own transaction
  taxonomy is frozen.
- **Mahila Parichalana Mandali term length disagrees across two frozen module docs.**
  `docs/03_Solution/modules/governance/04_governance_business_rules.md` (GOV-BR-036, "Mahila
  Term | FROZEN") sets the Mandali's term at **3 years**;
  `docs/03_Solution/modules/mahila/04_mahila_business_rules.md` (MAH-040, "Two-Year Term")
  freezes it at **2 years**. Both are marked FROZEN in their own module. Flagged here, not
  resolved, since picking a winner is a design decision this pass shouldn't make unilaterally.
- **`DATABASE_DESIGN_STANDARDS.md` states a business-identifier convention that contradicts the
  project's own frozen convention.** §6/§15/§21 of `docs/03_Solution/database/
  DATABASE_DESIGN_STANDARDS.md` (`SOL-DB-001`) define `_id` as the suffix for "sequential
  business identifiers" (`person_id`, `organization_id`, `sangha_sevi_id`), reserving `_code`
  for "stable classification codes" only. This directly contradicts the actual implemented SQL
  (`database/ddl/03_person/02_person.sql` uses `person_code`, not `person_id`) and the
  correction already recorded in `CLAUDE.md`. This document's own source-inventory list of
  module table-design docs suggests it absorbed the newer module docs' inconsistent `_id` usage
  (the same `person_id`/`person_code` conflict tracked for the Person module) rather than the
  actual frozen DDL convention — worth a human decision on which document is wrong before any
  new DDL is authored against `SOL-DB-001`'s stated convention. Separately, `SOL-DB-001` §31
  ("Schema Naming") also states "All tables reside in the `public` schema... No schema-per-module
  decision has been frozen" — stale since commit `764b643` namespaced every table under a
  dedicated `nss` schema (see "Database schema" above); this document needs both corrections.
- **Governance layer has an unresolved `GOV-ORG-00X` rule-ID collision, producing ambiguous
  citations.** `docs/00_Project_Governance/GOV/GOV-001_Project_Governance_Principles.md` §4 and
  `GOV-002_Organizational_Governance_Standard.md` §5 each independently define their own
  `GOV-ORG-001`–`004` (GOV-001: Statutory Authority / Governance Hierarchy / Rule Authority /
  Separation of Governance and Implementation; GOV-002: Apex Organizational Governance Principle
  / Statutory Authority Precedence / Organizational Hierarchy Integrity / Authoritative Document
  Recognition — plus GOV-001 has a 5th, `GOV-ORG-005` Traceability Principle, that GOV-002 has no
  counterpart for). `GDR-002_Creation_of_the_REF-MS_Authoritative_Reference_Family.md` (lines
  38-39) cites `GOV-ORG-001/002` and `GOV-ORG-004` meaning GOV-002's rules, while
  `GDR-004_Governance_Authority_Structure_Clarification.md` (line 55) cites `GOV-ORG-004` meaning
  GOV-001's "Separation of Governance and Implementation" — the same ID pointing at two different
  normative rules depending on which GDR you're reading. Not fixed here — renumbering either
  document's rule IDs is a governance content decision, not a drift correction; flagging only.
- **`STD/05_security_standards.md` §9's RBAC table vocabulary has drifted from both its own
  sibling standard and the implemented schema.** It lists RBAC core tables as `user_account`,
  `role`, `permission`, `role_permission`, `user_role` — but `STD/02_naming_conventions.md` §8
  mandates an `entity_master` suffix for master/lookup tables (its own sibling document's
  convention), and the actual DDL (`database/ddl/00_bootstrap/`) plus the newer
  `docs/03_Solution/security/SECURITY_ARCHITECTURE.md` §4.3 both correctly use `role_master`,
  `permission_master`, `role_permission`, `user_role`, `admin_scope`. Not fixed here — `STD/`
  is part of the frozen Governance Baseline; flagging for a human correction pass.
- **Six lifecycle documents restate Person-death-cascade rules instead of citing the existing
  lifecycle standards.** `person/03_person_lifecycle.md` (SOL-PER-005),
  `family/03_family_lifecycle.md` (SOL-FAM-005), `governance/03_governance_lifecycle.md`
  (SOL-GOV-005), `attendance/03_attendance_lifecycle.md` (SOL-ATT-006),
  `authentication/03_authentication_security_lifecycle.md` (SOL-AUTH-005), and
  `administration/03_administration_lifecycle.md` (SOL-ADMIN-005) each independently restate
  near-identical death-effect language, but none cites
  `docs/03_Solution/standards/lifecycle/PERSON_LIFECYCLE_RULES.md` (SOL-LIFE-002) or
  `PARTICIPATION_LIFECYCLE_RULES.md` (SOL-LIFE-001) as authority, even though SOL-LIFE-001 §16
  explicitly says modules "shall reference this standard rather than duplicating these rules."
  Content doesn't contradict SOL-LIFE-002 for the modules already in its consequence table
  (governance/family/attendance match it); Authentication and Administration aren't in that
  table at all, so their "not automatically deactivated" stance is a genuine gap in
  SOL-LIFE-002 rather than a contradiction. Not fixed here — editing six lifecycle docs' rule
  text is a content decision, not a drift correction.
- **Governance's and Mahila's lifecycle docs disagree on more than just term length.** Beyond
  the already-tracked 3-year vs. 2-year Mandali term conflict,
  `governance/03_governance_lifecycle.md` §33 models Mahila reconstitution as a formal
  consensus-attempt → election → `election`/`election_result`-table process, while
  `mahila/03_mahila_lifecycle.md` §24–26 describes routine reconstitution as Parichalak
  consensus + President's consent with no formal election tables at all, reserving actual
  elections for President/Vice-President vacancies only. Neither lifecycle doc reconciles this
  against the other.
- **`programmes_events/` (Module #21) is not source-aligned like its siblings, but its
  cross-module reconciliation is complete.** Unlike every other module (tagged `v1.0.0 DRAFT —
  SOURCE ALIGNED`), `programmes_events/` is v0.1.0, explicitly "FORMAL MODULE FREEZE PENDING,"
  and none of its candidate tables are frozen DDL. Its candidate-table set (`programme_type`,
  `event`, `event_day`, `event_session`, `event_registration`, `event_location`,
  `event_history`) is settled — `PROGRAMMES_EVENTS_RECONCILIATION_DECISIONS.md` (`SOL-EVT-007`)
  closed all 7 gates the cross-module review had left open, including the "Ownership Ambiguity"
  risk (resolved: UPBS/Kishor/Sevak's own event entities become common-Event extensions, not
  left standalone or merely referenced) and confirming Weekly Sangha Puja stays
  Attendance-owned with no P&E dependency. Reconciliation being complete is not the same as the
  module being frozen — don't cite any table name as settled yet.
- **Mobile strategy is Flutter, not PWA.** `TECH_STACK_DECISIONS.md` §4 (`TECH-MOB-001`,
  FROZEN) targets Android + iOS from day one (Hive/Drift for offline storage, FCM for push) —
  supersedes an earlier PWA-first/Capacitor position. If any older doc or memory still says
  "PWA" for the mobile client specifically, treat it as superseded — the web app's own
  IndexedDB/Service-Worker offline support for browser-based on-site registration is unaffected
  and remains a parallel path.
- **`assets_property/` (Module #22) is the physical/administrative record of NSS property and
  assets** — `Property`/`Asset` as primary entities plus `Custodianship`/`Statutory Record`/
  `Maintenance Record`, 7 tables, 74 business rules. Tagged `v1.0.0 DRAFT — SOURCE ALIGNED`
  like most other modules (unlike Programmes & Events). Explicitly does not own financial
  transactions/depreciation (Finance), acquisition/disposal approval (Governance), or
  historical/cultural significance (Heritage) — those modules may reference the same physical
  entity without duplicating records. One rule (`AP-066`, whether "sacred articles" fall under
  this module or Heritage's model) is explicitly PENDING.
- **Two pre-DDL architecture "gates" sit on top of the 12-tier build order**
  (`SOL-ARCH-009`/`010`). `FK_DEPENDENCY_GRAPH.md` topologically sorts all 86 frozen tables into
  8 dependency depths (zero cycles) and resolves the audit-actor circular-dependency problem
  (`sangha_sevi` needed for audit columns everywhere, but itself depends on Foundation) via a
  two-pass DDL strategy: create tables without audit-actor FKs first, add those constraints in
  a second pass. `DDL_CREATION_ORDER.md` turns that into the exact numbered `CREATE TABLE`
  sequence. Tiers 1-2 (Foundation, Organization) have been executed against `database/ddl/`;
  Tiers 3-12 have not. `BOOTSTRAP_ARCHITECTURE.md` (`SOL-ARCH-011`) adds a "Phase 0" ahead of
  Tier 1 for the 3 RBAC tables — DDL is implemented and committed. The 7 Programmes
  & Events candidate tables are explicitly listed in both
  but marked NOT EXECUTABLE pending that module's own formal freeze.
- **Role catalogue discrepancy between the frozen design docs and the actual Bootstrap RBAC
  DDL/seed.** ~~RESOLVED~~ — `05_administration_table_design.md` §8.7 and `SOL-BOOT-001` §4.2
  now describe 8 roles / 5 scope levels, matching the DDL CHECK constraint and seed data.
  `NSS_ERP_PATHA_CHAKRA_ADMIN` / `PATHA_CHAKRA` added to the frozen catalogue.
- **`nss_db_backend` PostgreSQL role privileges.** ~~RESOLVED~~ — `database/scripts/04_grant_backend.sql`
  now grants `nss_db_backend` `USAGE` on schema `nss`, `SELECT` on all existing tables, and
  (via `ALTER DEFAULT PRIVILEGES`) `SELECT` on future tables — read-only, matching the FastAPI
  Tier 0 API's own read-only usage. `BOOTSTRAP_ARCHITECTURE.md` (`SOL-ARCH-011`) still only
  formalizes the `nss_db_owner`/`NSS_ERP_ADMIN` distinction and doesn't mention this role by
  name, but the privileges themselves are now defined and implemented.
- **`code_explanations/` was reorganized from per-tier to per-layer, then moved out of
  `architecture/` entirely.** The original
  `TIER0_VERTICAL_SLICE.md`/`TIER1_FOUNDATION.md`/`SECURITY_HARDENING.md` (which interleaved
  narration of the same files across multiple tier-scoped documents) were retired and replaced
  by `API_CODE_EXPLANATIONS.md`, `DATABASE_CODE_EXPLANATIONS.md`, `UI_CODE_EXPLANATIONS.md`,
  `SECURITY_CODE_EXPLANATIONS.md`, and `TESTING_CODE_EXPLANATIONS.md` — one document per layer,
  each giving every source file in that layer its own "Requirement + Line-by-line" section
  regardless of which tier introduced it. `TIER0_SECURITY_AUDIT.md`/`TIER1_SECURITY_AUDIT.md`/
  `TIER2_SECURITY_AUDIT.md` (audit findings, not code narration) were not part of this
  per-layer reorganization and still exist under their original names. Separately, as part of
  the Tier 2 Organization slice, the whole `code_explanations/` folder was relocated one level
  up — `docs/03_Solution/architecture/code_explanations/` → `docs/03_Solution/code_explanations/`
  — and the API contract docs were pulled out of `architecture/` into a new consolidated
  `docs/03_Solution/api/` folder (`BOOTSTRAP_API_CONTRACT.md`, `FOUNDATION_API_CONTRACT.md`,
  `ORGANIZATION_API_CONTRACT.md`), so `architecture/` no longer holds either — see the
  `docs/03_Solution/` detail above for both folders' current contents. Any reference elsewhere
  (including in older commits/docs) to `docs/03_Solution/architecture/code_explanations/` or
  `docs/03_Solution/architecture/FOUNDATION_API_CONTRACT.md` is stale.
- **Filename collision in `docs/03_Solution/modules/administration/`.**
  `06_bootstrap_rbac_table_design.md` (`SOL-BOOT-001`) and `06_correspondence_register_erd.md`
  (`SOL-ADMIN-006`) share the same leading number — not renamed here, flagging only.

## Open questions / TODOs

- **`tests/test_security.py`'s docstring claims `DISABLE_DOCS` is verified, but no test actually
  exercises it** — none of the 8 tests hits `/docs`, `/redoc`, or `/openapi.json`. Either add a
  test or trim the docstring.
- **CORS tests only exercise the unconfigured (default-empty `CORS_ORIGINS`) path** —
  `TestCORS`'s two tests assert `Access-Control-Allow-Origin` is *absent* when no origins are
  configured; there's no test setting `CORS_ORIGINS` and asserting the header *is* present for
  an allowed origin, or absent for a non-allowed one.
- **Both Security Posture Summary ASCII tables** (`TIER0_SECURITY_AUDIT.md`,
  `TIER1_SECURITY_AUDIT.md`) still list only the original 9-10 checks — neither was updated to
  add rows for the new CORS/rate-limiting/security-header protections added in
  `SECURITY_CODE_EXPLANATIONS.md`, even though the advisory tables above them were updated.
  Cosmetic, not a correctness issue.
- **Merge/release Tier 3 `Person` endpoints** — implemented (`api/routers/person.py`, 4
  endpoints, `frontend/person.html`, 56 tests) but still on `feature/tier3-person-module`, not
  yet merged to `develop`/`main` or tagged — see Key Workflow #5/"Current position" above.
- **Decide the Organization type-to-type parent matrix** (which org types may parent which —
  e.g. does ANCHALIKA/ZILLA sit under KENDRA, does PATHA_CHAKRA sit under SAKHA or KENDRA) —
  the v1.1.0 GOVERNANCE ALIGNED business rules doc explicitly left this open rather than
  freezing it; do not treat any specific matrix as decided until this is resolved.
- **Reconcile Person's frozen design docs against the Foundation-`master_data` pattern actually
  implemented** — `docs/03_Solution/modules/person/` describes dedicated per-domain master
  tables for gender/marital_status/address_type, but the implemented DDL resolves these through
  Foundation's `master_data` instead (the same pattern already applied to Organization). This is
  the Person-side counterpart of the still-open Organization `master_data` migration Gotcha
  above — needs the same governance decision (update the frozen design docs, or treat the
  `master_data` migration as itself the frozen decision going forward).
- **Implement the `id_sequence_master` increment/formatting logic** (no function, trigger, or
  API code currently does this — see Key Workflow #3).
- **Implement the Founder & Heritage schema** — the v1.0.0 design
  (`docs/03_Solution/modules/heritage/`) specifies 8 tables; zero implementation exists (neither
  SQL DDL nor an API) for any of them.
- **Build API endpoints for `family`, `membership`, and `heritage`** — SQL DDL exists for none
  of these yet either; nothing is reachable over HTTP.
- **Decide the scope of `governance` and `attendance`** — Solution-layer designs exist for both,
  but no DDL or API implementation exists yet for either.
- **Build out the FastAPI application beyond Tier 0/1/2/3** — per `TECH_STACK_DECISIONS.md`,
  FastAPI is the approved API layer; Tier 0's 4 read-only bootstrap-RBAC endpoints, Tier 1's
  17 read-only Foundation endpoints, and Tier 2's 6 read-only Organization endpoints are all
  implemented and released (v0.7.0, v0.8.0); Tier 3's 4 read-only Person endpoints are
  implemented but not yet released (see "Current position" above) — every other tier's API phase
  (Family, Membership, Heritage, etc.) remains unbuilt.
- **Grow the frontend beyond Tier 0/1/2/3** — `frontend/` now has four verification UIs
  (Tailwind + DaisyUI + Alpine.js, no build step): the Tier 0 Bootstrap Verification UI, the
  Tier 1 Foundation Verification UI, the Tier 2 Organization Verification UI, and the Tier 3
  Person Verification UI. None is the full admin dashboard; the 13 mockups under
  `docs/03_Solution/ui/mockups/` remain the visual target for later tiers, and login/session UI
  is deferred to Tier 5.
- **No `.env.example`** — new contributors have to reverse-engineer required env vars from
  `api/config.py`; consider adding one.
- **`docs/02_Requirements/` and `docs/04_Testing/` are empty scaffolding** — folder structure
  exists (per `AUTH-001`/`GOV-003` repository architecture) but no actual requirements or test
  documentation has been written yet.
- **`ORG-PENDING-001` (organization short code) is frozen in `CROSS_MODULE_PRINCIPLES.md` but
  never propagated into the Organization module's own doc set.** None of
  `docs/03_Solution/modules/organization/{01_organization_module_overview,02_organization_erd,
  04_organization_business_rules,05_organization_table_design}.md` or that module's own
  `README.md` mention `organization_short_code`, `ORG-PENDING-001`, or `VARCHAR(5)` anywhere —
  the frozen column exists only in the cross-module architecture doc, not in the module that
  will actually own the column. Flagged, not fixed, since adding the column to the module's own
  design docs is itself a design-doc edit, not a drift correction.
- **Three DDL-phase design notes (`CROSS_MODULE_PRINCIPLES.md` §20-21):** `ORG-PENDING-001`
  (organization short code format, 3–5 letters) — FROZEN. `MEM-PENDING-001` (local Sakha number
  format + a proposed three-level Sangha Sevi → Sakha Affiliation → Local Number identity chain
  — likely needs a dedicated entity rather than the current inline VARCHAR fields) — PENDING.
  `ATT-PENDING-001` (Visitor vs. Approved Darshak threshold, classified ERP-operational not
  source-derived) — PENDING, non-blocking. `CORR-EXT-001` (organization-scoped correspondence
  reference numbering) — FROZEN, unblocked by the `ORG-PENDING-001` freeze. Correspondence
  format is `<ORG_SHORT_CODE>/IN/YYYY-YY/NNN` (per-organization sequences).
- **Reconcile the implemented `organization_code` column with the frozen `ORG-PENDING-001`
  spec.** `database/ddl/02_organization/03_organization.sql` defines `organization_code
  VARCHAR(10) NULL`; `ORG-PENDING-001` (`CROSS_MODULE_PRINCIPLES.md` §20.1) froze
  `organization_short_code VARCHAR(5) NOT NULL`. Different column name, different width,
  different nullability — needs an explicit decision on whether the DDL should be altered to
  match the frozen spec, or the spec updated to match what was actually built. See Key Workflow
  #4/Gotchas.
- **Reconcile seeded organization-type codes with the design docs' short forms.**
  `database/seed/01_foundation/02_master_data.sql` (formerly `database/seed/02_organization/
  01_organization_type_master.sql`, retired by the `master_data` migration) seeds
  `ANCHALIKA_SANGHA`/`ZILLA_SANGHA`/`SAKHA_SANGHA`; the Organization module's own business rules
  doc uses the short forms `ANCHALIKA`/`ZILLA`/`SAKHA` (`SAKHA_ASANA`/`PATHA_CHAKRA` already
  match). Needs a decision on which form is authoritative before this seed data or the design
  docs are extended further.
- **Seeded organization status includes `SUSPENDED`, contradicting the frozen business rule
  that excludes it.** `database/seed/01_foundation/02_master_data.sql` (formerly
  `database/seed/02_organization/02_organization_status_master.sql`, retired by the
  `master_data` migration) seeds `SUSPENDED` as one of the unified `STATUS` category's 13
  values, but `03_organization_lifecycle.md` §81 ("No Unsupported
  States") and `04_organization_business_rules.md` ORG-BR-059 ("No Unsupported Status") both
  explicitly list `SUSPENDED` as an example of a status the design does **not** introduce
  without an approved governance change. Needs a decision on whether the seed data should drop
  `SUSPENDED` or the business rule/lifecycle docs should be updated to approve it.
- **Resolve whether the two top-level `database/ddl/README.md`/`database/seed/README.md`
  files should keep existing at all.** `database/README.md`'s own execution-order section
  already covers everything they cover, via the per-module READMEs — they may be redundant
  duplication that will drift again next time a module lands. Not resolved here since deleting
  them is a structural decision, not a drift correction.
- **Reconcile `04_foundation_table_design.md`/the Foundation ERD with the implemented
  `postal_code`/`city_village_postal_code_map` tables** — these 2 tables exist in
  `database/ddl/01_foundation/` but aren't described in the Foundation module's own design docs
  (which describe 10 tables, not the 12 implemented).
- **One Correspondence Register rule is PENDING** — `CORR-BR-018`'s `relationship_type`
  candidate values for `correspondence_finance_reference` are deferred until Finance's own
  transaction taxonomy is frozen.
- **One Assets & Property rule is PENDING** — `AP-066`, whether "sacred articles" fall under
  this module's Asset-custody model or Heritage's cultural-significance model, is unresolved.
- **Formal Module #21 (Programmes & Events) freeze is the one remaining step for that module** —
  its cross-module reconciliation is complete and its candidate table set is settled at 7, but
  the module overview doc and its own README were never bumped past v0.1.0/DRAFT, and none of
  its 7 tables are frozen DDL. Reconciliation-complete is not the same as module-frozen.
- **Resolve the Mahila Parichalana Mandali term-length conflict** —
  `governance/04_governance_business_rules.md` freezes 3 years,
  `mahila/04_mahila_business_rules.md` freezes 2 years; their lifecycle docs also disagree on
  the reconstitution process itself (formal election tables vs. consensus-only). Needs an
  explicit decision on which module doc is authoritative (or a joint correction to both) before
  either is implemented — see Gotchas.
- **Add `SOL-LIFE-001`/`SOL-LIFE-002` cross-references to the six lifecycle docs** that
  currently restate death-cascade rules instead of citing them (`person`, `family`,
  `governance`, `attendance`, `authentication`, `administration`) — a future pass could add
  cross-reference notes without changing any rule content.
- **Decide which document is authoritative for the business-identifier suffix** —
  `docs/03_Solution/database/DATABASE_DESIGN_STANDARDS.md` (`_id`) or the implemented SQL DDL +
  `CLAUDE.md` (`_code`). Needs an explicit correction to `SOL-DB-001` (or a project-wide
  convention change, which seems unlikely given how much existing SQL/documentation already
  uses `_code`).
- ~~**Reconcile the frozen role catalogue with the actual Bootstrap RBAC implementation**~~ —
  RESOLVED. §8.7 updated to 8 roles / 5 scope levels, adding `NSS_ERP_PATHA_CHAKRA_ADMIN`.
  Docs and seed now match.
- ~~**Define the `nss_db_backend` PostgreSQL role**~~ — RESOLVED by
  `database/scripts/04_grant_backend.sql` (read-only `SELECT` grants). See Gotchas.
- **Resolve the `06_bootstrap_rbac_table_design.md`/`06_correspondence_register_erd.md`
  filename collision** in `docs/03_Solution/modules/administration/` — both are numbered `06`.
  See Gotchas.
- **Decide how to reconcile the `organization_type_master`/`organization_status_master`
  retirement with the frozen docs that still describe them as separate physical tables** —
  `FK_DEPENDENCY_GRAPH.md`, `DDL_CREATION_ORDER.md`, the Organization module's own v1.1.0 design
  docs, `DATABASE_DESIGN_STANDARDS.md`, and `STD/02_naming_conventions.md`/
  `03_master_data_catalog.md` all still reference both tables; the implementation now uses
  Foundation's `master_data` instead. Needs an explicit governance decision on which side
  changes. See Gotchas.
- ~~**Fix `database/scripts/03_validate.sh`'s `id_sequence_master` duplicate check**~~ — **FIXED.**
  Changed from `entity_name` to `sequence_code`.
- **Reconcile `database/ddl/01_foundation/README.md`'s Design Decisions section with the actual
  `organization` table.** It states Organization stores `postal_code_pk` (FK to `postal_code`)
  plus `latitude`/`longitude` `NUMERIC(10,7)` — but the implemented `organization` table
  (`database/ddl/02_organization/03_organization.sql`) has only a plain-text `postal_code
  VARCHAR(20)` column and no `latitude`/`longitude` at all. That README section describes a
  future/aspirational design, not what's built.
