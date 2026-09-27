# docs/03_Solution/ui/

UI/UX design documentation (screen specs, wireframes) per the UI Roadmap in
`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md` (Phase 4) and `mockups/README.md`.

## Relationship to the implemented `frontend/`

`frontend/` (repo root) is a real, already-implemented frontend. It consists of four
authenticated pages — `login.html` (`/login`, which `/` redirects to), `register.html`
(`/register`), `dashboard.html` (`/dashboard` — the role-aware Member Dashboard) and `admin.html`
(`/admin` — the Administration Dashboard) — see root `CLAUDE.md` → Frontend and
`frontend/README.md`. It originally consisted instead of six Verification UIs (Tier 0
Bootstrap, Tier 1 Foundation, Tier 2 Organization, Tier 3 Person, Tier 4 Family, Tier 4
Membership) served at `/`, `/foundation`, `/organization`, `/person`, `/family` and
`/membership`; those six pages have been **retired and deleted**, and each one's functionality
now lives in a tab of `admin.html` (Bootstrap RBAC → System Settings, Foundation → Reference Data
+ Geography, Organization → Organizations + Organization Hierarchy, Person → Person Directory,
Membership → Member Directory) or `dashboard.html` (Family, Membership). It shares
the same tech stack as the mockups below (Tailwind CSS + DaisyUI, Alpine.js, no build
step) but is a distinct, functional artifact: it calls the real `/api/v1/*`
endpoints, whereas the mockups in `mockups/` are static,
non-functional visual targets for the future admin-dashboard UI (Phase 4) with sample/placeholder
data only. None of the 13 mockups below is one of the implemented pages, and the implemented
pages do not supersede or implement any of them — they cover different,
non-overlapping screens.

## Contents

- **`mockups/`** — 13 static HTML mockups (Tailwind CSS + DaisyUI via CDN, no build step)
  covering Login, Kendra/Sakha/Anchalika/Zilla dashboards, Admin, Member Profile, Family
  Dashboard, Member Search, Attendance Marking, Governance Dashboard, and both Mahila Sangha
  dashboards (central Mandali + local Sakha). See `mockups/README.md` for the full file list
  and design language (color-per-domain, saffron brand accent). These are visual targets for
  Phase 4 implementation, not functional prototypes — no wireframe/spec documents beyond the
  mockups themselves exist yet.
