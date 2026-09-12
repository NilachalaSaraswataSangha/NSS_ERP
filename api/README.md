# api/

FastAPI application — the only web/API layer in the codebase. Currently implements **Tier 0**
(read-only bootstrap-RBAC), **Tier 1** (read-only Foundation), and **Tier 2** (read-only
Organization) — no authentication, no ORM — behind a cross-tier security middleware stack
(headers, opt-in CORS, rate limiting).

An earlier Django prototype lived under `backend/` and covered parts of Foundation,
Authentication, Family, Membership, and Heritage; it was fully archived and removed once the
FastAPI direction (`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md`) was adopted.
`backend/` is now empty.

## Layout

```
api/
├── main.py             FastAPI app entry point — builds `app`, registers the security
│                        middleware stack (rate limiting → opt-in CORS → security headers, in
│                        that order), includes all three routers, mounts `frontend/assets/` at
│                        `/assets`, serves `frontend/index.html` at `/`,
│                        `frontend/foundation.html` at `/foundation` (if present), and
│                        `frontend/organization.html` at `/organization` (if present), closes
│                        the DB pool on shutdown
├── config.py            Settings: DB_NAME/DB_USER/DB_PASSWORD (required), DB_HOST (default
│                        localhost), DB_PORT (default 5432), API_PORT (default 8001),
│                        DISABLE_DOCS (default false), CORS_ORIGINS (comma-separated, default
│                        empty), RATE_LIMIT (default `60/minute`) — read from api/.env via
│                        python-dotenv
├── database.py          psycopg2 SimpleConnectionPool (1-5 conns), connects as
│                        `nss_db_backend` (read-only); get_connection() is a FastAPI
│                        generator dependency
├── middleware.py        `add_security_headers(request, call_next)` — sets
│                        `X-Content-Type-Options`/`X-Frame-Options`/`Referrer-Policy`/
│                        `Permissions-Policy` on every response, plus `Cache-Control: no-store`
│                        scoped to `/api/*` only
├── routers/
│   ├── bootstrap.py     4 endpoints under /api/v1/bootstrap — no auth, no ORM, raw
│   │                    parameterized SQL against nss.role_master/permission_master/
│   │                    role_permission
│   ├── foundation.py    17 endpoints under /api/v1/foundation across 11 tables — master data,
│   │                    system config, geography, and runtime document metadata (see below)
│   └── organization.py  6 endpoints under /api/v1/organization across 3 tables — reference
│                        data (types, statuses), core organizations (list/detail/children),
│                        and a self-referencing hierarchy tree via `WITH RECURSIVE`
└── schemas/
    ├── bootstrap.py      Pydantic response models (RoleResponse, PermissionResponse,
    │                     HealthResponse) — audit columns deliberately excluded
    ├── foundation.py     11 plain Pydantic models, one per exposed table/view — audit columns,
    │                     `current_value`, and unimplemented FK columns deliberately excluded
    └── organization.py   4 Pydantic models (OrganizationTypeResponse,
                          StatusResponse, OrganizationResponse,
                          OrganizationHierarchyNodeResponse) — OrganizationResponse includes
                          contact/online-presence fields (phone_number, mobile_number, email,
                          org_email, website_url, org_website_url, youtube_channel_url,
                          org_youtube_channel_url)
```

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
   `Cache-Control: no-store` on `/api/*` responses only. Deliberately skips `X-XSS-Protection`
   (obsolete), CSP (deferred — Tailwind Play CDN's inline styles conflict with a strict policy),
   and HSTS (left to Render's edge TLS).

Verified by `tests/test_security.py` (8 tests, 3 classes). Full walkthrough:
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
| GET | `/api/v1/bootstrap/roles` | The 8 frozen roles from `nss.role_master` |
| GET | `/api/v1/bootstrap/permissions` | `nss.permission_master` rows (empty by design — catalogue not frozen yet) |
| GET | `/api/v1/bootstrap/roles/{role_pk}/permissions` | Permissions mapped to a role (empty — no `role_permission` rows exist yet); 404 if `role_pk` doesn't match an active role |

All four are unauthenticated and read-only — they exist to verify the RBAC schema is queryable,
not to enforce RBAC.

## Endpoints (Tier 1)

17 read-only endpoints under `/api/v1/foundation`, across 11 tables — no auth, no ORM, raw
parameterized SQL. Grouped by theme:

| Group | Endpoints |
|-------|-----------|
| Master data | `/categories`, `/categories/{pk}`, `/master-data` (filter by `category_code`/`category_pk`), `/master-data/{pk}` |
| System config | `/settings`, `/settings/{setting_key}`, `/sequences` (excludes `current_value`) |
| Geographic | `/countries`, `/countries/{pk}`, `/states`, `/states/{pk}`, `/districts`, `/districts/{pk}`, `/cities`, `/postal-codes`, `/postal-code-mappings` |
| Runtime | `/documents` |

`nss.field_change_log` is deliberately not exposed — deferred to Tier 5 (needs auth). All list
endpoints filter `is_active = TRUE` (except the postal-code-mapping junction table, which has no
such column); detail endpoints 404 on missing/inactive rows. Full contract:
`docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`. Verified by 59 pytest integration
tests (`tests/test_foundation.py`).

## Endpoints (Tier 2)

6 read-only endpoints under `/api/v1/organization` — no auth, no ORM, raw
parameterized SQL. Organization type values come from Foundation `master_data`
(category `ORGANIZATION_TYPE`). Status values come from the unified ERP-wide
`STATUS` category. Organization LEFT JOINs
Foundation's geography tables (country, state, district, city_village, postal_code)
for address resolution, since those FKs are nullable.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/organization/types` | The 10 frozen organization types from `nss.master_data` (category `ORGANIZATION_TYPE`) |
| GET | `/api/v1/organization/statuses` | The 13 unified lifecycle statuses from `nss.master_data` (category `STATUS`) |
| GET | `/api/v1/organization/organizations` | Organizations with resolved type/status/parent/geography context; optional `type_code`/`status_code` filters |
| GET | `/api/v1/organization/organizations/{organization_pk}` | Single organization detail; 404 if missing/inactive |
| GET | `/api/v1/organization/organizations/{organization_pk}/children` | Direct children of an organization; 404 if the parent `organization_pk` doesn't exist |
| GET | `/api/v1/organization/hierarchy` | Full organization tree as a flat list with a `depth` field, via a `WITH RECURSIVE` CTE |

All list endpoints filter `is_active = TRUE`; detail/children endpoints 404 on a missing parent.
Full contract: `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`. Verified by 51 pytest
integration tests (`tests/test_organization.py`).

See `docs/PROJECT_DOCUMENTATION.md` → Key workflows for more detail on all three tiers.
