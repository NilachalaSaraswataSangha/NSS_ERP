# Organization API Contract — Tier 2 Read-Only

| Field       | Value                                          |
|-------------|------------------------------------------------|
| Document    | ORGANIZATION_API_CONTRACT                      |
| Version     | 1.0                                            |
| Tier        | 2 — Organization                               |
| Authority   | SOL-ARCH-010, SOL-ORG-005 SS19-SS52            |
| Status      | DRAFT                                          |

---

## 1. Purpose

This document defines the API contract for the Tier 2 Organization read-only API.
All endpoints are GET-only. No authentication. `nss_db_backend` connects with
SELECT-only privileges.

The Organization API exposes the institutional hierarchy of Nilachala Saraswata
Sangha — from the apex Kendra through Anchalika/Zilla, Sakha, and Patha Chakra
levels — along with reference data (organization types, lifecycle statuses) and
a recursive hierarchy endpoint for tree navigation.

Write operations (POST/PATCH/DELETE) are deferred to Tier 5 when authenticated
administration and authorization exist.

---

## 2. Conventions

### From Tier 0 (Carried Forward)

- **Prefix:** `/api/v1/organization`
- **Tag:** `organization`
- **Router:** `api/routers/organization.py`
- **Schemas:** `api/schemas/organization.py`
- **DB access:** `conn = Depends(get_connection)` with raw psycopg2
- **Response models:** Pydantic v2 `BaseModel` — no `ConfigDict(from_attributes=True)`
  (raw psycopg2 returns dictionaries, not ORM objects)
- **Audit columns excluded:** `created_at`, `updated_at`, `deleted_at` are never
  returned in API responses
- **Active-only by default:** All list endpoints filter `WHERE is_active = TRUE`
- **UUID path parameters:** Validated by FastAPI/Pydantic (422 on malformed UUID)
- **404 on missing:** `HTTPException(status_code=404)` when a PK lookup yields no row

### New for Tier 2

- **Shared SQL fragment:** `_ORG_SELECT` centralises the 34-column SELECT with
  8 JOINs (2 INNER + 6 LEFT) to avoid duplication across 3 endpoints
- **Combinable filters:** `type_code` and `status_code` query parameters are
  independently combinable (`if`/`if`, not `if`/`elif`)
- **Parent existence guard:** The children endpoint verifies the parent exists
  before querying, preventing `200 []` for non-existent parents
- **Recursive CTE:** The hierarchy endpoint uses a leaner 10-column query
  (no address, contact, geographic fields) for tree structure only
- **Two-field pattern for NSS-level vs org-specific:** `website_url`,
  `youtube_channel_url`, and `email` are NOT NULL DEFAULT (NSS-level,
  always present); `org_website_url`, `org_youtube_channel_url`, and
  `org_email` are nullable (org-specific)

### Endpoint Classification

| Class                          | Endpoints                                       | Consumer               |
|--------------------------------|-------------------------------------------------|------------------------|
| Reference data                 | types, statuses                                 | Dropdowns / filters    |
| Core organization data         | organizations (list, detail, children)           | Application / frontend |
| Navigation / tree              | hierarchy                                        | Tree view UI           |

---

## 3. Endpoint Catalogue

### 3.1 Reference Data

#### 3.1.1 List Organization Types

```
GET /api/v1/organization/types
```

Returns all active organization types from `nss.organization_type_master`.

**Query Parameters:** None

**Response:** `200 OK`

```json
[
  {
    "organization_type_pk": "uuid",
    "organization_type_code": "KENDRA",
    "organization_type_name": "Kendra Sangha",
    "description": "...",
    "sort_order": 1,
    "is_active": true
  }
]
```

**Tier 2 state:** 8 frozen types matching the NSS Bye-Law hierarchy
(Kendra, Nilachala Kutira, Smruti Mandira, Anchalika, Zilla, Sakha,
Patha Chakra, Mahila Sangha).

**SQL Pattern:**

```sql
SELECT organization_type_pk, organization_type_code,
       organization_type_name, description,
       sort_order, is_active
FROM   nss.organization_type_master
WHERE  is_active = TRUE
ORDER BY sort_order
```

---

#### 3.1.2 List Organization Statuses

```
GET /api/v1/organization/statuses
```

Returns all active organization lifecycle statuses from
`nss.organization_status_master`.

**Query Parameters:** None

**Response:** `200 OK`

```json
[
  {
    "organization_status_pk": "uuid",
    "organization_status_code": "ACTIVE",
    "organization_status_name": "Active",
    "description": "...",
    "sort_order": 1,
    "is_active": true
  }
]
```

**Tier 2 state:** 6 statuses (Active, Proposed, Suspended, Dissolved,
Merged, Under Review).

**SQL Pattern:**

```sql
SELECT organization_status_pk, organization_status_code,
       organization_status_name, description,
       sort_order, is_active
FROM   nss.organization_status_master
WHERE  is_active = TRUE
ORDER BY sort_order
```

---

### 3.2 Core Organization Data

All three endpoints below use the shared `_ORG_SELECT` SQL fragment (36 columns,
8 JOINs) to ensure consistent column ordering and avoid duplication.

#### 3.2.1 List Organizations

```
GET /api/v1/organization/organizations
```

Returns all active organizations with resolved type, status, parent, contact,
online presence, and geographic context.

**Query Parameters:**

| Param         | Type   | Required | Description                          |
|---------------|--------|----------|--------------------------------------|
| `type_code`   | string | No       | Filter by organization type code     |
| `status_code` | string | No       | Filter by organization status code   |

Both filters are independently combinable. A non-matching filter returns `[]`,
not an error.

**Response:** `200 OK`

```json
[
  {
    "organization_pk": "uuid",
    "organization_id": null,
    "organization_name": "Nilachala Saraswata Sangha",
    "organization_code": "KEN",

    "organization_type_pk": "uuid",
    "organization_type_code": "KENDRA",
    "organization_type_name": "Kendra Sangha",

    "organization_status_pk": "uuid",
    "organization_status_code": "ACTIVE",
    "organization_status_name": "Active",

    "parent_organization_pk": null,
    "parent_organization_name": null,

    "address_line_1": "Satsikshya Mandir, A/4, Unit-9",
    "address_line_2": "Bhubaneswar",

    "phone_number": "+91-674-2390055",
    "mobile_number": "+91-9238106823",
    "email": "info@nsspuri.org",
    "org_email": null,

    "website_url": "https://www.nsspuri.org",
    "org_website_url": null,
    "youtube_channel_url": "https://www.youtube.com/@NilachalaSaraswataSangha",
    "org_youtube_channel_url": null,

    "district_pk": null,
    "district_name": null,
    "state_pk": null,
    "state_name": null,
    "country_pk": "uuid",
    "country_name": "India",
    "city_village_pk": null,
    "city_village_name": null,
    "postal_code_pk": "uuid",
    "postal_code": "751022",

    "latitude": null,
    "longitude": null,

    "is_active": true
  }
]
```

**Tier 2 state:** 3 seeded organizations (Kendra, Nilachala Kutira,
Smruti Mandira) — all roots, no children.

**SQL Pattern (shared `_ORG_SELECT`):**

```sql
SELECT o.organization_pk,
       o.organization_id,
       o.organization_name,
       o.organization_code,
       ot.organization_type_pk,
       ot.organization_type_code,
       ot.organization_type_name,
       os.organization_status_pk,
       os.organization_status_code,
       os.organization_status_name,
       o.parent_organization_pk,
       p.organization_name AS parent_organization_name,
       o.address_line_1,
       o.address_line_2,
       o.phone_number,
       o.mobile_number,
       o.email,
       o.org_email,
       o.website_url,
       o.org_website_url,
       o.youtube_channel_url,
       o.org_youtube_channel_url,
       o.district_pk,
       d.district_name,
       o.state_pk,
       s.state_name,
       o.country_pk,
       c.country_name,
       o.city_village_pk,
       cv.city_village_name,
       o.postal_code_pk,
       pc.postal_code,
       o.latitude,
       o.longitude,
       o.is_active
FROM   nss.organization o
JOIN   nss.organization_type_master ot
       ON ot.organization_type_pk = o.organization_type_pk
JOIN   nss.organization_status_master os
       ON os.organization_status_pk = o.organization_status_pk
LEFT JOIN nss.organization p
       ON p.organization_pk = o.parent_organization_pk
LEFT JOIN nss.district d
       ON d.district_pk = o.district_pk
LEFT JOIN nss.state s
       ON s.state_pk = o.state_pk
LEFT JOIN nss.country c
       ON c.country_pk = o.country_pk
LEFT JOIN nss.city_village cv
       ON cv.city_village_pk = o.city_village_pk
LEFT JOIN nss.postal_code pc
       ON pc.postal_code_pk = o.postal_code_pk
WHERE  o.is_active = TRUE
ORDER BY ot.sort_order, o.organization_name
```

When `type_code` is provided, add: `AND ot.organization_type_code = %s`
When `status_code` is provided, add: `AND os.organization_status_code = %s`

---

#### 3.2.2 Get Organization by PK

```
GET /api/v1/organization/organizations/{organization_pk}
```

Returns a single organization with full resolved context. 404 if not found
or inactive.

**Path Parameters:**

| Param              | Type | Required | Description              |
|--------------------|------|----------|--------------------------|
| `organization_pk`  | UUID | Yes      | Organization primary key |

**Response:** `200 OK` — single `OrganizationResponse`

**Error Responses:**

| Status | When                                |
|--------|-------------------------------------|
| 404    | PK not found or inactive            |
| 422    | Malformed UUID                      |

**SQL Pattern:** `_ORG_SELECT` + `WHERE o.organization_pk = %s AND o.is_active = TRUE`

---

#### 3.2.3 List Organization Children

```
GET /api/v1/organization/organizations/{organization_pk}/children
```

Returns direct children of a given organization. 404 if the parent
does not exist.

**Path Parameters:**

| Param              | Type | Required | Description                    |
|--------------------|------|----------|--------------------------------|
| `organization_pk`  | UUID | Yes      | Parent organization primary key |

**Response:** `200 OK` — list of `OrganizationResponse`

**Error Responses:**

| Status | When                                     |
|--------|------------------------------------------|
| 404    | Parent `organization_pk` not found       |
| 422    | Malformed UUID                           |

**Design note:** The two-step pattern (existence check + children query)
prevents a non-existent parent from silently returning `200 []`, which
would be indistinguishable from "parent exists but has no children."

**Tier 2 state:** All 3 seeded organizations are roots — this endpoint
returns `[]` for all valid parents. Children will appear when Anchalika,
Zilla, Sakha, and Patha Chakra organizations are created.

**SQL Pattern:**

```sql
-- Step 1: Verify parent exists
SELECT 1 FROM nss.organization
WHERE  organization_pk = %s AND is_active = TRUE

-- Step 2: Fetch children
_ORG_SELECT
WHERE  o.parent_organization_pk = %s AND o.is_active = TRUE
ORDER BY ot.sort_order, o.organization_name
```

---

### 3.3 Navigation

#### 3.3.1 Organization Hierarchy

```
GET /api/v1/organization/hierarchy
```

Returns the full organizational hierarchy as a flat list with depth.
Uses a recursive CTE starting from root nodes (`parent = NULL`).

**Query Parameters:** None

**Response:** `200 OK`

```json
[
  {
    "organization_pk": "uuid",
    "organization_name": "Nilachala Saraswata Sangha",
    "organization_code": "KEN",
    "organization_type_code": "KENDRA",
    "organization_type_name": "Kendra Sangha",
    "organization_status_code": "ACTIVE",
    "organization_status_name": "Active",
    "parent_organization_pk": null,
    "depth": 0,
    "is_active": true
  }
]
```

**Design note:** Uses a leaner 10-column query (vs 36 in `_ORG_SELECT`) —
no address, contact, online-presence, or geographic fields. The hierarchy
view shows only organizational structure (name, type, status, depth).
The UI reconstructs the tree using `depth` for indentation; the response
is deliberately flat, not nested JSON.

**Tier 2 state:** 3 root nodes at depth 0. When child organizations are
created, deeper levels will appear (Kendra → Anchalika → Sakha → Patha Chakra
= depth 0 → 1 → 2 → 3).

**SQL Pattern:**

```sql
WITH RECURSIVE org_tree AS (
    -- Anchor: root nodes (no parent)
    SELECT o.organization_pk, o.organization_name,
           o.organization_code,
           ot.organization_type_code, ot.organization_type_name,
           os.organization_status_code, os.organization_status_name,
           o.parent_organization_pk,
           0 AS depth, o.is_active
    FROM   nss.organization o
    JOIN   nss.organization_type_master ot
           ON ot.organization_type_pk = o.organization_type_pk
    JOIN   nss.organization_status_master os
           ON os.organization_status_pk = o.organization_status_pk
    WHERE  o.parent_organization_pk IS NULL
      AND  o.is_active = TRUE

    UNION ALL

    -- Recursive: children
    SELECT o.organization_pk, o.organization_name,
           o.organization_code,
           ot.organization_type_code, ot.organization_type_name,
           os.organization_status_code, os.organization_status_name,
           o.parent_organization_pk,
           t.depth + 1, o.is_active
    FROM   nss.organization o
    JOIN   nss.organization_type_master ot
           ON ot.organization_type_pk = o.organization_type_pk
    JOIN   nss.organization_status_master os
           ON os.organization_status_pk = o.organization_status_pk
    JOIN   org_tree t
           ON t.organization_pk = o.parent_organization_pk
    WHERE  o.is_active = TRUE
)
SELECT * FROM org_tree
ORDER BY depth, organization_name
```

---

## 4. Response Schema Summary

### Pydantic Models (api/schemas/organization.py)

| Model                              | Endpoint(s)                          | Field Count |
|------------------------------------|--------------------------------------|-------------|
| `OrganizationTypeResponse`         | types                                | 6           |
| `OrganizationStatusResponse`       | statuses                             | 6           |
| `OrganizationResponse`             | organizations, detail, children      | 36          |
| `OrganizationHierarchyNodeResponse`| hierarchy                            | 10          |

### OrganizationResponse — 34 Fields by Group

| Group              | Fields                                                                                          |
|--------------------|-------------------------------------------------------------------------------------------------|
| Core (4)           | organization_pk, organization_id, organization_name, organization_code                          |
| Classification (3) | organization_type_pk, organization_type_code, organization_type_name                            |
| Lifecycle (3)      | organization_status_pk, organization_status_code, organization_status_name                      |
| Hierarchy (2)      | parent_organization_pk, parent_organization_name                                                |
| Address (2)        | address_line_1, address_line_2                                                                  |
| Contact (4)        | phone_number, mobile_number, email, org_email                                                   |
| Online Presence (4)| website_url, org_website_url, youtube_channel_url, org_youtube_channel_url                       |
| Geographic (10)    | district_pk, district_name, state_pk, state_name, country_pk, country_name, city_village_pk, city_village_name, postal_code_pk, postal_code |
| Coordinates (2)    | latitude, longitude                                                                             |
| Status (1)         | is_active                                                                                       |

### Two-Field Pattern (NSS-Level vs Org-Specific)

| NSS-Level (NOT NULL DEFAULT)    | Org-Specific (nullable)        | Purpose                    |
|---------------------------------|--------------------------------|----------------------------|
| `email`                         | `org_email`                    | NSS email vs org's own     |
| `website_url`                   | `org_website_url`              | NSS website vs org's own   |
| `youtube_channel_url`           | `org_youtube_channel_url`      | NSS YouTube vs org's own   |

Every organization inherits the NSS website and YouTube channel via DEFAULT.
If an organization (e.g., a Sakha) has its own website or YouTube channel,
those go in the `org_*` columns. The UI displays both when present.

### Fields Deliberately Excluded

| Field                          | Reason                                      |
|--------------------------------|---------------------------------------------|
| `created_at`                   | System audit — not API-facing (Tier 0 rule) |
| `updated_at`                   | System audit — not API-facing               |
| `deleted_at`                   | System audit — not API-facing               |

---

## 5. Endpoint Count Summary

| Group              | Endpoints | Tables Covered                                            |
|--------------------|-----------|-----------------------------------------------------------|
| Reference Data     | 2         | organization_type_master, organization_status_master      |
| Core Organizations | 3         | organization (list, detail, children)                     |
| Navigation         | 1         | organization (recursive CTE)                              |
| **Total**          | **6**     | **3 tables exposed**                                      |

---

## 6. Error Responses

Carried forward from Tier 0:

| Status | When                                      | Body                                     |
|--------|-------------------------------------------|------------------------------------------|
| 200    | Success                                   | Response model (list or single)          |
| 404    | PK lookup — not found or inactive         | `{"detail": "Organization not found"}`   |
| 404    | Parent PK — not found or inactive         | `{"detail": "Parent organization not found"}` |
| 422    | Malformed UUID or invalid query parameter | FastAPI validation error                 |

---

## 7. Implementation File Map

```
api/
  routers/
    organization.py             <- 6 endpoint handlers + 2 helpers + _ORG_SELECT
  schemas/
    organization.py             <- 4 Pydantic response models
database/
  ddl/02_organization/
    01_organization_type_master.sql
    02_organization_status_master.sql
    03_organization.sql
  seed/02_organization/
    01_organization_type_master.sql   (8 types)
    02_organization_status_master.sql (6 statuses)
    03_organization.sql              (3 organizations)
tests/
  test_organization.py          <- Integration tests
frontend/
  organization.html             <- Organization Verification UI
docs/
  03_Solution/code_explanations/
      API_CODE_EXPLANATIONS.md        <- Code walkthrough (SS2.9-2.10)
      TIER2_SECURITY_AUDIT.md         <- Security audit (15 checks)
      TESTING_CODE_EXPLANATIONS.md    <- Test walkthrough (SS2.5)
```

---

## 8. Seed Data Summary

| Organization                        | Code | Type           | Contact                                       | Online Presence                |
|-------------------------------------|------|----------------|-----------------------------------------------|--------------------------------|
| Nilachala Saraswata Sangha          | KEN  | Kendra         | Ph: +91-674-2390055, Mob: +91-9238106823      | NSS website + YouTube (DEFAULT)|
| Nilachala Kutira                    | NKT  | Nilachala Kutira | —                                            | NSS website + YouTube (DEFAULT)|
| Sri Shri Nigamananda Smruti Mandir  | SMR  | Smruti Mandira | Ph: +91-6752-230631, Email: info@nsspuri.org  | NSS website + YouTube (DEFAULT)|

All 3 organizations are roots (`parent_organization_pk = NULL`).
All 3 inherit `website_url` and `youtube_channel_url` from column DEFAULTs.

---

## 9. Future (Tier 5+)

When Authentication + Administration arrives:

```
Authenticated user
       |
ERP role + permission + scope
       |
POST   /api/v1/organization/organizations          (create)
PATCH  /api/v1/organization/organizations/{pk}      (update)
DELETE /api/v1/organization/organizations/{pk}      (soft-delete)
```

Write operations will include:
- Contact field validation (email format, phone format)
- `org_website_url` and `org_youtube_channel_url` population
- Organization lifecycle transitions (e.g., Proposed -> Active)
- Child organization creation under parent hierarchy

The DB role (`nss_db_backend`) will be granted narrowly scoped write privileges
at that time — not before. A separate `nss_db_writer` role is not created until
an authenticated write requirement exists.

---

## 10. Non-Breaking Extension Points

These can be added later without changing existing contracts:

| Extension          | Mechanism                                     |
|--------------------|-----------------------------------------------|
| Pagination         | Add `?page=1&page_size=50` query params       |
| Text search        | Add `?search=...` using existing GIN index on `organization_name` |
| Recursive depth    | Add `WHERE depth < N` guard to hierarchy CTE  |
| Include inactive   | Add `?include_inactive=true` (auth-gated)     |

**Deliberately excluded from this list:**

| Capability               | Why                                                     |
|--------------------------|---------------------------------------------------------|
| Include inactive records | Authorization concern — admin-only when auth exists     |
| Nested JSON hierarchy    | Flat + depth is the chosen pattern; UI reconstructs tree|
| President/governance     | Deferred to Tier 3 Membership (role-assignment model)   |
