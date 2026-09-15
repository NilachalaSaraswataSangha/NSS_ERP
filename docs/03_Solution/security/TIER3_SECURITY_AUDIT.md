# Tier 3 — Person Security Audit

| Field       | Value                                    |
|-------------|------------------------------------------|
| Document    | TIER3_SECURITY_AUDIT                     |
| Version     | 1.1                                      |
| Tier        | 3 — Person                               |
| Status      | Complete                                 |

---

## 1. Scope

This audit covers all code introduced in the Tier 3 Person vertical slice:

| File                                | What                                        |
|-------------------------------------|---------------------------------------------|
| `api/schemas/person.py`            | 3 Pydantic response models                  |
| `api/routers/person.py`            | 4 GET endpoint handlers (shared helpers)    |
| `api/helpers.py`                   | Shared cursor→Pydantic helpers + pagination |
| `api/main.py`                      | Router registration + HTML route (updated)  |
| `frontend/person.html`             | Person Verification UI                      |
| `frontend/assets/js/person.js`     | Alpine.js data component                    |
| `tests/test_person.py`             | 49 integration tests                        |
| `database/ddl/03_person/*.sql`     | 2 table DDL files                           |

**Out of scope:** Tier 0/1/2 code (audited separately), Foundation DDL referenced by Person FKs (audited in Tier 1), deployment configuration.

---

## 2. Audit Results

### 2.1 PASSED — No Vulnerabilities Found

| #  | Area                          | Technique                                | Verdict |
|----|-------------------------------|-----------------------------------------|---------|
| 1  | SQL Injection                 | All 4 endpoints use `%s` parameterised placeholders via psycopg2. `_PERSON_DETAIL_SELECT`, `_PERSON_SUMMARY_SELECT`, and `_ADDRESS_SELECT` are static string constants, not user-influenced. The `list_persons` endpoint dynamically appends `AND` clauses for `gender_code`, `marital_status_code`, and `blood_group_code` filters — but the filter values are always passed through `params.append()` and `cur.execute(sql, tuple(params))`, never interpolated into the SQL string. | PASS |
| 2  | SQL Injection — Trigram Search | The `search_persons` endpoint constructs a `prefix_pattern = f"{q}%"` for ILIKE matching. Verified: this pattern is passed as a `%s` parameter to `cur.execute()`, never interpolated into the SQL string. The trigram operators (`%%`, `similarity()`) are static SQL syntax. The `q` parameter enters only via positional `%s` placeholders (5 uses in the execute call). | PASS |
| 3  | Sensitive Data Protection     | **Critical for this tier.** `aadhaar_encrypted` (BYTEA) and `aadhaar_hash` (VARCHAR) are present in the DDL but deliberately excluded from all 3 SQL SELECT fragments (`_PERSON_DETAIL_SELECT`, `_PERSON_SUMMARY_SELECT`, `_ADDRESS_SELECT`). They do not appear in any Pydantic response model. Only `aadhaar_last4` (4-character masked suffix) is selected and returned — and only in `PersonResponse` (detail), not in `PersonSummaryResponse` (list/search). The UI displays this as "XXXX XXXX 1234" via client-side `x-text` template. Verified by `test_list_excludes_sensitive_aadhaar`, `test_detail_excludes_sensitive_aadhaar`, and `test_search_returns_summary_fields`. | PASS |
| 4  | Audit Column Exclusion        | `PersonResponse` (28 DB columns → 22 exposed fields) excludes all 6 audit columns: `created_at`, `updated_at`, `deleted_at`, `created_by_sangha_sevi_pk`, `updated_by_sangha_sevi_pk`, `deleted_by_sangha_sevi_pk`. `PersonSummaryResponse` (16 fields) and `PersonAddressResponse` (17 fields) similarly exclude them. All 3 SQL SELECT fragments confirm — no audit column is selected. Verified by `test_list_excludes_audit_columns`, `test_detail_excludes_audit_columns`, `test_search_excludes_audit_columns`. | PASS |
| 5  | Credential Leakage            | No new credentials introduced. Person router imports only `get_connection` from `api.database` — same SELECT-only `nss_db_backend` pool used by Tier 0/1/2. No new `.env` variables. | PASS |
| 6  | Error / Stack Trace Leakage   | 404 responses use a single generic message: `"Person not found"` (detail and addresses endpoints). No database error details, connection strings, or stack traces leak through any error path. | PASS |
| 7  | XSS via API Response          | All 4 endpoints return JSON (`Content-Type: application/json`). Pydantic models enforce typed fields (UUID, str, int, bool, date). No raw HTML rendering from user input. Frontend uses Alpine.js `x-text` exclusively (auto-escapes HTML entities) — zero uses of `x-html`, `innerHTML`, `eval()`, `document.write()`, or `Function()` in `person.js`. The Aadhaar masked display (`'XXXX XXXX ' + selectedPerson.aadhaar_last4`) uses string concatenation with `x-text`, not `x-html`. | PASS |
| 8  | Database Privilege Scope      | `nss_db_backend` has SELECT-only privileges (`04_grant_backend.sql` with `ALTER DEFAULT PRIVILEGES`). Person router has zero INSERT/UPDATE/DELETE statements. Even if an attacker could inject SQL (they can't — see #1), no write operation would execute. | PASS |
| 9  | UUID Validation               | `person_pk: UUID` path parameter in `get_person` and `list_person_addresses` causes FastAPI to return 422 for malformed UUIDs. Verified by `test_detail_bad_uuid_returns_422` and `test_addresses_bad_uuid_returns_422`. | PASS |
| 10 | Person Existence Check        | `list_person_addresses` verifies the person exists (`SELECT 1 FROM nss.person WHERE person_pk = %s AND is_active = TRUE`) before querying addresses. Without this, any UUID — valid or not — would return `200 []`, making "person exists with no addresses" indistinguishable from "person doesn't exist." Verified by `test_addresses_fake_pk_returns_404`. | PASS |
| 11 | Search Input Validation       | The `q` query parameter has `min_length=2` (FastAPI/Pydantic validation), preventing single-character or empty searches that could be expensive trigram scans. Verified by `test_search_min_length_validation` and `test_search_requires_query`. Results are capped at `LIMIT 50` in the SQL. | PASS |
| 12 | Query Parameter Scope         | `gender_code`, `marital_status_code`, and `blood_group_code` are the only query parameters accepted on `/persons` (via `Query(None)`). `/search` accepts only `q` (required). FastAPI ignores unrecognised query parameters by default — no mass-assignment or parameter pollution risk. | PASS |
| 13 | Connection Management         | All 4 endpoints use `with conn.cursor() as cur:` context managers. `get_connection` (Tier 0 code) uses `try/finally` to guarantee `pool.putconn(conn)`. The `list_person_addresses` endpoint opens two cursor blocks sequentially (existence check, then address query) on the same connection — both wrapped in `with`, no leak path. | PASS |
| 14 | CDN SRI Pinning               | `frontend/person.html` uses the identical `<head>` CDN block as Tier 0/1/2 pages: DaisyUI 4.12.14 with `integrity="sha384-..."` + `crossorigin="anonymous"`, Alpine.js 3.14.8 with same SRI pattern. Tailwind Play CDN has no SRI (JIT compiler — expected). No new CDN dependencies introduced. | PASS |
| 15 | Security Headers              | Person API endpoints (`/api/v1/person/*`) inherit the global security middleware: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`. `Cache-Control: no-store` applied to `/api/*` paths only. Verified by 5 dedicated tests in `TestPersonSecurity`. | PASS |
| 16 | DDL Security — Aadhaar        | `02_person.sql` stores Aadhaar encrypted (`aadhaar_encrypted BYTEA` — application-layer encryption via pgcrypto `pgp_sym_encrypt`), hashed (`aadhaar_hash VARCHAR(64)` — SHA-256 for duplicate detection), and masked (`aadhaar_last4 CHAR(4)` — display-only). CHECK constraint: `aadhaar_last4 ~ '^\d{4}$'` ensures only 4 digits are stored. The encrypted and hash columns are never readable via the API (`nss_db_backend` has only SELECT; application layer never SELECTs them). | PASS |
| 17 | DDL Security — Format Checks  | `02_person.sql` includes CHECK constraints on: `mobile_number` (digits/spaces/dashes, 7-15 chars), `email` (basic `@` and `.` check), `country_phone_code` (`+` prefix, 1-4 digits), `emergency_contact_phone` (same as mobile). These are schema-level safety nets active from day one of writes, independent of API-layer Pydantic validation (deferred to Tier 5). | PASS |
| 18 | `_rows_to_models` Duplication | Person router duplicates the `_rows_to_models`/`_row_to_model` helper functions from earlier routers. Not a security risk — they're pure data-mapping functions with no side effects — but noted as continued duplication (see Tier 2 advisory A4). | PASS |

### 2.2 ADVISORY — Deployment Hardening

| #  | Area                    | Status       | Resolution                                                                                           |
|----|-------------------------|--------------|------------------------------------------------------------------------------------------------------|
| A1 | Pagination              | **RESOLVED** | `list_persons` now accepts `limit` (1–500, default 100) and `offset` (≥0) query parameters via `api.helpers.DEFAULT_LIMIT` / `MAX_LIMIT`. FastAPI's `Query(ge=1, le=500)` enforces bounds (422 on violation). SQL appends `LIMIT %s OFFSET %s` with parameterised values. 7 pagination tests added in `test_person.py`. |
| A2 | Search Result Limit     | **RESOLVED** | `search_persons` retains `LIMIT 50`. `list_persons` now has pagination (A1). Both list and search endpoints are bounded. |
| A3 | Aadhaar Encryption Key  | **ADVISORY** | The DDL defines `aadhaar_encrypted BYTEA` for pgcrypto symmetric encryption, but the encryption key management strategy is not yet defined. No write endpoints exist (Tier 3 is read-only), so this is a Tier 5+ concern. The encryption key must never be stored in the database or `.env` alongside `DB_PASSWORD`. |
| A4 | Filter Value Logging    | **ADVISORY** | `gender_code`, `marital_status_code`, `blood_group_code`, and `q` query parameters are logged by uvicorn's access log (they appear in the URL). Gender and medical data (blood group) are personal data under Indian data protection law. When the system goes live, consider suppressing query parameters from access logs or using POST for search. No action needed for the current read-only verification tier. |
| A5 | Helper Duplication      | **RESOLVED** | Extracted to `api/helpers.py` as `rows_to_models()` and `row_to_model()`. All 4 routers (bootstrap, foundation, organization, person) now import from the shared module. Pagination constants (`DEFAULT_LIMIT`, `MAX_LIMIT`) are also centralised there. |

---

## 3. Verdict

**No blocking vulnerabilities.** The Tier 3 Person codebase is safe for local development, integration testing, and deployment to Render/Neon.

All 18 checks passed. No fixes required. The Person tier introduces the project's first sensitive PII handling (Aadhaar) and the audit confirms the defence-in-depth strategy works: encrypted at rest (DDL), never selected by the API (SQL), never modelled in the response (Pydantic), never rendered in the UI (no `aadhaar_encrypted`/`aadhaar_hash` references in HTML/JS). 3 of 5 advisory items resolved (pagination, search limit, helper deduplication); 2 awareness-only items retained (Aadhaar key management deferred to Tier 5+, filter value logging).

### Security Posture Summary

```
Attack Surface          Protection
─────────────────       ──────────────────────────────────────
SQL injection           Parameterised queries (%s) in all 4 endpoints,
                        including dynamic WHERE clauses and trigram search
Credential exposure     No new credentials; reuses nss_db_backend pool
Error leakage           Generic 404 messages; no stack traces
Privilege escalation    nss_db_backend = SELECT-only; zero write SQL
XSS                     JSON API + Alpine.js x-text (auto-escape)
UUID tampering          FastAPI type validation (422 on malformed)
Unauthorised writes     No POST/PATCH/DELETE endpoints exist
Audit data exposure     All 6 audit columns excluded from all 3 models
Aadhaar data leak       encrypted+hash never in SELECT/model/UI;
                        only aadhaar_last4 in detail (not list/search)
Search abuse            min_length=2 + LIMIT 50 caps scan cost
Person spoofing         Existence check before address query (404 guard)
CDN supply chain        SRI hashes on DaisyUI + Alpine.js (identical to T0/T1/T2)
```

---

## 4. Test Coverage for Security

5 dedicated security tests in `test_person.py::TestPersonSecurity` verify that the global security middleware applies to Person endpoints:

| Test                                          | What It Prevents                              |
|-----------------------------------------------|-----------------------------------------------|
| `test_person_api_has_security_headers`        | Missing/wrong security headers on Person API  |
| `test_person_api_has_cache_control_no_store`  | Stale API responses served from cache         |
| `test_person_ui_no_cache_control_no_store`    | Incorrect `no-store` on cacheable UI page     |
| `test_search_has_security_headers`            | Missing headers on search endpoint            |
| `test_404_has_security_headers`               | Missing headers on error responses            |

Additionally, the broader `test_person.py` test suite (49 tests) provides indirect security coverage:

| Test                                          | Security Aspect Covered                       |
|-----------------------------------------------|-----------------------------------------------|
| `test_detail_fake_pk_returns_404`             | PK enumeration returns generic error          |
| `test_detail_bad_uuid_returns_422`            | Malformed UUID rejected at framework level    |
| `test_addresses_fake_pk_returns_404`          | Person existence guard prevents silent 200    |
| `test_addresses_bad_uuid_returns_422`         | Malformed UUID in addresses route rejected    |
| `test_list_excludes_audit_columns`            | Audit columns not accidentally exposed        |
| `test_detail_excludes_audit_columns`          | Audit columns not in detail response          |
| `test_search_excludes_audit_columns`          | Audit columns not in search results           |
| `test_list_excludes_sensitive_aadhaar`        | aadhaar_encrypted/hash never in list          |
| `test_detail_excludes_sensitive_aadhaar`      | aadhaar_encrypted/hash never in detail        |
| `test_search_returns_summary_fields`          | aadhaar fields not in search results          |
| `test_search_requires_query`                  | Empty search rejected (422)                   |
| `test_search_min_length_validation`           | Single-char search rejected (422)             |
| `test_filter_nonexistent_gender_returns_empty`| Non-matching filter returns `[]`, not error   |

These tests run on every `pytest` invocation. If any fails, the build breaks before the regression can be deployed.
