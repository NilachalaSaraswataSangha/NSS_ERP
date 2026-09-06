# database/scripts/

Executable bootstrap/build/validate scripts for the raw-SQL DDL track.
Run from the repository root.

## Execution Order

### macOS / Linux (bash)

```bash
psql -U postgres      -d postgres  -f database/scripts/00_create_database.sql
psql -U postgres      -d nss_erp   -f database/scripts/01_extensions.sql
./database/scripts/02_build.sh
./database/scripts/03_validate.sh
```

### Windows (PowerShell)

```powershell
psql -U postgres      -d postgres  -f database\scripts\00_create_database.sql
psql -U postgres      -d nss_erp   -f database\scripts\01_extensions.sql
.\database\scripts\02_build.ps1
.\database\scripts\03_validate.ps1
```

## Script Reference

| File | Run as | Target DB | Purpose |
|---|---|---|---|
| `00_create_database.sql` | superuser (`postgres`) | `postgres` | Creates `nss_erp` database, `nss_db_owner`/`nss_db_backend` roles, installs `dblink`. Fully idempotent. |
| `01_extensions.sql` | superuser (`postgres`) | `nss_erp` | Installs `pgcrypto`, `pg_trgm`, `btree_gin`, `postgis`. Creates `nss` schema. Grants `nss_db_owner` LOGIN + schema privileges. Idempotent. |
| `02_build.sh` / `.ps1` | `nss_db_owner` | `nss_erp` | Runs all implemented DDL + seed (Bootstrap RBAC, Foundation, Organization). Not idempotent — drop/recreate DB for clean rebuild. |
| `03_validate.sh` / `.ps1` | `nss_db_owner` | `nss_erp` | Post-build checks: table existence, row counts, unique constraints, FK integrity. Run after build; does not execute any DDL/seed. |

Build and validate scripts accept optional args:

- **bash:** `DB_NAME DB_USER DB_HOST DB_PORT` (positional, defaults: `nss_erp nss_db_owner localhost 5432`)
- **PowerShell:** `-DbName -DbUser -DbHost -DbPort` (named, same defaults)

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
