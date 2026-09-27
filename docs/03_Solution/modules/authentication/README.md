# NSS ERP Authentication & Security Module

Status: IMPLEMENTED (Tier 5) — SOURCE ALIGNED, v1.0.0/v0.1.0 (lifecycle doc). Full Solution
design is 5 files. Authentication was delivered in Tier 5: the `user_account` and
`password_history` tables owned by this module exist in `database/ddl/`, and the FastAPI
API now exposes the full auth surface (login, refresh, logout, change-/forgot-/reset-password,
me, profile) with Argon2 hashing and HS256 JWT — see `api/routers/auth.py`,
`api/services/auth_service.py`, and the RBAC layer (`api/dependencies/rbac.py`,
`api/services/rbac_service.py`). The earlier Django prototype (`backend/`) with its simpler
`Role`/`UserRole`/`LoginAudit` schema was fully removed before this implementation. Security
verification: `docs/03_Solution/security/TIER5_SECURITY_AUDIT.md`.

**Naming note:** this Solution-layer document set (`SOL-AUTH-001`…`005`) is unrelated to the
governance-layer `AUTH-001` under `docs/00_Project_Governance/AUTH/` (the Authoritative
Reference Standard) — see `docs/00_Project_Governance/AUTH/README.md`'s terminology note. Same
three letters, two entirely different documents.

---

## Documents

01_authentication_security_module_overview.md (`SOL-AUTH-001`) — Version 1.0.0
Purpose: Centralized security foundation — authentication, account security, password
security, identity verification, secure session access; authorization management via
Roles/Permissions/Organizational Scope.

02_authentication_security_erd.md — Version 1.0.0
Purpose: Entity relationship design for the seven-table security foundation.

03_authentication_security_lifecycle.md — Version 0.1.0, DRAFT, Document ID `SOL-AUTH-005`
Purpose: `user_account` states (ACTIVE/LOCKED/INACTIVE), append-only `password_history`,
conceptual session lifecycle (application layer), RBAC deferred to Administration, account
deactivation preserves business records, Person-death integration.

04_authentication_security_business_rules.md — Version 1.0.0, AUTH-BR-001–AUTH-BR-080
Purpose: Business rules — Argon2 password hashing, JWT authentication, session management,
encrypted sensitive data (including Aadhaar), Row-Level Security identified as security
principles. Explicitly does not freeze `login_history`/`session_history`/MFA/password-reset/
lockout tables — "security standards do not by themselves authorize new database tables."

05_authentication_security_table_design.md — Version 1.0.0
Purpose: Physical table design — seven tables split between identity/credential security here
and RBAC management in Administration.

---

## Key facts

- **Seven tables appear in this document's ERD**, but ownership is exclusive per the
  **Table Ownership Declaration (Frozen, `CROSS_MODULE_PRINCIPLES.md`)**: this
  module owns only `user_account` and `password_history` (identity verification and credential
  security). The other five (`role_master`, `permission_master`, `role_permission`, `user_role`,
  `admin_scope`) are exclusively owned by `docs/03_Solution/modules/administration/` — they
  appear here too only because Authentication needs to *evaluate* roles/permissions/scope, not
  because it manages them. Both modules may FK to the other's tables, but ownership is
  canonical and non-overlapping.
- No `login_history` or `session_history` tables and no MFA. Lockout is implemented via
  `user_account` columns (`failed_login_attempts`, `locked_until`), not a separate table.
  `password_reset_token` was added in Tier 5.1 for OTP-based self-service reset.

## Note — design/code status (Tier 5)

This module's design has been implemented. `user_account` and `password_history` (owned here)
and the RBAC tables owned by Administration (`role_master`, `permission_master`,
`role_permission`, `user_role`, `admin_scope`) all exist in `database/ddl/`, are seeded
(`database/seed/00_bootstrap/` + `04_admin/`), and are exercised by the auth/admin API. The
`password_reset_token` table was added in Tier 5.1 for self-service OTP reset — a table not
frozen in the original SOL-AUTH design, added under an explicit Tier 5.1 decision (20/09/2026).
The previous Django prototype's `Role`/`UserRole`/`LoginAudit` models (auto-increment PKs, FK to
Django's built-in `auth.User`) were removed along with the rest of `backend/`; there is nothing
left to reconcile against.

---

## Current Status

Design Complete · ERD Complete · Lifecycle Documented (SOL-AUTH-005 — §16 now cross-references
`SOL-LIFE-002` (Person death) and `SOL-LIFE-001` (participation consequences)) · Business Rules
Drafted (SOURCE
ALIGNED) · Table Design Drafted (SOURCE ALIGNED) · **SQL + API Implemented (Tier 5)** — DDL,
seed, and the auth/RBAC API are live and tested; security-verified in
`docs/03_Solution/security/TIER5_SECURITY_AUDIT.md`.
