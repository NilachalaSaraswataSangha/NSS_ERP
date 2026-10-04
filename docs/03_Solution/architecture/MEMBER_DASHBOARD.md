# Member Dashboard — Architecture and Data Flow

**Document ID:** ARCH-DASHBOARD-001
**Version:** 0.18.2
**Status:** LIVING DOCUMENT
**Last Updated:** 2026-09-30 (token storage, admin-tab org stats, add/remove-member authorization and endpoint-gating notes refreshed against the Tier 5 code; earlier 2026-09-21: corrected Sakha Affiliations/Journey/Selected-person-detail endpoint
paths in §3.2/§3.3 to match `frontend/assets/js/dashboard.js`)

---

## 1. Overview

The Member Dashboard is the primary post-login destination for all NSS ERP users. It presents a unified, role-aware interface where every piece of data is fetched dynamically from REST APIs — no hardcoded or mock data.

**Files:**
- `frontend/dashboard.html` — Alpine.js template + embedded CSS
- `frontend/assets/js/dashboard.js` — Alpine component logic, API calls, tree renderer

**Tech Stack:** Alpine.js (reactive state), Tailwind CSS + DaisyUI (styling), `NSSAuth.apiFetch()` (authenticated requests)

---

## 2. Authentication and Initialization

| Step | Action | API |
|------|--------|-----|
| 1 | User logs in with Sangha Sevi ID or Person ID | `POST /api/v1/auth/login` |
| 2 | Access/refresh JWTs stored in `localStorage` via `NSSAuth` (`auth.js`) | — |
| 3 | Dashboard loads; `init()` reads JWT, extracts `person_pk`, `roles`, `scopes` | — |
| 4 | Parallel API calls fetch all tab data | See Section 3 |

**Login ID:** Case-insensitive. Accepts Sangha Sevi ID (e.g., SS1, ss1) or Person ID (e.g., P1, p1). The auth router tries `UPPER(sangha_sevi_id)` first, then falls back to `UPPER(person_id)`.

---

## 3. Tab Data Sources

All data is fetched dynamically on dashboard initialization. No tab contains hardcoded values.

### 3.1 Personal Tab

| Data | API Endpoint | Notes |
|------|-------------|-------|
| Person details (name, DOB, gender, mobile, email, blood group, marital status, Aadhaar) | `GET /api/v1/person/persons/{person_pk}` | Core person record |
| Addresses (permanent, present, native) | `GET /api/v1/person/persons/{person_pk}/addresses` | All address types |

### 3.2 Membership Tab

| Data | API Endpoint | Notes |
|------|-------------|-------|
| Membership snapshot (Sevi ID, type, status, Sakha, Parichaya Patra, Anumati Patra) | `GET /api/v1/family/person/{person_pk}/membership-summary` | Single consolidated endpoint |
| Sakha Affiliations | `GET /api/v1/membership/members/{sangha_sevi_pk}/affiliations` | Keyed by `sangha_sevi_pk` (resolved from the membership-summary call above), not `person_pk` — history of Sakha associations |
| Journey Timeline | `GET /api/v1/membership/members/{sangha_sevi_pk}/journey` | Keyed by `sangha_sevi_pk` — ordered lifecycle events |

### 3.3 Family Tab

| Data | API Endpoint | Notes |
|------|-------------|-------|
| Family info, members, head history | `GET /api/v1/family/person/{person_pk}/families` | Returns family group, all members with relationship types, head history |
| Family tree graph | `GET /api/v1/family/families/{family_group_pk}/graph?viewer_person_pk={person_pk}` | BFS-computed dynamic relationship labels from viewer's perspective |
| Selected person detail | `GET /api/v1/person/persons/{person_pk}` | On-demand when a tree node or member row is clicked |
| Selected person membership | `GET /api/v1/family/person/{person_pk}/membership-summary` | On-demand, parallel with person detail |

**Tree Visualization:** Recursive renderer (`renderTree()` → `_renderSubtree()` → `_renderCouple()` → `_renderPerson()`) generates HTML via Alpine's `x-html` directive. No external charting library. `_buildCoupleTree(allPersons)` (tree construction) and a shared `_renderGenSubtree(nodes, isRoot, renderCouple, recurse)` (rendering skeleton, committed, not yet merged) are now reused by both this Family tab and the Family-of-Origin org browser in the Admin tabs below — previously each independently implemented the whole algorithm.

**Viewer Perspective:** Always the logged-in user. No "View As" selector — the graph API is called with the user's own `person_pk` as `viewer_person_pk`.

**Members Sort Order:**
1. Grandparents (Grandfather, Grandmother)
2. Parents (Father, Mother)
3. You (viewer)
4. Spouse (Wife, Husband)
5. Siblings and in-laws (Brother, Sister, Brother-in-Law, Sister-in-Law)
6. Children (Son, Daughter)
7. Grandchildren (Grandson, Granddaughter)
8. Others

Sort is driven by the `relationship_label` from the graph API, matched against a display-order priority map in `sortedFamilyMembers()`.

### 3.4 Documents Tab

| Data | Source | Notes |
|------|--------|-------|
| Parichaya Patra (Kendra #, status, validity) | Membership summary (already fetched) | No additional API call |
| Anumati Patra (document #, status, validity) | Membership summary (already fetched) | Shown only when `NSS.showAnumatiPatra(membership_type_code)` returns true (hidden for ASSOCIATE type) |

### 3.5 Admin Tabs (Role-Based)

| Data | Source | Notes |
|------|--------|-------|
| Which tabs appear | `user.roles` from JWT token | RBAC-driven; e.g., NSS_ERP_ADMIN sees System Admin, NSS_ERP_KENDRA_ADMIN sees Kendra Management |
| Org-level stats (Active Members, Families, Sakha counts, renewals due) | `GET /api/v1/organization/organizations/{pk}/stats` and `GET /api/v1/membership/organizations/{pk}/darshak-summary` | Rendered by the shared `assets/js/org-dashboard.js` (`orgDashboardTab()`), embedded as the "Org Dashboard" tab of both this page and `admin.html` (committed, not yet merged); every number is real, while attendance % and renewal-tracking widgets from the mockups show honest "not tracked yet" placeholders |

**Admin tab types:** System Admin, Kendra Management, Anchalika Management, Zilla Management, Sakha Management, Patha Chakra Management, Audit and Compliance, Reports.

---

## 4. UI Architecture

### 4.1 Layout

- **Left sidebar:** Navigation links for all tabs (Personal, Membership, Family, Documents, Attendance, Governance, + dynamic admin tabs)
- **Content area:** Active tab content, full width
- **Responsive:** Sidebar collapses to hamburger menu on mobile
- **Family tab:** Two-column grid — tree canvas (left, flexible width) + detail panel (right, 360px fixed). Collapses to single column below 1024px.

### 4.2 Tab Persistence

Active tab is stored in `sessionStorage` under key `nss_dashboard_tab`. On page refresh, the dashboard restores the last active tab instead of defaulting to Personal.

### 4.3 Styling

- **Badge system:** All badges use `NSS.*BadgeClass()` helpers from `nss-config.js` + `badges.css`. No inline badge colors.
- **Data identity classes:** `data-sevi-id`, `data-erp-no`, `data-kendra-no`, `data-family-id`, `data-sakha-name` for consistent formatting.
- **Family tree CSS:** Sky-blue connectors (`#0ea5e9`), dashed couple borders, amber viewer avatar, indigo selected ring (`#4f46e5`), generation dividers, avatar gradients per relationship type.

### 4.4 Cache Busting

**Automatic, committed, not yet merged — no longer a hand-maintained `?v=X.X.X` string.**
`api/main.py`'s `_serve_page()`/`_render_html_with_asset_versions()` rewrites every
`/assets/js/*.js`/`/assets/css/*.css` reference in the served `dashboard.html` to `?v=<10-char
sha256 prefix of that file's current contents>` at request time (memoized by file mtime); the
old manual `?v=` query string was removed from `dashboard.html`'s `<script>` tag entirely. The
`.version-badge` element in the bottom-right corner (`v0.21.0` in the current markup) is a
separate, unrelated concept — a hardcoded app-release label, not a cache-busting mechanism, and
is not updated by the new hashing.

---

## 5. API Authentication

All API calls use `NSSAuth.apiFetch(url)` which:
1. Reads the access JWT from `localStorage`
2. Attaches `Authorization: Bearer <token>` header
3. On 401, tries one refresh-token cycle (`POST /api/v1/auth/refresh`); if that fails, redirects to the login page

**Endpoint gating (Tier 5 branch, committed, not yet merged):** the dashboard's own reads are
authorized by *ownership* rather than a blanket permission — `/person/persons/{pk}` and
`/addresses` (self or `PERSON_VIEW`), `/membership/members/{pk}` and its four sub-resources
(self or `MEMBERSHIP_VIEW`), and `/family/person/{pk}/families|membership-summary` plus
`/family/families/{pk}/*` (self / current relative / family member, with `FAMILY_VIEW` as the
admin override). Member search (`/membership/search`) requires `MEMBERSHIP_VIEW`.

---

## 6. Family Member Management (Add / Remove)

### 6.1 Add Member

The family head, a family admin, or a holder of `FAMILY_MANAGE` can add a new person to the family.

| Step | UI Action | API |
|------|-----------|-----|
| 1 | Click "Add" button in Members panel | — |
| 2 | Type search query (min 2 chars) | `GET /api/v1/membership/search?q={query}` |
| 3 | Select person from results | — |
| 4 | Choose relationship type (RELATIONSHIP_TYPE master_data) | — |
| 5 | Optionally set tree link (PARENT_OF or SPOUSE_OF + target member) | — |
| 6 | Confirm | `POST /api/v1/family/families/{pk}/members` |

**Search fields:** Person ID, Sangha Sevi ID, Local Sakha ERP ID, name (trigram), mobile, email, Kendra Number (Parichaya Patra document_number).

**Authorization:** Requester must be the current head or a current family admin (or hold `FAMILY_MANAGE`); merely being a family member is not enough (403). JWT required.

**Validation:**
- Target person must exist and be active
- Target must not already be a current family member (409 Conflict)
- Relationship type code must be a valid RELATIONSHIP_TYPE value_code

### 6.2 Remove Member

Only the current family head, a family admin, or a holder of `FAMILY_MANAGE` can remove members (FAM-048).

| Step | UI Action | API |
|------|-----------|-----|
| 1 | Click ✕ on a member row (visible only to head) | — |
| 2 | Confirm removal via browser dialog | — |
| 3 | Execute | `DELETE /api/v1/family/families/{pk}/members` |

**Authorization:** same rule as Add Member (`_require_family_manage` — head via `family_head_history` where `effective_to IS NULL`, or a `family_admin` row, or `FAMILY_MANAGE`).

**Constraints:**
- The requester cannot remove themselves (400 "You cannot remove yourself from the family")
- Soft-delete only: sets `is_current=FALSE`, `effective_to=today` on `family_relationship` and all associated `family_link` rows

---

## 7. Pending / Placeholder

| Feature | Status | Dependency |
|---------|--------|------------|
| Attendance % and renewal-tracking widgets on the Org Dashboard | Placeholder ("not tracked yet") | No attendance/renewal-tracking tables exist yet |
| Attendance tab | Placeholder content | Attendance module not built |
| Governance tab | Placeholder content | Governance module not built |

---

END OF DOCUMENT
