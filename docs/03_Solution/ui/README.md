# docs/03_Solution/ui/

UI/UX design documentation (screen specs, wireframes) per the UI Roadmap in
`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md` (Phase 4) and `mockups/README.md`.

## Relationship to the implemented `frontend/`

`frontend/` (repo root) is a real, already-implemented frontend — the Tier 0 Bootstrap
Verification UI, served by FastAPI at `/` (see root `CLAUDE.md` → Frontend). It shares the same
tech stack as the mockups below (Tailwind CSS + DaisyUI via CDN, Alpine.js, no build step) but is
a distinct, functional artifact: it calls the real `/api/v1/bootstrap/*` endpoints and verifies
DB connectivity/RBAC seed data, whereas the mockups in `mockups/` are static, non-functional
visual targets for the future admin-dashboard UI (Phase 4) with sample/placeholder data only.
None of the 13 mockups below is the Tier 0 Bootstrap Verification UI, and the Tier 0 UI does not
supersede or implement any of them — they cover different, non-overlapping screens.

## Contents

- **`mockups/`** — 13 static HTML mockups (Tailwind CSS + DaisyUI via CDN, no build step)
  covering Login, Kendra/Sakha/Anchalika/Zilla dashboards, Admin, Member Profile, Family
  Dashboard, Member Search, Attendance Marking, Governance Dashboard, and both Mahila Sangha
  dashboards (central Mandali + local Sakha). See `mockups/README.md` for the full file list
  and design language (color-per-domain, saffron brand accent). These are visual targets for
  Phase 4 implementation, not functional prototypes — no wireframe/spec documents beyond the
  mockups themselves exist yet.
