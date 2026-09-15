# Tier 4 — Family & Membership Security Audit

| Field       | Value                                       |
|-------------|---------------------------------------------|
| Document    | TIER4_SECURITY_AUDIT                        |
| Version     | 1.0                                         |
| Tier        | 4 — Family & Membership                     |
| Status      | Complete                                    |

---

## 1. Scope

This audit covers all code introduced in the Tier 4 vertical slice (Family + Membership):

| File                                           | What                                        |
|------------------------------------------------|---------------------------------------------|
| `api/schemas/family.py`                        | 3 Pydantic response models                  |
| `api/routers/family.py`                        | 4 GET endpoint handlers                     |
| `api/schemas/membership.py`                    | 5 Pydantic response models                  |
| `api/routers/membership.py`                    | 7 GET endpoint handlers                     |
| `api/main.py`                                  | Router registration + HTML routes (updated) |
| `frontend/membership.html`                     | Membership Verification UI                  |
| `frontend/assets/js/membership.js`             | Alpine.js data component                    |
| `frontend/family.html`                         | Family Verification UI                      |
| `frontend/assets/js/family.js`                 | Alpine.js data component                    |
| `tests/test_family.py`                         | 51 integration tests                        |
| `tests/test_membership.py`                     | 99 integration tests                        |
| `database/ddl/04_family/*.sql`                 | 4 table DDL files                           |
| `database/ddl/05_membership/*.sql`             | 12 table DDL files                          |

**Out of scope:** Tier 0/1/2/3 code (audited separately), Foundation/Organization/Person DDL referenced by Tier 4 FKs (audited in Tiers 1–3), deployment configuration.

---

## 2. Audit Results

### 2.1 PASSED — No Vulnerabilities Found

| #  | Area                          | Technique                                | Verdict |
|----|-------------------------------|-----------------------------------------|---------|
| 1  | SQL Injection — Core Queries  | All 11 endpoints (4 Family + 7 Membership) use `%s` parameterised placeholders via psycopg2. `_MEMBER_SELECT`, `_FAMILY_SELECT`, and all inline SQL fragments are static string constants, not user-influenced. The `list_members` endpoint dynamically appends `AND` clauses for `type_code`, `status_code`, and `org_code` filters — but values are always passed through `params.append()` and `cur.execute(sql, tuple(params))`, never interpolated. | PASS |
| 2  | SQL Injection — Trigram Search | The `search_members` endpoint constructs `prefix_pattern = f"{q}%"` for ILIKE matching and `name_q = re.split(r'[.@]', q)[0]` for trigram comparison. Both are passed as `%s` parameters to `cur.execute()` — 9 positional placeholders in total. The trigram operators (`similarity()`) and `EXISTS` subquery are static SQL. The `re.split()` call processes `q` purely in Python (no regex injection vector — `re.split` on a literal pattern class `[.@]` cannot be exploited). | PASS |
| 3  | SQL Injection — Subquery      | The `search_members` endpoint includes an `EXISTS (SELECT 1 FROM nss.parichaya_patra pp WHERE pp.sangha_sevi_pk = ss.sangha_sevi_pk AND pp.document_number ILIKE %s)` subquery for Kendra Number search. The `document_number ILIKE %s` uses a parameterised placeholder — the subquery is static SQL with no user-controlled table or column names. | PASS |
| 4  | Audit Column Exclusion        | All 8 Pydantic response models (3 Family + 5 Membership) exclude audit columns: `created_at`, `updated_at`, `deleted_at`, `created_by_sangha_sevi_pk`, `updated_by_sangha_sevi_pk`, `deleted_by_sangha_sevi_pk`. All SQL SELECT fragments confirm — no audit column is selected. Verified by `test_list_excludes_audit_columns` (×2), `test_detail_excludes_audit_columns` (×2), `test_affiliations_excludes_audit_columns`, `test_pp_excludes_audit_columns`, `test_ap_excludes_audit_columns`, `test_journey_excludes_audit_columns`, `test_search_excludes_audit_columns`, `test_members_excludes_audit_columns`, `test_head_history_excludes_audit_columns`. | PASS |
| 5  | Sensitive Data Protection     | No Aadhaar fields (`aadhaar_encrypted`, `aadhaar_hash`, `aadhaar_last4`) are selected in any Tier 4 SQL fragment or returned in any response model. `MemberResponse` includes person fields via JOIN but deliberately selects only `person_id`, `first_name`, `middle_name`, `last_name`, `country_phone_code`, `mobile_number`, `email` — no sensitive Person columns leak through the membership layer. | PASS |
| 6  | Credential Leakage            | No new credentials introduced. Both routers import only `get_connection` from `api.database` — same SELECT-only `nss_db_backend` pool used by all tiers. No new `.env` variables. `import re` in `membership.py` is stdlib-only (no external dependency). | PASS |
| 7  | Error / Stack Trace Leakage   | 404 responses use generic messages: `"Member not found"` (5 endpoints), `"Family not found"` (3 endpoints). No database error details, connection strings, or stack traces leak through any error path. | PASS |
| 8  | XSS via API Response          | All 11 endpoints return JSON (`Content-Type: application/json`). Pydantic models enforce typed fields (UUID, str, date, bool). No raw HTML rendering from user input. Both `membership.js` and `family.js` use Alpine.js `x-text` exclusively (auto-escapes HTML entities) — zero uses of `x-html`, `innerHTML`, `eval()`, `document.write()`, or `Function()`. The `typeDisplayName()` function in `membership.js` substitutes "Darshaka" for PROBATIONARY — a hardcoded string, not user input. | PASS |
| 9  | Database Privilege Scope      | `nss_db_backend` has SELECT-only privileges. Both routers have zero INSERT/UPDATE/DELETE statements. Even if an attacker could inject SQL (they can't — see #1/#2/#3), no write operation would execute. | PASS |
| 10 | UUID Validation               | `sangha_sevi_pk: UUID` and `family_group_pk: UUID` path parameters in all sub-resource endpoints cause FastAPI to return 422 for malformed UUIDs. Verified by `test_detail_bad_uuid_returns_422` (×2), `test_affiliations_bad_uuid_returns_422`, `test_pp_bad_uuid_returns_422`, `test_ap_bad_uuid_returns_422`, `test_journey_bad_uuid_returns_422`, `test_members_bad_uuid_returns_422`, `test_head_history_bad_uuid_returns_422`. | PASS |
| 11 | Member/Family Existence Check | All 9 sub-resource endpoints (5 Membership + 4 Family) verify the parent entity exists (`SELECT 1 ... WHERE pk = %s AND is_active = TRUE`) before querying sub-resources. Without this, any UUID would return `200 []`, making "entity exists with no records" indistinguishable from "entity doesn't exist." Verified by `test_*_fake_pk_returns_404` tests (9 total). | PASS |
| 12 | Search Input Validation       | The `q` query parameter has `min_length=2` and `max_length=100` (FastAPI/Pydantic validation), preventing both empty/single-character searches (expensive trigram scans) and excessively long queries. Verified by `test_search_q_too_short_returns_422`. Results capped at `LIMIT 50` in SQL. | PASS |
| 13 | Query Parameter Scope         | `list_members` accepts `type_code`, `status_code`, `org_code`, `limit`, `offset` via `Query()`. `list_families` accepts `limit`, `offset`. `/search` accepts only `q` (required). FastAPI ignores unrecognised query parameters — no mass-assignment or parameter pollution risk. | PASS |
| 14 | Connection Management         | All 11 endpoints use `with conn.cursor() as cur:` context managers. Sub-resource endpoints open two cursor blocks sequentially (existence check, then data query) on the same connection — both wrapped in `with`, no leak path. `get_connection` (Tier 0 code) uses `try/finally` to guarantee `pool.putconn(conn)`. | PASS |
| 15 | CDN SRI Pinning               | `frontend/membership.html` and `frontend/family.html` use the identical `<head>` CDN block as all prior tier pages: DaisyUI 4.12.14 with `integrity="sha384-..."` + `crossorigin="anonymous"`, Alpine.js 3.14.8 with same SRI pattern. Tailwind Play CDN has no SRI (JIT compiler — expected). No new CDN dependencies introduced. | PASS |
| 16 | Security Headers              | Membership and Family API endpoints inherit the global security middleware: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy: camera=(), microphone=(), geolocation=()`. `Cache-Control: no-store` applied to `/api/*` paths only. Verified by `TestMembershipSecurity` (5 tests) and `TestFamilySecurity` (4 tests). | PASS |
| 17 | Pagination Bounds             | `list_members` and `list_families` accept `limit` (1–500, default 100) and `offset` (≥0) via `Query(ge=..., le=...)`. FastAPI returns 422 on out-of-range values. Verified by `test_pagination_limit_zero_returns_422`, `test_pagination_limit_over_max_returns_422`, `test_pagination_negative_offset_returns_422` (both Family and Membership). | PASS |
| 18 | Trigram False-Positive Guard   | Email-like search queries (containing `.` or `@`) are split before trigram comparison: `name_q = re.split(r'[.@]', q)[0]`. This prevents "aniket.mishra" from trigram-matching "Ramesh Mishra" (similarity of "Mishra" vs "aniket.mishra" = 0.5, above the 0.45 threshold). The full query string is still used for ILIKE prefix matching on email, so exact email prefix search is unaffected. Not a vulnerability but a data-quality safeguard that prevents information leakage through unintended search matches. | PASS |
| 19 | DDL — Membership Tables       | 12 DDL files define the membership schema. `sangha_sevi.person_pk` has a UNIQUE constraint (enforces one-membership-per-person). `membership_sakha_affiliation` has a partial unique index on `(sangha_sevi_pk) WHERE effective_to IS NULL` (enforces one active affiliation). CHECK constraint on `affiliation_status`/`effective_to` consistency. No sensitive columns (Aadhaar) in any membership table. | PASS |
| 20 | DDL — Family Tables           | 4 DDL files define the family schema. Foreign keys reference internal UUIDs (`person_pk`, `family_group_pk`). `family_relationship.relationship_type_master_data_pk` references `master_data` (master-data driven values). No sensitive columns. | PASS |
| 21 | Shared Helper Security        | Both routers import `rows_to_models` and `row_to_model` from `api.helpers` (centralised in Tier 3). These are pure data-mapping functions — they call `cursor.description` to get column names and construct Pydantic models via `**dict(zip(columns, row))`. No SQL execution, no side effects, no user input processing. | PASS |

### 2.2 ADVISORY — Deployment Hardening

| #  | Area                    | Status       | Resolution                                                                                           |
|----|-------------------------|--------------|------------------------------------------------------------------------------------------------------|
| A1 | Pagination              | **RESOLVED** | Both `list_members` and `list_families` accept bounded `limit`/`offset` via `api.helpers.DEFAULT_LIMIT` / `MAX_LIMIT`. Search retains `LIMIT 50`. All list endpoints are bounded. |
| A2 | Helper Duplication      | **RESOLVED** | Both routers import from shared `api/helpers.py`. No duplicated helper functions. |
| A3 | Filter Value Logging    | **ADVISORY** | `type_code`, `status_code`, `org_code`, and `q` query parameters appear in uvicorn access log URLs. Membership type and search terms could be considered personal data context. When the system goes live, consider suppressing query parameters from access logs or using POST for search. No action needed for read-only verification tier. |
| A4 | Contact Data in Search  | **ADVISORY** | `MemberResponse` now includes `mobile_number` and `email` (from person table via JOIN). These are personal contact fields returned in list and search results (not just detail). Currently read-only with no authentication — acceptable for internal verification but should be gated by RBAC when authentication is added in Tier 5. |

---

## 3. Verdict

**No blocking vulnerabilities.** The Tier 4 Family & Membership codebase is safe for local development, integration testing, and deployment to Render/Neon.

All 21 checks passed. No fixes required. Tier 4 is the largest read-only API surface (11 endpoints across 16 DDL tables) and introduces the most complex search logic (7-field trigram + prefix + EXISTS subquery). The audit confirms that the parameterised query discipline established in Tiers 0–3 scales cleanly: no SQL interpolation in any of the 11 endpoints, including the multi-field search with its `re.split()` preprocessing and `EXISTS` subquery.

### Security Posture Summary

```
Attack Surface          Protection
─────────────────       ──────────────────────────────────────
SQL injection           Parameterised queries (%s) in all 11 endpoints,
                        including 9-param search with trigram + EXISTS subquery
Credential exposure     No new credentials; reuses nss_db_backend pool
Error leakage           Generic 404 messages; no stack traces
Privilege escalation    nss_db_backend = SELECT-only; zero write SQL
XSS                     JSON API + Alpine.js x-text (auto-escape);
                        "Darshaka" label is hardcoded, not user input
UUID tampering          FastAPI type validation (422 on malformed)
Unauthorised writes     No POST/PATCH/DELETE endpoints exist
Audit data exposure     All audit columns excluded from all 8 models
Aadhaar data leak       No Aadhaar fields in any Tier 4 SQL or model
Search abuse            min_length=2, max_length=100, LIMIT 50
Entity spoofing         Existence check before all 9 sub-resource queries (404)
Trigram false positive   Email-like queries split before trigram comparison
Contact data scope      mobile/email returned in list/search (RBAC deferred to T5)
CDN supply chain        SRI hashes on DaisyUI + Alpine.js (identical to T0–T3)
Pagination abuse        limit 1–500 enforced; offset ≥ 0; 422 on violation
```

---

## 4. Test Coverage for Security

### 4.1 Membership — `TestMembershipSecurity` (5 dedicated tests)

| Test                                              | What It Prevents                              |
|---------------------------------------------------|-----------------------------------------------|
| `test_membership_api_has_security_headers`        | Missing/wrong security headers on API         |
| `test_membership_api_has_cache_control_no_store`  | Stale API responses served from cache         |
| `test_membership_ui_no_cache_control_no_store`    | Incorrect `no-store` on cacheable UI page     |
| `test_404_has_security_headers`                   | Missing headers on error responses            |
| `test_sub_endpoints_have_security_headers`        | Missing headers on sub-resource 404s          |

### 4.2 Family — `TestFamilySecurity` (4 dedicated tests)

| Test                                              | What It Prevents                              |
|---------------------------------------------------|-----------------------------------------------|
| `test_family_api_has_security_headers`            | Missing/wrong security headers on API         |
| `test_family_api_has_cache_control_no_store`      | Stale API responses served from cache         |
| `test_family_ui_no_cache_control_no_store`        | Incorrect `no-store` on cacheable UI page     |
| `test_404_has_security_headers`                   | Missing headers on error responses            |

### 4.3 Indirect Security Coverage (from broader test suites)

| Test Pattern                                      | Count | Security Aspect Covered                   |
|---------------------------------------------------|-------|-------------------------------------------|
| `test_*_fake_pk_returns_404`                      | 9     | PK enumeration returns generic error      |
| `test_*_bad_uuid_returns_422`                     | 8     | Malformed UUID rejected at framework level|
| `test_*_excludes_audit_columns`                   | 9     | Audit columns not accidentally exposed    |
| `test_search_q_too_short_returns_422`             | 1     | Empty/short search rejected               |
| `test_search_excludes_audit_columns`              | 1     | Audit columns not in search results       |
| `test_search_has_security_headers`                | 1     | Security headers on search endpoint       |
| `test_pagination_*_returns_422`                   | 6     | Out-of-range pagination rejected          |

Total: 150 tests (99 Membership + 51 Family). All run on every `pytest` invocation. If any fails, the build breaks before the regression can be deployed.

---

## 5. Cross-References

- `TIER0_SECURITY_AUDIT.md` — Bootstrap (health, middleware)
- `TIER1_SECURITY_AUDIT.md` — Foundation (master data, geography)
- `TIER2_SECURITY_AUDIT.md` — Organization
- `TIER3_SECURITY_AUDIT.md` — Person (Aadhaar handling)
- `SECURITY_ARCHITECTURE.md` — Project-wide security design
- `SECURITY_AUDIT_TIER0_4.md` — Aggregate summary across all tiers
