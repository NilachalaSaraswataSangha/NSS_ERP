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
`DISABLE_DOCS` (disable Swagger/ReDoc), `DEBUG_MODE` (echoes `otp_debug` on
`/forgot-password` and warns at startup — never enable in production),
`DB_READ_POOL_MIN`/`DB_READ_POOL_MAX` (default `2`/`15`),
`DB_WRITE_POOL_MIN`/`DB_WRITE_POOL_MAX` (default `1`/`5`, Tier 5), and
`CSP_ENABLED`/`CSP_REPORT_ONLY`/`CSP_SCRIPT_SRC_EXTRA`/`CSP_STYLE_SRC_EXTRA` (Tier 5
Content-Security-Policy — enabled and enforcing by default; `CSP_REPORT_ONLY=true` switches
to `Content-Security-Policy-Report-Only` for rollout; the two `_EXTRA` vars take
comma-separated extra origins so adding a CDN never needs a code change — see
`api/middleware.py::build_csp()` and `docs/03_Solution/security/TIER5_SECURITY_AUDIT.md` §2.2).

**Tier 5 (Authentication + Administration) — in progress, uncommitted on
`feature/tier5-authentication-administration`, not merged/released.** On top of the above,
`api/.env` also needs `DB_WRITE_USER`/`DB_WRITE_PASSWORD` (a second, write-capable
`nss_db_writer` DB role/pool — see Database below) and `JWT_SECRET_KEY` before any
`/api/v1/auth/*`/`/api/v1/admin/*`/`/api/v1/register`/`/api/v1/admin/claims/*` endpoint will
work (`Settings.validate_auth()` raises otherwise); Tier 0-4 read-only endpoints still start up
fine without them. `database/scripts/06_setup_env.sh` (superuser) generates a working `api/.env`
for you, including a random `JWT_SECRET_KEY`. Treat every Tier 5 fact in this file as
in-progress — verify against `git status`/`git log` before assuming it's shipped.

`frontend/assets/css/tailwind.min.css` is a committed, generated artifact — a fresh clone
already has a working build, no Node.js required just to run the app. Only needed if you're
changing Tailwind/DaisyUI classes in `frontend/*.html` or `frontend/assets/js/*.js`:

```bash
npm install
npm run css:build   # one-shot rebuild
npm run css:watch   # rebuild on file change, for active frontend dev
```

## Database

Hand-written PostgreSQL DDL under `database/ddl/`, numeric folder order, executed via `psql` (no
migration tool for this track). Bootstrap sequence (full commands and rationale in
`database/scripts/README.md` and `docs/PROJECT_DOCUMENTATION.md` → Setup & running):

1. `00_create_database.sql` (superuser) — creates `nss_erp` DB + `nss_db_owner`/`nss_db_backend`
   roles (and, on the Tier 5 branch below, `nss_db_writer` too), then set their passwords via
   `ALTER ROLE ... PASSWORD`.
2. `01_extensions.sql` (superuser) — installs pgcrypto/pg_trgm/btree_gin/postgis, creates the
   `nss` schema (all tables live under `nss.*`, not `public`; `search_path` is `nss, public`).
3. `database/scripts/02_build.sh`/`.ps1` (as `nss_db_owner`) — runs all implemented DDL+seed in
   phase order: `00_bootstrap` (RBAC, 3 tables, seeded 9 roles) → `01_foundation` (12 tables,
   seeded, incl. ORGANIZATION_TYPE + unified STATUS + BLOOD_GROUP in master_data) →
   `02_organization` (1 table, seeded — type via Foundation ORGANIZATION_TYPE, status via
   unified STATUS, plus 175 real Sakha Sangha branches via `05_sakha_branches.sql`, new/
   uncommitted) → `03_person` (2 tables: `person` 28 columns, `person_address`) →
   `04_family` (6 tables: `family_group`, `family_relationship`, `family_head_history`,
   `family_transition_history`, `family_link` — the last is a graph-edge table, see
   Architecture below — plus `family_admin`, new/uncommitted, Family Admin role assignments) →
   `05_membership` (13 tables: `sangha_sevi` plus
   status/renewal/transfer/affiliation/journey/review history tables and
   `parichaya_patra`/`anumati_patra` + their history tables, plus
   `darshak_attendance_registration`, new/uncommitted, cross-Sakha Darshak attendance) →
   grants `nss_db_backend` read-only
   `SELECT` (Phase 9 — makes the separate `04_grant_backend.sql` step below redundant but
   harmless to also run) → **(new/uncommitted, Tier 5)** `06_authentication` (4 tables:
   `user_account`, `password_history`, `registration_claim`, `password_reset_token`) →
   `07_administration` (2 tables: `user_role`, `admin_scope`) → grants `nss_db_writer`
   write access on auth+admin tables only (`database/scripts/05_create_writer_role.sql`) →
   seeds a single admin superuser via `python3 scripts/bootstrap_admin.py` (not plain SQL — the
   password hash needs a runtime Argon2 hash). `01_person_master_tables.sql` is superseded (its
   data now lives in Foundation master_data) — not run.
4. `database/scripts/03_validate.sh`/`.ps1` — row-count/FK integrity checks. **Known stale even
   before Tier 5:** hardcodes `organization`/`person`/`master_data` row counts from an earlier
   snapshot, and there are no Family/Membership/Authentication/Administration checks at all —
   expect this script to report false failures until it's updated.
5. `database/scripts/04_grant_backend.sql` (as `nss_db_owner`) — grants `nss_db_backend`
   read-only `SELECT`, needed before the API can connect. Already run as `02_build`'s Phase 9;
   this manual step is only needed if you skip the full build script.

**Tier 5 (Authentication + Administration) — in progress, uncommitted on
`feature/tier5-authentication-administration`, not merged to `develop`/`main`, no release tag.**
Adds a second, write-capable PostgreSQL role/pool: `nss_db_writer` (grants only `INSERT`/
`UPDATE` on the new auth+admin tables, `SELECT` on everything else — see
`database/scripts/05_create_writer_role.sql`). New DDL under `database/ddl/06_authentication/`
(4 tables) and `database/ddl/07_administration/` (2 tables), plus `family_admin` and
`darshak_attendance_registration` added to the already-implemented Family/Membership modules
(see above), and `nss.system_event_log` added to Foundation
(`database/ddl/01_foundation/14_system_event_log.sql`) with a DB-level `fn_audit_trigger()`
(`15_audit_trigger.sql`) attached via a `DO $$` loop to every `nss.*` table, firing on every
INSERT/UPDATE/DELETE and driven by session variables the app sets via
`api/helpers.py::log_audit()` — **9 new tables total**. `database/scripts/06_setup_env.sh` (new)
sets passwords on all three PostgreSQL roles and generates a working `api/.env` (incl. a random
`JWT_SECRET_KEY`) in one step. **`database/scripts/README.md`'s Phase 13 description is now
fixed** (was previously wrong — referenced nonexistent seed files and fictional
`Admin@123`/"Ramesh Mishra" credentials): it now correctly describes `scripts/bootstrap_admin.py`
against `database/seed/04_admin/01_admin_bootstrap.sql`, default login `SS1`/`P1`, password
`NSSAdmin1`, matching the actual `02_build.sh` behavior.

**Every Tier 4 "verification"/demo seed file has been deleted on this branch** —
`database/seed/02_organization/04_tier4_verification_orgs.sql`,
`database/seed/03_person/02_tier4_verification_persons.sql`,
`database/seed/04_family/01_tier4_verification_family.sql` +
`02_tier4_verification_family_links.sql`,
`database/seed/05_membership/01_tier4_verification_membership.sql`,
`database/seed/99_extended_test_data.sql`, and `database/seed/99_fix_memberships.sql` are all
gone, along with **`database/migrations/` in its entirety** (`README.md`,
`add_performance_indexes.sql`, `update_darshaka.sql`). A fresh build now produces a database
with **zero demo Person/Family/Membership data** — real data comes from the registration/
approval flow (`POST /api/v1/register` → Sakha-admin `POST /api/v1/admin/claims/{pk}/approve`)
or the single seeded admin superuser above. `database/fixes/` was a new, narrow successor to
`migrations/` for one-off data-repair scripts (not wired into any build script) — its only file,
`fix_missing_ghost_transitions.sql`, hardcoded UUIDs from the now-deleted
demo seed data and had no effect on a fresh build; it (and the whole `fixes/` folder) has since
been deleted as verifiably obsolete — `family.py`'s auto-transfer logic already covers the case
it was patching, and the seed rows its UUIDs targeted no longer exist.

**`tests/conftest.py` was rewritten** to hold one session-scoped `nss_db_writer` connection for
the whole pytest run, wrapping each test module in a `SAVEPOINT` rolled back at teardown (both
`get_connection`/`get_write_connection` are overridden to yield that connection) — this is what
lets the suite run against the now-seed-less database. See Tests & lint below.

**Historical note (v0.10.4, now superseded by the Tier 5 branch above):**
`database/migrations/` used to hold `update_darshaka.sql` (a one-off `PROBATIONARY` display-name
fix) and `add_performance_indexes.sql` (4 composite partial indexes for the FAM-036
majority-rule CTE hot path, wired into `02_build.sh` as "Phase 8b" — a deliberate exception to
the "migrations are never auto-run" convention, flagged as an inconsistency at the time). Both
files are gone: `update_darshaka.sql` is superseded by a corrected seed value, and the
performance indexes are now baked directly into `family_relationship`/`sangha_sevi`/
`membership_sakha_affiliation`'s own DDL files (search for `family_majority` in
`database/ddl/`). `render.yaml`'s `--workers 2`, `api/database.py`'s `minconn` bump, and the
frontend's non-blocking fetches from that release are all still in place. `database/fixes/`
(the narrow, never-wired-in successor to `migrations/` for one-off data-repair scripts) has
since been deleted outright — its one script was verifiably obsolete (see Database above).

`.sh`/`.ps1` script pairs must stay operationally identical — shell-mechanics wrappers only,
never a place for platform-specific logic.

**Role naming convention:** `nss_db_*` = PostgreSQL infrastructure roles (lowercase);
`NSS_ERP_*` = application RBAC roles in `role_master` (uppercase) — separate security
boundaries.

**Deployment (Render.com):** `render.yaml` + `render_build.sh` (repo root) duplicate the same
DDL/seed sequence directly via `psql` as an idempotent Render build step — keep in sync with
`02_build.sh` if phase order changes. Points at an external Neon.dev Postgres instance (no
managed DB declared in `render.yaml` itself). Not yet run in production. **Unverified risk (new,
uncommitted):** `render_build.sh` now runs `npm install`/`npx tailwindcss` as its first step, but
`render.yaml` declares `runtime: python` — Node.js availability in that runtime is untested; see
`docs/03_Solution/architecture/DEPLOYMENT_PROCEDURE.md` Step 2 for the full risk and fallback
options.

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
- `GET /api/v1/bootstrap/roles` — 9 frozen roles
- `GET /api/v1/bootstrap/permissions` — was empty by design through Tier 4; **now returns real
  rows on the Tier 5 branch (in progress, uncommitted)** since `permission_master` is seeded
- `GET /api/v1/bootstrap/roles/{role_pk}/permissions` — same: no longer empty for roles that
  have mappings in `role_permission`

Tier 1 endpoints (`api/routers/foundation.py` — 23 endpoints across 11 tables under
`/api/v1/foundation`; **now gated by `Depends(require_permission("FOUNDATION_VIEW"))` on the
Tier 5 branch, in progress** — was read-only/no-auth through Tier 4, JWT + `FOUNDATION_VIEW`
required now): master data (`/categories`, `/master-data`), system config (`/settings`,
`/sequences` — excludes `current_value`), geography (`/countries`, `/states`, `/districts`,
`/cities`, `/postal-codes`, `/postal-code-mappings`), and runtime (`/documents`). **17 of the 23
are these reads; the other 6 are new write endpoints (in progress, uncommitted) gated by a
separate `FOUNDATION_MANAGE` permission and `get_write_connection`:** `POST`/`PATCH
/master-data`, `POST`/`PATCH /settings`, `POST`/`PATCH /sequences` (add/edit a master-data
value, system setting, or ID sequence respectively; each logs via `log_audit()`).
`field_change_log` is deliberately still not exposed via this router (`/api/v1/foundation/
change-log` does not exist, enforced by `tests/api/test_foundation.py::TestChangeLogNotExposed`)
— audit-trail access instead lives behind its own `AUDIT_VIEW`-gated router, see Tier 5 Audit
below. Full contract: `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` (not yet updated for the
permission gate or the 6 write endpoints).

Tier 2 endpoints (`api/routers/organization.py` — 7 endpoints under `/api/v1/organization`;
**now gated by `require_permission("ORGANIZATION_VIEW")` on the Tier 5 branch, in progress**):
reference data (`/types`, `/statuses`), organization records
(`/organizations` with optional `type_code`/`status_code` filters + `limit`/`offset` pagination,
`/organizations/{organization_pk}`,
`/organizations/{organization_pk}/children`), children-stats (`/organizations/{organization_pk}/children-stats`
— aggregate family/member/person counts per direct child, recursing through descendant Sakhas
and applying the same FAM-036 majority-rule "effective Sakha" computation Family's
`/sakha-alignment` implements independently — the two are not factored into a shared SQL
helper, a real duplication; see Gotchas), and the self-referencing tree
(`/hierarchy` with `limit`/`offset` pagination and CTE depth guard at 10, via a `WITH RECURSIVE` CTE
— note `/children-stats`'s own recursive CTE has **no** depth-cap guard, unlike `/hierarchy`).
Full contract: `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md` (not yet updated for the
permission gate).

Tier 3 endpoints (`api/routers/person.py` — 4 endpoints under `/api/v1/person`; **now gated by
`require_permission("PERSON_VIEW")` on the Tier 5 branch, in progress**): person list with
filters and `limit`/`offset` pagination
(`/persons?gender_code=&marital_status_code=&blood_group_code=&limit=&offset=`),
person detail (`/persons/{person_pk}`), person addresses
(`/persons/{person_pk}/addresses`), and trigram search (`/search?q=`).
Master-data FKs (gender, marital status, blood group, emergency relationship, address type)
are resolved via JOINs. Sensitive fields (aadhaar_encrypted, aadhaar_hash) are **never**
returned — only aadhaar_last4 for masked display. (A separate `PERSON_VIEW_SENSITIVE`
permission is seeded but not yet wired to any endpoint — Aadhaar masking above is
unconditional regardless of permission.)

Tier 4 endpoints — Family (`api/routers/family.py`) — originally 7 read-only, no-auth
endpoints under `/api/v1/family`: family group list with filters + pagination, family group
detail, family group members, family group head history, plus 3 newer endpoints —
`/families/{pk}/graph?viewer_person_pk=`
(dynamic relationship-label computation via BFS graph traversal over `nss.family_link` edges,
implemented in the new `api/services/family_graph.py` — the first file in a new `api/services/`
layer, distinct from `routers`/`schemas`; test coverage added on the Tier 5 branch, see below),
`/families/{pk}/sakha-alignment` (FAM-036 majority-rule "effective Sakha" computation — `is_aligned`
is hardcoded `True` by design, since the returned Sakha is always the computed majority; per-member
`is_home_sakha` flags still surface real mismatches), and `/person/{person_pk}/membership-summary`
(bridges family context to membership context for a UI panel; **still no test coverage**).
Full contract: `docs/03_Solution/api/API_CONTRACT.md` (documents the original 7; not yet updated
for the 9 below). **Unlike a blanket `require_permission` gate, all 16 `family.py` endpoints (the
7 original reads and the 9 Tier 5 writes below) are now gated by `get_current_user` plus an
ownership check (in progress, uncommitted)** — a person reaches their own family through their
`family_relationship`/`family_admin` row (`_require_family_view`/`_require_family_manage`/
`_require_family_head` helpers), with `FAMILY_VIEW`/`FAMILY_MANAGE` as the admin override for
browsing families the caller doesn't belong to; `list_families` (browse-all) requires
`FAMILY_VIEW` outright. `database/seed/00_bootstrap/01_permission_master.sql`'s `FAMILY_VIEW`
permission is used this way, not via a blanket per-route gate like Foundation/Organization/
Person/Membership — this is a deliberate design choice (see the router's own module docstring),
not a gap. `bootstrap.py`'s 4 Tier 0 endpoints are now the only unauthenticated routes left in
the whole API.

**`family.py` grew 9 more endpoints on the Tier 5 branch (in progress, uncommitted) — 16
total, module docstring updated to say "Tier 4 read-only + Tier 5 write endpoints":**
`GET /person/{pk}/families` (families a person belongs to); `POST /families` (create a family —
authenticated user becomes founding member + head, auto-generates the next `family_id`, uses the
new `SELF` `RELATIONSHIP_TYPE` value); `POST /families/{pk}/members` (add a member — requester
must be head or family admin, or hold `FAMILY_MANAGE`); `DELETE /families/{pk}/members` (remove a
member — same rule, FAM-048); `POST /families/{pk}/links` (create `family_link`
graph edges — same rule); `GET/POST/DELETE /families/{pk}/admins` (list/assign/revoke
`family_admin` rows — assign/revoke require the requester to be the current head or hold
`FAMILY_MANAGE`, FAM-046/FAM-050); and
`POST /families/{pk}/transfer-head` (head-only). All 9 write endpoints use
`get_write_connection` (`nss_db_writer`) on top of the ownership model above. **Test coverage
added on the Tier 5 branch (in progress, uncommitted):** a new
`tests/api/test_family_ownership.py` (20 tests) specifically exercises the ownership/ role-less-
member path — `/graph`, add/remove member, admin assign/revoke, transfer-head — as a genuine
role-less JWT holder rather than through an admin token that would bypass the ownership check;
`tests/api/test_family.py` (52 tests, admin-token path) still covers only the original 7 reads
plus org-admin/Sakha-alignment scenarios.

Tier 4 endpoints — Membership (`api/routers/membership.py` — 7 endpoints under
`/api/v1/membership`; **now gated by `require_permission("MEMBERSHIP_VIEW")` on the Tier 5
branch, in progress**): member list with filters + pagination,
member detail, member Sakha affiliations, member Parichaya Patra records, member journey events,
member search (7-field: sangha_sevi_id, person_id, local_sakha_erp_id, name trigram 0.45,
mobile, email, Kendra number), and person search (4-field: person_id, name trigram 0.45,
mobile, email). Trigram email-split: `re.split(r'[.@]', q)[0]` for trigram params to prevent
false positives. Search auto-selects single result. Inline detail panel in search tabs.
Full contract: `docs/03_Solution/api/API_CONTRACT.md` (46 endpoints total, not yet updated for
the permission gate);
`docs/03_Solution/api/PERSON_API_CONTRACT.md`. Repeated inline 404-existence checks were
recently replaced by a shared `require_entity()` helper in `api/helpers.py` (behavior
unchanged).

Swagger UI at `/docs` (disable via `DISABLE_DOCS=true` in `api/.env`). **The six standalone
Tier 0-4 verification pages/routes (`/bootstrap`, `/foundation`, `/organization`, `/person`,
`/family`, `/membership` and their `frontend/*.html`/`assets/js/*.js` files) have been retired
on the Tier 5 branch (in progress, uncommitted)** — see the "Retired standalone verification
pages" comment in `api/main.py`. Their functionality now lives behind authentication inside
`admin.html` (Reference Data, Organization Hierarchy, Person Directory, Member Directory,
Roles & System Settings, Registration Approvals tabs) and `dashboard.html` (Family tab + org
family browser). `GET /` 302-redirects to `/login`. The API connects as `nss_db_backend`
(SELECT-only) for the read endpoints above; Tier 0 (`bootstrap.py`, 4 endpoints) is the only
unauthenticated router left — `family.py`'s ownership model (see above) means even its 7
original GET endpoints now require a JWT.

**Tier 5 endpoints (Authentication + Administration) — in progress, uncommitted on
`feature/tier5-authentication-administration`, not merged/released.** Connect via a second,
write-capable `nss_db_writer` pool (`api/database.py::get_write_connection`); need
`DB_WRITE_USER`/`DB_WRITE_PASSWORD`/`JWT_SECRET_KEY` in `api/.env` (see Setup above).
- `api/routers/auth.py`, prefix `/api/v1/auth`, 8 endpoints: `POST /login` (login_id = Sangha
  Sevi ID or Person ID, case-insensitive; Argon2; 5-attempt/30s lockout), `POST /refresh`,
  `POST /logout` (stateless — no server-side revocation), `POST /change-password`,
  `POST /forgot-password` (6-digit OTP, rate-limited 3/hour, anti-enumeration generic response,
  `otp_debug` echoed only when `DEBUG_MODE=true`), `POST /reset-password`, `GET /me`, and
  `PATCH /profile`.
- `api/routers/admin.py`, prefix `/api/v1/admin`, 23 endpoints: user CRUD (`GET/POST /users`,
  `GET /users/{pk}`, `GET /persons/check-contact` advisory duplicate lookup,
  `POST /users/{pk}/reset-password`, `PATCH /users/{pk}/status`,
  `DELETE /users/{pk}`), role assignment (`GET/POST /users/{pk}/roles`,
  `DELETE /users/{pk}/roles/{user_role_pk}`), `POST /persons` (admin-created person, no
  account), sangha-sevi provisioning (`POST /sangha-sevi`, `GET /sangha-sevi/check/{person_pk}`,
  `POST /sangha-sevi/check-batch`), `GET /dashboard-stats`, and org management (`GET/POST
  /organizations`, `GET /organizations/kumari-sevak-sakha-options` (ORG-BR-101/102),
  `GET /sakha-scope-options` (ORG-BR-103), `GET /organizations/code-availability`,
  `GET /organizations/next-code` (sequence-driven code preview),
  `PATCH /organizations/{pk}/short-code`, `PATCH /organizations/{pk}` —
  scope-gated). All endpoints require `require_permission(...)`/`require_any_permission(...)`
  (`api/dependencies/rbac.py`). **`nss.permission_master`/`nss.role_permission` are now seeded**
  (`database/seed/00_bootstrap/01_permission_master.sql`/`03_role_permission.sql` — no longer
  empty; `FOUNDATION_VIEW`/`ORGANIZATION_VIEW`/`PERSON_VIEW`/`PERSON_VIEW_SENSITIVE`/
  `FAMILY_VIEW`/`MEMBERSHIP_VIEW`/`AUDIT_VIEW` plus the admin/user-management permission set are
  all mapped to roles), so these endpoints no longer blanket-403 — this supersedes the "every
  role gets 403 until the catalogue is frozen" caveat that applied earlier in this branch's
  development.
- `api/routers/audit.py`, prefix `/api/v1/audit`, 1 endpoint: `GET /change-log` — filterable
  (`table_name`/`record_pk`/`field_name`/`changed_by_sangha_sevi_pk`/date range), paginated
  read access to `nss.field_change_log`, gated by a dedicated `AUDIT_VIEW` permission (seeded to
  `NSS_ERP_ADMIN`/`NSS_ERP_KENDRA_ADMIN`/`NSS_ERP_AUDITOR`). Connects via the read-only
  `nss_db_backend` pool (`get_connection`, not `get_write_connection` — it never writes; the
  change log is populated by the DB-level `fn_audit_trigger()`, see Architecture below). This is
  the authenticated counterpart to Tier 1's deliberately-unexposed `field_change_log` — resolves
  the Deferred Items item that previously said this data had "no router change... yet."
- `api/routers/registration.py`, prefix `/api/v1/register`: `POST ""` — self-registration
  creates `person` + `user_account(PENDING_APPROVAL)` + optional `registration_claim`; **no
  `sangha_sevi` is created here** — that only happens on admin approval. Also
  `GET /check-duplicate` (pre-submit contact-uniqueness check).
- `api/routers/claim_approval.py`, prefix `/api/v1/admin/claims`: `GET ""` (list, scoped to the
  admin's `admin_scope` orgs unless NSS-WIDE), `GET/PATCH /{pk}`, `POST /{pk}/approve` (creates
  `sangha_sevi` + `membership_sakha_affiliation`, activates the account), `POST /{pk}/reject`.

## Frontend

`frontend/` — **on the Tier 5 branch (in progress, uncommitted), the six original Tier 0-4
standalone verification pages (`index.html`/`foundation.html`/`organization.html`/
`person.html`/`family.html`/`membership.html` and their per-page JS) have been deleted
entirely**, not just had their routes retired — see the "Retired standalone verification
pages" comment in `api/main.py`. Their functionality was folded into the two Tier 5 dashboard
pages instead: `admin.html` (Reference Data, Organization Hierarchy, Person Directory, Member
Directory, Roles & System Settings, and a Registration Approvals tab — see claim-approval note
below) and `dashboard.html` (a Family tab, including the family-tree visualization that used to
live in `family.html`, consuming `/graph` and `/sakha-alignment`). Served as static files by
FastAPI: Tailwind CSS + DaisyUI (pre-built via Tailwind CLI — no longer CDN, see below),
Alpine.js (CDN), vanilla `fetch()`. No React/Vue/Angular, no Django templates.
The 4 remaining pages (`login.html`, `register.html`, `dashboard.html`, `admin.html`) still
share `assets/js/nss-config.js` (display-name overrides, e.g. `PROBATIONARY` → "Darshaka";
badge-class lookup maps; document-visibility rules) and `assets/css/badges.css`
(every `badge-status-*`/`badge-type-*`/`badge-aff-*`/`badge-gender-*` class) — pages must NOT
redefine these classes locally in inline `<style>` blocks. Two new shared stylesheets,
`assets/css/nss-layout.css` and `assets/css/nss-datepicker.css`, back the `nss-layout.js`/
`nss-datepicker.js` helpers below but have no entry yet in `frontend/README.md`'s file
reference. See `frontend/README.md` for the full file/function reference.

**Tier 5 pages — in progress, uncommitted on `feature/tier5-authentication-administration`, now
documented in `frontend/README.md`:** `login.html` (`/login`, root `/` redirects here),
`register.html` (`/register` — self-registration form, consumes `POST /api/v1/register` plus
the new `05_sakha_branches.sql` seed for the Sakha dropdown), `dashboard.html` (`/dashboard` —
member dashboard, see `docs/03_Solution/architecture/MEMBER_DASHBOARD.md`), and `admin.html`
(`/admin` — the actual admin dashboard, now the sole home for the Tier 0-4 verification
functionality since those six standalone pages were deleted — see Frontend intro above).
Backing JS:
`login.js`, `register.js`, `dashboard.js`, `admin.js`, plus shared helpers `auth.js` (`NSSAuth`
— JWT storage/refresh + authenticated `fetch()` wrapper), `nss-layout.js` (`NSSLayout` —
sidebar/topbar mixin shared by `admin.html`/`dashboard.html`), and
`nss-datepicker.js`/`nss-dialog.js`/`nss-location.js`. **`claim-approval.html` was never built
as a standalone page — this is no longer an open gap.**
The Sakha-admin review queue for `registration_claim` rows (`api/routers/claim_approval.py`)
shipped as a "Registration Approvals" tab inside `admin.html`/`admin.js` instead (list w/
status filter + pagination, detail view, inline edit, pending-count sidebar badge,
`canApproveClaims` permission gate, and integration into the Person Directory tab — a pending
claim blocks Sangha-Sevi creation for that person and shows a "View Claim" jump-link). A
`forgot-password.html` route is wired in `api/main.py` (guarded by `if _forgot_password_path.
is_file()`) but **that file still doesn't exist** — that route remains never registered.

**CSS build (released, see `frontend/README.md` for the committed-artifact workflow):** Tailwind CSS + DaisyUI moved
from CDN (`<script src="https://cdn.tailwindcss.com">` + DaisyUI CDN `<link>`) to a pre-built,
tree-shaken, minified stylesheet — `frontend/assets/css/tailwind.min.css` (~72 KB), generated
from `frontend/assets/css/tailwind-input.css` via `tailwind.config.js` and the root
`package.json` (`devDependencies`: `tailwindcss`, `daisyui`; `npm run css:build` / `css:watch`).
All HTML pages `<link>` the built file instead of loading the CDN scripts; Alpine.js stays
on CDN (unchanged). `render_build.sh` runs `npm install` + `npx tailwindcss ... --minify` before
the Python dependency step. **If you edit any Tailwind/DaisyUI class in `frontend/*.html` or
`frontend/assets/js/*.js`, you must re-run `npm run css:build` locally** (or the change won't
appear — `tailwind.min.css` is a committed, generated artifact, not rebuilt automatically on
page load like the old CDN JIT compiler was). `node_modules/` is gitignored;
`package-lock.json`/`tailwind.min.css`/`tailwind-input.css` are committed.

## Tests & lint

pytest is configured (`pytest.ini` at repo root). Run from the repository root:

```
pytest                    # all tests (api + db + ui + security)
pytest -m integration     # tests/api/ + tests/db/ + tests/security/
pytest -m ui               # tests/ui/ (Playwright browser tests)
pytest tests/api/test_organization.py                     # one file
pytest tests/api/test_bootstrap.py::TestHealth::test_health_returns_ok  # one test
```

**The Tier 5 branch reorganized `tests/` from a flat `tests/test_*.py` package into four
subdirectories**: `tests/api/` (16 files, TestClient/integration tests against the live API),
`tests/db/` (`test_data_integrity.py`, cross-module DB smoke tests), `tests/ui/` (13 files — a
brand-new Playwright browser-test suite covering login/register/dashboard/admin flows, not a
rename of anything), and `tests/security/` (6 files, added after the reorg above — a dedicated
security-assertion suite; see below). `pytest.ini` declares `integration`/`ui`/`db` markers
(no separate marker was added for `tests/security/` — those files use `pytest.mark.integration`
same as `tests/api/`), and `requirements.txt` gained `pytest-playwright`/`playwright`/
`pytest-base-url`/`greenlet` (plus `argon2-cffi`/`PyJWT` for Tier 5 auth itself).

Every `tests/api/`/`tests/db/`/`tests/security/` test is an integration test — nothing is
mocked — so a
bootstrapped local database and `api/.env` are required first; `tests/ui/` additionally needs
Playwright browsers installed and a running app. **`tests/conftest.py` was rewritten on the
Tier 5 branch**: it now holds one session-scoped `nss_db_writer` connection for the whole run,
wraps each test *module* in a `SAVEPOINT` rolled back at teardown, and overrides both
`get_connection`/`get_write_connection` to yield that connection — this is what lets the suite
pass against a database with **zero pre-seeded demo data** (all Tier 4 verification seed files
were deleted on this branch, see Database above). It has since gained session-scoped
`admin_view_token`/`authed_client`/`anon_client` fixtures and an autouse `_reset_rate_limiter`
fixture, used by the newer permission-gated tests below.

**`tests/security/` is new** (added after the initial `tests/api`/`tests/db`/`tests/ui` reorg):
`test_admin_security.py` (17), `test_audit_security.py` (4), `test_auth_security.py` (4),
`test_forgot_password_security.py` (6), `test_registration_security.py` (3), and
`test_security_headers.py` (24) — **58 tests**. Mostly the auth-gating/401/403/RBAC assertions
extracted out of `tests/api/test_admin.py`, `test_auth.py`, `test_registration.py`,
`test_forgot_password.py`, plus (`test_security_headers.py`) genuinely new coverage for CSP,
rate limiting, CORS, and `DEBUG_MODE`. The old flat `tests/api/test_security.py` (previously 8
tests) no longer exists — fully absorbed into this directory.

Current per-file counts (AST-counted `test_*` functions, replacing every figure below —
extraction into `tests/security/` above lowered several files' own counts, this is not lost
coverage):
`tests/api/test_bootstrap.py` (9), `test_foundation.py` (45), `test_organization.py` (58,
incl. `TestChildrenStats`), `test_person.py` (55), `test_family.py`
(52, incl. `TestOrgAdminFamilyFilter`/`TestSakhaAlignment` — admin-token path only, still no
coverage for `/person/{pk}/membership-summary`), `test_family_ownership.py` (20, new —
role-less-JWT ownership path: `/graph`, add/remove member, admin assign/revoke, transfer-head;
see the Family section above), `test_membership.py` (94), `test_auth.py` (16), `test_admin.py`
(72), `test_registration.py` (14), `test_forgot_password.py` (6), `test_sakha_branches.py`
(33), `test_claim_approval.py` (11, covers GET-detail/PATCH-edit/scope-enforcement for
`claim_approval.py`, previously only indirectly covered), `test_audit.py` (4, covers the
`audit.py` router), `test_error_messages.py` (15, new — covers `api/error_handlers.py`'s
human-readable validation/integrity-error messages), and `test_sorting.py` (14, new — covers
the shared column-sort-whitelist helper used by every router's `sort_by`/`sort_dir` params) —
**518 tests in
`tests/api/`** across 16 files. Plus `tests/db/test_data_integrity.py` (23, unchanged) and `tests/security/`
(58, see above): **599 non-UI tests**. `tests/ui/` adds **134**
more across 13 Playwright files, unchanged (`dashboard` alone is 52). **733 tests total**
(AST-counted `test_*` functions — corrects a previously-stated "620", which predated
`test_error_messages.py`/`test_family_ownership.py`/`test_sorting.py` and the growth of
`test_admin.py` (38→72), `test_person.py` (41→55), and `test_membership.py` (78→94) as their
routers gained endpoints). The `test_page_loads_tailwind`/
`test_page_loads_daisyui` assertions that used to live in all 6 Tier 0-4 API test files
**no longer exist** — removed along with the deleted verification pages they tested (see
Frontend below), not a regression. `test_kumari_transition_has_event` and `TestChildrenStats`
still
`pytest.skip()` gracefully against the seed-less database. See `tests/README.md`. No lint/format
tooling is configured yet — don't add one unilaterally.

## Architecture

**Repository layout:**
```
NSS_ERP/
├── api/                    FastAPI Tier 0-5; every Tier 1-4 GET endpoint except bootstrap.py's
│   │                         is now permission-gated (see Running the FastAPI API above) —
│   │                         family.py uses an ownership model instead of a blanket permission,
│   │                         but is fully authenticated too; only bootstrap.py's 4 endpoints
│   │                         remain unauthenticated
│   ├── helpers.py          Shared cursor→Pydantic helpers + pagination constants + next_id()/
│   │                         resolve_or_create_city_village()/get_active_status_pk()/
│   │                         log_audit() (writes nss.system_event_log)/require_entity() + more
│   │                         — see api/README.md for the full function list
│   ├── middleware.py       Security headers + Cache-Control scoping + Content-Security-Policy
│   │                         (build_csp(), Tier 5)
│   ├── dependencies/       (Tier 5, in progress) auth.py (get_current_user/get_optional_user),
│   │                         rbac.py (require_permission/require_any_permission)
│   ├── routers/            bootstrap.py (Tier 0, unauthenticated), foundation.py/organization.py/
│   │                         person.py/membership.py (Tiers 1-4, permission-gated on this
│   │                         branch), family.py (Tier 4, 16 endpoints — ownership-based auth on
│   │                         all of them, not just the 9 Tier 5 writes), auth.py/admin.py/registration.py/
│   │                         claim_approval.py/audit.py (Tier 5, in progress)
│   ├── schemas/            bootstrap.py, foundation.py, organization.py, person.py, family.py,
│   │                         membership.py, auth.py, admin.py, audit.py (last three: Tier 5,
│   │                         in progress) — Pydantic response models
│   └── services/           family_graph.py — BFS graph-traversal relationship computation;
│                             auth_service.py/rbac_service.py (Tier 5, in progress) — Argon2/JWT,
│                             UserContext + permission/scope loading
├── frontend/               Web UI (Tailwind/DaisyUI pre-built + Alpine.js CDN, served by FastAPI)
│   │                         — the six Tier 0-4 standalone verification pages were deleted on
│   │                         this branch (see Frontend section above); only login/register/
│   │                         dashboard/admin.html remain
│   └── assets/             js/nss-config.js + css/badges.css + css/tailwind.min.css (generated,
│                             see package.json) — shared config/badge-styles/CSS for all pages;
│                             Tier 5 (in progress) adds login.js/register.js/dashboard.js/
│                             admin.js + nss-datepicker.js/nss-dialog.js/nss-location.js/
│                             nss-layout.js helpers + nss-layout.css/nss-datepicker.css
├── package.json            CSS build tooling only (Tailwind CLI + DaisyUI devDependencies) —
│                             not a general Node.js app; `npm run css:build`/`css:watch`
├── tailwind.config.js       Tailwind content globs (`frontend/**/*.html`, `frontend/assets/js/**/*.js`) + DaisyUI plugin
├── database/               Hand-written PostgreSQL DDL + seed + scripts
│   ├── ddl/                Table definitions (00_bootstrap, 01_foundation, 02_organization,
│   │                         03_person, 04_family, 05_membership, plus 06_authentication/
│   │                         07_administration — Tier 5, in progress)
│   ├── seed/                Seed data (mirrors ddl/ folder order); all Tier 4 demo/verification
│   │                         seed files and the standalone 99_*.sql scripts were deleted on the
│   │                         Tier 5 branch — a fresh build now seeds zero demo Person/Family/
│   │                         Membership rows, only 175 real Sakha branches + one admin superuser
│   │                         (`04_admin/`, Tier 5, in progress); `00_bootstrap/
│   │                         01_permission_master.sql`/`03_role_permission.sql` are now
│   │                         populated (no longer empty placeholders)
│   ├── (no `fixes/` folder anymore — its one narrow data-repair script was deleted as
│   │                         verifiably obsolete; see Database above)
│   └── scripts/             DB creation, build, validate, grant scripts; Tier 5 (in progress)
│                             adds 05_create_writer_role.sql, 06_setup_env.sh
├── scripts/                 (Tier 5, in progress) bootstrap_admin.py — seeds the admin
│                             superuser with a runtime-generated Argon2 hash
├── tests/                  pytest suite, reorganized (Tier 5) into tests/api/ (16 files:
│                             test_bootstrap.py, test_foundation.py, test_organization.py,
│                             test_person.py, test_family.py, test_family_ownership.py,
│                             test_membership.py, test_auth.py, test_admin.py,
│                             test_registration.py, test_forgot_password.py,
│                             test_sakha_branches.py, test_claim_approval.py, test_audit.py,
│                             test_error_messages.py, test_sorting.py),
│                             tests/db/ (test_data_integrity.py), tests/ui/ (13 Playwright
│                             browser-test files), and tests/security/ (6 files, added after the
│                             initial reorg — see Tests & lint above)
├── docs/                   All project documentation
├── BY-LAW/                 Source reference material
└── NSS LOGO/               Branding assets
```

`backend/` (the earlier Django prototype) was fully removed once the FastAPI direction was
adopted — it no longer exists on disk, only in Git history. `api/` (FastAPI, raw
psycopg2, no ORM/SQLAlchemy/migration tool) is the only API layer. Tier 5 (JWT auth + RBAC) is
now in progress but **uncommitted, not merged/released** on
`feature/tier5-authentication-administration` (see Setup/Database/Running sections above for
the full detail; don't treat it as shipped) — but unlike earlier in this branch's life, **most
Tier 1-4 GET endpoints are no longer unauthenticated either**: `foundation.py`/`organization.py`/
`person.py`/`membership.py` are now gated by `require_permission("<MODULE>_VIEW")`, and
`family.py` is gated by an ownership check (see Tier 4 Family section above) rather than a
blanket permission. Only
`bootstrap.py`'s 4 Tier 0 endpoints remain open, no-auth routes. Security middleware
(`api/middleware.py`) provides security headers (X-Content-Type-Options, X-Frame-Options,
Referrer-Policy, Permissions-Policy), Cache-Control scoping (`no-store` on `/api/*`;
`public, max-age=86400, must-revalidate` on `/assets/*`), CORS
(configurable via `CORS_ORIGINS`; `allow_methods` widened from `["GET"]` to `["GET", "POST",
"PATCH", "DELETE"]` to support Tier 5 writes), rate limiting (SlowAPIMiddleware, default
60/minute), and — new on this branch — a Content-Security-Policy (`build_csp()`, configurable
via `CSP_ENABLED`/`CSP_REPORT_ONLY`/`CSP_SCRIPT_SRC_EXTRA`/`CSP_STYLE_SRC_EXTRA`, see Setup
above; `script-src` omits `'unsafe-inline'` — all inline event handlers were removed from the
frontend rather than nonced, see `docs/03_Solution/security/TIER5_SECURITY_AUDIT.md` §2.2 A2).
All of the above is now verified by `tests/security/test_security_headers.py` (the old flat
`tests/test_security.py`/`tests/api/test_security.py` no longer exists — see Tests & lint
above).
Note: Tier 5's write endpoints (`family.py`'s 9, `auth.py`, `admin.py`, `registration.py`,
`claim_approval.py`) add their *own* JWT+RBAC layer via `api/dependencies/`, layered on top of,
not replacing, this middleware.

**DB naming (SQL DDL track):** tables `snake_case`; internal PK suffix `_pk`; FKs reference
internal PKs, never business IDs; business identifiers use `_id` for entity identifiers
(`person_id`, `organization_id`, `family_group_id`, `sangha_sevi_id`) and `_code` for
Foundation/reference-data codes (`category_code`, `value_code`, `organization_type_code`).
**As of Tier 4, business-identifier examples/docs use unpadded sequence values** (`P1`, `SS1`,
`SKH1`, `F1` — not `P00000001`) — `id_sequence_master.padding_length`'s CHECK constraint was
loosened to allow `0` for this. **ID generation is now actually wired up** (in progress, on the
Tier 5 branch): `api/helpers.py::next_id(cur, sequence_code)` does an atomic `UPDATE ...
RETURNING` against `id_sequence_master` and is used by `api/routers/registration.py`,
`api/routers/admin.py`, and `api/routers/claim_approval.py` for `PERSON`/`SANGHA_SEVI`/
org-type sequences — resolving the previous "no function/trigger/API code does this yet" gap
(see `docs/PROJECT_DOCUMENTATION.md` → Key Workflow #3, itself now stale and due for an update).
Audit columns:
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

## Deferred Items (TODO)

Items explicitly deferred to later tiers. Do not implement these until their target tier.

| Item | Target Tier | Reason | Affects |
|------|-------------|--------|---------|
| Email/phone/mobile format validation (Organization) | Tier 5 | Tiers 0–2 are read-only; no write endpoints exist yet | `nss.organization` — add CHECK constraints for `phone_number`, `mobile_number`, `email`, `org_email`, `website_url`, `org_website_url`, `youtube_channel_url`, `org_youtube_channel_url` |
| Mobile OTP verification | Tier 5 (Authentication) | Contact verification is an authentication concern — still not implemented; the Tier 5 `password_reset_token` OTP (in progress) is a *password-reset* mechanism, not mobile/email verification, and doesn't resolve this item | `nss.person` — may need `is_mobile_verified BOOLEAN` column |
| Email confirmation | Tier 5 (Authentication) | Contact verification is an authentication concern — still not implemented | `nss.person` — may need `is_email_verified BOOLEAN` column |
| President/governance role linkage | Tier 6 (Governance) | Requires `sangha_sevi` table + role assignment model | Governance module tables |
| ~~`field_change_log` API exposure~~ | ~~Tier 5 (Authentication)~~ | **Fixed (uncommitted):** exposed via a new, dedicated `api/routers/audit.py` (`GET /api/v1/audit/change-log`, gated by `AUDIT_VIEW`) — not via `foundation.py` as this row originally anticipated; `/api/v1/foundation/change-log` deliberately still doesn't exist | `api/routers/audit.py` |
| ~~`nss_db_writer` role + write grants~~ | ~~Tier 5~~ | **In progress (uncommitted):** `database/scripts/05_create_writer_role.sql` + `api/database.py::get_write_pool()` implement this on `feature/tier5-authentication-administration` — not yet merged/released, but no longer literally undone | `database/scripts/05_create_writer_role.sql` |
| i18n / multi-language support | New feature branch | `language_master` + `translation` tables; Odia/Hindi priority, English default; DB stays English-only | Foundation module + all UIs |
| Pass 2 audit-actor FK constraints | After Auth/Membership | `*_by_sangha_sevi_pk` FK constraints deferred until `sangha_sevi` table exists — `sangha_sevi` has existed since Tier 4, but Pass 2 itself is still not implemented, including for the new Tier 5 tables (`user_account`, `user_role`, `admin_scope`, etc., all of which have the same nullable, unconstrained audit-actor columns) | `person`, `person_address`, `organization`, and now every Tier 5 table too |
| Inactive person search endpoint | Tier 5 (Authentication) | Needs role-based access (admin/auditor only) to view soft-deleted or deceased persons — still not implemented; Tier 5's `admin.py` has no such endpoint | Person API router — separate endpoint with auth-gated permissions |
| Kumari DDL (5 tables) | Tier 8 | Requires frozen Membership module | `kumari_sangha`, `kumari_member`, `kumari_activity`, `kumari_activity_participant`, `kumari_membership_transition` |
| Sevak/Mahila DDL | Tier 9 | Requires frozen Membership + Kumari | `sevak_sangha` tables, `mahila_sangha` tables |
| ~~Fix `test_kumari_transition_has_event`~~ | ~~Pre-freeze~~ | **Fixed on the Tier 5 branch (uncommitted):** now `pytest.skip()`s if `SS5` isn't seeded rather than asserting against it — no longer fails against the seed-less database | `test_membership.py` |
| ~~Add test coverage for the 9 new `family.py` write endpoints~~ | ~~Pre-freeze~~ | **Fixed (uncommitted):** `tests/api/test_family_ownership.py` (new, 20 tests) now exercises add/remove-member, admin assign/revoke, and transfer-head through a genuine role-less JWT holder, alongside `/graph` | `tests/api/test_family_ownership.py` |
| ~~Fix `test_page_loads_tailwind`/`test_page_loads_daisyui` (10 tests)~~ | ~~Pre-freeze~~ | **Fixed on the Tier 5 branch (uncommitted):** all 6 files' assertions now check for `tailwind.min.css`/`"tailwind"` instead of the old `cdn.tailwindcss.com`/`daisyui` CDN strings | `tests/test_bootstrap.py`, `test_foundation.py`, `test_organization.py`, `test_person.py`, `test_family.py`, `test_membership.py` |
| Fix `database/scripts/03_validate.sh`/`.ps1` | Pre-freeze | Hardcodes stale row counts (`organization`, `person`, `master_data`) from before the Tier 4 verification seed even existed; that seed has since been deleted entirely (see Database above), so the actual counts have changed again — no Family/Membership/Authentication/Administration checks exist at all | `database/scripts/03_validate.sh`, `.ps1` |
| Factor out duplicated FAM-036 SQL | Pre-freeze | The majority-rule "effective Sakha" CTE is implemented twice, identically, in `organization.py`'s `/children-stats` and `family.py`'s `/sakha-alignment`/`_FAMILY_SELECT` — no shared helper | `api/routers/organization.py`, `api/routers/family.py` |
| Add depth-cap guard to `_CHILDREN_STATS_SQL` | Pre-freeze | Its recursive CTE has no `depth < 10` guard, unlike `/hierarchy` — a circular parent reference could recurse indefinitely | `api/routers/organization.py` |
| Add test coverage for `/membership-summary` | Pre-freeze | `/graph` gained coverage via `tests/api/test_family_ownership.py` (uncommitted, see Tier 4 Family above); `/person/{pk}/membership-summary` still has zero test coverage | `tests/api/test_family.py`, `tests/api/test_family_ownership.py` |
| ~~Update stale module docstrings~~ | ~~Pre-freeze~~ | **Fixed:** `organization.py`'s docstring now says "7 GET endpoints" and drops the stale "No authentication" claim; `family.py`'s docstring is already fixed (now says "Tier 4 read-only + Tier 5 write endpoints"); `api/main.py`'s own module docstring also had a stale URL list (still advertising the six retired verification pages) — fixed to match the "Retired standalone verification pages" comment already in the file | `api/routers/organization.py`, `api/main.py` |
| Document the dual audit-write path | Pre-freeze (Tier 5) | `api/helpers.py::log_audit()` (called explicitly from `family.py`'s 9 write endpoints) and the new DB-level `fn_audit_trigger()` (fires on the same INSERT via a `DO $$`-installed trigger on every `nss.*` table) both write to `nss.system_event_log` for the same event, producing duplicate rows with different shapes — no de-duplication exists yet | `api/helpers.py`, `database/ddl/01_foundation/15_audit_trigger.sql` |
| ~~Wire `/children-stats` into the UI it claims to serve~~ | ~~Pre-freeze~~ | **Fixed (uncommitted), in a different page than expected:** `frontend/assets/js/dashboard.js` (`_fetchOrgChildrenStats(orgPk)`, near line 2076) now calls it from the org family browser in `dashboard.html`, not from `admin.html`/`admin.js`'s Organization Hierarchy tab as the endpoint's own docstring still implies | `frontend/assets/js/dashboard.js` |
| ~~Seed/freeze `permission_master`/`role_permission`~~ | ~~Pre-freeze (Tier 5)~~ | **Fixed (uncommitted):** both are now populated — `FOUNDATION_VIEW`/`ORGANIZATION_VIEW`/`PERSON_VIEW`/`PERSON_VIEW_SENSITIVE`/`FAMILY_VIEW`/`MEMBERSHIP_VIEW`/`AUDIT_VIEW` plus the admin/user-management permission set are mapped to roles; `require_permission(...)` calls no longer blanket-403 for every role | `database/seed/00_bootstrap/01_permission_master.sql`, `03_role_permission.sql` |
| ~~Fix `database/scripts/README.md`'s Phase 13 description~~ | ~~Pre-freeze (Tier 5)~~ | **Fixed (uncommitted):** now correctly describes `scripts/bootstrap_admin.py` against `database/seed/04_admin/01_admin_bootstrap.sql`, default login `SS1`/`P1`/`NSSAdmin1`, matching real `02_build.sh` behavior | `database/scripts/README.md` |
| Document Tier 5 frontend pages in `frontend/README.md` | Pre-freeze (Tier 5) | **Further fixed:** `admin.html`'s own row now does mention the merged-in "Registration Approvals" (claims-review) tab. Only remaining gap: the `nss-layout.css`/`nss-datepicker.css` stylesheets are covered in prose (the "Shared new helpers" section) but still have no dedicated `### assets/css/...` subsection in the File Reference, unlike `badges.css`/`style.css` | `frontend/README.md` |
| Reconcile the two "auto-provision `sangha_sevi` on approval" code paths | Pre-freeze (Tier 5) | `claim_approval.py::approve_claim()` and `admin.py::update_status()` (activating a claim-less `PENDING_APPROVAL` user) each independently generate/link a `sangha_sevi_id` — no shared helper, could diverge | `api/routers/claim_approval.py`, `api/routers/admin.py` |
| Create `frontend/forgot-password.html` or drop the dead route | Pre-freeze (Tier 5) | `api/main.py` registers `GET /forgot-password` only `if _forgot_password_path.is_file()` — the file doesn't exist, so the route is currently never registered even though `POST /api/v1/auth/forgot-password`/`reset-password` are implemented and tested | `frontend/forgot-password.html` (missing), `api/main.py` |
| ~~Update `database/README.md` for the 9 new Tier 5 tables~~ | ~~Pre-freeze (Tier 5)~~ | **Fixed (uncommitted):** now documents all 9 new tables (incl. `system_event_log`/`fn_audit_trigger`), `06_authentication/`, `07_administration/`, `family_admin`, `darshak_attendance_registration`, `database/seed/04_admin/`, and `scripts/bootstrap_admin.py`. (`database/fixes/` — mentioned in an earlier version of this row — has since been deleted outright as verifiably obsolete, not just documented; see Database above) | `database/README.md` |
| Update `database/ddl/01_foundation/README.md` for `system_event_log`/`fn_audit_trigger` | Pre-freeze (Tier 5) | Still says "12 tables" — doesn't mention the new `14_system_event_log.sql`/`15_audit_trigger.sql` | `database/ddl/01_foundation/README.md` |
| ~~Reconcile `admin.py`/`auth.py`/`registration.py` endpoint lists in this file~~ | ~~Pre-freeze (Tier 5)~~ | **Fixed (uncommitted):** this file's Tier 5 endpoints section now lists `admin.py`'s full 23 (incl. sangha-sevi provisioning, `/dashboard-stats`, `/persons/check-contact`, and the 4 org-creation-helper GETs), `auth.py`'s `PATCH /profile`, `registration.py`'s `GET /check-duplicate`, and the new `audit.py` router | `CLAUDE.md` (this file) |
| ~~Build `claim-approval.html`/`.js` or drop the dead backend path~~ | ~~Pre-freeze (Tier 5)~~ | **Resolved (uncommitted), differently than framed:** the claims-review UI for `api/routers/claim_approval.py` shipped as a "Registration Approvals" tab inside `admin.html`/`admin.js` rather than a standalone page — no dead route, no missing page | `frontend/admin.html`, `frontend/assets/js/admin.js` |
| ~~Wire `FAMILY_VIEW` permission into `family.py`'s GET endpoints, or drop it~~ | ~~Pre-freeze (Tier 5)~~ | **Resolved (uncommitted), differently than framed:** rather than a blanket per-route `require_permission("FAMILY_VIEW")` gate, `family.py` now uses an ownership model — every one of its 16 endpoints requires `get_current_user`, and a person reaches their own family through their `family_relationship`/`family_admin` row; `FAMILY_VIEW`/`FAMILY_MANAGE` are used as the admin override for browsing families the caller doesn't belong to (`list_families` requires `FAMILY_VIEW` outright). This is a deliberate design choice per the router's own module docstring, not a gap | `api/routers/family.py` |
| Document Foundation's 6 new write endpoints and `FOUNDATION_MANAGE` | Pre-freeze (Tier 5) | `foundation.py` gained `POST`/`PATCH /master-data`, `/settings`, `/sequences` (gated by a new `FOUNDATION_MANAGE` permission, distinct from `FOUNDATION_VIEW`) — resolved in this pass, but `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` still documents only the 17 original reads | `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` |
| `next_id()` silently ignores `id_sequence_master.padding_length` | Pre-freeze | `api/helpers.py::next_id()` returns `f"{prefix}{current_value}"` with no zero-padding logic at all — every seeded `padding_length` value (`PERSON` at 10, most others at 8) is dead configuration as far as ID generation is concerned, even though `foundation.py::update_sequence()`'s own docstring implies padding changes affect future IDs. Either wire padding into `next_id()`/`peek_next_id()`, or drop the column | `api/helpers.py`, `api/routers/foundation.py` |

## Tier 4 Frozen Decisions (2026-09-12)

| Decision | Resolution |
|----------|------------|
| MEM-PENDING-001 — Local Sakha Number | `membership_sakha_affiliation` table design FROZEN as documented in SOL-MEM-005 §27.1. Persistent per person per Sakha; archived on transfer (never reassigned); reactivated on return. |
| Kendra Number (annual) | Maps to `parichaya_patra.document_number` (e.g., `345/2024/2025`). New number each FY. Parichaya Patra row also snapshots `affiliated_organization_pk` (FK → organization) and `local_sakha_erp_id` (VARCHAR copy) for card reproduction accuracy. |
| Membership Status Vocabulary | Option A — add `RENEWAL_PENDING`, `ON_HOLD`, `DISCIPLINARY_REVIEW` to unified `STATUS` category in Foundation `master_data`. No separate `MEMBERSHIP_STATUS` category. |
| Three-tier member identity | (1) Sangha Sevi ID (NSS-wide, permanent) on `sangha_sevi`; (2) Local Sakha Number (per Sakha, per affiliation) on `membership_sakha_affiliation`; (3) Kendra Number (annual, per FY) on `parichaya_patra.document_number` |
| Associate member credentials | Parichaya Patra yes, Anumati Patra no (MBR-019A, MBR-019B). Anumati Patra section hidden in UI for ASSOCIATE `membership_type_code`. |
| Darshaka portal display | PROBATIONARY in DB → "Darshaka" in portal UI (MBR-007) |
| Member search | 7-field: `sangha_sevi_id`, `person_id`, `local_sakha_erp_id`, name trigram (threshold 0.45), mobile, email, Kendra number. Trigram email-split: `re.split(r'[.@]', q)[0]`. Search auto-selects single result; inline detail panel in search tabs. |
| Person search | 4-field: `person_id`, name trigram (threshold 0.45), mobile, email. Same email-split rule. |
| UI label | "Sakha Sangha ID" for `local_sakha_erp_id` (Tier 2 identity). Person ID shown in all tables. |
| Organization types | 13 types (3 new: KUMARI_SANGHA / KS, SEVAK_SANGHA / SEV, MAHILA_SANGHA / MS). 14 ID sequences accordingly. |
| Seed data (2026-09-12 snapshot) | 8 persons (P1–P8), 5 members (SS1–SS5 incl. Kumari transition SS5), 2 Sakhas, 2 Anchalas — **superseded, not just grown:** every Tier 4 verification-seed file this snapshot referenced (`database/seed/03_person/02_tier4_verification_persons.sql`, `database/seed/99_extended_test_data.sql`, and the rest listed under Database above) has since been **deleted** on the Tier 5 branch (uncommitted). A fresh build now seeds zero demo Person/Family/Membership rows — only 175 real Sakha branches and one admin superuser (`P1`/`SS1`, via `database/seed/04_admin/`). Do not assume any of the P1-P17/SS1-SS8 example IDs above exist in a freshly built database. |

**Note:** Person DDL (`02_person.sql`) already includes DB-level format validation CHECK
constraints (mobile, email, country code, Aadhaar last-4, emergency phone) — these are
schema-level safety nets that cost nothing and will be active from day one of writes. The
deferral above is specifically about Organization DDL (frozen Tier 2) and API-layer Pydantic
validation.
