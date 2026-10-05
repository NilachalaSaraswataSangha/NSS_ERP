# NSS ERP — Getting Started

---

## Document Metadata

| Item | Value |
|---|---|
| Document Name | Getting Started |
| Repository Path | docs/03_Solution/architecture/GETTING_STARTED.md |
| Version | 1.8 |
| Status | Active |
| Authority | NSS ERP Architecture |

---

# 1. Prerequisites

- PostgreSQL 14+ (local or Neon.dev)
- Python 3.12+ with pip
- psql CLI (included with PostgreSQL)
- Node.js + npm — **optional**, only needed if you're changing Tailwind/DaisyUI CSS classes.
  `frontend/assets/css/tailwind.min.css` is a committed, generated artifact, so a fresh clone
  runs the app without Node.js installed at all.

---

# 2. Database Setup

## macOS / Linux (bash)

```bash
# 2a. Create database and roles (as superuser)
psql -U postgres -d postgres -f database/scripts/00_create_database.sql

# 2b. Install extensions and create nss schema (as superuser)
psql -U postgres -d nss_erp -f database/scripts/01_extensions.sql

# 2c. Set role passwords + generate api/.env (prompts for each role's password)
./database/scripts/06_setup_env.sh
#     Re-run with --force to overwrite an existing api/.env:
#     ./database/scripts/06_setup_env.sh --force

# 2d. Build all DDL + seed (as nss_db_owner)
./database/scripts/02_build.sh

# 2e. Validate (as nss_db_owner)
./database/scripts/03_validate.sh
```

## Windows (PowerShell)

```powershell
# 2a. Create database and roles (as superuser)
psql -U postgres -d postgres -f database\scripts\00_create_database.sql

# 2b. Install extensions and create nss schema (as superuser)
psql -U postgres -d nss_erp -f database\scripts\01_extensions.sql

# 2c. Set role passwords + generate api\.env
#     Windows does not have 06_setup_env.sh — run the equivalent manually:
psql -U postgres -d postgres -c "ALTER ROLE nss_db_owner PASSWORD 'nssowner';"
psql -U postgres -d postgres -c "ALTER ROLE nss_db_backend PASSWORD 'nssadmin';"
psql -U postgres -d postgres -c "ALTER ROLE nss_db_writer PASSWORD 'nsswriter';"
#     Then create api\.env (see Section 3 below) or copy from a teammate.

# 2d. Build all DDL + seed (as nss_db_owner)
.\database\scripts\02_build.ps1

# 2e. Validate (as nss_db_owner)
.\database\scripts\03_validate.ps1
```

> **Never commit real passwords.** The `.env` file is in `.gitignore`. Use `.pgpass` (macOS/Linux)
> or `%APPDATA%\postgresql\pgpass.conf` (Windows) for passwordless `psql` connections, or set
> `PGPASSWORD` in your shell session. `06_setup_env.sh` handles all of this for local dev.

---

# 3. API Setup

```bash
# Install Python dependencies
# macOS / Linux:
python3 -m pip install -r requirements.txt
# Windows:
#   py -m pip install -r requirements.txt
```

**`api/.env` is already generated** by Step 2c (`06_setup_env.sh`). It contains all
required variables: database credentials for both read and write pools, and a
randomly generated JWT secret. No manual editing needed for local dev.

If you're on **Windows** or need to create the file manually:

```powershell
@"
DB_NAME=nss_erp
DB_USER=nss_db_backend
DB_PASSWORD=nssadmin
DB_HOST=localhost
DB_PORT=5432
DB_WRITE_USER=nss_db_writer
DB_WRITE_PASSWORD=nsswriter
JWT_SECRET_KEY=replace_with_a_random_64char_hex_string
"@ | Out-File -Encoding utf8 api\.env
```

> **Generate a JWT secret** with `python3 -c "import secrets; print(secrets.token_hex(32))"` and
> paste the output as `JWT_SECRET_KEY`. Never reuse this across environments.

---

# 3b. Frontend CSS (optional — only if editing Tailwind/DaisyUI classes)

```bash
npm install
npm run css:build   # one-shot rebuild of frontend/assets/css/tailwind.min.css
npm run css:watch   # rebuild on every file change, for active frontend dev
```

Skip this section if you're not touching `frontend/*.html` or `frontend/assets/js/*.js` class
names — the built CSS is already committed. `render_build.sh` runs this build automatically on
every deploy.

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
| `http://localhost:8001/` | Redirects to `/login` |
| `http://localhost:8001/login` | Login (Authentication) |
| `http://localhost:8001/register` | Self-Registration |
| `http://localhost:8001/forgot-password` | **No such page, by design** — forgot/reset-password is inline on `/login`; `POST /api/v1/auth/forgot-password`/`reset-password` back it |
| `http://localhost:8001/dashboard` | Member Dashboard (post-login landing page) |
| `http://localhost:8001/admin` | Admin console (Users, Create User/Sangha-Sevi/Organization, Organizations, Assign Sakhas, Registration Approvals, Geo Approvals, Person/Member Directory, Organization Hierarchy, Org Dashboard, Reference Data, Geography, System Settings) |
| `http://localhost:8001/docs` | Swagger UI (OpenAPI) |
| `http://localhost:8001/api/v1/` | API endpoints |

The six standalone Tier 0-4 verification pages (`/bootstrap`, `/foundation`, `/organization`,
`/person`, `/family`, `/membership`) have been retired — their functionality now lives inside
`/admin` and `/dashboard` (see `frontend/README.md`). See `api/README.md` for the full
per-router endpoint list and security-middleware detail.

---

# 5. Run Tests

```bash
# macOS / Linux:
python3 -m pytest tests/ -v

# Windows:
py -m pytest tests/ -v
```

**921 test functions (1092 collected items)**, split across four directories: 567 in `tests/api/` (17 files — routers +
integration coverage), 43 in `tests/db/` (cross-module data integrity, credential-schema and festival-schema
invariants), 62 in `tests/security/` (auth-gating/401/403/RBAC + CSP/rate-limit/CORS
assertions), and 249 in `tests/ui/` (23 Playwright browser-test files — needs Playwright
browsers installed and a running app).
`test_kumari_transition_has_event` and `TestChildrenStats` gracefully `pytest.skip()` against
the seed-less database rather than fail. See `tests/README.md` for the full per-file test
inventory.

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

# 7e. Set role passwords + regenerate api/.env
./database/scripts/06_setup_env.sh --force

# 7f. Full build (DDL + seed, all phases)
./database/scripts/02_build.sh

# 7g. Validate
./database/scripts/03_validate.sh
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

# 7e. Set role passwords + create api\.env
#     Windows: run ALTER ROLE manually (see Section 2 Windows steps)
#     and create api\.env manually (see Section 3).

# 7f. Full build (DDL + seed, all phases)
.\database\scripts\02_build.ps1

# 7g. Validate
.\database\scripts\03_validate.ps1
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
| 1 | Foundation DDL | 13 tables, incl. the 5-level geography chain (`country` → `state` → `district` → `city_village` → `postal_code`) and `festival_master`/`festival_calendar_date`; `system_event_log` (14th) is created separately in Phase 14 |
| 2 | Foundation Seed | Master categories, master data, geography, sequences, settings |
| 3 | Organization DDL | 1 table (includes short_code column, performance indexes) |
| 4 | Organization Seed | Base organizations, Sakha postal codes, 175 Sakha branches |
| 5 | Person DDL | 2 tables |
| 6 | Family DDL | 6 tables (includes performance indexes) |
| 7 | Membership DDL | 14 tables (includes performance indexes) |
| 8 | *(reserved — no demo data)* | |
| 9 | Grant Backend | Read-only access for `nss_db_backend` |
| 10 | Authentication DDL | 5 tables (`user_account`, `password_history`, `registration_claim`, `password_reset_token`, `user_session`) |
| 11 | Administration DDL | 2 tables (`user_role`, `admin_scope`) |
| 12 | Grant Writer | Write access for `nss_db_writer` (auth + admin tables only) |
| 13 | Admin Bootstrap | Seed NSSAdmin user account (runtime bootstrap via `bootstrap_admin.py`) |
| 14 | Audit DDL | `system_event_log` table + `fn_audit_trigger()` attached to every `nss.*` table |

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
