# frontend/

Tier 0 Bootstrap Verification UI, Tier 1 Foundation Verification UI, Tier 2 Organization
Verification UI, Tier 3 Person Verification UI, and Tier 4 Family + Membership Verification UIs
for Nilachala Saraswata Sangha.

**Purpose:** Verify the database → API → frontend integration for each tier as it's built.
None of the six pages is an operational administration dashboard. Together they establish the
frontend shell that later tiers grow into.

**Tech stack:** Tailwind CSS + DaisyUI (pre-built via Tailwind CLI — no longer CDN, see
`../package.json`/`../tailwind.config.js`), Alpine.js (CDN), vanilla
`fetch()` for JSON API consumption. No React/Vue/Angular. No Django templates. Node.js/npm is
only needed to rebuild CSS after a Tailwind/DaisyUI class change — the built CSS
(`assets/css/tailwind.min.css`) is committed, so running the app itself needs no Node.js.

**Served by:** FastAPI mounts this directory as static files. No
separate frontend server, no CORS configuration needed.

---

## Directory Structure

```
frontend/
├── index.html              Tier 0 Bootstrap Verification UI (Alpine.js application)
├── foundation.html         Tier 1 Foundation Verification UI (Alpine.js application)
├── organization.html       Tier 2 Organization Verification UI (Alpine.js application)
├── person.html             Tier 3 Person Verification UI (Alpine.js application)
├── family.html             Tier 4 Family Verification UI (Alpine.js application)
├── membership.html         Tier 4 Membership Verification UI (Alpine.js application)
├── assets/
│   ├── css/
│   │   ├── badges.css          Shared badge-status/type/affiliation/gender CSS classes + data-identity typography (all six pages)
│   │   ├── style.css           Minimal project-specific CSS overrides
│   │   ├── tailwind-input.css  Tailwind directives (`@tailwind base/components/utilities`) — build input, see ../package.json
│   │   └── tailwind.min.css    Generated, committed build output (~72 KB) — DO NOT hand-edit; regenerate via `npm run css:build`
│   ├── img/
│   │   ├── nss-logo.png          NSS logo, compressed for web (~100 KB, was 1.4 MB)
│   │   └── nss-logo-original.png Uncompressed original, kept for reference/reprocessing
│   └── js/
│       ├── app.js          Alpine.js data component + API fetch logic for index.html
│       ├── foundation.js   Alpine.js data component + API fetch logic for foundation.html
│       ├── organization.js Alpine.js data component + API fetch logic for organization.html
│       ├── person.js       Alpine.js data component + API fetch logic for person.html
│       ├── family.js       Alpine.js data component + API fetch logic for family.html
│       ├── membership.js   Alpine.js data component + API fetch logic for membership.html
│       └── nss-config.js   Shared `NSS` config object — badge-class lookups, Bye-Law display-name
│                           overrides, document-visibility rules (all six pages)
└── README.md               This file
```

All six pages share the same header pattern with a nav bar linking between `/` ("Bootstrap"),
`/foundation` ("Foundation"), `/organization` ("Organization"), `/person` ("Person"), `/family`
("Family"), and `/membership` ("Membership"), so any page is one click away from any other. Every
page also loads `assets/css/badges.css` and `assets/js/nss-config.js` in `<head>`, immediately
after `style.css` — these two files are the single source of truth for badge CSS classes and
their display-name/visibility logic across the whole frontend. **Convention for future page
authors:** individual pages must **not** redefine `badge-status-*`/`badge-type-*`/`badge-aff-*`
classes in a page-local inline `<style>` block — add any new status/type/affiliation value to
`badges.css` (and, if it needs a lookup helper, to `nss-config.js`'s `NSS` object) instead, so
every page picks it up automatically.

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

**CSS/JS dependencies (loaded in `<head>`, identical on `index.html`, `foundation.html`,
`organization.html`, `person.html`, `family.html`, and `membership.html`):**

| Library | Version | Purpose |
|---------|---------|---------|
| Tailwind CSS + DaisyUI | `3.4.17` / `4.12.14`, pre-built via Tailwind CLI into `assets/css/tailwind.min.css` (`<link rel="stylesheet" href="/assets/css/tailwind.min.css">`) — no longer CDN, no SRI (same-origin static file, not a third-party script) | Utility-first CSS framework + component library (cards, tables, badges, alerts, spinners) |
| Alpine.js | `3.14.8`, pinned with `integrity`/`crossorigin` (SRI), still CDN | Reactive UI state and DOM binding |

The old unpinned `tailwindcss@2` prebuilt CSS and an incompatible `@tailwindcss/browser` 4.x
build were both removed as part of the security-hardening pass — see
`docs/03_Solution/code_explanations/SECURITY_CODE_EXPLANATIONS.md` and
`UI_CODE_EXPLANATIONS.md` in the same folder.

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

### organization.html

The Tier 2 Organization Verification UI entry point, structurally parallel to `index.html` and
`foundation.html`: same head boilerplate and System Status card (reusing
`GET /api/v1/bootstrap/health`), but with "Organization" active in the nav bar and subtitle
"Tier 2 — Organization Verification". Below the status card, a DaisyUI `tabs tabs-boxed` bar
with 3 tabs, each lazily loaded on first visit (driven by `activeTab` / `switchTab(tab)` in
`organization.js`):

| Tab | Contents |
|-----|----------|
| **Reference Data** | Two side-by-side tables: "Organization Types" (code/name/description/sort order, 8 rows) and "Lifecycle Statuses" (code/name/description/sort order, 6 rows) |
| **Organizations** | Filterable list (2-column layout): left/wide panel is the organization table (code/name/type badge/status badge/parent/location) with `<select>` filters for type and status (`selectedTypeFilter`/`selectedStatusFilter`, `filterOrganizations()` — status filter auto-disables for the 3 singleton institutional types; auto-selects the sole result when a filter narrows to exactly one org); right panel is a detail view — key fields, Address, Contact (phone/mobile), Online Presence (NSS + org-specific email/website/YouTube links), Geographic (district/state/country), Coordinates, and a Children sub-table (hidden entirely for types that can't have children — the 2 institutional singletons plus `PATHA_CHAKRA`/`SAKHA_ASANA`) that lazy-loads on row click (`selectOrganization()`, toggle-deselect on repeat click). Status badges use 6 dedicated `.badge-status-*` CSS classes (one per lifecycle status) rather than DaisyUI's generic semantic badges |
| **Hierarchy** | Flat recursive-CTE result rendered client-side as an indented tree using a `depthIndent(node.depth)` inline-style helper, with type badge, name, code, and a status badge per node |

Loads `<script src="/assets/js/organization.js">` at the bottom.

---

### assets/js/organization.js

Alpine.js data component for `organization.html`. Defines one global function:
`organizationApp()`. Constant `ORG_API = "/api/v1/organization"`.

**State groups:** `activeTab`, `health{loading,connected}` (shared pattern with `app.js`),
reference data (`orgTypes`, `orgStatuses`), organizations (`organizations`,
`selectedTypeFilter`, `selectedStatusFilter`, `selectedOrg`, `orgChildren`), hierarchy
(`hierarchy`). Each collection has matching `*Loading`/`*Error` booleans following the same
convention as `app.js`/`foundation.js`.

**Lifecycle:** `init()` calls `fetchHealth()` then `loadReferenceTab()` — only the active tab's
data loads eagerly; `switchTab()` lazily triggers `loadOrganizationsTab()`/`loadHierarchyTab()`
on first visit to each tab, guarded so repeat switches don't re-fetch (each guard checks the
target array is still empty before fetching).

**API calls** (all relative, all under `${ORG_API}` except the shared health check):
`GET /api/v1/bootstrap/health`, `GET ${ORG_API}/types`, `GET ${ORG_API}/statuses`,
`GET ${ORG_API}/organizations` (optional `?type_code=`/`?status_code=`, rebuilt by
`filterOrganizations()` on filter change), `GET ${ORG_API}/organizations/{pk}/children`
(fetched on `selectOrganization()`), `GET ${ORG_API}/hierarchy`.

**Error-handling pattern:** identical to `app.js`/`foundation.js` — loading=true/error=false →
try/fetch/check `res.ok`/parse JSON → catch sets error flag only → finally clears loading.
`selectOrganization(org)` toggle-deselects: clicking the already-selected row clears
`selectedOrg` and `orgChildren`.

**Helper:** `depthIndent(depth)` returns an inline `padding-left` style string
(`${depth * 1.5}rem`) used by the Hierarchy tab to visually nest tree rows without any
client-side tree-building logic — the API already returns depth per flat row.

---

### person.html

The Tier 3 Person Verification UI entry point, structurally parallel to the earlier tier pages:
same head boilerplate and System Status card (reusing `GET /api/v1/bootstrap/health`), but with
"Person" active in the nav bar and subtitle "Tier 3 — Person Verification". Below the status
card, a DaisyUI `tabs tabs-boxed` bar with 2 tabs, each lazily loaded on first visit (driven by
`activeTab` / `switchTab(tab)` in `person.js`):

| Tab | Contents |
|-----|----------|
| **Persons** | Filterable list (2-column layout): left/wide panel is the person table (person_id/name/gender/DOB/mobile/email/marital status/blood group/status) with `<select>` filters for gender, marital status, and blood group (all sourced from Foundation master-data via `GET /api/v1/foundation/master-data?category_code=`); right panel is a detail view — identity, demographics, contact, masked Aadhaar ("XXXX XXXX 1234"), emergency contact section (name/phone/relationship), remarks, and an Addresses sub-section showing each address as a card with type badge, primary badge, address lines, landmark, and resolved location chain (city/village, postal code, district, state, country). Addresses auto-load on row click (`selectPerson()`, toggle-deselect on repeat click). Person lifecycle states (Active/Deceased/Inactive) are derived from `is_active` + `date_of_death` and shown via dedicated `.badge-status-*` CSS classes |
| **Search** | Trigram fuzzy search input (min 2 chars, 300ms debounce) querying `GET /api/v1/person/search?q=`; results table (person_id/name/gender/DOB/mobile/email/status) in a grid layout (`xl:col-span-2`) alongside its own inline "Person Detail" panel — clicking a result calls `selectPerson(p)` directly (no tab switch, same pattern as `membership.js`'s Search tab); if the search returns exactly one result it is auto-selected |

Loads `<script src="/assets/js/person.js?v=2.2">` at the bottom (cache-bust version — see the
note under `family.html` above; treat as a snapshot, not re-verified every doc pass).

---

### assets/js/person.js

Alpine.js data component for `person.html`. Defines one global function: `personApp()`.
Constants `PERSON_API = "/api/v1/person"` and `FOUNDATION_API = "/api/v1/foundation"`.

**State groups:** `activeTab`, `health{loading,connected}` (shared pattern with `app.js`),
filter options (`genderOptions`, `maritalStatusOptions`, `bloodGroupOptions` — loaded from
Foundation master-data), persons (`persons`, `selectedGenderFilter`, `selectedMaritalFilter`,
`selectedBloodGroupFilter`, `selectedPerson`, `personAddresses`), search (`searchQuery`,
`searchResults`, `searchExecuted`, `_searchDebounce`). Each collection has matching
`*Loading`/`*Error` booleans.

**Lifecycle:** `init()` calls `fetchHealth()` then `fetchFilterOptions()` and `fetchPersons()`
in parallel via `Promise.all`. Filter options are loaded once via 3 parallel
`GET /api/v1/foundation/master-data?category_code=` calls using `Promise.allSettled`.

**API calls** (all relative):
`GET /api/v1/bootstrap/health`,
`GET /api/v1/foundation/master-data?category_code=GENDER|MARITAL_STATUS|BLOOD_GROUP` (filter
options), `GET /api/v1/person/persons?gender_code=&marital_status_code=&blood_group_code=`,
`GET /api/v1/person/persons/{person_pk}` (full detail with resolved master-data names),
`GET /api/v1/person/persons/{person_pk}/addresses` (resolved location chain),
`GET /api/v1/person/search?q=` (trigram similarity search).

**Error-handling pattern:** identical to other tier JS files — loading=true/error=false →
try/fetch/check `res.ok`/parse JSON → catch sets error flag only → finally clears loading.
`selectPerson(p)` toggle-deselects; detail and addresses are fetched in parallel via
`Promise.all` on row click.

**Helpers:**
- `formatName(p)` — joins first/middle/last name parts, filtering nulls
- `formatPhone(p)` — prepends country_phone_code if present
- `statusLabel(p)` — derives lifecycle label: "Active" (is_active + no death), "Deceased"
  (is_active + date_of_death), "Inactive" (!is_active)
- `statusBadgeClass(p)` — maps lifecycle to `.badge-status-active`/`-deceased`/`-inactive`

---

### family.html

The Tier 4 Family Verification UI entry point, structurally parallel to the earlier tier pages
for header/status boilerplate (same head boilerplate and System Status card reusing
`GET /api/v1/bootstrap/health`, "Family" active in the nav bar, subtitle "Tier 4 — Family
Verification"), but the body departs from every other tier page's tab-bar pattern. It renders a
tab-less 3-panel layout — `grid-cols-1 lg:grid-cols-[220px_1fr] xl:grid-cols-[220px_1fr_360px]` —
driven by a `viewMode` toggle ("My Family" / "Org View"; state `viewMode`, default `"admin"`,
despite an in-code comment still calling `"member"` "the current default"):

| Panel | Contents |
|-------|----------|
| **Left (220px)** | The view-mode toggle buttons, then — in **Org View** (`viewMode === 'admin'`) — an org breadcrumb (`orgBreadcrumb`, clickable via `breadcrumbNav(i)`) and a drill-down list of org-children cards (`orgChildren`, one card per child org with name/code/type plus inline family/member/person count badges once `orgChildrenStats` loads); once a Sakha is drilled into (`selectedSakhaCode` set) the panel switches to a **Families** list scoped to that Sakha. In **My Family** view (`viewMode === 'member'`) the panel shows the same Families list, unfiltered. Clicking a family row calls `selectFamily(f)` |
| **Center (1fr)** | "Family Tree" — a "View As" `<select>` (`viewerPersonPk`) letting the user re-root the relationship computation on any family member, then a dynamic generation-based tree rendered via `x-html="renderTree()"` inside `.tree-canvas`: couples grouped in dashed boxes, connector lines between generations, avatar circles color-coded by relationship (`av-viewer`/`av-spouse`/`av-parent`/... classes), viewer/head corner-indicator badges. Clicking any tree node calls `handleTreeClick($event)` → `selectPerson()` |
| **Right (360px, `xl` only)** | Family Info (ID/status/name/Sakha/formed date), then — once a person is selected from the tree or member list — a detail card with demographics, a spouse mini-card (click to jump to the spouse), a "Sangha Membership" block (Sangha Sevi ID, type/status badges, Sakha + Sakha Sangha ID with an amber "Different" mismatch badge when `isMemberSakhaMismatch()` is true), Parichaya Patra / Anumati Patra snapshots, and emergency contact; below that, a Members list (each row clickable, YOU/HEAD badges, amber mismatch warning icon) and a Head History list (bordered rows, "Now" badge when `effective_to` is null) |

The org-admin drill-down (`fetchOrgRoot()` → `fetchOrgChildren(orgPk)` → `drillIntoOrg(org)`)
starts from the Kendra root and lets an admin walk Kendra → Anchalika → ... → Sakha; drilling
into a `SAKHA_SANGHA`-typed org stops the org-tree descent and loads that Sakha's families
instead. Per-child family/member/person count badges are populated by a **separate,
non-blocking** background fetch (`_fetchOrgChildrenStats()`), so the org-children cards render
immediately and the (heavier, uncapped-recursion) stats badges fill in a beat later. The tree/
graph visualization consumes `GET /api/v1/family/families/{pk}/graph?viewer_person_pk=`; the
Sakha-mismatch badges consume `GET /api/v1/family/families/{pk}/sakha-alignment`.

Loads `<script src="/assets/js/family.js?v=24">` at the bottom (cache-bust version — treat this
and the other pages' `?v=N` strings below as a snapshot taken during this doc pass, not
something to re-verify line-by-line every time).

---

### assets/js/family.js

Alpine.js data component for `family.html`. Defines one global function: `familyApp()`.
Constants `FAMILY_API = "/api/v1/family"` and `ORG_API = "/api/v1/organization"`. Also defines
module-level tree-rendering helpers: `avatarClass(gen, isHead, isSpouse)` (relationship →
`.av-*` CSS class) plus the `GEN_LABELS`/`SPOUSE_LABELS` lookup tables.

**State groups:** `health{loading,connected}` (shared pattern with `app.js`); view mode
(`viewMode` — `"member"`/`"admin"`, default `"admin"`); org navigation (`orgBreadcrumb`,
`orgChildren`, `orgChildrenLoading`, `orgChildrenStats`, `selectedSakhaCode`); families
(`families`, `familiesLoading`, `familiesError`, `selectedFamily`, `detailLoading`); members and
head history (`familyMembers`, `membersLoading`, `headHistory`, `headLoading`); graph
(`viewerPersonPk`, `graphMembers`, `graphLoading`, `graphError`); selected-person detail
(`selectedPerson`, `selectedPersonDetail`, `selectedPersonLoading`, `selectedPersonMembership`,
`selectedPersonMembershipLoading`); Sakha alignment (`sakhaAlignment`, `sakhaAlignmentLoading`);
and the recursive tree itself (`treeHead`, `treeSpouse`, `treeNodes`, `_allTreePersons`,
rebuilt by `buildTree()` every time `graphMembers` changes). No `activeTab` state — this is the
only tier page without a DaisyUI tab bar.

**Lifecycle:** `init()` fires `fetchHealth()` without awaiting it ("Fire health check in
parallel — don't block data loading" per the code comment), then branches on `viewMode`:
`await this.fetchOrgRoot()` for `"admin"`, `await this.fetchFamilies()` for `"member"`.
`switchViewMode(mode)` re-runs the same branch when the user toggles "My Family"/"Org View",
resetting family/detail/org state first.

**API calls:**
`GET /api/v1/bootstrap/health`;
`GET ${ORG_API}/organizations?type_code=KENDRA` (`fetchOrgRoot()` — finds the Kendra root and
seeds `orgBreadcrumb`);
`GET ${ORG_API}/organizations/{pk}/children` (`fetchOrgChildren(orgPk)` — awaited, renders cards
immediately);
`GET ${ORG_API}/organizations/{pk}/children-stats` (`_fetchOrgChildrenStats(orgPk)` — fired from
inside `fetchOrgChildren()` but **not awaited by it**, so it resolves in the background and
populates `orgChildrenStats` after the org-children cards are already on screen);
`GET ${FAMILY_API}/families` (optional `?sakha_code=`, used both for the unfiltered "My Family"
list and the Sakha-scoped list once `drillIntoOrg()` lands on a `SAKHA_SANGHA`);
`GET ${FAMILY_API}/families/{pk}/members` and `GET ${FAMILY_API}/families/{pk}/head-history`
(fetched together via `Promise.all` in `selectFamily()`);
`GET ${FAMILY_API}/families/{pk}/graph?viewer_person_pk=` (`fetchGraph()` — called after a
family loads, defaulting `viewerPersonPk` to the head or the first member if there's no head —
and again from `changeViewer()`);
`GET ${FAMILY_API}/families/{pk}/sakha-alignment` (`fetchSakhaAlignment()`, fired
fire-and-forget from `selectFamily()`);
`GET /api/v1/person/persons/{person_pk}` and
`GET ${FAMILY_API}/person/{person_pk}/membership-summary` (fetched together via `Promise.all`
in `selectPerson()`, populating `selectedPersonDetail` and `selectedPersonMembership`).

**Error-handling pattern:** the top-level `fetchHealth()`/`fetchOrgRoot()`/`fetchFamilies()`
calls follow the usual loading/error-flag/finally shape. Everything downstream of a family or
org selection is treated as non-fatal on failure — `selectFamily()`'s members/head-history
fetch, `_fetchOrgChildrenStats()`, and `fetchSakhaAlignment()` all swallow errors silently
(comments call stats and alignment "supplementary"/"informational"), so a partial failure never
blocks the family's core fields, the org cards, or the tree from rendering. `fetchGraph()` is
the one exception in this cluster — it does set `graphError = true` on failure, surfaced in the
UI as "Failed to compute family graph." `selectFamily(f)`/`selectPerson(member)` both
toggle-deselect on repeat click of the same row, same convention as
`selectOrganization()`/`selectPerson()` (person.js).

**Helpers:**
- `formatName(m)` — joins first/middle/last name parts, filtering nulls (same implementation as
  `person.js`'s `formatName()` and `membership.js`'s `formatName()`)
- `displayRelationship(m)` — resolves a display label for a member: viewer flag → direct
  `relationship_label` (from `/graph`) → lookup in `graphMembers` by `person_pk` → viewer-PK
  match → `is_head` fallback → static `relationship_type_name`/`relationship_type_code`
- `getInitials(m)`, `getAvatarClass(m)` — avatar-circle initials and `.av-*` CSS class, falling
  back to a `graphMembers` lookup when called for a plain member-table row that lacks
  `_avatarClass`
- `getSpouseName(personPk)` / `getSpousePersonPk(personPk)` / `getSpouseInitials(personPk)` /
  `selectSpouse(personPk)` — resolve and navigate to a person's spouse via `graphMembers`
  (falling back to the synthesized `treeSpouse` for the viewer)
- `isMemberSakhaMismatch(personPk)` / `getMemberSakhaName(personPk)` — read
  `sakhaAlignment.members` to flag/display a member whose affiliated Sakha differs from the
  family's FAM-036 majority Sakha
- `buildTree()` — rebuilds the recursive couple/children tree from `graphMembers` every time the
  graph loads (synthesizes the viewer node, groups spouses into couples, links couples to
  parent couples via `parent_person_pks`, finds root couples with no parent in the graph)
- `renderTree()` / `_renderSubtree()` / `_renderCouple()` / `_renderPerson()` / `_esc()` — build
  the tree's HTML string by hand (not Alpine templates) for `x-html`, since the tree's depth and
  branching are only known at runtime; `_esc()` does minimal HTML-escaping of user-visible
  name/label text before interpolation
- `handleTreeClick(event)` — event-delegation click handler on the tree container; resolves the
  clicked `data-person-pk` back to a member object and calls `selectPerson()`

---

### membership.html

The Tier 4 Membership Verification UI entry point, structurally parallel to `person.html`: same
head boilerplate and System Status card, but with "Membership" active in the nav bar and
subtitle "Tier 4 — Membership Verification". Below the status card, a compact "Three-Tier Member
Identity" legend card explains the module's central non-obvious concept before any data loads:

| Tier | Column | Example | Scope |
|------|--------|---------|-------|
| Sangha Sevi ID | `sangha_sevi_id` | `SS1` | NSS-wide, permanent, never reused |
| Sakha Sangha ID (Local Sakha ERP Number) | `local_sakha_erp_id` | `ESS1192` | Sakha-scoped, auto-generated, changes on transfer |
| Kendra Number | `parichaya_patra.document_number` | `345/2026/2027` | Kendra-wide, annual (financial year) |

Below the legend, a DaisyUI `tabs tabs-boxed` bar with 2 tabs (driven by `activeTab` /
`switchTab(tab)` in `membership.js`):

| Tab | Contents |
|-----|----------|
| **Members** | Filterable list (2-column layout): left/wide panel is the member table (Sangha Sevi ID/Person ID/Person/Mobile/Email/Type/Status/Sakha/Sakha Sangha ID/Joining Date/Renewal Due) with `<select>` filters for membership type and status (`selectedTypeFilter`/`selectedStatusFilter`); right panel is a detail view — identity block, then four sub-sections that lazy-load together on row click: Sakha Affiliations (effective-dated history), Parichaya Patra (Kendra Number + issuance snapshot), Anumati Patra (hidden entirely for Associate members, who don't receive one — `x-show="selectedMember.membership_type_code !== 'ASSOCIATE'"`), and a Journey Timeline rendered as DaisyUI vertical steps |
| **Search** | Trigram + prefix search input (min 2 chars, 300ms debounce) querying `GET /api/v1/membership/search?q=` across all three identity tiers plus name, mobile, and email; same inline-detail-panel pattern as the Members tab — clicking a result calls `selectMember()` directly without switching tabs |

**UI label convention:** the database column `local_sakha_erp_id` is always displayed as
**"Sakha Sangha ID"** in this UI (table headers, detail panel, Parichaya Patra snapshot) — the
UI-facing label differs from both the DB column name and the API-contract term "Local Sakha ERP
Number"/"ERP Number" used in `docs/03_Solution/api/API_CONTRACT.md`. `PROBATIONARY` membership
type likewise displays as **"Darshaka"** (`typeDisplayName()`, MBR-007) — the database stores
`PROBATIONARY`, the portal shows the Odia/NSS operational term.

Loads `<script src="/assets/js/membership.js?v=4.0">` at the bottom (cache-bust version — see
the note under `family.html` above; treat as a snapshot, not re-verified every doc pass).

---

### assets/js/membership.js

Alpine.js data component for `membership.html`. Defines one global function:
`membershipApp()`. Constant `MEMBERSHIP_API = "/api/v1/membership"`.

**State groups:** `activeTab`, `health{loading,connected}` (shared pattern with `app.js`),
members (`members`, `selectedTypeFilter`, `selectedStatusFilter`, `selectedMember`,
`detailLoading`), sub-data (`affiliations`, `parichayaPatras`, `anumatiPatras`,
`journeyEvents` — all four fetched together per selected member), search (`searchQuery`,
`searchResults`, `searchExecuted`, `_searchDebounce`). Each collection has matching
`*Loading`/`*Error` booleans following the same convention as the other tier JS files.

**Lifecycle:** `init()` fires `fetchHealth()` without awaiting it (doesn't block data loading),
then awaits `fetchMembers()`. `switchTab()` re-fetches members only if the list is still empty
(guard against redundant refetch on repeat tab visits).

**API calls** (all relative, all under `${MEMBERSHIP_API}` except the shared health check):
`GET /api/v1/bootstrap/health`, `GET ${MEMBERSHIP_API}/members` (optional
`?type_code=&status_code=`), `GET ${MEMBERSHIP_API}/members/{sangha_sevi_pk}/affiliations`,
`GET ${MEMBERSHIP_API}/members/{sangha_sevi_pk}/parichaya-patra`,
`GET ${MEMBERSHIP_API}/members/{sangha_sevi_pk}/anumati-patra`,
`GET ${MEMBERSHIP_API}/members/{sangha_sevi_pk}/journey` (last four fetched together via
`Promise.all` in `selectMember()`), `GET ${MEMBERSHIP_API}/search?q=`.

**Error-handling pattern:** identical to the other tier JS files — loading=true/error=false →
try/fetch/check `res.ok`/parse JSON → catch sets error flag only → finally clears loading.
`selectMember(member)` toggle-deselects on repeat click of the same row, same as
`selectPerson()`/`selectOrganization()`.

**Helpers:**
- `formatName(m)` — same implementation as `person.js`'s `formatName()`
- `typeDisplayName(m)` — delegates to shared `NSS.typeDisplayName()` (`assets/js/nss-config.js`);
  still returns `"Darshaka"` for `PROBATIONARY` (UI-label convention, see above)
- `typeBadgeClass(m)`, `statusBadgeClass(m)`, `affBadgeClass(a)`, `docBadgeClass(doc)` — thin
  wrappers delegating to shared `NSS.typeBadgeClass()`/`NSS.statusBadgeClass()`/
  `NSS.affBadgeClass()` (`assets/js/nss-config.js`), which map membership type, lifecycle
  status, affiliation status, and document (Parichaya/Anumati Patra) status to `.badge-type-*`/
  `.badge-status-*`/`.badge-aff-*` classes now centralized in `assets/css/badges.css` — no
  longer defined inline in `membership.html`'s own `<style>` block

---

### assets/css/badges.css

Single source of truth for every badge CSS class used across all six pages, plus the three-tier
identity typographic classes. Loaded by every page's `<head>`, right after `style.css` and
right before `nss-config.js`.

**Class families:**

| Prefix | Count | Purpose |
|--------|-------|---------|
| `.badge-status-*` | 18 | Unified lifecycle status (Organization/Membership/Family — the full `STATUS` category superset) |
| `.badge-type-*` | 4 | Membership type (`probationary`/`regular`/`associate`/`honorary`) |
| `.badge-aff-*` | 3 | Sakha affiliation status (`active`/`archived`/`reactivated`) |
| `.badge-gender-*` | 3 | Gender (`male`/`female`/`other`) |
| `.badge-marital` | 1 | Marital status (single generic style, not per-value) |
| `.badge-role-*` | 2 | Family-tree role indicators (`viewer` = "YOU", `head` = "HEAD") |
| `.data-*` | 6 | Typographic classes for identity fields: `data-sevi-id`/`data-erp-no`/`data-kendra-no` (three-tier identity, theme-aware via DaisyUI CSS variables), `data-sakha-name`, `data-family-id`, `data-label` |

**Rule for future page authors:** individual pages must **not** define `badge-status-*`,
`badge-type-*`, or `badge-aff-*` classes in a page-local inline `<style>` block — this file is
the only place they're allowed to live. Also overrides DaisyUI's default `.badge`/`.badge-xs`
padding (`!important`, since DaisyUI's compiled stylesheet would otherwise win).

---

### assets/js/nss-config.js

Global `NSS` config object, loaded by every page's `<head>` right after `badges.css` and before
the page's own `*.js` file. Not an Alpine.js component (no `x-data` registration) — plain shared
state/logic that any page's inline bindings or `*.js` file calls directly as `NSS.methodName()`.

**What it provides:**

| Member | Purpose |
|--------|---------|
| `TYPE_DISPLAY_NAMES` / `typeDisplayName(code, dbName)` | Bye-Law display-name overrides (currently just `PROBATIONARY` → `"Darshaka"`, MBR-007); falls back to the API's `value_name`, then the raw code |
| `STATUS_BADGE_MAP` / `statusBadgeClass(code)` | Lifecycle status → `.badge-status-*` class, falling back to `badge-ghost` for unknown codes |
| `TYPE_BADGE_MAP` / `typeBadgeClass(code)` | Membership type → `.badge-type-*` class |
| `AFF_BADGE_MAP` / `affBadgeClass(status)` | Affiliation status → `.badge-aff-*` class |
| `GENDER_BADGE_MAP` / `genderBadgeClass(code)` | Gender → `.badge-gender-*` class |
| `showParichayaPatra(typeCode)` | Always `true` — kept as a named method for one documented home, even though the rule doesn't currently vary |
| `showAnumatiPatra(typeCode)` | `true` for every membership type except `ASSOCIATE` (MBR-019A/B) — used by `membership.html` and `family.html`'s `x-show` bindings |

Extracted from what used to be near-duplicate `if`/`else` chains inside `membership.js` (and an
inline `!== 'ASSOCIATE'` check repeated in both `membership.html` and `family.html`) — see
`docs/03_Solution/code_explanations/UI_CODE_EXPLANATIONS.md` §2.14 for the full walkthrough.

---

### assets/css/style.css

Minimal project-specific CSS. Tailwind and DaisyUI handle almost all styling
via the pre-built `tailwind.min.css` — this file exists only for overrides that cannot be
expressed as utility classes.

**Current rules:**

| Selector | Purpose |
|----------|---------|
| `[x-cloak]` | Hides elements with the `x-cloak` attribute until Alpine.js initialises, preventing a flash of unstyled/unrendered template syntax. Standard Alpine.js pattern. |

---

### assets/css/tailwind-input.css / tailwind.min.css

`tailwind-input.css` is the build input — just the three `@tailwind` directives
(`base`/`components`/`utilities`), processed by Tailwind CLI per `../tailwind.config.js`
(`content` globs cover `frontend/**/*.html` and `frontend/assets/js/**/*.js`; `daisyui` plugin
loaded). `tailwind.min.css` is the generated, minified, tree-shaken output (~72 KB) that all six
pages `<link>` — it's committed to the repo (not gitignored), so cloning the repo gives a
working build without installing Node.js. Regenerate via `npm run css:build` (one-shot) or
`npm run css:watch` (rebuild on change) from the repository root after editing any
Tailwind/DaisyUI class in the HTML or JS files — the old CDN Play compiler generated classes at
page-load time in the browser; this pre-built file does not, so a missed rebuild means the new
class silently has no styling.

---

### assets/img/nss-logo.png

NSS logo with transparent background, compressed for web (~100 KB, down from a 1.4 MB original).
Copied from `NSS LOGO/logooo.png`
in the repository root. Displayed in the page header at 56 × 56 pixels. The uncompressed
original is kept alongside it as `assets/img/nss-logo-original.png` for future reprocessing.

---

## How FastAPI Serves This Directory

Defined in `api/main.py`. Registered only if the respective file/directory
exists on disk:

| URL Pattern | FastAPI Handler | Serves |
|-------------|----------------|--------|
| `GET /` | Explicit route → `FileResponse(frontend/index.html)` | The Bootstrap Verification UI |
| `GET /foundation` | Explicit route → `FileResponse(frontend/foundation.html)` | The Foundation Verification UI |
| `GET /organization` | Explicit route → `FileResponse(frontend/organization.html)` | The Organization Verification UI |
| `GET /person` | Explicit route → `FileResponse(frontend/person.html)` | The Person Verification UI |
| `GET /family` | Explicit route → `FileResponse(frontend/family.html)` | The Family Verification UI |
| `GET /membership` | Explicit route → `FileResponse(frontend/membership.html)` | The Membership Verification UI |
| `GET /assets/*` | `StaticFiles` mount → `frontend/assets/` | CSS, JS, images (shared by every page) |

**Why not mount at `/`?** A root-level `StaticFiles` mount would shadow
FastAPI's built-in `/docs` (Swagger UI) and `/openapi.json`. By mounting
only `/assets/*` and serving each page via an explicit route, all
FastAPI built-in routes remain accessible.

**Graceful degradation:** If `frontend/` does not exist on disk, the
mount and all six routes are skipped entirely. If any individual HTML file is
missing, `/` still works — the API continues to work in API-only mode — `/docs` and
`/api/v1/*` are unaffected. The `/foundation`, `/organization`, `/person`, `/family`, and
`/membership` routes are only registered `if` the respective HTML file exists on disk (see
`api/main.py`).

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
`docs/03_Solution/api/FOUNDATION_API_CONTRACT.md`.

Audit columns (`created_at`, `*_by_sangha_sevi_pk`) are excluded from every response by design.

**`organization.html` (via `organization.js`):**

| Method | URL | Response | Tier 2 State |
|--------|-----|----------|-------------|
| GET | `/api/v1/bootstrap/health` | `{ status, database }` | Shared with index.html |
| GET | `/api/v1/organization/types` | `OrganizationTypeResponse[]` | 8 frozen types |
| GET | `/api/v1/organization/statuses` | `OrganizationStatusResponse[]` | 6 lifecycle statuses |
| GET | `/api/v1/organization/organizations?type_code=&status_code=` | `OrganizationResponse[]` | 3 seeded organizations (KEN, NKT, SMR), all roots |
| GET | `/api/v1/organization/organizations/{organization_pk}` | `OrganizationResponse` | Not called directly by the UI (list already carries full detail); available for future use |
| GET | `/api/v1/organization/organizations/{organization_pk}/children` | `OrganizationResponse[]` | Empty — all 3 seeded organizations are roots with no children |
| GET | `/api/v1/organization/hierarchy` | `OrganizationHierarchyNodeResponse[]` | 3 nodes, all at depth 0 |

Response schemas are defined in `api/schemas/organization.py`. `OrganizationResponse` also
resolves geography FK names (country/state/district/city_village/postal_code) via LEFT JOINs to
Foundation's tables. Full contract: `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md`.

**`person.html` (via `person.js`):**

| Method | URL | Response | Tier 3 State |
|--------|-----|----------|-------------|
| GET | `/api/v1/bootstrap/health` | `{ status, database }` | Shared with index.html |
| GET | `/api/v1/foundation/master-data?category_code=GENDER` | `MasterDataResponse[]` | Filter options for gender dropdown |
| GET | `/api/v1/foundation/master-data?category_code=MARITAL_STATUS` | `MasterDataResponse[]` | Filter options for marital status dropdown |
| GET | `/api/v1/foundation/master-data?category_code=BLOOD_GROUP` | `MasterDataResponse[]` | Filter options for blood group dropdown |
| GET | `/api/v1/person/persons?gender_code=&marital_status_code=&blood_group_code=` | `PersonSummaryResponse[]` | Compact list (no Aadhaar, emergency, photo) |
| GET | `/api/v1/person/persons/{person_pk}` | `PersonResponse` | Full detail with resolved master-data names; aadhaar_last4 only (never encrypted/hash) |
| GET | `/api/v1/person/persons/{person_pk}/addresses` | `PersonAddressResponse[]` | Resolved address type + location chain (city→district→state→country); primary first |
| GET | `/api/v1/person/search?q=` | `PersonSummaryResponse[]` | Trigram similarity on first_name/last_name + ILIKE prefix on person_id/mobile; max 50 results |

Response schemas are defined in `api/schemas/person.py`. Sensitive fields (`aadhaar_encrypted`,
`aadhaar_hash`) are never returned by the API — only `aadhaar_last4` for masked display.

**`family.html` (via `family.js`):**

| Method | URL | Response | Tier 4 State |
|--------|-----|----------|-------------|
| GET | `/api/v1/bootstrap/health` | `{ status, database }` | Shared with index.html |
| GET | `/api/v1/family/families` | `FamilyGroupResponse[]` | 1 seeded family (F1 Mishra Paribara) |
| GET | `/api/v1/family/families/{family_group_pk}` | `FamilyGroupResponse` | Not called directly by the UI (list already carries full detail); available for future use |
| GET | `/api/v1/family/families/{family_group_pk}/members` | `FamilyMemberResponse[]` | 3 current members (Ramesh/Sushma/Aniket Mishra) |
| GET | `/api/v1/family/families/{family_group_pk}/head-history` | `FamilyHeadHistoryResponse[]` | 1 head-history record (Ramesh Mishra, current) |
| GET | `/api/v1/family/families?sakha_code=` | `FamilyGroupResponse[]` | Used by the org-admin drill-down view (`family.js`'s `fetchFamilies()`) once a Sakha is selected |
| GET | `/api/v1/family/families/{family_group_pk}/graph?viewer_person_pk=` | graph-member array | Dynamic relationship-label computation via BFS traversal over `nss.family_link`, implemented in `api/services/family_graph.py`; drives the tree visualization. No test coverage yet |
| GET | `/api/v1/family/families/{family_group_pk}/sakha-alignment` | `FamilySakhaAlignmentResponse` | FAM-036 majority-rule "effective Sakha" computation; powers the amber mismatch badges |
| GET | `/api/v1/family/person/{person_pk}/membership-summary` | membership summary | Bridges family context to membership context for the right-panel detail card. No test coverage yet |
| GET | `/api/v1/person/persons/{person_pk}` | `PersonResponse` | Full person detail, fetched alongside `membership-summary` when a tree node/member row is selected |
| GET | `/api/v1/organization/organizations?type_code=KENDRA` | `OrganizationResponse[]` | Admin-view root lookup (`fetchOrgRoot()`) |
| GET | `/api/v1/organization/organizations/{organization_pk}/children` | `OrganizationResponse[]` | Admin-view drill-down cards |
| GET | `/api/v1/organization/organizations/{organization_pk}/children-stats` | aggregate counts | Background, non-blocking fetch; populates the family/member/person count badges on org-children cards |

Response schemas are defined in `api/schemas/family.py` (and `api/schemas/organization.py` for
the org-navigation calls above). `FamilyGroupResponse` resolves family status (Foundation's
unified `STATUS` category) and Sakha name/code via JOINs; member and head-history responses
resolve person name fields and (for members) relationship type via JOINs. Full contract:
`docs/03_Solution/api/API_CONTRACT.md` §7.

**`membership.html` (via `membership.js`):**

| Method | URL | Response | Tier 4 State |
|--------|-----|----------|-------------|
| GET | `/api/v1/bootstrap/health` | `{ status, database }` | Shared with index.html |
| GET | `/api/v1/membership/members?type_code=&status_code=` | `MemberResponse[]` | 5 seeded members (SS1–SS5) |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}` | `MemberResponse` | Not called directly by the UI (list already carries full detail); available for future use |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}/affiliations` | `SakhaAffiliationResponse[]` | 1 row per member, 2 for the transferred member (SS3) |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}/parichaya-patra` | `ParichayaPatraResponse[]` | Regular/Associate members only — Probationary members have none |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}/anumati-patra` | `AnumatiPatraResponse[]` | Probationary members (current) + Regular members who progressed from Probationary (historical, EXPIRED); Associate members have none |
| GET | `/api/v1/membership/members/{sangha_sevi_pk}/journey` | `JourneyEventResponse[]` | Chronological lifecycle events per member |
| GET | `/api/v1/membership/search?q=` | `MemberResponse[]` | Trigram + prefix search across all 3 identity tiers, name, mobile, and email; max 50 results |

Response schemas are defined in `api/schemas/membership.py`. `MemberResponse` resolves person
name/contact, membership type, status, organization (Sakha), and the current active
`local_sakha_erp_id` via JOINs. Full contract: `docs/03_Solution/api/API_CONTRACT.md` §8.

## Future Growth

This shell is designed to evolve:

```
Tier 0   Bootstrap Verification (current)
Tier 1   Foundation Verification (current)
Tier 2   Organization Verification (current)
Tier 3   Person Verification (current)
Tier 4   Family + Membership Verification (current)
  ...
Tier 5   Authentication + login/session UI
  ...
         Full ERP interface
```

The page structure, CSS framework, and Alpine.js pattern established
here carry forward. Authentication UI is deferred to Tier 5 — Tiers 0-4
intentionally have no login, no session, no fake credentials.
