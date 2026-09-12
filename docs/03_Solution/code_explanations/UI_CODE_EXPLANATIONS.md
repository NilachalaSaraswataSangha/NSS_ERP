# UI Code Explanations — `frontend/`

| Field       | Value                                                                  |
|-------------|-------------------------------------------------------------------------|
| Document    | UI_CODE_EXPLANATIONS                                                   |
| Version     | 1.2                                                                     |
| Scope       | All source files under `frontend/`, excluding binary assets (images)    |
| Status      | Complete (updated: org-to-master-data migration)                       |

---

## 1. Purpose of this document

This document is the current, authoritative line-by-line (HTML: section-by-section /
directive-by-directive; JS: state-property-by-property / method-by-method; CSS:
rule-by-rule) reference for every source file in the frontend/UI layer.

It replaces the UI-relevant portions of three retired documents:

- `TIER0_VERTICAL_SLICE.md` (§5 — `frontend/index.html`, `assets/js/app.js`, `assets/css/style.css`)
- `TIER1_FOUNDATION.md` (§6 — `frontend/foundation.html`, `assets/js/foundation.js`)
- `SECURITY_HARDENING.md` (§7 — CDN pinning / Subresource Integrity changes to both HTML files)

Those three documents also covered the database, API, and test layers, and the
cross-tier security-middleware stack — none of that is repeated here; consult
`FOUNDATION_API_CONTRACT.md` and the (now-deleted) tier docs' git history for that
material. This document is organized **file-by-file**, in the order the five files are
listed in §2, rather than tier-by-tier, because a UI file (e.g. `style.css`) is shared
across tiers and a per-tier split would fragment its explanation.

`frontend/README.md` remains the primary human-facing reference for this folder — it
carries the state/method summary tables, the API-endpoints-consumed tables, and the
"how FastAPI serves this directory" reference. This document does not duplicate those
tables verbatim; it adds the missing line-by-line depth that `frontend/README.md`
intentionally leaves out (README.md is a reference card, this is a walkthrough). Where a
README table already gives the complete picture (e.g. the state-property table for
`app.js`), this document restates it briefly for context and then walks the actual code.

All code shown below was read directly from the current working tree; version numbers,
SRI hashes, and attribute values are transcribed exactly.

---

## 2. Files

### 2.1 `frontend/index.html`

**Requirement.** This is the Tier 0 "Bootstrap Verification UI" — the human-facing proof
that the full stack (PostgreSQL `nss.role_master`/`permission_master`/`role_permission` →
FastAPI `/api/v1/bootstrap/*` → browser) actually works end to end, without requiring
Swagger UI or `curl`. It is explicitly **not** an administration dashboard: there is no
login (Tier 0 has no authentication by design — deferred to Tier 5), no forms, and no
CRUD. It is a single static HTML file served by FastAPI's explicit `GET /` route
(`api/main.py`), which mounts `bootstrapApp()` (defined in `assets/js/app.js`) as an
Alpine.js component.

**Section-by-section walkthrough** (file has 278 lines):

**`<head>` (lines 1–17):**
```html
<html lang="en" data-theme="light">
```
- `data-theme="light"` selects DaisyUI's built-in "light" theme for every DaisyUI
  component on the page (cards, badges, buttons, tables).

```html
<link rel="icon" type="image/png" href="/assets/img/nss-logo.png">
<title>Nilachala Saraswata Sangha — Bootstrap Verification</title>
```
- Favicon and tab title both reuse the NSS logo asset served from the static mount.

CDN dependency block (identical on `foundation.html`, exact strings from the current
file):
```html
<!-- Tailwind CSS Play CDN (Tailwind 3.x JIT — generates utility classes in-browser) -->
<script src="https://cdn.tailwindcss.com"></script>
<!-- DaisyUI 4.12.14 (requires Tailwind 3.x) -->
<link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.14/dist/full.min.css" rel="stylesheet" integrity="sha384-iMbeRReqpIEp0z+cPe0FZxnbV/GbGyGjDfou8Rjcr6KSJIptc245QXNVjLMtu5TR" crossorigin="anonymous">
<!-- Alpine.js 3.14.8 -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js" integrity="sha384-X9kJyAubVxnP0hcA+AMMs21U445qsnqhnUF8EBlEpP3a42Kh/JwWjlv2ZcvGfphb" crossorigin="anonymous"></script>

<link rel="stylesheet" href="/assets/css/style.css">
```
- **Tailwind CSS** — loaded via the Play CDN (`cdn.tailwindcss.com`), a browser-side
  JIT compiler that scans the DOM for utility classes and generates matching CSS at
  runtime. It always serves the latest Tailwind 3.x; there is no version to pin in the
  URL, and Subresource Integrity (SRI) does not apply to it because its content is not a
  fixed, hashable artifact — it is explicitly a development-time tool, acknowledged
  as a residual risk rather than hardened.
- **DaisyUI** — pinned to the exact version `4.12.14` on jsdelivr, with an `integrity`
  attribute carrying a `sha384-` Subresource Integrity hash
  (`sha384-iMbeRReqpIEp0z+cPe0FZxnbV/GbGyGjDfou8Rjcr6KSJIptc245QXNVjLMtu5TR`) and
  `crossorigin="anonymous"` (required for the browser to perform the SRI check on a
  cross-origin resource). If jsdelivr ever served a tampered or corrupted file not
  matching this hash, the browser would refuse to apply the stylesheet.
- **Alpine.js** — pinned to `3.14.8`, also on jsdelivr, with its own SRI hash
  (`sha384-X9kJyAubVxnP0hcA+AMMs21U445qsnqhnUF8EBlEpP3a42Kh/JwWjlv2ZcvGfphb`) and
  `crossorigin="anonymous"`. The `defer` attribute delays script execution until the
  HTML document has been fully parsed, so Alpine's `x-data`/`x-init` scan finds a
  complete DOM.
- The local stylesheet `/assets/css/style.css` (§2.5) is loaded last, after the CDN
  stylesheets, so any override rules in it win on specificity ties.
- A page-local `<style>` block follows the `style.css` link, overriding DaisyUI's default
  `.badge`/`.badge-xs`/`.badge-sm` padding and defining 6 `.badge-status-*` classes for
  distinct per-status colors. This block used to be identical across `index.html`,
  `foundation.html`, and `organization.html`; as of the v2.0 org-to-master-data migration
  (2026-09-12), `organization.html`'s copy grew to 13 `.badge-status-*` classes (matching the
  unified `STATUS` category's 13 values — see §2.6), while `index.html` and `foundation.html`
  still carry the older 6-class copy, since neither page renders a lifecycle-status badge. The
  padding override affects every badge on this page (the health-status dot and the
  roles-count badge); the `.badge-status-*` classes themselves are unused here — only
  Organization's Reference Data/Organizations/Hierarchy tabs render lifecycle-status badges
  (see §2.6) — but the block is duplicated rather than factored into `style.css` itself.

---

### 2.6 `frontend/organization.html`

> **v2.0 (2026-09-12):** Type/status field references renamed `organization_status_*` →
> `status_*` throughout (fetch URLs unchanged); type count 8→10 and status count 6→13 following
> the org-to-master-data migration; badge CSS grew from 6 `.badge-status-*` classes to 13; the
> children-hidden-for-types list grew to include `PARIBARIK_ASANA`/`PARIBARIK_SANGHA`.

**Requirement.** This is the Tier 2 "Organization Verification UI" — the visual proof that
the 6 read-only `/api/v1/organization/*` endpoints correctly expose `organization` plus
Foundation's shared `master_data`/`master_category` tables (for type/status, categories
`ORGANIZATION_TYPE` and `STATUS`). It is
structurally parallel to `foundation.html` (same head boilerplate, same System Status card
reusing the Tier 0 health endpoint, same nav bar with three tier links) and organizes its
surface area into three tabs: Reference Data, Organizations, and Hierarchy. Mobile-
responsive from initial implementation (unlike Tiers 0/1, which were retrofitted), using
the same Tailwind breakpoint patterns (`px-3 sm:px-6`, `text-lg sm:text-2xl`, etc.).
Served by FastAPI's `GET /organization` route, conditional on the file existing on disk.

**Section-by-section walkthrough:**

**`<head>`:**
- Same CDN dependency block as `index.html` and `foundation.html`: Tailwind Play CDN,
  DaisyUI 4.12.14 with SRI (`sha384-iMbeRReqpIEp0z+...`), Alpine.js 3.14.8 with SRI
  (`sha384-X9kJyAubVxnP0hcA+...`), local `style.css`. Only the `<title>` differs
  ("— Organization Verification").
- A page-local `<style>` block (also duplicated in `index.html`/`foundation.html` — see below)
  overrides DaisyUI's default `.badge`/`.badge-xs`/`.badge-sm` padding (`!important`, since
  DaisyUI's CDN stylesheet loads after any plain CSS in `style.css` and would otherwise win)
  and defines 13 `.badge-status-*` classes (`active`/`proposed`/`approved`/`suspended`/
  `inactive`/`lapsed`/`transferred`/`resigned`/`expelled`/`deceased`/`dissolved`/`archived`/
  `expired`), each a solid background color with white text — replacing DaisyUI's
  generic semantic badges (`badge-success`/`badge-warning`/`badge-ghost`) so all 13 lifecycle
  statuses (from Foundation's unified `STATUS` category — see §2.7) get their own distinct,
  readable color instead of sharing a handful of generic badges. The 7 classes added in the
  v2.0 migration (`lapsed`/`transferred`/`resigned`/`expelled`/`deceased`/`dissolved`/
  `expired`) cover status values that `STATUS` absorbed from the wider, ERP-unified lifecycle
  vocabulary — values the old 6-status, Organization-only set never needed.

**Root component:**
```html
<div x-data="organizationApp()" x-init="init()" class="mx-auto px-3 py-4 sm:px-6 sm:py-6 lg:px-10 2xl:px-16">
```
- Mobile-first padding: `px-3 py-4` below 640px, `sm:px-6 sm:py-6` from 640px, `lg:px-10`
  from 1024px, `2xl:px-16` at 1536px+. Calls `organizationApp()` (§2.7).

**Header:** Same layout as `index.html`/`foundation.html` but with mobile-responsive sizing
(`h-10 w-10 sm:h-14 sm:w-14` for the logo, `text-lg sm:text-2xl` for the title). The nav
bar has three links: Bootstrap, Foundation, Organization — with Organization styled
`btn-active`.

**System Status card:** Identical `x-if` triad to the other pages, bound to
`organizationApp().health`, calling the Tier 0 `/api/v1/bootstrap/health` endpoint.

**Tab bar:**
```html
<div class="tabs tabs-boxed bg-base-100 shadow-sm mb-4 inline-flex overflow-x-auto -mx-3 px-3 sm:mx-0 sm:px-0">
    <button class="tab" :class="{ 'tab-active': activeTab === 'reference' }" @click="switchTab('reference')">Reference Data</button>
    <button class="tab" :class="{ 'tab-active': activeTab === 'organizations' }" @click="switchTab('organizations')">Organizations</button>
    <button class="tab" :class="{ 'tab-active': activeTab === 'hierarchy' }" @click="switchTab('hierarchy')">Hierarchy</button>
</div>
```
- `overflow-x-auto` with `-mx-3 px-3 sm:mx-0 sm:px-0` makes the tab bar horizontally
  scrollable on mobile (tab labels don't wrap), while restoring normal margins on larger
  screens. Same DaisyUI `tabs tabs-boxed` pattern as `foundation.html`.

**Tab 1 — Reference Data:** Two-column grid (`grid-cols-1 xl:grid-cols-2`) with
Organization Types (10 frozen types, sourced from Foundation `master_data` category
`ORGANIZATION_TYPE`) on the left and Lifecycle Statuses (13 unified statuses, category
`STATUS`) on the right. Each card follows the standard loading/error/data `x-if` triad.
Type and status badges use `whitespace-nowrap` on both the `<td>` and `<span>` to prevent
text spill for long names like "Anchalika Sangha". Every status `<tr>`/badge binding reads
`s.status_pk`/`s.status_code`/`s.status_name` (renamed from `organization_status_*` in the
pre-migration schema) — the `status_pk + '-row'` key expression on the `<template x-for>` is
a leftover disambiguation pattern from when multiple tables shared row keys, kept for
uniqueness safety.

**Tab 2 — Organizations:** Filter controls at the top (type and status dropdowns, both
`x-model`-bound to `selectedTypeFilter`/`selectedStatusFilter`, triggering
`filterOrganizations()` on change — see §2.7 for the full current body, including the
auto-select-on-single-result behavior). The status `<select>` is `:disabled` (and dimmed via
`:class="{ 'opacity-40 cursor-not-allowed': ... }"`) whenever the type filter is `KENDRA`,
`NILACHALA_KUTIRA`, or `SMRUTI_MANDIRA` — each is a unique singleton type with no meaningful
status dimension. Below, a responsive table of organizations with
clickable rows (`@click="selectOrganization(org)"`); each row's status badge uses the
`badge-status-*` classes (one `:class` binding per status code, now 13 — see the `<head>`
notes above) rather than DaisyUI's generic semantic badges, reading `org.status_code`/
`org.status_name` (renamed from `organization_status_code`/`organization_status_name`).
When an organization is selected, a detail panel appears below the table showing:
- Full organization metadata (name, code, ID, type, status) — the Status field reads
  `selectedOrg.status_name` (renamed from `organization_status_name`).
- Address information (address lines, city/village, district, state, country, postal code).
- Coordinates (latitude, longitude) if present.
- A Children section — wrapped in `<template x-if="!['NILACHALA_KUTIRA', 'SMRUTI_MANDIRA',
  'PATHA_CHAKRA', 'SAKHA_ASANA', 'PARIBARIK_ASANA', 'PARIBARIK_SANGHA'].includes(selectedOrg.organization_type_code)">`
  — entirely hidden for org types that structurally cannot have children (the two unique
  institutional types, plus `PATHA_CHAKRA`, `SAKHA_ASANA`, and — new in the v2.0 migration —
  the two family-level types `PARIBARIK_ASANA` and `PARIBARIK_SANGHA`, all leaf types in the
  hierarchy). When shown, the children list (fetched via `/organizations/{pk}/children`) has
  its own loading/empty state handling and the same `badge-status-*` classes as the parent
  table, reading `child.status_code`/`child.status_name` (renamed from
  `organization_status_code`/`organization_status_name`).

**Tab 3 — Hierarchy:** Flat tree rendering of the recursive CTE result. Each node is
rendered as a row with indentation controlled by:
```html
<div :style="depthIndent(node.depth)" class="flex items-center gap-2">
```
- `depthIndent(depth)` returns `padding-left: ${depth * 1.5}rem` — depth 0 (roots) has no
  indent, depth 1 gets 1.5rem, depth 2 gets 3rem, etc. Each node shows its name,
  type badge, and status badge (also using the now-13 `badge-status-*` classes, reading
  `node.status_code`/`node.status_name` — renamed from `organization_status_code`/
  `organization_status_name` — replacing an earlier 3-way `active`/`proposed`/"everything
  else" `badge-ghost` mapping that collapsed the rest into one indistinguishable grey badge),
  and code.

**Footer and script include:** Same copyright footer as the other pages. Loads
`<script src="/assets/js/organization.js"></script>` at the bottom.

---

### 2.7 `frontend/assets/js/organization.js`

> **v2.0 (2026-09-12):** State/fetch logic unchanged (fetch URLs are still
> `/api/v1/organization/types` and `/statuses` — Organization does **not** call Foundation's
> `master-data` endpoint directly). Comment banners updated to say "10 frozen types" and "13
> unified lifecycle statuses." All downstream field consumption (in `organization.html`) reads
> `status_*` instead of `organization_status_*` — see §2.6.

**Requirement.** The client-side state/behaviour layer for `organization.html`, mirroring
the role `foundation.js` plays for `foundation.html` but scoped to the Organization
module's 6 API endpoints across 3 tabs. Defines one global factory function,
`organizationApp()`.

**Full file, 214 lines. Walkthrough:**

```javascript
const ORG_API = "/api/v1/organization";
```
- Same relative-path pattern as `app.js`'s `API_BASE` and `foundation.js`'s `FND_API`. Points
  at the Organization router's own `/types`/`/statuses` endpoints — those endpoints internally
  query Foundation's `master_data` (see `API_CODE_EXPLANATIONS.md` §2.9), but this file never
  calls `/api/v1/foundation/master-data` itself; the indirection is entirely server-side.

**State properties** (grouped by the file's own comment banners):

```javascript
activeTab: "reference",
health: { loading: true, connected: false },
```
- Default tab is `"reference"` (vs Foundation's `"master"`).
- Same health object shape, reusing the Tier 0 health endpoint.

**Reference Data group:**
```javascript
orgTypes: [],
orgTypesLoading: true,
orgTypesError: false,

orgStatuses: [],
orgStatusesLoading: true,
orgStatusesError: false,
```
- Both start `loading: true` because they're fetched eagerly by `init()`. The file's module
  docstring documents these as "1. Organization Types (10 frozen types)" and "2. Statuses (13
  unified lifecycle statuses)" — both counts bumped by the org-to-master-data migration (from
  8 and 6 respectively).

**Organizations group:**
```javascript
organizations: [],
orgsLoading: true,
orgsError: false,
selectedTypeFilter: "",
selectedStatusFilter: "",

selectedOrg: null,
orgChildren: [],
childrenLoading: false,
childrenError: false,
```
- `selectedTypeFilter` and `selectedStatusFilter` are bound via `x-model` to the filter
  dropdowns. `selectedOrg` drives the detail panel; `orgChildren` holds the children list
  for the selected organization.

**Hierarchy group:**
```javascript
hierarchy: [],
hierarchyLoading: true,
hierarchyError: false,
```

**Init:**
```javascript
async init() {
    await this.fetchHealth();
    await this.loadReferenceTab();
},
```
- Sequential: health check first, then the default tab's data. Same pattern as
  `foundation.js`'s `init()`.

**Tab switching and lazy loading:**
```javascript
async switchTab(tab) {
    this.activeTab = tab;
    if (tab === "reference") await this.loadReferenceTab();
    else if (tab === "organizations") await this.loadOrganizationsTab();
    else if (tab === "hierarchy") await this.loadHierarchyTab();
},

async loadReferenceTab() {
    if (this.orgTypes.length === 0) await this.fetchOrgTypes();
    if (this.orgStatuses.length === 0) await this.fetchOrgStatuses();
},

async loadOrganizationsTab() {
    if (this.organizations.length === 0) await this.fetchOrganizations();
},

async loadHierarchyTab() {
    if (this.hierarchy.length === 0) await this.fetchHierarchy();
},
```
- Same lazy-load-once pattern as `foundation.js`: `array.length === 0` guards prevent
  re-fetching on tab revisits. This works because all three data sets (types, statuses,
  organizations, hierarchy) are seeded and never legitimately empty.

**Reference Data fetchers:**
```javascript
async fetchOrgTypes() { ... }
async fetchOrgStatuses() { ... }
```
- Standard four-step pattern against `GET ${ORG_API}/types` and `GET ${ORG_API}/statuses`.

**Organization fetchers:**
```javascript
async fetchOrganizations() {
    this.orgsLoading = true;
    this.orgsError = false;
    try {
        let url = `${ORG_API}/organizations`;
        const params = [];
        if (this.selectedTypeFilter)
            params.push(`type_code=${encodeURIComponent(this.selectedTypeFilter)}`);
        if (this.selectedStatusFilter)
            params.push(`status_code=${encodeURIComponent(this.selectedStatusFilter)}`);
        if (params.length) url += `?${params.join("&")}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error(res.statusText);
        this.organizations = await res.json();
    } catch {
        this.orgsError = true;
    } finally {
        this.orgsLoading = false;
    }
},
```
- Builds the URL with optional `type_code` and `status_code` query parameters, both
  `encodeURIComponent`-encoded. Unlike Foundation's `filterByCategory()` which converts
  empty string to `null`, here empty strings are simply not appended to the params array.

```javascript
async filterOrganizations() {
    // Clear detail panel — previous selection may not exist in new filter results
    this.selectedOrg = null;
    this.orgChildren = [];

    // Status filter is not applicable for unique institutional types
    const noStatusTypes = ['KENDRA', 'NILACHALA_KUTIRA', 'SMRUTI_MANDIRA'];
    if (noStatusTypes.includes(this.selectedTypeFilter)) {
        this.selectedStatusFilter = '';
    }

    this.organizations = [];
    await this.fetchOrganizations();

    // Auto-select if filter yields exactly one result
    if (this.organizations.length === 1) {
        await this.selectOrganization(this.organizations[0]);
    }
},
```
- Bound to both filter dropdowns' `@change`. Clears `selectedOrg`/`orgChildren` first, since
  the previously-selected organization may not be in the new filtered result set. `KENDRA`,
  `NILACHALA_KUTIRA`, and `SMRUTI_MANDIRA` are each a unique, singleton institutional type with
  no meaningful status filter (there's only ever one row) — selecting one of them as the type
  filter forces `selectedStatusFilter` back to `""` (the corresponding `<select>` is also
  `:disabled` and dimmed in `organization.html`, see §2.6). Blanks the array (so the loading
  spinner shows), re-fetches, then auto-selects the single result if the filter narrowed the
  list to exactly one organization — sparing the user an extra click for the common
  "look up one org by type" case.

```javascript
async selectOrganization(org) {
    if (this.selectedOrg?.organization_pk === org.organization_pk) {
        this.selectedOrg = null;
        this.orgChildren = [];
        return;
    }
    this.selectedOrg = org;
    this.childrenLoading = true;
    this.childrenError = false;
    this.orgChildren = [];

    try {
        const res = await fetch(
            `${ORG_API}/organizations/${org.organization_pk}/children`
        );
        if (!res.ok) throw new Error(res.statusText);
        this.orgChildren = await res.json();
    } catch {
        this.childrenError = true;
    } finally {
        this.childrenLoading = false;
    }
},
```
- Same toggle-off guard pattern as `app.js`'s `selectRole()` and `foundation.js`'s
  geographic drill-down. Clicking the same org again deselects and clears children.
  Selecting a new org immediately blanks `orgChildren` (preventing stale data flash) and
  fetches `GET /organizations/{pk}/children`.

**Hierarchy fetcher:**
```javascript
async fetchHierarchy() { ... }
```
- Standard four-step pattern against `GET ${ORG_API}/hierarchy`.

**Helper:**
```javascript
depthIndent(depth) {
    return `padding-left: ${depth * 1.5}rem`;
},
```
- Returns an inline CSS `padding-left` value proportional to `depth`. Called from the
  hierarchy tab's `x-for` loop via `:style="depthIndent(node.depth)"`. At depth 0 (roots),
  returns `padding-left: 0rem`; at depth 1, `1.5rem`; at depth 2, `3rem`; etc.

**Root component (line 20):**
```html
<div x-data="bootstrapApp()" x-init="init()" class="mx-auto px-6 py-6 lg:px-10 2xl:px-16">
```
- `x-data="bootstrapApp()"` — calls the factory function defined in `app.js` to create
  this component's reactive data store; every directive inside this `<div>` can read
  and write that store's properties.
- `x-init="init()"` — runs once, immediately after the store is created, calling the
  `init()` method (§2.2) which kicks off the three parallel API fetches.
- The padding classes (`px-6` mobile → `lg:px-10` tablet → `2xl:px-16` large desktop)
  give the page progressive side margins with no `max-width` cap, so the layout fills
  the viewport rather than centering in a fixed column.

**Header (lines 23–35):**
```html
<header class="mb-6 flex items-center justify-between flex-wrap gap-4">
    <div class="flex items-center gap-4">
        <img src="/assets/img/nss-logo.png" alt="NSS Logo" class="h-14 w-14 object-contain">
        <div>
            <h1 ...>Nilachala Saraswata Sangha</h1>
            <p ...>Tier 0 — Bootstrap Verification</p>
        </div>
    </div>
    <nav class="flex gap-2">
        <a href="/" class="btn btn-sm btn-active">Bootstrap</a>
        <a href="/foundation" class="btn btn-sm btn-ghost">Foundation</a>
    </nav>
</header>
```
- Static logo (56×56px via `h-14 w-14`), title, and tier subtitle — no Alpine bindings.
- Two-link nav: `Bootstrap` is styled `btn-active` (the current page) and `Foundation`
  is `btn-ghost` (the other page, one click away). These are plain anchor tags, not
  Alpine-driven — the "active" styling is hardcoded per file rather than computed,
  since each HTML file only ever represents one nav state.

**System Status card (lines 38–62)** — a centred, narrow card (`max-w-md mx-auto`)
showing database connectivity as a three-way `x-if` chain:
```html
<template x-if="health.loading">
    <span ...><span class="loading loading-spinner loading-xs"></span> Checking...</span>
</template>
<template x-if="!health.loading && health.connected">
    <span ...><span class="badge badge-success badge-xs"></span> <span>Database Connected</span></span>
</template>
<template x-if="!health.loading && !health.connected">
    <span ...><span class="badge badge-error badge-xs"></span> <span>Database Unavailable</span></span>
</template>
```
- `x-if` (not `x-show`) is used for all three branches — Alpine physically adds/removes
  the `<template>`'s content from the DOM rather than toggling `display`, since exactly
  one of the three states is ever true and there is no need to keep the other two
  mounted.
- The three conditions are mutually exclusive and jointly exhaustive over
  `{loading: bool, connected: bool}`, so exactly one renders at a time.
- DaisyUI `loading loading-spinner loading-xs` renders an animated spinner;
  `badge-success`/`badge-error` render green/red dot badges. No raw error text is ever
  shown — the UI only ever displays one of these three fixed strings.

**Three-column responsive grid (line 65):**
```html
<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 xl:gap-6">
```
- 1 column below `md` (mobile, stacked), 2 columns from `md` to below `xl` (tablet — the
  third card wraps below), 3 columns from `xl` up (desktop — all three side by side).

**Card 1 — RBAC Roles (lines 68–124):**
```html
<span class="badge badge-ghost badge-sm" x-text="roles.length + ' roles'"></span>
```
- `x-text` sets the badge's text content reactively to e.g. `"8 roles"`.

Three mutually exclusive `x-if` blocks gate the card body:
```html
<template x-if="rolesLoading">
    <div class="flex justify-center py-6">
        <span class="loading loading-spinner loading-md"></span>
    </div>
</template>

<template x-if="!rolesLoading && rolesError">
    <div class="alert alert-error mt-2">
        <span class="text-sm">Failed to load roles.</span>
    </div>
</template>

<template x-if="!rolesLoading && !rolesError && roles.length > 0">
    <div class="overflow-x-auto mt-2">
        <table class="table table-sm">
            <!-- header row + x-for body, shown separately below -->
        </table>
    </div>
</template>
```
- `rolesLoading` (spinner), `!rolesLoading && rolesError` (DaisyUI `alert alert-error`),
  and `!rolesLoading && !rolesError && roles.length > 0` (the data table) are mutually
  exclusive. There is no explicit "0 roles, no error" branch — Tier 0 always seeds 8
  roles, so this state is not designed for, but if the array were empty and non-error, no
  table would render (silently blank card body).

```html
<template x-for="role in roles" :key="role.role_master_pk">
    <tr class="cursor-pointer hover"
        :class="{ 'bg-base-200': selectedRole?.role_master_pk === role.role_master_pk }"
        @click="selectRole(role)">
```
- `x-for="role in roles"` — repeats the `<tr>` once per element of the `roles` array
  (§2.2 state).
- `:key="role.role_master_pk"` — gives Alpine a stable identity per row for efficient
  DOM diffing across re-renders (analogous to React's `key`).
- `:class="{ 'bg-base-200': ... }"` — conditionally applies the highlight class only to
  the row matching `selectedRole` (optional-chained since `selectedRole` starts `null`).
- `@click="selectRole(role)"` — calls the method (§2.2) that drives the third card.

The remaining cells in the row:
```html
<td class="font-mono text-xs whitespace-nowrap" x-text="role.role_code" :title="role.role_code"></td>
<td class="text-xs" x-text="role.role_name" :title="role.role_name"></td>
<td>
    <span class="badge badge-xs"
          :class="role.role_class === 'SYSTEM' ? 'badge-primary' : 'badge-secondary'"
          x-text="role.role_class">
    </span>
</td>
<td class="text-xs" x-text="role.scope_level || '—'"></td>
<td class="text-center">
    <span x-show="role.is_active" class="text-success">&#10003;</span>
    <span x-show="!role.is_active" class="text-error">&#10007;</span>
</td>
```
- `role.role_code` and `role.role_name` are bound via `x-text` and mirrored into a
  `:title` attribute (native browser hover tooltip) — useful since the code cell is
  `font-mono text-xs whitespace-nowrap` and can visually truncate on narrow layouts.
- Ternary `:class` on the class badge — `SYSTEM` roles get the primary (blue) badge
  colour, anything else (`ORGANIZATIONAL`) gets secondary.
- `scope_level` renders as `role.scope_level || '—'` (em dash fallback for null scope).
- The Active column uses two `x-show` spans (not `x-if`) — both `✓` (`&#10003;`,
  `text-success`) and `✗` (`&#10007;`, `text-error`) are always in the DOM; `x-show`
  merely toggles `display:none` on whichever doesn't match `role.is_active`.

**Card 2 — Permissions (lines 127–185):** structurally identical loading/error pattern,
plus a fourth `x-if` branch specific to this card:
```html
<template x-if="!permissionsLoading && !permissionsError && permissions.length === 0">
    <div class="py-4">
        <p ...>No permissions configured yet.</p>
        <p ...>Permission catalogue is populated progressively as functional modules are implemented.</p>
    </div>
</template>
```
- Unlike the Roles card, Permissions is expected to be empty in Tier 0 (no
  `permission_master` seed data), so this branch explicitly explains why, rather than
  silently rendering nothing. The data-table branch (`permissions.length > 0`) uses the
  same code/name cell pattern as Roles, but the class badge is replaced by a module badge:
```html
<span class="badge badge-outline badge-xs" x-text="perm.module_code"></span>
```
  and there is no `@click` handler on the `<tr>` — this table is not interactive.

**Card 3 — Role Permissions (lines 188–264)** — the only interactive/drill-down card:
```html
<template x-if="!selectedRole">
    <p ...>Select a role from the left to view its permissions.</p>
</template>
<template x-if="selectedRole">
    ...
</template>
```
- Before any row is clicked, shows a prompt. After selection, shows a detail strip:
```html
<div class="flex flex-wrap gap-x-4 gap-y-1 text-xs mb-3">
    <div>
        <span class="text-base-content/50">Role:</span>
        <span class="font-mono font-semibold" x-text="selectedRole.role_code"></span>
    </div>
    <div>
        <span class="text-base-content/50">Class:</span>
        <span x-text="selectedRole.role_class"></span>
    </div>
    <div>
        <span class="text-base-content/50">Scope:</span>
        <span x-text="selectedRole.scope_level || '—'"></span>
    </div>
</div>
```
  showing `selectedRole.role_code`, `role_class`, and `scope_level || '—'`, followed by
  its own independent loading/error/empty `x-if` chain:
```html
<template x-if="rolePermsLoading">
    <div class="flex items-center gap-2 py-2">
        <span class="loading loading-spinner loading-xs"></span>
        <span class="text-sm text-base-content/60">Loading permissions...</span>
    </div>
</template>

<template x-if="!rolePermsLoading && rolePermsError">
    <div class="alert alert-error">
        <span class="text-sm">Failed to load role permissions.</span>
    </div>
</template>

<template x-if="!rolePermsLoading && !rolePermsError && rolePermissions.length === 0">
    <p class="text-sm text-base-content/60">No permissions assigned.</p>
</template>
```
  driven by `rolePermsLoading` / `rolePermsError` / `rolePermissions`. The fourth branch
  (`rolePermissions.length > 0`) repeats the same code/name/module-badge/active-checkmark
  row shape used in Card 2.

**Footer (lines 269–271):**
```html
<footer class="text-center text-xs text-base-content/30 mt-6">
    <p>&copy; 2026 Nilachala Saraswata Sangha. All rights reserved.</p>
</footer>
```
- Static, no bindings.

**Script include (line 275):**
```html
<script src="/assets/js/app.js"></script>
```
- Loaded last, after the root `<div>` markup, without `defer` — by this point Alpine.js
  (deferred, loaded in `<head>`) has already executed and is waiting; `app.js` merely
  needs to define the global `bootstrapApp()` function before Alpine's initial scan
  reaches this `<div>`, which it does since script tags execute in document order and
  Alpine's own `defer`red execution runs after all synchronous scripts including this
  one.

---

### 2.2 `frontend/assets/js/app.js`

**Requirement.** This file is the entire client-side "brain" for `index.html`: it owns
all reactive state (loading flags, fetched arrays, selection state) and all
communication with the four Tier 0 Bootstrap API endpoints. It exists so `index.html`
stays pure markup — every dynamic behaviour lives here, in one factory function,
`bootstrapApp()`, that Alpine.js instantiates via `x-data="bootstrapApp()"`.

**Full file, 108 lines. Walkthrough:**

```javascript
const API_BASE = "/api/v1/bootstrap";
```
- Module-scope constant, not part of the returned Alpine store. A **relative** path —
  no scheme/host/port — so requests always target whatever origin served this page
  (works identically on `localhost:8001`, a Render deployment, etc., with zero
  configuration).

```javascript
function bootstrapApp() {
    return {
```
- A plain factory function returning a plain object literal. Alpine calls this once per
  `x-data` mount and uses the returned object as the reactive store (Alpine wraps every
  property in a reactivity proxy).

**State properties** (in declaration order):

```javascript
health: { loading: true, connected: false },
```
- Nested object backing the System Status card; starts "checking" and "not connected"
  until the first fetch resolves.

```javascript
roles: [],
rolesLoading: true,
rolesError: false,
```
- `roles` is the backing array for the RBAC Roles table, empty until `fetchRoles()`
  populates it. `rolesLoading` gates the Roles card's spinner branch — `true` from the
  start because `init()` fetches immediately on mount. `rolesError` gates the Roles
  card's error `alert`.

```javascript
permissions: [],
permissionsLoading: true,
permissionsError: false,
```
- Backing array for the Permissions table, plus the same loading/error pair pattern as
  `roles`/`rolesLoading`/`rolesError`.

```javascript
selectedRole: null,
rolePermissions: [],
rolePermsLoading: false,
rolePermsError: false,
```
- `selectedRole` is the clicked role object, or `null` if none selected — read by the
  `:class` highlight binding and the Role Permissions card's `x-if`. `rolePermissions`
  holds the permissions for `selectedRole`, populated on click. `rolePermsLoading` starts
  `false` (unlike `rolesLoading`/`permissionsLoading`) because this panel only loads in
  response to a user click, not on initial mount; `rolePermsError` follows the same
  toggle-on-demand pattern.

**Methods:**

```javascript
async init() {
    await Promise.all([
        this.fetchHealth(),
        this.fetchRoles(),
        this.fetchPermissions(),
    ]);
},
```
- Called once by `x-init="init()"`. `Promise.all` fires all three fetches **concurrently**
  rather than sequentially — each card populates independently as soon as its own fetch
  resolves, instead of waiting for the slowest of the three before showing any data.

```javascript
async fetchHealth() {
    this.health.loading = true;
    try {
        const res = await fetch(`${API_BASE}/health`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        this.health.connected = data.database === "connected";
    } catch {
        this.health.connected = false;
    } finally {
        this.health.loading = false;
    }
},
```
- Calls `GET /api/v1/bootstrap/health`. `res.ok` is `true` only for HTTP 200–299; a
  non-2xx status is deliberately converted into a thrown `Error` so it falls into the
  same `catch` as a network failure or JSON-parse failure — the UI treats "reachable but
  errored" and "unreachable" identically as "disconnected."
- `data.database === "connected"` reads the specific field from the API's
  `HealthResponse` shape (`{status, database}`) — it does not merely check `res.ok`,
  since the health endpoint can return HTTP 200 with `database: "unreachable"` (a
  "degraded" but still-responding API).
- The bare `catch { ... }` (no bound error variable) intentionally discards the error
  object — no error detail is ever surfaced to `connected`, satisfying the "never expose
  raw database errors" design constraint.
- `finally` unconditionally clears `loading`, regardless of which branch ran.

```javascript
async fetchRoles() {
    this.rolesLoading = true;
    this.rolesError = false;
    try {
        const res = await fetch(`${API_BASE}/roles`);
        if (!res.ok) throw new Error(res.statusText);
        this.roles = await res.json();
    } catch {
        this.rolesError = true;
    } finally {
        this.rolesLoading = false;
    }
},
```
- Identical four-step shape to every other fetch method in this file (and in
  `foundation.js`): (1) set `loading=true, error=false`; (2) `try` fetch → check
  `res.ok` → parse JSON → assign to state; (3) `catch` sets only the error flag; (4)
  `finally` clears loading. `GET /api/v1/bootstrap/roles` returns the 8 frozen roles as
  a JSON array which is assigned wholesale to `this.roles`, triggering the `x-for` in
  `index.html` to re-render.

```javascript
async fetchPermissions() {
    this.permissionsLoading = true;
    this.permissionsError = false;
    try {
        const res = await fetch(`${API_BASE}/permissions`);
        if (!res.ok) throw new Error(res.statusText);
        this.permissions = await res.json();
    } catch {
        this.permissionsError = true;
    } finally {
        this.permissionsLoading = false;
    }
},
```
- Same four-step pattern against `GET /api/v1/bootstrap/permissions`. In Tier 0 this
  endpoint always returns `[]` (no `permission_master` seed data) — the method has no
  special-case handling for that; an empty array is a perfectly normal successful
  response, and the "No permissions configured yet" messaging lives entirely in the
  HTML's `x-if permissions.length === 0` branch, not here.

```javascript
async selectRole(role) {
    // Toggle off if clicking the same role
    if (this.selectedRole?.role_master_pk === role.role_master_pk) {
        this.selectedRole = null;
        this.rolePermissions = [];
        return;
    }

    this.selectedRole = role;
    this.rolePermsLoading = true;
    this.rolePermsError = false;
    this.rolePermissions = [];

    try {
        const res = await fetch(
            `${API_BASE}/roles/${role.role_master_pk}/permissions`
        );
        if (!res.ok) throw new Error(res.statusText);
        this.rolePermissions = await res.json();
    } catch {
        this.rolePermsError = true;
    } finally {
        this.rolePermsLoading = false;
    }
},
```
- Triggered by `@click="selectRole(role)"` on each role row.
- **Toggle guard first**: `this.selectedRole?.role_master_pk === role.role_master_pk` —
  the optional-chain (`?.`) is required because `selectedRole` may be `null` on the
  first call; comparing `null?.role_master_pk` yields `undefined`, which never equals a
  real UUID, so the guard is false and execution falls through on first click. Clicking
  the *same* already-selected role a second time clears both `selectedRole` and
  `rolePermissions` and returns early — no fetch is issued.
- Selecting a *different* (or first) role sets `selectedRole`, immediately blanks
  `rolePermissions` (so stale data from a previous selection never flashes under the new
  role's header while the new fetch is in flight), then fetches
  `GET /api/v1/bootstrap/roles/{role_pk}/permissions`. In Tier 0 this always resolves to
  `[]` (no `role_permission` seed rows), but the fetch/loading/error machinery is fully
  exercised regardless.

---

### 2.3 `frontend/foundation.html`

**Requirement.** This is the Tier 1 "Foundation Verification UI" — the visual proof that
the 17 read-only `/api/v1/foundation/*` endpoints correctly expose 11 of the 12
Foundation tables (the 12th, `field_change_log`, is intentionally never exposed — audit
data needs authentication, deferred to Tier 5). It is structurally parallel to
`index.html` (same head boilerplate, same System Status card reusing the Tier 0 health
endpoint, same nav bar) but organizes its much larger surface area — master data,
system config, a 4-level geographic hierarchy, and runtime tables — into four tabs
instead of index.html's fixed three-column layout, since all of that could not
reasonably fit on one screen at once. Served by FastAPI's explicit `GET /foundation`
route, conditional on the file existing on disk.

**Section-by-section walkthrough** (597 lines):

**`<head>` (lines 1–17):**
```html
<title>Nilachala Saraswata Sangha — Foundation Verification</title>

<!-- Tailwind CSS Play CDN (Tailwind 3.x JIT — generates utility classes in-browser) -->
<script src="https://cdn.tailwindcss.com"></script>
<!-- DaisyUI 4.12.14 (requires Tailwind 3.x) -->
<link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.14/dist/full.min.css" rel="stylesheet" integrity="sha384-iMbeRReqpIEp0z+cPe0FZxnbV/GbGyGjDfou8Rjcr6KSJIptc245QXNVjLMtu5TR" crossorigin="anonymous">
<!-- Alpine.js 3.14.8 -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.8/dist/cdn.min.js" integrity="sha384-X9kJyAubVxnP0hcA+AMMs21U445qsnqhnUF8EBlEpP3a42Kh/JwWjlv2ZcvGfphb" crossorigin="anonymous"></script>

<link rel="stylesheet" href="/assets/css/style.css">
```
- Byte-for-byte the same CDN block as `index.html` (§2.1) — same Tailwind Play CDN script
  tag, same DaisyUI 4.12.14 `<link>` with the identical
  `integrity="sha384-iMbeRReqpIEp0z+cPe0FZxnbV/GbGyGjDfou8Rjcr6KSJIptc245QXNVjLMtu5TR"`
  hash, same Alpine.js 3.14.8 `<script defer>` with the identical
  `integrity="sha384-X9kJyAubVxnP0hcA+AMMs21U445qsnqhnUF8EBlEpP3a42Kh/JwWjlv2ZcvGfphb"`
  hash, same local `/assets/css/style.css` link, and the same trailing `.badge-status-*`
  `<style>` block described in §2.1. Only the `<title>` differs
  ("— Foundation Verification").

**Root component and header (lines 20–35):**
```html
<div x-data="foundationApp()" x-init="init()" class="mx-auto px-6 py-6 lg:px-10 2xl:px-16">
```
- Same wrapper pattern as `index.html`, calling `foundationApp()` (§2.4) instead of
  `bootstrapApp()`. Header is identical except the subtitle reads "Tier 1 — Foundation
  Verification" and the nav swaps which link is `btn-active`:
```html
<a href="/" class="btn btn-sm btn-ghost">Bootstrap</a>
<a href="/foundation" class="btn btn-sm btn-active">Foundation</a>
```

**System Status card (lines 38–62):** byte-for-byte identical `x-if` triad to
`index.html` (`health.loading` / `!loading && connected` / `!loading && !connected`),
bound to the same-shaped `health` object — but here it is populated by
`foundationApp().fetchHealth()` calling the *Tier 0* endpoint
`/api/v1/bootstrap/health` directly (§2.4), not a Foundation-specific health check.
Foundation has no `/api/v1/foundation/health` of its own; it deliberately reuses Tier 0's.

**Tab bar (lines 65–70):**
```html
<div class="tabs tabs-boxed bg-base-100 shadow-sm mb-4 inline-flex">
    <button class="tab" :class="{ 'tab-active': activeTab === 'master' }" @click="switchTab('master')">Master Data</button>
    <button class="tab" :class="{ 'tab-active': activeTab === 'config' }" @click="switchTab('config')">System Config</button>
    <button class="tab" :class="{ 'tab-active': activeTab === 'geo' }" @click="switchTab('geo')">Geographic</button>
    <button class="tab" :class="{ 'tab-active': activeTab === 'runtime' }" @click="switchTab('runtime')">Runtime Tables</button>
</div>
```
- DaisyUI `tabs tabs-boxed` component. Each `<button>`'s `:class` object-syntax binding
  adds `tab-active` only when `activeTab` (state, default `"master"`) equals that tab's
  key. `@click="switchTab('config')"` (etc.) is the only way `activeTab` changes — see
  §2.4 for the lazy-load side effects triggered inside `switchTab()`.

**Tab panel wrapper pattern** — all four tab bodies share:
```html
<div x-show="activeTab === 'master'" x-cloak>
```
- `x-show` (not `x-if`) — all four tab `<div>`s stay mounted in the DOM at all times;
  only `display` is toggled. This is a deliberate contrast with `index.html`'s use of
  `x-if` for its mutually-exclusive states: here, once a tab's data has been fetched
  (e.g. drilled several levels into Geographic), switching away and back must not lose
  that DOM/selection state, which `x-if` (destroy-and-recreate) would do but `x-show`
  (hide-and-keep) does not.
- `x-cloak` — combined with the CSS rule in `style.css` (§2.5), this hides the panel
  markup (including raw `{{ }}`/directive text) until Alpine has finished its initial
  render pass, preventing a flash of unstyled/unbound content on first page load. It is
  used here (and not in `index.html`) because `index.html`'s equivalent branching is all
  done via `<template x-if>`, which Alpine never renders to the live DOM until the
  condition is true — so there is nothing to cloak. `foundation.html`'s tab panels are
  live, always-present DOM nodes that only start correctly hidden once Alpine attaches,
  hence the extra `x-cloak` guard.

**Tab 1 — Master Data (lines 72–191):** a 2-column grid of two cards:
```html
<div class="grid grid-cols-1 xl:grid-cols-2 gap-4 xl:gap-6">
```
- 1 column on mobile, 2 columns from `xl` up — Master Categories on the left, Master
  Data Values on the right.

**Master Categories card:**
```html
<h2 class="card-title text-sm uppercase tracking-wide text-base-content/50">Master Categories</h2>
<span class="badge badge-ghost badge-sm" x-text="categories.length + ' categories'"></span>
```
- Badge counter, same pattern as `index.html`'s cards. The body is gated by a
  loading/error/data `x-if` triad — with no explicit "empty" branch, since categories
  are seeded:
```html
<template x-if="categoriesLoading"> ... spinner ... </template>
<template x-if="!categoriesLoading && categoriesError"> ... alert ... </template>
<template x-if="!categoriesLoading && !categoriesError"> ... table ... </template>
```
- The data-table row:
```html
<template x-for="cat in categories" :key="cat.master_category_pk">
    <tr class="hover">
        <td class="font-mono text-xs whitespace-nowrap" x-text="cat.category_code"></td>
        <td class="text-xs" x-text="cat.category_name"></td>
        <td class="text-xs text-base-content/60 max-w-xs truncate" x-text="cat.description || '—'" :title="cat.description"></td>
        <td class="text-xs text-center" x-text="cat.display_order"></td>
        <td class="text-center">
            <span x-show="cat.is_active" class="text-success">&#10003;</span>
            <span x-show="!cat.is_active" class="text-error">&#10007;</span>
        </td>
    </tr>
</template>
```
- Renders `category_code`, `category_name`, a truncated `description || '—'` with
  `:title` carrying the full text for a hover tooltip, `display_order`, and the same
  `x-show` ✓/✗ active-indicator pattern seen in `index.html`.

**Master Data Values card:**
```html
<span class="badge badge-ghost badge-sm" x-text="filteredMasterData.length + ' values'"></span>
```
- Badge counter bound to a **computed getter**, `filteredMasterData.length + ' values'`
  (not the raw `masterData.length`), because this card is filterable. The filter control:
```html
<select class="select select-bordered select-sm w-full max-w-xs"
        x-model="selectedCategoryCode"
        @change="filterByCategory()">
    <option value="">All Categories</option>
    <template x-for="cat in categories" :key="cat.category_code">
        <option :value="cat.category_code" x-text="cat.category_name"></option>
    </template>
</select>
```
  - `x-model="selectedCategoryCode"` — two-way binds the `<select>`'s value to state;
    Alpine keeps them in sync in both directions.
  - `@change="filterByCategory()"` — re-fetches master data scoped to the newly chosen
    category (or all, if `"All Categories"` — empty string — is chosen); see §2.4.
  - The `<option>` list is itself an `x-for` over `categories`, so the dropdown's
    choices are populated from the same API data as the left card, never hardcoded.
- The data-table row:
```html
<template x-for="md in filteredMasterData" :key="md.master_data_pk">
    <tr class="hover">
        <td><span class="badge badge-outline badge-xs" x-text="md.category_code"></span></td>
        <td class="font-mono text-xs whitespace-nowrap" x-text="md.value_code"></td>
        <td class="text-xs" x-text="md.value_name"></td>
        <td class="text-xs text-center" x-text="md.display_order"></td>
        <td class="text-center">
            <span x-show="md.is_active" class="text-success">&#10003;</span>
            <span x-show="!md.is_active" class="text-error">&#10007;</span>
        </td>
    </tr>
</template>
```
- Iterates `x-for="md in filteredMasterData"` — the **computed getter**, not `masterData`
  directly — showing a `category_code` badge, `value_code`, `value_name`,
  `display_order`, and the same ✓/✗ pattern.

**Tab 2 — System Config (lines 193–292):** same 2-column grid shape.

**System Settings card** — a flat table, no filter, no interactivity:
```html
<template x-for="s in settings" :key="s.system_setting_pk">
    <tr class="hover">
        <td class="font-mono text-xs whitespace-nowrap" x-text="s.setting_key"></td>
        <td class="text-xs font-semibold" x-text="s.setting_value"></td>
        <td><span class="badge badge-outline badge-xs" x-text="s.data_type"></span></td>
        <td class="text-xs text-base-content/60 max-w-xs truncate" x-text="s.description || '—'" :title="s.description"></td>
    </tr>
</template>
```
- `setting_key` (mono), `setting_value` in `font-semibold`, a `data_type` outline badge,
  and a truncated `description` with the full text in `:title`.

**ID Sequences card** — table with "Max Digits" and "Range" columns (renamed from "Padding"
and "Format Sample" in the v2.0 migration — see the note at §2.4):
```html
<td class="text-xs text-center" x-text="seq.padding_length"></td>
<td class="font-mono text-xs text-primary" x-text="formatSample(seq)"></td>
```
- The "Max Digits" column displays the raw `seq.padding_length` value directly (no helper
  call) — unchanged column content, just a clearer header than the old "Padding," since
  `padding_length` no longer implies a single fixed-width sample is the most useful preview
  (see below).
- The "Range" column calls the `formatSample(seq)` helper (§2.4) per row to synthesize a
  `min → max` preview range string from `prefix` + `padding_length` — the column deliberately
  does **not** display `current_value`, because the API response (`SequenceResponse`) never
  includes that field at all (it is infrastructure state, excluded by design at the
  Pydantic-schema layer).

**Tab 3 — Geographic (lines 294–518):** the most complex tab — an interactive
drill-down through Country → State → District → City/Village, plus a Postal Codes panel
keyed off the selected country.

Breadcrumb (rendered only once a country is selected):
```html
<template x-if="selectedCountry">
    <div class="flex items-center gap-1 text-sm mb-4">
        <span x-text="selectedCountry.country_name"></span>
        <template x-if="selectedState">
            <span><span>&#x203A;</span><span x-text="selectedState.state_name"></span></span>
        </template>
        <template x-if="selectedDistrict">
            <span><span>&#x203A;</span><span x-text="selectedDistrict.district_name"></span></span>
        </template>
    </div>
</template>
```
- Three nested `x-if` templates build a progressively longer breadcrumb
  (`India`, then `India › Odisha`, then `India › Odisha › Khordha`) as deeper
  selections are made. The separator is the literal entity `&#x203A;` (›) rather than a
  DaisyUI/CSS pseudo-element, chosen because pseudo-element separators did not render
  consistently in all configurations tested.

Four-column grid of drill-down list cards:
```html
<div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
```
- 1 column on mobile, 2 from `md`, 4 (Countries/States/Districts/Cities side by side)
  from `xl` up. Each level follows the same shape (shown here for Countries → States;
  Districts → Cities/Villages repeat it one level deeper):
```html
<template x-for="c in countries" :key="c.country_pk">
    <button class="btn btn-sm btn-block justify-start gap-2"
            :class="selectedCountry?.country_pk === c.country_pk ? 'btn-primary' : 'btn-ghost'"
            @click="selectCountry(c)">
        <span class="font-mono text-xs" x-text="c.country_code"></span>
        <span class="text-xs" x-text="c.country_name"></span>
    </button>
</template>
```
- Full-width (`btn-block`) buttons, not table rows, for the list-of-buttons drill-down
  affordance. Selected item gets `btn-primary` (Countries), `btn-secondary` (States), or
  `btn-accent` (Districts) — a different DaisyUI accent colour per depth level, purely
  visual, so the currently active path through the hierarchy is scannable at a glance.
- The States/Districts/Cities cards additionally gate on the parent selection:
```html
<template x-if="!selectedCountry">
    <p ...>Select a country to view states.</p>
</template>
<template x-if="selectedCountry && statesLoading"> ... </template>
<template x-if="selectedCountry && !statesLoading && !statesError"> ... list ... </template>
```
  and Districts/Cities add a fourth branch for the empty-but-loaded case:
```html
<template x-if="selectedState && !districtsLoading && !districtsError && districts.length === 0">
    <p ...>No districts seeded for this state.</p>
</template>
```
  distinguishing "nothing selected yet," "loading," "error," and "loaded but genuinely
  empty" as four separate, explicit UI states (Cities/Villages' empty state adds an
  extra explanatory line: "This is expected — city/village data is deferred reference
  data.").

Postal Codes panel (lines 468–517), rendered only when a country is selected, keyed to
`selectedCountry` rather than to any deeper selection:
```html
<h2 ...>Postal Codes — <span x-text="selectedCountry.country_name"></span></h2>
```
- The data-table row:
```html
<template x-for="pc in postalCodes" :key="pc.postal_code_pk">
    <tr class="hover">
        <td class="font-mono text-xs" x-text="pc.postal_code"></td>
        <td class="text-xs" x-text="pc.post_office_name || '—'"></td>
        <td class="text-xs" x-text="pc.state_name"></td>
        <td class="text-center">
            <span x-show="pc.is_active" class="text-success">&#10003;</span>
            <span x-show="!pc.is_active" class="text-error">&#10007;</span>
        </td>
    </tr>
</template>
```
- `postal_code`, `post_office_name || '—'`, `state_name`, and the ✓/✗ active indicator;
  own independent `postalCodesLoading` gate and an "empty for this country" message.

**Tab 4 — Runtime Tables (lines 520–585):** a single, narrower Document Master card:
```html
<section class="card bg-base-100 shadow-sm max-w-2xl">
```
- `max-w-2xl` caps the card's width — unlike the other tabs' full-width grids, this tab
  has only one card, so it is intentionally not stretched. Badge counter, and a
  loading/empty/data `x-if` triad (loading spinner; `documents.length === 0`; `documents.length > 0`) gate the body.
- The data-table row:
```html
<template x-for="doc in documents" :key="doc.document_master_pk">
    <tr class="hover">
        <td><span class="badge badge-outline badge-xs" x-text="doc.document_type_code"></span></td>
        <td class="text-xs" x-text="doc.document_name"></td>
        <td class="font-mono text-xs" x-text="doc.document_number || '—'"></td>
        <td class="text-xs" x-text="doc.mime_type || '—'"></td>
        <td class="text-xs text-center" x-text="doc.version"></td>
    </tr>
</template>
```
- `document_type_code` (badge), `document_name`, `document_number || '—'`,
  `mime_type || '—'`, `version`. Closes with a static explanatory footnote, not
data-bound:
```html
<p class="text-xs text-base-content/40">
    field_change_log exists in the database but is not exposed in Tier 1.
    Audit data requires authentication — deferred to Tier 5.
</p>
```
- This line exists purely to document, in the running UI itself, why a 12th Foundation
  table has no corresponding tab/section anywhere on the page.

**Footer and script include (lines 587–594):** identical copyright footer to
`index.html`; loads `<script src="/assets/js/foundation.js"></script>` at the bottom.

---

### 2.4 `frontend/assets/js/foundation.js`

**Requirement.** The client-side state/behaviour layer for `foundation.html`, mirroring
the role `app.js` plays for `index.html` but scaled to cover 6 API resource groups
(categories, master-data, settings, sequences, 5 geographic levels, documents) across 4
lazily-loaded tabs, plus a filter dropdown and a multi-level toggleable drill-down.
Defines one global factory function, `foundationApp()`.

**Full file, 332 lines. Walkthrough:**

```javascript
const FND_API = "/api/v1/foundation";
```
- Same relative-path pattern as `app.js`'s `API_BASE`, scoped to the Foundation router
  prefix. The Tier 0 health check is called via its own separate literal path
  (`/api/v1/bootstrap/health`) inside `fetchHealth()` rather than through this constant,
  since it belongs to a different router.

**State properties**, in the order declared, grouped by the file's own comment banners:

```javascript
activeTab: "master",
```
- Controls which of the four tab panels is visible; read by every
  `x-show="activeTab === '...'"` binding and every tab button's `:class`.

```javascript
health: { loading: true, connected: false },
```
- Identical shape to `app.js`, reused for the shared System Status card.

**Master Data group:**
```javascript
categories: [],
categoriesLoading: true,
categoriesError: false,

masterData: [],
masterDataLoading: false,
masterDataError: false,
selectedCategoryCode: "",  // filter dropdown
```
- `selectedCategoryCode` is bound via `x-model` to the filter `<select>`. Note the
  asymmetry: `categoriesLoading` starts `true` (fetched eagerly by `init()`) but
  `masterDataLoading` starts `false` — both are actually fetched together in
  `loadMasterTab()` (below), so this initial `false` is momentarily inaccurate but is
  overwritten to `true` within `fetchMasterData()` before any render depending on it
  would matter in practice.

**System Settings group:**
```javascript
settings: [],
settingsLoading: true,
settingsError: false,
```

**ID Sequences group:**
```javascript
sequences: [],
sequencesLoading: true,
sequencesError: false,
```

**Geographic group:**
```javascript
countries: [],
countriesLoading: true,
countriesError: false,

states: [],
statesLoading: false,
statesError: false,
selectedCountry: null,

districts: [],
districtsLoading: false,
districtsError: false,
selectedState: null,

cities: [],
citiesLoading: false,
citiesError: false,
selectedDistrict: null,

postalCodes: [],
postalCodesLoading: false,
postalCodesError: false,
```
- Only `countries*` starts in the "loading" state (fetched eagerly when the Geographic
  tab is first opened); every deeper level (`states`/`districts`/`cities`/`postalCodes`)
  starts `loading: false` because it is fetched only in reaction to a parent-level click.

**Runtime group:**
```javascript
documents: [],
documentsLoading: true,
documentsError: false,
```
- There is also an implicit, undeclared `_runtimeLoaded` flag — see `loadRuntimeTab()`
  below — set as a property the first time it's assigned rather than declared upfront in
  the returned object literal.

**Init:**
```javascript
async init() {
    await this.fetchHealth();
    // Load data for the default tab
    await this.loadMasterTab();
},
```
- Unlike `app.js`'s `init()` (which fires 3 fetches in `Promise.all` concurrently),
  this `init()` awaits sequentially: health check first, then the default tab's data.
  Only the default (`"master"`) tab's data is loaded eagerly — the other three tabs'
  data is deferred until first visited.

```javascript
async fetchHealth() {
    this.health.loading = true;
    try {
        const res = await fetch("/api/v1/bootstrap/health");
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        this.health.connected = data.database === "connected";
    } catch {
        this.health.connected = false;
    } finally {
        this.health.loading = false;
    }
},
```
- Byte-for-byte the same try/catch/finally shape as `app.js`'s `fetchHealth()`, against
  the Tier 0 endpoint by its literal path (not `FND_API`, since it isn't a Foundation
  route).

**Tab switching and lazy loading:**
```javascript
async switchTab(tab) {
    this.activeTab = tab;
    if (tab === "master") await this.loadMasterTab();
    else if (tab === "config") await this.loadConfigTab();
    else if (tab === "geo") await this.loadGeoTab();
    else if (tab === "runtime") await this.loadRuntimeTab();
},
```
- Bound to every tab button's `@click`. Sets `activeTab` (driving the `x-show`
  bindings) and then delegates to the tab-specific loader.

```javascript
async loadMasterTab() {
    if (this.categories.length === 0) await this.fetchCategories();
    if (this.masterData.length === 0) await this.fetchMasterData();
},

async loadConfigTab() {
    if (this.settings.length === 0) await this.fetchSettings();
    if (this.sequences.length === 0) await this.fetchSequences();
},

async loadGeoTab() {
    if (this.countries.length === 0) await this.fetchCountries();
},

async loadRuntimeTab() {
    if (!this._runtimeLoaded) {
        await this.fetchDocuments();
        this._runtimeLoaded = true;
    }
},
```
- **Lazy-load-once guards.** `loadMasterTab`/`loadConfigTab`/`loadGeoTab` all use
  `if (array.length === 0)` as the "not yet loaded" test — cheap and works because none
  of those endpoints are expected to legitimately return an empty array in a healthy
  system (categories/master-data/settings/sequences/countries are all seeded).
  `loadRuntimeTab` cannot use that same test, because `documents` is *expected* to be
  legitimately empty (no seed data, runtime-populated table) — an empty-array check
  would re-fetch on every single tab visit. Instead it introduces a one-shot boolean
  flag, `this._runtimeLoaded`, assigned dynamically (not present in the initial state
  object literal) the first time this method runs, and checked thereafter.

**Master Data fetchers:**
```javascript
async fetchCategories() {
    this.categoriesLoading = true;
    this.categoriesError = false;
    try {
        const res = await fetch(`${FND_API}/categories`);
        if (!res.ok) throw new Error(res.statusText);
        this.categories = await res.json();
    } catch {
        this.categoriesError = true;
    } finally {
        this.categoriesLoading = false;
    }
},
```
- Standard four-step pattern against `GET /api/v1/foundation/categories`.

```javascript
async fetchMasterData(categoryCode) {
    this.masterDataLoading = true;
    this.masterDataError = false;
    try {
        let url = `${FND_API}/master-data`;
        if (categoryCode) url += `?category_code=${encodeURIComponent(categoryCode)}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(res.statusText);
        this.masterData = await res.json();
    } catch {
        this.masterDataError = true;
    } finally {
        this.masterDataLoading = false;
    }
},
```
- Takes an optional `categoryCode` parameter. When falsy (undefined/null/empty string),
  the base URL with no query string is used, fetching **all** master data values across
  every category. When truthy, `encodeURIComponent(categoryCode)` URL-encodes it into a
  `?category_code=` query parameter, matching the FastAPI endpoint's optional
  `category_code` filter (`api/routers/foundation.py`).

```javascript
async filterByCategory() {
    await this.fetchMasterData(this.selectedCategoryCode || null);
},
```
- Bound to the filter `<select>`'s `@change`. Converts an empty-string selection (the
  "All Categories" option's `value=""`) to `null` before delegating to
  `fetchMasterData()`, so choosing "All Categories" re-fetches the unfiltered set rather
  than filtering on the literal empty string.

**System Config fetchers:**
```javascript
async fetchSettings() {
    this.settingsLoading = true;
    this.settingsError = false;
    try {
        const res = await fetch(`${FND_API}/settings`);
        if (!res.ok) throw new Error(res.statusText);
        this.settings = await res.json();
    } catch {
        this.settingsError = true;
    } finally {
        this.settingsLoading = false;
    }
},

async fetchSequences() {
    this.sequencesLoading = true;
    this.sequencesError = false;
    try {
        const res = await fetch(`${FND_API}/sequences`);
        if (!res.ok) throw new Error(res.statusText);
        this.sequences = await res.json();
    } catch {
        this.sequencesError = true;
    } finally {
        this.sequencesLoading = false;
    }
},
```
- `fetchSettings()` and `fetchSequences()` are both the same four-step pattern against
  `GET ${FND_API}/settings` and `GET ${FND_API}/sequences` respectively, no parameters,
  populating `this.settings` / `this.sequences`.

**Geographic fetchers and drill-down:**
```javascript
async fetchCountries() {
    this.countriesLoading = true;
    this.countriesError = false;
    try {
        const res = await fetch(`${FND_API}/countries`);
        if (!res.ok) throw new Error(res.statusText);
        this.countries = await res.json();
    } catch {
        this.countriesError = true;
    } finally {
        this.countriesLoading = false;
    }
},
```
- Standard pattern, no parameters — Countries is the top of the hierarchy.

```javascript
async selectCountry(country) {
    if (this.selectedCountry?.country_pk === country.country_pk) {
        this.selectedCountry = null;
        this.states = [];
        this.selectedState = null;
        this.districts = [];
        this.selectedDistrict = null;
        this.cities = [];
        this.postalCodes = [];
        return;
    }
    this.selectedCountry = country;
    this.selectedState = null;
    this.districts = [];
    this.selectedDistrict = null;
    this.cities = [];

    this.statesLoading = true;
    this.statesError = false;
    try {
        const res = await fetch(`${FND_API}/states?country_pk=${country.country_pk}`);
        if (!res.ok) throw new Error(res.statusText);
        this.states = await res.json();
    } catch {
        this.statesError = true;
    } finally {
        this.statesLoading = false;
    }

    // Also load postal codes for this country
    this.postalCodesLoading = true;
    this.postalCodesError = false;
    try {
        const res = await fetch(`${FND_API}/postal-codes?country_pk=${country.country_pk}`);
        if (!res.ok) throw new Error(res.statusText);
        this.postalCodes = await res.json();
    } catch {
        this.postalCodesError = true;
    } finally {
        this.postalCodesLoading = false;
    }
},
```
- **Toggle-off guard** (`?.` optional chaining, same reasoning as `app.js`'s
  `selectRole`): clicking the already-selected country deselects it and cascades a full
  clear of every downstream level (states, selectedState, districts, selectedDistrict,
  cities, postalCodes) — this is the "clear entire drill-down" branch.
- **Selecting a new country**: first clears everything below the country level (in case
  a deeper selection was active from a previous country), then issues **two sequential
  fetches**, one after the other (each fully awaited before the next starts, not run in
  parallel): `states?country_pk=...` and `postal-codes?country_pk=...`. Both use their
  own independent loading/error flag pairs, so the States card and the Postal Codes
  panel can show independent loading spinners even though they're triggered from the
  same click.

```javascript
async selectState(state) {
    if (this.selectedState?.state_pk === state.state_pk) {
        this.selectedState = null;
        this.districts = [];
        this.selectedDistrict = null;
        this.cities = [];
        return;
    }
    this.selectedState = state;
    this.selectedDistrict = null;
    this.cities = [];

    this.districtsLoading = true;
    this.districtsError = false;
    try {
        const res = await fetch(`${FND_API}/districts?state_pk=${state.state_pk}`);
        if (!res.ok) throw new Error(res.statusText);
        this.districts = await res.json();
    } catch {
        this.districtsError = true;
    } finally {
        this.districtsLoading = false;
    }
},
```
- Same toggle-off-and-cascade-clear / select-and-fetch-children shape one level down:
  toggling off clears districts/selectedDistrict/cities; selecting fetches
  `districts?state_pk=...`. Notably, `selectState` does **not** re-fetch postal codes —
  the Postal Codes panel stays scoped to the country level throughout the whole
  drill-down (confirmed by `foundation.html`'s panel header,
  `Postal Codes — {{selectedCountry.country_name}}`, and by the DDL/API design in which
  `PostalCodeResponse` carries state context but the UI only ever filters by country).

```javascript
async selectDistrict(district) {
    if (this.selectedDistrict?.district_pk === district.district_pk) {
        this.selectedDistrict = null;
        this.cities = [];
        return;
    }
    this.selectedDistrict = district;

    this.citiesLoading = true;
    this.citiesError = false;
    try {
        const res = await fetch(`${FND_API}/cities?district_pk=${district.district_pk}`);
        if (!res.ok) throw new Error(res.statusText);
        this.cities = await res.json();
    } catch {
        this.citiesError = true;
    } finally {
        this.citiesLoading = false;
    }
},
```
- Bottom of the drill-down chain: toggle-off clears only `cities` (nothing deeper
  exists); selecting fetches `cities?district_pk=...`. In practice this always resolves
  to `[]` at Tier 1 (no city/village seed data), which `foundation.html`'s
  `districts.length === 0` / empty-state branches account for.

**Runtime fetcher:**
```javascript
async fetchDocuments() {
    this.documentsLoading = true;
    this.documentsError = false;
    try {
        const res = await fetch(`${FND_API}/documents`);
        if (!res.ok) throw new Error(res.statusText);
        this.documents = await res.json();
    } catch {
        this.documentsError = true;
    } finally {
        this.documentsLoading = false;
    }
},
```
- Standard pattern, no parameters, against `GET ${FND_API}/documents`; called exactly
  once per page load by `loadRuntimeTab()`'s `_runtimeLoaded` guard.

**Helpers:**
```javascript
get filteredMasterData() {
    if (!this.selectedCategoryCode) return this.masterData;
    return this.masterData.filter(
        d => d.category_code === this.selectedCategoryCode
    );
},
```
- An Alpine/JS **computed getter** (accessed as a property, `filteredMasterData`, not
  called as a function) — recomputed reactively whenever `masterData` or
  `selectedCategoryCode` changes. When no category filter is set, returns the raw
  `masterData` array unmodified; otherwise returns only rows whose `category_code`
  matches. In practice this client-side filter is redundant with the server-side
  `?category_code=` filter already applied by `fetchMasterData()`/`filterByCategory()`,
  but it also protects the badge counter (`filteredMasterData.length`) and table body
  from ever transiently showing unfiltered data while a filtered fetch is in flight.

> **v2.0 (2026-09-12):** `formatSample(seq)` changed from returning a single zero-padded
> sample to a `min → max` range string, because `id_sequence_master`'s padding-length CHECK
> was loosened to allow `padding_length = 3` (see `DATABASE_CODE_EXPLANATIONS.md`'s
> `04_id_sequence_master.sql` section) — a single fixed-width sample like `PS001` is far less
> informative for a narrow-range sequence than seeing the full `PS1 → PS999` span. The ID
> Sequences table's "Padding"/"Format Sample" column headers became "Max Digits"/"Range" to
> match (see §2.3).

```javascript
formatSample(seq) {
    const max = "9".repeat(seq.padding_length);
    return `${seq.prefix}1 → ${seq.prefix}${max}`;
},
```
- Plain (non-getter, non-async) helper method, called per-row from the ID Sequences
  table's "Range" column (`x-text="formatSample(seq)"`). Builds a `min → max` range string by
  repeating the literal character `"9"` `seq.padding_length` times to get the widest possible
  value for that padding, then formatting `${prefix}1 → ${prefix}${max}`. For example,
  `prefix: "SS"`, `padding_length: 8` → `"9".repeat(8)` → `"99999999"` →
  `"SS1 → SS99999999"`. Unlike the pre-migration version (which zero-padded a single sample
  value, e.g. `"SS00000001"`), this shows the full range a sequence can produce — more
  informative now that `padding_length` varies more widely across sequences (3 for
  `PARIBARIK_SANGHA` up to 10 for `PERSON`). It deliberately uses the
  constant `"9"` (for the max) and `"1"` (for the min), never `seq.current_value` — the API's
  `SequenceResponse` never includes `current_value` in the first place (excluded at the schema
  layer as infrastructure state), so this helper has no such field available even if it wanted
  to use it; it exists purely to preview the *format*, not to predict or display the
  next real ID that will be issued.

---

### 2.5 `frontend/assets/css/style.css`

**Requirement.** Tailwind and DaisyUI (both CDN-delivered) supply essentially all visual
styling via utility classes and components; this file exists only to hold the one rule
that **cannot** be expressed as a Tailwind utility class because it targets a
framework-specific attribute (`x-cloak`) that Tailwind doesn't know about. It is the
smallest file in the frontend layer, shared unmodified by both `index.html` and
`foundation.html`.

**Full file, 10 lines:**
```css
/*
 * NSS ERP — Tier 0 minimal custom styles.
 * Tailwind/DaisyUI handle the heavy lifting via CDN.
 * This file is for project-specific overrides only.
 */

/* Keep the body from showing unstyled content before Alpine initialises */
[x-cloak] {
    display: none !important;
}
```
- The header comment states the file's scope and intent directly.
- **The one rule** — an attribute selector, `[x-cloak]`, matching any element carrying
  the `x-cloak` attribute (used in `foundation.html`'s four tab panels; see §2.3) — sets
  `display: none !important;`.
- **Why this is needed at all:** Alpine.js only removes the `x-cloak` attribute from an
  element *after* it has finished evaluating that element's directives on initial page
  load. Until that removal happens, the browser would otherwise render the element in
  its default (visible) state — which, for an element whose visibility is meant to be
  controlled by `x-show="activeTab === '...'"`, would mean every tab panel flashing
  visible simultaneously for one rendering frame before Alpine hides the non-active
  three. This CSS rule pre-emptively hides any `[x-cloak]` element via a plain
  browser-native CSS selector (no JavaScript required, so it applies even before
  Alpine's script has finished downloading/parsing/executing), and Alpine's own runtime
  then strips the `x-cloak` attribute once it has taken over, letting the rule stop
  applying and `x-show`'s own inline-style toggling take over cleanly.
- `!important` ensures this rule outranks any Tailwind utility class (e.g. a stray
  `block` or `grid` class) that might otherwise force the element visible before Alpine
  attaches.
- `index.html` loads this same stylesheet but has no `x-cloak` attributes anywhere in
  its markup (its conditional sections all use `<template x-if>`, which Alpine never
  inserts into the live DOM until true, so there is nothing to flash) — the rule is
  simply inert, harmless dead weight on that page.

---

## 3. Cross-references

- `frontend/README.md` — primary human-facing reference for this folder: directory
  structure, per-file summary tables (state properties, methods, API endpoints
  consumed), the FastAPI static-serving/routing setup (`api/main.py`), and the
  Tier-by-tier growth plan. Read that first for the "what" and "where"; this document
  supplies the "how, exactly" for each file's actual code.
- `docs/03_Solution/api/FOUNDATION_API_CONTRACT.md` — the authoritative API
  contract for the 17 `/api/v1/foundation/*` endpoints consumed by `foundation.html` /
  `foundation.js` (request/response shapes, filter query parameters, the deliberate
  exclusion of `current_value` and `field_change_log`).
- `docs/03_Solution/api/ORGANIZATION_API_CONTRACT.md` — the authoritative API
  contract for the 6 `/api/v1/organization/*` endpoints consumed by `organization.html` /
  `organization.js`.
