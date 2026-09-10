# api/

FastAPI application — the only web/API layer in the codebase. Currently implements **Tier 0**
(read-only bootstrap-RBAC) and **Tier 1** (read-only Foundation) — no authentication, no ORM.

An earlier Django prototype lived under `backend/` and covered parts of Foundation,
Authentication, Family, Membership, and Heritage; it was fully archived and removed once the
FastAPI direction (`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md`) was adopted.
`backend/` is now empty.

## Layout

```
api/
├── main.py             FastAPI app entry point — builds `app`, includes both routers, mounts
│                        `frontend/assets/` at `/assets`, serves `frontend/index.html` at `/`
│                        and `frontend/foundation.html` at `/foundation`, closes the DB pool on
│                        shutdown
├── config.py            Settings: DB_NAME/DB_USER/DB_PASSWORD (required), DB_HOST (default
│                        localhost), DB_PORT (default 5432), API_PORT (default 8001),
│                        DISABLE_DOCS (default false) — read from api/.env via python-dotenv
├── database.py          psycopg2 SimpleConnectionPool (1-5 conns), connects as
│                        `nss_db_backend` (read-only); get_connection() is a FastAPI
│                        generator dependency
├── routers/
│   ├── bootstrap.py     4 endpoints under /api/v1/bootstrap — no auth, no ORM, raw
│   │                    parameterized SQL against nss.role_master/permission_master/
│   │                    role_permission
│   └── foundation.py    17 endpoints under /api/v1/foundation across 11 tables — master data,
│                        system config, geography, and runtime document metadata (see below)
└── schemas/
    ├── bootstrap.py      Pydantic response models (RoleResponse, PermissionResponse,
    │                     HealthResponse) — audit columns deliberately excluded
    └── foundation.py     11 plain Pydantic models, one per exposed table/view — audit columns,
                          `current_value`, and unimplemented FK columns deliberately excluded
```

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
`docs/03_Solution/architecture/FOUNDATION_API_CONTRACT.md`. Verified by 47 pytest integration
tests (`tests/test_foundation.py`).

See `docs/PROJECT_DOCUMENTATION.md` → Key workflows for more detail on both tiers.
