# NSS ERP — Getting Started

---

## Document Metadata

| Item | Value |
|---|---|
| Document Name | Getting Started |
| Repository Path | docs/03_Solution/architecture/GETTING_STARTED.md |
| Version | 1.0 |
| Status | Active |
| Authority | NSS ERP Architecture |

---

# 1. Prerequisites

- PostgreSQL 14+ (local or Neon.dev)
- Python 3.12+ with pip
- psql CLI (included with PostgreSQL)

---

# 2. Database Setup

## macOS / Linux (bash)

```bash
# 2a. Create database and roles (as superuser)
psql -U postgres -d postgres -f database/scripts/00_create_database.sql

# 2b. Set passwords for both roles (as superuser)
psql -U postgres -d postgres -c "ALTER ROLE nss_db_owner PASSWORD 'your_password_here';"
psql -U postgres -d postgres -c "ALTER ROLE nss_db_backend PASSWORD 'your_password_here';"

# 2c. Install extensions and create nss schema (as superuser)
psql -U postgres -d nss_erp -f database/scripts/01_extensions.sql

# 2d. Build all DDL + seed (as nss_db_owner)
./database/scripts/02_build.sh

# 2e. Validate (as nss_db_owner)
./database/scripts/03_validate.sh

# 2f. Grant backend role read-only access (as nss_db_owner)
# Note: 02_build.sh already runs this as its Phase 9 — this manual step is
# redundant after a successful build, but 04_grant_backend.sql is idempotent
# (GRANT statements are safe to re-run), so re-running it here is harmless.
psql -U nss_db_owner -d nss_erp -f database/scripts/04_grant_backend.sql
```

## Windows (PowerShell)

```powershell
# 2a. Create database and roles (as superuser)
psql -U postgres -d postgres -f database\scripts\00_create_database.sql

# 2b. Set passwords for both roles (as superuser)
psql -U postgres -d postgres -c "ALTER ROLE nss_db_owner PASSWORD 'your_password_here';"
psql -U postgres -d postgres -c "ALTER ROLE nss_db_backend PASSWORD 'your_password_here';"

# 2c. Install extensions and create nss schema (as superuser)
psql -U postgres -d nss_erp -f database\scripts\01_extensions.sql

# 2d. Build all DDL + seed (as nss_db_owner)
.\database\scripts\02_build.ps1

# 2e. Validate (as nss_db_owner)
.\database\scripts\03_validate.ps1

# 2f. Grant backend role read-only access (as nss_db_owner)
# Note: 02_build.ps1 already runs this as its Phase 9 — this manual step is
# redundant after a successful build, but 04_grant_backend.sql is idempotent
# (GRANT statements are safe to re-run), so re-running it here is harmless.
psql -U nss_db_owner -d nss_erp -f database\scripts\04_grant_backend.sql
```

> **Never commit real passwords.** Use `.pgpass` (macOS/Linux) or `%APPDATA%\postgresql\pgpass.conf`
> (Windows) for passwordless `psql` connections, or set `PGPASSWORD` in your shell session.

---

# 3. API Setup

```bash
# Install Python dependencies
# macOS / Linux:
python3 -m pip install -r requirements.txt
# Windows:
#   py -m pip install -r requirements.txt
```

Create `api/.env` with the `nss_db_backend` password from Step 2b:

**macOS / Linux:**
```bash
cat > api/.env << 'EOF'
DB_NAME=nss_erp
DB_USER=nss_db_backend
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
EOF
```

**Windows (PowerShell):**
```powershell
@"
DB_NAME=nss_erp
DB_USER=nss_db_backend
DB_PASSWORD=your_password_here
DB_HOST=localhost
DB_PORT=5432
"@ | Out-File -Encoding utf8 api\.env
```

---

# 4. Start the API

```bash
# macOS / Linux:
python3 -m uvicorn api.main:app --reload --port 8001

# Windows:
py -m uvicorn api.main:app --reload --port 8001
```

**URLs:**

| URL | What |
|-----|------|
| `http://localhost:8001/` | Bootstrap Verification UI |
| `http://localhost:8001/foundation` | Foundation Verification UI |
| `http://localhost:8001/organization` | Organization Verification UI |
| `http://localhost:8001/person` | Person Verification UI |
| `http://localhost:8001/family` | Family Verification UI |
| `http://localhost:8001/membership` | Membership Verification UI |
| `http://localhost:8001/docs` | Swagger UI (OpenAPI) |
| `http://localhost:8001/api/v1/` | API endpoints |

See `api/README.md` for the full per-tier endpoint list and security-middleware detail.

---

# 5. Run Tests

```bash
# macOS / Linux:
python3 -m pytest tests/ -v

# Windows:
py -m pytest tests/ -v
```

**363 tests total:** 21 (Tier 0 Bootstrap) + 59 (Tier 1 Foundation) + 64 (Tier 2 Organization) +
61 (Tier 3 Person) + 8 (Security Middleware) + 51 (Tier 4 Family) + 99 (Tier 4 Membership). See
`tests/README.md` for the per-file test inventory.

---

# 6. Script Reference

See `database/scripts/README.md` for detailed script reference (what each script does, build
phases, role naming conventions, cross-platform principles).

---

# 7. Database Rebuild (Clean Slate)

The build script (`02_build.sh` / `02_build.ps1`) is idempotent for re-runs (it
skips tables/rows that already exist). However, if you need a **clean rebuild** —
for example after schema changes, seed data edits, or switching branches — you must
drop and recreate the database.

## Full Rebuild Procedure

### macOS / Linux (bash)

```bash
# 7a. Stop the API server (if running) and terminate stale connections
#     Stale psql sessions or uvicorn connection pools will block the drop.
psql -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'nss_erp' AND pid <> pg_backend_pid();"

# 7b. Drop the existing database (as superuser)
#     WARNING: This destroys ALL data in nss_erp.
psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS nss_erp;"

# 7c. Recreate database and roles (idempotent — roles survive the drop)
psql -U postgres -d postgres -f database/scripts/00_create_database.sql

# 7d. Reinstall extensions and recreate nss schema
psql -U postgres -d nss_erp -f database/scripts/01_extensions.sql

# 7e. Full build (DDL + seed, all phases)
./database/scripts/02_build.sh

# 7f. Validate
./database/scripts/03_validate.sh

# 7g. Grant backend read-only access
# Note: already run as Phase 9 inside 02_build.sh — safe to re-run (idempotent).
psql -U nss_db_owner -d nss_erp -f database/scripts/04_grant_backend.sql
```

### Windows (PowerShell)

```powershell
# 7a. Stop the API server (if running) and terminate stale connections
#     Stale psql sessions or uvicorn connection pools will block the drop.
psql -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'nss_erp' AND pid <> pg_backend_pid();"

# 7b. Drop the existing database (as superuser)
#     WARNING: This destroys ALL data in nss_erp.
psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS nss_erp;"

# 7c. Recreate database and roles (idempotent -- roles survive the drop)
psql -U postgres -d postgres -f database\scripts\00_create_database.sql

# 7d. Reinstall extensions and recreate nss schema
psql -U postgres -d nss_erp -f database\scripts\01_extensions.sql

# 7e. Full build (DDL + seed, all phases)
.\database\scripts\02_build.ps1

# 7f. Validate
.\database\scripts\03_validate.ps1

# 7g. Grant backend read-only access
# Note: already run as Phase 9 inside 02_build.ps1 — safe to re-run (idempotent).
psql -U nss_db_owner -d nss_erp -f database\scripts\04_grant_backend.sql
```

## When to Rebuild

| Scenario | Action |
|---|---|
| DDL schema change (new column, altered constraint) | Full rebuild required |
| Seed data edit (new rows, changed values) | Full rebuild required |
| New DDL file added to build script | Full rebuild required |
| Branch switch with different schema state | Full rebuild required |
| API code change only (no DB changes) | No rebuild needed — restart uvicorn |
| New test added (no DB changes) | No rebuild needed |

## Build Phases (execution order)

The build script executes in this order. All phases run within a
single `02_build.sh` / `02_build.ps1` invocation:

| Phase | Module | What |
|------:|--------|------|
| 0 | Bootstrap RBAC | 3 tables + seed (roles, permissions) |
| 1 | Foundation DDL | 12 tables |
| 2 | Foundation Seed | Master categories, master data, geography, sequences, settings |
| 3 | Organization DDL | 1 table |
| 4 | Organization Seed | Base organizations |
| 5 | Person DDL | 2 tables |
| 6 | Family DDL | 4 tables |
| 7 | Membership DDL | 12 tables |
| 8 | Tier 4 Verification Seed | Test organizations, persons, families, memberships |
| 9 | Grant Backend | Read-only access for `nss_db_backend` |

## Troubleshooting

**"database nss_erp is being accessed by other users"**

Close all psql sessions and stop the API server before dropping:

```bash
# macOS / Linux:
psql -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'nss_erp' AND pid <> pg_backend_pid();"
psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS nss_erp;"
```

```powershell
# Windows:
psql -U postgres -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'nss_erp' AND pid <> pg_backend_pid();"
psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS nss_erp;"
```

**Build fails mid-way**

The build aborts on the first real error (non-idempotent failures). Fix the
failing SQL file, then run a full rebuild from Step 7a — partial rebuilds on a
broken schema are not supported.

---

# End of Document
