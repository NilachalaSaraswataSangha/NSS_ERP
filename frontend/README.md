# frontend/

Tier 0 Bootstrap Verification UI for Nilachala Saraswata Sangha.

**Purpose:** Verify the Tier 0 database → API → frontend integration.
This is not an operational administration dashboard. It establishes the
initial frontend shell that later tiers grow into.

**Tech stack:** Tailwind CSS + DaisyUI (CDN), Alpine.js (CDN), vanilla
`fetch()` for JSON API consumption. No React/Vue/Angular. No Node.js
build step. No Django templates.

**Served by:** FastAPI mounts this directory as static files. No
separate frontend server, no CORS configuration needed.

---

## Directory Structure

```
frontend/
├── index.html              Main HTML page (Alpine.js application)
├── assets/
│   ├── css/
│   │   └── style.css       Minimal project-specific CSS overrides
│   ├── img/
│   │   └── nss-logo.png    NSS logo (PNG with transparency)
│   └── js/
│       └── app.js          Alpine.js data component + API fetch logic
└── README.md               This file
```

---

## File Reference

### index.html

The single-page application entry point. Contains four UI sections,
each rendered by Alpine.js directives bound to the `bootstrapApp()`
data component defined in `app.js`.

| Section | HTML Comment | API Endpoint Consumed | What It Shows |
|---------|-------------|----------------------|---------------|
| **Header** | `<!-- Header -->` | — | NSS logo, "Nilachala Saraswata Sangha", "Tier 0 — Bootstrap Verification" |
| **System Status** | `<!-- System Status -->` | `GET /api/v1/bootstrap/health` | Three-state indicator: "Checking..." (spinner), "Database Connected" (green badge), or "Database Unavailable" (red badge). Never exposes raw database errors. |
| **RBAC Roles** | `<!-- RBAC Roles -->` | `GET /api/v1/bootstrap/roles` | Table of all active roles (code, name, class, scope, active status) with a counter badge. Rows are clickable — selecting a role triggers the Role Permissions section. SYSTEM-class roles show a primary badge; ORGANIZATIONAL-class roles show a secondary badge. |
| **Permissions** | `<!-- Permissions -->` | `GET /api/v1/bootstrap/permissions` | Table of all active permissions with a counter badge. In Tier 0 this is intentionally empty — the UI displays an explanatory message: "No permissions configured yet. Permission catalogue is populated progressively as functional modules are implemented." |
| **Role Permissions** | `<!-- Role Permissions (interactive) -->` | `GET /api/v1/bootstrap/roles/{role_pk}/permissions` | Displays permissions assigned to the selected role. Before any role is selected: "Select a role from the table above to view its permissions." After selection: shows role code, class, scope, and a permissions table (empty in Tier 0 — "No permissions assigned."). Clicking the same role again deselects it (toggle). |
| **Footer** | `<!-- Footer -->` | — | Copyright notice: "© 2026 Nilachala Saraswata Sangha. All rights reserved." |

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

Defined in `api/main.py`. Two mechanisms, registered only if the
`frontend/` directory exists on disk:

| URL Pattern | FastAPI Handler | Serves |
|-------------|----------------|--------|
| `GET /` | Explicit route → `FileResponse(frontend/index.html)` | The main HTML page |
| `GET /assets/*` | `StaticFiles` mount → `frontend/assets/` | CSS, JS, images |

**Why not mount at `/`?** A root-level `StaticFiles` mount would shadow
FastAPI's built-in `/docs` (Swagger UI) and `/openapi.json`. By mounting
only `/assets/*` and serving `index.html` via an explicit route, all
FastAPI built-in routes remain accessible.

**Graceful degradation:** If `frontend/` does not exist on disk, the
mount and route are skipped entirely. The API continues to work in
API-only mode — `/docs` and `/api/v1/*` are unaffected.

---

## API Endpoints Consumed

All endpoints are read-only. No authentication. No CRUD.

| Method | URL | Response | Tier 0 State |
|--------|-----|----------|-------------|
| GET | `/api/v1/bootstrap/health` | `{ status, database }` | `{ "status": "ok", "database": "connected" }` |
| GET | `/api/v1/bootstrap/roles` | `RoleResponse[]` | 8 frozen roles |
| GET | `/api/v1/bootstrap/permissions` | `PermissionResponse[]` | Empty array (by design) |
| GET | `/api/v1/bootstrap/roles/{role_pk}/permissions` | `PermissionResponse[]` | Empty array (no mappings); 404 if role not found |

Response schemas are defined in `api/schemas/bootstrap.py`. Audit
columns (`created_at`, `*_by_sangha_sevi_pk`) are excluded from API
responses by design.

---

## Future Growth

This shell is designed to evolve:

```
Tier 0   Bootstrap Verification (current)
Tier 1   Person / Organization views
Tier 2   Heritage views
  ...
Tier 5   Authentication + login/session UI
  ...
         Full ERP interface
```

The page structure, CSS framework, and Alpine.js pattern established
here carry forward. Authentication UI is deferred to Tier 5 — Tier 0
intentionally has no login, no session, no fake credentials.
