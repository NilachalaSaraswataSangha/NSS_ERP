# NSS ERP — Security Audit (Tier 0–4)

---

## Document Metadata

| Item | Value |
|---|---|
| Document Name | Security Audit — Tier 0–4 |
| Document ID | SOL-SEC-002 |
| Domain | Cross-Module |
| Repository Path | docs/03_Solution/security/SECURITY_AUDIT_TIER0_4.md |
| Version | 1.0.0 |
| Status | Current |
| Audit Date | 2026-09-13 |
| Scope | All API endpoints, middleware, database access (Tiers 0–4) |

---

# 1. Purpose

This document records the security posture of the NSS ERP across Tiers
0–4 (Bootstrap, Foundation, Organization, Person, Family, Membership).

It assesses what security controls are in place, what is intentionally
deferred, and what requires attention.

---

# 2. Security Controls — Implemented

## 2.1 HTTP Security Headers

All responses (API and frontend) include:

| Header | Value | Mitigation |
|---|---|---|
| X-Content-Type-Options | `nosniff` | MIME-sniffing attacks |
| X-Frame-Options | `DENY` | Clickjacking |
| Referrer-Policy | `strict-origin-when-cross-origin` | URL path leakage |
| Permissions-Policy | `camera=(), microphone=(), geolocation=()` | Device API abuse |

**Status:** PASS — verified by `test_security.py` and per-module test suites.

## 2.2 Cache Control

| Scope | Cache-Control | Status |
|---|---|---|
| API responses (`/api/*`) | `no-store` | PASS — prevents stale data |
| Frontend routes | Not set (browser default) | PASS — allows asset caching |

**Status:** PASS — verified by tests.

## 2.3 Rate Limiting

| Control | Implementation |
|---|---|
| Library | `slowapi` (token bucket) |
| Default limit | `60/minute` per IP |
| Configuration | `RATE_LIMIT` env var |
| Exceeded response | `429 Too Many Requests` |

**Status:** PASS — verified by `test_security.py::TestRateLimiting`.

## 2.4 CORS

| Control | Implementation |
|---|---|
| Default | No CORS headers (no origins configured) |
| Configuration | `CORS_ORIGINS` env var (comma-separated) |
| Methods allowed | `GET` only |

**Status:** PASS — restrictive by default. Origins must be explicitly configured.

## 2.5 Database Access Control

| Control | Implementation |
|---|---|
| DB user | `nss_db_backend` |
| Privileges | SELECT-only on `nss.*` schema |
| Connection pool | `psycopg2.pool.SimpleConnectionPool` (min=1, max=5) |
| Query style | Parameterized queries (no string interpolation) |

**Status:** PASS — the API cannot INSERT, UPDATE, DELETE, or DROP.

## 2.6 Sensitive Data Protection

| Data | Protection | Status |
|---|---|---|
| `aadhaar_encrypted` | Never returned by any endpoint | PASS |
| `aadhaar_hash` | Never returned by any endpoint | PASS |
| `aadhaar_last4` | Detail endpoint only (not in list/search) | PASS |
| Audit actor PKs | Excluded from all responses | PASS |

**Status:** PASS — verified by `test_person.py` and `test_membership.py`.

## 2.7 Input Validation

| Control | Implementation |
|---|---|
| Path parameters | UUID validation via FastAPI/Pydantic → 422 on invalid |
| Query parameters | Type + range validation (ge, le, min_length) → 422 |
| SQL injection | Parameterized queries (`%s` placeholders) — no string formatting |

**Status:** PASS.

## 2.8 API Documentation Toggle

| Control | Implementation |
|---|---|
| `DISABLE_DOCS=true` | Hides `/docs`, `/redoc`, `/openapi.json` |
| Default | Enabled (development mode) |

**Status:** PASS.

---

# 3. Security Controls — Intentionally Deferred

These controls are documented as requirements in SECURITY_ARCHITECTURE.md
but not yet implemented. All are scoped to Tier 5+.

| Control | Deferred To | Rationale |
|---|---|---|
| Authentication (login) | Tier 5 | Current API is read-only verification; no write operations |
| Authorization (RBAC enforcement) | Tier 5 | No write operations to protect yet |
| HTTPS / HSTS | Deployment platform | Render/hosting adds TLS automatically |
| Content-Security-Policy (CSP) | Tier 5 | Tailwind moved from CDN to a pre-built stylesheet (uncommitted, `develop`), removing the original blocker, but a full audit of remaining inline styles (e.g. Alpine.js `x-cloak`) hasn't happened; CSP still needs a nonce strategy |
| Row-Level Security (RLS) | Tier 5 | No multi-tenant access yet |
| Session management | Tier 5 | No login sessions exist |
| MFA | Tier 5 | Requires authentication first |

**Assessment:** These deferrals are appropriate for a read-only
verification API. No write operations exist. The database user has
SELECT-only privileges. Authentication becomes critical when write
endpoints are added.

---

# 4. Potential Improvements

## 4.1 Low Priority (Current Tier)

| Item | Description | Risk |
|---|---|---|
| HTTPS enforcement | Add `Strict-Transport-Security` header if not auto-added by hosting | Low — hosting handles TLS |
| Request logging | Log request paths + response codes for audit trail | Low — no auth to track yet |
| Error message leakage | 500 errors may expose internal stack traces in dev mode | Low — FastAPI debug mode is dev-only |

## 4.2 Required Before Tier 5

| Item | Description | Priority |
|---|---|---|
| Authentication middleware | JWT or session-based auth for write endpoints | Critical |
| RBAC enforcement | Per-endpoint permission checks | Critical |
| CSP headers | Content-Security-Policy with nonce for inline scripts | High |
| Audit logging | Log who accessed what (after auth exists) | High |
| Password storage | Argon2 hashing (documented in Auth module specs) | Critical |

---

# 5. Test Coverage

| Test File | Scope | Tests |
|---|---|---|
| `test_security.py` | Global security middleware | 5 tests (headers, cache, rate limit, CORS) |
| `test_bootstrap.py` | Tier 0 endpoints | Security header verification |
| `test_foundation.py` | Tier 1 endpoints | Audit column exclusion |
| `test_organization.py` | Tier 2 endpoints | Security headers, cache control |
| `test_person.py` | Tier 3 endpoints | Aadhaar exclusion, security headers |
| `test_family.py` | Tier 4 Family endpoints | Security headers, audit exclusion |
| `test_membership.py` | Tier 4 Membership endpoints | Security headers, audit exclusion |

All security-relevant assertions are tagged with `pytest.mark.integration`.

---

# 6. Database Security Summary

```text
Application Layer
    │
    ├── FastAPI security middleware (headers, rate limiting, CORS)
    │
    ├── Pydantic response models (field-level filtering — no audit cols, no Aadhaar)
    │
    ├── Parameterized SQL (psycopg2 %s placeholders — no injection)
    │
    └── Connection pool → nss_db_backend user
                              │
                              └── GRANT SELECT ON ALL TABLES IN SCHEMA nss
                                  (no INSERT, UPDATE, DELETE, DROP, TRUNCATE)
```

---

# 7. Conclusion

The Tier 0–4 API has a **sound read-only security posture**:

- All responses include protective HTTP headers
- API responses are not cached
- Rate limiting prevents abuse
- Database access is restricted to SELECT
- Sensitive data (Aadhaar) is excluded from API responses
- SQL injection is prevented by parameterized queries
- Input validation returns 422 on malformed requests

Authentication and authorization are appropriately deferred to Tier 5,
when write operations will be introduced.

---

# End of Document
