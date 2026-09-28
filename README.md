# NSS ERP

Nilachala Saraswata Sangha Enterprise Resource Planning (NSS ERP)

---

# Overview

NSS ERP is a comprehensive web-based management platform being developed for Nilachala Saraswata Sangha.

The system is designed to support membership management, family management, governance, attendance tracking, Kumari Sangha, Kishor Puja, Founder & Heritage records, UPBS operations, reporting, and future NSS operational activities.

The project follows a:

```text
Database First
    ↓
API First
    ↓
UI First
```

design philosophy, ensuring that business rules are frozen before implementation.

---

# Project Objectives

* Centralized NSS member management
* Family-first relationship tracking
* Governance and committee management
* Attendance and review workflows
* Kumari Sangha and Kishor Puja management
* Founder & Heritage preservation
* UPBS operational support
* Historical record preservation
* Audit-compliant data management
* Role-based access control
* International branch support

---

# Technology Stack

> **Note:** `docs/03_Solution/architecture/TECH_STACK_DECISIONS.md` is the Approved
> forward-looking decision record — it replaces Bootstrap 5 with Tailwind CSS +
> DaisyUI + Alpine.js, and adds a hosting/offline plan. The FastAPI half of that decision
> is now partially implemented (Tier 0 bootstrap endpoints); the stack below reflects the
> current codebase.

## Frontend

* Tailwind CSS + DaisyUI (pre-built via Tailwind CLI, no longer CDN — see `package.json`,
  `tailwind.config.js`, `frontend/assets/css/tailwind-input.css`/`tailwind.min.css`) + Alpine.js
  (CDN) — no frontend framework. Node.js is only needed to rebuild CSS after a class change
  (`npm install && npm run css:build`); the built CSS is committed, so a fresh clone runs
  without Node.js.
* `frontend/` now consists of exactly four pages: `login.html` (at `/login`, which `/` also
  302-redirects to), `register.html` (at `/register`), `dashboard.html` (at `/dashboard` — the
  role-aware member dashboard, see `docs/03_Solution/architecture/MEMBER_DASHBOARD.md`; tabs:
  Personal, Family, Membership, Attendance, Governance, Documents), and `admin.html` (at
  `/admin` — the administration console; tabs: Users, User Detail, Create User, Create
  Sangha-Sevi, Password, Create Organization, Organizations, Claims, Person Directory, Member
  Directory, Organization Hierarchy, Reference Data, Geography, System Settings), plus their
  `assets/js/*.js` files (`login.js`, `register.js`, `dashboard.js`, `admin.js`, `auth.js`, and
  the shared helpers `nss-config.js`/`nss-datepicker.js`/`nss-dialog.js`/`nss-location.js`/
  `nss-layout.js`). The Tier 0-4 standalone verification pages (`index.html`,
  `foundation.html`, `organization.html`, `person.html`, `family.html`, `membership.html`) and
  their per-page JS have been **deleted**; their functionality was folded into `admin.html`
  (Foundation → Reference Data / Geography, Organization → Organizations / Organization
  Hierarchy, Person → Person Directory, Membership → Member Directory) and `dashboard.html`
  (Family → Family tab, incl. the family-tree visualization and Sakha-alignment mismatch
  badges; Membership → Membership tab). **`claim-approval.html` does not exist** — the
  registration-claim review queue backed by `api/routers/claim_approval.py` is served by
  `admin.html`'s Claims tab instead. All pages are served as static files by FastAPI; see
  `frontend/README.md` for the full file/function reference. 13 static mockups for later tiers
  exist under `docs/03_Solution/ui/mockups/`.

---

## Backend

* FastAPI — the only web/API layer in the codebase (`api/`), currently a Tier 0 read-only
  bootstrap-RBAC API plus a Tier 1 Foundation API (23 endpoints across 11 tables — 17 reads
  plus 6 new write endpoints, in progress/uncommitted, gated by a `FOUNDATION_MANAGE`
  permission) plus
  a Tier 2 Organization API (7 endpoints) plus a Tier 3 Person API
  (4 endpoints across 2 tables) plus a Tier 4 Family API (16 endpoints across 6
  tables — 7 original read endpoints plus 9 newer Tier 5 authenticated write endpoints
  implemented directly in this router file, see below) and Membership API (7 endpoints); 61
  Tier 0-4 endpoints total; no ORM, raw `psycopg2`. **Partway through the same in-progress
  branch below, Foundation/Organization/Person/Membership's GET endpoints also
  gained `require_permission(...)` gating, and Family separately gained an ownership-based auth
  model on all 16 of its endpoints (a person reaches their own family through their
  `family_relationship`/`family_admin` row, with `FAMILY_VIEW`/`FAMILY_MANAGE` as the admin
  override) — only Tier 0's 4 `bootstrap.py` endpoints remain unauthenticated.** Plus, in
  progress/uncommitted on
  `feature/tier5-authentication-administration`:** a Tier 5 Authentication API
  (`api/routers/auth.py` — login/refresh/logout/change-password/forgot-password/reset-password/me/
  profile, 8 endpoints), Registration API (`api/routers/registration.py` — self-service
  `POST /api/v1/register` plus `GET /check-duplicate`), Claim Approval API (`api/routers/claim_approval.py` — 5 endpoints for
  Sakha-admin review of registration claims), Admin API (`api/routers/admin.py` — user/role/
  organization/Sangha-Sevi management, 23 endpoints), and a new Audit API
  (`api/routers/audit.py` — `GET /change-log` over `nss.field_change_log`, gated by `AUDIT_VIEW`)
  — none of these are released or merged to `develop`/
  `main` yet — **100 endpoints across 11 routers in total**. See `CLAUDE.md` and `docs/PROJECT_DOCUMENTATION.md` → Architecture ("Tier 5") for
  the current, code-verified detail.
  `docs/PROJECT_DOCUMENTATION.md` → Architecture,
  `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`, and `docs/03_Solution/api/API_CONTRACT.md`.
* Django — an earlier prototype existed under `backend/` but was fully archived and removed
  once the FastAPI direction was adopted; `backend/` is now empty.

---

## Database

* PostgreSQL

---

## Authentication

* **Tiers 0-4 were originally deliberately unauthenticated by design (read-only).** JWT-based
  authentication + RBAC is now implemented — Argon2 password hashing, access/refresh JWTs,
  `nss.user_account`/
  `password_history`/`registration_claim`/`password_reset_token` tables, and role/scope-based
  authorization for `/api/v1/admin/*` — but **in progress/uncommitted** on `feature/tier5-
  authentication-administration`, not yet merged or released. **Partway through that same
  branch, Foundation/Organization/Person/Membership's Tier 1-4 GET endpoints also gained
  `require_permission(...)` gating, and Family gained an ownership-based auth model on all 16
  of its endpoints instead** (only Tier 0's 4 `bootstrap.py` endpoints remain
  unauthenticated), and `nss.permission_master`/`role_permission` are now seeded, so these
  permission checks no longer blanket-403.

---

## Deployment

* Render.com — `render.yaml` (repo root) defines a free-tier web service (`uvicorn
  api.main:app`). It does not provision a database itself; `DB_NAME`/`DB_USER`/`DB_PASSWORD`/
  `DB_HOST`/`DB_PORT` are set manually in the Render dashboard, pointing at an external Neon.dev
  PostgreSQL instance. `render_build.sh` installs Python deps and runs the DB bootstrap (DDL +
  seed) on first deploy only, skipping it on subsequent deploys if `nss.role_master` already
  exists.

---

## Future Enhancements

* Redis Cache
* Background Workers
* Mobile Application
* API Integrations

---

# Project Architecture

```text
Browser / HTTP client
   │
   ▼
Security Middleware (CORS, rate limiting, security headers)
   │
   ▼
FastAPI (api/main.py, Tier 0 bootstrap + Tier 1 foundation + Tier 2 organization + Tier 3 person + Tier 4 family + membership routers)
   │
   ▼
psycopg2 connection pool (api/database.py) — raw SQL, no ORM
   │
   ▼
PostgreSQL (nss.* schema)
```

*(See `docs/03_Solution/code_explanations/` for full line-by-line walkthroughs of
every source file, organized by layer — `API_CODE_EXPLANATIONS.md`,
`DATABASE_CODE_EXPLANATIONS.md`, `UI_CODE_EXPLANATIONS.md`, `SECURITY_CODE_EXPLANATIONS.md`,
`TESTING_CODE_EXPLANATIONS.md`.)*

---

# Getting Started

See [`docs/03_Solution/architecture/GETTING_STARTED.md`](docs/03_Solution/architecture/GETTING_STARTED.md) for full setup instructions (database, API, tests) and database rebuild procedures.

---

# Core Principles

## Person ≠ Member

A Person may exist without being a Member.

Examples:

* Family Member
* Kumari Participant
* Kishor Participant
* Future Applicant
* Historical Person

A Member must always be a Person.

---

## Family First

Family relationships are maintained independently of membership status.

---

## History Never Deleted

Business records are preserved permanently.

Physical deletion is avoided.

Soft delete is preferred.

---

## Audit First

All critical business operations must be auditable.

---

## Master Data Driven

Business configuration is controlled through master tables rather than hardcoded values.

---

## Global Ready

The system is designed to support NSS activities within India and internationally.

---

# Organization Hierarchy

```text
KENDRA
├── ANCHALIKA_SANGHA
│   └── SAKHA_SANGHA / SAKHA_ASANA
│       ├── KUMARI_SANGHA
│       ├── SEVAK_SANGHA
│       └── MAHILA_SANGHA          (local, per-Sakha)
├── ZILLA_SANGHA
│   └── SAKHA_SANGHA / SAKHA_ASANA
│       ├── KUMARI_SANGHA
│       ├── SEVAK_SANGHA
│       └── MAHILA_SANGHA          (local, per-Sakha)
├── PATHA_CHAKRA
├── PARIBARIK_SANGHA                ("Gruhasana" — see notes)
└── MAHILA_SANGHA                   (Kendra / Central — exactly one)

NILACHALA_KUTIRA   — unique, no parent, no children; peer of KENDRA, not under it
SMRUTI_MANDIRA     — unique, no parent, no children; peer of KENDRA, not under it
```

Notes:

* `ANCHALIKA_SANGHA` and `ZILLA_SANGHA` are siblings directly under `KENDRA` — never nested
  under each other.
* `SAKHA_SANGHA`/`SAKHA_ASANA` sit only under `ANCHALIKA_SANGHA` or `ZILLA_SANGHA`.
* `KUMARI_SANGHA`/`SEVAK_SANGHA` sit only under `SAKHA_SANGHA`.
* `MAHILA_SANGHA` is **one type, two tiers, distinguished by parent** — `parent = KENDRA`
  identifies the single Kendra/Central Mahila Sangha; `parent = SAKHA_SANGHA` identifies a
  local, per-Sakha Mahila Sangha. The Bye-Law's central-supervises-branches relationship is a
  governance relationship, deliberately *not* encoded as a parent-child org edge.
* `PARIBARIK_SANGHA` ("Paribarik Sangha", family organisation attached to Kendra — Bye-Law
  Preamble) sits directly under `KENDRA`. It is org-level, not tied to an individual person.
* `PARIBARIK_ASANA` ("Gruhasana") is conceptually attached to a `sangha_sevi` (a person's
  membership record), not to another organization — that `sangha_sevi` belongs to exactly one
  `SAKHA_SANGHA`. Since `nss.organization` has no direct link to `sangha_sevi` today, its
  `parent_organization_pk` is set to that person's current Sakha Sangha as an implementation
  proxy, not a literal org-tree claim.
* `PATHA_CHAKRA` may operate within India or internationally.
* Admin scope levels (`nss.admin_scope`/`nss.role_master.scope_level`) cover `NSS-WIDE`,
  `KENDRA`, `ANCHALIKA`, `ZILLA`, `SAKHA`, `PATHA_CHAKRA`, and `KENDRA_MAHILA_SANGHA` only — no
  role is scoped to `SAKHA_ASANA`, `KUMARI_SANGHA`, `SEVAK_SANGHA`, `PARIBARIK_SANGHA`, or
  `PARIBARIK_ASANA`.

> **Frozen (2026-09-25):** the type-to-type parent compatibility matrix above is now frozen —
> see `docs/03_Solution/modules/organization/04_organization_business_rules.md` §28
> (ORG-BR-087–095), an explicit governance decision. This supersedes the prior "open item"
> framing (the matrix used to be left undecided; only the generic apex + self-referencing
> structure was frozen).

> **Frozen separately:** a **13-type inventory** (`docs/03_Solution/modules/organization/
> 04_organization_business_rules.md` ORG-BR-064 lists the earlier 8; the remaining 5 —
> `PARIBARIK_SANGHA`, `PATHA_CHAKRA`, `KUMARI_SANGHA`, `SEVAK_SANGHA`, `MAHILA_SANGHA` — are
> seeded in `database/seed/01_foundation/02_master_data.sql` under `ORGANIZATION_TYPE`).

> **Open:** the frozen 3-table structure is no longer what's implemented in SQL — the former
> `organization_type_master`/`organization_status_master` tables were retired in favor of rows
> in Foundation's generic `master_data` (see `docs/PROJECT_DOCUMENTATION.md` → Gotchas for the
> full reconciliation status).

---

# Module Structure

*The sections below describe the full planned module roadmap. Foundation, Organization,
Person, Family, and Membership are the only modules on this list with API/backend implementation
so far — a Tier 0 FastAPI bootstrap-RBAC API, a Tier 1 Foundation API, a Tier 2 Organization
API, a Tier 3 Person API, and a Tier 4 Family + Membership API (see Current Development Status
below for full endpoint/table counts), plus SQL DDL for Bootstrap RBAC, Foundation,
Organization, Person, Family, and Membership. An earlier Django prototype briefly
implemented parts of Foundation, Membership, Family, Governance (stub), Attendance (stub), and
Founder & Heritage under `backend/`, but it was fully archived and removed once the FastAPI
direction was adopted. Solution-layer design documentation (overview/ERD/lifecycle/business-
rules/table-design) is complete for essentially every module on this roadmap — ahead of, and not
yet reconciled with, any code implementation for the modules beyond Foundation/Organization/
Person.
**Programmes & Events is the one exception**: still DRAFT, explicitly not frozen, though its
cross-module reconciliation gates are closed and its candidate table set has settled.
See `docs/PROJECT_DOCUMENTATION.md` for the current, code-verified status of each.*

## Foundation

* Organization Management
* Person Management
* Master Data
* Authentication & RBAC
* Audit & History
* Global Location Management

---

## Membership

* Member Registration
* Membership Types
* Membership Approval
* Renewal
* Transfer
* Membership Journey
* Sangha Sevi ID Management

---

## Family

* Family Dashboard
* Family Tree
* Relationship Management

---

## Governance

* General Body
* Governing Body
* Advisory Board
* Committees
* Position Assignment

---

## Attendance

* Weekly Attendance
* Attendance Review
* Attendance Reports

---

## Mahila Sangha

* Membership
* Activities
* Governance

---

## Kumari Sangha

* KM Identity
* Activities
* Training
* Membership Transition

---

## Kishor Puja

* KH Identity
* Registration
* Guardian Assignment

---

## Sevak Sangha

* Volunteer Development
* Training
* Activities

---

## Founder & Heritage

* Biography
* Philosophy
* Teachings
* Publications

---

## UPBS

* Registration
* Accommodation
* Committee Management
* Reports

---

## Reports & Analytics

* Membership Reports
* Attendance Reports
* Governance Reports
* UPBS Reports

---

## Administration

* Users
* Roles
* Permissions
* System Settings

---

# Database Design Principles

## Person Module

```text
Person ≠ Member
```

A Person may exist without Membership.

A Member must always be linked to a Person.

---

## Contact Information

Supports:

* International Phone Numbers
* Country Phone Codes
* Email Addresses

Rules:

* Mobile Number + Country Phone Code must be unique.
* Email is not required to be unique.
* At least one contact method is mandatory.

---

## Address Management

Supports:

* Multiple Addresses
* Primary Address Selection
* Global Locations
* Postal Code Mapping

Rules:

* One Person may have multiple addresses.
* Only one address may be Primary.
* Primary Address may be changed at any time.

---

## Location Hierarchy

```text
Country
    ↓
State / Province
    ↓
District / Region
    ↓
City / Village
```

Postal Codes are maintained separately and linked through mapping tables.

---

# Development Workflow

## Branch Strategy

```text
main
 └── develop
      └── feature/*
```

---

## Feature Development Workflow

```text
Create Feature Branch
        ↓
Implement Changes
        ↓
Commit Changes
        ↓
Merge into develop
        ↓
Create Release Notes
        ↓
Create Git Tag
        ↓
Merge develop into main
        ↓
Create GitHub Release
```

---

# Release Management

Every version must include:

* Git Tag
* Release Notes Document
* GitHub Release

Release Notes Location:

```text
docs/05_Releases/
```

Examples:

```text
v0.1.0.md
v0.2.0.md
v0.2.1.md
v0.3.0.md
v0.4.0.md
v0.5.0.md
v0.5.1.md
v0.6.0.md
v0.7.0.md
v0.8.0.md
v0.9.0.md
v0.10.0.md
v0.10.4.md
```

---

# Completed Milestones

## v0.1.0

Initial Project Setup

---

## v0.2.0

Foundation Models

---

## v0.2.1

Admin Setup

---

## v0.3.0

UI Foundation and Authentication Complete

---

## v0.4.0

Organization Module Design Complete *(design/ERD/business-rules/table-design docs only — see
v0.5.1+ and Current Development Status below for the later SQL implementation)*

---

## v0.5.0

Person Module Design Complete

---

## v0.5.1

Person Database Schema Complete

* Global Location Model
* Person Schema
* Person Address Schema
* International Mobile Support
* Address Mapping Model

---

## v0.6.0

Full-Stack Tier 0 — Documentation, Database, API, UI, and Deployment

* 22-module solution documentation complete (overview, ERD, lifecycle, business rules, table design)
* 5 architecture documents frozen (SOL-ARCH-007 through SOL-ARCH-011)
* 18-table database implementation (Bootstrap RBAC + Foundation + Organization vertical slices)
* FastAPI Tier 0 bootstrap API (4 read-only endpoints)
* Bootstrap Verification UI (responsive 3-column layout, Tailwind + DaisyUI + Alpine.js)
* Render.com + Neon.dev deployment configuration
* Project governance standards and authoritative reference corpus
* NSS-WIDE scope for SYSTEM roles
* Terminology corrections (Kishor, Bye-Law, statutory)

---

## v0.7.0

Tier 1 Foundation — API, Web UI, Security Hardening

* FastAPI Tier 1 Foundation API (17 read-only endpoints across 11 tables)
* Tier 1 Foundation Verification UI (4-tab layout: Master Data, System Config, Geographic
  drill-down, Runtime Tables)
* Cross-tier security-hardening middleware (security headers, opt-in CORS, rate limiting via
  `slowapi`) + CDN Subresource Integrity pinning (DaisyUI, Alpine.js)
* Test suite grown from 9 to 64 tests (Tier 0 + Tier 1 Foundation + security middleware)
* `pytest`/`httpx` pinned in `requirements.txt`; both security audit reports updated to v1.1
* Code-explanation docs reorganized from 3 per-tier files to 5 per-layer files
  (API/Database/UI/Security/Testing)

---

## v0.8.0

Tier 2 Organization — API, Web UI

* FastAPI Tier 2 Organization API (6 read-only endpoints, incl. a self-referencing hierarchy
  tree via a `WITH RECURSIVE` CTE)
* Organization contact and online-presence fields (8 new columns on `nss.organization`)
* Tier 2 Organization Verification UI (3-tab layout: Reference Data, Organizations, Hierarchy)
* Test suite grown from 64 to 139 tests (Tier 0 + Tier 1 + Tier 2 + security middleware)
* `TIER2_SECURITY_AUDIT.md` added — no blocking findings
* `code_explanations/` and API contracts (`docs/03_Solution/api/`) moved out of `architecture/`

---

## v0.9.0

Organization Master-Data Migration + Tier 3 Person — API, Web UI

* Organization master-data migration: `organization_type_master`/`organization_status_master`
  retired in favor of Foundation's `master_category`/`master_data` (10 org types, unified
  13-value `STATUS` category)
* FastAPI Tier 3 Person API (4 read-only endpoints, incl. `pg_trgm` fuzzy search)
* Person DDL rewrite onto the Foundation `master_data` pattern (`person`, `person_address`)
* Shared `api/helpers.py` (cursor→Pydantic + pagination), adopted by Organization too, plus
  `limit`/`offset` pagination on Organization's list/hierarchy endpoints
* Tier 3 Person Verification UI (2-tab layout: Persons, Search)
* Test suite grown from 139 to 208 tests (Tier 0 + Tier 1 + Tier 2 + Tier 3 + security)
* `TIER3_SECURITY_AUDIT.md` added — no blocking findings, Aadhaar defence-in-depth confirmed

---

# Current Development Status

Completed:

* Foundation Architecture
* Authentication Foundation
* Organization Module Design (v1.1.0, GOVERNANCE ALIGNED; type-to-type parent hierarchy left as
  an open item, not frozen)
* Person Module Design (v2.0.0, FROZEN — 2 tables: `person`, `person_address`; `document_master`
  is owned by Foundation, see below)
* Person Database Schema (complete — `person` (28 columns) + `person_address` implemented under
  `database/ddl/03_person/`, superseding the v0.5.1 prototype by following the Foundation
  `master_data` pattern: gender/marital status/blood group/emergency relationship/address type
  resolve via `nss.master_data`, not dedicated per-domain master tables)
* Foundation Database Schema ("Foundation Vertical Slice" — 12 tables + full seed data under
  `database/ddl/01_foundation/`/`database/seed/01_foundation/` — 11 of the 12 tables are now
  consumed by the Tier 1 Foundation API, see below; `field_change_log` remains unconsumed,
  deferred to Tier 5)
* Organization Database Schema ("Organization Vertical Slice" — 1 table (`organization`) + full
  seed data under `database/ddl/02_organization/`/`database/seed/02_organization/`; the former
  `organization_type_master`/`organization_status_master` tables were retired in favor of
  Foundation's generic `master_data` (categories `ORGANIZATION_TYPE`, 10 values; `STATUS`, 13
  values, shared across modules) — now consumed by the Tier 2 Organization API (see below). This
  diverges from the frozen 3-table module design — see `docs/PROJECT_DOCUMENTATION.md` →
  Gotchas. Combined with Foundation, Bootstrap RBAC, Person, Family, and Membership:
  **35 tables implemented** — see `database/README.md`)
* Bootstrap RBAC DDL (`role_master`/`permission_master`/`role_permission`, `SOL-BOOT-001`/
  `SOL-ARCH-011` — DDL implemented and committed; `role_master` seeded with 8 roles,
  the other two empty pending the permission catalogue; ownership stays with Administration,
  see `docs/PROJECT_DOCUMENTATION.md` → Gotchas for a role-catalogue discrepancy this surfaced)
* FastAPI Tier 0 Bootstrap API (`api/` — 4 read-only endpoints: health check, roles,
  permissions, role→permissions; no auth, no ORM, raw `psycopg2` against `nss.*`, connects as
  `nss_db_backend`; the Django prototype that previously lived under `backend/` was archived
  and removed)
* Tier 0 Bootstrap Verification UI (`frontend/` — Tailwind CSS + DaisyUI (pre-built via Tailwind
  CLI, no longer CDN) + Alpine.js, served as static files by FastAPI; 4 sections: system status,
  RBAC roles, permissions, interactive role→permissions drill-down)
* FastAPI Tier 1 Foundation API (`api/routers/foundation.py` — 17 read-only endpoints across
  11 tables: master data, system settings, ID sequences, geography (country → state → district
  → city/village + postal codes), and document_master; `field_change_log` deliberately not
  exposed, deferred to Tier 5; no auth, no ORM, backed by 59 pytest integration tests — see
  `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`)
* Tier 1 Foundation Verification UI (`frontend/foundation.html` + `assets/js/foundation.js` —
  4-tab layout: Master Data, System Config, Geographic drill-down, Runtime Tables) — **page since
  retired and deleted; this functionality now lives in `admin.html`'s Reference Data and
  Geography tabs**
* Released as v0.7.0 — merged to `main`
* FastAPI Tier 2 Organization API (`api/routers/organization.py` — 6 read-only endpoints under
  `/api/v1/organization`: reference data (types, statuses), organization records (list with
  `type_code`/`status_code` filters, single-record lookup, children), and a self-referencing
  hierarchy tree via `WITH RECURSIVE`; no auth, no ORM, backed by 64 pytest integration tests —
  see `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`)
* Tier 2 Organization Verification UI (`frontend/organization.html` +
  `assets/js/organization.js` — 3-tab layout: Reference Data, Organizations, Hierarchy) — **page
  since retired and deleted; this functionality now lives in `admin.html`'s Organizations and
  Organization Hierarchy tabs**
* Implemented and released as v0.8.0 — merged to `main`
* FastAPI Tier 3 Person API (`api/routers/person.py` — 4 read-only endpoints under
  `/api/v1/person`: person list with `gender_code`/`marital_status_code`/`blood_group_code`
  filters and pagination, person detail, person addresses, and trigram-based (`pg_trgm`) name
  search; gender/marital status/blood group/emergency relationship/address type resolved via
  JOINs against Foundation's `master_data`; `aadhaar_encrypted`/`aadhaar_hash` are never
  returned — only `aadhaar_last4` for masked display (PER-BR-081); no auth, no ORM, backed by
  61 pytest integration tests — see `docs/03_Solution/api/PERSON_API_CONTRACT.md`)
* Tier 3 Person Verification UI (`frontend/person.html` + `assets/js/person.js` — Persons/Search
  tab layout structurally parallel to the Organization Verification UI) — **page since retired
  and deleted; this functionality now lives in `admin.html`'s Person Directory tab**
* Implemented and released as v0.9.0 — merged to `main`
* FastAPI Tier 4 Family API (`api/routers/family.py` — 7 read-only endpoints under
  `/api/v1/family`: family list with filters and pagination, family detail, family members
  (relationships per family), family head history, plus 3 newer endpoints — `/graph`
  (dynamic relationship-label computation via BFS traversal over `nss.family_link` edges, in a
  new `api/services/family_graph.py` — no test coverage yet), `/sakha-alignment` (FAM-036
  majority-rule "effective Sakha" computation with per-member mismatch flags), and
  `/person/{pk}/membership-summary` (bridges family context to membership context — also no
  test coverage yet); no auth, no ORM, backed by 67 pytest integration tests)
* FastAPI Tier 4 Membership API (`api/routers/membership.py` — 7 read-only endpoints under
  `/api/v1/membership`: member list with filters and pagination, member detail, a 7-field
  member search (Sangha Sevi ID, person ID, local Sakha ERP ID, name trigram, mobile, email,
  Kendra number) plus a 4-field person search, Sakha affiliation history, Parichaya Patra and
  Anumati Patra records, and journey-event timeline per member; three-tier identity model —
  Sangha Sevi ID (NSS-wide, permanent), Local Sakha Number (Sakha-scoped, auto-generated),
  Kendra Number (annual per FY, on `parichaya_patra.document_number`); no auth, no ORM, backed
  by 99 pytest integration tests — the largest test file in the repo)
* FastAPI Tier 2 Organization API grew a 7th endpoint, `/organizations/{pk}/children-stats`
  (aggregate family/member/person counts per direct child, recursing through descendant
  Sakhas and reusing the same FAM-036 majority-rule computation — implemented independently
  from Family's version, a real SQL duplication; its own docstring claims org-admin-sidebar UI
  wiring that does not exist in `admin.html`/`admin.js`'s Organization Hierarchy tab — which
  absorbed the deleted `organization.html`/`organization.js` — either)
* Tier 4 Family Verification UI (`frontend/family.html` + `assets/js/family.js` — now includes
  a family-tree visualization, viewer selector, and Sakha-alignment mismatch badges) and Tier 4
  Membership Verification UI (`frontend/membership.html` + `assets/js/membership.js`) — **both
  pages since retired and deleted; this functionality now lives in `dashboard.html`'s Family and
  Membership tabs, with the administrative member lookup in `admin.html`'s Member Directory tab**
* New shared frontend config: `frontend/assets/js/nss-config.js` (display-name overrides —
  `PROBATIONARY` → "Darshaka" — badge-class lookup maps, document-visibility rules) and
  `frontend/assets/css/badges.css` (every badge CSS class, single source of truth) — at the time,
  all 6 verification pages included both; both files survive the page retirement and are now
  included by `admin.html`/`dashboard.html`; no per-page duplicate inline badge styles
* Family DDL (5 tables: `family_group`, `family_relationship`, `family_head_history`,
  `family_transition_history`, `family_link` — the last stores only direct
  parent/spouse edges; every other kinship term is computed dynamically) and Membership DDL
  (12 tables: `sangha_sevi` plus
  status/renewal/transfer/affiliation/journey/review history tables, `parichaya_patra`/
  `anumati_patra` and their history tables) under `database/ddl/04_family/`/`05_membership/`
* New `database/migrations/` folder (narrow ad-hoc data-fix scripts, not a schema-migration
  tool) and two standalone `database/seed/99_*.sql` verification-data scripts (manual-run only)
* New consolidated `docs/03_Solution/api/API_CONTRACT.md` (cross-tier reference, Tiers 0-4,
  46 endpoints total) and security-audit docs moved from `code_explanations/` to a dedicated
  `docs/03_Solution/security/` folder (now including `TIER4_SECURITY_AUDIT.md`)
* New `tests/test_data_integrity.py` (23 tests) — cross-module smoke tests verifying every
  module has at least one active entity
* Merged to `develop` and `main`, tagged `v0.10.0` (see `docs/05_Releases/v0.10.0.md`)
* Three patch/hotfix tags followed v0.10.0, no individual release-notes docs yet: `v0.10.1`
  (wired `family_link` into `02_build.sh`/`render_build.sh`, extended `render_build.sh` through
  the full Tier 4 phase sequence), `v0.10.2` (creates `nss_db_owner`/`nss_db_backend` roles on
  Neon before granting — `render_build.sh` was failing at the grant step on a fresh Neon
  deploy), `v0.10.3` (root-cause idempotency fix: every `CREATE TABLE`/`INDEX` in `database/ddl/`
  now uses `IF NOT EXISTS`, every seed `INSERT` is now an upsert — fixes a production Neon
  database that was silently missing newer `master_data` columns/rows because a multi-`INSERT`
  seed file aborted partway through on the first pre-existing row)
* `v0.10.4` — performance-hardening pass (composite partial indexes for the FAM-036 CTE hot
  path, Uvicorn `--workers 2`, connection pool `minconn` 1→2, non-blocking frontend fetches);
  merged `performance-optimization` → `develop` → `main` (see `docs/05_Releases/v0.10.4.md`)
* Global Location Model
* Membership Module Design (v1.0, DRAFT — table/column shapes now match the implemented DDL,
  but the design doc itself hasn't been reconciled to FROZEN yet)
* Family Module Design (v1.0, DRAFT — same: implemented DDL matches, doc still DRAFT)
* Attendance Module Design (Review Workflow Frozen)
* Founder & Heritage Module Design (v1.0.0, SOURCE ALIGNED — 8 tables designed; zero
  implementation exists for any of them)
* Kumari Sangha Module Design (v1.0.0, SOURCE ALIGNED)
* Kishor Puja Module Design (v1.0.0, SOURCE ALIGNED — Guardian Model frozen v2.1)
* Mahila Sangha Module Design (v2.1.0, Bye-Law-aligned governance model)
* Sevak Sangha Module Design (partially frozen — table design only; see
  `docs/PROJECT_DOCUMENTATION.md`)
* Foundation Module Design (v1.0.0, SOURCE ALIGNED — describes 10 tables: the original 8
  master-data/geography/sequence tables plus `document_master` + `field_change_log`).
  **SQL implements 12 tables** (2
  more than the design doc covers — see Foundation Database Schema above and
  `docs/PROJECT_DOCUMENTATION.md`)
* Administration Module Design (v1.0.0/v1.2.0, SOURCE ALIGNED — 8 Administration-owned tables:
  5 RBAC tables plus the Correspondence Register; table-design doc frozen at v1.2.0 for the
  parallel administrative role model (`SOL-ADMIN-004`); `user_account`/`password_history` are
  exclusively Authentication-owned)
* Authentication & Security Module Design (v1.0.0, SOURCE ALIGNED — exclusively owns
  `user_account`+`password_history`; references but doesn't own Administration's 5 RBAC tables;
  no corresponding API/backend implementation exists yet)
* Governance Module Design (v1.0.0, SOURCE ALIGNED — Unified Body Governance Model + Elections,
  9 tables; freezes the Mahila Parichalana Mandali term at 3 years, conflicting with the Mahila
  module's own frozen 2-year term — unreconciled, see `docs/PROJECT_DOCUMENTATION.md`)
* Publications Module Design (v1.0.0, SOURCE ALIGNED + USER REQUIREMENTS — zero new tables,
  reuses Founder & Heritage's publication tables)
* UPBS Module Design (v1.0.0, SOURCE ALIGNED — 7 tables)
* Reports & Analytics Module Design (v1.0.0, SOURCE ALIGNED — 5 metadata/config-only tables)
* Audit Module Design (v1.0.0, SOURCE ALIGNED — 2 tables)
* Backup & Technical Module Design (v1.0.0, SOURCE ALIGNED — 2 tables)
* Finance Module Design (v1.0.0, SOURCE ALIGNED — 7 tables: financial_year, financial_scope,
  fund_master, financial_transaction, financial_receipt, financial_payment, financial_transfer;
  derives from NSS Bye-Law Section F and Mahila Sangha Bye-Law Clause 7)
* Programmes & Events Module Design (Module #21, v0.1.0, DRAFT — NOT FROZEN — Programme Type →
  Event Instance two-level model; 7 candidate common tables, all cross-module reconciliation
  gates closed (`SOL-EVT-007`) but no table frozen DDL yet)
* Assets & Property Module Design (Module #22, v1.0.0, SOURCE ALIGNED — 7 tables: property,
  asset, custodianship, property_statutory_record, maintenance_record, property_document,
  asset_document; 74 business rules)
* Frontend CSS build migration (uncommitted on `develop` as of this writing): Tailwind CSS +
  DaisyUI moved from CDN (`<script src="https://cdn.tailwindcss.com">` + DaisyUI CDN `<link>`)
  to a pre-built, tree-shaken, minified stylesheet (`frontend/assets/css/tailwind.min.css`,
  ~72 KB) generated via Tailwind CLI (`package.json`, `tailwind.config.js`); all 6 verification
  pages updated to `<link>` the built file; `render_build.sh` runs `npm install` + the Tailwind
  build before Python deps. `api/middleware.py` gained a `Cache-Control: public, max-age=86400,
  must-revalidate` header on `/assets/*` responses (previously only `/api/*` had a Cache-Control
  value at all) — no test coverage yet for this new header. The logo asset
  (`frontend/assets/img/nss-logo.png`) was also compressed (1.4 MB → ~100 KB), with the original
  kept as `nss-logo-original.png`.
* **Tier 5 — Authentication + Administration (in progress, uncommitted on
  `feature/tier5-authentication-administration`, not merged/released — treat every fact below as
  a snapshot of a moving branch, verify against `git status`/`git log` before relying on it):**
  9 new tables (`user_account`, `password_history`, `registration_claim`,
  `password_reset_token` under `database/ddl/06_authentication/`; `user_role`, `admin_scope`
  under `database/ddl/07_administration/`; `family_admin` and
  `darshak_attendance_registration` added to the already-implemented Family/Membership modules;
  plus `system_event_log` under `database/ddl/01_foundation/14_system_event_log.sql`, backed by
  a database-level `fn_audit_trigger()` (`15_audit_trigger.sql`, `SOL-AUDIT-004`) that fires on
  every INSERT/UPDATE/DELETE across `nss.*` business tables — actor identity comes from
  session variables (`nss.actor_sangha_sevi_pk`/`nss.actor_user_account_pk`) the app sets per
  request, not from application code, so writes can't bypass the audit trail; `api/helpers.py`
  also gained an application-level `log_audit()` used explicitly by the new write endpoints) —
  44 tables total once merged. New `api/routers/auth.py` (login/refresh/logout/change-password/
  forgot-password/reset-password/me), `api/routers/registration.py` (self-service
  `POST /api/v1/register`), `api/routers/claim_approval.py` (Sakha-admin review of registration
  claims), and `api/routers/admin.py` (user/role/organization management) — plus 9 new
  authenticated write endpoints added directly to `api/routers/family.py` (add/remove family
  member, family links, family admin assignment, head transfer, create family). New
  `nss_db_writer` PostgreSQL role (write access scoped to the new auth/admin tables only). Every
  Tier 4 "verification"/demo seed file has been deleted on this branch — a fresh build now
  produces a database with **zero demo Person/Family/Membership data**; real data comes from the
  registration/approval flow or a single seeded admin superuser
  (`scripts/bootstrap_admin.py`). `tests/conftest.py` was rewritten around a session-scoped
  `SAVEPOINT`-per-module fixture architecture to support this. See `CLAUDE.md` and
  `docs/PROJECT_DOCUMENTATION.md` for the full, current detail — this bullet is a summary, not
  the source of truth.

Current Focus:

* Reconciling Solution-layer design docs with actual SQL/API implementation across all 22
  documented modules — every module now has a complete (or largely complete) design. Five
  modules have real SQL implementation (Foundation: 12 tables; Organization: 1 table; Person:
  2 tables; Family: 5 tables; Membership: 12 tables) — 32 tables total, plus Bootstrap RBAC's
  3 tables (35 total), plus the Tier 0 FastAPI bootstrap-RBAC API. Foundation has a full
  Tier 1 API + Web UI (17 endpoints, 59 tests), released as v0.7.0. Organization has a full
  Tier 2 API + Web UI (7 endpoints, 72 tests), released as v0.8.0 (the 7th endpoint,
  `/children-stats`, was added later on top of Tier 4). Person now also has a full
  Tier 3 API + Web UI (4 endpoints, 61 tests), released as v0.9.0. Also in v0.9.0: the
  Organization master-data migration retiring `organization_type_master`/
  `organization_status_master` in favor of Foundation's `master_category`/`master_data`.
  Family and Membership now also have a full Tier 4 API + Web UI (7 + 7 original read
  endpoints, 67 + 99 tests — 46 endpoints total across Tiers 0-4), released as v0.10.0 (see
  `docs/05_Releases/v0.10.0.md`). The suite has since been reorganized off flat `tests/test_*.py`
  files into `tests/api/`, `tests/db/`, and a new Playwright browser-driven `tests/ui/` layer
  (backing the `ui`/`db` pytest markers now in `pytest.ini` alongside `integration`), and grown
  well past the old flat-file count as of the in-progress Tier 5 branch
  (`feature/tier5-authentication-administration`, uncommitted) — see
  `tests/README.md` for the current per-file breakdown and fixture architecture; the last
  released tag (`v0.10.4`) had 410.

---

# Tier-Wise Implementation Status

Each tier follows the vertical slice pattern: **DB -> API -> Web UI -> Flutter Mobile**.

| Tier | Modules | Focus | DB | API | Web UI | Mobile |
|------|---------|-------|----|-----|--------|--------|
| **0** | Bootstrap RBAC | Infrastructure bootstrap — `role_master`, `permission_master`, `role_permission` (3 tables) | Done | Done (4 endpoints) | Done (Bootstrap Verification) | -- |
| **1** | Foundation | Master data, geography, ID sequences, document/change-log (12 tables) | Done | Done (17 endpoints) | Done (Foundation Verification) | -- |
| **2** | Organization | Org types, statuses, self-referencing hierarchy (1 table; types/statuses sourced from Foundation `master_data`) | Done | Done (7 endpoints) | Done (Organization Verification) | -- |
| **3** | Person | Person identity, contact, address (2 tables: `person`, `person_address`) | Done | Done (4 endpoints) | Done (Person Verification) | -- |
| **4** | Family, Membership | Family groups/relationships + dynamic relationship graph (5 tables) + membership registration/approval/transfer/lifecycle (12 tables) | Done | Done (14 endpoints) | Done (Family + Membership Verification) | -- |
| **5** | Authentication, Administration | `user_account`, `password_history`, RBAC management, JWT/session | In progress (uncommitted) | In progress (uncommitted — auth, registration, claim-approval, admin routers exist) | In progress (uncommitted — login/register/dashboard/admin/claim-approval pages exist) | -- |
| **6** | Attendance, Governance, Assets & Property | Weekly sangha puja attendance + review, unified body governance + elections, property/asset custodianship | Not started | Not started | Not started | -- |
| **7** | Heritage (Founder & Heritage) | Founder record, teachings, objectives, milestones, publications framework (8 tables) | Not started | Not started | Not started | -- |
| **8** | Kumari Sangha, Kishor Puja | Youth modules — KM/KH identity, annual events, guardian assignment, SS transition | Not started | Not started | Not started | -- |
| **9** | Mahila Sangha, Sevak Sangha | Mahila governance (unified body model), Sevak volunteer/training/seva | Not started | Not started | Not started | -- |
| **10** | UPBS, Finance | UPBS event operations (registration, delegate cards, prasad patra) + financial transactions | Not started | Not started | Not started | -- |
| **11** | Publications, Reports, Audit, Backup | Cross-cutting — publication catalogue, reporting metadata, audit trail, backup records | Not started | Not started | Not started | -- |
| **12** | Programmes & Events | Common event framework (DRAFT, not frozen) — programme types, event instances, sessions | Not started | Not started | Not started | -- |

**Legend:**
- **Done** — implemented and merged to `develop`
- **Not started** — design docs complete, no implementation yet
- **--** — Mobile (Flutter) starts after Web UI stabilizes per tier; no mobile work planned until core tiers (0-5) have working web UIs

Tier ordering is driven by FK dependencies — each tier only depends on tables from earlier tiers. Tier 12 (Programmes & Events) is last because it remains DRAFT and cross-cuts nearly everything.

**Release convention:** one git tag per completed tier. Each tag is merged to `main` with a
release document under `docs/05_Releases/` before the next tier begins.

| Release | Tier | Scope |
|---------|------|-------|
| v0.6.0 | Tier 0 | Bootstrap RBAC — DB + API + UI + deployment (**released**) |
| v0.7.0 | Tier 1 | Foundation — API + Web UI + security hardening (DB already done) (**released**) |
| v0.8.0 | Tier 2 | Organization — API + Web UI (DB already done) (**released**) |
| v0.9.0 | Tier 3 | Person — DB rewrite + API + Web UI, plus the Organization master-data migration (**released**) |
| v0.10.0 | Tier 4 | Family + Membership — full vertical slice, family graph, Organization children-stats (**released**) |
| v0.10.1-v0.10.4 | Tier 4 (hotfixes) | Idempotent DDL/seed, Neon role bootstrap, performance indexes, a11y/perf polish (**released**) |
| v0.11.0 | Tier 5 | Authentication + Administration — full vertical slice (**in progress, uncommitted on `feature/tier5-authentication-administration`, not yet tagged**) |
| ... | Tier 6-12 | One tag per tier through Tier 12 |

Next Release Target:

```text
v0.11.0 — Tier 5 Authentication + Administration: user_account, password_history, RBAC
management, JWT/session; exposes field_change_log via API (deferred until now, needs auth);
adds nss_db_writer role + first write endpoints.
```

---

# Repository Structure

```text
NSS_ERP
│
├── api
│   ├── routers              (bootstrap.py, foundation.py, organization.py, person.py, family.py, membership.py; plus, in progress/uncommitted: auth.py, admin.py, registration.py, claim_approval.py)
│   ├── schemas               (bootstrap.py, foundation.py, organization.py, person.py, family.py, membership.py; plus, in progress/uncommitted: auth.py, admin.py)
│   ├── services              (family_graph.py — BFS relationship computation; plus, in progress/uncommitted: auth_service.py, rbac_service.py)
│   └── dependencies          (in progress/uncommitted — auth.py, rbac.py: FastAPI dependency-injected JWT/RBAC guards)
│
├── frontend                (login/register/dashboard/admin pages, served by FastAPI; the Tier 0-4 standalone verification pages were deleted and folded into admin.html/dashboard.html)
│   └── assets               (shared js/nss-config.js + css/badges.css, plus per-page files)
│
├── backend                (empty — earlier Django prototype archived and removed)
│
├── database
│   ├── ddl                  (00_bootstrap .. 05_membership; plus, in progress/uncommitted: 06_authentication, 07_administration)
│   ├── seed
│   ├── fixes                (in progress/uncommitted — narrow ad-hoc data-fix scripts, successor to the removed `migrations/`)
│   └── scripts
│
├── scripts                (in progress/uncommitted — repo-root Python ops scripts, e.g. `bootstrap_admin.py`; distinct from `database/scripts/`)
│
├── tests                  (pytest integration tests)
│
├── docs
│   ├── 00_Project_Governance
│   ├── 01_Authoritative_References
│   ├── 02_Requirements
│   ├── 03_Solution
│   ├── 04_Testing
│   └── 05_Releases
│
├── CLAUDE.md
├── README.md
├── pytest.ini
└── requirements.txt
```

See `docs/PROJECT_DOCUMENTATION.md` for the full, code-verified breakdown of each directory.

---

# Current Stable Version

```text
v0.10.4
```

Tier 4 Family + Membership (performance-hardening hotfix) — the latest tagged release on `main`.
Tier 5 (Authentication + Administration) is in progress, uncommitted, on
`feature/tier5-authentication-administration` — see `CLAUDE.md` and
`docs/PROJECT_DOCUMENTATION.md` for its current state.

---

# License

Internal NSS ERP Project

All Rights Reserved.
