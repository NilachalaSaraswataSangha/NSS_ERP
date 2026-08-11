# NSS ERP — Project Documentation

This document is a detailed, standalone explanation of how the NSS ERP codebase is
actually built, as of the current repository state (branch `feature/ref-documentation`,
most recent milestone `v0.5.1`). It is written for a human getting oriented in the
system, and is more explanatory than `README.md` or any `CLAUDE.md`. Where the code
diverges from what the README or docs describe, that is called out explicitly.

---

## 1. Overview

NSS ERP is a web-based management platform for Nilachala Saraswata Sangha (NSS), an
organization with a hierarchical structure (Kendra → Anchalika/Zilla → Sakha /
Patha Chakra). It is intended to manage membership, family relationships,
governance bodies, attendance, and several sub-organizations (Kumari Sangha,
Kishore Puja, Mahila Sangha, Sevak Sangha, UPBS), plus founder/heritage records.

The project follows a **Database First → API First → UI First** philosophy — SQL DDL
and business rules are meant to be frozen (`docs/modules/**`) before Django models are
written, and Django models before UI/views. In practice, as detailed in
[Section 9 (Conventions & gotchas)](#9-conventions--gotchas), this ordering has not
been applied uniformly: several Django apps have working models with no corresponding
DDL yet.

Stack:
- **Backend**: Django 6.0.6 (server-rendered app), with FastAPI 0.136.3 present as a
  dependency for a future API layer (no FastAPI routes exist in the repo yet).
- **Frontend**: Django Templates + Bootstrap 5 + HTMX (via `django-htmx`).
- **Database**: PostgreSQL, accessed through Django ORM; hand-written DDL also lives
  under `database/ddl/`.
- **Auth**: Django's built-in authentication system today; JWT is a stated future goal.

---

## 2. Architecture

Request flow, as implemented today:

```
Browser
   │
   ▼
Django URL dispatcher (backend/config/urls.py)
   │
   ▼
App-level views (function-based, backend/<app>/views.py)
   │
   ▼
Django ORM models (backend/<app>/models.py)
   │
   ▼
PostgreSQL
```

The README's architecture diagram also shows a "FastAPI Services" layer between
templates and the ORM. That layer does not exist yet — `FastAPI` and `Starlette`/
`Uvicorn` are installed (`requirements.txt`) but there is no FastAPI app, router, or
ASGI wiring for it anywhere in `backend/`. The only ASGI/WSGI entry points
(`backend/config/asgi.py`, `backend/config/wsgi.py`) point at the Django app.

**Two parallel schema-design tracks exist:**

1. **Django models** (`backend/*/models.py`) — used to actually run the app via
   `manage.py migrate`. These are simpler (e.g. `CharField` choices instead of
   master-data foreign keys, plain integer/auto PKs).
2. **Hand-authored DDL** (`database/ddl/**`) — the "Database First" source of truth
   per `docs/standards/01_project_standards.md`, using UUID primary keys, dedicated
   master tables, and full audit columns (`created_at`, `updated_at`, `deleted_at`,
   `is_active`).

These two tracks currently **disagree** in several places — see
[Section 9](#9-conventions--gotchas). Anyone extending the schema should treat
`database/ddl/` + `docs/modules/**` as the design of record and expect the Django
models to eventually be brought in line with it (this already happened once: compare
the simple `foundation.Person` Django model against the much more detailed
`database/ddl/03_person/02_person.sql`).

**Documentation layers**, from most to least authoritative:

```
docs/01_Authoritative_References/   ← transcribed NSS Bye-Law text (legal ground truth)
docs/standards/                     ← frozen, project-wide engineering standards
docs/modules/<module>/              ← per-module design docs, ERDs, business rules, table design
database/ddl/, database/seed/       ← hand-written SQL implementing the frozen module design
backend/<app>/                      ← Django implementation (models/views/urls/admin)
docs/releases/                      ← changelog of what shipped in each version
```

---

## 3. Directory structure

```
NSS_ERP
├── backend/                  Django project (see Section 4)
│   ├── config/                Django settings, root urls, wsgi/asgi
│   ├── authentication/        Role/UserRole/LoginAudit, login view
│   ├── foundation/            OrganizationType, Organization, Address, Person
│   ├── membership/            MembershipType, MembershipStatus, SanghaSevi
│   ├── family/                FamilyGroup, FamilyMembership
│   ├── governance/            empty stub app (not installed)
│   ├── attendance/            empty stub app (not installed)
│   ├── dashboard/             one view (kendra_dashboard), no models
│   ├── templates/             shared templates (base/, auth/, dashboard/, foundation/)
│   └── static/                css/app.css, js/app.js
├── database/
│   ├── ddl/                   hand-written schema, in numbered phase folders
│   │   ├── 01_foundation/     extensions, id_sequence_master, location hierarchy
│   │   ├── 02_organization/   organization tables — files exist but are EMPTY
│   │   └── 03_person/         person + person_address + related masters (complete)
│   └── seed/                  reference/master data matching the ddl phases
│       ├── 01_foundation/     id sequences, country_master seed
│       └── 03_person/         gender/marital_status/address_type seed
├── docs/
│   ├── 01_Authoritative_References/   NSS Bye-Law, organized as SECTION-A .. SECTION-J
│   ├── standards/              5 frozen project-wide standards documents
│   ├── modules/                per-module design docs (organization/, person/)
│   └── releases/               v0.1.0.md .. v0.5.1.md changelog
├── requirements.txt
└── README.md
```

---

## 4. Backend: Django apps in detail

`backend/config/settings.py` — `INSTALLED_APPS` currently includes only
**foundation, membership, family, authentication** (plus Django's own apps). The
**governance**, **attendance**, and **dashboard** app directories exist on disk but
`dashboard` is wired into `urls.py` despite not being in `INSTALLED_APPS` (it has no
models, so this happens to work); `governance` and `attendance` are inert stub apps
with no models, views, URLs, or migrations.

### 4.1 `foundation` — org & person primitives

`backend/foundation/models.py`:
- `OrganizationType` — `code` (unique), `name`, `description`, `is_active`. Master-like
  lookup table for organization types (KENDRA/ANCHALIKA/ZILLA/SAKHA/PATHA_CHAKRA in
  concept, though no seed/migration enforces those specific values in Django).
- `Organization` — FK → `OrganizationType` (`PROTECT`), `code` (unique), `name`,
  `short_name`. No self-referencing `parent_organization` field yet, so the
  Kendra→Anchalika/Zilla→Sakha hierarchy described in the README/design docs is not
  yet representable in the Django model (contrast with `docs/modules/organization/02_organization_erd.md`,
  which specifies a `parent_organization_pk` self-reference).
- `Address` — flat, denormalized address fields (`city`, `district`, `state`,
  `postal_code`, `country`), unlike the normalized location hierarchy in the DDL.
- `Person` — `first_name`/`middle_name`/`last_name`, `gender` (plain `CharField`, not
  an FK to a `gender_master`), `date_of_birth`, `mobile_number`, `email`, FK →
  `Address` (`SET_NULL`). Implements "Person ≠ Member" only implicitly — there is no
  `membership` field on `Person`; the link is the other direction
  (`SanghaSevi.person`, a `OneToOneField`).

Views (`backend/foundation/views.py`): `person_list` and `person_detail`, both
`@login_required`, rendering `foundation/person_list.html` and
`foundation/person_detail.html`. Routes in `backend/foundation/urls.py`:
`persons/` and `persons/<int:pk>/`.

Admin (`backend/foundation/admin.py`) registers all four models with list
display/search/filter configured.

### 4.2 `authentication` — login & RBAC scaffolding

`backend/authentication/models.py`:
- `Role` — `code` (unique), `name`, `description`, `is_active`.
- `UserRole` — FK → Django `User` (`CASCADE`) and FK → `Role` (`PROTECT`),
  `is_primary`, `unique_together=(user, role)`. This is a basic RBAC join table; it
  does not yet implement the richer role/permission/scope model described in
  `docs/standards/05_security_standards.md` (no `permission` or `role_permission`
  tables, no row-level-security scope).
- `LoginAudit` — FK → `User` (`SET_NULL`), `login_time`, `ip_address`, `user_agent`,
  `success`. Not registered in Django admin.

View: `login_view` (`backend/authentication/views.py`) — function-based, handles
POST login, redirects to `/dashboard/` on success. Route: `login/`
(`backend/authentication/urls.py`).

### 4.3 `membership` — Sangha Sevi (member) record

`backend/membership/models.py`:
- `MembershipType`, `MembershipStatus` — simple code/name lookup tables.
- `SanghaSevi` — `sangha_sevi_id` (unique), `person` (`OneToOneField` → `foundation.Person`,
  `PROTECT`), `organization` (FK → `foundation.Organization`, `PROTECT`),
  `membership_type`, `membership_status`, `joining_date`, `renewal_due_date`.

This app has **no views beyond the generated stub, no `urls.py`, and no templates** —
only the model layer and Django admin registration exist. Per the README and
`docs/releases/v0.5.1.md`, Membership Module design/business-rules/DDL is the
declared "current focus" / next milestone (`v0.6.0`), so this is expected
in-progress state rather than an oversight.

### 4.4 `family` — family grouping

`backend/family/models.py`:
- `FamilyGroup` — `family_id` (unique), `family_name`, `is_active`, `remarks`.
- `FamilyMembership` — FK → `FamilyGroup` (`CASCADE`), FK → `foundation.Person`
  (`PROTECT`), `relationship` (`CharField` choices: HEAD/SPOUSE/CHILD/PARENT/SIBLING/OTHER),
  `is_primary`, `start_date`, `end_date`.

Like `membership`, this app has model + migrations only: no views, no `urls.py`, and
`backend/family/admin.py` is **completely empty** (no models registered).

### 4.5 `governance`, `attendance` — unstarted

Both are Django app skeletons (`django-admin startapp` output, untouched): empty
`models.py`/`views.py`/`admin.py`, and `governance`/`attendance` have no migrations
folder content beyond `__init__.py`. Neither is in `INSTALLED_APPS`.

### 4.6 `dashboard` — landing page only

No models. `backend/dashboard/views.py` has `kendra_dashboard`, rendering
`dashboard/kendra_dashboard.html` (a `sakha_dashboard.html` template also exists but
has no view wired to it yet). Route: `""` → `kendra_dashboard`
(`backend/dashboard/urls.py`), mounted at `dashboard/` in the root URL conf. Note the
view has **no `@login_required`**, unlike `foundation`'s views — worth fixing before
this is a real landing page, since `LOGIN_REDIRECT_URL` sends every successful login
here.

### 4.7 Project wiring

`backend/config/settings.py`:
- Loads config from a `.env` file at the repo root via `django-environ`
  (`environ.Env.read_env(BASE_DIR / '.env')`); DB credentials (`DB_NAME`, `DB_USER`,
  `DB_PASSWORD`, `DB_HOST`, `DB_PORT`) come from environment variables, not hardcoded.
- `DATABASES` uses `django.db.backends.postgresql`.
- Standard middleware stack (security, session, common, csrf, auth, messages,
  x-frame-options) — nothing custom added yet.
- Templates: `APP_DIRS=True`, plus a project-level `backend/templates/` dir.
- `STATIC_URL = 'static/'`, static files served from `backend/static/`.
- `LOGIN_URL = "/login/"`, `LOGIN_REDIRECT_URL = "/dashboard/"`, `LOGOUT_REDIRECT_URL = "/login/"`.

`backend/config/urls.py` (root conf): `""` redirects to `login`; `admin/` → Django
admin; `""` → `authentication.urls`; `dashboard/` → `dashboard.urls`; `""` →
`foundation.urls`.

---

## 5. Database: DDL & seed data

`database/ddl/` is organized into numbered phase folders, executed in order:

**`01_foundation/`** (complete):
- `01_extensions.sql` — enables `pgcrypto` (for UUID generation).
- `02_id_sequence_master.sql` — `id_sequence_master` table, one row per business-ID
  prefix (e.g. `PERSON`→`P`, `SANGHA_SEVI`→`SS`, `ORGANIZATION`→`ORG`, `FAMILY`→`F`),
  seeded in `database/seed/01_foundation/01_id_sequence_master.sql`.
- `03_location_master_tables.sql` — full location hierarchy: `country_master` →
  `state_province_master` → `district_region_master` → `city_village_master`, plus
  `postal_code_master` and a `city_village_postal_code_map` join table. Composite
  uniqueness is scoped per-parent (e.g. state unique within country) to support
  international structures. Seeded with 5 countries in
  `database/seed/01_foundation/02_location_master_seed.sql` — no states/districts/
  cities/postal codes are seeded yet.

**`02_organization/`** — **all 4 files are empty placeholders**
(`01_organization_type_master.sql`, `02_organization_status_master.sql`,
`03_organization.sql`, `04_organization_address.sql`). The design is fully specified
in `docs/modules/organization/` (see Section 6) but not yet transcribed into SQL —
this is the main blocker for a real "Database First" Organization implementation.

**`03_person/`** (complete):
- `01_person_master_tables.sql` — `gender_master`, `marital_status_master`,
  `address_type_master`.
- `02_person.sql` — `person` table: UUID PK, unique `person_code`, gender/marital
  status FKs, `country_phone_code` + `mobile_number` (unique pair, both-or-neither via
  `chk_person_mobile_pair`), `email`, a `chk_person_contact_required` check requiring
  mobile or email, full audit columns including `deleted_at` for soft delete.
- `03_person_address.sql` — `person_address`: FK to `person`, `address_type`, and the
  location mapping table; a partial unique index enforces **at most one primary
  address per person** (`WHERE is_primary = TRUE`).
- Seeded in `database/seed/03_person/01_person_master_tables.sql` (genders, marital
  statuses, address types).

There is no `database/scripts/` directory despite the README's repository-structure
diagram listing one.

---

## 6. Module design docs (`docs/modules/`)

Two modules have full design documentation (design → ERD → business rules → table
design), each versioned and marked with a status:

- **`docs/modules/organization/`** (status: frozen business rules, v1.0 DRAFT docs) —
  specifies a **single `organization` table** with a self-referencing
  `parent_organization_pk` for the whole Kendra/Anchalika/Zilla/Sakha/Patha_Chakra
  hierarchy, rather than one table per level. Business-ID scheme:
  `KD0001`/`AN0001`/`ZL0001`/`SK0001`/`PC0001` generated via `id_sequence_master`.
  Hierarchy validity rules (e.g. only one active KENDRA; ANCHALIKA's parent must be
  KENDRA; SAKHA's parent must be ANCHALIKA or ZILLA) are documented in
  `03_organization_business_rules.md` but **not yet enforced anywhere** — neither in
  the (empty) DDL nor in the Django model, which has no parent field at all.
- **`docs/modules/person/`** (status: design/ERD/business-rules/table-design all
  frozen, SQL implementation complete as of v0.5.1) — this is the one module where
  design docs, DDL, and (a simplified) Django model all exist, making it the best
  reference for how the other modules are meant to evolve.

`docs/modules/person/README.md` is a good model for how a module's own index/status
page should look if new module folders are added (e.g. for Membership or Family).

---

## 7. Standards (`docs/standards/`)

Five frozen (v1.0) standards documents govern how everything above should
ultimately be built:

- **`01_project_standards.md`** — core principles (Person ≠ Member, Family First,
  History Never Deleted, Documentation First, Master Data Driven, Audit First,
  Security by Design, By-Law Supremacy), tech stack, and the Database→API→UI workflow.
- **`02_naming_conventions.md`** — table names singular/snake_case
  (`person`, `family_group`); PK columns are always `<table>_pk` (UUID); business IDs
  are separate `<table>_id` columns, never used as PK; FKs always reference `_pk`
  columns; master tables suffixed `_master`; history tables suffixed `_history`;
  Django models PascalCase; API paths kebab-case; git branches
  `feature/*`/`fix/*`/`hotfix/*`.
- **`03_master_data_catalog.md`** — inventory of ~20 planned master-data categories
  (geography, organization, membership, family, governance, attendance, security,
  Kumari/Kishore/Sevak, UPBS, finance, etc.) — most are not yet implemented as tables.
- **`04_audit_standards.md`** — mandatory audit columns on every table
  (`created_at`/`created_by_sangha_sevi_pk`/`updated_at`/`updated_by_sangha_sevi_pk`/
  `deleted_at`/`deleted_by_sangha_sevi_pk`/`is_active`), soft-delete-only policy, and
  a planned central `audit_master` log table (not yet implemented).
- **`05_security_standards.md`** — RBAC + row-level security by organizational scope
  (KENDRA=all, ANCHALIKA/ZILLA/SAKHA=assigned subtree, PERSONAL=own data), password
  policy (12+ chars, Argon2/PBKDF2), account lockout after 5 failed attempts,
  30-minute session timeout. **Not yet implemented** in `authentication` — current
  code is plain Django auth with a basic `Role`/`UserRole` table and no RLS, no
  lockout, no password policy enforcement.

These standards documents describe the target state; treat gaps between them and
`backend/` as known, tracked technical debt rather than bugs to silently "fix" without
checking against a release plan first.

---

## 8. Setup & running

There is no documented setup script; based on `requirements.txt` and
`backend/config/settings.py`:

```bash
# from repo root
pip install -r requirements.txt

# create a .env file at the repo root with at minimum:
#   DB_NAME=...
#   DB_USER=...
#   DB_PASSWORD=...
#   DB_HOST=...
#   DB_PORT=...

cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

No test runner configuration beyond Django's default was found — each app has an
essentially empty `tests.py` (generated stub), so `python manage.py test` currently
exercises nothing meaningful. No Makefile, Dockerfile, or CI config exists in the
repo at present, despite Docker/Nginx/Gunicorn/Ubuntu being named as the deployment
target stack in `docs/standards/01_project_standards.md` and the README.

The hand-written SQL in `database/ddl/` and `database/seed/` is not wired into
`manage.py migrate` — it must be applied manually against PostgreSQL (e.g. via
`psql`) if you want the DDL-first schema rather than Django's own migrations. Right
now these two schemas are not the same (see Section 9), so running both against the
same database is not safe without reconciling them first.

---

## 9. Conventions & gotchas

- **Two schemas, one database, currently out of sync.** Django's own migrations
  (`backend/*/migrations/`) create a simpler schema (integer/auto PKs, `CharField`
  choices instead of master-table FKs, denormalized `Address`). The hand-written DDL
  in `database/ddl/03_person/` implements the "frozen" design (UUID PKs, master-data
  FKs for gender/marital status, normalized location hierarchy, full audit columns).
  Don't assume the two are interchangeable; when working on Person-related code,
  check which schema is actually the DB target before adding new logic.
- **Organization hierarchy isn't modeled yet in code.** The README, standards docs,
  and `docs/modules/organization/` all describe a Kendra→Anchalika/Zilla→Sakha/Patha_Chakra
  tree via `parent_organization_pk`. Neither the Django `Organization` model nor the
  (empty) DDL files implement this yet — `Organization` today is a flat table.
- **`membership` and `family` apps are model-only.** No views, no `urls.py`, no
  templates, and `family/admin.py` doesn't register anything. If asked to "add a
  membership page" or "wire up family CRUD," expect to build the view/URL/template
  layer from scratch, not just extend existing ones.
- **`governance` and `attendance` are empty scaffolds and not installed.** Don't
  assume seeing the directory means there's anything to build on — check
  `INSTALLED_APPS` in `backend/config/settings.py` before referencing them.
- **`dashboard.kendra_dashboard` has no `@login_required`,** unlike every other view
  in the project, even though it's the default post-login landing page.
- **RBAC is minimal today.** `authentication.Role`/`UserRole` is a plain
  many-to-many; there's no `Permission` model, no row-level security, and none of the
  password/session policies in `docs/standards/05_security_standards.md` are
  enforced by code yet (Django's defaults apply).
- **FastAPI is a dependency but unused.** Don't be misled by `requirements.txt` or
  the README's architecture diagram into thinking there's an API layer — there isn't
  one in the current codebase.
- **Numbered SQL/doc files encode execution/reading order**, per
  `docs/standards/02_naming_conventions.md` (`NN_description.sql`,
  `NN_description.md`). Preserve this when adding new DDL or module docs.
- **Soft delete is policy, not yet universal.** The DDL for `person`/`person_address`
  has `deleted_at`; the Django models for every app currently use plain `is_active`
  booleans with no `deleted_at`/`deleted_by` columns, so physical vs. soft delete
  behavior differs depending on which layer you're reading.

---

## 10. Open questions / TODOs found in code

- `database/ddl/02_organization/*.sql` — all four files are present but empty; this
  is the most concrete, file-level TODO in the repo (the design to fill them in
  already exists in `docs/modules/organization/04_organization_table_design.md`).
- `backend/family/admin.py` — no models registered (`FamilyGroup`, `FamilyMembership`
  are invisible in Django admin today).
- `backend/membership/views.py`, `backend/family/views.py` — stub files
  (`# Create your views here.`), no logic implemented.
- `backend/governance/*`, `backend/attendance/*` — entirely stub apps (`# Create your
  models/views here.` / `# Register your models here.`), not in `INSTALLED_APPS`.
- `docs/releases/v0.1.0.md` through `v0.4.0.md` have release dates written as
  `14-06-2026`, which is inconsistent with the repo's actual git history (these
  early milestones predate `v0.5.1`, dated `2026-06-15`) — likely a copy-paste date
  typo across those files rather than real chronology; worth fixing before these
  notes are treated as an authoritative timeline.
- No `database/scripts/` directory exists despite being listed in the README's
  repository-structure diagram.

---

## 11. Authoritative References (`docs/01_Authoritative_References/`)

This directory holds a verbatim transcription of the NSS Bye-Law (Fourth Edition,
2025), reorganized into an official section hierarchy (per recent commit
`0d41860 refactor(ref): reorganize authoritative references into official Bye-Law
section hierarchy`). It is the legal ground truth that `docs/standards/` and
`docs/modules/` business rules should trace back to (the "By-Law Supremacy"
principle in `01_project_standards.md`).

Structure — 10 sections, each a folder of `REF-NNN[-NNN]_TITLE.md` files:

| Section | Contents |
|---|---|
| SECTION-A_PRELIMINARY_AND_GENERAL_PROVISIONS | REF-001 — NSS Constitution |
| SECTION-B_MEMBERSHIPS | REF-002 — Membership Bye-Laws |
| SECTION-C_CONSTITUTION_OF_THE_KENDRA_SANGHA | REF-003-001 .. 009 — Kendra Sangha constitution, Governing Body, and duties of President/VP/Secretary/Assistant Secretary/Treasurer/Parichalak |
| SECTION-D_ADVISORY_BOARD | REF-003-010 |
| SECTION-E_GENERAL_BODY | REF-003-011 |
| SECTION-F_FUNDS_OF_THE_KENDRA_SANGHA | REF-003-012, 013 — Funds, and their utilization/management |
| SECTION-G_ACCOUNTS_AND_AUDIT | REF-003-014 |
| SECTION-H_POWER_TO_AMEND | REF-003-015 |
| SECTION-I_DISSOLUTION | REF-003-016 |
| SECTION-J_RESOLUTIONS | REF-003-017 — Additional Resolutions, 1975 |

Each `REF-` document follows a consistent format: metadata header (ID, title,
version, status), a revision history table, a statement of source/edition/authority,
and the transcribed provision text broken into numbered subsections — these are
meant as a faithful record of the Bye-Law, not an ERP-specific interpretation or
summary.

---

## 12. Release history (`docs/releases/`)

| Version | Name | Highlights |
|---|---|---|
| v0.1.0 | Initial Setup | Repo scaffolding, Git Flow, Documentation First / Database First decisions frozen |
| v0.2.0 | Foundation Models | Foundation app, initial Person/Family/Membership models |
| v0.2.1 | Admin Setup | Django admin registration for early models |
| v0.3.0 | UI Foundation and Authentication Complete | Base layout, login page, authentication app, dashboard foundation |
| v0.4.0 | Organization Module Frozen | Organization design/ERD/business-rules/table-design docs frozen; DDL not yet implemented |
| v0.5.0 | Person Module Frozen | Person design/ERD/business-rules/table-design docs frozen |
| v0.5.1 (current stable) | Person Database Schema Complete | Full DDL + seed for foundation (id sequences, location hierarchy) and person modules |

Declared next target: **v0.6.0 — Membership Module Design** (business rules, table
design, Sangha Sevi ID strategy, lifecycle, approval workflow, DDL), matching the
README's "Current Focus" and the fact that `membership`'s Django model already
exists but has no DDL, views, or docs yet.
