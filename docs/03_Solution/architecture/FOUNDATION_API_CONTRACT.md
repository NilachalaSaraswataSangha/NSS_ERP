# Foundation API Contract — Tier 1 Read-Only

| Field       | Value                                          |
|-------------|------------------------------------------------|
| Document    | FOUNDATION_API_CONTRACT                        |
| Version     | 1.1                                            |
| Tier        | 1 — Foundation                                 |
| Authority   | SOL-FND-001, SOL-FND-003, SOL-FND-004          |
| Status      | DRAFT                                          |

---

## 1. Purpose

This document defines the API contract for the Tier 1 Foundation read-only API.
All endpoints are GET-only. No authentication. `nss_db_backend` connects with
SELECT-only privileges.

Write operations (POST/PATCH/DELETE) are deferred to Tier 5 when authenticated
administration and authorization exist.

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
| Deferred to Tier 5             | change-log (field_change_log)                                   | Authenticated audit viewers  |

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

| Param        | Type | Required | Description               |
|--------------|------|----------|---------------------------|
| `state_pk`   | UUID | No       | Filter by state           |
| `country_pk` | UUID | No       | Filter by country         |

**Response:** `200 OK`

```json
[
  {
    "postal_code_pk": "uuid",
    "country_pk": "uuid",
    "state_pk": "uuid",
    "state_name": "Odisha",
    "postal_code": "751022",
    "post_office_name": "Unit 9 SO, Bhubaneswar",
    "is_active": true
  }
]
```

**SQL Pattern:**

```sql
SELECT pc.postal_code_pk, pc.country_pk, pc.state_pk,
       s.state_name,
       pc.postal_code, pc.post_office_name, pc.is_active
FROM   nss.postal_code pc
JOIN   nss.state s ON s.state_pk = pc.state_pk
WHERE  pc.is_active = TRUE
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

#### 3.4.2 Field Change Log — DEFERRED TO TIER 5

```
field_change_log is NOT exposed in Tier 1.
```

**Rationale:** Even though the table is empty at launch, establishing an
anonymous audit endpoint creates a contract that would later need to be
restricted. Audit/change-log data should only be available to authenticated,
authorized consumers.

**Tier 5 plan:** When authentication arrives, expose as:

```
GET /api/v1/foundation/change-log     (authenticated + authorized)
```

The database table exists and functions correctly for internal writes;
it simply has no anonymous read endpoint.

---

## 4. Response Schema Summary

### Pydantic Models (api/schemas/foundation.py)

| Model                     | Endpoint(s)                      | Fields                                                              |
|---------------------------|----------------------------------|---------------------------------------------------------------------|
| `CategoryResponse`        | categories, categories/{pk}      | master_category_pk, category_code, category_name, description, display_order, is_active |
| `MasterDataResponse`      | master-data, master-data/{pk}    | master_data_pk, master_category_pk, category_code, category_name, value_code, value_name, description, display_order, is_active |
| `SettingResponse`          | settings, settings/{key}         | system_setting_pk, setting_key, setting_value, description, data_type, is_active |
| `SequenceResponse`         | sequences                        | id_sequence_master_pk, sequence_code, sequence_name, prefix, padding_length, description, is_active |
| `CountryResponse`          | countries, countries/{pk}        | country_pk, country_code, country_name, display_order, is_active    |
| `StateResponse`            | states, states/{pk}              | state_pk, country_pk, country_code, country_name, state_code, state_name, display_order, is_active |
| `DistrictResponse`         | districts, districts/{pk}        | district_pk, state_pk, state_name, district_code, district_name, display_order, is_active |
| `CityVillageResponse`      | cities                           | city_village_pk, district_pk, district_name, city_village_code, city_village_name, city_village_type, display_order, is_active |
| `PostalCodeResponse`       | postal-codes                     | postal_code_pk, country_pk, state_pk, state_name, postal_code, post_office_name, is_active |
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
| **Total**          | **17**    | **11 tables exposed (12th — field_change_log — deferred)**|

---

## 6. Error Responses

Carried forward from Tier 0:

| Status | When                                      | Body                                |
|--------|-------------------------------------------|-------------------------------------|
| 200    | Success                                   | Response model (list or single)     |
| 404    | PK/key lookup — not found or inactive     | `{"detail": "... not found"}`       |
| 422    | Malformed UUID or invalid query parameter | FastAPI validation error            |

---

## 7. Implementation File Map

```
api/
  routers/
    foundation.py          ← 17 endpoint handlers
  schemas/
    foundation.py          ← 11 Pydantic response models
tests/
  test_foundation.py       ← Integration tests
frontend/
  foundation.html          ← Foundation Verification UI
docs/
  03_Solution/architecture/
    code_explanations/
      TIER1_FOUNDATION.md  ← Code walkthrough (post-implementation)
```

---

## 8. Implementation Sequence

```
1. Create api/schemas/foundation.py      (11 Pydantic models)
2. Create api/routers/foundation.py      (17 GET handlers)
3. Register router in api/main.py
4. Create tests/test_foundation.py       (integration tests)
5. Run API + database integration tests
6. Swagger / manual verification
7. Build Foundation Verification UI
8. UI / manual verification
9. Code explanation document
10. Freeze Tier 1 → v0.7.0
```

---

## 9. Future (Tier 5+)

When Authentication + Administration arrives:

```
Authenticated user
       ↓
ERP role + permission + scope
       ↓
POST   /api/v1/foundation/categories          (create)
PATCH  /api/v1/foundation/categories/{pk}      (update)
DELETE /api/v1/foundation/categories/{pk}      (soft-delete)
PATCH  /api/v1/foundation/settings/{key}       (update value)
GET    /api/v1/foundation/change-log           (authenticated audit)
...
```

Write operations will be added per-endpoint as authorized use cases emerge.
The DB role (`nss_db_backend`) will be granted narrowly scoped write privileges
at that time — not before.

Inactive-record visibility (`include_inactive`) is an authorization concern,
not a query-parameter extension — it will be gated behind authenticated
administrative access.

---

## 10. Non-Breaking Extension Points

These can be added later without changing existing contracts:

| Extension          | Mechanism                                     |
|--------------------|-----------------------------------------------|
| Pagination         | Add `?page=1&page_size=50` query params       |
| Text search        | Add `?search=...` using existing GIN indexes  |
| Field selection    | Add `?fields=code,name` for partial responses |

**Deliberately excluded from this list:**

| Capability               | Why                                                     |
|--------------------------|---------------------------------------------------------|
| Include inactive records | Authorization concern — admin-only when auth exists     |
| Unrestricted sort        | Same — historical/admin data exposure requires authz    |
