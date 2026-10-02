# docs/05_Releases/

Release notes. Every version includes a git tag, this notes file, and a GitHub release.

| Version | Milestone |
|---|---|
| `v0.1.0.md` | Initial project setup |
| `v0.2.0.md` | Foundation models |
| `v0.2.1.md` | Admin setup |
| `v0.3.0.md` | UI foundation and authentication complete |
| `v0.4.0.md` | Organization module complete (design — see `docs/03_Solution/modules/organization/`) |
| `v0.5.0.md` | Person module design complete |
| `v0.5.1.md` | Person database schema complete (global location model, person schema, person address schema, international mobile support, address mapping model) |
| `v0.6.0.md` | Full-Stack Tier 0 — 22-module documentation, 18-table database (Bootstrap RBAC + Foundation + Organization), FastAPI bootstrap API, responsive Bootstrap Verification UI, Render.com + Neon.dev deployment, project governance standards, authoritative reference corpus, NSS-WIDE scope |
| `v0.7.0.md` | Tier 1 Foundation — 17-endpoint API, 4-tab Foundation Verification UI, cross-tier security-hardening middleware (headers/CORS/rate-limiting/CDN SRI), test suite grown 9→64, code-explanation docs reorganized per-layer |
| `v0.8.0.md` | Tier 2 Organization — 6-endpoint API (incl. recursive-CTE hierarchy tree), 3-tab Organization Verification UI, contact/online-presence fields, test suite grown 64→139, `code_explanations/` and API contracts moved out of `architecture/` |
| `v0.9.0.md` | Organization master-data migration + Tier 3 Person — 4-endpoint API (incl. `pg_trgm` search), Person DDL rewrite onto Foundation `master_data`, shared `api/helpers.py`, test suite grown 139→208 |
| `v0.10.0.md` | Tier 4 Family + Membership — full vertical slice (5 Family + 12 Membership tables at the time, 14 read-only endpoints), family graph, Organization `/children-stats`, consolidated `API_CONTRACT.md` |
| `v0.10.1.md` | Build-script fix — `family_link` wired into `02_build.sh`, `render_build.sh` brought to Tier 4 parity |
| `v0.10.2.md` | `render_build.sh` creates `nss_db_owner`/`nss_db_backend` roles on Neon before granting |
| `v0.10.3.md` | Idempotent DDL + seed — root-cause fix for Neon schema/data drift |
| `v0.10.4.md` | Performance hardening — connection pool, composite partial indexes, multi-worker Uvicorn (latest released tag) |

Tier 5 (Authentication + Administration) has **no release notes yet** — it is in progress,
uncommitted, on `feature/tier5-authentication-administration`; its notes will be `v0.11.0.md`
once merged and tagged.
