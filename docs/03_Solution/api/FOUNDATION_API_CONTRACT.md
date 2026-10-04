# Foundation API Contract — Tier 1

| Field       | Value                                          |
|-------------|------------------------------------------------|
| Document    | FOUNDATION_API_CONTRACT                        |
| Version     | 1.2                                            |
| Tier        | 1 — Foundation                                 |
| Authority   | SOL-FND-001, SOL-FND-003, SOL-FND-004          |
| Status      | DRAFT                                          |

---

## 1. Purpose

This document defines the API contract for the Tier 1 Foundation API: **23 endpoints —
17 reads plus 6 writes**.

> **Tier 5 update (committed, not yet merged on `feature/tier5-authentication-administration`,
> not merged/released).** Originally this API was GET-only and unauthenticated. On the Tier 5
> branch:
>
> - The 17 GET endpoints (§3.1-§3.4) now require a valid JWT whose user holds the
>   **`FOUNDATION_VIEW`** permission (`require_permission("FOUNDATION_VIEW")`, 401 without a
>   token, 403 without the permission). They still connect as `nss_db_backend`
>   (SELECT-only). Sections 2-6 below describe request/response shapes, which are unchanged;
>   read "No authentication" in any older sentence below as superseded by this note.
> - 6 write endpoints (§3.5) were added, gated by a separate **`FOUNDATION_MANAGE`**
>   permission, connecting as `nss_db_writer` (`get_write_connection`), each writing an audit
>   entry via `api/helpers.py::log_audit()` (the DB-level audit trigger also fires).
> - `field_change_log` is still **not** exposed here (`/api/v1/foundation/change-log` does not
>   exist; asserted by `tests/api/test_foundation.py::TestChangeLogNotExposed`). Audit-trail
>   reads live behind `GET /api/v1/audit/change-log` (`AUDIT_VIEW`).
> - The public registration page no longer calls these endpoints; it uses unauthenticated
>   `/api/v1/register/reference-data|states|districts|postal-codes`, thin wrappers over the same
>   `fetch_*()` helpers in `foundation.py`.

### Governing Principle

> Foundation owns the mechanism; business modules own the meaning.

The Foundation API exposes reference and master data for consumption by the
application. It is not an administrative CRUD console.

---

## 2. Conventions

### From Tier 0 (Carried Forward)

- **Prefix:** `/api/v1/foundation`
- **Tag:** `foundation`
- **Router:** `api/routers/foundation.py`
- **Schemas:** `api/schemas/foundation.py`
- **DB access:** `conn = Depends(get_connection)` with raw psycopg2
- **Response models:** Pydantic v2 `BaseModel` — no `ConfigDict(from_attributes=True)`
  (raw psycopg2 returns dictionaries, not ORM objects)
- **Audit columns excluded:** `created_at`, `updated_at`, `deleted_at` are never
  returned in API responses
- **Active-only by default:** All list endpoints filter `WHERE is_active = TRUE`
  (except tables without `is_active`)
- **UUID path parameters:** Validated by FastAPI/Pydantic (422 on malformed UUID)
- **404 on missing:** `HTTPException(status_code=404)` when a PK lookup yields no row

### New for Tier 1

- **Query parameter filtering:** Parent-child relationships use optional query
  params (e.g., `?country_pk=...`) rather than forcing nested paths
- **Hierarchical drill-down:** Geographic endpoints support optional parent
  filtering at each level
- **Code-based lookup:** Some tables support lookup by business code in addition
  to PK (e.g., `?category_code=GENDER`)
- **No pagination in Tier 1:** Data volumes are manageable (largest is districts
  at ~700 records). Pagination can be added as a non-breaking change when needed.

### Endpoint Classification

Endpoints are classified by their intended consumer:

| Class                          | Endpoints                                                       | Consumer                     |
|--------------------------------|-----------------------------------------------------------------|------------------------------|
| Normal consumption API         | categories, master-data, settings, countries, states, districts, cities, postal-codes, postal-code-mappings | Application / frontend |
| Infrastructure / verification  | sequences, documents                                            | ERP verification / admin     |
| Not exposed here               | change-log (field_change_log) — served by `/api/v1/audit/change-log` | Authenticated audit viewers (`AUDIT_VIEW`) |
| Write endpoints (Tier 5)       | POST/PATCH master-data, settings, sequences (§3.5)              | Foundation admins (`FOUNDATION_MANAGE`) |

---

## 3. Endpoint Catalogue

### 3.1 Master Data Subsystem

#### 3.1.1 List Categories

```
GET /api/v1/foundation/categories
```

Returns all active master categories.

**Query Parameters:** None

**Response:** `200 OK`

```json
[
  {
    "master_category_pk": "uuid",
    "category_code": "GENDER",
    "category_name": "Gender",
    "description": "...",
    "display_order": 1,
    "is_active": true
  }
]
```

**SQL Pattern:**

```sql
SELECT master_category_pk, category_code, category_name,
       description, display_order, is_active
FROM   nss.master_category
WHERE  is_active = TRUE
ORDER BY display_order, category_name
```

---

#### 3.1.2 Get Category by PK

```
GET /api/v1/foundation/categories/{master_category_pk}
```

Returns a single category. 404 if not found or inactive.

**Response:** `200 OK` — single `CategoryResponse`

---

#### 3.1.3 List Master Data Values

```
GET /api/v1/foundation/master-data
```

Returns all active master data values. Optionally filtered by category.

**Query Parameters:**

| Param           | Type   | Required | Description                        |
|-----------------|--------|----------|------------------------------------|
| `category_code` | string | No       | Filter by parent category code     |
| `category_pk`   | UUID   | No       | Filter by parent category PK       |

If both are provided, `category_pk` takes precedence.

**Response:** `200 OK`

```json
[
  {
    "master_data_pk": "uuid",
    "master_category_pk": "uuid",
    "category_code": "GENDER",
    "category_name": "Gender",
    "value_code": "MALE",
    "value_name": "Male",
    "description": null,
    "display_order": 1,
    "is_active": true
  }
]
```

**Design note:** The response includes `category_code` and `category_name` via
JOIN so the UI can display master data with its category context without a
second API call.

**SQL Pattern:**

```sql
SELECT md.master_data_pk, md.master_category_pk,
       mc.category_code, mc.category_name,
       md.value_code, md.value_name,
       md.description, md.display_order, md.is_active
FROM   nss.master_data md
JOIN   nss.master_category mc ON mc.master_category_pk = md.master_category_pk
WHERE  md.is_active = TRUE
  AND  mc.is_active = TRUE
ORDER BY mc.display_order, mc.category_name,
         md.display_order, md.value_name
```

When `category_code` is provided, add: `AND mc.category_code = %s`

---

#### 3.1.4 Get Master Data Value by PK

```
GET /api/v1/foundation/master-data/{master_data_pk}
```

Returns a single master data value (with category context). 404 if not found
or inactive.

**Response:** `200 OK` — single `MasterDataResponse`

---

### 3.2 System Configuration Subsystem

#### 3.2.1 List System Settings

```
GET /api/v1/foundation/settings
```

Returns all active system settings.

**Query Parameters:** None

**Response:** `200 OK`

```json
[
  {
    "system_setting_pk": "uuid",
    "setting_key": "CURRENT_MEMBERSHIP_YEAR",
    "setting_value": "2026-2027",
    "description": "...",
    "data_type": "STRING",
    "is_active": true
  }
]
```

**SQL Pattern:**

```sql
SELECT system_setting_pk, setting_key, setting_value,
       description, data_type, is_active
FROM   nss.system_setting
WHERE  is_active = TRUE
ORDER BY setting_key
```

---

#### 3.2.2 Get Setting by Key

```
GET /api/v1/foundation/settings/{setting_key}
```

Lookup by business key (not PK). Returns a single setting. 404 if not found
or inactive.

**Response:** `200 OK` — single `SettingResponse`

**SQL Pattern:**

```sql
SELECT ... FROM nss.system_setting
WHERE  setting_key = %s AND is_active = TRUE
```

**Rationale:** Settings are consumed by code using their key name
(`CURRENT_MEMBERSHIP_YEAR`), not their UUID. A key-based lookup is the natural
access pattern.

---

#### 3.2.3 List ID Sequences (Infrastructure/Verification)

```
GET /api/v1/foundation/sequences
```

Returns all active ID sequence configurations. `current_value` is excluded —
it is infrastructure state, not consumer data.

**Query Parameters:** None

**Response:** `200 OK`

```json
[
  {
    "id_sequence_master_pk": "uuid",
    "sequence_code": "SANGHA_SEVI",
    "sequence_name": "Sangha Sevi Code",
    "prefix": "SS",
    "padding_length": 8,
    "description": "...",
    "is_active": true
  }
]
```

**SQL Pattern:**

```sql
SELECT id_sequence_master_pk, sequence_code, sequence_name,
       prefix, padding_length,
       description, is_active
FROM   nss.id_sequence_master
WHERE  is_active = TRUE
ORDER BY sequence_code
```

---

### 3.3 Geographic Subsystem

The geographic tables form a strict hierarchy:

```
Country
   ↓ (1:N)
State
   ↓ (1:N)
District
   ↓ (1:N)
City/Village ←──→ Postal Code  (M:N via mapping table)
```

Each level supports optional parent filtering.

#### 3.3.1 List Countries

```
GET /api/v1/foundation/countries
```

**Response:** `200 OK`

```json
[
  {
    "country_pk": "uuid",
    "country_code": "IN",
    "country_name": "India",
    "display_order": 1,
    "is_active": true
  }
]
```

**SQL:** `SELECT ... FROM nss.country WHERE is_active = TRUE ORDER BY display_order, country_name`

---

#### 3.3.2 Get Country by PK

```
GET /api/v1/foundation/countries/{country_pk}
```

404 if not found or inactive.

---

#### 3.3.3 List States

```
GET /api/v1/foundation/states
```

**Query Parameters:**

| Param        | Type | Required | Description            |
|--------------|------|----------|------------------------|
| `country_pk` | UUID | No       | Filter by parent country |

**Response:** `200 OK`

```json
[
  {
    "state_pk": "uuid",
    "country_pk": "uuid",
    "country_code": "IN",
    "country_name": "India",
    "state_code": "OD",
    "state_name": "Odisha",
    "display_order": 1,
    "is_active": true
  }
]
```

**Design note:** Includes `country_code` and `country_name` via JOIN for display
context.

**SQL Pattern:**

```sql
SELECT s.state_pk, s.country_pk,
       c.country_code, c.country_name,
       s.state_code, s.state_name,
       s.display_order, s.is_active
FROM   nss.state s
JOIN   nss.country c ON c.country_pk = s.country_pk
WHERE  s.is_active = TRUE
  AND  c.is_active = TRUE
ORDER BY c.display_order, s.display_order, s.state_name
```

When `country_pk` is provided, add: `AND s.country_pk = %s`

---

#### 3.3.4 Get State by PK

```
GET /api/v1/foundation/states/{state_pk}
```

404 if not found or inactive.

---

#### 3.3.5 List Districts

```
GET /api/v1/foundation/districts
```

**Query Parameters:**

| Param      | Type | Required | Description                       |
|------------|------|----------|-----------------------------------|
| `state_pk` | UUID | No       | Filter by parent state            |

Without `state_pk`, returns ALL active districts (~700+). Functional for
verification; pagination deferred.

**Response:** `200 OK`

```json
[
  {
    "district_pk": "uuid",
    "state_pk": "uuid",
    "state_name": "Odisha",
    "district_code": "KHD",
    "district_name": "Khordha",
    "display_order": 1,
    "is_active": true
  }
]
```

**Design note:** Includes `state_name` via JOIN. Does NOT include country
fields — the consumer can resolve via the state's `country_pk` if needed.

**SQL Pattern:**

```sql
SELECT d.district_pk, d.state_pk,
       s.state_name,
       d.district_code, d.district_name,
       d.display_order, d.is_active
FROM   nss.district d
JOIN   nss.state s ON s.state_pk = d.state_pk
WHERE  d.is_active = TRUE
  AND  s.is_active = TRUE
ORDER BY s.state_name, d.display_order, d.district_name
```

---

#### 3.3.6 Get District by PK

```
GET /api/v1/foundation/districts/{district_pk}
```

404 if not found or inactive.

---

#### 3.3.7 List Cities/Villages

```
GET /api/v1/foundation/cities
```

**Query Parameters:**

| Param         | Type   | Required | Description              |
|---------------|--------|----------|--------------------------|
| `district_pk` | UUID   | No       | Filter by parent district |

**Response:** `200 OK`

```json
[
  {
    "city_village_pk": "uuid",
    "district_pk": "uuid",
    "district_name": "Khordha",
    "city_village_code": "BBS",
    "city_village_name": "Bhubaneswar",
    "city_village_type": "CITY",
    "display_order": 1,
    "is_active": true
  }
]
```

**Current state:** Returns empty array (no seed data). This is correct.

---

#### 3.3.8 List Postal Codes

```
GET /api/v1/foundation/postal-codes
```

**Query Parameters:**

| Param         | Type | Required | Description                                                      |
|---------------|------|----------|------------------------------------------------------------------|
| `state_pk`    | UUID | No       | Filter by state                                                  |
| `country_pk`  | UUID | No       | Filter by country (resolved via `state.country_pk`)              |
| `district_pk` | UUID | No       | Filter by district (via `city_village` — see note below)         |
| `q`           | str  | No       | Match the PIN digits (prefix, min 2 chars)                       |

**Response:** `200 OK`

```json
[
  {
    "postal_code_pk": "uuid",
    "country_pk": "uuid",
    "state_pk": "uuid",
    "state_name": "Odisha",
    "postal_code": "751022",
    "is_active": true
  }
]
```

> **Simplified Geography Model (2026-10-02).** `nss.post_office` is
> retired. `nss.postal_code` is unique on `postal_code` alone — one row
> per PIN globally, carrying a pre-resolved dominant `state_pk`. There is
> no office-level detail any more: `post_office_name` and `office_count`
> are gone, and `?q=` matches PIN digits only. `country_pk` is still
> returned for the frontend cascade but is derived from
> `state.country_pk`, not stored on `postal_code`. `postal_code` has no
> `district_pk` of its own, so district scoping resolves through
> `nss.city_village`, which carries both `district_pk` and
> `postal_code_pk` as direct anchors.

**SQL Pattern:**

```sql
SELECT pc.postal_code_pk, pc.state_pk,
       s.state_name, s.country_pk,
       pc.postal_code, pc.is_active
FROM   nss.postal_code pc
JOIN   nss.state s ON s.state_pk = pc.state_pk
WHERE  pc.is_active = TRUE
  -- district_pk filter:
  -- AND EXISTS (SELECT 1 FROM nss.city_village cv
  --             WHERE cv.postal_code_pk = pc.postal_code_pk
  --               AND cv.is_active = TRUE
  --               AND cv.district_pk = %s)
ORDER BY pc.postal_code
```

---

#### 3.3.9 List City-Postal Code Mappings

```
GET /api/v1/foundation/postal-code-mappings
```

**Query Parameters:**

| Param            | Type | Required | Description             |
|------------------|------|----------|-------------------------|
| `city_village_pk`| UUID | No       | Filter by city/village  |
| `postal_code_pk` | UUID | No       | Filter by postal code   |

**Response:** `200 OK`

```json
[
  {
    "city_village_postal_code_map_pk": "uuid",
    "city_village_pk": "uuid",
    "city_village_name": "...",
    "postal_code_pk": "uuid",
    "postal_code": "751022"
  }
]
```

**Design note:** This is a pure junction table — no `is_active`, no `deleted_at`.
Response includes display fields from both sides via JOIN.

**Current state:** Returns empty array (no seed data). Correct.

---

### 3.4 Runtime Tables (Intentionally Empty)

#### 3.4.1 List Documents (Infrastructure/Verification)

```
GET /api/v1/foundation/documents
```

**Query Parameters:**

| Param              | Type   | Required | Description                    |
|--------------------|--------|----------|--------------------------------|
| `document_type_code` | string | No     | Filter by document type code   |

**Response:** `200 OK`

```json
[
  {
    "document_master_pk": "uuid",
    "document_type_code": "PHOTO",
    "document_number": null,
    "document_name": "...",
    "storage_path": "...",
    "file_size_bytes": 12345,
    "mime_type": "image/jpeg",
    "version": 1,
    "checksum": null,
    "description": null,
    "is_active": true
  }
]
```

**Design note:** Tier 1 exposes only the currently useful fields. FK fields
(`person_pk`, `uploaded_by_sangha_sevi_pk`) are excluded — their targets don't
exist yet. The response shape will be revisited when consuming modules arrive;
no assumption is made here about the final representation.

**Current state:** Returns empty array. Correct — documents are runtime data
populated when document-consuming modules start using them.

---

#### 3.4.2 Field Change Log — NOT EXPOSED HERE (see `/api/v1/audit/change-log`)

```
field_change_log is NOT exposed by this router (no /api/v1/foundation/change-log).
```

**Rationale:** audit/change-log data must only be available to authenticated, authorized
consumers with their own permission. Rather than hang it off Foundation, Tier 5 exposes it
through a dedicated router: `GET /api/v1/audit/change-log`, gated by `AUDIT_VIEW` (seeded to
`NSS_ERP_ADMIN`, `NSS_ERP_KENDRA_ADMIN`, `NSS_ERP_AUDITOR`). The absence of a Foundation
change-log route is enforced by `tests/api/test_foundation.py::TestChangeLogNotExposed`.

---

> **Later additions not detailed in this document (see `API_CONTRACT.md` §4):** `GET /post-offices`
> (post offices under a PIN, SOL-ARCH-010 Amendment 2026-10-03), `GET /sakha-postal-codes`,
> `GET /festivals` + `GET`/`POST`/`PATCH /festival-calendar-dates` (`FOUNDATION_CALENDAR_MANAGE`
> for writes), and four member-facing `POST /{districts|postal-codes|post-offices|city-villages}/propose`
> endpoints (any logged-in user with an active Sangha Sevi; rows land `PENDING` and are reviewed
> via `/api/v1/admin/geo-entries/*`). The router therefore has 33 endpoints in total.

### 3.5 Write Endpoints (Tier 5 — committed, not yet merged)

All six require a JWT with the **`FOUNDATION_MANAGE`** permission, use the write-capable
`nss_db_writer` connection, and call `log_audit()` (`module="foundation"`). Codes are
upper-cased and trimmed server-side. Immutable identifiers (category, `value_code`,
`setting_key`, `data_type`, `sequence_code`) cannot be changed by PATCH because other tables
and code reference them.

| # | Method | Path | Body | Success | Errors |
|---|--------|------|------|---------|--------|
| 3.5.1 | POST | `/master-data` | `CreateMasterDataRequest`: `category_code`, `value_code` (<=50), `value_name` (<=150), `description?`, `display_order` (>=0, default 0), `applicable_modules?` (NULL = all modules) | 201 `MasterDataResponse` | 404 unknown category; 409 duplicate `value_code` in category |
| 3.5.2 | PATCH | `/master-data/{master_data_pk}` | `UpdateMasterDataRequest`: any of `value_name`, `description`, `display_order`, `applicable_modules` | 200 `MasterDataResponse` | 404 not found; 422 no fields supplied |
| 3.5.3 | POST | `/settings` | `CreateSettingRequest`: `setting_key` (<=100), `setting_value`, `data_type` (`STRING`\|`INTEGER`\|`BOOLEAN`\|`DATE`\|`JSON`, default `STRING`), `description?` | 201 `SettingResponse` | 409 duplicate key; 422 bad `data_type` or value not valid for the type (DATE is DD/MM/YYYY) |
| 3.5.4 | PATCH | `/settings/{setting_key}` | `UpdateSettingRequest`: `setting_value`, `description?` | 200 `SettingResponse` | 404; 422 value invalid for the stored `data_type` |
| 3.5.5 | POST | `/sequences` | `CreateSequenceRequest`: `sequence_code` (<=50), `sequence_name` (<=100), `prefix` (<=20), `padding_length` (0-12, default 8), `description?` | 201 `SequenceResponse` | 409 duplicate code or name |
| 3.5.6 | PATCH | `/sequences/{sequence_code}` | `UpdateSequenceRequest`: any of `sequence_name`, `prefix`, `padding_length`, `description` | 200 `SequenceResponse` | 404; 409 duplicate name |

`current_value` is never writable through the API; new sequences start at 0. Note:
`api/helpers.py::next_id()` currently returns `prefix + number` without applying
`padding_length`, so padding edits are stored but do not yet change generated IDs (tracked as a
deferred item in `CLAUDE.md`).

---

## 4. Response Schema Summary

### Pydantic Models (api/schemas/foundation.py)

| Model                     | Endpoint(s)                      | Fields                                                              |
|---------------------------|----------------------------------|---------------------------------------------------------------------|
| `CategoryResponse`        | categories, categories/{pk}      | master_category_pk, category_code, category_name, description, display_order, is_active |
| `MasterDataResponse`      | master-data, master-data/{pk} (+ POST/PATCH) | master_data_pk, master_category_pk, category_code, category_name, value_code, value_name, description, applicable_modules, display_order, is_active |
| `SettingResponse`          | settings, settings/{key} (+ POST/PATCH) | system_setting_pk, setting_key, setting_value, description, data_type, is_active |
| `SequenceResponse`         | sequences (+ POST/PATCH)         | id_sequence_master_pk, sequence_code, sequence_name, prefix, padding_length, description, is_active |
| `CountryResponse`          | countries, countries/{pk}        | country_pk, country_code, country_name, display_order, is_active    |
| `StateResponse`            | states, states/{pk}              | state_pk, country_pk, country_code, country_name, state_code, state_name, display_order, is_active |
| `DistrictResponse`         | districts, districts/{pk}        | district_pk, state_pk, state_name, district_code, district_name, display_order, is_active |
| `CityVillageResponse`      | cities                           | city_village_pk, district_pk, district_name, city_village_code, city_village_name, city_village_type, display_order, is_active |
| `PostalCodeResponse`       | postal-codes                     | postal_code_pk, country_pk, state_pk, state_name, postal_code, is_active |
| `PostalCodeMappingResponse` | postal-code-mappings            | city_village_postal_code_map_pk, city_village_pk, city_village_name, postal_code_pk, postal_code |
| `DocumentResponse`         | documents                        | document_master_pk, document_type_code, document_number, document_name, storage_path, file_size_bytes, mime_type, version, checksum, description, is_active |

### Fields Deliberately Excluded

| Field                          | Reason                                      |
|--------------------------------|---------------------------------------------|
| `created_at`                   | System audit — not API-facing (Tier 0 rule) |
| `updated_at`                   | System audit — not API-facing               |
| `deleted_at`                   | System audit — not API-facing               |
| `current_value` (sequences)    | Infrastructure state — not consumer data    |
| `person_pk`                    | FK target doesn't exist yet (Pass 2)        |
| `uploaded_by_sangha_sevi_pk`   | FK target doesn't exist yet (Pass 2)        |
| `uploaded_at`                  | Deferred with uploaded_by context            |
| `changed_by_sangha_sevi_pk`    | FK target doesn't exist yet (Pass 2)        |

---

## 5. Endpoint Count Summary

| Group              | Endpoints | Tables Covered                                            |
|--------------------|-----------|-----------------------------------------------------------|
| Master Data        | 4         | master_category (list, detail), master_data (list, detail)|
| System Config      | 3         | system_setting (list, by-key), id_sequence_master (list)  |
| Geographic         | 9         | country (2), state (2), district (2), city_village (1), postal_code (1), mapping (1) |
| Runtime            | 1         | document_master (1)                                       |
| **Total (reads)**  | **17**    | **11 tables exposed (`field_change_log` served by `/api/v1/audit/change-log`)** |
| Writes (Tier 5)    | 6         | master_data (POST, PATCH), system_setting (POST, PATCH), id_sequence_master (POST, PATCH) |
| **Grand total**    | **23**    |                                                           |

---

## 6. Error Responses

Carried forward from Tier 0:

| Status | When                                      | Body                                |
|--------|-------------------------------------------|-------------------------------------|
| 200/201| Success / created                         | Response model (list or single)     |
| 401    | Missing/invalid/expired JWT (Tier 5)      | `{"detail": "..."}`                 |
| 403    | Lacks `FOUNDATION_VIEW` (reads) or `FOUNDATION_MANAGE` (writes) | `{"detail": "..."}` |
| 404    | PK/key lookup — not found or inactive     | `{"detail": "... not found"}`       |
| 409    | Duplicate code/key/name on create (writes)| `{"detail": "... already exists"}`  |
| 422    | Malformed UUID, invalid query parameter, invalid write body/value | Human-readable validation error (`api/error_handlers.py`) |

---

## 7. Implementation File Map

```
api/
  routers/
    foundation.py          <- 23 endpoint handlers (17 GET + 6 write);
                              fetch_countries/states/districts/postal_codes/master_data()
                              are also reused by routers/registration.py's public endpoints
  schemas/
    foundation.py          <- response models + Create/Update request models
tests/
  api/test_foundation.py   <- Integration tests (45)
frontend/
  admin.html, assets/js/admin.js
                           <- Reference Data, Geography and System Settings tabs
                              (replace the retired foundation.html)
docs/
  03_Solution/code_explanations/
    API_CODE_EXPLANATIONS.md      <- Code walkthrough
    SECURITY_CODE_EXPLANATIONS.md <- Middleware/CORS/rate-limit walkthrough
    TESTING_CODE_EXPLANATIONS.md  <- Test walkthrough
```

---

## 8. Implementation History

```
Tier 1 (v0.7.0): 17 GET handlers, 11 response models, Foundation Verification UI
Tier 5 (branch feature/tier5-authentication-administration):
  - require_permission("FOUNDATION_VIEW") added to every GET
  - 6 write handlers + Create/Update request models + FOUNDATION_MANAGE permission
  - Verification UI retired; functionality moved into admin.html
```

---

## 9. Future

Not yet implemented (would need its own governance decision): create/update/soft-delete of
`master_category`, country/state/district/city/postal-code writes, and `include_inactive`
visibility. Inactive-record visibility remains an authorization concern, not a query-parameter
extension — it would be gated behind authenticated administrative access.

---

## 10. Non-Breaking Extension Points

These can be added later without changing existing contracts:

| Extension          | Mechanism                                     |
|--------------------|-----------------------------------------------|
| Pagination         | Add `?limit=`/`?offset=` (as used by the other routers) |
| Text search        | Add `?search=...` using existing GIN indexes  |
| Field selection    | Add `?fields=code,name` for partial responses |

**Deliberately excluded from this list:**

| Capability               | Why                                                     |
|--------------------------|---------------------------------------------------------|
| Include inactive records | Authorization concern — admin-only when auth exists     |
| Unrestricted sort        | Same — historical/admin data exposure requires authz    |
