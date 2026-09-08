# docs/03_Solution/

Solution-layer design docs: per-module design (`modules/`) plus cross-cutting design areas.

| Folder | Status |
|---|---|
| `modules/` | 22 module folders, each with a complete or largely-complete design doc set (`programmes_events/` still v0.1.0 DRAFT/not frozen; `assets_property/` is the 22nd) — see `modules/README.md` for the per-module status table |
| `architecture/` | 12 cross-module architecture docs: `TECH_STACK_DECISIONS.md` (v1.3, approved tech decision record — FastAPI is now the sole backend framework, Django removed), `DEVELOPER_REFERENCE_GUIDE.md`, `BOOTSTRAP_ARCHITECTURE.md`, `CROSS_MODULE_PRINCIPLES.md`, `DDL_CREATION_ORDER.md`, `FK_DEPENDENCY_GRAPH.md`, `MODULE_DEPENDENCY_MAP.md`, `IMPLEMENTATION_DEPENDENCY_ORDER.md`, plus 4 Programmes & Events docs (`PROGRAMME_EVENT_DOMAIN_MODEL.md`, `EVENT_ENTITY_RECONCILIATION.md`, `PROGRAMMES_EVENTS_CROSS_MODULE_REVIEW.md`, `PROGRAMMES_EVENTS_RECONCILIATION_DECISIONS.md`) — see `architecture/README.md` for the per-file status table |
| `database/` | `DATABASE_DESIGN_STANDARDS.md` (`SOL-DB-001`) — cross-module DB conventions consolidation |
| `security/` | `SECURITY_ARCHITECTURE.md` (`SOL-SEC-001`) — security ownership/routing map |
| `standards/` | `lifecycle/` — `SOL-LIFE-001`/`SOL-LIFE-002`, both FROZEN v1.0.0 |
| `infrastructure/` | `DEPLOYMENT_SYNC_PLAN.md` — deployment/repo-sync plan |
| `ui/` | `mockups/` — 13 static HTML mockups (Tailwind + DaisyUI via CDN) |
| `api/` | Reserved — no design content written yet. Note: FastAPI code now exists and runs at the root-level `api/` folder (Tier 0 bootstrap-RBAC endpoints) — this `docs/03_Solution/api/` folder is a separate, still-empty documentation scaffold for that code's design |

See `docs/PROJECT_DOCUMENTATION.md` → `03_Solution/` detail for the full code-verified
breakdown of every file in each folder.
