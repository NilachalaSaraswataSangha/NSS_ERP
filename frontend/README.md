# frontend/

Tier 0 Bootstrap Verification UI and Tier 1 Foundation Verification UI for Nilachala Saraswata
Sangha.

**Purpose:** Verify the database → API → frontend integration for each tier as it's built.
Neither page is an operational administration dashboard. Together they establish the frontend
shell that later tiers grow into.

**Tech stack:** Tailwind CSS + DaisyUI (CDN), Alpine.js (CDN), vanilla
`fetch()` for JSON API consumption. No React/Vue/Angular. No Node.js
build step. No Django templates.

**Served by:** FastAPI mounts this directory as static files. No
separate frontend server, no CORS configuration needed.

---

## Directory Structure

```
frontend/
├── index.html              Tier 0 Bootstrap Verification UI (Alpine.js application)
├── foundation.html         Tier 1 Foundation Verification UI (Alpine.js application)
├── assets/
│   ├── css/
│   │   └── style.css       Minimal project-specific CSS overrides
│   ├── img/
│   │   └── nss-logo.png    NSS logo (PNG with transparency)
│   └── js/
│       ├── app.js          Alpine.js data component + API fetch logic for index.html
│       └── foundation.js   Alpine.js data component + API fetch logic for foundation.html
└── README.md               This file
```

Both pages share the same header pattern with a nav bar linking between `/` ("Bootstrap") and
`/foundation` ("Foundation"), so either page is one click away from the other.

---

## File Reference

### index.html

The single-page application entry point. Uses a two-tier layout designed
to fit all sections on a single screen without scrolling:

1. **System Status** — centred card at the top (narrow, `max-w-md mx-auto`)
2. **Responsive grid** below:
   - Left: RBAC Roles (clickable rows)
   - Centre: Permissions (catalogue)
   - Right: Role Permissions (drill-down on role click)

The grid adapts to screen width:

| Screen | Breakpoint | Layout |
|--------|-----------|--------|
| Mobile (< 768px) | default | 1 column (stacked) |
| Tablet (768px–1279px) | `md` | 2 columns (Role Permissions wraps below) |
| Desktop (≥ 1280px) | `xl` | 3 columns (all side by side) |

Layout fills the full viewport width with progressive side padding
(`px-6` mobile, `lg:px-10` tablet, `2xl:px-16` large desktop). No
max-width cap — tables stretch dynamically with the screen.

Each section is rendered by Alpine.js directives bound to the
`bootstrapApp()` data component defined in `app.js`.

| Section | Position | API Endpoint Consumed | What It Shows |
|---------|----------|----------------------|---------------|
| **Header** | Top, full width | — | NSS logo, "Nilachala Saraswata Sangha", "Tier 0 — Bootstrap Verification" |
| **System Status** | Top, centred | `GET /api/v1/bootstrap/health` | Three-state indicator: "Checking..." (spinner), "Database Connected" (green badge), or "Database Unavailable" (red badge). Never exposes raw database errors. |
| **RBAC Roles** | Left column | `GET /api/v1/bootstrap/roles` | Table: Code, Name, Class (badge), Scope, Active (✓/✗). Counter badge. Rows are clickable — selecting a role triggers the Role Permissions column. SYSTEM-class roles show a primary badge; ORGANIZATIONAL-class roles show a secondary badge. |
| **Permissions** | Centre column | `GET /api/v1/bootstrap/permissions` | Table: Code, Name, Module (badge), Active (✓/✗). Counter badge. In Tier 0 this is intentionally empty — the UI displays an explanatory message. |
| **Role Permissions** | Right column | `GET /api/v1/bootstrap/roles/{role_pk}/permissions` | Table: Code, Name, Module (badge), Active (✓/✗). Before selection: prompt text. After: role detail header (code, class, scope) + permissions table. Toggle deselect on same role. |
| **Footer** | Bottom, full width | — | Copyright notice: "© 2026 Nilachala Saraswata Sangha. All rights reserved." |

**Table features:**
- `table-sm` density (DaisyUI) — readable without being cramped
- Hover tooltips via `:title` binding on Code and Name cells
- `overflow-x-auto` wrapper per table — horizontal scroll on very narrow screens
- Active column: ✓ (green) for active, ✗ (red) for inactive
- Card padding scales: `p-4` base, `xl:p-6` on desktop
- Grid gap scales: `gap-4` base, `xl:gap-6` on desktop

**CDN dependencies (loaded in `<head>`):**

| Library | Version | Purpose |
|---------|---------|---------|
| Tailwind CSS | v2 (base) + Play CDN | Utility-first CSS framework |
| DaisyUI | v4 | Component library (cards, tables, badges, alerts, spinners) |
| Alpine.js | v3 | Reactive UI state and DOM binding |

**How Alpine.js is wired:**

The root `<div>` declares `x-data="bootstrapApp()"` and `x-init="init()"`.
On page load, Alpine calls `bootstrapApp()` (from `app.js`) to create the
reactive data store, then calls `init()` which fetches health, roles, and
permissions in parallel. The HTML uses Alpine directives (`x-if`, `x-for`,
`x-text`, `x-show`, `@click`, `:class`) to render data reactively.

---

### assets/js/app.js

Alpine.js data component that manages all UI state and API communication.
Defines one global function: `bootstrapApp()`.

**Constants:**

| Name | Value | Purpose |
|------|-------|---------|
| `API_BASE` | `"/api/v1/bootstrap"` | Base URL for all API calls. No hardcoded hostname — uses relative paths so it works regardless of host/port. |

**`bootstrapApp()` — Alpine.js data component:**

Returns an object with reactive state properties and async methods.

**State properties:**

| Property | Type | Initial Value | Purpose |
|----------|------|---------------|---------|
| `health.loading` | boolean | `true` | Whether the health check is in progress |
| `health.connected` | boolean | `false` | Whether the database is reachable |
| `roles` | array | `[]` | List of role objects from the API |
| `rolesLoading` | boolean | `true` | Loading state for roles fetch |
| `rolesError` | boolean | `false` | Error state for roles fetch |
| `permissions` | array | `[]` | List of permission objects from the API |
| `permissionsLoading` | boolean | `true` | Loading state for permissions fetch |
| `permissionsError` | boolean | `false` | Error state for permissions fetch |
| `selectedRole` | object/null | `null` | Currently selected role (clicked in the table) |
| `rolePermissions` | array | `[]` | Permissions for the selected role |
| `rolePermsLoading` | boolean | `false` | Loading state for role-permissions fetch |
| `rolePermsError` | boolean | `false` | Error state for role-permissions fetch |

**Methods:**

| Method | Trigger | API Call | Behaviour |
|--------|---------|----------|-----------|
| `init()` | `x-init` on page load | — | Calls `fetchHealth()`, `fetchRoles()`, and `fetchPermissions()` in parallel via `Promise.all`. |
| `fetchHealth()` | Called by `init()` | `GET /api/v1/bootstrap/health` | Sets `health.connected = true` if the response contains `database: "connected"`. On any error (network failure, non-200 response), sets `health.connected = false`. Never exposes error details to the UI. |
| `fetchRoles()` | Called by `init()` | `GET /api/v1/bootstrap/roles` | Populates `roles[]` with the JSON array. On error, sets `rolesError = true`. |
| `fetchPermissions()` | Called by `init()` | `GET /api/v1/bootstrap/permissions` | Populates `permissions[]` with the JSON array (empty in Tier 0). On error, sets `permissionsError = true`. |
| `selectRole(role)` | `@click` on a role table row | `GET /api/v1/bootstrap/roles/{role_pk}/permissions` | If the clicked role is already selected, deselects it (toggle). Otherwise, sets `selectedRole` and fetches that role's permissions. On error, sets `rolePermsError = true`. |

**Error handling pattern:**

Every fetch method follows the same structure:
1. Set loading state to `true`, error state to `false`
2. `try`: fetch → check `res.ok` → parse JSON → update data
3. `catch`: set error state to `true` (no error details exposed)
4. `finally`: set loading state to `false`

---

### foundation.html

The Tier 1 Foundation Verification UI entry point, structurally parallel to `index.html`: same
head boilerplate and System Status card (reusing `GET /api/v1/bootstrap/health`), but with
"Foundation" active in the nav bar and subtitle "Tier 1 — Foundation Verification". Below the
status card, a DaisyUI `tabs tabs-boxed` bar with 4 tabs, each lazily loaded on first visit
(driven by `activeTab` / `switchTab(tab)` in `foundation.js`):

| Tab | Contents |
|-----|----------|
| **Master Data** | "Master Categories" table (code/name/description/order/active) + "Master Data Values" table with a category-filter `<select>` (`selectedCategoryCode`, `filterByCategory()`) |
| **System Config** | "System Settings" table (key/value/type/description) + "ID Sequences" table (code/name/prefix/padding/`formatSample()`-generated sample) — deliberately excludes `current_value` |
| **Geographic** | Breadcrumb of selected country › state › district, then 4 columns: Countries → States → Districts → Cities/Villages (each a clickable list, `selectCountry()`/`selectState()`/`selectDistrict()`, toggle-deselect on repeat click), plus a Postal Codes section keyed to the selected country; handles "no districts seeded" and "no cities/villages seeded" empty states |
| **Runtime Tables** | "Document Master" table (type/name/number/MIME/version) with an explanatory empty state; notes that `field_change_log` exists in the DB but isn't exposed in Tier 1 (deferred to Tier 5, needs auth) |

Loads `<script src="/assets/js/foundation.js">` at the bottom.

---

### assets/js/foundation.js

Alpine.js data component for `foundation.html`. Defines one global function:
`foundationApp()`. Constant `FND_API = "/api/v1/foundation"`.

**State groups:** `activeTab`, `health{loading,connected}` (shared pattern with `app.js`),
master data (`categories`, `masterData`, `selectedCategoryCode`), config (`settings`,
`sequences`), geographic (`countries`, `states`+`selectedCountry`, `districts`+`selectedState`,
`cities`+`selectedDistrict`, `postalCodes`), runtime (`documents`).

**Lifecycle:** `init()` calls `fetchHealth()` then `loadMasterTab()` — only the active tab's
data loads eagerly; `switchTab()` lazily triggers `loadConfigTab()`/`loadGeoTab()`/
`loadRuntimeTab()` on first visit to each tab, guarded so repeat switches don't re-fetch.

**API calls** (all relative, all under `${FND_API}` except the shared health check):
`GET /api/v1/bootstrap/health`, `GET ${FND_API}/categories`,
`GET ${FND_API}/master-data` (optional `?category_code=`), `GET ${FND_API}/settings`,
`GET ${FND_API}/sequences`, `GET ${FND_API}/countries`,
`GET ${FND_API}/states?country_pk=...`, `GET ${FND_API}/postal-codes?country_pk=...` (fetched
alongside states in `selectCountry()`), `GET ${FND_API}/districts?state_pk=...`,
`GET ${FND_API}/cities?district_pk=...`, `GET ${FND_API}/documents`. The API also exposes
per-PK detail routes (`/categories/{pk}`, `/master-data/{pk}`, `/settings/{key}`,
`/countries/{pk}`, `/states/{pk}`, `/districts/{pk}`, `/postal-code-mappings`) that this UI
doesn't consume yet.

**Error-handling pattern:** identical to `app.js` — loading=true/error=false → try/fetch/check
`res.ok`/parse JSON → catch sets error flag only (never exposes raw error text) → finally
clears loading. `selectCountry()`/`selectState()`/`selectDistrict()` all toggle-deselect:
clicking the already-selected item clears it and every downstream selection/data.

---

### assets/css/style.css

Minimal project-specific CSS. Tailwind and DaisyUI handle all styling
via CDN — this file exists only for overrides that cannot be expressed
as utility classes.

**Current rules:**

| Selector | Purpose |
|----------|---------|
| `[x-cloak]` | Hides elements with the `x-cloak` attribute until Alpine.js initialises, preventing a flash of unstyled/unrendered template syntax. Standard Alpine.js pattern. |

---

### assets/img/nss-logo.png

NSS logo with transparent background. Copied from `NSS LOGO/logooo.png`
in the repository root. Displayed in the page header at 56 × 56 pixels.

---

## How FastAPI Serves This Directory

Defined in `api/main.py`. Registered only if the respective file/directory
exists on disk:

| URL Pattern | FastAPI Handler | Serves |
|-------------|----------------|--------|
| `GET /` | Explicit route → `FileResponse(frontend/index.html)` | The Bootstrap Verification UI |
| `GET /foundation` | Explicit route → `FileResponse(frontend/foundation.html)` | The Foundation Verification UI |
| `GET /assets/*` | `StaticFiles` mount → `frontend/assets/` | CSS, JS, images (shared by both pages) |

**Why not mount at `/`?** A root-level `StaticFiles` mount would shadow
FastAPI's built-in `/docs` (Swagger UI) and `/openapi.json`. By mounting
only `/assets/*` and serving each page via an explicit route, all
FastAPI built-in routes remain accessible.

**Graceful degradation:** If `frontend/` does not exist on disk, the
mount and both routes are skipped entirely. If only `foundation.html` is missing, `/` still
works — the API continues to work in API-only mode — `/docs` and `/api/v1/*` are unaffected.

---

## API Endpoints Consumed

All endpoints are read-only. No authentication. No CRUD.

**`index.html` (via `app.js`):**

| Method | URL | Response | Tier 0 State |
|--------|-----|----------|-------------|
| GET | `/api/v1/bootstrap/health` | `{ status, database }` | `{ "status": "ok", "database": "connected" }` |
| GET | `/api/v1/bootstrap/roles` | `RoleResponse[]` | 8 frozen roles |
| GET | `/api/v1/bootstrap/permissions` | `PermissionResponse[]` | Empty array (by design) |
| GET | `/api/v1/bootstrap/roles/{role_pk}/permissions` | `PermissionResponse[]` | Empty array (no mappings); 404 if role not found |

Response schemas are defined in `api/schemas/bootstrap.py`.

**`foundation.html` (via `foundation.js`):**

| Method | URL | Response | Tier 1 State |
|--------|-----|----------|-------------|
| GET | `/api/v1/bootstrap/health` | `{ status, database }` | Shared with index.html |
| GET | `/api/v1/foundation/categories` | `CategoryResponse[]` | 11 seeded categories |
| GET | `/api/v1/foundation/master-data?category_code=` | `MasterDataResponse[]` | 58 seeded values |
| GET | `/api/v1/foundation/settings` | `SettingResponse[]` | 4 seeded settings |
| GET | `/api/v1/foundation/sequences` | `SequenceResponse[]` | 9 seeded sequences (`current_value` excluded) |
| GET | `/api/v1/foundation/countries` | `CountryResponse[]` | 5 seeded countries |
| GET | `/api/v1/foundation/states?country_pk=` | `StateResponse[]` | 112 seeded states |
| GET | `/api/v1/foundation/districts?state_pk=` | `DistrictResponse[]` | ~770 seeded districts (India only) |
| GET | `/api/v1/foundation/cities?district_pk=` | `CityVillageResponse[]` | Empty (no seed data yet) |
| GET | `/api/v1/foundation/postal-codes?country_pk=` | `PostalCodeResponse[]` | 2 seeded postal codes |
| GET | `/api/v1/foundation/documents` | `DocumentResponse[]` | Empty (no seed data yet) |

Response schemas are defined in `api/schemas/foundation.py`. `nss.field_change_log` is
deliberately not exposed by any endpoint — deferred to Tier 5 (needs auth). Full contract:
`docs/03_Solution/architecture/FOUNDATION_API_CONTRACT.md`.

Audit columns (`created_at`, `*_by_sangha_sevi_pk`) are excluded from every response by design.

---

## Future Growth

This shell is designed to evolve:

```
Tier 0   Bootstrap Verification (current)
Tier 1   Foundation Verification (current)
Tier 2   Organization / Person views
  ...
Tier 5   Authentication + login/session UI
  ...
         Full ERP interface
```

The page structure, CSS framework, and Alpine.js pattern established
here carry forward. Authentication UI is deferred to Tier 5 — Tiers 0-1
intentionally have no login, no session, no fake credentials.
