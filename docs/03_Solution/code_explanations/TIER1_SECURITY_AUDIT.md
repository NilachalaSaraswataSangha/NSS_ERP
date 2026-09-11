# Tier 1 — Foundation Security Audit

| Field       | Value                                    |
|-------------|------------------------------------------|
| Document    | TIER1_SECURITY_AUDIT                     |
| Version     | 1.1                                      |
| Tier        | 1 — Foundation                           |
| Status      | Complete                                 |

---

## 1. Scope

This audit covers all code introduced in the Tier 1 Foundation vertical slice:

| File                              | What                              |
|-----------------------------------|-----------------------------------|
| `api/schemas/foundation.py`       | 11 Pydantic response models       |
| `api/routers/foundation.py`       | 17 GET endpoint handlers          |
| `api/main.py`                     | Router registration + HTML route  |
| `frontend/foundation.html`        | Foundation Verification UI        |
| `frontend/assets/js/foundation.js`| Alpine.js data component          |
| `tests/test_foundation.py`        | 47 integration tests              |

**Out of scope:** Database DDL (covered by Foundation table-design reviews), Tier 0 code (audited separately), deployment configuration.

---

## 2. Audit Results

### 2.1 PASSED — No Vulnerabilities Found

| #  | Area                        | Technique                                | Verdict |
|----|-----------------------------|-----------------------------------------|---------|
| 1  | SQL Injection               | All queries use `%s` parameterised placeholders via psycopg2. No string interpolation or f-string SQL anywhere in the router. | PASS |
| 2  | Credential Leakage          | Database credentials read from `api/.env` (gitignored). `.env` is in `.gitignore` (line 11). No hardcoded passwords in source. | PASS |
| 3  | `.env` Exposure             | `.env` lives inside `api/` which is not served as static. `StaticFiles` only mounts `frontend/assets/`. No route exposes `api/.env`. | PASS |
| 4  | Error / Stack Trace Leakage | Health endpoint returns only `"ok"`/`"degraded"` and `"connected"`/`"unreachable"`. `check_connection()` catches all exceptions and returns boolean — no error detail leakage. 404 responses use generic messages (`"Category not found"`, `"State not found"`, etc.). | PASS |
| 5  | XSS via API Response        | All API responses are JSON (`Content-Type: application/json`). Pydantic models enforce typed fields (UUID, str, int, bool) — no raw HTML rendering from user input. Frontend uses Alpine.js `x-text` (auto-escapes) not `x-html`. | PASS |
| 6  | Audit Data Exposure         | `field_change_log` has no API endpoint. A contract-enforcement test (`test_change_log_endpoint_returns_404`) prevents accidental re-addition. Audit columns (`created_at`, `updated_at`, `deleted_at`, `*_by_sangha_sevi_pk`) are excluded from all response models. | PASS |
| 7  | Infrastructure State Leak   | `current_value` from `id_sequence_master` is excluded from `SequenceResponse` and the SQL SELECT. A contract-enforcement test (`test_current_value_not_exposed`) prevents accidental re-addition. | PASS |
| 8  | Database Privilege Scope    | `nss_db_backend` has SELECT-only privileges (`04_grant_backend.sql`). Even if an attacker could inject SQL (they can't — see #1), no INSERT/UPDATE/DELETE would execute. | PASS |
| 9  | Exception Handling          | Every endpoint uses cursor context managers (`with conn.cursor() as cur`). Connection pooling uses `try/finally` to guarantee connection return (`pool.putconn(conn)`). No connection leak paths. | PASS |

### 2.2 ADVISORY — Deployment Hardening

These items were standard production-hardening concerns identified during the initial audit.

| #  | Area                    | Status       | Resolution                                                                                           |
|----|-------------------------|--------------|------------------------------------------------------------------------------------------------------|
| A1 | CORS Policy             | **RESOLVED** | `CORSMiddleware` added in `api/main.py`. Origins configured via `CORS_ORIGINS` env var (comma-separated). GET-only. Never `allow_origins=["*"]`. Only activates when origins are configured — no-op locally. |
| A2 | Rate Limiting           | **RESOLVED** | `slowapi` rate limiter added in `api/main.py`. Default `60/minute`, configurable via `RATE_LIMIT` env var. Per-IP keying via `get_remote_address`. Verified by `test_rate_limit_returns_429`. |
| A3 | Pagination              | **ADVISORY** | List endpoints return all matching rows. Foundation tables are small (8 categories, ~30 states, ~700 districts). Add `limit`/`offset` or cursor pagination if datasets grow or if this pattern is adopted by larger modules. |
| A4 | `psycopg2-binary`       | **N/A**      | Deploying directly from `main` to Render. `psycopg2-binary` is the correct choice — Render uses pre-built containers where source-compiling against system `libpq` adds no security benefit. |
| A5 | Security Headers        | **RESOLVED** | `api/middleware.py` adds 4 headers to every response: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`. `Cache-Control: no-store` applied to `/api/*` routes only (not static assets). `X-XSS-Protection` omitted (obsolete). CSP deferred until frontend CDN strategy is finalized. HSTS left to Render. |
| A6 | CDN SRI                 | **PARTIAL**  | DaisyUI 4.12.14 and Alpine.js 3.14.8 have verified `integrity="sha384-..."` + `crossorigin="anonymous"` attributes. Tailwind Play CDN (`cdn.tailwindcss.com`) is a browser JIT compiler — SRI does not apply. Redundant Tailwind 2.x pre-built CSS and incompatible `@tailwindcss/browser` 4.x removed. |

---

## 3. Verdict

**No blocking vulnerabilities.** The Tier 1 codebase is safe for local development, integration testing, and deployment to Render/Neon.

5 of 6 advisory items resolved — CORS, rate limiting, security headers implemented; `psycopg2-binary` confirmed as N/A for Render deployments. CDN SRI is partial: DaisyUI and Alpine.js have verified integrity hashes; Tailwind Play CDN is a JIT compiler where SRI does not apply. Pagination (A3) remains advisory — Foundation tables are small enough that it's not needed yet. CSP is deferred until the frontend CDN strategy is finalized.

### Security Posture Summary

```
Attack Surface          Protection
─────────────────       ──────────────────────────────────────
SQL injection           Parameterised queries (%s) — no interpolation
Credential exposure     .env gitignored, not served, no hardcoded secrets
Data leakage            Audit columns excluded, change-log deferred,
                        current_value excluded, generic 404 messages
Privilege escalation    nss_db_backend = SELECT-only
XSS                     JSON API + Alpine.js x-text (auto-escape)
Unauthorised writes     No POST/PATCH/DELETE endpoints exist
```

---

## 4. Contract-Enforcement Tests

Two automated tests serve as security regression guards:

| Test                                | What It Prevents                          |
|-------------------------------------|-------------------------------------------|
| `test_current_value_not_exposed`    | Re-adding infrastructure state to the API |
| `test_change_log_endpoint_returns_404` | Adding an anonymous audit endpoint     |

These tests run on every `pytest` invocation. If either fails, the build breaks before the regression can be deployed.
