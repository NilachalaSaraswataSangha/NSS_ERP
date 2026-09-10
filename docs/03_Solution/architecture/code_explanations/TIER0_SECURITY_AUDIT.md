# Tier 0 — Bootstrap Security Audit

| Field       | Value                                    |
|-------------|------------------------------------------|
| Document    | TIER0_SECURITY_AUDIT                     |
| Version     | 1.0                                      |
| Tier        | 0 — Bootstrap RBAC                       |
| Status      | Complete                                 |

---

## 1. Scope

This audit covers all code in the Tier 0 Bootstrap vertical slice:

| File                              | What                              |
|-----------------------------------|-----------------------------------|
| `api/config.py`                   | Environment-based settings        |
| `api/database.py`                 | psycopg2 connection pool          |
| `api/schemas/bootstrap.py`        | 3 Pydantic response models        |
| `api/routers/bootstrap.py`        | 4 GET endpoint handlers           |
| `api/main.py`                     | App entry point + frontend mount  |
| `frontend/index.html`             | Bootstrap Verification UI         |
| `frontend/assets/js/app.js`       | Alpine.js data component          |
| `frontend/assets/css/style.css`   | Alpine.js cloak directive         |
| `tests/test_bootstrap.py`         | 9 integration tests               |
| `database/scripts/*.sql`          | DB setup scripts                  |
| `database/ddl/00_bootstrap/*.sql` | 3 table DDL files                 |
| `database/seed/00_bootstrap/*.sql`| Seed data (8 roles)               |

**Out of scope:** Render/Neon deployment configuration (covered in DEPLOYMENT_PROCEDURE.md).

---

## 2. Audit Results

### 2.1 PASSED — No Vulnerabilities Found

| #  | Area                        | Technique                                | Verdict |
|----|-----------------------------|-----------------------------------------|---------|
| 1  | SQL Injection               | All queries in `bootstrap.py` use `%s` parameterised placeholders via psycopg2. The role-permissions endpoint passes `str(role_pk)` through `%s` — no string interpolation or f-string SQL. The existence-check query (`SELECT 1 FROM nss.role_master WHERE role_master_pk = %s`) is also parameterised. | PASS |
| 2  | Credential Leakage          | Database credentials read from `api/.env` via `python-dotenv`. No hardcoded passwords, connection strings, or API keys in source. `config.py` defaults sensitive fields to empty string and fails fast via `validate()`. | PASS |
| 3  | `.env` Exposure             | `.env` is in `.gitignore` (line 11). The `.env` file lives inside `api/` which is not served as static — `StaticFiles` only mounts `frontend/assets/`. No route exposes any file from `api/`. | PASS |
| 4  | Error / Stack Trace Leakage | `check_connection()` catches all `Exception` types and returns only a boolean — no error detail, no stack trace, no connection string leakage. Health endpoint returns only `"ok"`/`"degraded"` and `"connected"`/`"unreachable"`. The 404 response for invalid role PK uses a generic message (`"Role not found"`). | PASS |
| 5  | XSS via Frontend            | Alpine.js uses `x-text` throughout (auto-escapes HTML entities). Zero uses of `x-html`, `innerHTML`, `eval()`, `document.write()`, or `Function()` in `app.js`. All API responses are `Content-Type: application/json` — no raw HTML rendering from user input. | PASS |
| 6  | Database Privilege Scope    | `nss_db_backend` has SELECT-only privileges (`04_grant_backend.sql`). `GRANT SELECT ON ALL TABLES` + `ALTER DEFAULT PRIVILEGES ... GRANT SELECT`. No INSERT, UPDATE, or DELETE grants. Even if an attacker could inject SQL (they can't — see #1), no write operation would execute. | PASS |
| 7  | Connection Pool Safety      | `get_connection()` uses `try/finally` to guarantee `pool.putconn(conn)` is called after every request — no connection leak paths. `close_pool()` is called via the FastAPI lifespan handler on shutdown. Pool size is bounded (`maxconn=5`). | PASS |
| 8  | UUID Validation             | `role_pk: UUID` path parameter type annotation causes FastAPI to return 422 Unprocessable Entity for malformed UUIDs. No custom parsing or string manipulation of UUIDs — psycopg2 receives `str(role_pk)` through parameterised queries. | PASS |
| 9  | Seed Data Integrity         | Seed SQL uses explicit `INSERT INTO ... VALUES` with hardcoded data — no dynamic content. Role codes follow the `NSS_ERP_*` naming convention. CHECK constraints enforce valid `role_class` and `scope_level` values at the database level. | PASS |
| 10 | Audit Column Exclusion      | Response models (`RoleResponse`, `PermissionResponse`) exclude all audit columns: `created_at`, `created_by_sangha_sevi_pk`, `updated_at`, `updated_by_sangha_sevi_pk`, `deleted_at`, `deleted_by_sangha_sevi_pk`. Only business-relevant fields are exposed. | PASS |

### 2.2 FIX APPLIED — ConfigDict Removal

| Item | Before | After | Rationale |
|------|--------|-------|-----------|
| `RoleResponse` | `model_config = ConfigDict(from_attributes=True)` | Removed | Raw psycopg2 returns tuples → converted to dicts via `dict(zip(columns, row))` → Pydantic receives keyword arguments. `from_attributes` is ORM plumbing — unnecessary overhead that signals an integration the project doesn't have. Aligned with Tier 1 convention. |
| `PermissionResponse` | `model_config = ConfigDict(from_attributes=True)` | Removed | Same rationale. |
| Import | `from pydantic import BaseModel, ConfigDict` | `from pydantic import BaseModel` | Unused import removed. |

All 9 tests pass after this change (0.10s).

### 2.3 ADVISORY — Deployment Hardening (Not Blocking)

These items are standard production-hardening concerns, not vulnerabilities in the current codebase. All are addressed at deployment time (Tier 5 or infrastructure layer).

| #  | Area                    | Current State                                   | Recommendation                                     | When          |
|----|-------------------------|-------------------------------------------------|-----------------------------------------------------|---------------|
| A1 | CORS Policy             | No CORS middleware configured. Browser same-origin policy applies (frontend served by same FastAPI app). | Add `CORSMiddleware` with explicit `allow_origins` when frontend and API are deployed to different origins. Never use `allow_origins=["*"]`. | Tier 5 / deployment |
| A2 | Rate Limiting           | No rate limiting on any endpoint. All endpoints are read-only and anonymous. | Add rate limiting via reverse proxy (Nginx, Cloudflare) or FastAPI middleware (`slowapi`) before public exposure. | Deployment |
| A3 | Security Headers        | No explicit security headers (`X-Content-Type-Options`, `Strict-Transport-Security`, `X-Frame-Options`). | Add via reverse proxy or FastAPI middleware. Render.com adds HSTS on custom domains by default. | Deployment |
| A4 | CDN Integrity           | Frontend loads Tailwind CSS, DaisyUI, and Alpine.js via CDN (`cdn.jsdelivr.net`, `cdn.tailwindcss.com`) without Subresource Integrity (SRI) hashes. | Add `integrity` and `crossorigin` attributes to CDN `<script>` and `<link>` tags. Low risk for an internal verification UI. | Before public exposure |
| A5 | `psycopg2-binary`       | Using `psycopg2-binary` (pre-compiled). Fine for development and Render deployment. | Consider `psycopg2` (source build against system `libpq`) for production Linux deployments to receive `libpq` security patches. | Production hardening |
| A6 | Swagger UI in Production | `/docs`, `/redoc`, `/openapi.json` are accessible by default. `DISABLE_DOCS` toggle added in Tier 1 but should be set in production. | Set `DISABLE_DOCS=true` in Render environment variables. | Deployment |

---

## 3. Verdict

**No blocking vulnerabilities.** The Tier 0 Bootstrap codebase is safe for local development, integration testing, and deployment to Render/Neon.

One fix applied: removed unnecessary `ConfigDict(from_attributes=True)` to align with the project's no-ORM convention.

The 6 advisory items are deployment-hardening concerns appropriate for Tier 5 (authentication / production infrastructure) or the reverse proxy layer. None affect the read-only Bootstrap verification API.

### Security Posture Summary

```
Attack Surface          Protection
─────────────────       ──────────────────────────────────────
SQL injection           Parameterised queries (%s) — no interpolation
Credential exposure     .env gitignored, not served, no hardcoded secrets
Error leakage           check_connection() returns boolean only;
                        generic 404 messages; no stack traces
Privilege escalation    nss_db_backend = SELECT-only
XSS                     JSON API + Alpine.js x-text (auto-escape)
UUID tampering          FastAPI type validation (422 on malformed)
Unauthorised writes     No POST/PATCH/DELETE endpoints exist
Connection exhaustion   Pool bounded at maxconn=5 with try/finally
Audit data exposure     All audit columns excluded from response models
```
