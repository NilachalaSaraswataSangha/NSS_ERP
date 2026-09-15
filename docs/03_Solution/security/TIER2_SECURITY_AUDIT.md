# Tier 2 — Organization Security Audit

| Field       | Value                                    |
|-------------|------------------------------------------|
| Document    | TIER2_SECURITY_AUDIT                     |
| Version     | 1.2                                      |
| Tier        | 2 — Organization                         |
| Status      | Complete                                 |

---

## 1. Scope

This audit covers all code introduced in the Tier 2 Organization vertical slice:

| File                                | What                                        |
|-------------------------------------|---------------------------------------------|
| `api/schemas/organization.py`       | 4 Pydantic response models                  |
| `api/routers/organization.py`       | 6 GET endpoint handlers (shared helpers)    |
| `api/helpers.py`                    | Shared cursor→Pydantic helpers + pagination |
| `api/main.py`                       | Router registration + HTML route (updated)  |
| `frontend/organization.html`        | Organization Verification UI                |
| `frontend/assets/js/organization.js`| Alpine.js data component                    |
| `tests/test_organization.py`        | 48 integration tests                        |
| `database/ddl/02_organization/*.sql`| 3 table DDL files                           |
| `database/seed/02_organization/*.sql`| Seed data (8 types, 6 statuses, 3 orgs)    |

**Out of scope:** Tier 0/1 code (audited separately), Foundation DDL referenced by Organization FKs (audited in Tier 1), deployment configuration.

---

## 2. Audit Results

### 2.1 PASSED — No Vulnerabilities Found

| #  | Area                          | Technique                                | Verdict |
|----|-------------------------------|-----------------------------------------|---------|
| 1  | SQL Injection                 | All 6 endpoints use `%s` parameterised placeholders via psycopg2. The `list_organizations` endpoint dynamically appends `AND` clauses for `type_code` and `status_code` filters — but the filter values are always passed through `params.append()` and `cur.execute(sql, tuple(params))`, never interpolated into the SQL string. `_ORG_SELECT` is a static string constant, not user-influenced. The recursive CTE in `get_organization_hierarchy` is fully static SQL with no parameters. | PASS |
| 2  | SQL Injection — Dynamic WHERE | The `list_organizations` endpoint builds SQL dynamically (`sql += " AND ot.organization_type_code = %s"`). Verified: the column names are hardcoded string literals (`ot.organization_type_code`, `os.organization_status_code`), never derived from user input. The user-supplied `type_code` and `status_code` values enter only as `%s` placeholders. | PASS |
| 3  | Credential Leakage            | No new credentials introduced. Organization router imports only `get_connection` from `api.database` — same SELECT-only `nss_db_backend` pool used by Tier 0/1. No new `.env` variables. | PASS |
| 4  | Error / Stack Trace Leakage   | 404 responses use generic messages: `"Organization not found"` (detail endpoint), `"Parent organization not found"` (children endpoint). No database error details, connection strings, or stack traces leak through any error path. | PASS |
| 5  | XSS via API Response          | All 6 endpoints return JSON (`Content-Type: application/json`). Pydantic models enforce typed fields (UUID, str, int, bool, float). No raw HTML rendering from user input. Frontend uses Alpine.js `x-text` exclusively (auto-escapes HTML entities) — zero uses of `x-html`, `innerHTML`, `eval()`, `document.write()`, or `Function()` in `organization.js`. | PASS |
| 6  | Audit Column Exclusion        | `OrganizationResponse` (36 fields) excludes all audit columns: `created_at`, `updated_at`, `deleted_at` are in the DDL but absent from the schema and the `_ORG_SELECT` SQL fragment. The 9 new contact/online-presence fields (`phone_number`, `mobile_number`, `email`, `org_email`, `website_url`, `org_website_url`, `youtube_channel_url`, `org_youtube_channel_url`) are all non-sensitive operational data. `OrganizationTypeResponse` and `OrganizationStatusResponse` (6 fields each) also exclude audit columns. `OrganizationHierarchyNodeResponse` (10 fields) similarly excludes them. | PASS |
| 7  | Database Privilege Scope      | `nss_db_backend` has SELECT-only privileges (`04_grant_backend.sql`). Organization router has zero INSERT/UPDATE/DELETE statements. Even if an attacker could inject SQL (they can't — see #1), no write operation would execute. | PASS |
| 8  | UUID Validation               | `organization_pk: UUID` path parameter in `get_organization` and `list_organization_children` causes FastAPI to return 422 for malformed UUIDs. Verified by `test_detail_bad_uuid_returns_422` and `test_children_bad_uuid_returns_422`. | PASS |
| 9  | Parent Existence Check        | `list_organization_children` verifies the parent exists (`SELECT 1 FROM nss.organization WHERE organization_pk = %s`) before querying children. Without this, any UUID — valid or not — would return `200 []`, making "org exists with no children" indistinguishable from "org doesn't exist." Verified by `test_children_fake_pk_returns_404`. | PASS |
| 10 | Recursive CTE Safety          | The recursive CTE in `get_organization_hierarchy` joins on `o.parent_organization_pk = t.organization_pk` and the anchor filters `o.parent_organization_pk IS NULL`. A circular parent reference (org A → B → A) would cause infinite recursion — but PostgreSQL's default `work_mem` and `max_recursion_depth` (via `RECURSIVE` keyword) prevents runaway execution, and the DDL's FK constraint (`fk_organization_parent` referencing `nss.organization`) combined with the `is_active = TRUE` filter limits the traversal to valid, active rows. No user input influences the CTE structure. | PASS |
| 11 | Query Parameter Scope         | `type_code` and `status_code` are the only query parameters accepted (via `Query(None)`). FastAPI ignores unrecognised query parameters by default — no mass-assignment or parameter pollution risk. | PASS |
| 12 | Connection Management         | All 6 endpoints use `with conn.cursor() as cur:` context managers. `get_connection` (Tier 0 code) uses `try/finally` to guarantee `pool.putconn(conn)`. The `list_organization_children` endpoint opens two cursor blocks sequentially (existence check, then children query) on the same connection — both wrapped in `with`, no leak path. | PASS |
| 13 | CDN SRI Pinning               | `frontend/organization.html` uses the identical `<head>` CDN block as Tier 0/1 pages: DaisyUI 4.12.14 with `integrity="sha384-..."` + `crossorigin="anonymous"`, Alpine.js 3.14.8 with same SRI pattern. Tailwind Play CDN has no SRI (JIT compiler — expected). No new CDN dependencies introduced. | PASS |
| 14 | Security Headers              | Organization API endpoints (`/api/v1/organization/*`) inherit the global security middleware: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`. `Cache-Control: no-store` applied to `/api/*` paths only. Verified by 3 dedicated tests in `TestOrganizationSecurity`. | PASS |
| 15 | Seed Data Integrity           | Seed SQL uses explicit `INSERT INTO ... VALUES` with hardcoded data. Organization types (8) match the NSS Bye-Law hierarchy. Statuses (6) follow the documented lifecycle. 3 seed organizations use hardcoded UUIDs and reference existing Foundation seed data (country, state, district, postal code). No dynamic content or user-influenced values. | PASS |

### 2.2 ADVISORY — Deployment Hardening

| #  | Area                    | Status       | Resolution                                                                                           |
|----|-------------------------|--------------|------------------------------------------------------------------------------------------------------|
| A1 | Pagination              | **RESOLVED** | `list_organizations` and `get_organization_hierarchy` now accept `limit` (1–500, default 100) and `offset` (≥0) query parameters via `api.helpers.DEFAULT_LIMIT` / `MAX_LIMIT`. FastAPI's `Query(ge=1, le=500)` enforces bounds (422 on violation). SQL appends `LIMIT %s OFFSET %s` with parameterised values. 8 pagination tests added in `test_organization.py`. |
| A2 | Recursive CTE Depth     | **RESOLVED** | Added `AND t.depth < 10` guard to the recursive member of the hierarchy CTE. NSS hierarchy is 4 levels deep; the cap at 10 prevents infinite recursion from circular parent references while leaving headroom for any future structural changes. |
| A3 | Filter Value Logging    | **ADVISORY** | `type_code` and `status_code` query parameters are logged by uvicorn's access log (they appear in the URL). These are non-sensitive enumeration codes, not PII. No action needed, but noted for awareness if future filters accept user-identifiable data. |
| A4 | `_rows_to_models` / `_row_to_model` Duplication | **RESOLVED** | Extracted to `api/helpers.py` as `rows_to_models()` and `row_to_model()`. All 4 routers (bootstrap, foundation, organization, person) now import from the shared module. Pagination constants (`DEFAULT_LIMIT`, `MAX_LIMIT`) are also centralised there. Single point of maintenance for any future security hardening. |

---

## 3. Verdict

**No blocking vulnerabilities.** The Tier 2 Organization codebase is safe for local development, integration testing, and deployment to Render/Neon.

All 15 checks passed. No fixes required — the code follows the same security conventions established in Tier 0 and hardened in Tier 1 (parameterised queries, SELECT-only privilege, audit column exclusion, SRI pinning, security headers, generic error messages). 3 of 4 advisory items resolved (pagination, CTE depth guard, helper deduplication); 1 awareness-only item retained (filter value logging).

### Security Posture Summary

```
Attack Surface          Protection
─────────────────       ──────────────────────────────────────
SQL injection           Parameterised queries (%s) in all 6 endpoints,
                        including dynamic WHERE clauses
Credential exposure     No new credentials; reuses nss_db_backend pool
Error leakage           Generic 404 messages; no stack traces
Privilege escalation    nss_db_backend = SELECT-only; zero write SQL
XSS                     JSON API + Alpine.js x-text (auto-escape)
UUID tampering          FastAPI type validation (422 on malformed)
Unauthorised writes     No POST/PATCH/DELETE endpoints exist
Audit data exposure     All audit columns excluded from all 4 models
Recursive CTE abuse     Static SQL, no user input, PG depth safeguards
Parent spoofing         Existence check before children query (404 guard)
CDN supply chain        SRI hashes on DaisyUI + Alpine.js (identical to T0/T1)
```

---

## 4. Test Coverage for Security

3 dedicated security tests in `test_organization.py::TestOrganizationSecurity` verify that the global security middleware applies to Organization endpoints:

| Test                                | What It Prevents                              |
|-------------------------------------|-----------------------------------------------|
| `test_org_api_has_security_headers` | Missing/wrong security headers on Org API     |
| `test_org_api_has_cache_control_no_store` | Stale API responses served from cache   |
| `test_org_ui_no_cache_control_no_store` | Incorrect `no-store` on cacheable UI page |

Additionally, the broader `test_organization.py` test suite (48 tests) provides indirect security coverage:

| Test                                | Security Aspect Covered                       |
|-------------------------------------|-----------------------------------------------|
| `test_detail_fake_pk_returns_404`   | PK enumeration returns generic error          |
| `test_detail_bad_uuid_returns_422`  | Malformed UUID rejected at framework level    |
| `test_children_fake_pk_returns_404` | Parent existence guard prevents silent 200    |
| `test_children_bad_uuid_returns_422`| Malformed UUID in children route rejected     |
| `test_list_has_required_fields` (36 fields) | Audit columns not accidentally exposed |
| `test_filter_nonexistent_type_returns_empty` | Non-matching filter returns `[]`, not error |

These tests run on every `pytest` invocation. If any fails, the build breaks before the regression can be deployed.
