# Tier 0 — Bootstrap RBAC Vertical Slice

| Field       | Value                                    |
|-------------|------------------------------------------|
| Document    | TIER0_VERTICAL_SLICE                     |
| Version     | 2.0                                      |
| Release     | v0.6.0                                   |
| Authority   | SOL-ARCH-010, SOL-ARCH-011, SOL-BOOT-001 |
| Status      | FROZEN                                   |

---

## 1. Purpose

This document describes the complete Tier 0 vertical slice — from database DDL through seed data, API layer, web UI, and automated tests. It serves as the reference for how each layer connects and how to verify the entire stack end-to-end.

Tier 0 ("Bootstrap RBAC") establishes the minimum infrastructure required before any functional module can be built:

- 3 database tables (role_master, permission_master, role_permission)
- 8 frozen RBAC roles seeded
- 4 read-only API endpoints
- 1 verification UI (Tailwind + DaisyUI + Alpine.js)
- 9 automated integration tests (pytest)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  Browser / Client                    │
│  frontend/index.html  (Tailwind + DaisyUI + Alpine) │
└────────────────────────┬────────────────────────────┘
                         │  HTTP (fetch)
                         ▼
┌─────────────────────────────────────────────────────┐
│               FastAPI Application                    │
│  api/main.py          → app entry point              │
│  api/config.py        → env-based settings           │
│  api/database.py      → psycopg2 connection pool     │
│  api/routers/bootstrap.py → 4 endpoints              │
│  api/schemas/bootstrap.py → Pydantic response models  │
└────────────────────────┬────────────────────────────┘
                         │  psycopg2 (raw SQL)
                         ▼
┌─────────────────────────────────────────────────────┐
│           PostgreSQL  (nss_erp database)              │
│  Schema: nss                                         │
│  Role: nss_db_backend (SELECT-only in Tier 0)        │
│  Tables: role_master, permission_master,              │
│          role_permission                             │
└─────────────────────────────────────────────────────┘
```

---

## 3. Layer 1 — Database

### 3.1 PostgreSQL Setup Scripts

Run once as superuser (`postgres`):

**macOS / Linux:**
```bash
# Step 1: Create database, roles (nss_db_owner, nss_db_backend)
psql -U postgres -d postgres -f database/scripts/00_create_database.sql

# Step 2: Install extensions (pgcrypto, pg_trgm, btree_gin, postgis), create nss schema
psql -U postgres -d nss_erp -f database/scripts/01_extensions.sql
```

**Windows (Command Prompt):**
```cmd
REM Step 1: Create database, roles (nss_db_owner, nss_db_backend)
psql -U postgres -d postgres -f database\scripts\00_create_database.sql

REM Step 2: Install extensions, create nss schema
psql -U postgres -d nss_erp -f database\scripts\01_extensions.sql
```

**Windows (PowerShell):**
```powershell
# Step 1: Create database, roles (nss_db_owner, nss_db_backend)
psql -U postgres -d postgres -f database\scripts\00_create_database.sql

# Step 2: Install extensions, create nss schema
psql -U postgres -d nss_erp -f database\scripts\01_extensions.sql
```

> **Note:** On Windows, PostgreSQL is typically installed via the
> [EnterpriseDB installer](https://www.postgresql.org/download/windows/)
> or Chocolatey (`choco install postgresql`). Ensure `psql` is on your
> PATH (default: `C:\Program Files\PostgreSQL\16\bin`).

**Roles created:**

| PostgreSQL Role  | Purpose                                  | Privileges              |
|------------------|------------------------------------------|-------------------------|
| `nss_db_owner`   | DDL owner — runs CREATE TABLE, INSERT    | Owns `nss` schema       |
| `nss_db_backend` | Runtime — used by FastAPI application    | SELECT-only (Tier 0)    |

> **Naming convention (SOL-ARCH-011 §7.2):**
> `nss_db_*` = PostgreSQL infrastructure roles (lowercase).
> `NSS_ERP_*` = Application RBAC roles (UPPERCASE, stored in `role_master`).

---

### 3.2 DDL — Table Definitions

Run as `nss_db_owner` against `nss_erp`.

**macOS / Linux:**
```bash
psql -U nss_db_owner -d nss_erp -f database/ddl/00_bootstrap/01_role_master.sql
psql -U nss_db_owner -d nss_erp -f database/ddl/00_bootstrap/02_permission_master.sql
psql -U nss_db_owner -d nss_erp -f database/ddl/00_bootstrap/03_role_permission.sql
```

**Windows:**
```cmd
psql -U nss_db_owner -d nss_erp -f database\ddl\00_bootstrap\01_role_master.sql
psql -U nss_db_owner -d nss_erp -f database\ddl\00_bootstrap\02_permission_master.sql
psql -U nss_db_owner -d nss_erp -f database\ddl\00_bootstrap\03_role_permission.sql
```

---

#### 3.2.1 `nss.role_master` — Line-by-Line DDL Explanation

**File:** `database/ddl/00_bootstrap/01_role_master.sql`

```sql
CREATE TABLE nss.role_master
(
```
- Creates the table in the `nss` schema. All NSS ERP tables live in this schema; `public` is reserved for extensions.

```sql
    role_master_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),
```
- **Primary key** using UUID (not auto-increment integer).
- `gen_random_uuid()` comes from the `pgcrypto` extension (installed in `01_extensions.sql`).
- UUIDs prevent ID-guessing attacks and allow offline ID generation.

```sql
    role_code VARCHAR(50) NOT NULL,
```
- Machine-readable identifier (e.g. `NSS_ERP_ADMIN`). Used in code and API responses.
- `NOT NULL` — every role must have a code.

```sql
    role_name VARCHAR(100) NOT NULL,
```
- Human-readable label (e.g. "NSS ERP Administrator"). Displayed in the UI.

```sql
    role_class VARCHAR(30) NOT NULL,
```
- Classifies the role as either `SYSTEM` (NSS-wide) or `ORGANIZATIONAL` (scoped to an org unit).
- Enforced by a CHECK constraint below.

```sql
    scope_level VARCHAR(30) NULL,
```
- Defines the organizational scope: `NSS-WIDE`, `KENDRA`, `ANCHALIKA`, `ZILLA`, `SAKHA`, or `PATHA_CHAKRA`.
- `NULL` is allowed (the CHECK constraint permits it), but in practice all 8 frozen roles have a scope.

```sql
    description TEXT NULL,
```
- Optional free-text description of the role's purpose.

```sql
    display_order INTEGER NOT NULL
        DEFAULT 0,
```
- Controls the sort order when listing roles in the UI or API.
- Defaults to `0`; the seed sets explicit values 1–8.

```sql
    -- Audit columns
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    created_by_sangha_sevi_pk UUID NULL,
    updated_at TIMESTAMPTZ NULL,
    updated_by_sangha_sevi_pk UUID NULL,
    deleted_at TIMESTAMPTZ NULL,
    deleted_by_sangha_sevi_pk UUID NULL,
```
- **Standard audit pattern** used by every NSS ERP table:
  - `created_at` — auto-set on INSERT, never changed.
  - `created_by_sangha_sevi_pk` — FK to the person who created the row. NULL in Tier 0 (no auth yet).
  - `updated_at` / `updated_by` — set on UPDATE. NULL until first modification.
  - `deleted_at` / `deleted_by` — soft-delete timestamps. NULL while active.
- `TIMESTAMPTZ` stores timezone-aware timestamps (UTC internally).

```sql
    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```
- Soft-delete flag. `FALSE` = logically deleted. The API filters on `WHERE is_active = TRUE`.

```sql
    -- Unique constraints
    CONSTRAINT uq_role_master_code
        UNIQUE (role_code),
    CONSTRAINT uq_role_master_name
        UNIQUE (role_name),
```
- No two roles can share the same `role_code` or `role_name`.
- Named constraints make error messages readable (e.g. `violates unique constraint "uq_role_master_code"`).

```sql
    CONSTRAINT chk_role_master_class
        CHECK (role_class IN ('SYSTEM', 'ORGANIZATIONAL')),
```
- **Database-level enforcement** — the DB rejects any INSERT/UPDATE with an invalid `role_class`.
- Project preference: CHECK constraints over application-level validation.

```sql
    CONSTRAINT chk_role_master_scope_level
        CHECK
        (
            scope_level IS NULL
            OR
            scope_level IN ('NSS-WIDE', 'KENDRA', 'ANCHALIKA', 'ZILLA', 'SAKHA', 'PATHA_CHAKRA')
        ),
```
- Restricts `scope_level` to the 6 organizational tiers defined in the NSS Bye-Law, or NULL.
- These correspond to the 5 Organization Types (Kendra, Anchalika, Zilla, Sakha, Patha Chakra) plus the NSS-WIDE level for system roles.

```sql
    CONSTRAINT chk_role_master_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);
```
- Enforces **soft-delete consistency**: you cannot have `is_active = TRUE` with a `deleted_at` timestamp, or `is_active = FALSE` without one.
- This prevents orphaned states where a row appears active but has a deletion timestamp (or vice versa).

```sql
CREATE INDEX idx_role_master_active
    ON nss.role_master (is_active);
CREATE INDEX idx_role_master_code
    ON nss.role_master (role_code);
CREATE INDEX idx_role_master_class
    ON nss.role_master (role_class);
```
- **Performance indexes:**
  - `idx_role_master_active` — speeds up `WHERE is_active = TRUE` (used by every API query).
  - `idx_role_master_code` — speeds up lookups by role_code.
  - `idx_role_master_class` — speeds up filtering by SYSTEM vs ORGANIZATIONAL.

**Column summary:**

| Column                     | Type          | Constraints                                     |
|----------------------------|---------------|--------------------------------------------------|
| `role_master_pk`           | UUID PK       | DEFAULT gen_random_uuid()                        |
| `role_code`                | VARCHAR(50)   | NOT NULL, UNIQUE                                 |
| `role_name`                | VARCHAR(100)  | NOT NULL, UNIQUE                                 |
| `role_class`               | VARCHAR(30)   | NOT NULL, CHECK IN ('SYSTEM', 'ORGANIZATIONAL')  |
| `scope_level`              | VARCHAR(30)   | NULL, CHECK IN (NSS-WIDE, KENDRA, ANCHALIKA, ZILLA, SAKHA, PATHA_CHAKRA) |
| `description`              | TEXT          | NULL                                             |
| `display_order`            | INTEGER       | NOT NULL, DEFAULT 0                              |
| `created_at`               | TIMESTAMPTZ   | NOT NULL, DEFAULT CURRENT_TIMESTAMP              |
| `created_by_sangha_sevi_pk`| UUID          | NULL                                             |
| `updated_at`               | TIMESTAMPTZ   | NULL                                             |
| `updated_by_sangha_sevi_pk`| UUID          | NULL                                             |
| `deleted_at`               | TIMESTAMPTZ   | NULL                                             |
| `deleted_by_sangha_sevi_pk`| UUID          | NULL                                             |
| `is_active`                | BOOLEAN       | NOT NULL, DEFAULT TRUE                           |

---

#### 3.2.2 `nss.permission_master` — Line-by-Line DDL Explanation

**File:** `database/ddl/00_bootstrap/02_permission_master.sql`

```sql
CREATE TABLE nss.permission_master
(
    permission_master_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),
```
- Same UUID PK pattern as `role_master`.

```sql
    permission_code VARCHAR(80) NOT NULL,
```
- Machine-readable permission identifier (e.g. `FOUNDATION.VIEW`, `PERSON.EDIT`).
- Wider than role_code (80 vs 50) because permission codes include the module prefix.

```sql
    permission_name VARCHAR(150) NOT NULL,
```
- Human-readable label. Wider than role_name (150 vs 100) for descriptive permission names.

```sql
    module_code VARCHAR(50) NOT NULL,
```
- Which module this permission belongs to (e.g. `FOUNDATION`, `PERSON`, `ORGANIZATION`).
- Used for grouping and filtering in the UI.

```sql
    description TEXT NULL,
    display_order INTEGER NOT NULL DEFAULT 0,
```
- Same as role_master — optional description and UI sort order.

```sql
    -- Audit columns (same pattern as role_master)
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_sangha_sevi_pk UUID NULL,
    updated_at TIMESTAMPTZ NULL,
    updated_by_sangha_sevi_pk UUID NULL,
    deleted_at TIMESTAMPTZ NULL,
    deleted_by_sangha_sevi_pk UUID NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
```
- Identical audit column set. Every table in the NSS ERP schema follows this pattern.

```sql
    CONSTRAINT uq_permission_master_code
        UNIQUE (permission_code),
    CONSTRAINT chk_permission_master_soft_delete
        CHECK (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);
```
- `permission_code` must be unique across all modules.
- Same soft-delete consistency check as `role_master`.
- Note: `permission_name` is NOT unique (unlike `role_name`) — different modules could theoretically have permissions with the same display name.

```sql
CREATE INDEX idx_permission_master_active ON nss.permission_master (is_active);
CREATE INDEX idx_permission_master_code ON nss.permission_master (permission_code);
CREATE INDEX idx_permission_master_module ON nss.permission_master (module_code);
```
- `idx_permission_master_module` is unique to this table — enables fast filtering by module (e.g. "show all FOUNDATION permissions").

**Column summary:**

| Column                     | Type          | Constraints                                     |
|----------------------------|---------------|--------------------------------------------------|
| `permission_master_pk`     | UUID PK       | DEFAULT gen_random_uuid()                        |
| `permission_code`          | VARCHAR(80)   | NOT NULL, UNIQUE                                 |
| `permission_name`          | VARCHAR(150)  | NOT NULL                                         |
| `module_code`              | VARCHAR(50)   | NOT NULL                                         |
| `description`              | TEXT          | NULL                                             |
| `display_order`            | INTEGER       | NOT NULL, DEFAULT 0                              |
| Audit columns              | (same pattern as role_master)                       |

---

#### 3.2.3 `nss.role_permission` — Line-by-Line DDL Explanation

**File:** `database/ddl/00_bootstrap/03_role_permission.sql`

```sql
CREATE TABLE nss.role_permission
(
    role_permission_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),
```
- Junction table linking roles to permissions. Each row = "this role has this permission".

```sql
    role_master_pk UUID NOT NULL,
    permission_master_pk UUID NOT NULL,
```
- Both FKs are `NOT NULL` — a mapping must reference both a role and a permission.

```sql
    -- Audit (reduced set — no updated_at/updated_by)
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_sangha_sevi_pk UUID NULL,
    deleted_at TIMESTAMPTZ NULL,
    deleted_by_sangha_sevi_pk UUID NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
```
- No `updated_at`/`updated_by` — role-permission mappings are created or soft-deleted, never edited in place.

```sql
    CONSTRAINT fk_role_permission_role
        FOREIGN KEY (role_master_pk)
        REFERENCES nss.role_master (role_master_pk),
    CONSTRAINT fk_role_permission_permission
        FOREIGN KEY (permission_master_pk)
        REFERENCES nss.permission_master (permission_master_pk),
```
- **Foreign keys** enforce referential integrity at the database level.
- Cannot insert a mapping for a nonexistent role or permission.
- No `ON DELETE CASCADE` — rows are soft-deleted, never hard-deleted.

```sql
    CONSTRAINT uq_role_permission_mapping
        UNIQUE (role_master_pk, permission_master_pk),
```
- Prevents assigning the same permission to the same role twice.
- Composite unique constraint on both FK columns.

```sql
    CONSTRAINT chk_role_permission_soft_delete
        CHECK (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);
```
- Same soft-delete consistency check.

```sql
CREATE INDEX idx_role_permission_role ON nss.role_permission (role_master_pk);
CREATE INDEX idx_role_permission_permission ON nss.role_permission (permission_master_pk);
CREATE INDEX idx_role_permission_active ON nss.role_permission (is_active);
```
- `idx_role_permission_role` — speeds up "get all permissions for role X" (the `/roles/{role_pk}/permissions` endpoint).
- `idx_role_permission_permission` — speeds up reverse lookup "which roles have permission Y".

**Column summary:**

| Column                     | Type          | Constraints                                     |
|----------------------------|---------------|--------------------------------------------------|
| `role_permission_pk`       | UUID PK       | DEFAULT gen_random_uuid()                        |
| `role_master_pk`           | UUID          | NOT NULL, FK → role_master                       |
| `permission_master_pk`     | UUID          | NOT NULL, FK → permission_master                 |
| `created_at`               | TIMESTAMPTZ   | NOT NULL, DEFAULT CURRENT_TIMESTAMP              |
| `created_by_sangha_sevi_pk`| UUID          | NULL                                             |
| `deleted_at`               | TIMESTAMPTZ   | NULL                                             |
| `deleted_by_sangha_sevi_pk`| UUID          | NULL                                             |
| `is_active`                | BOOLEAN       | NOT NULL, DEFAULT TRUE                           |

**UNIQUE:** `uq_role_permission_mapping(role_master_pk, permission_master_pk)`

---

### 3.3 Seed Data

**File:** `database/seed/00_bootstrap/02_role_master.sql`

**macOS / Linux:**
```bash
psql -U nss_db_owner -d nss_erp -f database/seed/00_bootstrap/01_permission_master.sql   # empty
psql -U nss_db_owner -d nss_erp -f database/seed/00_bootstrap/02_role_master.sql          # 8 roles
psql -U nss_db_owner -d nss_erp -f database/seed/00_bootstrap/03_role_permission.sql      # empty
```

**Windows:**
```cmd
psql -U nss_db_owner -d nss_erp -f database\seed\00_bootstrap\01_permission_master.sql
psql -U nss_db_owner -d nss_erp -f database\seed\00_bootstrap\02_role_master.sql
psql -U nss_db_owner -d nss_erp -f database\seed\00_bootstrap\03_role_permission.sql
```

#### Seed SQL — Line-by-Line Explanation

```sql
INSERT INTO nss.role_master
    (role_code, role_name, role_class, scope_level, description, display_order)
VALUES
```
- Inserts into 6 columns. The remaining columns use defaults:
  - `role_master_pk` → auto-generated UUID
  - `created_at` → auto-set to now
  - `created_by_sangha_sevi_pk` → NULL (no auth in Tier 0)
  - `updated_at`, `updated_by`, `deleted_at`, `deleted_by` → NULL
  - `is_active` → TRUE

```sql
    ('NSS_ERP_ADMIN',
     'NSS ERP Administrator',
     'SYSTEM',
     'NSS-WIDE',
     'System-wide ERP administrator with all application permissions',
     1),
```
- **Row 1:** System administrator. `SYSTEM` class + `NSS-WIDE` scope = full access across the entire organization.
- `display_order = 1` — appears first in the UI.

```sql
    ('NSS_ERP_AUDITOR',
     'Auditor',
     'SYSTEM',
     'NSS-WIDE',
     'System-wide read-only auditor for compliance and review',
     2),
```
- **Row 2:** Read-only auditor. Can view everything but change nothing. Used for compliance reviews.

```sql
    ('NSS_ERP_REPORT_VIEWER',
     'Report Viewer',
     'SYSTEM',
     'NSS-WIDE',
     'System-wide read-only access to reports and dashboards',
     3),
```
- **Row 3:** Similar to Auditor but limited to reports/dashboards (when those modules exist).

```sql
    ('NSS_ERP_KENDRA_ADMIN', ... 'ORGANIZATIONAL', 'KENDRA', ..., 4),
    ('NSS_ERP_ANCHALIKA_ADMIN', ... 'ORGANIZATIONAL', 'ANCHALIKA', ..., 5),
    ('NSS_ERP_ZILLA_ADMIN', ... 'ORGANIZATIONAL', 'ZILLA', ..., 6),
    ('NSS_ERP_SAKHA_ADMIN', ... 'ORGANIZATIONAL', 'SAKHA', ..., 7),
    ('NSS_ERP_PATHA_CHAKRA_ADMIN', ... 'ORGANIZATIONAL', 'PATHA_CHAKRA', ..., 8);
```
- **Rows 4–8:** One admin role per organizational tier (Kendra → Anchalika → Zilla → Sakha → Patha Chakra).
- All are `ORGANIZATIONAL` class — scoped to a specific organizational unit, not system-wide.
- These map to the 5 Organization Types from the NSS Bye-Law.

**8 frozen roles (SOL-ADMIN-004 §8.7):**

| # | role_code                   | role_name                   | role_class      | scope_level  |
|---|-----------------------------|-----------------------------|-----------------|--------------|
| 1 | NSS_ERP_ADMIN               | NSS ERP Administrator       | SYSTEM          | NSS-WIDE     |
| 2 | NSS_ERP_AUDITOR             | Auditor                     | SYSTEM          | NSS-WIDE     |
| 3 | NSS_ERP_REPORT_VIEWER       | Report Viewer               | SYSTEM          | NSS-WIDE     |
| 4 | NSS_ERP_KENDRA_ADMIN        | Kendra Administrator        | ORGANIZATIONAL  | KENDRA       |
| 5 | NSS_ERP_ANCHALIKA_ADMIN     | Anchalika Administrator     | ORGANIZATIONAL  | ANCHALIKA    |
| 6 | NSS_ERP_ZILLA_ADMIN         | Zilla Administrator         | ORGANIZATIONAL  | ZILLA        |
| 7 | NSS_ERP_SAKHA_ADMIN         | Sakha Administrator         | ORGANIZATIONAL  | SAKHA        |
| 8 | NSS_ERP_PATHA_CHAKRA_ADMIN  | Patha Chakra Administrator  | ORGANIZATIONAL  | PATHA_CHAKRA |

**Empty by design:**
- `permission_master` seed — permission catalogue is populated progressively per module
- `role_permission` seed — depends on permission catalogue

---

### 3.4 Backend Privileges — Line-by-Line Explanation

**File:** `database/scripts/04_grant_backend.sql`

**macOS / Linux:**
```bash
psql -U nss_db_owner -d nss_erp -f database/scripts/04_grant_backend.sql
```

**Windows:**
```cmd
psql -U nss_db_owner -d nss_erp -f database\scripts\04_grant_backend.sql
```

```sql
GRANT USAGE ON SCHEMA nss TO nss_db_backend;
```
- Allows `nss_db_backend` to **see** the `nss` schema. Without this, the role cannot reference `nss.*` tables at all.

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA nss TO nss_db_backend;
```
- Grants **read-only** access to every table that currently exists in the `nss` schema.
- No INSERT, UPDATE, or DELETE — the FastAPI app can only read in Tier 0.

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA nss
    GRANT SELECT ON TABLES TO nss_db_backend;
```
- **Forward-looking**: any table created in `nss` in the future will automatically get SELECT granted to `nss_db_backend`.
- Saves having to re-run this script after every new DDL file.

---

## 4. Layer 2 — FastAPI Application

### 4.1 Configuration — Line-by-Line Explanation

**File:** `api/config.py`

```python
import os
from pathlib import Path
from dotenv import load_dotenv
```
- `os` — reads environment variables.
- `pathlib.Path` — cross-platform file path handling (works on both macOS/Linux and Windows).
- `dotenv.load_dotenv` — loads `.env` file into `os.environ` so the app can read DB credentials without system-level env vars.

```python
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path, encoding="utf-8-sig")
```
- `Path(__file__).resolve().parent` — resolves to the `api/` directory regardless of where the process was started.
  - On macOS/Linux: e.g. `/Users/you/NSS_ERP/api/`
  - On Windows: e.g. `C:\Users\you\NSS_ERP\api\`
- `encoding="utf-8-sig"` — handles .env files created on Windows that may have a BOM (Byte Order Mark).
- Loads `api/.env` into the environment. If the file doesn't exist, silently continues (env vars may be set externally).

```python
class Settings:
    DB_NAME: str = os.environ.get("DB_NAME", "")
    DB_USER: str = os.environ.get("DB_USER", "")
    DB_PASSWORD: str = os.environ.get("DB_PASSWORD", "")
    DB_HOST: str = os.environ.get("DB_HOST", "localhost")
    DB_PORT: str = os.environ.get("DB_PORT", "5432")
    API_PORT: int = int(os.environ.get("API_PORT", "8001"))
```
- Class attributes read from environment at import time.
- `DB_NAME`, `DB_USER`, `DB_PASSWORD` default to empty string (caught by `validate()`).
- `DB_HOST` defaults to `localhost` — works on both macOS/Linux and Windows.
- `DB_PORT` defaults to `5432` (standard PostgreSQL port).
- `API_PORT` defaults to `8001` and is cast to `int`.

```python
    def validate(self) -> None:
        missing = []
        if not self.DB_NAME:
            missing.append("DB_NAME")
        if not self.DB_USER:
            missing.append("DB_USER")
        if not self.DB_PASSWORD:
            missing.append("DB_PASSWORD")
        if missing:
            raise RuntimeError(
                f"Required environment variables not set: {', '.join(missing)}. "
                f"Create api/.env or export them before starting the server."
            )
```
- Called before the first database connection.
- Fails fast with a clear error listing exactly which variables are missing.
- Does NOT check `DB_HOST`/`DB_PORT` (they have safe defaults).

```python
settings = Settings()
```
- Module-level singleton. Imported by `database.py` and anywhere else that needs config.

**Environment variables:**

| Variable     | Required | Default     | Description              |
|-------------|----------|-------------|--------------------------|
| `DB_NAME`   | Yes      | —           | Database name (`nss_erp`)|
| `DB_USER`   | Yes      | —           | PostgreSQL role          |
| `DB_PASSWORD`| Yes     | —           | Role password            |
| `DB_HOST`   | No       | `localhost` | PostgreSQL host          |
| `DB_PORT`   | No       | `5432`      | PostgreSQL port          |
| `API_PORT`  | No       | `8001`      | Uvicorn listen port      |

---

### 4.2 Database Pool — Line-by-Line Explanation

**File:** `api/database.py`

```python
import psycopg2
import psycopg2.pool
from api.config import settings
```
- `psycopg2` — Python adapter for PostgreSQL. Raw SQL, no ORM.
- `psycopg2.pool` — built-in connection pooling.
- `settings` — the config singleton (Section 4.1).

```python
_pool: psycopg2.pool.SimpleConnectionPool | None = None
```
- Module-level variable holding the shared connection pool.
- `None` until first use (lazy initialization).
- `SimpleConnectionPool | None` uses Python 3.10+ union syntax.

```python
def get_pool() -> psycopg2.pool.SimpleConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        settings.validate()
        _pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
        )
    return _pool
```
- **Lazy init**: pool is created on the first call, not at import time.
- `settings.validate()` is called before creating the pool — fails fast if env vars are missing.
- `minconn=1` — one connection kept open at all times (warm start).
- `maxconn=5` — at most 5 concurrent connections to PostgreSQL.
- If the pool was closed (e.g. after shutdown), it re-creates.

```python
def close_pool() -> None:
    global _pool
    if _pool is not None and not _pool.closed:
        _pool.closeall()
        _pool = None
```
- Called during FastAPI shutdown (via lifespan). Closes all connections cleanly.

```python
def get_connection():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)
```
- **FastAPI dependency** — used with `Depends(get_connection)` in route functions.
- `yield` makes it a generator: FastAPI calls `next()` to get the connection, then triggers `finally` after the request completes.
- `pool.getconn()` borrows a connection from the pool.
- `pool.putconn(conn)` returns it after the request — the connection is reused, not closed.

```python
def check_connection() -> bool:
    try:
        pool = get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
            return True
        finally:
            pool.putconn(conn)
    except Exception:
        return False
```
- Used by the `/health` endpoint.
- Executes `SELECT 1` — the simplest possible query to verify the database is reachable.
- Returns `True`/`False` — never leaks connection details or error messages.

---

### 4.3 Pydantic Schemas — Line-by-Line Explanation

**File:** `api/schemas/bootstrap.py`

```python
from uuid import UUID
from pydantic import BaseModel, ConfigDict
```
- `UUID` — Python's built-in UUID type. Pydantic serializes it as a string in JSON responses.
- `BaseModel` — Pydantic base class for data validation and serialization.
- `ConfigDict` — Pydantic v2 configuration.

```python
class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
```
- `from_attributes=True` — allows creating this model from objects with attributes (not just dicts). Future-proofing for ORM-style objects.

```python
    role_master_pk: UUID
    role_code: str
    role_name: str
    role_class: str
    scope_level: str | None
    description: str | None
    display_order: int
    is_active: bool
```
- Each field maps to a column in `nss.role_master`.
- `str | None` — Python 3.10+ union syntax for optional fields.
- **Deliberately excluded:** `created_at`, `created_by_sangha_sevi_pk`, `updated_at`, `updated_by_sangha_sevi_pk`, `deleted_at`, `deleted_by_sangha_sevi_pk`. These are internal audit columns not exposed via the API.

```python
class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    permission_master_pk: UUID
    permission_code: str
    permission_name: str
    module_code: str
    description: str | None
    display_order: int
    is_active: bool
```
- Same pattern as `RoleResponse`, maps to `nss.permission_master`.
- `module_code` allows the UI to group permissions by module.

```python
class HealthResponse(BaseModel):
    status: str       # "ok" or "degraded"
    database: str     # "connected" or "unreachable"
```
- Minimal health check response. Two string fields:
  - `status` — overall application status.
  - `database` — specifically whether the DB is reachable.

---

### 4.4 Endpoints — Line-by-Line Explanation

**File:** `api/routers/bootstrap.py`

```python
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from api.database import check_connection, get_connection
from api.schemas.bootstrap import HealthResponse, PermissionResponse, RoleResponse
```
- `APIRouter` — groups related endpoints under a shared prefix.
- `Depends` — FastAPI's dependency injection (used for database connections).
- `HTTPException` — raises HTTP error responses (404, 422).
- Imports the connection helpers and Pydantic schemas.

```python
router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])
```
- All endpoints in this router are prefixed with `/api/v1/bootstrap`.
- `tags=["bootstrap"]` — groups these endpoints in Swagger UI under "bootstrap".

#### Endpoint 1: Health Check

```python
@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
```
- `GET /api/v1/bootstrap/health`
- `response_model=HealthResponse` — FastAPI validates and serializes the return value.
- No `conn=Depends(get_connection)` — this endpoint uses `check_connection()` instead, which handles its own connection lifecycle.

```python
    db_ok = check_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unreachable",
    )
```
- Calls `check_connection()` (SELECT 1 — see Section 4.2).
- Returns `"ok"/"connected"` or `"degraded"/"unreachable"`.
- Never exposes connection details or error messages — security by design.

#### Endpoint 2: List Roles

```python
@router.get("/roles", response_model=list[RoleResponse])
def list_roles(conn=Depends(get_connection)) -> list[RoleResponse]:
```
- `GET /api/v1/bootstrap/roles`
- `conn=Depends(get_connection)` — FastAPI injects a database connection from the pool. The connection is automatically returned to the pool after the response is sent.
- `response_model=list[RoleResponse]` — response is a JSON array of role objects.

```python
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role_master_pk, role_code, role_name, role_class,
                   scope_level, description, display_order, is_active
              FROM nss.role_master
             WHERE is_active = TRUE
             ORDER BY display_order
            """
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
```
- Opens a cursor (auto-closed by `with` block).
- Raw SQL query — no ORM. Selects only the columns that match `RoleResponse` fields.
- `WHERE is_active = TRUE` — only active (non-deleted) roles.
- `ORDER BY display_order` — deterministic ordering (1–8 for the frozen roles).
- `cur.description` — psycopg2 provides column metadata after execute. We extract column names.
- `cur.fetchall()` — returns all rows as a list of tuples.

```python
    return [RoleResponse(**dict(zip(columns, row))) for row in rows]
```
- `zip(columns, row)` — pairs column names with values: `[("role_master_pk", uuid), ("role_code", "NSS_ERP_ADMIN"), ...]`
- `dict(...)` — converts to a dictionary: `{"role_master_pk": uuid, "role_code": "NSS_ERP_ADMIN", ...}`
- `RoleResponse(**dict(...))` — unpacks into the Pydantic model, which validates types and serializes to JSON.
- List comprehension builds the full response array.

#### Endpoint 3: List Permissions

```python
@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(conn=Depends(get_connection)) -> list[PermissionResponse]:
```
- `GET /api/v1/bootstrap/permissions`
- Same pattern as `list_roles`.

```python
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT permission_master_pk, permission_code, permission_name,
                   module_code, description, display_order, is_active
              FROM nss.permission_master
             WHERE is_active = TRUE
             ORDER BY module_code, display_order
            """
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return [PermissionResponse(**dict(zip(columns, row))) for row in rows]
```
- `ORDER BY module_code, display_order` — groups permissions by module, then sorts within each module.
- In Tier 0, this returns an **empty list** — permission_master has no seed data yet.

#### Endpoint 4: Role Permissions

```python
@router.get("/roles/{role_pk}/permissions", response_model=list[PermissionResponse])
def list_role_permissions(role_pk: UUID, conn=Depends(get_connection)) -> list[PermissionResponse]:
```
- `GET /api/v1/bootstrap/roles/{role_pk}/permissions`
- `role_pk: UUID` — FastAPI parses the path parameter as a UUID. If the string is not a valid UUID, FastAPI automatically returns **422 Unprocessable Entity** (this is what `test_role_permissions_invalid_uuid` tests).

```python
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM nss.role_master WHERE role_master_pk = %s AND is_active = TRUE",
            (str(role_pk),),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Role not found")
```
- First verifies the role exists. `%s` is a parameterized query (prevents SQL injection).
- `str(role_pk)` — psycopg2 requires UUID to be passed as string.
- If no row is returned, raises **404 Not Found**.

```python
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pm.permission_master_pk, pm.permission_code, pm.permission_name,
                   pm.module_code, pm.description, pm.display_order, pm.is_active
              FROM nss.role_permission rp
              JOIN nss.permission_master pm
                ON pm.permission_master_pk = rp.permission_master_pk
             WHERE rp.role_master_pk = %s
               AND rp.is_active = TRUE
               AND pm.is_active = TRUE
             ORDER BY pm.module_code, pm.display_order
            """,
            (str(role_pk),),
        )
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
    return [PermissionResponse(**dict(zip(columns, row))) for row in rows]
```
- JOINs `role_permission` with `permission_master` to get the permission details.
- Filters on `is_active = TRUE` for both the mapping and the permission.
- In Tier 0, returns an **empty list** (no role-permission mappings exist yet).

**Endpoint summary:**

| Method | Path                                          | Response            | Description                        |
|--------|-----------------------------------------------|---------------------|------------------------------------|
| GET    | `/api/v1/bootstrap/health`                    | `HealthResponse`    | Liveness/readiness probe           |
| GET    | `/api/v1/bootstrap/roles`                     | `list[RoleResponse]`| All active roles (8 frozen)        |
| GET    | `/api/v1/bootstrap/permissions`               | `list[PermissionResponse]` | All active permissions (empty in Tier 0) |
| GET    | `/api/v1/bootstrap/roles/{role_pk}/permissions`| `list[PermissionResponse]` | Permissions for a role; 404 if not found; 422 if bad UUID |

---

### 4.5 Application Entry — Line-by-Line Explanation

**File:** `api/main.py`

```python
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from api.database import close_pool
from api.routers import bootstrap
```
- `asynccontextmanager` — creates the lifespan handler for startup/shutdown.
- `Path` — cross-platform file path (works on Windows and macOS/Linux).
- `StaticFiles` — serves static assets (CSS, JS, images).
- `FileResponse` — serves a single file (index.html).

```python
_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
```
- Resolves to the `frontend/` directory relative to this file.
  - macOS/Linux: `/path/to/NSS_ERP/frontend`
  - Windows: `C:\path\to\NSS_ERP\frontend`
- `Path` handles the `/` vs `\` difference automatically.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    close_pool()
```
- **Lifespan handler**: code before `yield` runs at startup (none needed), code after runs at shutdown.
- `close_pool()` — cleanly closes all database connections when the server stops.

```python
app = FastAPI(
    title="NSS ERP API",
    version="0.1.0",
    description="Nilachala Saraswata Sangha ERP — Tier 0 Bootstrap API. Read-only RBAC verification endpoints.",
    lifespan=lifespan,
)
```
- Creates the FastAPI application instance.
- `title`, `version`, `description` appear in the Swagger UI at `/docs`.

```python
app.include_router(bootstrap.router)
```
- Registers all 4 bootstrap endpoints (Section 4.4) with the app.

```python
if _FRONTEND_DIR.is_dir():
    _index_path = _FRONTEND_DIR / "index.html"
    app.mount(
        "/assets",
        StaticFiles(directory=str(_FRONTEND_DIR / "assets")),
        name="frontend-assets",
    )

    @app.get("/", include_in_schema=False)
    async def serve_frontend():
        return FileResponse(str(_index_path))
```
- Only mounts the frontend if the `frontend/` directory exists (graceful degradation).
- `/assets/*` serves CSS, JS, and images from `frontend/assets/`.
- `/` serves `frontend/index.html`.
- `include_in_schema=False` — the root route doesn't appear in Swagger UI (it's a UI page, not an API endpoint).

---

### 4.6 Starting the Server

**macOS / Linux:**
```bash
cd /path/to/NSS_ERP

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure database connection
cat > api/.env << 'EOF'
DB_NAME=nss_erp
DB_USER=nss_db_backend
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
EOF

# Start the server
python3 -m uvicorn api.main:app --reload --port 8001
```

**Windows (Command Prompt):**
```cmd
cd C:\path\to\NSS_ERP

REM Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt

REM Configure database connection (create api\.env manually or use echo)
echo DB_NAME=nss_erp > api\.env
echo DB_USER=nss_db_backend >> api\.env
echo DB_PASSWORD=your_password_here >> api\.env
echo DB_HOST=localhost >> api\.env
echo DB_PORT=5432 >> api\.env

REM Start the server
python -m uvicorn api.main:app --reload --port 8001
```

**Windows (PowerShell):**
```powershell
cd C:\path\to\NSS_ERP

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure database connection
@"
DB_NAME=nss_erp
DB_USER=nss_db_backend
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
"@ | Set-Content api\.env

# Start the server
python -m uvicorn api.main:app --reload --port 8001
```

> **Windows note:** If `Activate.ps1` is blocked by execution policy, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

**URLs (same on all platforms):**
- http://localhost:8001/ — Bootstrap Verification UI
- http://localhost:8001/docs — Swagger UI (OpenAPI)
- http://localhost:8001/api/v1/bootstrap/health — Health check

---

## 5. Layer 3 — Frontend (Bootstrap Verification UI)

**Stack:** Tailwind CSS + DaisyUI + Alpine.js (all via CDN — no build step, no Node.js required).

**Files:**

| File                          | Purpose                                |
|-------------------------------|----------------------------------------|
| `frontend/index.html`        | Single-page app shell                  |
| `frontend/assets/js/app.js`  | Alpine.js component (`bootstrapApp()`) |
| `frontend/assets/css/style.css` | Custom styles (minimal)             |
| `frontend/assets/img/nss-logo.png` | NSS logo                         |

### 5.1 `frontend/index.html` — Key Sections Explained

```html
<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2/dist/tailwind.min.css" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/npm/daisyui@4/dist/full.min.css" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3/dist/cdn.min.js"></script>
```
- **Tailwind CSS** — utility-first CSS framework. Classes like `bg-base-200`, `text-sm`, `px-6` are all Tailwind.
- **DaisyUI** — component library built on Tailwind. Provides `card`, `badge`, `table`, `alert`, `loading` components.
- **Alpine.js** — lightweight reactive framework. `x-data`, `x-init`, `x-for`, `x-text`, `x-if`, `@click` are Alpine directives.
- `defer` on Alpine — ensures the DOM is parsed before Alpine initializes.

```html
<div x-data="bootstrapApp()" x-init="init()" class="mx-auto px-6 py-6 lg:px-10 2xl:px-16">
```
- `x-data="bootstrapApp()"` — creates an Alpine component instance using the function defined in `app.js`.
- `x-init="init()"` — calls the `init()` method when the component mounts (fetches health, roles, permissions in parallel).

```html
<template x-if="!health.loading && health.connected">
    <span class="flex items-center gap-2">
        <span class="badge badge-success badge-xs"></span>
        <span class="text-sm">Database Connected</span>
    </span>
</template>
```
- `x-if` — conditional rendering. Only shows this block when loading is done AND the database is connected.
- `badge badge-success` — DaisyUI green badge.

```html
<template x-for="role in roles" :key="role.role_master_pk">
    <tr class="cursor-pointer hover"
        :class="{ 'bg-base-200': selectedRole?.role_master_pk === role.role_master_pk }"
        @click="selectRole(role)">
```
- `x-for` — loops over the `roles` array, rendering one table row per role.
- `:key` — Alpine uses this for efficient DOM updates (like React's `key`).
- `:class` — dynamically adds `bg-base-200` (highlight) when this role is selected.
- `@click="selectRole(role)"` — calls `selectRole()` when the row is clicked, triggering the role-permissions fetch.

**UI layout:** Three-column responsive grid:
1. **RBAC Roles** — table of 8 roles (clickable rows)
2. **Permissions** — table (empty in Tier 0, shows explanatory message)
3. **Role Permissions** — shows permissions for the clicked role

**System Status** card at top shows database connectivity (green/red badge).

The UI is read-only — no forms, no CRUD.

---

### 5.2 `frontend/assets/js/app.js` — Line-by-Line Explanation

```javascript
const API_BASE = "/api/v1/bootstrap";
```
- Base URL for all API calls. Relative path — works regardless of host/port because the frontend is served by the same FastAPI app.

```javascript
function bootstrapApp() {
    return {
```
- Alpine.js component factory function. Returns an object containing all reactive data and methods.

```javascript
        // State: health check
        health: { loading: true, connected: false },
```
- `loading: true` — shows the spinner initially.
- `connected: false` — defaults to disconnected; updated after the fetch.

```javascript
        // State: roles list
        roles: [],
        rolesLoading: true,
        rolesError: false,
```
- `roles` — array of role objects from the API. Empty until fetched.
- `rolesLoading` / `rolesError` — control which UI template is shown (spinner, error alert, or data table).

```javascript
        // State: permissions list
        permissions: [],
        permissionsLoading: true,
        permissionsError: false,
```
- Same pattern for the permissions panel.

```javascript
        // State: role permissions (interactive)
        selectedRole: null,
        rolePermissions: [],
        rolePermsLoading: false,
        rolePermsError: false,
```
- `selectedRole` — the role object the user clicked (or null).
- `rolePermissions` — permissions for that role (fetched on click).
- `rolePermsLoading` starts `false` (not `true`) because this panel only loads on user interaction.

```javascript
        async init() {
            await Promise.all([
                this.fetchHealth(),
                this.fetchRoles(),
                this.fetchPermissions(),
            ]);
        },
```
- Called by `x-init` when the page loads.
- `Promise.all` — fires all 3 API calls **in parallel** (not sequentially). The page populates as each resolves.

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
- `fetch(...)` — browser Fetch API call to `/api/v1/bootstrap/health`.
- `res.ok` — true if HTTP status is 200–299.
- `data.database === "connected"` — checks the specific field from `HealthResponse`.
- `catch` — any error (network, parse, non-200 status) → show as disconnected.
- `finally` — always hides the loading spinner.

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
- Same try/catch/finally pattern as `fetchHealth`.
- On success, `this.roles` is set to the JSON array — Alpine automatically re-renders the `x-for` loop.

```javascript
        async fetchPermissions() { ... },
```
- Identical pattern for permissions.

```javascript
        async selectRole(role) {
            if (this.selectedRole?.role_master_pk === role.role_master_pk) {
                this.selectedRole = null;
                this.rolePermissions = [];
                return;
            }
```
- **Toggle behavior**: clicking the same role again deselects it.
- `?.` — optional chaining; `selectedRole` may be `null`.

```javascript
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
    };
}
```
- Sets the selected role, clears old permissions, shows spinner.
- Fetches `/api/v1/bootstrap/roles/{uuid}/permissions`.
- In Tier 0, always returns an empty array (no role-permission mappings exist).

---

### 5.3 `frontend/assets/css/style.css` — Explanation

```css
[x-cloak] {
    display: none !important;
}
```
- **Alpine.js cloak directive**: prevents a flash of unstyled content (FOUC).
- Elements with `x-cloak` attribute are hidden until Alpine initializes and removes the attribute.
- Without this, users would briefly see raw template syntax (`{{ }}`, `x-text`) before Alpine renders.

---

## 6. Layer 4 — Automated Tests

### 6.1 Test Infrastructure

| File                   | Purpose                                      |
|------------------------|----------------------------------------------|
| `pytest.ini`           | Test runner configuration                    |
| `tests/__init__.py`    | Package marker                               |
| `tests/conftest.py`    | Shared fixtures (FastAPI TestClient)         |
| `tests/test_bootstrap.py` | 9 integration tests for 4 API contracts  |

### 6.2 How It Works

Tests use FastAPI's `TestClient` (from Starlette), which calls the ASGI app directly — **no HTTP server is started**. The app connects to the **local PostgreSQL** database (not Neon) using the same `api/.env` configuration.

```
pytest process
  └─ TestClient(app)
       └─ FastAPI app (api/main.py)
            └─ psycopg2 pool → local PostgreSQL (nss_erp)
```

The `client` fixture is scoped to the test module — one TestClient instance shared across all tests in a file.

---

### 6.3 `pytest.ini` — Line-by-Line Explanation

**File:** `pytest.ini`

```ini
[pytest]
```
- Section header. Tells pytest this file contains its configuration.

```ini
testpaths = tests
```
- Only look for tests in the `tests/` directory (not in `api/`, `frontend/`, `database/`, etc.).

```ini
python_files = test_*.py
```
- Only files matching `test_*.py` are collected as test modules.

```ini
python_classes = Test*
```
- Only classes starting with `Test` are collected as test classes (e.g. `TestHealth`, `TestRoles`).

```ini
python_functions = test_*
```
- Only functions starting with `test_` are collected as test cases.

```ini
addopts = -v --tb=short
```
- `-v` — verbose output: shows each test name and PASSED/FAILED instead of just dots.
- `--tb=short` — on failure, shows a short traceback (not the full stack).

```ini
markers =
    integration: API tests requiring local PostgreSQL
```
- Registers a custom marker `integration`. Allows running only these tests with `pytest -m integration`.
- Without registering, pytest would show a warning about unknown markers.

---

### 6.4 `tests/__init__.py` — Explanation

**File:** `tests/__init__.py`

```python
# tests package
```
- Makes `tests/` a Python package. Required so pytest can import test modules correctly.
- The comment is just for clarity — the file could be empty.

---

### 6.5 `tests/conftest.py` — Line-by-Line Explanation

**File:** `tests/conftest.py`

```python
import pytest
from fastapi.testclient import TestClient
from api.main import app
```
- `pytest` — the test framework. Provides `@pytest.fixture` and `@pytest.mark`.
- `TestClient` — Starlette's test client, re-exported by FastAPI. Sends HTTP requests to the app without starting a server.
- `app` — the FastAPI application instance from `api/main.py`.

```python
@pytest.fixture(scope="module")
def client():
```
- `@pytest.fixture` — declares `client` as a reusable test fixture.
- `scope="module"` — one TestClient instance is created per test file and shared across all tests in that file. This is more efficient than creating a new client per test (`scope="function"`).

```python
    with TestClient(app) as c:
        yield c
```
- `TestClient(app)` — creates a test client that wraps the FastAPI app.
- `with ... as c` — the context manager triggers the app's lifespan events (startup/shutdown).
- `yield c` — provides the client to test functions. After all tests in the module complete, the `with` block exits and triggers `close_pool()` (the shutdown handler).

**How tests use it:**

```python
def test_something(self, client):  # ← pytest injects the fixture by name
    response = client.get("/api/v1/bootstrap/health")
```

---

### 6.6 `tests/test_bootstrap.py` — Line-by-Line Explanation

**File:** `tests/test_bootstrap.py`

```python
"""
NSS ERP — Tier 0 Bootstrap API tests.

Four integration tests corresponding to the four Tier 0 API contracts:
  1. GET /api/v1/bootstrap/health
  2. GET /api/v1/bootstrap/roles
  3. GET /api/v1/bootstrap/permissions
  4. GET /api/v1/bootstrap/roles/{role_pk}/permissions

These tests run against local PostgreSQL (not Neon).
The database must be bootstrapped with DDL + seed before running.
"""
```
- Module docstring documenting what this file tests and its prerequisites.

```python
import pytest

pytestmark = pytest.mark.integration
```
- `pytestmark` — applies the `integration` marker to **every test** in this file.
- Equivalent to adding `@pytest.mark.integration` on each test individually, but less repetitive.
- Allows running `pytest -m integration` to target these tests specifically.

#### TestHealth

```python
class TestHealth:
    """GET /api/v1/bootstrap/health"""

    def test_health_returns_ok(self, client):
        response = client.get("/api/v1/bootstrap/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
```
- `client.get(...)` — sends a GET request through the TestClient. No actual HTTP — the ASGI app is called directly.
- `response.status_code` — the HTTP status code.
- `response.json()` — parses the response body as JSON.
- Asserts the health endpoint returns 200 with `status="ok"` and `database="connected"`.
- If the local PostgreSQL is down, this test **fails** — by design, it's an integration test.

#### TestRoles

```python
class TestRoles:
    """GET /api/v1/bootstrap/roles"""

    def test_roles_returns_list(self, client):
        response = client.get("/api/v1/bootstrap/roles")
        assert response.status_code == 200
        roles = response.json()
        assert isinstance(roles, list)
        assert len(roles) == 8, f"Expected 8 frozen roles, got {len(roles)}"
```
- Verifies the response is a list of exactly 8 roles (the frozen seed count).
- The custom message `f"Expected 8 frozen roles, got {len(roles)}"` makes failure diagnostics clear.

```python
    def test_roles_have_required_fields(self, client):
        response = client.get("/api/v1/bootstrap/roles")
        roles = response.json()
        required_fields = {
            "role_master_pk", "role_code", "role_name",
            "role_class", "scope_level", "display_order", "is_active",
        }
        for role in roles:
            assert required_fields.issubset(role.keys()), (
                f"Missing fields in role {role.get('role_code', '?')}: "
                f"{required_fields - role.keys()}"
            )
            assert role["is_active"] is True
```
- `required_fields` — a set of the 7 fields defined in `RoleResponse` (minus `description` which is optional).
- `issubset` — checks that every required field is present in each role dict.
- `role["is_active"] is True` — uses `is` (identity check) not `==` (equality check). In JSON, `true` deserializes to Python `True`.
- If a field is missing, the error message names the role and lists which fields are absent.

```python
    def test_roles_include_known_codes(self, client):
        response = client.get("/api/v1/bootstrap/roles")
        codes = {r["role_code"] for r in response.json()}
        expected = {
            "NSS_ERP_ADMIN", "NSS_ERP_AUDITOR", "NSS_ERP_REPORT_VIEWER",
            "NSS_ERP_KENDRA_ADMIN", "NSS_ERP_ANCHALIKA_ADMIN",
            "NSS_ERP_ZILLA_ADMIN", "NSS_ERP_SAKHA_ADMIN",
            "NSS_ERP_PATHA_CHAKRA_ADMIN",
        }
        assert codes == expected, f"Role codes mismatch: {codes ^ expected}"
```
- Set comprehension `{r["role_code"] for r in ...}` — extracts all role_code values.
- `codes == expected` — exact match (no extra, no missing).
- `codes ^ expected` — symmetric difference: shows which codes are in one set but not the other (makes failures diagnostic).

```python
    def test_system_roles_have_nss_wide_scope(self, client):
        response = client.get("/api/v1/bootstrap/roles")
        system_roles = [r for r in response.json() if r["role_class"] == "SYSTEM"]
        assert len(system_roles) == 3
        for role in system_roles:
            assert role["scope_level"] == "NSS-WIDE", (
                f"SYSTEM role {role['role_code']} has scope "
                f"'{role['scope_level']}', expected 'NSS-WIDE'"
            )
```
- Filters to only `SYSTEM`-class roles.
- Verifies there are exactly 3 (ADMIN, AUDITOR, REPORT_VIEWER).
- Each must have `scope_level = "NSS-WIDE"` — enforces the business rule that system roles are organization-wide.

#### TestPermissions

```python
class TestPermissions:
    """GET /api/v1/bootstrap/permissions"""

    def test_permissions_returns_list(self, client):
        response = client.get("/api/v1/bootstrap/permissions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```
- Only checks that the endpoint returns 200 with a list.
- Does NOT assert the list is empty — that would break when permissions are added in later tiers.
- Lightweight: just verifies the endpoint is functional.

#### TestRolePermissions

```python
class TestRolePermissions:
    """GET /api/v1/bootstrap/roles/{role_pk}/permissions"""

    def test_role_permissions_valid_role(self, client):
        roles_response = client.get("/api/v1/bootstrap/roles")
        roles = roles_response.json()
        assert len(roles) > 0, "No roles to test against"
        role_pk = roles[0]["role_master_pk"]
        response = client.get(f"/api/v1/bootstrap/roles/{role_pk}/permissions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```
- **Integration approach**: first fetches the real roles list, then uses an actual `role_master_pk` UUID.
- No hardcoded UUIDs — the test adapts to whatever UUIDs `gen_random_uuid()` generated.
- Verifies the endpoint returns 200 with a list (empty in Tier 0).

```python
    def test_role_permissions_invalid_role(self, client):
        fake_pk = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/bootstrap/roles/{fake_pk}/permissions")
        assert response.status_code == 404
```
- Uses a valid UUID format that doesn't exist in the database.
- Verifies the endpoint returns **404 Not Found** (not 200 with empty list).
- This tests the `HTTPException(status_code=404)` branch in the router.

```python
    def test_role_permissions_invalid_uuid(self, client):
        response = client.get("/api/v1/bootstrap/roles/not-a-uuid/permissions")
        assert response.status_code == 422
```
- `"not-a-uuid"` is not a valid UUID string.
- FastAPI's path parameter validation (`role_pk: UUID`) rejects it with **422 Unprocessable Entity**.
- This tests FastAPI's built-in type validation — no custom code needed.

---

## 7. How to Run Tests

### 7.1 Prerequisites

1. **Local PostgreSQL** running with the `nss_erp` database bootstrapped (DDL + seed — see Section 3)
2. **`api/.env`** configured with valid DB credentials for `nss_db_backend`
3. **Python virtual environment** with dependencies installed

### 7.2 Setup (one-time)

**macOS / Linux:**
```bash
cd /path/to/NSS_ERP

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install app dependencies + test dependencies
pip install -r requirements.txt
pip install pytest httpx
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

### 7.3 Run All Tests

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
tests/test_bootstrap.py::TestHealth::test_health_returns_ok PASSED
tests/test_bootstrap.py::TestRoles::test_roles_returns_list PASSED
tests/test_bootstrap.py::TestRoles::test_roles_have_required_fields PASSED
tests/test_bootstrap.py::TestRoles::test_roles_include_known_codes PASSED
tests/test_bootstrap.py::TestRoles::test_system_roles_have_nss_wide_scope PASSED
tests/test_bootstrap.py::TestPermissions::test_permissions_returns_list PASSED
tests/test_bootstrap.py::TestRolePermissions::test_role_permissions_valid_role PASSED
tests/test_bootstrap.py::TestRolePermissions::test_role_permissions_invalid_role PASSED
tests/test_bootstrap.py::TestRolePermissions::test_role_permissions_invalid_uuid PASSED

9 passed
```

### 7.4 Run Specific Subsets

These commands are the same on all platforms (once the venv is activated):

```bash
# Only integration-marked tests
pytest -m integration

# Only one test file
pytest tests/test_bootstrap.py

# Only one test class
pytest tests/test_bootstrap.py::TestRoles

# Only one test
pytest tests/test_bootstrap.py::TestRoles::test_roles_include_known_codes

# With full traceback on failure
pytest --tb=long

# Quiet mode (dots only)
pytest -q
```

### 7.5 Troubleshooting

| Symptom | Cause | Fix (macOS/Linux) | Fix (Windows) |
|---------|-------|--------------------|---------------|
| `ModuleNotFoundError: No module named 'api'` | Not running from repo root | `cd /path/to/NSS_ERP` | `cd C:\path\to\NSS_ERP` |
| `RuntimeError: Required environment variables not set` | Missing `api/.env` | Create `api/.env` (Section 4.6) | Create `api\.env` (Section 4.6) |
| `psycopg2.OperationalError: connection refused` | PostgreSQL not running | `brew services start postgresql@16` | Start via Services panel or `pg_ctl start -D "C:\Program Files\PostgreSQL\16\data"` |
| `FAILED test_roles_returns_list - assert 0 == 8` | Seed data not loaded | Run seed scripts (Section 3.3) | Run seed scripts (Section 3.3) |
| `ImportError: httpx` | httpx not installed | `pip install httpx` | `pip install httpx` |
| `Activate.ps1 cannot be loaded because running scripts is disabled` | PowerShell execution policy | N/A | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| `'python3' is not recognized` | Python not on PATH | N/A (comes with macOS) | Use `python` instead of `python3`, or add to PATH |

---

## 8. File Tree Summary

```
NSS_ERP/
├── api/
│   ├── .env                    # Local DB credentials (not committed)
│   ├── __init__.py
│   ├── config.py               # Settings from env vars
│   ├── database.py             # psycopg2 connection pool
│   ├── main.py                 # FastAPI app entry point
│   ├── routers/
│   │   ├── __init__.py
│   │   └── bootstrap.py        # 4 Tier 0 endpoints
│   └── schemas/
│       ├── __init__.py
│       └── bootstrap.py        # Pydantic response models
├── database/
│   ├── scripts/
│   │   ├── 00_create_database.sql   # Roles + DB creation
│   │   ├── 01_extensions.sql        # Extensions + nss schema
│   │   └── 04_grant_backend.sql     # SELECT-only for nss_db_backend
│   ├── ddl/
│   │   └── 00_bootstrap/
│   │       ├── 01_role_master.sql
│   │       ├── 02_permission_master.sql
│   │       └── 03_role_permission.sql
│   └── seed/
│       └── 00_bootstrap/
│           ├── 01_permission_master.sql   # (empty)
│           ├── 02_role_master.sql         # 8 frozen roles
│           └── 03_role_permission.sql     # (empty)
├── frontend/
│   ├── index.html              # Bootstrap Verification UI
│   ├── assets/
│   │   ├── css/style.css       # Alpine.js cloak + overrides
│   │   ├── js/app.js           # Alpine.js component
│   │   └── img/nss-logo.png
│   └── README.md
├── tests/
│   ├── __init__.py             # Package marker
│   ├── conftest.py             # TestClient fixture
│   └── test_bootstrap.py       # 9 integration tests
├── pytest.ini                  # Test runner config
├── requirements.txt            # Python dependencies
├── render.yaml                 # Render.com IaC
├── render_build.sh             # Idempotent build + bootstrap
└── .gitignore
```

---

## 9. Vertical Slice Sequence — End to End

The Tier 0 vertical slice follows the project's **Business Rules First → Documentation First → Database First → API First → UI First** design philosophy:

```
Step 1: DDL
  database/scripts/00_create_database.sql    → DB + PostgreSQL roles
  database/scripts/01_extensions.sql         → extensions + nss schema
  database/ddl/00_bootstrap/*.sql            → 3 tables

Step 2: Seed
  database/seed/00_bootstrap/*.sql           → 8 roles (2 files empty)

Step 3: Privileges
  database/scripts/04_grant_backend.sql      → SELECT-only for backend

Step 4: API
  api/config.py                              → env-based settings
  api/database.py                            → connection pool
  api/schemas/bootstrap.py                   → response contracts
  api/routers/bootstrap.py                   → 4 read-only endpoints
  api/main.py                                → mounts router + frontend

Step 5: UI
  frontend/index.html + assets/              → verification dashboard

Step 6: Test
  pytest.ini + tests/                        → 9 integration tests
  Run: pytest from repo root                 → all 9 pass
```

---

## 10. Deployment

Tier 0 is deployed to **Neon.dev** (PostgreSQL) + **Render.com** (application).

- `render_build.sh` handles idempotent DDL + seed on first deploy
- `render.yaml` defines the Render service configuration
- See `docs/03_Solution/architecture/DEPLOYMENT_PROCEDURE.md` for full details

---

## 11. What Tier 0 Does NOT Include

| Intentionally excluded | Rationale                                  |
|------------------------|--------------------------------------------|
| Authentication         | Deferred to Tier 5 (SOL-ARCH-010)          |
| CRUD operations        | Tier 0 is read-only verification           |
| Permission seed data   | Populated progressively per module         |
| Role-permission maps   | Depends on permission catalogue            |
| Mobile app             | Deferred until after Tiers 0-5 (TECH-MOB-001) |
| ORM                    | Raw psycopg2 by design                     |
| Write privileges       | nss_db_backend is SELECT-only in Tier 0    |
