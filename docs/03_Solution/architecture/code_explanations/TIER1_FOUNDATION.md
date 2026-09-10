# Tier 1 — Foundation Vertical Slice

| Field       | Value                                    |
|-------------|------------------------------------------|
| Document    | TIER1_FOUNDATION                         |
| Version     | 2.0                                      |
| Release     | v0.7.0                                   |
| Authority   | SOL-ARCH-010, SOL-FND-001                |
| Status      | FROZEN                                   |

---

## 1. Purpose

This document describes the complete Tier 1 vertical slice — from Pydantic schemas through API router, web UI, and automated tests. It serves as the reference for how each layer connects and how to verify the Foundation data stack end-to-end.

Tier 1 ("Foundation") adds a read-only API exposing 11 of the 12 Foundation tables. The 12th table (`field_change_log`) is intentionally excluded — audit data requires authentication (deferred to Tier 5).

- 11 Pydantic response models
- 17 read-only GET endpoints
- 1 verification UI (4 tabs — Tailwind + DaisyUI + Alpine.js)
- 47 automated integration tests (pytest, 13 test classes)
- 2 contract-enforcement tests (security regression guards)

**Note:** Foundation DDL (12 tables) and seed data (8 tables seeded, 4 empty by design) were created in the Foundation database phase prior to this vertical slice. This document covers the API, UI, and test layers only. For DDL details, see the Foundation table-design documents.

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Browser / Client                    │
│  frontend/foundation.html (Tailwind + DaisyUI)      │
│  frontend/assets/js/foundation.js (Alpine.js)       │
└────────────────────────┬────────────────────────────┘
                         │  HTTP (fetch)
                         ▼
┌─────────────────────────────────────────────────────┐
│               FastAPI Application                    │
│  api/main.py               → app entry point         │
│  api/config.py             → env-based settings      │
│  api/database.py           → psycopg2 connection pool│
│  api/routers/foundation.py → 17 endpoints            │
│  api/schemas/foundation.py → 11 Pydantic models      │
└────────────────────────┬────────────────────────────┘
                         │  psycopg2 (raw SQL)
                         ▼
┌─────────────────────────────────────────────────────┐
│           PostgreSQL  (nss_erp database)              │
│  Schema: nss                                         │
│  Role: nss_db_backend (SELECT-only)                  │
│  Tables: 12 Foundation tables                        │
│  (field_change_log excluded from API)                │
└─────────────────────────────────────────────────────┘
```

---

## 3. Layer 1 — Pydantic Schemas

### 3.1 Design Decisions

**File:** `api/schemas/foundation.py`

```python
from uuid import UUID
from pydantic import BaseModel
```
- `UUID` — Python's built-in UUID type. Pydantic serializes it as a string in JSON responses.
- `BaseModel` — Pydantic v2 base class for data validation and serialization.
- **Note:** `ConfigDict(from_attributes=True)` is NOT imported or used. The Tier 0 Bootstrap schemas use `ConfigDict(from_attributes=True)` as future-proofing for ORM-style objects, but Tier 1 drops it. Raw psycopg2 returns tuples → we convert to dicts with `dict(zip(columns, row))` → Pydantic receives keyword arguments. `from_attributes` is unnecessary overhead that signals ORM integration the project doesn't have.

---

### 3.2 Master Data Subsystem Models

#### `CategoryResponse`

```python
class CategoryResponse(BaseModel):
    """Master category — a logical group of related master values."""

    master_category_pk: UUID
    category_code: str
    category_name: str
    description: str | None
    display_order: int
    is_active: bool
```
- Maps to `nss.master_category`.
- `str | None` — Python 3.10+ union syntax for optional fields.
- `description` is nullable — not every category needs one.
- **Excluded audit columns:** `created_at`, `created_by_sangha_sevi_pk`, `updated_at`, `updated_by_sangha_sevi_pk`, `deleted_at`, `deleted_by_sangha_sevi_pk`. This is the project's API convention from Tier 0 — audit columns are internal, not consumer data.

**Field summary:**

| Field               | Type      | Nullable | Source Column           |
|---------------------|-----------|----------|-------------------------|
| `master_category_pk`| UUID      | No       | PK                      |
| `category_code`     | str       | No       | UNIQUE business key     |
| `category_name`     | str       | No       | Human-readable label    |
| `description`       | str\|None | Yes      | Optional description    |
| `display_order`     | int       | No       | UI sort order           |
| `is_active`         | bool      | No       | Soft-delete flag        |

#### `MasterDataResponse`

```python
class MasterDataResponse(BaseModel):
    """
    Master data value with parent category context.

    Includes category_code and category_name via JOIN so the UI can
    display master data with its category context in a single API call.
    """

    master_data_pk: UUID
    master_category_pk: UUID
    category_code: str
    category_name: str
    value_code: str
    value_name: str
    description: str | None
    display_order: int
    is_active: bool
```
- Maps to `nss.master_data` JOINed with `nss.master_category`.
- `master_category_pk` — FK to the parent category. Included so the UI can link back.
- `category_code`, `category_name` — **JOINed parent context fields**. These come from `master_category` via SQL JOIN, not from `master_data` itself. This keeps the UI display-ready without a second API call to resolve the category name.
- `value_code`, `value_name` — the master data value's own business key and display label.

---

### 3.3 System Configuration Models

#### `SettingResponse`

```python
class SettingResponse(BaseModel):
    """System-wide configurable setting."""

    system_setting_pk: UUID
    setting_key: str
    setting_value: str
    description: str | None
    data_type: str
    is_active: bool
```
- Maps to `nss.system_setting`.
- `setting_key` — the business key used by code (e.g. `CURRENT_MEMBERSHIP_YEAR`). Settings are consumed by key name, not by UUID.
- `setting_value` — stored as string regardless of type; `data_type` tells the consumer how to interpret it (e.g. `INTEGER`, `STRING`, `DATE`).

#### `SequenceResponse`

```python
class SequenceResponse(BaseModel):
    """
    ID sequence configuration for generating business identifiers.

    Infrastructure/verification endpoint. current_value is excluded —
    it's infrastructure state, not consumer data.
    """

    id_sequence_master_pk: UUID
    sequence_code: str
    sequence_name: str
    prefix: str
    padding_length: int
    description: str | None
    is_active: bool
```
- Maps to `nss.id_sequence_master`.
- `prefix` + `padding_length` define the ID format pattern (e.g. prefix `"SS"` + padding `8` → `SS00000001`).
- **`current_value` is deliberately excluded.** The database column exists (`nss.id_sequence_master.current_value`), but it is infrastructure state — the next number to be assigned. Exposing it through an anonymous API would leak operational state. A contract-enforcement test (`test_current_value_not_exposed`) prevents accidental re-addition.

---

### 3.4 Geographic Subsystem Models

#### `CountryResponse`

```python
class CountryResponse(BaseModel):
    """Country reference record."""

    country_pk: UUID
    country_code: str
    country_name: str
    display_order: int
    is_active: bool
```
- Maps to `nss.country`. Standalone — no JOINed fields needed.

#### `StateResponse`

```python
class StateResponse(BaseModel):
    """
    State/province with parent country context.

    Includes country_code and country_name via JOIN.
    """

    state_pk: UUID
    country_pk: UUID
    country_code: str
    country_name: str
    state_code: str
    state_name: str
    display_order: int
    is_active: bool
```
- Maps to `nss.state` JOINed with `nss.country`.
- `country_code`, `country_name` — JOINed parent context. The UI shows "Odisha — India" without a second call.

#### `DistrictResponse`

```python
class DistrictResponse(BaseModel):
    """
    District with parent state context.

    Includes state_name via JOIN. Does not include country fields —
    resolve via the state's country_pk if needed.
    """

    district_pk: UUID
    state_pk: UUID
    state_name: str
    district_code: str
    district_name: str
    display_order: int
    is_active: bool
```
- Maps to `nss.district` JOINed with `nss.state`.
- `state_name` — JOINed parent context. Only state_name (not country fields) because the geographic drill-down UI already has the country from the previous step.

#### `CityVillageResponse`

```python
class CityVillageResponse(BaseModel):
    """City/village with parent district context."""

    city_village_pk: UUID
    district_pk: UUID
    district_name: str
    city_village_code: str
    city_village_name: str
    city_village_type: str
    display_order: int
    is_active: bool
```
- Maps to `nss.city_village` JOINed with `nss.district`.
- `city_village_type` — distinguishes `CITY` from `VILLAGE` (CHECK constraint in DDL).
- `district_name` — JOINed parent context.

#### `PostalCodeResponse`

```python
class PostalCodeResponse(BaseModel):
    """Postal code with parent state context."""

    postal_code_pk: UUID
    country_pk: UUID
    state_pk: UUID
    state_name: str
    postal_code: str
    post_office_name: str | None
    is_active: bool
```
- Maps to `nss.postal_code` JOINed with `nss.state`.
- `post_office_name` — nullable; not every postal code record has a named post office.

#### `PostalCodeMappingResponse`

```python
class PostalCodeMappingResponse(BaseModel):
    """
    City/village to postal code mapping (M:N junction).

    Pure junction table — no is_active, no soft-delete.
    Includes display fields from both sides via JOIN.
    """

    city_village_postal_code_map_pk: UUID
    city_village_pk: UUID
    city_village_name: str
    postal_code_pk: UUID
    postal_code: str
```
- Maps to `nss.city_village_postal_code_map` JOINed with both `nss.city_village` and `nss.postal_code`.
- **No `is_active`, no `display_order`** — this is a pure junction table. Rows are created or deleted, never soft-deleted.
- `city_village_name`, `postal_code` — JOINed display fields from both sides of the M:N relationship.

---

### 3.5 Runtime Tables Model

#### `DocumentResponse`

```python
class DocumentResponse(BaseModel):
    """
    Document master record.

    Tier 1 exposes only the currently useful fields. FK fields
    (person_pk, uploaded_by_sangha_sevi_pk) are excluded — their
    targets don't exist yet. The response shape will be revisited
    when consuming modules arrive; no assumption is made here about
    the final representation.
    """

    document_master_pk: UUID
    document_type_code: str
    document_number: str | None
    document_name: str
    storage_path: str
    file_size_bytes: int | None
    mime_type: str | None
    version: int
    checksum: str | None
    description: str | None
    is_active: bool
```
- Maps to `nss.document_master`.
- **Intentionally shape-agnostic.** The docstring makes no assumption about the final representation. When consuming modules (Person, Organization) arrive, this model may gain or change fields.
- **Excluded FK fields:** `person_pk`, `uploaded_by_sangha_sevi_pk` — their target tables don't exist yet (Person module is Pass 2). Including them would create broken references.

**JOINed parent context — full model summary:**

| Model                       | JOINed fields                        | Avoids                              |
|-----------------------------|--------------------------------------|--------------------------------------|
| `MasterDataResponse`        | `category_code`, `category_name`     | Second call for parent category      |
| `StateResponse`             | `country_code`, `country_name`       | Second call for parent country       |
| `DistrictResponse`          | `state_name`                         | Second call for parent state         |
| `CityVillageResponse`       | `district_name`                      | Second call for parent district      |
| `PostalCodeResponse`        | `state_name`                         | Second call for parent state         |
| `PostalCodeMappingResponse` | `city_village_name`, `postal_code`   | Lookups on both sides of junction    |

---

## 4. Layer 2 — FastAPI Router

### 4.1 Router Setup — Line-by-Line Explanation

**File:** `api/routers/foundation.py`

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_connection
from api.schemas.foundation import (
    CategoryResponse,
    CityVillageResponse,
    ...
)
```
- `APIRouter` — groups related endpoints under a shared prefix.
- `Depends` — FastAPI's dependency injection (used for database connections via `get_connection`).
- `HTTPException` — raises HTTP error responses (404).
- `Query` — declares optional query parameters with descriptions (shown in Swagger UI).
- All 11 Pydantic response models are imported from the schemas module.

```python
router = APIRouter(prefix="/api/v1/foundation", tags=["foundation"])
```
- All 17 endpoints in this router are prefixed with `/api/v1/foundation`.
- `tags=["foundation"]` — groups these endpoints in Swagger UI under "foundation" (separate from "bootstrap").

---

### 4.2 Helper Functions — Line-by-Line Explanation

```python
def _rows_to_models(cur, model_class):
    """Convert cursor results to a list of Pydantic models."""
    columns = [desc[0] for desc in cur.description]
    return [model_class(**dict(zip(columns, row))) for row in cur.fetchall()]
```
- `cur.description` — psycopg2 provides column metadata after `execute()`. Each `desc` is a 7-tuple; `desc[0]` is the column name.
- `[desc[0] for desc in cur.description]` — extracts column names as a list: `["master_category_pk", "category_code", ...]`.
- `cur.fetchall()` — returns all rows as a list of tuples.
- `zip(columns, row)` — pairs column names with values: `[("master_category_pk", uuid), ("category_code", "ORG_TYPE"), ...]`.
- `dict(zip(...))` — converts to a dictionary: `{"master_category_pk": uuid, "category_code": "ORG_TYPE", ...}`.
- `model_class(**dict(...))` — unpacks as keyword arguments to the Pydantic constructor, which validates types and serializes to JSON.
- This is the entire "cursor → Pydantic" bridge. No ORM. The SQL SELECT column list must match the model's fields exactly — a mismatch produces a Pydantic validation error at runtime, caught immediately.

```python
def _row_to_model(cur, model_class):
    """Convert a single cursor result to a Pydantic model, or None."""
    columns = [desc[0] for desc in cur.description]
    row = cur.fetchone()
    if row is None:
        return None
    return model_class(**dict(zip(columns, row)))
```
- Same pattern as `_rows_to_models`, but for single-row queries (detail endpoints).
- `cur.fetchone()` — returns one row or `None` if no match.
- Returns `None` when the row doesn't exist — the calling endpoint converts this to `HTTPException(404)`.

**Why this pattern?**

1. The router never hardcodes column positions — column names come from `cur.description`.
2. The dict-unpacking approach is explicit and debuggable — if a column is missing, Pydantic raises a clear validation error.
3. Both helpers are used by every endpoint, eliminating repetitive cursor-to-model conversion code.

---

### 4.3 Endpoint Group 1 — Master Data (4 endpoints)

#### `GET /categories` — List Categories

```python
@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(conn=Depends(get_connection)) -> list[CategoryResponse]:
    """List all active master categories."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT master_category_pk, category_code, category_name,
                   description, display_order, is_active
            FROM   nss.master_category
            WHERE  is_active = TRUE
            ORDER BY display_order, category_name
        """)
        return _rows_to_models(cur, CategoryResponse)
```
- `conn=Depends(get_connection)` — FastAPI injects a database connection from the pool. The connection is automatically returned after the response is sent.
- `response_model=list[CategoryResponse]` — response is a JSON array of category objects.
- `WHERE is_active = TRUE` — only active (non-deleted) categories. Inactive records are invisible — there is no `include_inactive` parameter (that's an authorization concern for Tier 5).
- `ORDER BY display_order, category_name` — deterministic ordering: first by explicit sort order, then alphabetically within the same order.
- SELECT column list matches `CategoryResponse` fields exactly.

#### `GET /categories/{master_category_pk}` — Category Detail

```python
@router.get("/categories/{master_category_pk}", response_model=CategoryResponse)
def get_category(
    master_category_pk: UUID,
    conn=Depends(get_connection),
) -> CategoryResponse:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT master_category_pk, category_code, category_name,
                   description, display_order, is_active
            FROM   nss.master_category
            WHERE  master_category_pk = %s AND is_active = TRUE
        """, (str(master_category_pk),))
        result = _row_to_model(cur, CategoryResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Category not found")
        return result
```
- `master_category_pk: UUID` — FastAPI parses the path parameter as a UUID. If the string is not a valid UUID, FastAPI automatically returns **422 Unprocessable Entity**.
- `%s` — parameterised query placeholder. `(str(master_category_pk),)` passes the UUID as a string (psycopg2 requires this).
- `WHERE ... AND is_active = TRUE` — inactive records return 404, same as nonexistent records.
- `_row_to_model` returns `None` if no row found → `HTTPException(404)`.

#### `GET /master-data` — List Master Data Values

```python
@router.get("/master-data", response_model=list[MasterDataResponse])
def list_master_data(
    category_code: str | None = Query(None, description="Filter by category code"),
    category_pk: UUID | None = Query(None, description="Filter by category PK"),
    conn=Depends(get_connection),
) -> list[MasterDataResponse]:
```
- Two optional query parameters for filtering: `category_code` (string) and `category_pk` (UUID).
- `Query(None, description=...)` — declares the parameter as optional with a Swagger UI description.

```python
    base_sql = """
        SELECT md.master_data_pk, md.master_category_pk,
               mc.category_code, mc.category_name,
               md.value_code, md.value_name,
               md.description, md.display_order, md.is_active
        FROM   nss.master_data md
        JOIN   nss.master_category mc
               ON mc.master_category_pk = md.master_category_pk
        WHERE  md.is_active = TRUE
          AND  mc.is_active = TRUE
    """
```
- **JOIN** — fetches `category_code` and `category_name` from the parent `master_category` table. This is the "JOINed parent context" pattern.
- Both `md.is_active` and `mc.is_active` are checked — if either the value or its parent category is soft-deleted, the value is excluded.

```python
    params: list = []

    if category_pk is not None:
        base_sql += " AND md.master_category_pk = %s"
        params.append(str(category_pk))
    elif category_code is not None:
        base_sql += " AND mc.category_code = %s"
        params.append(category_code)
```
- **Dynamic WHERE clause building.** If `category_pk` is provided, it takes precedence over `category_code`.
- All user input goes through `%s` parameterised placeholders — no string interpolation, no SQL injection surface.
- `params` is a list that grows as filters are added.

```python
    base_sql += """
        ORDER BY mc.display_order, mc.category_name,
                 md.display_order, md.value_name
    """

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, MasterDataResponse)
```
- `tuple(params)` — psycopg2 expects a tuple for parameterised queries.
- Ordering: categories first (by display_order, then name), then values within each category.

#### `GET /master-data/{master_data_pk}` — Master Data Detail

Same pattern as category detail: parameterised PK lookup with JOIN, 404 if not found.

---

### 4.4 Endpoint Group 2 — System Configuration (3 endpoints)

#### `GET /settings` — List Settings

```python
@router.get("/settings", response_model=list[SettingResponse])
def list_settings(conn=Depends(get_connection)) -> list[SettingResponse]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT system_setting_pk, setting_key, setting_value,
                   description, data_type, is_active
            FROM   nss.system_setting
            WHERE  is_active = TRUE
            ORDER BY setting_key
        """)
        return _rows_to_models(cur, SettingResponse)
```
- Straightforward list endpoint. No JOINs — settings are a flat table.
- `ORDER BY setting_key` — alphabetical by business key.

#### `GET /settings/{setting_key}` — Setting by Business Key

```python
@router.get("/settings/{setting_key}", response_model=SettingResponse)
def get_setting_by_key(
    setting_key: str,
    conn=Depends(get_connection),
) -> SettingResponse:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT system_setting_pk, setting_key, setting_value,
                   description, data_type, is_active
            FROM   nss.system_setting
            WHERE  setting_key = %s AND is_active = TRUE
        """, (setting_key,))
        result = _row_to_model(cur, SettingResponse)
        if result is None:
            raise HTTPException(status_code=404, detail="Setting not found")
        return result
```
- **Business key lookup**, not UUID lookup. Settings are consumed by code using their key name (`CURRENT_MEMBERSHIP_YEAR`), not their UUID. This is the natural access pattern.
- `setting_key: str` — path parameter is a string, not UUID. FastAPI does not validate the format (any string is valid).

#### `GET /sequences` — List ID Sequences

```python
@router.get("/sequences", response_model=list[SequenceResponse])
def list_sequences(conn=Depends(get_connection)) -> list[SequenceResponse]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id_sequence_master_pk, sequence_code, sequence_name,
                   prefix, padding_length,
                   description, is_active
            FROM   nss.id_sequence_master
            WHERE  is_active = TRUE
            ORDER BY sequence_code
        """)
        return _rows_to_models(cur, SequenceResponse)
```
- **`current_value` is NOT in the SELECT list.** The column exists in the database but is deliberately excluded from the API response. It's infrastructure state (the next number to be assigned), not consumer data.
- Infrastructure/verification endpoint — consumers use this to see what ID patterns exist, not to allocate IDs.

---

### 4.5 Endpoint Group 3 — Geographic (9 endpoints)

#### Query Parameter Filtering Pattern

Parent-child relationships use **optional query parameters**, not nested routes:

```python
# Flat: GET /states?country_pk=...
@router.get("/states")
def list_states(country_pk: UUID | None = Query(None)):
```

Not:

```python
# Nested (rejected): GET /countries/{pk}/states
```

**Rationale:** Flat query params are simpler for the frontend, composable with pagination/search later, and avoid coupling endpoint paths to the data hierarchy.

#### `GET /countries` — List Countries

```python
@router.get("/countries", response_model=list[CountryResponse])
def list_countries(conn=Depends(get_connection)) -> list[CountryResponse]:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT country_pk, country_code, country_name,
                   display_order, is_active
            FROM   nss.country
            WHERE  is_active = TRUE
            ORDER BY display_order, country_name
        """)
        return _rows_to_models(cur, CountryResponse)
```
- No JOINs — countries are top-level entities.
- Top of the geographic drill-down hierarchy: Countries → States → Districts → Cities/Villages.

#### `GET /countries/{country_pk}` — Country Detail

Same pattern as category detail. Parameterised PK lookup, 404 if not found.

#### `GET /states` — List States (with optional country filter)

```python
@router.get("/states", response_model=list[StateResponse])
def list_states(
    country_pk: UUID | None = Query(None, description="Filter by parent country"),
    conn=Depends(get_connection),
) -> list[StateResponse]:
    base_sql = """
        SELECT s.state_pk, s.country_pk,
               c.country_code, c.country_name,
               s.state_code, s.state_name,
               s.display_order, s.is_active
        FROM   nss.state s
        JOIN   nss.country c ON c.country_pk = s.country_pk
        WHERE  s.is_active = TRUE
          AND  c.is_active = TRUE
    """
    params: list = []

    if country_pk is not None:
        base_sql += " AND s.country_pk = %s"
        params.append(str(country_pk))

    base_sql += " ORDER BY c.display_order, s.display_order, s.state_name"

    with conn.cursor() as cur:
        cur.execute(base_sql, tuple(params))
        return _rows_to_models(cur, StateResponse)
```
- JOIN with `country` to include `country_code` and `country_name` in each state record.
- Optional `country_pk` filter narrows results to one country.
- Without the filter, returns all states across all countries.
- Ordering: country display order → state display order → state name.

#### `GET /states/{state_pk}` — State Detail

Same pattern: parameterised PK lookup with JOIN, 404 if not found.

#### `GET /districts` — List Districts (with optional state filter)

Same pattern as states: JOIN with `state` for `state_name`, optional `state_pk` filter.

#### `GET /districts/{district_pk}` — District Detail

Parameterised PK lookup with JOIN, 404 if not found.

#### `GET /cities` — List Cities/Villages (with optional district filter)

```python
@router.get("/cities", response_model=list[CityVillageResponse])
def list_cities(
    district_pk: UUID | None = Query(None, description="Filter by parent district"),
    conn=Depends(get_connection),
) -> list[CityVillageResponse]:
```
- Same filter pattern as states/districts.
- **Currently returns empty** — no city/village seed data by design. The table structure is verified; data arrives when consuming modules need it.

#### `GET /postal-codes` — List Postal Codes (with optional state/country filter)

```python
@router.get("/postal-codes", response_model=list[PostalCodeResponse])
def list_postal_codes(
    state_pk: UUID | None = Query(None, description="Filter by state"),
    country_pk: UUID | None = Query(None, description="Filter by country"),
    conn=Depends(get_connection),
) -> list[PostalCodeResponse]:
```
- Two optional filters: `state_pk` and `country_pk`. If `state_pk` is provided, it takes precedence (more specific).
- JOIN with `state` for `state_name`.

#### `GET /postal-code-mappings` — List City-to-PostalCode Mappings

```python
@router.get("/postal-code-mappings", response_model=list[PostalCodeMappingResponse])
def list_postal_code_mappings(
    city_village_pk: UUID | None = Query(None, description="Filter by city/village"),
    postal_code_pk: UUID | None = Query(None, description="Filter by postal code"),
    conn=Depends(get_connection),
) -> list[PostalCodeMappingResponse]:
```
- **Pure junction table** — both filters can be applied simultaneously (AND logic, not OR).
- Double JOIN: `city_village` for `city_village_name` and `postal_code` for `postal_code`.
- No `is_active` filter — junction table has no soft-delete.

```python
    conditions: list[str] = []
    params: list = []

    if city_village_pk is not None:
        conditions.append("m.city_village_pk = %s")
        params.append(str(city_village_pk))
    if postal_code_pk is not None:
        conditions.append("m.postal_code_pk = %s")
        params.append(str(postal_code_pk))

    if conditions:
        base_sql += " WHERE " + " AND ".join(conditions)
```
- **Both filters are independent** — unlike states/postal-codes where one takes precedence, both conditions can apply simultaneously. This is appropriate for a junction table: "show mappings for city X AND postal code Y".

---

### 4.6 Endpoint Group 4 — Runtime (1 endpoint)

#### `GET /documents` — List Documents

```python
@router.get("/documents", response_model=list[DocumentResponse])
def list_documents(
    document_type_code: str | None = Query(None, description="Filter by document type code"),
    conn=Depends(get_connection),
) -> list[DocumentResponse]:
```
- Optional `document_type_code` filter (string, not UUID — type codes are business keys like `PHOTO`, `ID_PROOF`).
- **Currently returns empty** — documents are runtime data uploaded by users, not seed data.
- No JOINs — FK fields (`person_pk`, `uploaded_by_sangha_sevi_pk`) are excluded from the response because their target tables don't exist yet.

---

### 4.7 Endpoint Summary Table

| Method | Path                                          | Response Model              | Filter Params              | Description                     |
|--------|-----------------------------------------------|-----------------------------|----------------------------|---------------------------------|
| GET    | `/api/v1/foundation/categories`               | `list[CategoryResponse]`    | —                          | All active categories           |
| GET    | `/api/v1/foundation/categories/{pk}`          | `CategoryResponse`          | —                          | Category by PK; 404/422         |
| GET    | `/api/v1/foundation/master-data`              | `list[MasterDataResponse]`  | `category_code`, `category_pk` | Values with category context |
| GET    | `/api/v1/foundation/master-data/{pk}`         | `MasterDataResponse`        | —                          | Value by PK; 404/422            |
| GET    | `/api/v1/foundation/settings`                 | `list[SettingResponse]`     | —                          | All active settings             |
| GET    | `/api/v1/foundation/settings/{key}`           | `SettingResponse`           | —                          | Setting by business key; 404    |
| GET    | `/api/v1/foundation/sequences`                | `list[SequenceResponse]`    | —                          | ID sequences (no current_value) |
| GET    | `/api/v1/foundation/countries`                | `list[CountryResponse]`     | —                          | All active countries            |
| GET    | `/api/v1/foundation/countries/{pk}`           | `CountryResponse`           | —                          | Country by PK; 404/422          |
| GET    | `/api/v1/foundation/states`                   | `list[StateResponse]`       | `country_pk`               | States with country context     |
| GET    | `/api/v1/foundation/states/{pk}`              | `StateResponse`             | —                          | State by PK; 404/422            |
| GET    | `/api/v1/foundation/districts`                | `list[DistrictResponse]`    | `state_pk`                 | Districts with state context    |
| GET    | `/api/v1/foundation/districts/{pk}`           | `DistrictResponse`          | —                          | District by PK; 404/422         |
| GET    | `/api/v1/foundation/cities`                   | `list[CityVillageResponse]` | `district_pk`              | Cities (empty at launch)        |
| GET    | `/api/v1/foundation/postal-codes`             | `list[PostalCodeResponse]`  | `state_pk`, `country_pk`   | Postal codes with state context |
| GET    | `/api/v1/foundation/postal-code-mappings`     | `list[PostalCodeMappingResponse]` | `city_village_pk`, `postal_code_pk` | Junction (empty at launch) |
| GET    | `/api/v1/foundation/documents`                | `list[DocumentResponse]`    | `document_type_code`       | Documents (empty — runtime)     |

---

## 5. Layer 2 (continued) — Router Registration

### 5.1 `api/main.py` — Tier 1 Additions

```python
from api.routers import bootstrap, foundation
```
- Imports both routers. `bootstrap` was Tier 0; `foundation` is Tier 1.

```python
app.include_router(foundation.router)
```
- Registers all 17 Foundation endpoints with the app, alongside the 4 Bootstrap endpoints.

```python
    _foundation_path = _FRONTEND_DIR / "foundation.html"
    if _foundation_path.is_file():

        @app.get("/foundation", include_in_schema=False)
        async def serve_foundation():
            """Serve the Foundation Verification UI."""
            return FileResponse(str(_foundation_path))
```
- Serves `frontend/foundation.html` at `/foundation`.
- `include_in_schema=False` — keeps this HTML-serving route out of Swagger UI. Only API endpoints belong in the OpenAPI spec.
- Conditional: only registers the route if the file exists (graceful degradation).

---

## 6. Layer 3 — Frontend (Foundation Verification UI)

**Stack:** Tailwind CSS + DaisyUI + Alpine.js (all via CDN — no build step, no Node.js required).

**Files:**

| File                              | Purpose                                |
|-----------------------------------|----------------------------------------|
| `frontend/foundation.html`        | Page structure + layout (4 tabs)       |
| `frontend/assets/js/foundation.js`| Alpine.js data component               |

### 6.1 `frontend/assets/js/foundation.js` — Line-by-Line Explanation

```javascript
const FND_API = "/api/v1/foundation";
```
- Base URL for all Foundation API calls. Relative path — works regardless of host/port because the frontend is served by the same FastAPI app.

```javascript
function foundationApp() {
    return {
```
- Alpine.js component factory function. Returns an object containing all reactive data and methods.
- Referenced by `x-data="foundationApp()"` in the HTML.

#### State Variables

```javascript
        // Active tab
        activeTab: "master",
```
- Controls which tab is visible. Starts on "master" (Master Data tab).

```javascript
        // Health (reuse bootstrap endpoint)
        health: { loading: true, connected: false },
```
- Reuses the `/api/v1/bootstrap/health` endpoint from Tier 0. Avoids duplicating the health check in the Foundation router.

```javascript
        // ── Master Data ──────────────────────────────
        categories: [],
        categoriesLoading: true,
        categoriesError: false,

        masterData: [],
        masterDataLoading: false,
        masterDataError: false,
        selectedCategoryCode: "",  // filter dropdown
```
- Each data group follows the same pattern: `data[]`, `loading`, `error`.
- `selectedCategoryCode` — bound to a `<select>` dropdown for filtering master data by category.

```javascript
        // ── Geographic ───────────────────────────────
        countries: [],
        countriesLoading: true,
        countriesError: false,

        states: [],
        statesLoading: false,
        statesError: false,
        selectedCountry: null,

        districts: [],
        ...
        selectedState: null,

        cities: [],
        ...
        selectedDistrict: null,

        postalCodes: [],
        ...
```
- Geographic data uses a **drill-down pattern**: clicking a country loads its states, clicking a state loads its districts, etc.
- `selectedCountry`, `selectedState`, `selectedDistrict` — the currently selected entity at each level (or `null`).
- States/districts/cities start with `loading: false` — they are only loaded on user interaction, not on page load.

#### Initialization

```javascript
        async init() {
            await this.fetchHealth();
            // Load data for the default tab
            await this.loadMasterTab();
        },
```
- Called by `x-init="init()"` when the page loads.
- Fetches health first (to show the connectivity badge), then loads the Master Data tab.

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
- Same try/catch/finally pattern as the Tier 0 Bootstrap UI.
- `res.ok` — true if HTTP status is 200–299.
- `catch` — any error (network, parse, non-200) → show as disconnected.
- `finally` — always hides the spinner.

#### Tab Switching and Lazy Loading

```javascript
        async switchTab(tab) {
            this.activeTab = tab;
            if (tab === "master") await this.loadMasterTab();
            else if (tab === "config") await this.loadConfigTab();
            else if (tab === "geo") await this.loadGeoTab();
            else if (tab === "runtime") await this.loadRuntimeTab();
        },
```
- Called by `@click="switchTab('config')"` on tab buttons.

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
- **Lazy loading** — data is fetched only when a tab is first visited.
- `if (this.categories.length === 0)` — only fetch if not already loaded.
- `_runtimeLoaded` flag — documents table is empty by design, so `length === 0` wouldn't prevent re-fetching. The flag is a one-time gate.

#### Master Data Category Filter

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
- `encodeURIComponent(categoryCode)` — URL-encodes the category code (handles special characters safely).
- If `categoryCode` is falsy (null/empty), fetches all master data.

```javascript
        async filterByCategory() {
            await this.fetchMasterData(this.selectedCategoryCode || null);
        },
```
- Called when the dropdown value changes. `selectedCategoryCode || null` converts empty string to null (fetch all).

#### Geographic Drill-Down

```javascript
        async selectCountry(country) {
            if (this.selectedCountry?.country_pk === country.country_pk) {
                // Toggle off — clear entire drill-down
                this.selectedCountry = null;
                this.states = [];
                this.selectedState = null;
                this.districts = [];
                this.selectedDistrict = null;
                this.cities = [];
                this.postalCodes = [];
                return;
            }
```
- **Toggle behavior**: clicking the same country again deselects it and clears all child selections.
- `?.` — optional chaining; `selectedCountry` may be `null`.

```javascript
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
```
- Selecting a new country: clears all child selections, then fetches states filtered by country PK.
- Also fetches postal codes for this country (separate fetch, same pattern).

```javascript
        async selectState(state) { ... }
        async selectDistrict(district) { ... }
```
- Same toggle + fetch-children pattern at each level.
- `selectState` fetches districts for the selected state.
- `selectDistrict` fetches cities/villages for the selected district.

#### Computed Property and Helper

```javascript
        get filteredMasterData() {
            if (!this.selectedCategoryCode) return this.masterData;
            return this.masterData.filter(
                d => d.category_code === this.selectedCategoryCode
            );
        },
```
- Alpine.js computed getter. Filters the master data array by the selected category code.
- If no category is selected, returns the full array.

```javascript
        formatSample(seq) {
            const padded = "1".padStart(seq.padding_length, "0");
            return `${seq.prefix}${padded}`;
        },
```
- Shows the ID format pattern for each sequence.
- Uses a static `"1"` — **not** `current_value` (which is excluded from the API response as infrastructure state).
- For a sequence with prefix `"SS"` and padding 8: `"1".padStart(8, "0")` → `"00000001"` → `"SS00000001"`.

---

### 6.2 Frontend Tab Structure

| Tab            | Data source endpoints                          | Key behaviour                          |
|----------------|-----------------------------------------------|----------------------------------------|
| Master Data    | `/categories`, `/master-data`                  | Category dropdown filter               |
| System Config  | `/settings`, `/sequences`                      | Format sample preview for sequences    |
| Geographic     | `/countries`, `/states`, `/districts`, `/cities`, `/postal-codes` | 4-column interactive drill-down |
| Runtime Tables | `/documents`                                   | "Empty by design" message + Tier 5 note |

**Breadcrumb navigation** appears only when drill-down is active:

```
India › Odisha › Khordha
```

Using explicit `›` (`&#x203A;`) separators rather than DaisyUI pseudo-elements (which don't render in all configurations).

---

## 7. Layer 4 — Automated Tests

### 7.1 Test Infrastructure

| File                          | Purpose                                      |
|-------------------------------|----------------------------------------------|
| `pytest.ini`                  | Test runner configuration (unchanged)        |
| `tests/__init__.py`           | Package marker (unchanged)                   |
| `tests/conftest.py`           | Shared `client` fixture (unchanged)          |
| `tests/test_foundation.py`    | 47 integration tests for 17 API contracts    |

### 7.2 How It Works

Tests use FastAPI's `TestClient` (from Starlette), which calls the ASGI app directly — **no HTTP server is started**. The app connects to the **local PostgreSQL** database (not Neon) using the same `api/.env` configuration.

```
pytest process
  └─ TestClient(app)
       └─ FastAPI app (api/main.py)
            └─ psycopg2 pool → local PostgreSQL (nss_erp)
```

The `client` fixture is scoped to the test module — one TestClient instance shared across all tests in a file.

---

### 7.3 `tests/test_foundation.py` — Line-by-Line Explanation

```python
"""
NSS ERP — Tier 1 Foundation API tests.

Integration tests for the 17 Foundation GET endpoints across 11 tables.
...
"""
```
- Module docstring documenting what this file tests and its prerequisites.

```python
import pytest

pytestmark = pytest.mark.integration

BASE = "/api/v1/foundation"
```
- `pytestmark` — applies the `integration` marker to **every test** in this file.
- `BASE` — constant for the Foundation API prefix. All test URLs are built from this.

#### TestCategories (6 tests)

```python
class TestCategories:
    """GET /api/v1/foundation/categories  +  categories/{pk}"""

    def test_list_returns_200(self, client):
        r = client.get(f"{BASE}/categories")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        assert len(data) > 0, "Expected seeded categories"
```
- Verifies the endpoint returns 200 with a non-empty list (categories are seeded).
- Custom assertion message makes failure diagnostics clear.

```python
    def test_list_has_required_fields(self, client):
        r = client.get(f"{BASE}/categories")
        required = {
            "master_category_pk", "category_code", "category_name",
            "description", "display_order", "is_active",
        }
        for cat in r.json():
            assert required.issubset(cat.keys()), (
                f"Missing fields in category {cat.get('category_code', '?')}: "
                f"{required - cat.keys()}"
            )
            assert cat["is_active"] is True
```
- `required` — set of the 6 fields defined in `CategoryResponse`.
- `issubset` — checks that every required field is present in each category dict.
- If a field is missing, the error message names the category and lists which fields are absent.
- `is True` — uses identity check, not equality. JSON `true` deserializes to Python `True`.

```python
    def test_detail_valid_pk(self, client):
        cats = client.get(f"{BASE}/categories").json()
        pk = cats[0]["master_category_pk"]
        r = client.get(f"{BASE}/categories/{pk}")
        assert r.status_code == 200
        assert r.json()["master_category_pk"] == pk
```
- **Integration approach**: first fetches the real categories list, then uses an actual UUID.
- No hardcoded UUIDs — the test adapts to whatever UUIDs `gen_random_uuid()` generated.

```python
    def test_detail_fake_pk_returns_404(self, client):
        fake = "00000000-0000-0000-0000-000000000000"
        assert client.get(f"{BASE}/categories/{fake}").status_code == 404

    def test_detail_bad_uuid_returns_422(self, client):
        assert client.get(f"{BASE}/categories/not-a-uuid").status_code == 422
```
- `00000000-...` is a valid UUID format that doesn't exist → 404.
- `"not-a-uuid"` is not a valid UUID → FastAPI returns 422 Unprocessable Entity.

#### TestMasterData (8 tests)

```python
    def test_filter_by_category_code(self, client):
        cats = client.get(f"{BASE}/categories").json()
        code = cats[0]["category_code"]
        r = client.get(f"{BASE}/master-data", params={"category_code": code})
        assert r.status_code == 200
        for md in r.json():
            assert md["category_code"] == code
```
- Fetches a real category code, then filters master data by it.
- Verifies **every** returned value has the correct category code — not just the first.

```python
    def test_filter_nonexistent_category_returns_empty(self, client):
        r = client.get(f"{BASE}/master-data", params={"category_code": "ZZZZZZZ_FAKE"})
        assert r.status_code == 200
        assert r.json() == []
```
- A filter with no matching data returns 200 with an empty list — not 404.
- This is the correct REST convention: the query succeeded, there are just no results.

#### TestSettings (4 tests)

```python
    def test_lookup_by_key(self, client):
        settings = client.get(f"{BASE}/settings").json()
        key = settings[0]["setting_key"]
        r = client.get(f"{BASE}/settings/{key}")
        assert r.status_code == 200
        assert r.json()["setting_key"] == key
```
- Tests the business-key lookup (string path parameter, not UUID).

```python
    def test_lookup_nonexistent_key_returns_404(self, client):
        assert client.get(f"{BASE}/settings/ZZZZZ_FAKE_KEY").status_code == 404
```
- A nonexistent setting key returns 404.

#### TestSequences (3 tests)

```python
    def test_current_value_not_exposed(self, client):
        """current_value is infrastructure state — must NOT be in the response."""
        for seq in client.get(f"{BASE}/sequences").json():
            assert "current_value" not in seq, (
                f"current_value leaked in sequence {seq.get('sequence_code', '?')}"
            )
```
- **Contract-enforcement test.** Iterates over every sequence record and asserts `current_value` is not present.
- If someone accidentally adds `current_value` back to `SequenceResponse` or the SQL SELECT, this test breaks the build.

#### TestCountries (5 tests), TestStates (5 tests), TestDistricts (5 tests)

Same patterns: list-200, required-fields, filter-by-parent-PK, detail-valid-PK, detail-fake-404.

```python
    def test_list_has_joined_country_fields(self, client):
        """Each state includes country_code and country_name via JOIN."""
        required = {
            "state_pk", "country_pk", "country_code", "country_name",
            "state_code", "state_name", "display_order", "is_active",
        }
        for s in client.get(f"{BASE}/states").json():
            assert required.issubset(s.keys())
```
- Verifies the JOINed parent context fields are present in each state record.

```python
    def test_filter_by_country_pk(self, client):
        countries = client.get(f"{BASE}/countries").json()
        cpk = countries[0]["country_pk"]
        r = client.get(f"{BASE}/states", params={"country_pk": cpk})
        assert r.status_code == 200
        for s in r.json():
            assert s["country_pk"] == cpk
```
- Verifies filtering actually works — every returned state belongs to the specified country.

#### TestCities (2 tests), TestPostalCodeMappings (1 test)

```python
class TestCities:
    """GET /api/v1/foundation/cities — intentionally empty at Tier 1."""

    def test_list_returns_200(self, client):
        """Cities endpoint returns 200 (empty list — no seed data by design)."""
        r = client.get(f"{BASE}/cities")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
```
- Tests for tables that are **empty by design**. Verifies the endpoint works (returns 200 with a list) without asserting non-emptiness.

#### TestDocuments (2 tests)

```python
class TestDocuments:
    """GET /api/v1/foundation/documents — intentionally empty at Tier 1."""

    def test_list_returns_200(self, client):
        r = client.get(f"{BASE}/documents")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_filter_by_type_code_returns_200(self, client):
        r = client.get(f"{BASE}/documents", params={"document_type_code": "PHOTO"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)
```
- Documents are runtime data — empty is expected.
- Filter test verifies the query parameter doesn't cause an error even with no data.

#### TestChangeLogNotExposed (1 test)

```python
class TestChangeLogNotExposed:
    """Verify that field_change_log has NO anonymous endpoint in Tier 1."""

    def test_change_log_endpoint_returns_404(self, client):
        """
        /api/v1/foundation/change-log must NOT exist.

        Audit data is deferred to Tier 5 authenticated API.
        If this test fails, someone added an anonymous audit endpoint.
        """
        r = client.get(f"{BASE}/change-log")
        assert r.status_code in (404, 405), (
            f"change-log endpoint should not exist in Tier 1, "
            f"got status {r.status_code}"
        )
```
- **Contract-enforcement test.** Guards against accidental addition of an anonymous audit endpoint.
- Accepts both 404 (not found) and 405 (method not allowed) — either means the endpoint doesn't exist for GET.

#### TestFoundationUI (1 test)

```python
class TestFoundationUI:
    """GET /foundation — serves the verification UI page."""

    def test_foundation_page_returns_200(self, client):
        r = client.get("/foundation")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
```
- Verifies the UI route serves HTML (not JSON, not 404).
- Note: this is `/foundation` (no `/api/v1/` prefix) — it's a page route, not an API endpoint.

---

### 7.4 Test Category Summary

| Category               | Count | What they verify                              |
|------------------------|-------|-----------------------------------------------|
| List 200 + non-empty   | 10    | Seeded tables return data                     |
| Required fields        | 7     | Response shape matches Pydantic model         |
| Detail by PK           | 5     | Valid PK returns correct record               |
| 404 on fake PK         | 5     | Nonexistent UUID returns 404                  |
| 422 on bad UUID        | 4     | Malformed UUID returns 422 validation error   |
| Query param filters    | 8     | Filtering narrows results correctly           |
| Empty-by-design        | 4     | Empty tables return `[]` not errors           |
| Contract enforcement   | 2     | `current_value` not leaked, change-log not exposed |
| UI route               | 1     | `/foundation` serves HTML                     |
| Active-only            | 1     | All returned records have `is_active=True`    |

---

## 8. How to Run Tests

### 8.1 Prerequisites

1. **Local PostgreSQL** running with the `nss_erp` database bootstrapped (DDL + seed — Foundation tables created and seeded)
2. **`api/.env`** configured with valid DB credentials for `nss_db_backend`
3. **Python virtual environment** with dependencies installed

### 8.2 Setup (one-time)

**macOS / Linux:**
```bash
cd /path/to/NSS_ERP

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install app dependencies + test dependencies
python3 -m pip install -r requirements.txt
python3 -m pip install pytest httpx
```

**Windows (Command Prompt):**
```cmd
cd C:\path\to\NSS_ERP

REM Create virtual environment
python -m venv .venv
.venv\Scripts\activate.bat

REM Install app dependencies + test dependencies
pip install -r requirements.txt
pip install pytest httpx
```

**Windows (PowerShell):**
```powershell
cd C:\path\to\NSS_ERP

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install app dependencies + test dependencies
pip install -r requirements.txt
pip install pytest httpx
```

> **Why httpx?** FastAPI's `TestClient` uses `httpx` internally to make
> in-process HTTP requests. It's listed as a Starlette test dependency
> but not in `requirements.txt` (which only has runtime deps).

### 8.3 Run All Tests

**macOS / Linux:**
```bash
source .venv/bin/activate
pytest
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
pytest
```

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
pytest
```

**Expected output (all platforms):**

```
tests/test_bootstrap.py    — 9 passed (Tier 0)
tests/test_foundation.py   — 47 passed (Tier 1)

56 passed in ~0.5s
```

### 8.4 Run Specific Subsets

These commands are the same on all platforms (once the venv is activated):

```bash
# Only Foundation tests
pytest tests/test_foundation.py

# Only one test class
pytest tests/test_foundation.py::TestCategories

# Only one test
pytest tests/test_foundation.py::TestSequences::test_current_value_not_exposed

# Only integration-marked tests
pytest -m integration

# With full traceback on failure
pytest --tb=long
```

### 8.5 Troubleshooting

| Symptom | Cause | Fix (macOS/Linux) | Fix (Windows) |
|---------|-------|--------------------|---------------|
| `ModuleNotFoundError: No module named 'api'` | Not running from repo root | `cd /path/to/NSS_ERP` | `cd C:\path\to\NSS_ERP` |
| `RuntimeError: Required environment variables not set` | Missing `api/.env` | Create `api/.env` (see Tier 0 §4.6) | Create `api\.env` (see Tier 0 §4.6) |
| `psycopg2.OperationalError: connection refused` | PostgreSQL not running | `brew services start postgresql@16` | Start via Services panel |
| `FAILED test_list_returns_200 - assert 0 > 0` | Seed data not loaded | Run Foundation seed scripts | Run Foundation seed scripts |
| `ImportError: httpx` | httpx not installed | `pip install httpx` | `pip install httpx` |
| `Activate.ps1 cannot be loaded` | PowerShell execution policy | N/A | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |

---

## 9. File Tree Summary

```
NSS_ERP/
├── api/
│   ├── .env                    # Local DB credentials (not committed)
│   ├── __init__.py
│   ├── config.py               # Settings from env vars (unchanged)
│   ├── database.py             # psycopg2 connection pool (unchanged)
│   ├── main.py                 # Mounts bootstrap + foundation routers
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── bootstrap.py        # 4 Tier 0 endpoints (unchanged)
│   │   └── foundation.py       # 17 Tier 1 endpoints ← NEW
│   └── schemas/
│       ├── __init__.py
│       ├── bootstrap.py        # Tier 0 models (unchanged)
│       └── foundation.py       # 11 Tier 1 response models ← NEW
├── database/
│   ├── scripts/                # DB setup (unchanged)
│   ├── ddl/
│   │   ├── 00_bootstrap/       # 3 Tier 0 tables (unchanged)
│   │   └── 01_foundation/      # 12 Foundation tables (pre-existing)
│   └── seed/
│       ├── 00_bootstrap/       # 8 roles (unchanged)
│       └── 01_foundation/      # Foundation seed data (pre-existing)
├── frontend/
│   ├── index.html              # Bootstrap Verification UI (unchanged)
│   ├── foundation.html         # Foundation Verification UI ← NEW
│   ├── assets/
│   │   ├── css/style.css       # Alpine.js cloak (unchanged)
│   │   ├── js/
│   │   │   ├── app.js          # Bootstrap Alpine.js component (unchanged)
│   │   │   └── foundation.js   # Foundation Alpine.js component ← NEW
│   │   └── img/nss-logo.png
│   └── README.md
├── tests/
│   ├── __init__.py             # Package marker (unchanged)
│   ├── conftest.py             # TestClient fixture (unchanged)
│   ├── test_bootstrap.py       # 9 Tier 0 tests (unchanged)
│   └── test_foundation.py      # 47 Tier 1 tests ← NEW
├── docs/03_Solution/architecture/
│   ├── FOUNDATION_API_CONTRACT.md  # API contract v1.1
│   └── code_explanations/
│       ├── TIER0_VERTICAL_SLICE.md # Tier 0 code explanation
│       ├── TIER1_FOUNDATION.md     # This file
│       └── TIER1_SECURITY_AUDIT.md # Security audit
├── pytest.ini                  # Test runner config (unchanged)
├── requirements.txt            # Python dependencies (unchanged)
├── render.yaml                 # Render.com IaC
├── render_build.sh             # Idempotent build + bootstrap
└── .gitignore
```

---

## 10. Vertical Slice Sequence — End to End

The Tier 1 vertical slice follows the project's **Business Rules First → Documentation First → Database First → API First → UI First** design philosophy:

```
Step 1: Database (pre-existing — not part of this vertical slice)
  database/ddl/01_foundation/*.sql       → 12 Foundation tables
  database/seed/01_foundation/*.sql      → Seed data (8 tables seeded)
  database/scripts/04_grant_backend.sql  → SELECT-only for backend

Step 2: API Contract
  docs/.../FOUNDATION_API_CONTRACT.md    → v1.1 (reviewed + amended)

Step 3: Schemas
  api/schemas/foundation.py              → 11 Pydantic response models

Step 4: Router
  api/routers/foundation.py              → 17 GET endpoints + 2 helpers

Step 5: Registration
  api/main.py                            → mounts foundation router + /foundation HTML route

Step 6: Frontend
  frontend/foundation.html + assets/js/foundation.js  → 4-tab verification UI

Step 7: Tests
  tests/test_foundation.py               → 47 integration tests
  Run: pytest from repo root             → all 56 pass (9 Tier 0 + 47 Tier 1)

Step 8: Security Audit
  docs/.../code_explanations/TIER1_SECURITY_AUDIT.md → 0 blocking, 6 advisory

Step 9: Code Explanation
  docs/.../code_explanations/TIER1_FOUNDATION.md     → this file
```

---

## 11. The Three Authorities

Tier 1 exemplifies the NSS architecture's separation of concerns:

```
PostgreSQL DDL           FastAPI + Pydantic         Frontend
(database truth)         (API contract)             (presentation)
─────────────────        ─────────────────          ─────────────────
12 Foundation tables     11 response models         4 verification tabs
nss.* schema             17 GET endpoints           Alpine.js drill-down
UUID PKs, FKs            JOINed parent context      category filter
constraints, indexes     parameterised SQL          breadcrumb navigation
                         active-only filtering
```

**Raw SQL** controls what data is retrieved from PostgreSQL.
**Pydantic** controls what shape and types the API exposes.
**Neither replaces the other.** Neither is an ORM.

The governing principle remains:

> **Foundation owns the mechanism; business modules own the meaning.**

---

## 12. Endpoint Classification

Not all endpoints serve the same consumer:

| Class                          | Endpoints                                     |
|--------------------------------|-----------------------------------------------|
| Normal consumption API         | categories, master-data, settings, countries, states, districts, cities, postal-codes, postal-code-mappings |
| Infrastructure / verification  | sequences, documents                          |
| Deferred to Tier 5             | change-log (field_change_log)                 |

---

## 13. What Tier 1 Does NOT Include

| Intentionally excluded | Rationale                                  |
|------------------------|--------------------------------------------|
| Authentication         | Deferred to Tier 5 (SOL-ARCH-010)          |
| CRUD operations        | No POST/PATCH/DELETE until Tier 5 auth     |
| field_change_log API   | Audit data requires authentication         |
| `current_value` field  | Infrastructure state, not consumer data    |
| `include_inactive`     | Authorization concern for Tier 5           |
| Pagination             | Foundation tables are small (~700 max)     |
| Mobile app             | Deferred until after Tiers 0-5 (TECH-MOB-001) |
| ORM                    | Raw psycopg2 by design                     |
| Write privileges       | nss_db_backend is SELECT-only              |
| Person/Organization FKs| Target tables don't exist yet (Pass 2)     |
