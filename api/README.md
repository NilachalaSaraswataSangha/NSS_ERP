# api/

FastAPI application — the only web/API layer in the codebase. Implements **Tier 0**
(read-only bootstrap-RBAC, unauthenticated), **Tier 1** (Foundation), **Tier 2** (
Organization), **Tier 3** (Person), and **Tier 4** (Family + Membership) —
no ORM — behind a cross-tier security middleware stack (headers, opt-in CORS, rate limiting,
plus a new Content-Security-Policy). **Partway through this branch's development, Tiers 1-3
and Membership (Tier 4) gained `require_permission("<MODULE>_VIEW")` gating on every GET
endpoint** — they were read-only/no-auth through the Tier 4 release. **Family (Tier 4) later
took a different path**: rather than a blanket permission, every one of `family.py`'s 16
endpoints (7 original reads + 9 Tier 5 writes) now requires `get_current_user` plus an
ownership check — a person reaches their own family through their `family_relationship`/
`family_admin` row, with `FAMILY_VIEW`/`FAMILY_MANAGE` as the admin override (see the Family
section below). Only Tier 0's 4 `bootstrap.py` endpoints remain fully unauthenticated now.

**Tier 5 (Authentication + Administration + Audit) is in progress, uncommitted** on branch
`feature/tier5-authentication-administration` — not yet merged/released. It adds the first
authenticated, write-path endpoints: JWT login/refresh/logout/password-management
(`routers/auth.py`), user/role/organization administration (`routers/admin.py`),
self-registration (`routers/registration.py`), Sakha-admin claim approval
(`routers/claim_approval.py`), and an authenticated audit-trail viewer (`routers/audit.py`),
backed by a new `api/dependencies/` layer and two new
`api/services/` modules (`auth_service.py`, `rbac_service.py`) — see "Endpoints (Tier 5)" below
and `docs/PROJECT_DOCUMENTATION.md` → Architecture ("Tier 5") for full detail. Everything in
this Tier 5 section should be read as in-flight, not shipped.

An earlier Django prototype lived under `backend/` and covered parts of Foundation,
Authentication, Family, Membership, and Heritage; it was fully archived and removed once the
FastAPI direction (`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md`) was adopted.
`backend/` is now empty.

## Layout

```
api/
├── main.py             FastAPI app entry point — builds `app`, registers the security
│                        middleware stack (rate limiting → opt-in CORS → security headers → CSP,
│                        in
│                        that order), includes the six Tier 0-4 routers plus (Tier 5, in
│                        progress) `auth`/`admin`/`registration`/`claim_approval`/`audit` — 11
│                        routers total, mounts
│                        `frontend/assets/` at `/assets`. **The six original Tier 0-4 page
│                        routes (`/`→`index.html`, `/foundation`, `/organization`, `/person`,
│                        `/family`, `/membership`) have been deleted** (see the "Retired
│                        standalone verification pages" comment in the file) — root `/` now
│                        redirects to `/login` instead. Serves — Tier 5,
│                        in progress — `frontend/login.html` at `/login`,
│                        `frontend/dashboard.html` at `/dashboard`, `frontend/admin.html` at
│                        `/admin`, `frontend/register.html` at `/register` (each gated
│                        `if <page>_path.is_file()`), plus a guarded `/forgot-password` route
│                        whose target file doesn't exist yet, so it never registers. There is no
│                        `/claim-approval` route or `claim-approval.html` file — that feature
│                        shipped as a tab inside `admin.html` instead. Closes
│                        the DB pool on shutdown
├── config.py            Settings: DB_NAME/DB_USER/DB_PASSWORD (required), DB_HOST (default
│                        localhost), DB_PORT (default 5432), API_PORT (default 8001),
│                        DISABLE_DOCS (default false), CORS_ORIGINS (comma-separated, default
│                        empty), RATE_LIMIT (default `60/minute`) — read from api/.env via
│                        python-dotenv. Tier 5 (in progress) adds DB_WRITE_USER/DB_WRITE_PASSWORD,
│                        JWT_SECRET_KEY/JWT_ACCESS_TOKEN_MINUTES/JWT_REFRESH_TOKEN_DAYS/
│                        JWT_ABSOLUTE_SESSION_DAYS, DB_READ_POOL_MIN/MAX, DB_WRITE_POOL_MIN/MAX,
│                        DEBUG_MODE, plus hardcoded (non-env) lockout/password-policy/OTP
│                        constants; `Settings.validate_auth()` gates only the write-pool path.
│                        CSP_ENABLED (default true), CSP_REPORT_ONLY (default false) and
│                        CSP_SCRIPT_SRC_EXTRA/CSP_STYLE_SRC_EXTRA (comma-separated extra
│                        origins) control the Content-Security-Policy built in middleware.py
├── database.py          psycopg2 SimpleConnectionPool (2-5 conns default), connects as
│                        `nss_db_backend` (read-only); get_connection() is a FastAPI
│                        generator dependency. Tier 5 (in progress) adds a second pool,
│                        get_write_pool()/get_write_connection(), connecting as `nss_db_writer`
│                        (auto-commit on success, rollback on exception)
├── helpers.py           Shared cursor→Pydantic conversion helpers (`rows_to_models`,
│                        `row_to_model`) used by every router, plus centralised pagination
│                        constants (`DEFAULT_LIMIT = 100`, `MAX_LIMIT = 500`) so all list
│                        endpoints share the same defaults/validation range — extracted from
│                        per-router duplicates when the Person router landed. Tier 5 (in
│                        progress) adds `next_id()` (atomic `id_sequence_master` allocation),
│                        `compose_local_sakha_erp_id()`, `resolve_or_create_city_village()`,
│                        `resolve_or_create_postal_code()`, `get_active_status_pk()`,
│                        `log_audit()` (writes a row to the new `nss.system_event_log` table —
│                        see Audit trail below), `require_entity()`, `check_duplicate_contact()`,
│                        `record_password_history()`, and `validate_and_hash_password()` — all
│                        used across `auth.py`/`admin.py`/`registration.py`/`claim_approval.py`
├── middleware.py        `add_security_headers(request, call_next)` — sets
│                        `X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy`/
│                        `Permissions-Policy` on every response, plus `Cache-Control: no-store`
│                        scoped to `/api/*` only. Also emits the `Content-Security-Policy`
│                        assembled by `build_csp()` (or the `-Report-Only` variant when
│                        CSP_REPORT_ONLY is set), skipping `CSP_EXEMPT_PATHS` — `/docs`,
│                        `/redoc`, `/openapi.json` — because Swagger UI embeds an inline script
├── routers/
│   ├── bootstrap.py     4 endpoints under /api/v1/bootstrap — no auth, no ORM, raw
│   │                    parameterized SQL against nss.role_master/permission_master/
│   │                    role_permission
│   ├── foundation.py    23 endpoints under /api/v1/foundation across 11 tables — 17 reads
│   │                    (master data, system config, geography, runtime document metadata,
│   │                    see below) plus 6 Tier 5 write endpoints (`POST`/`PATCH` on
│   │                    `/master-data`, `/settings`, `/sequences`). Reads gated by
│   │                    `require_permission("FOUNDATION_VIEW")`, writes by
│   │                    `require_permission("FOUNDATION_MANAGE")` on the Tier 5 branch
│   ├── organization.py  7 endpoints under /api/v1/organization across 3 tables — reference
│   │                    data (types, statuses), core organizations (list/detail/children),
│   │                    children-stats (recursive, no depth-cap guard — see Gotchas), and a
│   │                    self-referencing hierarchy tree via `WITH RECURSIVE`. Gated by
│   │                    `require_permission("ORGANIZATION_VIEW")` on the Tier 5 branch
│   ├── person.py        4 endpoints under /api/v1/person across 2 tables — person list
│   │                    (with gender/marital-status/blood-group filters + pagination),
│   │                    person detail, person addresses, and trigram-based (`pg_trgm`) search.
│   │                    Gated by `require_permission("PERSON_VIEW")` on the Tier 5 branch
│   ├── family.py        16 endpoints under /api/v1/family across 6 tables — 7 original reads
│   │                    (family group list/detail/members/head-history, plus `/graph` (dynamic
│   │                    relationship-label BFS via `api/services/family_graph.py`),
│   │                    `/sakha-alignment` (FAM-036 majority-rule computation), and
│   │                    `/person/{pk}/membership-summary`) plus 9 Tier 5 write endpoints
│   │                    (create family, add/remove member, create link, admin CRUD ×3,
│   │                    transfer-head). **Unlike the three routers above, `family.py` uses an
│   │                    ownership model instead of a blanket `require_permission` gate: every
│   │                    one of the 16 endpoints requires `get_current_user`, and a person
│   │                    reaches their own family through their `family_relationship`/
│   │                    `family_admin` row, with `FAMILY_VIEW`/`FAMILY_MANAGE` as the admin
│   │                    override** — a deliberate design choice per the router's own module
│   │                    docstring, not a gap. `tests/api/test_family_ownership.py` (20 tests,
│   │                    new) now covers the ownership path for the 9 write endpoints plus
│   │                    `/graph`; `/person/{pk}/membership-summary` still has no coverage
│   │                    (see "Endpoints (Tier 4)" below)
│   ├── membership.py    7 endpoints under /api/v1/membership — member list/detail, member
│   │                    search (7-field), member Sakha affiliations, Parichaya Patra records,
│   │                    Anumati Patra records, and journey events. Gated by
│   │                    `require_permission("MEMBERSHIP_VIEW")` on the Tier 5 branch
│   ├── auth.py          Tier 5 (in progress) — /api/v1/auth: login, refresh, logout,
│   │                    change-password, forgot-password, reset-password, /me, profile update
│   ├── admin.py         Tier 5 (in progress) — /api/v1/admin: user CRUD, Sangha Sevi
│   │                    creation/lookup (standalone from user accounts), role assignment,
│   │                    person creation, organization CRUD, dashboard-stats aggregate
│   ├── registration.py  Tier 5 (in progress) — /api/v1/register: self-registration
│   ├── claim_approval.py Tier 5 (in progress) — /api/v1/admin/claims: Sakha-admin review queue
│   │                        for registration_claim rows. Its frontend shipped as a
│   │                        "Registration Approvals" tab inside `admin.html`/`admin.js`, not a
│   │                        standalone page
│   └── audit.py          Tier 5 (in progress) — /api/v1/audit: `GET /change-log`, a
│                          filterable/paginated view over `nss.field_change_log`, gated by
│                          `AUDIT_VIEW`; the authenticated counterpart to Tier 1's
│                          deliberately-unexposed audit data
├── dependencies/        Tier 5 (in progress) — FastAPI `Depends()` factories, distinct from
│   ├── auth.py          `services/`: `get_current_user()` (mandatory JWT auth, loads
│   │                    UserContext) / `get_optional_user()` (same, returns None instead of
│   │                    401ing)
│   └── rbac.py          `require_permission(code)` / `require_any_permission(*codes)` —
│                        wrap `get_current_user()` and additionally 403 on missing permission
├── services/
│   ├── family_graph.py  BFS graph-traversal relationship computation over `nss.family_link`
│   │                    edges — first file in this layer, distinct from routers/schemas; no
│   │                    test coverage yet (see Gotchas)
│   ├── auth_service.py  Tier 5 (in progress) — Argon2 hashing, JWT create/decode
│   │                    (access 30 min / refresh 7 days / 30-day absolute session max),
│   │                    password-policy validation, lockout helpers (5 attempts / 30s)
│   └── rbac_service.py  Tier 5 (in progress) — `UserContext`/`ScopeInfo` dataclasses +
│                        `load_user_context()`: permissions = union of every active role's
│                        `role_permission` rows; scopes = one per active `user_role` +
│                        `admin_scope`
└── schemas/
    ├── bootstrap.py      Pydantic response models (RoleResponse, PermissionResponse,
    │                     HealthResponse) — audit columns deliberately excluded
    ├── foundation.py     11 plain Pydantic models, one per exposed table/view — audit columns,
    │                     `current_value`, and unimplemented FK columns deliberately excluded
    ├── organization.py   4 Pydantic models (OrganizationTypeResponse,
    │                     StatusResponse, OrganizationResponse,
    │                     OrganizationHierarchyNodeResponse) — OrganizationResponse includes
    │                     contact/online-presence fields (phone_number, mobile_number, email,
    │                     org_email, website_url, org_website_url, youtube_channel_url,
    │                     org_youtube_channel_url)
    ├── person.py         3 Pydantic models (PersonResponse, PersonSummaryResponse,
    │                     PersonAddressResponse) — PersonResponse/PersonSummaryResponse never
    │                     include `aadhaar_encrypted`/`aadhaar_hash`, only `aadhaar_last4` for
    │                     masked display (PER-BR-081); audit columns excluded
    ├── family.py         8 original Pydantic models (FamilyGroupResponse, FamilyMemberResponse,
    │                     FamilyGraphMemberResponse, PersonMembershipSummaryResponse,
    │                     FamilyHeadHistoryResponse, SakhaAffiliationCount, MemberSakhaInfo,
    │                     FamilySakhaAlignmentResponse) plus 8 more (Tier 5, in progress) for the
    │                     new write endpoints: AddFamilyMemberRequest,
    │                     RemoveFamilyMemberRequest, CreateFamilyLinkRequest,
    │                     CreateFamilyRequest, FamilyAdminResponse, AssignFamilyAdminRequest,
    │                     RevokeFamilyAdminRequest, TransferHeadRequest
    ├── membership.py     5 Pydantic models (MemberResponse, SakhaAffiliationResponse,
    │                     ParichayaPatraResponse, AnumatiPatraResponse, JourneyEventResponse)
    ├── auth.py           Tier 5 (in progress) — LoginRequest/Response,
    │                     RefreshRequest/Response, ChangePasswordRequest,
    │                     ForgotPasswordRequest/Response, ResetPasswordRequest, MeResponse,
    │                     ScopeResponse, MessageResponse, UpdateProfileRequest
    ├── admin.py          Tier 5 (in progress) — CreateUserRequest, ResetPasswordRequest,
    │                     UpdateStatusRequest, AssignRoleRequest, CreateSanghaSeviRequest,
    │                     UserAccountResponse, UserDetailResponse, UserListResponse,
    │                     RoleAssignmentResponse, CreateSanghaSeviResponse
    └── audit.py          Tier 5 (in progress) — FieldChangeLogResponse (the one schema in this
                          codebase that deliberately includes audit-actor columns, since the
                          whole point of this endpoint is exposing them)
```

## Endpoints (Tier 5 — in progress, uncommitted)

Not yet merged/released. Requires `api/.env` to also carry `DB_WRITE_USER`, `DB_WRITE_PASSWORD`,
and `JWT_SECRET_KEY` (see `docs/PROJECT_DOCUMENTATION.md` → Configuration) — every endpoint
below except `GET /api/v1/audit/change-log` is backed by the new `nss_db_writer` connection pool
(`api/database.py::get_write_connection`); `audit.py`'s endpoint never writes, so it connects via
the same read-only `nss_db_backend` pool (`get_connection`) the rest of this file describes.

| Method | Path | Auth | Returns |
|--------|------|------|---------|
| POST | `/api/v1/auth/login` | none | Access + refresh JWT; login_id = Sangha Sevi ID or Person ID |
| POST | `/api/v1/auth/refresh` | refresh token | New access JWT |
| POST | `/api/v1/auth/logout` | access token | Stateless — client discards tokens, no server-side revocation |
| POST | `/api/v1/auth/change-password` | access token | Self-service password change (policy + reuse check) |
| POST | `/api/v1/auth/forgot-password` | none | Generates a 6-digit OTP (`password_reset_token`); always returns a generic message (anti-enumeration) |
| POST | `/api/v1/auth/reset-password` | none | Consumes the OTP, sets a new password |
| GET | `/api/v1/auth/me` | access token | Profile + permissions + scopes |
| PATCH | `/api/v1/auth/profile` | access token | Self-service update of `mobile_number`/`country_phone_code`/`email`/`date_of_birth`; name fields are admin-only |
| GET/POST | `/api/v1/admin/users` | `ADMIN_USER_VIEW`/`ADMIN_USER_MANAGE`/`MEMBERSHIP_APPROVE` | List/create user accounts |
| GET | `/api/v1/admin/users/{pk}` | `ADMIN_USER_VIEW`/`ADMIN_USER_MANAGE`/`MEMBERSHIP_APPROVE` | User detail + role assignments |
| POST | `/api/v1/admin/users/{pk}/reset-password` | `ADMIN_USER_MANAGE` | Admin-initiated password reset |
| PATCH | `/api/v1/admin/users/{pk}/status` | `ADMIN_USER_MANAGE` | Activate/suspend/deactivate; auto-generates a `sangha_sevi_id` when activating a claim-less `PENDING_APPROVAL` user |
| DELETE | `/api/v1/admin/users/{pk}` | `ADMIN_USER_MANAGE` | Soft-delete (also revokes roles + scopes) |
| GET/POST | `/api/v1/admin/users/{pk}/roles` | `ADMIN_USER_VIEW`/`ADMIN_USER_MANAGE`/`MEMBERSHIP_APPROVE` (GET) / `ADMIN_ROLE_MANAGE` (POST) | List/assign role + scope |
| DELETE | `/api/v1/admin/users/{pk}/roles/{user_role_pk}` | `ADMIN_ROLE_MANAGE` | Revoke a role assignment |
| POST | `/api/v1/admin/persons` | `PERSON_MANAGE` | Admin creates a person directly (no account) |
| POST | `/api/v1/admin/sangha-sevi` | `ADMIN_USER_MANAGE`/`PERSON_MANAGE` | Create a standalone Sangha Sevi record, decoupled from user-account creation; scope-checked for non-`ADMIN_USER_MANAGE` callers |
| GET | `/api/v1/admin/sangha-sevi/check/{person_pk}` | `ADMIN_USER_VIEW`/`ADMIN_USER_MANAGE`/`MEMBERSHIP_APPROVE` | Whether a person already has an active Sangha Sevi record |
| POST | `/api/v1/admin/sangha-sevi/check-batch` | `ADMIN_USER_VIEW`/`ADMIN_USER_MANAGE`/`MEMBERSHIP_APPROVE` | Batch check up to 100 persons for an active Sangha Sevi or a pending registration claim |
| GET/POST | `/api/v1/admin/organizations` | `ADMIN_USER_VIEW`/`ADMIN_USER_MANAGE` / `NSS_ERP_ADMIN` only for create | List / create organizations |
| PATCH | `/api/v1/admin/organizations/{pk}/short-code` | `ADMIN_USER_MANAGE` | Set/clear the 3-5 char short code |
| PATCH | `/api/v1/admin/organizations/{pk}` | `ADMIN_USER_MANAGE`, scope-checked | Update org contact/address fields |
| GET | `/api/v1/admin/dashboard-stats` | (see `api/routers/admin.py::dashboard_stats`) | Aggregated counts for the admin dashboard cards |
| POST | `/api/v1/register` | none | Self-registration — creates `person` + `user_account(PENDING_APPROVAL)` + optional `registration_claim` |
| GET | `/api/v1/admin/claims` | `MEMBERSHIP_APPROVE`/`ADMIN_USER_MANAGE`, scoped | List registration claims |
| GET/PATCH | `/api/v1/admin/claims/{pk}` | same | Claim detail / admin edits before approval |
| POST | `/api/v1/admin/claims/{pk}/approve` | same | Creates `sangha_sevi` + affiliation, activates the account |
| POST | `/api/v1/admin/claims/{pk}/reject` | same | Leaves the account `PENDING_APPROVAL`, remarks required |
| GET | `/api/v1/audit/change-log` | `AUDIT_VIEW` | Filterable, paginated `nss.field_change_log` history — the authenticated counterpart to Tier 1's deliberately-unexposed `/api/v1/foundation/change-log` (which doesn't exist) |

**`nss.permission_master`/`nss.role_permission` are now seeded** (`database/seed/00_bootstrap/
01_permission_master.sql`/`03_role_permission.sql`) — `FOUNDATION_VIEW`/`ORGANIZATION_VIEW`/
`PERSON_VIEW`/`PERSON_VIEW_SENSITIVE`/`FAMILY_VIEW`/`MEMBERSHIP_VIEW`/`AUDIT_VIEW` plus the
admin/user-management permission set are mapped to roles, so `require_permission(...)`/
`require_any_permission(...)` calls above no longer blanket-403 for every role. No test coverage
gap list has been separately tracked for Tier 5 yet — see `tests/README.md`.

See `docs/PROJECT_DOCUMENTATION.md` → Key Workflow #9 for the full registration → approval →
login → RBAC flow this layer implements.

## Audit trail (Tier 5, in progress, uncommitted)

Every Tier 5 write endpoint calls `api/helpers.py::log_audit()` after each mutation, inserting a
row into the new `nss.system_event_log` table (`action`, `table_name`, `record_pk`, `actor_pk`,
`actor_user_account_pk`, `module`, `summary`, `detail` JSONB, `is_success`) —
`database/ddl/01_foundation/14_system_event_log.sql`. Independently, `database/ddl/01_foundation/
15_audit_trigger.sql` attaches a `fn_audit_trigger()` `AFTER INSERT OR UPDATE OR DELETE` trigger
to every other `nss.*` table (a `DO $$` loop over `pg_tables`), so raw SQL writes are captured
even if application code forgets to call `log_audit()` — the two mechanisms are independent and
both currently write to the same table, so a single mutation can produce two rows (one
app-authored with a human `summary`, one trigger-authored and generic).

## Security middleware

Registered in `api/main.py`, order matters (outermost registered last runs first):

1. **Rate limiting** (`slowapi`) — `Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])`
   registered via `SlowAPIMiddleware`; default `60/minute` per client IP, global (no per-route
   overrides yet). Returns 429 once the limit trips.
2. **CORS** (`fastapi.middleware.cors.CORSMiddleware`) — only added `if settings.CORS_ORIGINS:`;
   empty by default, so no CORS headers appear on any response out of the box. When configured,
   `GET`-only, credentials allowed, never a wildcard origin.
3. **Security headers** (`api/middleware.py`) — always on: `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
   `Permissions-Policy: camera=(), microphone=(), geolocation=()` on every response, plus
   `Cache-Control: no-store` on `/api/*` responses, and `Cache-Control: public, max-age=86400,
   must-revalidate` on `/assets/*` responses (new, uncommitted — Tailwind CDN→CLI migration; no
   test coverage yet). Deliberately skips `X-XSS-Protection`
   (obsolete); CSP remains deferred — the original blocker (Tailwind Play CDN's inline styles)
   no longer applies now that Tailwind is pre-built, but a full audit of remaining inline styles
   hasn't happened yet —
   and HSTS (left to Render's edge TLS).

Verified by `tests/security/test_security_headers.py` (24 tests) — the old flat
`tests/test_security.py` (8 tests) no longer exists, absorbed into the new `tests/security/`
directory (see `CLAUDE.md` → Tests & lint). Full walkthrough:
`docs/03_Solution/code_explanations/SECURITY_CODE_EXPLANATIONS.md`.

## Running

From the **repository root** (not from `api/`):

```
python3 -m uvicorn api.main:app --reload --port 8001   # macOS/Linux
py -m uvicorn api.main:app --reload --port 8001         # Windows
```

Requires `api/.env` with `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` (see
`database/scripts/README.md` for the full bootstrap-to-running-API sequence — the database must
be built and `nss_db_backend` granted read access via `database/scripts/04_grant_backend.sql`
before this will connect to anything meaningful).

Swagger UI: `http://localhost:8001/docs` (set `DISABLE_DOCS=true` in `api/.env` to turn off
`/docs`, `/redoc`, and `/openapi.json`).

## Endpoints (Tier 0)

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/bootstrap/health` | `{"status", "database"}` — liveness/DB-connectivity probe |
| GET | `/api/v1/bootstrap/roles` | The 9 frozen roles from `nss.role_master` |
| GET | `/api/v1/bootstrap/permissions` | `nss.permission_master` rows — was empty by design through Tier 4; **now returns real rows on the Tier 5 branch**, since the catalogue is seeded |
| GET | `/api/v1/bootstrap/roles/{role_pk}/permissions` | Permissions mapped to a role — same, no longer empty for roles with real `role_permission` mappings; 404 if `role_pk` doesn't match an active role |

All four are unauthenticated and read-only — they exist to verify the RBAC schema is queryable,
not to enforce RBAC.

## Endpoints (Tier 1)

23 endpoints under `/api/v1/foundation`, across 11 tables — no ORM, raw
parameterized SQL. 17 reads **gated by `require_permission("FOUNDATION_VIEW")` on the Tier 5
branch** (read-only/no-auth through Tier 4); 6 new write endpoints (below) gated by
`require_permission("FOUNDATION_MANAGE")` instead. Grouped by theme:

| Group | Endpoints |
|-------|-----------|
| Master data | `/categories`, `/categories/{pk}`, `/master-data` (filter by `category_code`/`category_pk`; `GET`+`POST`), `/master-data/{pk}` (`GET`+`PATCH`) |
| System config | `/settings` (`GET`+`POST`), `/settings/{setting_key}` (`GET`+`PATCH`), `/sequences` (`GET`+`POST`, excludes `current_value`), `/sequences/{sequence_code}` (`PATCH`) |
| Geographic | `/countries`, `/countries/{pk}`, `/states`, `/states/{pk}`, `/districts`, `/districts/{pk}`, `/cities`, `/postal-codes`, `/postal-code-mappings` |
| Runtime | `/documents` |

The 6 `POST`/`PATCH` endpoints above are new (Tier 5, in progress, uncommitted) —
`create_master_data`/`update_master_data`, `create_setting`/`update_setting`,
`create_sequence`/`update_sequence` — each writes via `get_write_connection` and logs through
`log_audit()`.

`nss.field_change_log` is deliberately not exposed — deferred to Tier 5 (needs auth). All list
endpoints filter `is_active = TRUE` (except the postal-code-mapping junction table, which has no
such column); detail endpoints 404 on missing/inactive rows. Full contract:
`docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`. Verified by 45 pytest integration
tests (`tests/api/test_foundation.py`; some of the original 59 were extracted into
`tests/security/`).

## Endpoints (Tier 2)

7 endpoints under `/api/v1/organization` — no ORM,
parameterized SQL. **Gated by `require_permission("ORGANIZATION_VIEW")` on the Tier 5 branch**
(read-only/no-auth through Tier 4). Organization type values come from Foundation `master_data`
(category `ORGANIZATION_TYPE`). Status values come from the unified ERP-wide
`STATUS` category. Organization LEFT JOINs
Foundation's geography tables (country, state, district, city_village, postal_code)
for address resolution, since those FKs are nullable.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/organization/types` | The 10 frozen organization types from `nss.master_data` (category `ORGANIZATION_TYPE`) |
| GET | `/api/v1/organization/statuses` | The 13 unified lifecycle statuses from `nss.master_data` (category `STATUS`) |
| GET | `/api/v1/organization/organizations` | Organizations with resolved type/status/parent/geography context; optional `type_code`/`status_code` filters, `limit`/`offset` pagination (default 100, max 500) |
| GET | `/api/v1/organization/organizations/{organization_pk}` | Single organization detail; 404 if missing/inactive |
| GET | `/api/v1/organization/organizations/{organization_pk}/children` | Direct children of an organization; 404 if the parent `organization_pk` doesn't exist |
| GET | `/api/v1/organization/organizations/{organization_pk}/children-stats` | Aggregate family/member/person counts per direct child, recursing through descendant Sakhas and applying the FAM-036 majority-rule "effective Sakha" computation; its own recursive CTE has **no** depth-cap guard, unlike `/hierarchy` |
| GET | `/api/v1/organization/hierarchy` | Full organization tree as a flat list with a `depth` field, via a `WITH RECURSIVE` CTE (depth guard at 10); `limit`/`offset` pagination |

All list endpoints filter `is_active = TRUE`; detail/children endpoints 404 on a missing parent.
Full contract: `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`. Verified by 58 pytest
integration tests (`tests/api/test_organization.py`; some of the original 72 were extracted into
`tests/security/`).

## Endpoints (Tier 3)

4 endpoints under `/api/v1/person` — no ORM, raw parameterized SQL. **Gated by
`require_permission("PERSON_VIEW")` on the Tier 5 branch** (read-only/no-auth through Tier 4).
Gender,
marital status, blood group, emergency relationship, and address type are resolved via JOINs
against Foundation's `master_data`. Trigram search relies on `pg_trgm` (installed in
`database/scripts/01_extensions.sql`).

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/person/persons` | Active persons (compact summary — no Aadhaar/emergency/photo fields); optional `gender_code`/`marital_status_code`/`blood_group_code` filters, `limit`/`offset` pagination (default 100, max 500) |
| GET | `/api/v1/person/persons/{person_pk}` | Single person detail with full resolved context, incl. masked `aadhaar_last4`; 404 if missing/inactive |
| GET | `/api/v1/person/persons/{person_pk}/addresses` | Active addresses for a person, with resolved address type + city/village/postal-code/district/state/country chain; 404 if the person doesn't exist |
| GET | `/api/v1/person/search` | Trigram similarity search (`pg_trgm`) on first/last name, plus prefix match on `person_id`/`mobile_number`; capped at 50 results |

`aadhaar_encrypted` and `aadhaar_hash` are never returned by any endpoint — only
`aadhaar_last4` for masked display (PER-BR-081). Full contract:
`docs/03_Solution/api/PERSON_API_CONTRACT.md`. Verified by 55 pytest integration tests
(`tests/api/test_person.py`; some of the original 61 were extracted into
`tests/security/test_*_security.py` — see `CLAUDE.md` → Tests & lint).

## Endpoints (Tier 4)

Originally 14 read-only endpoints across Family and Membership — no ORM, raw
parameterized SQL. **`membership.py`'s 7 gained `require_permission("MEMBERSHIP_VIEW")` gating
on the Tier 5 branch; `family.py`'s 7 gained an ownership-based auth model instead** (every
endpoint now requires `get_current_user`, with `FAMILY_VIEW`/`FAMILY_MANAGE` as the admin
override — a deliberate design choice, not a gap), and `family.py` separately
**gained 9 more, authenticated write endpoints on the Tier 5
branch (in progress, uncommitted) — see below.**

**Family** — originally 7 read-only endpoints under `/api/v1/family`, across 5 tables (now
authenticated — see above):

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/family/families` | Family group list with filters + pagination (requires `FAMILY_VIEW`) |
| GET | `/api/v1/family/families/{family_group_pk}` | Family group detail (current member, or `FAMILY_VIEW`) |
| GET | `/api/v1/family/families/{family_group_pk}/members` | Family group members |
| GET | `/api/v1/family/families/{family_group_pk}/head-history` | Family head history |
| GET | `/api/v1/family/families/{family_group_pk}/graph?viewer_person_pk=` | Dynamic relationship-label computation via BFS traversal over `nss.family_link` edges (`api/services/family_graph.py`); covered by `tests/api/test_family_ownership.py` |
| GET | `/api/v1/family/families/{family_group_pk}/sakha-alignment` | FAM-036 majority-rule "effective Sakha" computation — `is_aligned` is hardcoded `True` by design; per-member `is_home_sakha` flags surface real mismatches |
| GET | `/api/v1/family/person/{person_pk}/membership-summary` | Bridges family context to membership context for a UI panel; no test coverage yet |

Full contract: `docs/03_Solution/api/API_CONTRACT.md` (documents these 7 only, not yet updated
for the 9 below). Verified by 52 pytest integration tests
(`tests/api/test_family.py`; some of the original 67 were extracted into `tests/security/`) —
`/graph` and `/person/{pk}/membership-summary` are the two
exceptions with no coverage.

**Family (Tier 5 additions, in progress, uncommitted) — 9 more endpoints, all requiring
`get_current_user` (JWT) + `get_write_connection` (`nss_db_writer`), all with zero test
coverage:**

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/family/person/{person_pk}/families` | Families a person belongs to |
| POST | `/api/v1/family/families` | Create a family — authenticated user becomes founding member + head; auto-generates the next `family_id`; uses the new `SELF` `RELATIONSHIP_TYPE` value |
| POST | `/api/v1/family/families/{pk}/members` | Add a member — requester must be a current family member |
| DELETE | `/api/v1/family/families/{pk}/members` | Remove a member — requester must be head or admin (FAM-048) |
| POST | `/api/v1/family/families/{pk}/links` | Create `family_link` graph edges |
| GET | `/api/v1/family/families/{pk}/admins` | List `family_admin` rows (current by default, or full history) |
| POST | `/api/v1/family/families/{pk}/admins` | Assign a Family Admin — requester must be the current head (FAM-046) |
| DELETE | `/api/v1/family/families/{pk}/admins` | Revoke a Family Admin — requester must be the current head (FAM-050) |
| POST | `/api/v1/family/families/{pk}/transfer-head` | Transfer family headship |

**Membership** — 7 endpoints under `/api/v1/membership`:

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/membership/members` | Member list with filters + pagination |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}` | Member detail |
| GET | `/api/v1/membership/search` | 7-field member search: `sangha_sevi_id`, `person_id`, `local_sakha_erp_id`, name (trigram 0.45), mobile, email, Kendra number |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}/affiliations` | Member Sakha affiliations (current + historical) |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}/parichaya-patra` | Member Parichaya Patra records |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}/anumati-patra` | Member Anumati Patra records |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}/journey` | Member journey events |

Full contract: `docs/03_Solution/api/API_CONTRACT.md` (documents the original 46 endpoints
across Tiers 0-4; now 61 with Family's 9 Tier 5 writes and Foundation's 6, plus 28 more across
the 5 Tier 5-only routers — 89 endpoints total, see `CLAUDE.md`'s Running the FastAPI API
section for the current per-router breakdown).
Verified by 94 pytest integration tests (`tests/api/test_membership.py`; some of the original 99
were extracted into `tests/security/`).

See `docs/PROJECT_DOCUMENTATION.md` → Key workflows for more detail on all six tiers.
