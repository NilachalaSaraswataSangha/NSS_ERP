# docs/03_Solution/architecture/

Overall solution architecture documentation (cross-module, above the per-module docs in
`docs/03_Solution/modules/`).

## Files

- **`TECH_STACK_DECISIONS.md`** — Approved technology decision record: database (PostgreSQL on
  Neon.dev), backend (Django 6.0.6 + FastAPI 0.136.3 on Render.com/Uvicorn), frontend (Tailwind
  CSS + DaisyUI + HTMX + Alpine.js, replacing Bootstrap 5), mobile/offline strategy (PWA +
  IndexedDB + Background Sync), git remotes/deployment flow, and rejected alternatives.
- **`DEVELOPER_REFERENCE_GUIDE.md`** — Per-module "which document to read before coding" matrix
  following the REF → AUTH → GOV → REQ → SOLUTION → CODE → TEST → RELEASE lifecycle order.

This is the **approved target**, not yet the current code — `backend/` still runs Bootstrap 5
templates with no FastAPI wiring as of this writing. See `docs/PROJECT_DOCUMENTATION.md` →
Architecture for the current code-verified state and how it differs from these decisions.
