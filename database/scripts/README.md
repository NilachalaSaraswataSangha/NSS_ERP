# database/scripts/

Executable bootstrap/build/validate scripts for the raw-SQL DDL track.
Run from the repository root.

> **Getting started?** See the root `README.md` → **Getting Started** section for the full
> step-by-step setup sequence (database → API → tests). This file is the detailed script
> reference.

## Script Reference

| File | Run as | Target DB | Purpose |
|---|---|---|---|
| `00_create_database.sql` | superuser (`postgres`) | `postgres` | Creates `nss_erp` database, `nss_db_owner`/`nss_db_backend` roles (both with LOGIN, no password). Installs `dblink`. Fully idempotent. |
| `01_extensions.sql` | superuser (`postgres`) | `nss_erp` | Installs `pgcrypto`, `pg_trgm`, `btree_gin`, `postgis`. Creates `nss` schema owned by `nss_db_owner`. Idempotent. |
| `02_build.sh` / `.ps1` | `nss_db_owner` | `nss_erp` | Runs all implemented DDL + seed (Bootstrap RBAC, Foundation, Organization). Not idempotent — drop/recreate DB for clean rebuild. |
| `03_validate.sh` / `.ps1` | `nss_db_owner` | `nss_erp` | Post-build checks: table existence, row counts, unique constraints, FK integrity. Run after build; does not execute any DDL/seed. |
| `04_grant_backend.sql` | `nss_db_owner` | `nss_erp` | Grants `nss_db_backend` read-only access: `USAGE` on `nss` schema, `SELECT` on all tables, `ALTER DEFAULT PRIVILEGES` for future tables. Idempotent. |

Build and validate scripts accept optional args:

- **bash:** `DB_NAME DB_USER DB_HOST DB_PORT` (positional, defaults: `nss_erp nss_db_owner localhost 5432`)
- **PowerShell:** `-DbName -DbUser -DbHost -DbPort` (named, same defaults)

## Build Phases (internal execution order)

The build script (`02_build.sh` / `.ps1`) executes DDL and seed files in the frozen
SOL-ARCH-011 phase order. Authority: SOL-ARCH-010 (DDL Creation Order), SOL-ARCH-011
(Bootstrap Architecture).

### Phase 0 — Bootstrap RBAC (SOL-ARCH-011 §4)

| Step | File | Table | Depth |
|-----:|------|-------|------:|
| DDL | `ddl/00_bootstrap/01_role_master.sql` | `role_master` | 0 |
| DDL | `ddl/00_bootstrap/02_permission_master.sql` | `permission_master` | 0 |
| DDL | `ddl/00_bootstrap/03_role_permission.sql` | `role_permission` | 1 |
| Seed | `seed/00_bootstrap/01_permission_master.sql` | *(empty — catalogue not frozen)* | — |
| Seed | `seed/00_bootstrap/02_role_master.sql` | 8 frozen roles | — |
| Seed | `seed/00_bootstrap/03_role_permission.sql` | *(empty — depends on permissions)* | — |

### Phase 1 — Foundation DDL (12 tables, Depths 0–4)

| Step | File | Table | Depth |
|-----:|------|-------|------:|
| DDL | `ddl/01_foundation/02_master_category.sql` | `master_category` | 0 |
| DDL | `ddl/01_foundation/03_system_setting.sql` | `system_setting` | 0 |
| DDL | `ddl/01_foundation/04_id_sequence_master.sql` | `id_sequence_master` | 0 |
| DDL | `ddl/01_foundation/05_country.sql` | `country` | 0 |
| DDL | `ddl/01_foundation/06_document_master.sql` | `document_master` | 0 |
| DDL | `ddl/01_foundation/07_field_change_log.sql` | `field_change_log` | 0 |
| DDL | `ddl/01_foundation/08_master_data.sql` | `master_data` | 1 |
| DDL | `ddl/01_foundation/09_state.sql` | `state` | 1 |
| DDL | `ddl/01_foundation/10_district.sql` | `district` | 2 |
| DDL | `ddl/01_foundation/11_city_village.sql` | `city_village` | 3 |
| DDL | `ddl/01_foundation/12_postal_code.sql` | `postal_code` | 2 |
| DDL | `ddl/01_foundation/13_city_village_postal_code_map.sql` | `city_village_postal_code_map` | 4 |

### Phase 2 — Foundation Seed Data

| Step | File | Seeds |
|-----:|------|-------|
| Seed | `seed/01_foundation/01_master_category.sql` | 12 master categories (incl. ORGANIZATION_TYPE, unified STATUS) |
| Seed | `seed/01_foundation/02_master_data.sql` | Master data rows (incl. 10 org types + 13 unified statuses) |
| Seed | `seed/01_foundation/03_id_sequence_master.sql` | ID sequence definitions |
| Seed | `seed/01_foundation/04_country.sql` | Countries |
| Seed | `seed/01_foundation/05_state.sql` | States |
| Seed | `seed/01_foundation/06_district.sql` | Districts |
| Seed | `seed/01_foundation/07_system_setting.sql` | System settings |
| Seed | `seed/01_foundation/08_postal_code.sql` | Postal codes |

### Phase 3 — Organization DDL (1 table, Depth 1)

Organization type and status are now stored in Foundation `master_data`
(category `ORGANIZATION_TYPE` for types, unified `STATUS` for lifecycle
statuses). The standalone `organization_type_master` and
`organization_status_master` tables are retired.

| Step | File | Table | Depth |
|-----:|------|-------|------:|
| DDL | `ddl/02_organization/03_organization.sql` | `organization` | 1 |

### Phase 4 — Organization Seed Data

| Step | File | Seeds |
|-----:|------|-------|
| Seed | `seed/02_organization/03_organization.sql` | 3 organizations (resolves type/status via master_data) |

### Not executed (future phases)

- `ddl/03_person/` — superseded prototype, awaiting rewrite
- `seed/03_person/` — superseded prototype
- Pass 2 audit-actor FK constraints (deferred until `sangha_sevi` exists)
- All remaining modules (Authentication, Administration Phase 4+, Governance, etc.)

## Role Naming Convention

| Pattern | Layer | Examples |
|---|---|---|
| `nss_db_*` | PostgreSQL infrastructure | `nss_db_owner`, `nss_db_backend` |
| `NSS_ERP_*` | Application RBAC (`role_master`) | `NSS_ERP_ADMIN`, `NSS_ERP_KENDRA_ADMIN` |

## Cross-Platform Principle (Frozen)

The SQL DDL, seed data, and application code are **identical across platforms**. `.sh`
(macOS/Linux) and `.ps1` (Windows) scripts are developer/operational wrappers only — they
must not contain different business logic, database statements, or schema definitions.
Platform-specific behaviour is limited to shell mechanics (variable substitution, exit
codes, colour output). Both wrappers execute the same DDL and seed files in the same order.

## Starting the API

See root `README.md` → **Getting Started** → Steps 2–4 for API setup, startup, and testing.
