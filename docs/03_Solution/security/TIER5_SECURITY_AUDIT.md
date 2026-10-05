# Tier 5 Security Audit — Authentication, Administration & Audit

| Field | Value |
|---|---|
| Document | `TIER5_SECURITY_AUDIT.md` |
| Version | 1.2 |
| Status | Complete |
| Tier | 5 — Authentication + Administration + Audit (cross-cutting) |
| Date | 23/09/2026 (v1.0); updated 24/09/2026 (v1.1 — A1 resolution path fixed; v1.2 — advisories worked: A2 implemented, A3 closed as verified no-op, A5 mitigated, A4 raised as an explicit decision) |
| Authority | `IMPLEMENTATION_DEPENDENCY_ORDER.md` §19 (Tier 5 Exit Criteria); SOL-AUTH-001…006; Tier 5 design decisions (15/09/2026); Tier 5.1 self-service reset (20/09/2026) |

---

## 1. Scope

This audit covers all Tier 5 code: the authentication surface, the RBAC
enforcement layer, the administration API, the new authenticated audit-trail
viewer, and the supporting seed data. Tier 5 is the first tier to introduce
authentication and authorization, so it converts the "deferred to Tier 5"
advisories carried by the Tier 0–4 audits into either an implemented control
or an explicitly tracked OPEN item.

### Files in scope

| File | Role |
|---|---|
| `api/services/auth_service.py` | Argon2 hashing, password policy, JWT create/decode, lockout math |
| `api/dependencies/auth.py` | `get_current_user` / `get_optional_user` — JWT extraction + validation, actor session-var injection |
| `api/dependencies/rbac.py` | `require_permission` / `require_any_permission` dependency factories |
| `api/services/rbac_service.py` | `UserContext`, `load_user_context`, permission/scope evaluation |
| `api/routers/auth.py` | login, refresh, logout, change-password, forgot-password, reset-password, me, profile |
| `api/routers/admin.py` | User / role / scope / organization / sangha-sevi administration (permission-gated) |
| `api/routers/audit.py` | **New** — `GET /api/v1/audit/change-log` authenticated audit-trail viewer |
| `api/schemas/audit.py` | **New** — `FieldChangeLogResponse` |
| `api/middleware.py` | Global security headers + cache-control |
| `api/config.py` | Security-relevant settings + `validate` / `validate_auth` startup guards |
| `api/main.py` | Middleware wiring, router registration |
| `database/seed/00_bootstrap/01_permission_master.sql` | Permission catalogue (incl. `AUDIT_VIEW`, `PERSON_VIEW_SENSITIVE`) |
| `database/seed/00_bootstrap/03_role_permission.sql` | Role→permission map |
| `database/seed/04_admin/01_admin_bootstrap.sql` | Initial NSS Admin superuser seed |
| `tests/api/test_audit.py` | **New** — audit-viewer auth/permission/filter tests |

### Out of scope

- Tier 0–4 read-only endpoints and DDL — covered by their own per-tier audits.
- Frontend page logic beyond token handling — verification-UI concern.
- The DB audit trigger `nss.fn_audit_trigger()` internals — DDL-layer control,
  audited with the schema; this document audits the API that *reads* its output.

---

## 2. Audit Results

### 2.1 Passed

| # | Area | Technique / Evidence | Verdict |
|---|---|---|---|
| 1 | Password storage | Argon2 via `argon2.PasswordHasher` (`auth_service.hash_password` / `verify_password`); no plaintext or reversible storage anywhere. `VerifyMismatchError` caught → returns `False`, never leaks. | PASS |
| 2 | Password policy | `validate_password_policy` enforces 8–128 chars, ≥1 uppercase, ≥1 digit against `settings.PASSWORD_MIN/MAX_LENGTH`; applied on every set/change/reset via `validate_and_hash_password`. | PASS |
| 3 | JWT signing | `jwt.encode`/`jwt.decode` with `HS256` and `settings.JWT_SECRET_KEY`. Secret has **no default** — `Settings.validate_auth()` (called by `get_write_pool()`, `database.py:49`) raises `RuntimeError` if `JWT_SECRET_KEY` is unset, so auth/write endpoints cannot run with an empty secret. | PASS |
| 4 | Token typing | Access vs refresh distinguished by `token_type` claim; `get_current_user` rejects a refresh token on a protected route (401), `/refresh` rejects an access token (401). Prevents refresh-token-as-access confusion. | PASS |
| 5 | Session bounds | Access token 30 min, refresh 7 days, plus an **absolute** 30-day session cap enforced inside `decode_token` from the immutable `session_start` claim (preserved across refresh) — a stolen refresh token cannot extend a session indefinitely. | PASS |
| 6 | Account lockout | `is_account_locked` / `calculate_lockout_until`: 5 failed attempts → 30-second lock; counters reset on success. Failed attempts are audit-logged (`LOGIN_FAILED`, `is_success=False`). | PASS |
| 7 | Credential-error uniformity | Unknown login_id, missing account, wrong password, and non-ACTIVE status all return the same `401 "Invalid credentials."` — no username-enumeration oracle on login. | PASS |
| 8 | Reset anti-enumeration | `forgot-password` always returns the same generic message regardless of whether the account exists; `masked_contact` is only populated when resolution succeeds and the raw contact is never returned. | PASS |
| 9 | Reset OTP strength | 6-digit OTP from `secrets.randbelow` (CSPRNG), **hashed** (Argon2) at rest in `password_reset_token`, 15-min expiry, single-use (`is_used`), and prior unused tokens invalidated on re-request. | PASS |
| 10 | Reset rate limiting | Max 3 active OTP requests per user per 60-min window → `429`; independent of the global IP rate limiter, so it survives NAT/shared-IP. | PASS |
| 11 | RBAC enforcement | `require_permission` / `require_any_permission` compose over `get_current_user` (401 first, then 403). Verified every `admin.py` route and the new `audit.py` route carry a permission dependency — no unguarded write/admin endpoint. | PASS |
| 12 | Least-privilege reads | Audit viewer uses the SELECT-only read pool (`get_connection`); it can never write. The change log is populated solely by the DB trigger. | PASS |
| 13 | SQL injection | Audit viewer builds its dynamic `WHERE` from a fixed condition list with `%s` placeholders and a parallel `params` list; `LIMIT`/`OFFSET` are bound, not interpolated. All auth/admin queries parameterized. | PASS |
| 14 | Pagination bounds | Audit `limit` is `Query(ge=1, le=MAX_LIMIT=500)`; `limit=10000` → `422` (test-verified). Prevents unbounded result extraction. | PASS |
| 15 | Audit exposure boundary | Field-change history is reachable **only** via the authenticated `AUDIT_VIEW`-gated `/api/v1/audit/change-log`. The anonymous `/api/v1/foundation/change-log` still does not exist (Tier 1 `TestChangeLogNotExposed` and the new `TestFoundationChangeLogStillHidden` both assert 404/405). | PASS |
| 16 | AUDIT_VIEW seeding | `AUDIT_VIEW` seeded and mapped only to `NSS_ERP_ADMIN`, `NSS_ERP_KENDRA_ADMIN`, `NSS_ERP_AUDITOR` (`03_role_permission.sql`) — audit-trail access is not granted to ordinary member roles. | PASS |
| 17 | Actor attribution | `get_current_user` / `get_optional_user` set `nss.actor_user_account_pk` / `nss.actor_sangha_sevi_pk` via `set_config(..., TRUE)` (transaction-local) so the DB audit trigger records the true actor; not client-supplied. | PASS |
| 18 | Self-service scoping | `/change-password` verifies the current password and rejects reuse (422); `/profile` restricts editable fields to contact/DOB (name changes are admin-only) and runs a duplicate-contact check. Neither lets a user escalate or edit another record. | PASS |
| 19 | Bootstrap hygiene | `04_admin/01_admin_bootstrap.sql` never hardcodes a password hash (`%(password_hash)s` supplied at runtime by `scripts/bootstrap_admin.py`), seeds `force_password_change = TRUE`, and is idempotent (`WHERE NOT EXISTS`). | PASS |
| 20 | Transport & framing headers | `add_security_headers` applies `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` to every response; `Cache-Control: no-store` on `/api/*` so tokens/PII in API responses are not cached. | PASS |
| 21 | Docs toggle | `DISABLE_DOCS=true` removes `/docs`, `/redoc`, `/openapi.json` for production deployments — no schema disclosure. | PASS |

### 2.2 Advisory

| # | Area | Observation | Recommendation | Disposition |
|---|---|---|---|---|
| A1 | **Contact-field RBAC gating** (carried from TIER4 A4) | `person` / `membership` list & search still run anonymously (`get_connection`, no auth dependency) and their responses include `mobile_number` / `email`; the frontend consumes those fields. Gating them now would require authenticating the Tier 1–4 read endpoints, threading `get_optional_user` + `PERSON_VIEW_SENSITIVE` conditionally, and updating the frontend + anonymous tests. | **Resolution path decided (24/09/2026): retirement, not in-place gating.** The Tier 1–4 anonymous verification pages/routers are not being retrofitted with RBAC — they will be **deleted outright** once the Tier 5 authenticated Dashboard (already in progress) reaches feature parity with each page. This avoids maintaining a permanent dual-path (anonymous verification UI + authenticated dashboard) for the same data. Teardown scope per page, once its dashboard equivalent ships: `api/routers/{foundation,organization,person,family,membership}.py` + their `main.py` registrations; `frontend/{foundation,organization,person,family,membership}.html` + serve routes; `tests/api/test_{foundation,organization,person,family,membership}.py` and matching `tests/ui/test_ui_*.py` — deleted alongside, not orphaned. `TIER1_SECURITY_AUDIT.md`–`TIER4_SECURITY_AUDIT.md` are **not** deleted (historical record of the retired surface); each gets a closing note pointing to the dashboard feature that superseded it. `PERSON_VIEW_SENSITIVE` (already seeded to ADMIN/KENDRA_ADMIN/AUDITOR) remains available if a narrower in-dashboard sensitive-field gate is still wanted after retirement. | **OPEN, resolution path fixed** — tracked per-page against dashboard feature parity; final disposition becomes "resolved by page retirement" as each Tier 1–4 page is retired, not "resolved by gating." |
| A2 | Content-Security-Policy | **v1.1 observation was factually wrong and is corrected here.** It claimed "Tailwind now pre-built, no CDN … no third-party script origins remain". Re-verified against source on 24/09/2026: Tailwind *is* pre-built locally, but **Alpine.js 3.14.8 is still loaded from `https://cdn.jsdelivr.net`** (SRI-pinned) on all 10 HTML pages. Also measured: 0 inline `<script>` blocks, 6 inline event handlers (5 `onmouseover`/`onmouseout` pairs + 1 `onfocus`/`onblur` pair in `dashboard.html`) plus 1 `onclick` emitted from a JS HTML-string template in `nss-layout.js`, 1 inline `<style>` block, ~639 inline `style=` attributes, `data:image/svg+xml` URIs inside `tailwind.min.css`, and same-origin-only `fetch()` calls. | **IMPLEMENTED (24/09/2026).** `api/middleware.py:build_csp()` now emits a Content-Security-Policy on every response, derived from the measurements at left — every allowance is present because the frontend provably needs it. Enforced policy: `default-src 'self'; script-src 'self' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'`. **`script-src` deliberately omits `'unsafe-inline'`**, which required removing all 7 inline event handlers first — they were cosmetic hover/focus effects, replaced by CSS state selectors in `nss-layout.css` (`.nss-search-input:focus`, `.nss-hover-fade`, `.nss-pill-btn-{indigo,amber}`, `.nss-icon-btn-danger`, `.nss-row-selectable`), and the injected logout `onclick` replaced by one delegated `data-nss-action` listener in `nss-layout.js`. Env-controlled via `CSP_ENABLED`, `CSP_REPORT_ONLY` (non-blocking rollout), `CSP_SCRIPT_SRC_EXTRA` / `CSP_STYLE_SRC_EXTRA` (adding a CDN is an env change, not a code change). `/docs`, `/redoc`, `/openapi.json` are exempt (`CSP_EXEMPT_PATHS`) because Swagger UI embeds an inline script; those are disabled in production by `DISABLE_DOCS` anyway. | **Resolved.** Verified in a real browser: all 10 pages load with Alpine booted and zero CSP violations. 11 header tests + 3 source-guard tests in `tests/api/test_security.py`. **Residual, tracked:** `'unsafe-eval'` (Alpine 3's default build compiles directive expressions with `new Function()` — removing it needs the `@alpinejs/csp` build and rewriting every inline expression as a named method) and `style-src 'unsafe-inline'` (nonces cannot cover `style=` attributes; needs the ~639 attributes migrated to classes). Both are follow-ups, not Tier 5 scope. |
| A3 | Filter/term query logging | Carried from the TIER2–4 A-items as an unverified assumption. **Now verified by exhaustive source scan (24/09/2026): the claim does not hold for this codebase.** `api/` contains exactly two logging call sites — `api/helpers.py:306` (`logger.exception` on audit-write failure, logging `action` / `table_name` / `record_pk` only) and `api/routers/claim_approval.py:596` (`logger.warning` on an affiliation INSERT conflict, logging PKs and a local id). Neither logs a user-supplied filter, search term, or field value. No request/query logging middleware exists. | No change required — there is no app-level code path that writes filter or search values to a log. DB statement logging (`log_statement`) remains an infrastructure concern outside this codebase, unchanged by this tier. | **Resolved (verified no-op).** Reclassified from "awareness-only" to resolved: the finding was inherited by analogy rather than by evidence, and the evidence contradicts it. Re-open only if request logging or a logging middleware is introduced. |
| A4 | Logout is client-side only | Stateless JWT: `/logout` does not revoke; a leaked access token remains valid until `exp` (≤30 min). Documented as Tier 5.1. | **RESOLVED (2026-10-05).** Decision made between the two viable designs: **(a) denylist/session table** — adds `database/ddl/06_authentication/05_user_session.sql` (`nss.user_session`), a stateful session record (`issued_at`, `last_seen_at`, `expires_at`, `revoked_at`, `user_agent`, `ip_address`, `device_label`) created at login and revocable individually. **(b) stateless invalidation** — a `credentials_changed_at` watermark on `user_account`, no new table, but only revokes on credential change, not on logout, and cannot list a user's active sessions. **(a) was chosen specifically because a "logged-in devices" UI was required** — letting a user see and revoke individual sessions/devices — and only the stateful design supports that; the stateless watermark approach has no concept of a per-device session to list or revoke. This closes the Tier 5.2-style table decision flagged in v1.2: `04_authentication_security_business_rules.md`'s caution against authorizing new tables "by implication" is satisfied here by an explicit advisory resolution rather than an implied one. | **Resolved.** `nss.user_session` implemented; `/logout` now revokes the session (`revoked_at`), and a partial index `(user_account_pk, revoked_at) WHERE revoked_at IS NULL` backs the active-sessions-list query for the devices UI. |
| A5 | OTP debug echo | `forgot-password` returns `otp_debug` when `DEBUG_MODE=true`, for local testing before email/SMS delivery exists. Impact if wrongly enabled: anyone who can name a valid `login_id` can read that account's reset OTP and take it over. `DEBUG_MODE` defaults to false. | **Mitigated (24/09/2026).** The echo itself is retained deliberately — no email/SMS delivery exists yet, and `tests/api/test_forgot_password.py` drives the whole reset flow through `otp_debug`; removing it now would delete that coverage rather than improve security. Instead the failure mode (an inherited env var silently enabling it) is now detectable: `api/main.py:_warn_on_insecure_settings()` runs on startup and logs an explicit `SECURITY:` warning naming the exact exposure when `DEBUG_MODE` is on, and likewise if `CSP_ENABLED=false` or `CSP_REPORT_ONLY` is set. Remove the field entirely once delivery is integrated — still flagged in-code at `api/routers/auth.py:540-542`. | **Mitigated; removal tracked to OTP delivery.** Covered by `TestDebugModeWarning` in `tests/api/test_security.py` (warns when on, silent on secure defaults). |

No blocking vulnerabilities found.

---

## 3. Verdict

Tier 5 introduces authentication, RBAC enforcement, and the authenticated
audit-trail viewer with no blocking security defects. All 21 checks pass.

The five advisory items were then worked rather than left as a list (24/09/2026):
**A2 (CSP) is implemented** — a measured, enforced Content-Security-Policy whose
`script-src` omits `'unsafe-inline'`, which required removing every inline event
handler from the frontend first; **A3 is closed as a verified no-op** — the
inherited "filter values reach logs" finding is contradicted by the only two
logging call sites in `api/`; **A5 is mitigated** — an accidentally enabled
`DEBUG_MODE` now announces itself in the startup log. **A4 (token revocation) is
now resolved (2026-10-05)** — a stateful session table, `nss.user_session`, was
chosen over the stateless `credentials_changed_at` alternative specifically
because a "logged-in devices" UI was required, which only the stateful design
supports. One item remains open: **A1** (contact-field gating) has a fixed
resolution path — page retirement as the Dashboard reaches parity — and is
sequenced behind that build.

Correction carried in v1.2: the v1.1 A2 observation asserted that no third-party
script origins remained. That was wrong — Alpine.js is CDN-hosted — and the
implemented policy reflects verified source, not that assertion.

```
Tier 5 Security Posture Summary
───────────────────────────────
Authentication ....... Argon2 + HS256 JWT, typed tokens, absolute session cap
Account security ..... 5-attempt / 30s lockout, generic credential errors
Password reset ....... hashed single-use CSPRNG OTP, 15-min TTL, 3/hr limit,
                       anti-enumeration generic response
Authorization ........ require_permission / require_any_permission on 100% of
                       admin + audit endpoints; 401→403 ordering correct
Audit access ......... AUDIT_VIEW-gated, SELECT-only, parameterized, bounded;
                       anonymous foundation/change-log remains absent
Actor attribution .... transaction-local session vars feed the DB trigger
Secrets .............. JWT_SECRET_KEY has no default; startup guard enforces
Transport ............ security + cache headers on every response
Content policy ....... CSP enforced on every response; script-src without
                       'unsafe-inline' (all inline handlers removed);
                       residual 'unsafe-eval' (Alpine) + style 'unsafe-inline'
Insecure-config ...... startup warns on DEBUG_MODE / CSP disabled / report-only
OPEN ................. contact-field gating on Tier 1–4 anonymous reads (A1) —
                       resolution: page retirement as Dashboard reaches parity
                       (Dashboard build in progress as of 24/09/2026)
RESOLVED (2026-10-05)  token revocation on logout (A4) — stateful `nss.user_session`
                       table chosen over stateless `credentials_changed_at`
                       watermark; devices UI required the stateful design
Blocking issues ...... none
```

---

## 4. Test Coverage for Security

| Control | Test | File |
|---|---|---|
| No token → 401 | `TestChangeLogAuth::test_requires_authentication` | `tests/api/test_audit.py` |
| Authenticated, no permission → 403 | `TestChangeLogAuth::test_forbidden_without_permission` | `tests/api/test_audit.py` |
| AUDIT_VIEW holder → 200 | `TestChangeLogAuth::test_admin_can_read` | `tests/api/test_audit.py` |
| Filter correctness | `TestChangeLogQuery::test_filter_by_table_and_record` | `tests/api/test_audit.py` |
| Pagination cap | `TestChangeLogQuery::test_pagination_limit` | `tests/api/test_audit.py` |
| `limit` over MAX → 422 | `TestChangeLogQuery::test_limit_over_max_rejected` | `tests/api/test_audit.py` |
| Anonymous audit path absent | `TestFoundationChangeLogStillHidden::test_foundation_change_log_absent` | `tests/api/test_audit.py` |
| Anonymous audit path absent (Tier 1 guard) | `TestChangeLogNotExposed::test_change_log_endpoint_returns_404` | `tests/api/test_foundation.py` |
| Auth login / RBAC gate (admin, users, roles, scope) | existing `test_auth.py` / `test_admin.py` suites | `tests/api/` |
| CSP header present (frontend + API) | `TestContentSecurityPolicy::test_csp_present_on_{frontend,api}_response` | `tests/api/test_security.py` |
| CSP locks down default/object/frame/base/form/connect/font | `TestContentSecurityPolicy::test_csp_locks_down_default_and_dangerous_directives` | `tests/api/test_security.py` |
| CSP `script-src` forbids `'unsafe-inline'` | `TestContentSecurityPolicy::test_csp_script_src_forbids_unsafe_inline` | `tests/api/test_security.py` |
| CSP allows exactly what Alpine needs | `TestContentSecurityPolicy::test_csp_script_src_allows_alpine` | `tests/api/test_security.py` |
| CSP allows inline styles / `data:` images | `TestContentSecurityPolicy::test_csp_style_src_allows_inline`, `..._img_src_allows_data_uris` | `tests/api/test_security.py` |
| CSP exempts Swagger UI | `TestContentSecurityPolicy::test_csp_absent_on_swagger_docs` | `tests/api/test_security.py` |
| CSP report-only / disable / extra-origin toggles | `TestContentSecurityPolicy::test_csp_report_only_mode`, `..._can_be_disabled`, `..._extra_origins_are_appended` | `tests/api/test_security.py` |
| No inline handlers or `<script>` blocks in source (CSP source guard) | `TestNoInlineEventHandlers` (3 tests, HTML + JS templates) | `tests/api/test_security.py` |
| `DEBUG_MODE` warns at startup; secure defaults stay silent | `TestDebugModeWarning` (2 tests) | `tests/api/test_security.py` |

Browser verification for A2 (not part of the suite): `tests/ui/_csp_probe.py` loads
all 10 pages against a live server under the enforced policy and asserts Alpine
booted with zero CSP violations. Run with the server up:
`python3 -m uvicorn api.main:app --port 8001` then `python3 tests/ui/_csp_probe.py`.
It is prefixed with `_` so pytest does not collect it, and it is a diagnostic —
delete it freely.

Note: the permission-gated audit tests that need a second seeded user
(`audit_admin`, `norole_headers`) `pytest.skip` on the local single-seed DB
(only SS1/P1 exists, and it already has an account). This matches the existing
~118 skipped API tests with the same root cause and is not a regression; the
fixture-free gate tests (401 no-token, foundation 404) execute and pass.

---

## 5. Cross-References

- `docs/03_Solution/security/SECURITY_ARCHITECTURE.md` — ownership routing (Authentication = identity, Administration = RBAC, Audit = logging).
- `docs/03_Solution/security/SECURITY_AUDIT_TIER0_4.md` — the deferred-controls table (auth, RBAC, CSP, sessions) that Tier 5 discharges or re-tracks.
- `docs/03_Solution/security/TIER4_SECURITY_AUDIT.md` — origin of advisory A1 (contact fields in member list/search flagged for Tier 5 gating).
- `docs/03_Solution/architecture/IMPLEMENTATION_DEPENDENCY_ORDER.md` §19 — Tier 5 Exit Criteria.
- `docs/03_Solution/modules/authentication/` (SOL-AUTH-001…006) and `docs/03_Solution/modules/administration/` — design authority for the audited code.
- `docs/00_Project_Governance/STD/05_security_standards.md` — policy baseline (RBAC, RLS, auth model).
