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

* Tailwind CSS + DaisyUI (CDN) + Alpine.js (CDN) — no build step, no framework.
* `frontend/` implements a Tier 0 "Bootstrap Verification UI" (`index.html`, at `/`), a
  Tier 1 "Foundation Verification UI" (`foundation.html`, at `/foundation`), and a Tier 2
  "Organization Verification UI" (`organization.html`, at `/organization`) — none of these is
  the full admin dashboard yet — served as static files by FastAPI; see `frontend/README.md`
  for the full file/function reference. 13 static mockups for later tiers exist under
  `docs/03_Solution/ui/mockups/`.

---

## Backend

* FastAPI — the only web/API layer in the codebase (`api/`), currently a Tier 0 read-only
  bootstrap-RBAC API plus a Tier 1 read-only Foundation API (17 endpoints across 11 tables) plus
  a Tier 2 read-only Organization API (6 endpoints); no ORM, raw `psycopg2`, no auth. See
  `docs/PROJECT_DOCUMENTATION.md` → Architecture and
  `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`.
* Django — an earlier prototype existed under `backend/` but was fully archived and removed
  once the FastAPI direction was adopted; `backend/` is now empty.

---

## Database

* PostgreSQL

---

## Authentication

* None yet — Tier 0 is deliberately unauthenticated by design. RBAC/JWT enforcement is planned
  for a later tier.

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
FastAPI (api/main.py, Tier 0 bootstrap + Tier 1 foundation + Tier 2 organization routers)
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

## Prerequisites

- PostgreSQL 14+ (local or Neon.dev)
- Python 3.12+ with pip
- psql CLI (included with PostgreSQL)

## Step 1: Database Setup

### macOS / Linux (bash)

```bash
# 1a. Create database and roles (as superuser)
psql -U postgres -d postgres -f database/scripts/00_create_database.sql

# 1b. Set passwords for both roles (as superuser)
psql -U postgres -d postgres -c "ALTER ROLE nss_db_owner PASSWORD 'your_password_here';"
psql -U postgres -d postgres -c "ALTER ROLE nss_db_backend PASSWORD 'your_password_here';"

# 1c. Install extensions and create nss schema (as superuser)
psql -U postgres -d nss_erp -f database/scripts/01_extensions.sql

# 1d. Build all DDL + seed (as nss_db_owner)
./database/scripts/02_build.sh

# 1e. Validate (as nss_db_owner)
./database/scripts/03_validate.sh

# 1f. Grant backend role read-only access (as nss_db_owner)
psql -U nss_db_owner -d nss_erp -f database/scripts/04_grant_backend.sql
```

### Windows (PowerShell)

```powershell
# 1a. Create database and roles (as superuser)
psql -U postgres -d postgres -f database\scripts\00_create_database.sql

# 1b. Set passwords for both roles (as superuser)
psql -U postgres -d postgres -c "ALTER ROLE nss_db_owner PASSWORD 'your_password_here';"
psql -U postgres -d postgres -c "ALTER ROLE nss_db_backend PASSWORD 'your_password_here';"

# 1c. Install extensions and create nss schema (as superuser)
psql -U postgres -d nss_erp -f database\scripts\01_extensions.sql

# 1d. Build all DDL + seed (as nss_db_owner)
.\database\scripts\02_build.ps1

# 1e. Validate (as nss_db_owner)
.\database\scripts\03_validate.ps1

# 1f. Grant backend role read-only access (as nss_db_owner)
psql -U nss_db_owner -d nss_erp -f database\scripts\04_grant_backend.sql
```

> **Never commit real passwords.** Use `.pgpass` (macOS/Linux) or `%APPDATA%\postgresql\pgpass.conf`
> (Windows) for passwordless `psql` connections, or set `PGPASSWORD` in your shell session.

## Step 2: API Setup

```bash
# Install Python dependencies
# macOS / Linux:
python3 -m pip install -r requirements.txt
# Windows:
#   py -m pip install -r requirements.txt
```

Create `api/.env` with the `nss_db_backend` password from Step 1b:

**macOS / Linux:**
```bash
cat > api/.env << 'EOF'
DB_NAME=nss_erp
DB_USER=nss_db_backend
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
EOF
```

**Windows (PowerShell):**
```powershell
@"
DB_NAME=nss_erp
DB_USER=nss_db_backend
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
"@ | Out-File -Encoding utf8 api\.env
```

## Step 3: Start the API

```bash
# macOS / Linux:
python3 -m uvicorn api.main:app --reload --port 8001

# Windows:
py -m uvicorn api.main:app --reload --port 8001
```

**URLs:**

| URL | What |
|-----|------|
| `http://localhost:8001/` | Bootstrap Verification UI |
| `http://localhost:8001/foundation` | Foundation Verification UI |
| `http://localhost:8001/organization` | Organization Verification UI |
| `http://localhost:8001/docs` | Swagger UI (OpenAPI) |
| `http://localhost:8001/api/v1/` | API endpoints |

See `api/README.md` for the full per-tier endpoint list and security-middleware detail.

## Step 4: Run Tests

```bash
# macOS / Linux:
python3 -m pytest tests/ -v

# Windows:
py -m pytest tests/ -v
```

**139 tests total:** 21 (Tier 0 Bootstrap) + 59 (Tier 1 Foundation) + 51 (Tier 2 Organization) +
8 (Security Middleware). See `tests/README.md` for the per-file test inventory.

## Script Reference

See `database/scripts/README.md` for detailed script reference (what each script does, build
phases, role naming conventions, cross-platform principles).

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
├── ANCHALIKA
│   └── SAKHA
├── ZILLA
│   └── SAKHA
└── PATHA_CHAKRA
```

Notes:

* PATHA_CHAKRA is an Organization Type.
* PATHA_CHAKRA exists directly under KENDRA.
* PATHA_CHAKRA may operate within India or internationally.
* SAKHA exists under ANCHALIKA or ZILLA.

> **Open:** the Organization module's business rules (v1.1.0, GOVERNANCE ALIGNED,
> `docs/03_Solution/modules/organization/04_organization_business_rules.md`) explicitly leave
> the type-to-type parent compatibility matrix shown above as an **open item**, not a frozen
> decision — only the generic apex + self-referencing 3-table structure is frozen. Treat this
> diagram as the current working assumption, not a closed design.

> **Frozen separately:** an **8-type inventory** — the 5 types in the diagram above, plus
> `NILACHALA_KUTIRA` and `SMRUTI_MANDIRA` (both unique, fixed-code, not shown here since they
> don't participate in the parent hierarchy) and `SAKHA_ASANA` (sequence-generated like `SAKHA`,
> not yet placed in this diagram — its own parent relationship is part of the still-open matrix
> above). This is a type-*inventory* freeze only, separate from the still-open parent-matrix
> question.

> **Open:** the generic 3-table structure is implemented in SQL, but the seeded
> `organization_type_master` rows use `ANCHALIKA_SANGHA`/`ZILLA_SANGHA`/`SAKHA_SANGHA` as their
> business codes, not the short `ANCHALIKA`/`ZILLA`/`SAKHA` forms shown in the diagram above. See
> `docs/PROJECT_DOCUMENTATION.md` → Open questions / TODOs.

---

# Module Structure

*The sections below describe the full planned module roadmap. No module on this list has any
API/backend implementation yet — the only implemented code is a Tier 0 FastAPI bootstrap-RBAC
API (`api/`, 4 read-only endpoints) plus SQL DDL for Bootstrap RBAC, Foundation, and
Organization. An earlier Django prototype briefly implemented parts of Foundation, Membership,
Family, Governance (stub), Attendance (stub), and Founder & Heritage under `backend/`, but it
was fully archived and removed once the FastAPI direction was adopted. Solution-layer design
documentation (overview/ERD/lifecycle/business-rules/table-design) is complete for essentially
every module on this roadmap — ahead of, and not yet reconciled with, any code implementation.
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

# Current Development Status

Completed:

* Foundation Architecture
* Authentication Foundation
* Organization Module Design (v1.1.0, GOVERNANCE ALIGNED; type-to-type parent hierarchy left as
  an open item, not frozen)
* Person Module Design (v1.0.0, SOURCE ALIGNED — 1 table: `person`; `document_master` is owned
  by Foundation, see below)
* Person Database Schema (partial — `person`/`person_address` implemented; the docs' `person_id`
  naming doesn't match the DDL's `person_code`)
* Foundation Database Schema ("Foundation Vertical Slice" — 12 tables + full seed data under
  `database/ddl/01_foundation/`/`database/seed/01_foundation/` — 11 of the 12 tables are now
  consumed by the Tier 1 Foundation API, see below; `field_change_log` remains unconsumed,
  deferred to Tier 5)
* Organization Database Schema ("Organization Vertical Slice" — 3 tables
  (`organization_type_master`, `organization_status_master`, `organization`) + full seed data
  under `database/ddl/02_organization/`/`database/seed/02_organization/`, matching the frozen
  generic structure exactly — now consumed by the Tier 2 Organization API (see below). Combined
  with Foundation and Bootstrap RBAC: **18 tables implemented** — see `database/README.md`)
* Bootstrap RBAC DDL (`role_master`/`permission_master`/`role_permission`, `SOL-BOOT-001`/
  `SOL-ARCH-011` — DDL implemented and committed; `role_master` seeded with 8 roles,
  the other two empty pending the permission catalogue; ownership stays with Administration,
  see `docs/PROJECT_DOCUMENTATION.md` → Gotchas for a role-catalogue discrepancy this surfaced)
* FastAPI Tier 0 Bootstrap API (`api/` — 4 read-only endpoints: health check, roles,
  permissions, role→permissions; no auth, no ORM, raw `psycopg2` against `nss.*`, connects as
  `nss_db_backend`; the Django prototype that previously lived under `backend/` was archived
  and removed)
* Tier 0 Bootstrap Verification UI (`frontend/` — Tailwind CSS + DaisyUI + Alpine.js, no build
  step, served as static files by FastAPI; 4 sections: system status, RBAC roles, permissions,
  interactive role→permissions drill-down)
* FastAPI Tier 1 Foundation API (`api/routers/foundation.py` — 17 read-only endpoints across
  11 tables: master data, system settings, ID sequences, geography (country → state → district
  → city/village + postal codes), and document_master; `field_change_log` deliberately not
  exposed, deferred to Tier 5; no auth, no ORM, backed by 59 pytest integration tests — see
  `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`)
* Tier 1 Foundation Verification UI (`frontend/foundation.html` + `assets/js/foundation.js` —
  4-tab layout: Master Data, System Config, Geographic drill-down, Runtime Tables)
* Released as v0.7.0 — merged to `main`
* FastAPI Tier 2 Organization API (`api/routers/organization.py` — 6 read-only endpoints under
  `/api/v1/organization`: reference data (types, statuses), organization records (list with
  `type_code`/`status_code` filters, single-record lookup, children), and a self-referencing
  hierarchy tree via `WITH RECURSIVE`; no auth, no ORM, backed by 51 pytest integration tests —
  see `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`)
* Tier 2 Organization Verification UI (`frontend/organization.html` +
  `assets/js/organization.js` — 3-tab layout: Reference Data, Organizations, Hierarchy)
* Implemented on the `feature/tier2-organization` branch — not yet merged/released as v0.8.0
* Global Location Model
* Membership Module Design
* Family Module Design
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

Current Focus:

* Reconciling Solution-layer design docs with actual SQL/API implementation across all 22
  documented modules — every module now has a complete (or largely complete) design. Two
  modules have real SQL implementation (Foundation: 12 tables; Organization: 3 tables) — 15
  tables total, plus the Tier 0 FastAPI bootstrap-RBAC API. Foundation has a full Tier 1 API +
  Web UI (17 endpoints, 59 tests), released as v0.7.0. Organization now also has a full Tier 2
  API + Web UI (6 endpoints, 51 tests), implemented on the `feature/tier2-organization` branch.
  No release doc has been created yet for the Organization API/UI implementation or the
  module-documentation backlog.

---

# Tier-Wise Implementation Status

Each tier follows the vertical slice pattern: **DB -> API -> Web UI -> Flutter Mobile**.

| Tier | Modules | Focus | DB | API | Web UI | Mobile |
|------|---------|-------|----|-----|--------|--------|
| **0** | Bootstrap RBAC | Infrastructure bootstrap — `role_master`, `permission_master`, `role_permission` (3 tables) | Done | Done (4 endpoints) | Done (Bootstrap Verification) | -- |
| **1** | Foundation | Master data, geography, ID sequences, document/change-log (12 tables) | Done | Done (17 endpoints) | Done (Foundation Verification) | -- |
| **2** | Organization | Org types, statuses, self-referencing hierarchy (3 tables) | Done | Done (6 endpoints) | Done (Organization Verification) | -- |
| **3** | Person | Person identity, contact, address (2 tables designed) | Superseded (rewrite pending) | Not started | Not started | -- |
| **4** | Family, Membership | Family groups/relationships + membership registration/approval/transfer/lifecycle | Not started | Not started | Not started | -- |
| **5** | Authentication, Administration | `user_account`, `password_history`, RBAC management, JWT/session | Not started | Not started | Not started | -- |
| **6** | Attendance, Governance, Assets & Property | Weekly sangha puja attendance + review, unified body governance + elections, property/asset custodianship | Not started | Not started | Not started | -- |
| **7** | Heritage (Founder & Heritage) | Founder record, teachings, objectives, milestones, publications framework (8 tables) | Not started | Not started | Not started | -- |
| **8** | Kumari Sangha, Kishor Puja | Youth modules — KM/KH identity, annual events, guardian assignment, SS transition | Not started | Not started | Not started | -- |
| **9** | Mahila Sangha, Sevak Sangha | Mahila governance (unified body model), Sevak volunteer/training/seva | Not started | Not started | Not started | -- |
| **10** | UPBS, Finance | UPBS event operations (registration, delegate cards, prasad patra) + financial transactions | Not started | Not started | Not started | -- |
| **11** | Publications, Reports, Audit, Backup | Cross-cutting — publication catalogue, reporting metadata, audit trail, backup records | Not started | Not started | Not started | -- |
| **12** | Programmes & Events | Common event framework (DRAFT, not frozen) — programme types, event instances, sessions | Not started | Not started | Not started | -- |

**Legend:**
- **Done** — implemented and merged to `develop`
- **Superseded** — v0.5.1 Person DDL exists but uses per-domain masters; needs rewrite against Foundation's `master_category`/`master_data` pattern
- **Not started** — design docs complete, no implementation yet
- **--** — Mobile (Flutter) starts after Web UI stabilizes per tier; no mobile work planned until core tiers (0-5) have working web UIs

Tier ordering is driven by FK dependencies — each tier only depends on tables from earlier tiers. Tier 12 (Programmes & Events) is last because it remains DRAFT and cross-cuts nearly everything.

**Release convention:** one git tag per completed tier. Each tag is merged to `main` with a
release document under `docs/05_Releases/` before the next tier begins.

| Release | Tier | Scope |
|---------|------|-------|
| v0.6.0 | Tier 0 | Bootstrap RBAC — DB + API + UI + deployment (**released**) |
| v0.7.0 | Tier 1 | Foundation — API + Web UI + security hardening (DB already done) (**released**) |
| v0.8.0 | Tier 2 | Organization — API + Web UI (DB already done; implemented on `feature/tier2-organization` branch, **not yet released**) |
| v0.9.0 | Tier 3 | Person — DB rewrite + API + Web UI |
| v0.10.0 | Tier 4 | Family + Membership — full vertical slice |
| v0.11.0 | Tier 5 | Authentication + Administration — full vertical slice |
| ... | Tier 6-12 | One tag per tier through Tier 12 |

Next Release Target:

```text
v0.8.0 — Tier 2 Organization: API endpoints for org types, statuses, self-referencing
hierarchy, Web UI views. DB already complete (3 tables live since v0.6.0). API + Web UI are
implemented on the `feature/tier2-organization` branch, backed by 51 pytest integration
tests — not yet merged/tagged as v0.8.0.

Up next once v0.8.0 ships: v0.9.0 — Tier 3 Person: DB rewrite (superseding the v0.5.1 prototype
against Foundation's master_category/master_data pattern) + API + Web UI.
```

---

# Repository Structure

```text
NSS_ERP
│
├── api
│   ├── routers              (bootstrap.py, foundation.py, organization.py)
│   └── schemas               (bootstrap.py, foundation.py, organization.py)
│
├── frontend                (Tier 0 Bootstrap + Tier 1 Foundation + Tier 2 Organization Verification UIs, served by FastAPI)
│   └── assets
│
├── backend                (empty — earlier Django prototype archived and removed)
│
├── database
│   ├── ddl
│   ├── seed
│   └── scripts
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
v0.7.0
```

Tier 1 Foundation — API, Web UI, Security Hardening

---

# License

Internal NSS ERP Project

All Rights Reserved.
