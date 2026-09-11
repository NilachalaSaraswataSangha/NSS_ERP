# docs/03_Solution/api/

API design documentation: formal request/response contracts for the read-only FastAPI service
implemented at the root-level `api/` folder (raw psycopg2, no ORM; see `api/README.md` for the
running code). Each contract is written per-tier, as its vertical slice lands, and stays DRAFT
until the tier's implementation is frozen.

## Files

- **`BOOTSTRAP_API_CONTRACT.md`** (v1.0, DRAFT) — Tier 0 Bootstrap RBAC read-only contract: 4
  endpoints (`health`, `roles`, `permissions`, `roles/{pk}/permissions`) over 3 tables
  (`role_master`, `permission_master`, `role_permission`). No authentication; `nss_db_backend`
  connects SELECT-only.
- **`FOUNDATION_API_CONTRACT.md`** (v1.1, DRAFT) — Tier 1 Foundation read-only contract: 17
  endpoints across 11 tables (master data, system config, geography, runtime document
  metadata). Carries forward Tier 0's conventions plus new Tier 1 ones (query-param filtering,
  hierarchical drill-down, no pagination). `nss.field_change_log` is explicitly deferred to
  Tier 5 (needs auth) — not part of this contract.
- **`ORGANIZATION_API_CONTRACT.md`** (v1.0, DRAFT) — Tier 2 Organization read-only contract: 6
  endpoints (`types`, `statuses`, `organizations` list/detail/children, `hierarchy`) over 3
  tables, exposing the NSS institutional hierarchy (Kendra → Anchalika/Zilla → Sakha → Patha
  Chakra).

Each contract documents conventions, the full endpoint catalogue with example
requests/responses and SQL patterns, a response-schema summary, error responses, and an
implementation file map tying the contract back to its router/schema/test/frontend files.
Write operations (POST/PATCH/DELETE) are deferred to Tier 5 across all three contracts, once
authenticated administration and authorization exist.

See `docs/PROJECT_DOCUMENTATION.md` → Conventions & gotchas for how this folder relates to the
actual implemented code under `api/`, and `docs/03_Solution/code_explanations/` for line-by-line
code walkthroughs of the same endpoints.
