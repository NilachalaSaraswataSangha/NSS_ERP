# docs/03_Solution/security/

Solution-level security architecture and audit documentation, building on
`docs/00_Project_Governance/STD/05_security_standards.md` (RBAC, Row Level Security, auth
model).

## Files

- **`SECURITY_ARCHITECTURE.md`** — Cross-reference map of security ownership: STD-05 (policy),
  Authentication (identity), Administration (RBAC), Audit (logging), per-module business rules.
  Establishes authoritative-document routing without duplicating existing rules.
- **`TIER0_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 0 code.
  10 checks passed; 1 fix applied (ConfigDict removal); 6 advisory items (4 resolved, 1 partial,
  1 N/A). No blocking vulnerabilities found.
- **`TIER1_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 1 code.
  9 checks passed; 6 advisory items (3 resolved, 1 partial, 1 advisory, 1 N/A).
  No blocking vulnerabilities found.
- **`TIER2_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 2 code.
  15 checks passed; 0 fixes required; 4 advisory items (pagination, CTE depth, filter logging,
  helper duplication). No blocking vulnerabilities found.
- **`TIER3_SECURITY_AUDIT.md`** (v1.1, Complete) — security audit scoped to all Tier 3 (Person)
  code. 18 checks passed; 0 fixes required; 3 of 5 advisory items resolved (pagination, search
  limit, helper deduplication), 2 awareness-only items retained (Aadhaar key management deferred
  to Tier 5+, filter value logging). No blocking vulnerabilities found — confirms defence-in-depth
  for Aadhaar (encrypted at rest, never selected by the API, never modelled in Pydantic, never
  rendered in the UI).
- **`TIER4_SECURITY_AUDIT.md`** (v1.0, Complete) — security audit scoped to all Tier 4
  (Family + Membership) code: 4 GET endpoints over 3 Family tables, 7 GET endpoints over 5
  Membership tables, plus the Family/Membership DDL (4 + 12 tables), routers, schemas, and
  frontend. 21 checks passed; 0 fixes required; 2 advisory items (filter/search-term query
  logging, contact fields returned in member list/search — both flagged for RBAC gating at
  Tier 5). No blocking vulnerabilities found.
- **`SECURITY_AUDIT_TIER0_4.md`** (`SOL-SEC-002`, v1.0.0) — aggregate cross-tier summary across
  Tiers 0–4: implemented controls (security headers, cache control, rate limiting, CORS,
  database access control, sensitive-data protection, input validation, docs toggle),
  intentionally deferred controls (auth, RBAC enforcement, HSTS, CSP, RLS, sessions, MFA — all
  Tier 5+), and a table of potential improvements. Consolidates, rather than replaces, the
  per-tier audits above.

See `docs/03_Solution/code_explanations/` for line-by-line code walkthroughs of the same
endpoints/files (a different concern from the audit findings recorded here), and
`docs/03_Solution/api/` for the formal API contracts.
