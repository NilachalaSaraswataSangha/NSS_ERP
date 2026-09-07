# api/

FastAPI application — the only web/API layer in the codebase. Currently implements **Tier 0**
only: read-only bootstrap-RBAC verification endpoints, no authentication, no ORM.

An earlier Django prototype lived under `backend/` and covered parts of Foundation,
Authentication, Family, Membership, and Heritage; it was fully archived and removed once the
FastAPI direction (`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md`) was adopted.
`backend/` is now empty.

## Layout

```
api/
├── main.py             FastAPI app entry point — builds `app`, includes the bootstrap router,
│                        closes the DB pool on shutdown
├── config.py            Settings: DB_NAME/DB_USER/DB_PASSWORD (required), DB_HOST (default
│                        localhost), DB_PORT (default 5432), API_PORT (default 8001) — read
│                        from api/.env via python-dotenv
├── database.py          psycopg2 SimpleConnectionPool (1-5 conns), connects as
│                        `nss_db_backend` (read-only in Tier 0); get_connection() is a FastAPI
│                        generator dependency
├── routers/
│   └── bootstrap.py     4 endpoints under /api/v1/bootstrap — no auth, no ORM, raw
│                        parameterized SQL against nss.role_master/permission_master/
│                        role_permission
└── schemas/
    └── bootstrap.py      Pydantic response models (RoleResponse, PermissionResponse,
                          HealthResponse) — audit columns deliberately excluded
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

Swagger UI: `http://localhost:8001/docs`.

## Endpoints (Tier 0)

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/v1/bootstrap/health` | `{"status", "database"}` — liveness/DB-connectivity probe |
| GET | `/api/v1/bootstrap/roles` | The 8 frozen roles from `nss.role_master` |
| GET | `/api/v1/bootstrap/permissions` | `nss.permission_master` rows (empty by design — catalogue not frozen yet) |
| GET | `/api/v1/bootstrap/roles/{role_pk}/permissions` | Permissions mapped to a role (empty — no `role_permission` rows exist yet); 404 if `role_pk` doesn't match an active role |

All four are unauthenticated and read-only — they exist to verify the RBAC schema is queryable,
not to enforce RBAC. See `docs/PROJECT_DOCUMENTATION.md` → Key workflows for more detail.
