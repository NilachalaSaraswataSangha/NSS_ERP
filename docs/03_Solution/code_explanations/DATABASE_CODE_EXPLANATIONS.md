# NSS ERP — Database Code Explanations

| Field       | Value                                                                     |
|-------------|----------------------------------------------------------------------------|
| Document    | DATABASE_CODE_EXPLANATIONS                                               |
| Version     | 1.0                                                                       |
| Scope       | All SQL DDL, seed, and build/validate scripts under `database/`          |
| Status      | Complete                                                                  |

---

## 1. Purpose of this document

This is a file-by-file, line-by-line companion to every hand-written SQL/shell/PowerShell
artifact under `database/`. It exists at a different altitude than the documents it sits
alongside:

- `database/README.md` covers **execution order** (bootstrap sequence, phase table, module
  implementation status) and **what to run**, not what each statement inside a file does.
- `database/ddl/*/README.md` and `database/seed/*/README.md` are **per-folder summaries** —
  one paragraph per file, not column-by-column detail.
- This document is the **exhaustive walkthrough**: every column, every type, every constraint,
  every index, and — for seed files — the exact row count and representative data, for every
  file in `database/`.

Use `database/README.md` to know *when* to run a file and in what order. Use this document to
know *exactly what happens* when it runs.

**The build order, top to bottom — read this first if you're new to the codebase.** Every file
below is explained in exactly this sequence, because each phase's tables must exist before the
next phase's foreign keys can reference them:

```
database/scripts/00_create_database.sql   (superuser)  → creates nss_erp DB + the two
database/scripts/01_extensions.sql        (superuser)     PostgreSQL roles + the nss schema
                    │
                    ▼
database/scripts/02_build.sh / .ps1  (as nss_db_owner) — runs every DDL + seed file below,
                    │                                     in this exact order, via psql
                    ▼
   Bootstrap (Tier 0)         ddl/00_bootstrap/*.sql  →  seed/00_bootstrap/*.sql
   (3 tables)                 role_master, permission_master, role_permission
                    │
                    ▼
   Foundation (Tier 1)        ddl/01_foundation/*.sql →  seed/01_foundation/*.sql
   (12 tables)                master_category…city_village_postal_code_map
                    │
                    ▼
   Organization (Tier 2)      ddl/02_organization/*.sql → seed/02_organization/*.sql
   (3 tables)                 organization_type_master, organization_status_master,
                    │         organization
                    ▼
database/scripts/03_validate.sh / .ps1  (as nss_db_owner) — row-count/FK-integrity checks
database/scripts/04_grant_backend.sql   (as nss_db_owner) — grants nss_db_backend SELECT-only
                    │                                        access, needed before the API
                    ▼                                        can connect at all
The FastAPI app (see API_CODE_EXPLANATIONS.md) can now query nss.* through nss_db_backend

   Person (superseded prototype, ddl/03_person/ + seed/03_person/) — never run by
   02_build.sh; explained fully below anyway since it's still code in the repo, but
   every section for it says so.
```

Scope note: `database/ddl/03_person/` and `database/seed/03_person/` are a **superseded
prototype** — not executed by `database/scripts/02_build.sh`/`02_build.ps1`, kept only for
reference (see `database/ddl/03_person/README.md` and `database/README.md` → "Superseded
Artifacts"). They are still explained fully below because they are still code in the
repository, but every section for them opens with an explicit supersession notice.

---

## 2. Files

### database/scripts/00_create_database.sql

**Requirement**

Run once, by a PostgreSQL **superuser**, against the `postgres` database. This is the very
first script in the bootstrap sequence — before it runs, neither the `nss_erp` database nor
the `nss_db_owner`/`nss_db_backend` roles exist, so nothing else in `database/` can execute.
Without this file: there is no database to connect to, no owner role to run DDL as, and no
backend role for the FastAPI app to authenticate as. It is intentionally idempotent (safe to
re-run) because it uses existence checks before every `CREATE`.

**Line-by-line explanation**

```sql
CREATE EXTENSION IF NOT EXISTS dblink;
```

Installs the `dblink` extension in the `postgres` database. This is required because `CREATE
DATABASE` cannot be executed inside a transaction block (and top-level `DO $$ ... $$` blocks are
implicitly transactional), so the script uses `dblink_exec` to open a *separate* connection back
to the server and issue `CREATE DATABASE` there, outside the enclosing block's transaction.

```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'nss_db_owner'
    ) THEN
        CREATE ROLE nss_db_owner
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
        RAISE NOTICE 'Role nss_db_owner created (LOGIN, no password — set one before use).';
    ELSE
        ALTER ROLE nss_db_owner LOGIN;
        RAISE NOTICE 'Role nss_db_owner already exists — ensured LOGIN.';
    END IF;
END
$$;
```

`DO $$ ... $$` block #1 creates the `nss_db_owner` role. It checks `pg_catalog.pg_roles` for an
existing row with `rolname = 'nss_db_owner'`. If absent, `CREATE ROLE nss_db_owner LOGIN
NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;` creates a login role that is explicitly **not** a
superuser, cannot create databases or other roles, and does not automatically inherit privileges
of roles it might later be granted membership in. This is the DDL/schema-owning role (distinct
from the ERP application role `NSS_ERP_ADMIN`, which is a row in `role_master`, not a PostgreSQL
role — see the naming-convention comment block at the top of the file). If the role is already
present, `ALTER ROLE nss_db_owner LOGIN;` idempotently ensures LOGIN is set even if the role
pre-existed from an older script version. No password is set here — `RAISE NOTICE` reminds the
operator to set one via `ALTER ROLE ... PASSWORD '...'` afterward.

```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'nss_db_backend'
    ) THEN
        CREATE ROLE nss_db_backend
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
        RAISE NOTICE 'Role nss_db_backend created (LOGIN, no password — set one before use).';
    ELSE
        ALTER ROLE nss_db_backend LOGIN;
        RAISE NOTICE 'Role nss_db_backend already exists — ensured LOGIN.';
    END IF;
END
$$;
```

`DO $$ ... $$` block #2 creates `nss_db_backend` with the identical existence-check /
`CREATE ROLE ... LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT` / `ALTER ROLE ... LOGIN`
pattern. This is the runtime role the FastAPI app connects as.

```sql
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_database WHERE datname = 'nss_erp'
    ) THEN
        PERFORM dblink_exec(
            'dbname=postgres host=localhost port=5432 user=postgres password=root',
            'CREATE DATABASE nss_erp OWNER nss_db_owner'
        );
        RAISE NOTICE 'Database nss_erp created.';
    ELSE
        RAISE NOTICE 'Database nss_erp already exists — skipping.';
    END IF;
END
$$;
```

`DO $$ ... $$` block #3 creates the `nss_erp` database. It checks `pg_database` for `datname =
'nss_erp'`. If absent, it calls `dblink_exec('dbname=postgres host=localhost port=5432
user=postgres password=root', 'CREATE DATABASE nss_erp OWNER nss_db_owner')`. The connection
string is hardcoded to `localhost:5432` with a **local-dev placeholder password `root`** for the
`postgres` superuser — `dblink` does not inherit the invoking session's authentication, so this
must be edited before running against any shared/non-local environment (called out explicitly in
both this file's header comment and `database/README.md`). If the database is already present,
it just `RAISE NOTICE`s and skips — idempotent.

```sql
GRANT CONNECT ON DATABASE nss_erp TO nss_db_backend;
```

The only privilege granted in this file; table-level grants happen later in
`04_grant_backend.sql`, after tables exist.

---

### database/scripts/01_extensions.sql

**Requirement**

Run once, by a PostgreSQL **superuser**, against the `nss_erp` database, immediately after
`00_create_database.sql`. Installs the PostgreSQL extensions the Foundation DDL depends on and
creates the `nss` schema that every table in the project lives in. Without this file:
`gen_random_uuid()` (used as the default for every `_pk` column in every table) does not exist,
none of the `gin_trgm_ops` trigram indexes used throughout Foundation/Organization DDL can be
created, and there is no `nss` schema for any `CREATE TABLE nss.*` statement to target.

**Line-by-line explanation**

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
CREATE EXTENSION IF NOT EXISTS postgis;
```

`pgcrypto` provides `gen_random_uuid()`, used as the `DEFAULT` for every UUID surrogate primary
key across the schema. `pg_trgm` is trigram indexing, used for the `GIN (... gin_trgm_ops)`
fuzzy/partial-text-search indexes (e.g. `master_data.value_name`, `state.state_name`,
`district.district_name`, `city_village.city_village_name`, `postal_code.post_office_name`,
`organization.organization_name`). `btree_gin` allows GIN indexes over ordinary scalar types
(not just arrays/tsvector), enabling future composite GIN indexes that mix trigram and scalar
columns. `postgis` adds geospatial types/functions — not yet consumed by any table
(`organization.latitude`/`longitude` use plain `NUMERIC(10,7)`, not a PostGIS `geometry` column)
— installed ahead of need.

```sql
CREATE SCHEMA IF NOT EXISTS nss;
ALTER SCHEMA nss OWNER TO nss_db_owner;
ALTER DATABASE nss_erp SET search_path TO nss, public;
GRANT ALL ON SCHEMA nss TO nss_db_owner;
```

`CREATE SCHEMA IF NOT EXISTS nss;` is the single schema all application tables live in (never
`public`, which is reserved for extensions per this file's own comment). `ALTER SCHEMA nss OWNER
TO nss_db_owner;` makes `nss_db_owner` the schema owner, so it can subsequently `CREATE TABLE`
inside it without additional grants. `ALTER DATABASE nss_erp SET search_path TO nss, public;`
sets the *database-level* default `search_path`, so any new session connecting to `nss_erp`
resolves unqualified table names against `nss` first, then `public`, without each client having
to `SET search_path` explicitly. `GRANT ALL ON SCHEMA nss TO nss_db_owner;` is an explicit
schema-level privilege grant (`CREATE`/`USAGE`) reinforcing ownership from the `ALTER SCHEMA`
statement above.

---

### database/scripts/02_build.sh + database/scripts/02_build.ps1

**Requirement**

The single command that builds the entire currently-implemented schema (Bootstrap RBAC +
Foundation + Organization: 18 tables + seed data) in the exact phase order defined by
`database/README.md`'s "Execution Order" table. Without this pair, an operator would have to
manually run 26 individual `psql -f` commands in the correct dependency order by hand, with no
fail-fast behavior — a single missed or reordered file would either error out obscurely (FK to
a table that doesn't exist yet) or, worse, silently succeed against a half-built schema. It
explicitly does **not** run `database/ddl/03_person/` (superseded prototype) or apply the
deferred Pass 2 audit-actor FK constraints.

**Shared logic (both scripts)**

Both accept the same four optional parameters — `DB_NAME` (default `nss_erp`), `DB_USER`
(default `nss_db_owner`), `DB_HOST` (default `localhost`), `DB_PORT` (default `5432`). The
walkthrough below shows `02_build.sh`; the PowerShell version (`02_build.ps1`) is mechanically
equivalent — same files, same order, same behavior — see the platform-differences table after
the walkthrough for exactly how each mechanic is re-expressed in PowerShell syntax.

```bash
set -euo pipefail

DB_NAME="${1:-nss_erp}"
DB_USER="${2:-nss_db_owner}"
DB_HOST="${3:-localhost}"
DB_PORT="${4:-5432}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DDL_BASE="${REPO_ROOT}/database/ddl"
SEED_BASE="${REPO_ROOT}/database/seed"

if [ -z "${PGPASSWORD:-}" ]; then
    read -rsp "Password for ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}: " PGPASSWORD
    echo ""
    export PGPASSWORD
fi

PSQL="psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -v ON_ERROR_STOP=1"
```

`set -euo pipefail` is strict mode. The four parameters resolve from positional arguments with
bash parameter-expansion defaults. `SCRIPT_DIR`/`REPO_ROOT`/`DDL_BASE`/`SEED_BASE` resolve
absolute paths regardless of the caller's working directory. The password block prompts once for
a password if `PGPASSWORD` isn't already set in the environment, then exports it so every
subsequent `psql` invocation reuses it without re-prompting. `PSQL` bakes `-v ON_ERROR_STOP=1`
into every invocation, which makes `psql` itself halt a given file's script on the first SQL
error inside that file.

```bash
run_sql() {
    local label="$1"
    local file="$2"
    local output
    total=$((total + 1))
    if output=$(${PSQL} -f "${file}" 2>&1); then
        echo -e "  ${GREEN}[OK]${NC}   ${label}"
    else
        echo -e "  ${RED}[FAIL]${NC} ${label}"
        echo -e "  ${RED}Error:${NC}"
        echo "${output}" | sed 's/^/         /'
        failed=$((failed + 1))
        echo -e "  ${RED}Aborting — fix the above error before continuing.${NC}"
        exit 1
    fi
}
```

The `run_sql` helper (`Invoke-Sql` in PowerShell) invokes `psql ... -f <file>`, prints a colored
`[OK]`/`[FAIL]` line per file, and — critically — **aborts the entire script on the first
failure** (`exit 1` immediately, no attempt to continue past a broken statement).

```bash
FOUNDATION_DDL=(
    "master_category|02_master_category.sql"
    "system_setting|03_system_setting.sql"
    ...
    "city_village_postal_code_map|13_city_village_postal_code_map.sql"
)
for entry in "${FOUNDATION_DDL[@]}"; do
    label="${entry%%|*}"
    file="${entry##*|}"
    run_sql "${label}" "${DDL_BASE}/01_foundation/${file}"
done
```

Files execute in exactly this order, matching `database/README.md`:

- **Phase 0** — Bootstrap RBAC DDL (`01_role_master.sql`, `02_permission_master.sql`,
  `03_role_permission.sql`), then Bootstrap RBAC seed (same three files' `seed/` counterparts,
  same order).
- **Phase 1** — Foundation DDL, 12 files in dependency order (`02_master_category.sql` through
  `13_city_village_postal_code_map.sql`), driven by the label/file array shown above so the
  runner and its printed label stay in sync.
- **Phase 2** — Foundation seed, 8 files in dependency order (categories → data → sequences →
  country → state → district → settings → postal codes).
- **Phase 3** — Organization DDL, 3 files (type master → status master → `organization`).
- **Phase 4** — Organization seed, 3 files, same order.

```bash
if [ "$failed" -eq 0 ]; then
    echo -e "  ${GREEN}Database build completed successfully.${NC}"
    echo ""
    echo -e "  ${YELLOW}Not executed (future phases):${NC}"
    echo "    - Person DDL (03_person/ is superseded — awaiting rewrite)"
    echo "    - Authentication, Administration, remaining modules"
    echo "    - Pass 2 audit-actor FK constraints"
    exit 0
else
    echo -e "  ${RED}Database build FAILED (${failed} errors).${NC}"
    exit 1
fi
```

Finally the script prints a summary (`total`/`failed` counts) and, on success, explicitly lists
what was **not** executed: Person DDL (superseded, awaiting rewrite), Authentication/
Administration/remaining modules, and Pass 2 audit-actor FK constraints. It exits `0` on full
success, `1` on any failure.

The scripts are **not idempotent** — re-running against an already-built database fails on the
first `CREATE TABLE` (by design; a fresh rebuild means drop-and-recreate the database first, not
re-run this script).

**Platform-mechanical differences only**

| Aspect | `02_build.sh` | `02_build.ps1` |
|---|---|---|
| Strict-mode | `set -euo pipefail` | `$ErrorActionPreference = "Stop"` |
| Password prompt | `read -rsp "..." PGPASSWORD` (hidden stdin read) | `Read-Host -AsSecureString` + `Marshal::SecureStringToBSTR`/`PtrToStringAuto` to decode to plaintext for `$env:PGPASSWORD` |
| Failure detection | `if output=$(${PSQL} -f "${file}" 2>&1); then ... else ...` (captures combined stdout/stderr, checks exit code) | `& psql ... -f $File 2>&1` then check `$LASTEXITCODE -eq 0` |
| File-list structure | Bash array of `"label|file"` strings split with `${entry%%|*}` / `${entry##*|}` | PowerShell array of two-element arrays `@("label","file")`, indexed `$entry[0]`/`$entry[1]` |
| Color output | ANSI escape codes (`\033[0;32m` etc.) via `echo -e` | `-ForegroundColor` parameter on `Write-Host` |
| Path resolution | `$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)` then `../..` | `Split-Path -Parent $MyInvocation.MyCommand.Path` then `Resolve-Path "...\..\.."` |

No logic differs between the two — same files, same order, same abort-on-first-failure
behavior, same "not executed" disclosure at the end.

---

### database/scripts/03_validate.sh + database/scripts/03_validate.ps1

**Requirement**

A read-only post-build check that the schema built by `02_build.*` is structurally and
referentially correct — table existence, seeded row counts, uniqueness, and FK integrity —
without requiring a human to open `psql` and run ad hoc queries. Without this pair, a build that
silently seeded the wrong number of rows, left an orphaned FK, or introduced a duplicate
"unique" value would only surface later as an obscure application bug. It performs **no writes**
— it must be run after `02_build.*`, never instead of it.

**Shared logic (both scripts)**

Same `DB_NAME`/`DB_USER`/`DB_HOST`/`DB_PORT` parameters and password-prompt pattern as the build
scripts, but `psql` is invoked with `-t -A` (tuples-only, unaligned output) so every query result
comes back as a single bare scalar the shell can parse directly, e.g. `t`/`f` for booleans or a
bare integer for counts. The walkthrough below shows `03_validate.sh`; `03_validate.ps1` is
mechanically equivalent (see the platform-differences table below).

```bash
check_table_exists() {
    local table="$1"
    local result
    result=$(${PSQL} -c "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'nss' AND table_name = '${table}');" 2>&1 || echo "f")
    if [ "$result" = "t" ]; then
        log_pass "${table} exists"
    else
        log_fail "${table} MISSING"
    fi
}
```

`check_table_exists(table)` queries `information_schema.tables` for `table_schema = 'nss' AND
table_name = '<table>'`; PASS/FAIL.

```bash
check_row_count() {
    local table="$1"
    local expected="$2"
    local count
    count=$(${PSQL} -c "SELECT COUNT(*) FROM nss.${table};" 2>&1 || echo "ERROR")
    if [ "$count" = "ERROR" ]; then
        log_fail "${table}: query failed"
    elif [ "$count" -ge "$expected" ] 2>/dev/null; then
        log_pass "${table}: ${count} rows (expected >= ${expected})"
    else
        log_warn "${table}: ${count} rows (expected >= ${expected})"
    fi
}
```

`check_row_count(table, expected)` runs `SELECT COUNT(*) FROM nss.<table>`; PASS if `count >=
expected`, otherwise **WARN** (not FAIL — having more rows than the frozen seed count, e.g. from
later test data, is not treated as an error).

```bash
check_no_duplicates() {
    local table="$1"
    local column="$2"
    local dups
    dups=$(${PSQL} -c "SELECT COUNT(*) FROM (SELECT ${column} FROM nss.${table} GROUP BY ${column} HAVING COUNT(*) > 1) x;" 2>&1 || echo "ERROR")
    if [ "$dups" = "0" ]; then
        log_pass "${table}: no duplicate ${column}"
    elif [ "$dups" = "ERROR" ]; then
        log_fail "${table}: duplicate check failed"
    else
        log_fail "${table}: ${dups} duplicate ${column} values"
    fi
}
```

`check_no_duplicates(table, column)` groups by `<column>` with `HAVING COUNT(*) > 1` and counts
the groups; PASS if `0`.

```bash
check_fk_integrity() {
    local label="$1"
    local query="$2"
    local orphans
    orphans=$(${PSQL} -c "${query}" 2>&1 || echo "ERROR")
    if [ "$orphans" = "0" ]; then
        log_pass "${label}: FK integrity valid"
    elif [ "$orphans" = "ERROR" ]; then
        log_fail "${label}: FK check failed"
    else
        log_fail "${label}: ${orphans} orphaned rows"
    fi
}
```

`check_fk_integrity(label, query)` runs a caller-supplied `LEFT JOIN ... WHERE <parent>.pk IS
NULL` orphan-count query; PASS if `0`.

```bash
check_column_exists() {
    local table="$1"
    local column="$2"
    local result
    result=$(${PSQL} -c "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'nss' AND table_name = '${table}' AND column_name = '${column}');" 2>&1 || echo "f")
    if [ "$result" = "t" ]; then
        log_pass "${table}.${column} present"
    else
        log_fail "${table}.${column} MISSING"
    fi
}
```

`check_column_exists(table, column)` queries `information_schema.columns`; used only for the two
Pass-1 deferred columns on `document_master` (`person_pk`, `uploaded_by_sangha_sevi_pk`) that
exist as nullable columns but don't yet have their FK constraints attached (Pass 2, deferred
until `sangha_sevi` exists).

Checks run in three module blocks, matching `database/README.md`'s module table:

```bash
check_fk_integrity "role_permission -> role_master" \
    "SELECT COUNT(*) FROM nss.role_permission rp LEFT JOIN nss.role_master rm ON rp.role_master_pk = rm.role_master_pk WHERE rm.role_master_pk IS NULL;"
```

1. **Bootstrap RBAC** — 3 tables exist; `role_master` has ≥ 8 rows; no duplicate `role_code`;
   `role_permission → role_master` and `role_permission → permission_master` FK integrity (the
   call above is the actual FK-integrity query used for the first of those two checks).
2. **Foundation** — 12 tables exist; row-count floors matching the frozen seed
   (`master_category` ≥ 11, `master_data` ≥ 58, `id_sequence_master` ≥ 9, `country` ≥ 5,
   `state` ≥ 112, `district` ≥ 700, `system_setting` ≥ 4, `postal_code` ≥ 2); no duplicate
   `category_code`/`country_code`/`sequence_code`; FK integrity for `master_data →
   master_category`, `state → country`, `district → state`, `postal_code → country`,
   `postal_code → state`; and the two deferred-column existence checks on `document_master`.
3. **Organization** — 3 tables exist; row counts (8 types, 6 statuses, 3 orgs); no duplicate
   `organization_type_code`/`organization_status_code`/`organization_code`; FK integrity for
   `organization → organization_type_master`, `organization → organization_status_master`,
   `organization → country`, `organization → city_village`, `organization → postal_code` (the
   last two use `WHERE fk_col IS NOT NULL AND parent.pk IS NULL` since those FKs are nullable —
   an org with no `city_village_pk` set is not an orphan).

Finally prints `Passed`/`Warnings`/`Failed` counts; exits `0` if `fail_count = 0` (even with
warnings), `1` otherwise. The file header instructs future maintainers to extend this script
whenever new modules are added to `02_build.*`.

**Platform-mechanical differences only**

| Aspect | `03_validate.sh` | `03_validate.ps1` |
|---|---|---|
| Query execution | `${PSQL} -c "<query>"` with `\|\| echo "ERROR"` fallback on command failure | `Invoke-PsqlQuery` function checking `$LASTEXITCODE -ne 0` → returns `"ERROR"` |
| Numeric comparison | `[ "$count" -ge "$expected" ] 2>/dev/null` | `[int]$count -ge $Expected` |
| Logging functions | `log_pass`/`log_fail`/`log_warn` (snake_case, increment global counters via `$((...))`) | `Log-Pass`/`Log-Fail`/`Log-Warn` (PowerShell Verb-Noun convention, increment via `$script:pass_count++`) |
| Colors | ANSI escapes | `-ForegroundColor` |

Every query string, every expected threshold, and every check's pass/fail semantics are
identical between the two — this is the same validation matrix expressed in two shells.

---

### database/scripts/04_grant_backend.sql

**Requirement**

Grants the FastAPI runtime role `nss_db_backend` the minimum privilege it needs to actually read
data — `SELECT` on the `nss` schema's tables. Run as `nss_db_owner` (or superuser), after
`02_build.*` completes. Without this file, `nss_db_backend` can authenticate (it was granted
`CONNECT` in `00_create_database.sql`) but every query the API issues fails with "permission
denied for table X", because table ownership by `nss_db_owner` does not implicitly grant any
access to other roles. Comment in the file notes Tier 0 is `SELECT`-only by design; later tiers
add `INSERT`/`UPDATE` as write endpoints are implemented. Idempotent — safe to re-run.

**Line-by-line explanation**

```sql
GRANT USAGE ON SCHEMA nss TO nss_db_backend;
```

Schema-level `USAGE` is a separate privilege from table-level grants; without it,
`nss_db_backend` cannot even resolve `nss.<table>` names to look up privileges, regardless of
what table grants exist.

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA nss TO nss_db_backend;
```

Retroactively grants `SELECT` on every table that exists in `nss` *at the moment this statement
runs* — i.e. every table created by `02_build.*` up to this point.

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA nss
    GRANT SELECT ON TABLES TO nss_db_backend;
```

Forward-looking: registers a default-privilege rule so that any table `nss_db_owner` creates in
`nss` *after* this statement runs (e.g. a future Organization or Person table) is automatically
`SELECT`-granted to `nss_db_backend` without needing to re-run the previous statement.

---

### database/ddl/00_bootstrap/01_role_master.sql

**Requirement**

Defines `nss.role_master` — the catalogue of application RBAC roles (e.g.
`NSS_ERP_ADMIN`). Depth 0 (no FK dependencies) — it's the first table in the entire build
because `role_permission` (Depth 1) needs it to exist. Without this table there is no RBAC role
catalogue at all; the 8 frozen roles seeded later would have nowhere to live, and
`role_permission` couldn't be created (its FK targets this table).

**Line-by-line explanation**

```sql
CREATE TABLE nss.role_master
(
    role_master_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    role_code VARCHAR(50) NOT NULL,

    role_name VARCHAR(100) NOT NULL,

    role_class VARCHAR(30) NOT NULL,

    scope_level VARCHAR(30) NULL,

    description TEXT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    deleted_at TIMESTAMPTZ NULL,

    deleted_by_sangha_sevi_pk UUID NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

Columns, in order:
- `role_master_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()` — surrogate key, auto-generated.
- `role_code VARCHAR(50) NOT NULL` — the business identifier, e.g. `NSS_ERP_ADMIN`. Required.
- `role_name VARCHAR(100) NOT NULL` — human-readable name, e.g. `NSS ERP Administrator`.
- `role_class VARCHAR(30) NOT NULL` — restricted by `chk_role_master_class` (see below).
- `scope_level VARCHAR(30) NULL` — optional; restricted by `chk_role_master_scope_level` when
  present.
- `description TEXT NULL` — free-text, optional.
- `display_order INTEGER NOT NULL DEFAULT 0` — UI sort order.
- Audit block: `created_at`, `created_by_sangha_sevi_pk`, `updated_at`,
  `updated_by_sangha_sevi_pk`, `deleted_at`, `deleted_by_sangha_sevi_pk`, `is_active`. The four
  `*_sangha_sevi_pk` actor columns are nullable UUIDs with **no FK constraint** — this is the
  Pass 1 half of the project's documented Two-Pass DDL Strategy; the FK to `sangha_sevi` will be
  added in Pass 2, once that table exists and has at least one row (the bootstrap admin).

```sql
    -- Unique constraints
    CONSTRAINT uq_role_master_code
        UNIQUE (role_code),

    CONSTRAINT uq_role_master_name
        UNIQUE (role_name),

    -- CHECK constraints
    CONSTRAINT chk_role_master_class
        CHECK (role_class IN ('SYSTEM', 'ORGANIZATIONAL')),

    CONSTRAINT chk_role_master_scope_level
        CHECK
        (
            scope_level IS NULL
            OR
            scope_level IN ('NSS-WIDE', 'KENDRA', 'ANCHALIKA', 'ZILLA', 'SAKHA', 'PATHA_CHAKRA')
        ),

    CONSTRAINT chk_role_master_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);
```

`uq_role_master_code UNIQUE (role_code)` and `uq_role_master_name UNIQUE (role_name)` mean both
the business code and the display name must be unique. `chk_role_master_class CHECK (role_class
IN ('SYSTEM', 'ORGANIZATIONAL'))` allows only two role classes. `chk_role_master_scope_level
CHECK (scope_level IS NULL OR scope_level IN ('NSS-WIDE', 'KENDRA', 'ANCHALIKA', 'ZILLA',
'SAKHA', 'PATHA_CHAKRA'))` means the value is either unset, or one of the six organizational
scope levels that mirror the Organization module's hierarchy. `chk_role_master_soft_delete`
enforces the soft-delete invariant: a row can never be inactive without a deletion timestamp,
nor active with one set.

```sql
CREATE INDEX idx_role_master_active
    ON nss.role_master (is_active);

CREATE INDEX idx_role_master_code
    ON nss.role_master (role_code);

CREATE INDEX idx_role_master_class
    ON nss.role_master (role_class);
```

These three indexes support the common lookup patterns: active-only listing, lookup by code, and
filtering by SYSTEM vs ORGANIZATIONAL.

---

### database/ddl/00_bootstrap/02_permission_master.sql

**Requirement**

Defines `nss.permission_master` — the catalogue of individual application permissions, grouped
by `module_code`. Depth 0, sibling to `role_master`. Without it, `role_permission` (which maps
roles to permissions) has no permission side to reference; the permission catalogue itself is
currently seeded empty (pending the permission-catalogue freeze — see the seed file below), but
the table must still exist so the mapping table's FK can be declared.

**Line-by-line explanation**

```sql
CREATE TABLE nss.permission_master
(
    permission_master_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    permission_code VARCHAR(80) NOT NULL,

    permission_name VARCHAR(150) NOT NULL,

    module_code VARCHAR(50) NOT NULL,

    description TEXT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    deleted_at TIMESTAMPTZ NULL,

    deleted_by_sangha_sevi_pk UUID NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `permission_master_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `permission_code VARCHAR(80) NOT NULL` — business identifier for the permission.
- `permission_name VARCHAR(150) NOT NULL` — human-readable name.
- `module_code VARCHAR(50) NOT NULL` — which application module the permission belongs to (no
  CHECK restricting the value set — module codes are open-ended, unlike `role_class`).
- `description TEXT NULL`.
- `display_order INTEGER NOT NULL DEFAULT 0`.
- Same six-column audit block as `role_master` (`created_at`, `created_by_sangha_sevi_pk`,
  `updated_at`, `updated_by_sangha_sevi_pk`, `deleted_at`, `deleted_by_sangha_sevi_pk`), plus
  `is_active BOOLEAN NOT NULL DEFAULT TRUE`.

```sql
    -- Unique constraints
    CONSTRAINT uq_permission_master_code
        UNIQUE (permission_code),

    -- CHECK constraints
    CONSTRAINT chk_permission_master_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);
```

`uq_permission_master_code UNIQUE (permission_code)` — only the code is guaranteed unique
(unlike `role_master`, there is no unique constraint on `permission_name`).
`chk_permission_master_soft_delete` is the same soft-delete invariant pattern as `role_master`.

```sql
CREATE INDEX idx_permission_master_active
    ON nss.permission_master (is_active);

CREATE INDEX idx_permission_master_code
    ON nss.permission_master (permission_code);

CREATE INDEX idx_permission_master_module
    ON nss.permission_master (module_code);
```

The module index supports listing all permissions for a given module.

---

### database/ddl/00_bootstrap/03_role_permission.sql

**Requirement**

Defines `nss.role_permission` — the many-to-many join between `role_master` and
`permission_master`. Depth 1 (its FKs require both parent tables to exist first, hence it's
file `03_` after `01_`/`02_`). Without it there is no way to express "role X has permission Y" —
the entire RBAC authorization model has no join table.

**Line-by-line explanation**

```sql
CREATE TABLE nss.role_permission
(
    role_permission_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    role_master_pk UUID NOT NULL,

    permission_master_pk UUID NOT NULL,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    deleted_at TIMESTAMPTZ NULL,

    deleted_by_sangha_sevi_pk UUID NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `role_permission_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `role_master_pk UUID NOT NULL` — FK side 1.
- `permission_master_pk UUID NOT NULL` — FK side 2.
- Audit block is a **subset** of the other two Bootstrap tables: `created_at`,
  `created_by_sangha_sevi_pk`, `deleted_at`, `deleted_by_sangha_sevi_pk`, `is_active` — notably
  **no `updated_at`/`updated_by_sangha_sevi_pk`**. A role-permission mapping is either created
  or (soft-)deleted; it is not "updated" in place, so there's no update-tracking pair.

```sql
    -- Foreign keys
    CONSTRAINT fk_role_permission_role
        FOREIGN KEY (role_master_pk)
        REFERENCES nss.role_master (role_master_pk),

    CONSTRAINT fk_role_permission_permission
        FOREIGN KEY (permission_master_pk)
        REFERENCES nss.permission_master (permission_master_pk),

    -- Unique constraint: no duplicate mapping
    CONSTRAINT uq_role_permission_mapping
        UNIQUE (role_master_pk, permission_master_pk),

    -- CHECK constraints
    CONSTRAINT chk_role_permission_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);
```

`fk_role_permission_role` and `fk_role_permission_permission` are the two parent-table FKs that
make this table Depth 1. `uq_role_permission_mapping UNIQUE (role_master_pk,
permission_master_pk)` means a given role/permission pair can only be mapped once (prevents
duplicate grants). `chk_role_permission_soft_delete` is the same soft-delete invariant as the
other Bootstrap tables.

```sql
CREATE INDEX idx_role_permission_role
    ON nss.role_permission (role_master_pk);

CREATE INDEX idx_role_permission_permission
    ON nss.role_permission (permission_master_pk);

CREATE INDEX idx_role_permission_active
    ON nss.role_permission (is_active);
```

These support "all permissions for role X" and "all roles with permission Y" lookups in either
direction.

---

### database/seed/00_bootstrap/01_permission_master.sql

**Requirement**

Reserves the seed slot for `permission_master` in the build order (run by `02_build.*` between
the Bootstrap DDL phase and the `role_master` seed) so the phase numbering stays stable once the
permission catalogue is frozen. It currently inserts nothing.

**Line-by-line explanation**

```sql
-- =====================================================
-- NSS ERP
-- Module: Bootstrap RBAC
-- File: 01_permission_master.sql (seed)
-- Seed: Permission catalogue
-- Authority: SOL-ARCH-011 §4, SOL-ADMIN-004 §9.5
--
-- STATUS: EMPTY — permission catalogue NOT YET FROZEN
--
-- This file will be populated when the permission
-- catalogue is approved. Until then, no permission
-- rows are seeded.
-- =====================================================
```

The file contains only this header comment block — no `INSERT` statement. It will be populated
once the permission catalogue is approved (SOL-ADMIN-004 §9.5). Row count: **0**.

---

### database/seed/00_bootstrap/02_role_master.sql

**Requirement**

Seeds the 8 frozen application RBAC roles into `role_master` — the concrete rows that
`NSS_ERP_ADMIN` and the other administrative identities resolve to. Without this file the
Bootstrap Verification UI's `/api/v1/bootstrap/roles` endpoint would return an empty list, and
there would be no role for the eventual first administrator account to be assigned.

**Line-by-line explanation**

```sql
INSERT INTO nss.role_master
    (role_code, role_name, role_class, scope_level, description, display_order)
VALUES
    ('NSS_ERP_ADMIN',
     'NSS ERP Administrator',
     'SYSTEM',
     'NSS-WIDE',
     'System-wide ERP administrator with all application permissions',
     1),

    ('NSS_ERP_KENDRA_ADMIN',
     'Kendra Administrator',
     'ORGANIZATIONAL',
     'KENDRA',
     'Administrative authority scoped to a specific Kendra',
     4),

    -- ...5 more rows, same shape...
```

The column list supplies all six non-audit, non-PK columns explicitly — `role_master_pk`,
`is_active`, and the audit timestamps all fall back to their `DEFAULT`s (a fresh UUID, `TRUE`,
`CURRENT_TIMESTAMP` respectively); the nullable audit-actor columns stay `NULL` since no
`sangha_sevi` exists yet to attribute the insert to.

**Row count: 8** (all 8 rows listed — this is a small, fully-enumerable seed file):

| role_code | role_name | role_class | scope_level | display_order |
|---|---|---|---|---|
| `NSS_ERP_ADMIN` | NSS ERP Administrator | SYSTEM | NSS-WIDE | 1 |
| `NSS_ERP_AUDITOR` | Auditor | SYSTEM | NSS-WIDE | 2 |
| `NSS_ERP_REPORT_VIEWER` | Report Viewer | SYSTEM | NSS-WIDE | 3 |
| `NSS_ERP_KENDRA_ADMIN` | Kendra Administrator | ORGANIZATIONAL | KENDRA | 4 |
| `NSS_ERP_ANCHALIKA_ADMIN` | Anchalika Administrator | ORGANIZATIONAL | ANCHALIKA | 5 |
| `NSS_ERP_ZILLA_ADMIN` | Zilla Administrator | ORGANIZATIONAL | ZILLA | 6 |
| `NSS_ERP_SAKHA_ADMIN` | Sakha Administrator | ORGANIZATIONAL | SAKHA | 7 |
| `NSS_ERP_PATHA_CHAKRA_ADMIN` | Patha Chakra Administrator | ORGANIZATIONAL | PATHA_CHAKRA | 8 |

Pattern: the three `SYSTEM`/`NSS-WIDE` roles (admin, auditor, report viewer) are global; the five
`ORGANIZATIONAL` roles each scope to exactly one of the five organizational levels defined by
`chk_role_master_scope_level` in the DDL. Every `scope_level` value used here is one of the six
allowed by that CHECK constraint (`PATHA_CHAKRA` is used; `SAKHA_ASANA` — a seventh
organization type seeded later in Organization — has no corresponding admin role at all,
which is a notable asymmetry worth flagging rather than an error).

---

### database/seed/00_bootstrap/03_role_permission.sql

**Requirement**

Reserves the seed slot for `role_permission` mappings, run after `role_master` is seeded.
Currently empty because it structurally depends on `permission_master` being populated first,
and that catalogue isn't frozen yet.

**Line-by-line explanation**

```sql
-- =====================================================
-- NSS ERP
-- Module: Bootstrap RBAC
-- File: 03_role_permission.sql (seed)
-- Seed: Role-to-permission mappings
-- Authority: SOL-ARCH-011 §4, SOL-ADMIN-004 §10
--
-- STATUS: EMPTY — depends on permission catalogue
--
-- This file will be populated after 01_permission_master
-- seed is frozen. Role-permission mappings cannot exist
-- without permissions.
-- =====================================================
```

Header-comment-only file, no `INSERT`. Role-permission mappings cannot exist without
permissions. Row count: **0**.

---

### database/ddl/01_foundation/02_master_category.sql

**Requirement**

Defines `nss.master_category` — the top level of the generic two-table
lookup-value pattern (`master_category` + `master_data`) used throughout the schema for
enumerated reference data (gender, marital status, document type, etc.) instead of one
hand-rolled lookup table per concept. Depth 0, first Foundation table. Without it, `master_data`
(Depth 1) has nothing to categorize its values under, and none of the generic
category/value-driven master data used by Person, Membership, etc. designs would have a home.

**Line-by-line explanation**

```sql
CREATE TABLE nss.master_category
(
    master_category_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    category_code VARCHAR(50) NOT NULL,

    category_name VARCHAR(100) NOT NULL,

    description TEXT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `master_category_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `category_code VARCHAR(50) NOT NULL` — e.g. `GENDER`.
- `category_name VARCHAR(100) NOT NULL` — e.g. `Gender`.
- `description TEXT NULL`.
- `display_order INTEGER NOT NULL DEFAULT 0`.
- `created_at`, `updated_at`, `deleted_at`, `is_active` — note this is a **shorter** audit block
  than the Bootstrap tables: no `created_by_sangha_sevi_pk` / `updated_by_sangha_sevi_pk` /
  `deleted_by_sangha_sevi_pk` actor columns at all. Foundation's reference-data tables generally
  omit actor tracking (see also `system_setting`, `id_sequence_master`, `country`,
  `master_data`, `state`, `district`, `city_village`, `postal_code`) — only `document_master`
  (`uploaded_by_sangha_sevi_pk`) and `field_change_log` (`changed_by_sangha_sevi_pk`) carry actor
  references in this module.

```sql
    CONSTRAINT uq_master_category_code
        UNIQUE (category_code),

    CONSTRAINT uq_master_category_name
        UNIQUE (category_name),

    CONSTRAINT chk_master_category_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_master_category_active
    ON nss.master_category (is_active);

CREATE INDEX idx_master_category_code
    ON nss.master_category (category_code);
```

`uq_master_category_code` and `uq_master_category_name` are both unique. `chk_master_category_
soft_delete` is the standard soft-delete invariant. The two indexes are on `is_active` and
`category_code`.

---

### database/ddl/01_foundation/03_system_setting.sql

**Requirement**

Defines `nss.system_setting` — a generic key/value configuration store (e.g. current membership
year, password policy). Depth 0. Without it there is no database-backed place for
application-wide configuration that needs to be readable/editable without a code deploy;
everything would have to be a hardcoded constant, which conflicts with the project's
"Configuration Over Hardcoding" frozen principle.

**Line-by-line explanation**

```sql
CREATE TABLE nss.system_setting
(
    system_setting_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    setting_key VARCHAR(100) NOT NULL,

    setting_value TEXT NOT NULL,

    description TEXT NULL,

    data_type VARCHAR(20) NOT NULL
        DEFAULT 'STRING',

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `system_setting_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `setting_key VARCHAR(100) NOT NULL` — e.g. `CURRENT_MEMBERSHIP_YEAR`.
- `setting_value TEXT NOT NULL` — stored as text regardless of logical type; `data_type` (below)
  tells consumers how to interpret it.
- `description TEXT NULL`.
- `data_type VARCHAR(20) NOT NULL DEFAULT 'STRING'` — restricted by CHECK below.
- `created_at`, `updated_at`, `deleted_at`, `is_active` — standard four-column audit block.

```sql
    CONSTRAINT uq_system_setting_key
        UNIQUE (setting_key),

    CONSTRAINT chk_system_setting_data_type
        CHECK
        (
            data_type IN
            (
                'STRING',
                'INTEGER',
                'BOOLEAN',
                'DATE',
                'JSON'
            )
        ),

    CONSTRAINT chk_system_setting_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_system_setting_active
    ON nss.system_setting (is_active);

CREATE INDEX idx_system_setting_key
    ON nss.system_setting (setting_key);
```

`uq_system_setting_key UNIQUE (setting_key)`. `chk_system_setting_data_type CHECK (data_type IN
('STRING', 'INTEGER', 'BOOLEAN', 'DATE', 'JSON'))` is the five type-tag values a consumer can
expect. `chk_system_setting_soft_delete` is the standard invariant. Indexes cover `is_active` and
`setting_key`.

---

### database/ddl/01_foundation/04_id_sequence_master.sql

**Requirement**

Defines `nss.id_sequence_master` — a table-driven business-ID generator, one row per business
entity that needs a permanent, human-readable, sequential identifier (e.g. Sangha Sevi IDs,
Anchalika codes). This directly implements the project's frozen "Permanent Business Identifiers"
principle without hardcoding a PostgreSQL `SEQUENCE` per entity type — every sequence's prefix,
current counter, and zero-padding width are configurable data, not schema.

**Line-by-line explanation**

```sql
CREATE TABLE nss.id_sequence_master
(
    id_sequence_master_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sequence_code VARCHAR(50) NOT NULL,

    sequence_name VARCHAR(100) NOT NULL,

    prefix VARCHAR(20) NOT NULL,

    current_value BIGINT NOT NULL
        DEFAULT 0,

    padding_length INTEGER NOT NULL
        DEFAULT 8,

    description TEXT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `id_sequence_master_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `sequence_code VARCHAR(50) NOT NULL` — e.g. `SANGHA_SEVI`.
- `sequence_name VARCHAR(100) NOT NULL` — e.g. `Sangha Sevi Code`.
- `prefix VARCHAR(20) NOT NULL` — e.g. `SS`, prepended to the generated number.
- `current_value BIGINT NOT NULL DEFAULT 0` — the last-issued counter value; the application
  layer increments this atomically when issuing a new ID.
- `padding_length INTEGER NOT NULL DEFAULT 8` — how many digits the numeric part is zero-padded
  to.
- `description TEXT NULL`.
- `created_at`, `updated_at`, `deleted_at`, `is_active` — standard four-column audit block.

```sql
    CONSTRAINT uq_id_sequence_code
        UNIQUE (sequence_code),

    CONSTRAINT uq_id_sequence_name
        UNIQUE (sequence_name),

    CONSTRAINT chk_id_sequence_padding
        CHECK (padding_length BETWEEN 4 AND 12),

    CONSTRAINT chk_id_sequence_current_value
        CHECK (current_value >= 0),

    CONSTRAINT chk_id_sequence_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_id_sequence_active
    ON nss.id_sequence_master (is_active);

CREATE INDEX idx_id_sequence_code
    ON nss.id_sequence_master (sequence_code);
```

`uq_id_sequence_code` and `uq_id_sequence_name` are both unique. `chk_id_sequence_padding CHECK
(padding_length BETWEEN 4 AND 12)` bounds how wide a generated ID's numeric portion can be.
`chk_id_sequence_current_value CHECK (current_value >= 0)` means the counter can never go
negative. `chk_id_sequence_soft_delete` is the standard invariant. Indexes cover `is_active` and
`sequence_code`.

---

### database/ddl/01_foundation/05_country.sql

**Requirement**

Defines `nss.country` — the root of the location hierarchy (`country` → `state` → `district` →
`city_village`, plus `postal_code`). Depth 0. Without it, `state` (which FKs to it) cannot
exist, and the entire address/location model for Person, Organization, etc. has no anchor.

**Line-by-line explanation**

```sql
CREATE TABLE nss.country
(
    country_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    country_code CHAR(2) NOT NULL,

    country_name VARCHAR(100) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `country_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `country_code CHAR(2) NOT NULL` — fixed 2-character code, e.g. `IN`, `US` (ISO 3166-1
  alpha-2 style, though not formally constrained to the ISO list by a CHECK).
- `country_name VARCHAR(100) NOT NULL` — e.g. `India`.
- `display_order INTEGER NOT NULL DEFAULT 0`.
- `created_at`, `updated_at`, `deleted_at`, `is_active` — standard four-column audit block.

```sql
    CONSTRAINT uq_country_code
        UNIQUE (country_code),

    CONSTRAINT uq_country_name
        UNIQUE (country_name),

    CONSTRAINT chk_country_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_country_active
    ON nss.country (is_active);

CREATE INDEX idx_country_code
    ON nss.country (country_code);
```

`uq_country_code` and `uq_country_name` are both unique. `chk_country_soft_delete` is the
standard invariant. Indexes cover `is_active` and `country_code`.

---

### database/ddl/01_foundation/06_document_master.sql

**Requirement**

Defines `nss.document_master` — metadata for every uploaded/stored file in the system (photos,
ID proofs, certificates, correspondence, etc.), independent of which module owns the document.
Depth 0 by DDL classification, but logically it's a Person-module concept whose physical table
is owned by Foundation (per the file's own header note) — a deliberate split between logical
design ownership and physical DDL placement. Without it there would be no single place to
record where an uploaded file lives, what type it is, and (once Pass 2 lands) who uploaded it
and for which person.

**Line-by-line explanation**

```sql
CREATE TABLE nss.document_master
(
    document_master_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    document_type_code VARCHAR(50) NOT NULL,

    document_number VARCHAR(100) NULL,

    document_name VARCHAR(255) NOT NULL,

    storage_path TEXT NOT NULL,

    file_size_bytes BIGINT NULL,

    mime_type VARCHAR(100) NULL,

    version INTEGER NOT NULL
        DEFAULT 1,

    checksum VARCHAR(128) NULL,

    description TEXT NULL,

    person_pk UUID NULL,

    uploaded_by_sangha_sevi_pk UUID NULL,

    uploaded_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `document_master_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `document_type_code VARCHAR(50) NOT NULL` — links conceptually (not via FK) to the
  `DOCUMENT_TYPE` category in `master_data` (e.g. `PHOTO`, `ID_PROOF`).
- `document_number VARCHAR(100) NULL` — e.g. an ID-proof document's printed number; optional.
- `document_name VARCHAR(255) NOT NULL` — display name of the file.
- `storage_path TEXT NOT NULL` — where the file physically/logically lives (filesystem path,
  object-store key, etc.).
- `file_size_bytes BIGINT NULL`.
- `mime_type VARCHAR(100) NULL`.
- `version INTEGER NOT NULL DEFAULT 1` — supports re-uploaded/superseding versions of the same
  logical document; constrained by CHECK below.
- `checksum VARCHAR(128) NULL` — integrity hash of the stored file.
- `description TEXT NULL`.
- `person_pk UUID NULL` — **deferred FK** (Pass 1 nullable column, Pass 2 will attach `FOREIGN
  KEY REFERENCES person`, once the real `person` table exists — not the superseded prototype).
- `uploaded_by_sangha_sevi_pk UUID NULL` — **deferred FK**, same Pass 2 treatment, referencing
  the eventual `sangha_sevi` table.
- `uploaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP` — separate from `created_at`;
  this records when the *file* was uploaded, which may conceptually differ from row-creation
  time in some future workflow even though today they'd be set at the same moment.
- `created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`, `updated_at TIMESTAMPTZ NULL`,
  `deleted_at TIMESTAMPTZ NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`.

```sql
    CONSTRAINT chk_document_version_positive
        CHECK (version >= 1),

    CONSTRAINT chk_document_master_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_document_master_type_code
    ON nss.document_master (document_type_code);

CREATE INDEX idx_document_master_active
    ON nss.document_master (is_active);

CREATE INDEX idx_document_master_number
    ON nss.document_master (document_number)
    WHERE document_number IS NOT NULL;
```

- `chk_document_version_positive CHECK (version >= 1)`.
- `chk_document_master_soft_delete` — standard invariant.
- No FK constraints exist yet at all in this file (the two candidate FK columns are Pass-1
  nullable placeholders only).

Indexes: `idx_document_master_type_code (document_type_code)`, `idx_document_master_active
(is_active)`, and a **partial** index `idx_document_master_number (document_number) WHERE
document_number IS NOT NULL` — avoids indexing the (likely common) `NULL` case.

Note: the file's own header comment contains a minor internal inconsistency —
it states both `Sequence: #5 of 86` and `Sequence: #5 of 87` on consecutive lines (a leftover
from a prior renumbering that wasn't fully cleaned up); it does not affect the executed DDL.

---

### database/ddl/01_foundation/07_field_change_log.sql

**Requirement**

Defines `nss.field_change_log` — a generic, cross-table field-level audit trail (which record,
which field, old value, new value, who, when, why). Depth 0 by design choice, not by accident:
the file's own header explains it deliberately carries **no FK constraints** so that any table
in the schema can be logged against without creating circular or premature dependencies. Without
it, there would be no uniform way to answer "what did this field used to be, and who changed
it" for arbitrary tables — each module would need its own bespoke history table.

**Line-by-line explanation**

```sql
CREATE TABLE nss.field_change_log
(
    field_change_log_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    table_name VARCHAR(100) NOT NULL,

    record_pk UUID NOT NULL,

    field_name VARCHAR(100) NOT NULL,

    old_value TEXT NULL,

    new_value TEXT NULL,

    change_reason TEXT NULL,

    changed_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    changed_by_sangha_sevi_pk UUID NULL
);
```

- `field_change_log_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `table_name VARCHAR(100) NOT NULL` — which table the changed row belongs to, stored as plain
  text (not an FK to `information_schema`, obviously — it's metadata about metadata).
- `record_pk UUID NOT NULL` — the PK value of the changed row in that table.
- `field_name VARCHAR(100) NOT NULL` — which column changed.
- `old_value TEXT NULL` / `new_value TEXT NULL` — both stored as text regardless of the
  original column's type, so this table can log changes to any column of any type uniformly.
- `change_reason TEXT NULL` — optional free-text justification.
- `changed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`.
- `changed_by_sangha_sevi_pk UUID NULL` — the actor, again with **no FK constraint** (by
  explicit design here, unlike the Bootstrap tables' Pass-1/Pass-2 deferral — this table's
  header states references are intentionally left as unconstrained UUIDs to avoid circular
  dependencies, and the application layer is responsible for referential integrity).

No constraints beyond the column `NOT NULL`s — no unique constraints, no CHECK constraints, and
notably **no `is_active`/`deleted_at`/soft-delete pattern at all**: this table is an append-only
log, not a soft-deletable entity, consistent with the project's "History Never Deleted"
principle (there is nothing to soft-delete — log rows are permanent by construction).

```sql
CREATE INDEX idx_field_change_log_table_record
    ON nss.field_change_log (table_name, record_pk);

CREATE INDEX idx_field_change_log_changed_at
    ON nss.field_change_log (changed_at);

CREATE INDEX idx_field_change_log_field
    ON nss.field_change_log (table_name, field_name);
```

Indexes: `idx_field_change_log_table_record (table_name, record_pk)` — the primary lookup
pattern ("show me the history of this specific row"); `idx_field_change_log_changed_at
(changed_at)` — time-ordered queries; `idx_field_change_log_field (table_name, field_name)` —
"show me every change to this column across all rows of this table."

---

### database/ddl/01_foundation/08_master_data.sql

**Requirement**

Defines `nss.master_data` — the value side of the `master_category`/`master_data` generic
lookup pattern; every row is one enumerated value under one category (e.g. category `GENDER` →
values `MALE`/`FEMALE`/`OTHER`). Depth 1 (depends on `master_category`). Without it, the
category table has nothing under it, and none of the enumerated reference values consumed by
Person/Membership/Family modules (gender, marital status, membership type/status, relationship
type, document type, address type) have anywhere to live.

**Line-by-line explanation**

```sql
CREATE TABLE nss.master_data
(
    master_data_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    master_category_pk UUID NOT NULL,

    value_code VARCHAR(50) NOT NULL,

    value_name VARCHAR(150) NOT NULL,

    description TEXT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `master_data_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `master_category_pk UUID NOT NULL` — FK to the owning category.
- `value_code VARCHAR(50) NOT NULL` — e.g. `MALE`.
- `value_name VARCHAR(150) NOT NULL` — e.g. `Male`.
- `description TEXT NULL`.
- `display_order INTEGER NOT NULL DEFAULT 0`.
- `created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`, `updated_at TIMESTAMPTZ NULL`,
  `deleted_at TIMESTAMPTZ NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`.

```sql
    CONSTRAINT fk_master_data_category
        FOREIGN KEY (master_category_pk)
        REFERENCES nss.master_category (master_category_pk),

    CONSTRAINT uq_master_data_category_code
        UNIQUE (master_category_pk, value_code),

    CONSTRAINT chk_master_data_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_master_data_category
    ON nss.master_data (master_category_pk);

CREATE INDEX idx_master_data_active
    ON nss.master_data (is_active);

CREATE INDEX idx_master_data_value_code
    ON nss.master_data (value_code);

CREATE INDEX idx_master_data_value_name
    ON nss.master_data USING gin (value_name gin_trgm_ops);
```

- `fk_master_data_category FOREIGN KEY (master_category_pk) REFERENCES nss.master_category
  (master_category_pk)`.
- `uq_master_data_category_code UNIQUE (master_category_pk, value_code)` — the uniqueness scope
  is **per category**, not global: `value_code = 'ACTIVE'` can validly exist under both
  `MEMBERSHIP_STATUS` and (hypothetically) another category without conflict, because the
  unique constraint is composite.
- `chk_master_data_soft_delete` — standard invariant.

Indexes: `idx_master_data_category (master_category_pk)`, `idx_master_data_active (is_active)`,
`idx_master_data_value_code (value_code)`, and `idx_master_data_value_name USING gin (value_name
gin_trgm_ops)` — a trigram GIN index enabling fuzzy/partial-text search over value names (this
is the first table in the build to actually use the `pg_trgm` extension installed in
`01_extensions.sql`).

---

### database/ddl/01_foundation/09_state.sql

**Requirement**

Defines `nss.state` — states/provinces/territories under a country. Depth 1 (depends on
`country`). Without it, `district` (Depth 2, FKs to `state`) has no parent to attach to, and
the address hierarchy stops at the country level.

**Line-by-line explanation**

```sql
CREATE TABLE nss.state
(
    state_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    country_pk UUID NOT NULL,

    state_code VARCHAR(20) NOT NULL,

    state_name VARCHAR(100) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

- `state_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `country_pk UUID NOT NULL` — FK to owning country.
- `state_code VARCHAR(20) NOT NULL` — e.g. `OD` for Odisha.
- `state_name VARCHAR(100) NOT NULL` — e.g. `Odisha`.
- `display_order INTEGER NOT NULL DEFAULT 0`.
- `created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`, `updated_at TIMESTAMPTZ NULL`,
  `deleted_at TIMESTAMPTZ NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`.

```sql
    CONSTRAINT fk_state_country
        FOREIGN KEY (country_pk)
        REFERENCES nss.country (country_pk),

    CONSTRAINT uq_state_country_code
        UNIQUE (country_pk, state_code),

    CONSTRAINT uq_state_country_name
        UNIQUE (country_pk, state_name),

    CONSTRAINT chk_state_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_state_country
    ON nss.state (country_pk);

CREATE INDEX idx_state_active
    ON nss.state (is_active);

CREATE INDEX idx_state_name
    ON nss.state USING gin (state_name gin_trgm_ops);
```

- `fk_state_country FOREIGN KEY (country_pk) REFERENCES nss.country (country_pk)`.
- `uq_state_country_code UNIQUE (country_pk, state_code)` and `uq_state_country_name UNIQUE
  (country_pk, state_name)` — both uniqueness rules are scoped **per country**, so the same
  `state_code` (e.g. `AR` is used for both India's Arkansas-equivalent Arunachal Pradesh and,
  separately, US Arkansas — see the seed data below) can coexist under different countries
  without collision.
- `chk_state_soft_delete` — standard invariant.

Indexes: `idx_state_country (country_pk)`, `idx_state_active (is_active)`, `idx_state_name USING
gin (state_name gin_trgm_ops)` (fuzzy search).

---

### database/ddl/01_foundation/10_district.sql

**Requirement**

Defines `nss.district` — districts under a state. Depth 2 (depends on `state`). Without it,
`city_village` (Depth 3) has no parent, and no Indian district-level administrative geography
exists for organization/address records to reference.

**Line-by-line explanation**

```sql
CREATE TABLE nss.district
(
    district_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    state_pk UUID NOT NULL,

    district_code VARCHAR(20) NOT NULL,

    district_name VARCHAR(100) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

Columns: `district_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`; `state_pk UUID NOT NULL` (FK
to owning state); `district_code VARCHAR(20) NOT NULL`; `district_name VARCHAR(100) NOT NULL`;
`display_order INTEGER NOT NULL DEFAULT 0`; the standard four-column audit block
(`created_at`/`updated_at`/`deleted_at`/`is_active`).

```sql
    CONSTRAINT fk_district_state
        FOREIGN KEY (state_pk)
        REFERENCES nss.state (state_pk),

    CONSTRAINT uq_district_state_code
        UNIQUE (state_pk, district_code),

    CONSTRAINT uq_district_state_name
        UNIQUE (state_pk, district_name),

    CONSTRAINT chk_district_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_district_state
    ON nss.district (state_pk);

CREATE INDEX idx_district_active
    ON nss.district (is_active);

CREATE INDEX idx_district_name
    ON nss.district USING gin (district_name gin_trgm_ops);
```

Constraints: `fk_district_state FOREIGN KEY (state_pk) REFERENCES nss.state (state_pk)`;
`uq_district_state_code UNIQUE (state_pk, district_code)` and `uq_district_state_name UNIQUE
(state_pk, district_name)` — again scoped per-parent (per state), not global;
`chk_district_soft_delete` standard invariant.

Indexes: `idx_district_state (state_pk)`, `idx_district_active (is_active)`,
`idx_district_name USING gin (district_name gin_trgm_ops)`.

---

### database/ddl/01_foundation/11_city_village.sql

**Requirement**

Defines `nss.city_village` — the finest-grained named locality (city, town, or village) under a
district. Depth 3 (depends on `district`). Without it, there is no leaf-level locality node for
addresses to attach to, and `city_village_postal_code_map` (Depth 4, FKs to this table) cannot
exist.

**Line-by-line explanation**

```sql
CREATE TABLE nss.city_village
(
    city_village_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    district_pk UUID NOT NULL,

    city_village_code VARCHAR(20) NOT NULL,

    city_village_name VARCHAR(150) NOT NULL,

    city_village_type VARCHAR(20) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

Columns: `city_village_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`; `district_pk UUID NOT
NULL` (FK to owning district); `city_village_code VARCHAR(20) NOT NULL`; `city_village_name
VARCHAR(150) NOT NULL`; `city_village_type VARCHAR(20) NOT NULL` — restricted by CHECK below;
`display_order INTEGER NOT NULL DEFAULT 0`; standard four-column audit block.

```sql
    CONSTRAINT fk_city_village_district
        FOREIGN KEY (district_pk)
        REFERENCES nss.district (district_pk),

    CONSTRAINT uq_city_village_district_code
        UNIQUE (district_pk, city_village_code),

    CONSTRAINT uq_city_village_district_name
        UNIQUE (district_pk, city_village_name),

    CONSTRAINT chk_city_village_type
        CHECK
        (
            city_village_type IN
            (
                'CITY',
                'TOWN',
                'VILLAGE'
            )
        ),

    CONSTRAINT chk_city_village_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_city_village_district
    ON nss.city_village (district_pk);

CREATE INDEX idx_city_village_active
    ON nss.city_village (is_active);

CREATE INDEX idx_city_village_name
    ON nss.city_village USING gin (city_village_name gin_trgm_ops);
```

Constraints: `fk_city_village_district FOREIGN KEY (district_pk) REFERENCES nss.district
(district_pk)`; `uq_city_village_district_code UNIQUE (district_pk, city_village_code)` and
`uq_city_village_district_name UNIQUE (district_pk, city_village_name)` — per-district scoped
uniqueness; `chk_city_village_type CHECK (city_village_type IN ('CITY', 'TOWN', 'VILLAGE'))` —
exactly three allowed locality classifications; `chk_city_village_soft_delete` standard
invariant.

Indexes: `idx_city_village_district (district_pk)`, `idx_city_village_active (is_active)`,
`idx_city_village_name USING gin (city_village_name gin_trgm_ops)`.

---

### database/ddl/01_foundation/12_postal_code.sql

**Requirement**

Defines `nss.postal_code` — PIN/postal codes, scoped to a country with an explicit state
association. Depth 2 (depends on `country` and `state` — same depth as `district`, since it
doesn't depend on `district`). Implements the "PIN Code Geographic Model" amendment: a postal
code is not tied 1:1 to a single locality — that relationship is deliberately pulled out into
`city_village_postal_code_map` (M:N) so one PIN can serve multiple villages/towns and vice
versa. Without this table, `organization` and (in the superseded Person prototype)
`person_address` have no postal-code entity to reference.

**Line-by-line explanation**

```sql
CREATE TABLE nss.postal_code
(
    postal_code_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    country_pk UUID NOT NULL,

    state_pk UUID NOT NULL,

    postal_code VARCHAR(20) NOT NULL,

    post_office_name VARCHAR(150) NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

Columns: `postal_code_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`; `country_pk UUID NOT
NULL` (FK); `state_pk UUID NOT NULL` (FK) — the file's header comment explains this is a
*reference* FK for direct administrative ownership, not part of the uniqueness key;
`postal_code VARCHAR(20) NOT NULL` — the PIN value itself, stored as text (not numeric) since
some countries' postal codes contain letters and leading zeros must be preserved;
`post_office_name VARCHAR(150) NULL` — e.g. `Unit 9 SO`; standard four-column audit block.

```sql
    CONSTRAINT fk_postal_code_country
        FOREIGN KEY (country_pk)
        REFERENCES nss.country (country_pk),

    CONSTRAINT fk_postal_code_state
        FOREIGN KEY (state_pk)
        REFERENCES nss.state (state_pk),

    CONSTRAINT uq_postal_code_country
        UNIQUE (country_pk, postal_code),

    CONSTRAINT chk_postal_code_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_postal_code_country
    ON nss.postal_code (country_pk);

CREATE INDEX idx_postal_code_state
    ON nss.postal_code (state_pk);

CREATE INDEX idx_postal_code_code
    ON nss.postal_code (postal_code);

CREATE INDEX idx_postal_code_active
    ON nss.postal_code (is_active);

CREATE INDEX idx_postal_code_post_office
    ON nss.postal_code USING gin (post_office_name gin_trgm_ops)
    WHERE post_office_name IS NOT NULL;
```

Constraints: `fk_postal_code_country FOREIGN KEY (country_pk) REFERENCES nss.country
(country_pk)`; `fk_postal_code_state FOREIGN KEY (state_pk) REFERENCES nss.state (state_pk)`;
`uq_postal_code_country UNIQUE (country_pk, postal_code)` — a PIN is unique **within a
country's postal system**, per the header note (`state_pk` is deliberately excluded from this
unique key, since it's a reference column, not part of what makes a PIN distinct);
`chk_postal_code_soft_delete` standard invariant.

Indexes: `idx_postal_code_country (country_pk)`, `idx_postal_code_state (state_pk)`,
`idx_postal_code_code (postal_code)`, `idx_postal_code_active (is_active)`, and a **partial**
trigram index `idx_postal_code_post_office USING gin (post_office_name gin_trgm_ops) WHERE
post_office_name IS NOT NULL`.

---

### database/ddl/01_foundation/13_city_village_postal_code_map.sql

**Requirement**

Defines `nss.city_village_postal_code_map` — the explicit M:N join between `city_village` and
`postal_code`, implementing the PIN Code Geographic Model amendment described in
`12_postal_code.sql`'s header. Depth 4 (the deepest Foundation table — depends on both
`city_village` at Depth 3 and `postal_code` at Depth 2). Without it, there is no way to express
"this village is served by these PIN codes" (or the reverse) as a proper relation; addresses
would have to force a single PIN per locality, which the amendment explicitly rejected.

**Line-by-line explanation**

```sql
CREATE TABLE nss.city_village_postal_code_map
(
    city_village_postal_code_map_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    city_village_pk UUID NOT NULL,

    postal_code_pk UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
```

Columns: `city_village_postal_code_map_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`;
`city_village_pk UUID NOT NULL` (FK); `postal_code_pk UUID NOT NULL` (FK); `created_at
TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP` — and that's the **entire** column list; there
is no `updated_at`, `deleted_at`, or `is_active` at all. A pure join-table row is either present
or absent — there's nothing to "update" about a mapping, and removing a mapping is a hard delete
of the join row (the underlying `city_village`/`postal_code` history is preserved elsewhere via
their own soft-delete columns).

```sql
    CONSTRAINT fk_cv_pc_map_city_village
        FOREIGN KEY (city_village_pk)
        REFERENCES nss.city_village (city_village_pk),

    CONSTRAINT fk_cv_pc_map_postal_code
        FOREIGN KEY (postal_code_pk)
        REFERENCES nss.postal_code (postal_code_pk),

    CONSTRAINT uq_cv_pc_map
        UNIQUE (city_village_pk, postal_code_pk)
);

CREATE INDEX idx_cv_pc_map_city_village
    ON nss.city_village_postal_code_map (city_village_pk);

CREATE INDEX idx_cv_pc_map_postal_code
    ON nss.city_village_postal_code_map (postal_code_pk);
```

Constraints: `fk_cv_pc_map_city_village FOREIGN KEY (city_village_pk) REFERENCES
nss.city_village (city_village_pk)`; `fk_cv_pc_map_postal_code FOREIGN KEY (postal_code_pk)
REFERENCES nss.postal_code (postal_code_pk)`; `uq_cv_pc_map UNIQUE (city_village_pk,
postal_code_pk)` — prevents the same locality/PIN pair being mapped twice.

Indexes: `idx_cv_pc_map_city_village (city_village_pk)`, `idx_cv_pc_map_postal_code
(postal_code_pk)` — one index per FK direction, supporting lookups from either side of the M:N
relationship.

---

### database/seed/01_foundation/01_master_category.sql

**Requirement**

Seeds the 11 top-level lookup categories that every subsequent `master_data` value row attaches
to. Must run before `02_master_data.sql`, which resolves each value's `master_category_pk` via a
subquery on `category_code`.

**Line-by-line explanation**

```sql
INSERT INTO nss.master_category
    (category_code, category_name, description, display_order)
VALUES (...)
```

Four explicit columns per row; `master_category_pk`, `is_active`, `created_at` all default.

**Row count: 11** (all rows listed — small, fully-enumerable):

| category_code | category_name | display_order |
|---|---|---|
| `GENDER` | Gender | 1 |
| `RELATIONSHIP_TYPE` | Relationship Type | 2 |
| `MEMBERSHIP_TYPE` | Membership Type | 3 |
| `MEMBERSHIP_STATUS` | Membership Status | 4 |
| `LOGIN_ROLE` | Login Role | 5 |
| `STATUS_REASON` | Status Reason | 6 |
| `WORKFLOW_STATUS` | Workflow Status | 7 |
| `DOCUMENT_TYPE` | Document Type | 8 |
| `APPLICATION_TYPE` | Application Type | 9 |
| `MARITAL_STATUS` | Marital Status | 10 |
| `ADDRESS_TYPE` | Address Type | 11 |

Notable: three of these categories (`LOGIN_ROLE`, `STATUS_REASON`, `WORKFLOW_STATUS`,
`APPLICATION_TYPE`) have **no corresponding rows in `02_master_data.sql`** — they are
categories reserved for future modules (Authentication, Membership workflow) that haven't
seeded values yet; only 7 of the 11 categories actually have `master_data` children today.

---

### database/seed/01_foundation/02_master_data.sql

**Requirement**

Seeds the 58 concrete enumerated values consumed by Person/Membership/Family module designs
(gender, marital status, address type, document type, membership type, membership status,
relationship type). Must run after `01_master_category.sql`, since every `INSERT` resolves its
`master_category_pk` via `SELECT ... FROM nss.master_category mc ... WHERE mc.category_code =
'<CODE>'` joined against a `VALUES` literal — a subquery-driven pattern rather than hardcoded
UUIDs, since the category PKs are generated at category-insert time and aren't known in advance.

**Line-by-line explanation**

Each of the seven blocks follows the identical shape:
```sql
INSERT INTO nss.master_data (master_category_pk, value_code, value_name, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES (...), (...)) AS v(value_code, value_name, display_order)
WHERE mc.category_code = '<CATEGORY>';
```
The `CROSS JOIN` against a single-row-matching `master_category` (filtered by the `WHERE`) is
just a way to pair every literal `VALUES` row with that one category's PK without repeating the
UUID by hand.

**Row count: 58 total**, across 7 categories:

- **GENDER (3 rows):** `MALE`/Male/1, `FEMALE`/Female/2, `OTHER`/Other/3.
- **MARITAL_STATUS (5 rows):** `UNMARRIED`, `MARRIED`, `WIDOWED`, `DIVORCED`, `SEPARATED`
  (display_order 1–5, same order).
- **ADDRESS_TYPE (3 rows):** `PERMANENT`/Permanent Address/1, `CURRENT`/Current Address/2,
  `OFFICIAL`/Official Address/3.
- **DOCUMENT_TYPE (7 rows):** `PHOTO`, `ID_PROOF`, `ADDRESS_PROOF`, `CERTIFICATE`,
  `CORRESPONDENCE`, `PROPERTY_DOCUMENT`, `MEETING_MINUTES`.
- **MEMBERSHIP_TYPE (4 rows):** `PROBATIONARY`, `REGULAR`, `ASSOCIATE`, `HONORARY`.
- **MEMBERSHIP_STATUS (7 rows):** `ACTIVE`, `INACTIVE`, `SUSPENDED`, `TRANSFERRED`, `RESIGNED`,
  `EXPELLED`, `DECEASED`.
- **RELATIONSHIP_TYPE (29 rows)** — by far the largest block, covering the Indian family
  structure comprehensively for the future Family module's `family_relationship` table.
  Representative rows: `SPOUSE`/Spouse/1, `FATHER`/Father/2, `MOTHER`/Mother/3 (immediate
  family, orders 1–7); `FATHER_IN_LAW`/Father-in-Law/8 through `SISTER_IN_LAW`/Sister-in-Law/13
  (in-laws); `GRANDFATHER`/Grandfather/14 through `GRANDDAUGHTER`/Granddaughter/17
  (grandparents/grandchildren); `UNCLE`/Aunt/Nephew/Niece (18–21); `COUSIN`/Cousin/22 (a single
  ungendered catch-all, unlike the gendered pairs around it); `STEP_FATHER` through
  `STEP_DAUGHTER` (23–26, step-relations); `GUARDIAN`/Guardian/27 and `WARD`/Ward/28 (a notable
  non-blood-relation pair, included because guardianship is a real family-structure concern for
  the Family module, not just biological/marital relations); and a final catch-all
  `OTHER`/Other Relative/29.

  Sum check: 3+5+3+7+4+7+29 = **58**, matching the row count `03_validate.sh`/`.ps1` and
  `database/README.md` both expect.

---

### database/seed/01_foundation/03_id_sequence_master.sql

**Requirement**

Seeds the 9 business-ID sequence definitions that the application will use (once the
sequence-issuing logic is implemented) to mint permanent business identifiers for Person,
Sangha Sevi, and each level of the organizational hierarchy, plus Family and Document IDs.

**Line-by-line explanation**

```sql
INSERT INTO nss.id_sequence_master
    (sequence_code, sequence_name, prefix, current_value, padding_length)
VALUES (...)
```
Every row explicitly sets `current_value = 0` (no IDs issued yet) and a `padding_length` — all
`8` except `PERSON` at `10`.

**Row count: 9** (all rows listed — small, fully-enumerable):

| sequence_code | sequence_name | prefix | padding_length |
|---|---|---|---|
| `PERSON` | Person Code | `P` | 10 |
| `SANGHA_SEVI` | Sangha Sevi Code | `SS` | 8 |
| `ANCHALIKA` | Anchalika Code | `ANC` | 8 |
| `ZILLA` | Zilla Code | `ZL` | 8 |
| `SAKHA` | Sakha Code | `SKH` | 8 |
| `SAKHA_ASANA` | Sakha Asana Code | `SA` | 8 |
| `PATHA_CHAKRA` | Patha Chakra Code | `PC` | 8 |
| `FAMILY` | Family Code | `F` | 8 |
| `DOCUMENT` | Document Code | `DOC` | 8 |

Notable: `PERSON` is the only sequence with a 10-digit padding (vs. 8 for everything else) —
consistent with Person being expected to be the highest-cardinality entity in the system by a
wide margin (every member and every non-member family contact is a `person` row).

---

### database/seed/01_foundation/04_country.sql

**Requirement**

Seeds the 5 countries the schema currently recognizes. India is the operationally significant
one (NSS is an Odisha-based organization); the other four exist to support diaspora
members/addresses.

**Line-by-line explanation**

```sql
INSERT INTO nss.country (country_code, country_name, display_order)
VALUES ('IN', 'India', 1), ('US', 'United States', 2), ('GB', 'United Kingdom', 3),
       ('AU', 'Australia', 4), ('CA', 'Canada', 5);
```
A single plain literal `VALUES` list (no subquery needed — `country` has no parent to resolve).

**Row count: 5** (all rows listed):

| country_code | country_name | display_order |
|---|---|---|
| `IN` | India | 1 |
| `US` | United States | 2 |
| `GB` | United Kingdom | 3 |
| `AU` | Australia | 4 |
| `CA` | Canada | 5 |

---

### database/seed/01_foundation/05_state.sql

**Requirement**

Seeds every state/province/territory for all 5 seeded countries — full India coverage (needed
because NSS organizational units can, in principle, exist anywhere in India) plus full
subdivision coverage for the 4 diaspora countries.

**Line-by-line explanation**

Five blocks share the identical shape — a `CROSS JOIN` against a single-row-filtered `country`
paired with a literal `VALUES` list, same pattern as the `master_data` seed. Representative
sample (India block, showing the shape and a few rows out of 36; the other 4 country blocks are
structurally identical, just with different `WHERE c.country_code = '<CODE>'` filters and value
lists):

```sql
INSERT INTO nss.state (country_pk, state_code, state_name, display_order)
SELECT c.country_pk, v.state_code, v.state_name, v.display_order
FROM nss.country c
CROSS JOIN (VALUES
    -- States (28)
    ('AP', 'Andhra Pradesh',       1),
    ('AR', 'Arunachal Pradesh',    2),
    ...
    ('OD', 'Odisha',             19),
    ...
    ('WB', 'West Bengal',        28),
    -- Union Territories (8)
    ('AN', 'Andaman and Nicobar Islands', 29),
    ...
    ('DL', 'Delhi',                       32),
    ...
    ('PY', 'Puducherry',                  36)
) AS v(state_code, state_name, display_order)
WHERE c.country_code = 'IN';
```

**Row count: 112 total**, across 5 countries:

- **India (36 rows)** — all 28 states (display_order 1–28: Andhra Pradesh through West Bengal,
  alphabetical) plus all 8 union territories (display_order 29–36: Andaman and Nicobar Islands,
  Chandigarh, Dadra and Nagar Haveli and Daman and Diu, Delhi, Jammu and Kashmir, Ladakh,
  Lakshadweep, Puducherry). Example rows: `('OD', 'Odisha', 19)`, `('DL', 'Delhi', 32)`.
- **United States (51 rows)** — all 50 states (Alabama through Wyoming, alphabetical,
  display_order 1–50) plus the District of Columbia (order 51).
- **United Kingdom (4 rows)** — `ENG`/England, `SCO`/Scotland, `WLS`/Wales, `NIR`/Northern
  Ireland.
- **Australia (8 rows)** — the 6 states (`NSW`, `VIC`, `QLD`, `WA`, `SA`, `TAS`) plus 2
  territories (`ACT`, `NT`).
- **Canada (13 rows)** — the 10 provinces plus 3 territories (`NT`/Northwest Territories,
  `YT`/Yukon, `NU`/Nunavut).

Sum check: 36 + 51 + 4 + 8 + 13 = **112**, matching the expected row count in
`03_validate.sh`/`.ps1` and `database/README.md`.

Notable exception: several 2-letter `state_code` values are **reused across different
countries** — e.g. `AR` means Arkansas under `US` but Arunachal Pradesh under `IN`; `GA` means
Georgia under `US` but Goa under `IN`; `NL` means Newfoundland and Labrador under `CA` but
Nagaland under `IN`. This is not a bug — `uq_state_country_code` in the DDL scopes uniqueness to
`(country_pk, state_code)`, so cross-country reuse is explicitly permitted by design.

---

### database/seed/01_foundation/06_district.sql

**Requirement**

Seeds every district for all 28 Indian states and all 8 Indian union territories — the deepest
and most operationally relevant tier of the location hierarchy for NSS's own organizational
addresses, since NSS is Odisha-headquartered and its physical units are named/located at the
district level. Deliberately does **not** seed district-level subdivisions for the 4 diaspora
countries (the file's closing comment explains this explicitly: those subdivisions are "too
numerous and not operationally required for NSS at seed time" and would be populated at runtime
if ever needed).

**Line-by-line explanation**

36 blocks share the identical shape — one per Indian state/UT, same `CROSS JOIN` +
subquery-resolution pattern as `05_state.sql`, filtered this time on the parent `state` row
rather than `country`. Representative sample (the Odisha block in full — the largest, at 30
districts — and the smallest block, Lakshadweep's single district, showing both ends of the
size range):

```sql
-- =========================================================
-- INDIA — ODISHA (30 districts)
-- =========================================================

INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.district_code, v.district_name, v.display_order
FROM nss.state s
CROSS JOIN (VALUES
    ('ANG', 'Angul',            1),
    ('BLG', 'Balangir',         2),
    ...
    ('KHD', 'Khordha',         19),
    ...
    ('PUR', 'Puri',            26),
    ...
    ('SDG', 'Sundargarh',      30)
) AS v(district_code, district_name, display_order)
WHERE s.state_code = 'OD';

-- =========================================================
-- INDIA — LAKSHADWEEP (1 district)
-- =========================================================

INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.district_code, v.district_name, v.display_order
FROM nss.state s
CROSS JOIN (VALUES
    ('LKD', 'Lakshadweep', 1)
) AS v(district_code, district_name, display_order)
WHERE s.state_code = 'LD';
```

**Row count: 786**, one block per Indian state/UT (36 blocks total: 28 states + 8 UTs). Sizes
range from Odisha's 30 districts and Andhra Pradesh's/Arunachal Pradesh's 26 districts each,
down to single-district union territories. Representative rows:

- Odisha (`OD`, 30 districts, display_order 1–30): `('ANG', 'Angul', 1)`, `('CTC', 'Cuttack',
  7)`, `('KHD', 'Khordha', 19)`, `('PUR', 'Puri', 26)` — Puri and Khordha are directly relevant
  to NSS's Bhubaneswar/Puri headquarters addresses.
- Andhra Pradesh (`AP`, 26 districts): `('VIS', 'Visakhapatnam', 23)`.
- Lakshadweep (`LD`, 1 district — smallest block in the file): `('LKD', 'Lakshadweep', 1)`.

Notable exception: `district_code` values are **reused across states**, exactly parallel to the
`state_code` reuse pattern above — e.g. `KDP` is used both for Kadapa (`AP`) and Kandhamal
(`OD`); `NL` is used for Nagaland's... no — this is at the district level: uniqueness is scoped
per-state (`uq_district_state_code UNIQUE (state_pk, district_code)`), so short 3-letter codes
are freely reused across different states' district lists without collision.

---

### database/seed/01_foundation/07_system_setting.sql

**Requirement**

Seeds 4 initial application-wide configuration values. The file's own header notes these are
"illustrative defaults" — actual production values would be configured during deployment, not
hardcoded here permanently.

**Line-by-line explanation**

```sql
INSERT INTO nss.system_setting (setting_key, setting_value, description, data_type)
VALUES (...)
```

**Row count: 4** (all rows listed):

| setting_key | setting_value | data_type |
|---|---|---|
| `CURRENT_MEMBERSHIP_YEAR` | `2026-2027` | STRING |
| `DEFAULT_COUNTRY` | `IN` | STRING |
| `PASSWORD_EXPIRY_DAYS` | `90` | INTEGER |
| `MAX_LOGIN_ATTEMPTS` | `5` | INTEGER |

Notable: `PASSWORD_EXPIRY_DAYS` and `MAX_LOGIN_ATTEMPTS` are Authentication-module concerns
seeded here in Foundation ahead of the Authentication module's own tables being built — the
generic `system_setting` table is deliberately module-agnostic, so it can hold configuration for
not-yet-implemented modules without needing schema changes later.

---

### database/seed/01_foundation/08_postal_code.sql

**Requirement**

Seeds exactly the 2 postal codes needed by the Organization seed data (`03_organization.sql`
resolves both `751022` and `752001` via subquery). The file's own header is explicit that this
is a "minimal bootstrap set" — full national postal-code data loading is deferred to a future
task, not attempted here.

**Line-by-line explanation**

```sql
-- Bhubaneswar — Kendra (Satsikshya Mandir, Unit-9)
INSERT INTO nss.postal_code (country_pk, state_pk, postal_code, post_office_name)
SELECT c.country_pk, s.state_pk, '751022', 'Unit 9 SO'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD';

-- Puri — Nilachala Kutira, Smruti Mandira (Swargadwar area)
INSERT INTO nss.postal_code (country_pk, state_pk, postal_code, post_office_name)
SELECT c.country_pk, s.state_pk, '752001', 'Puri HO'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD';
```

Two statements, using an explicit `JOIN` (rather than the `CROSS JOIN`-against-VALUES pattern
used elsewhere) since each statement inserts a single literal row and needs to resolve both a
country and a state PK together.

**Row count: 2** (both rows listed):

| postal_code | post_office_name | Context |
|---|---|---|
| `751022` | Unit 9 SO | Bhubaneswar — Kendra (Satsikshya Mandir, Unit-9) |
| `752001` | Puri HO | Puri — Nilachala Kutira / Smruti Mandira (Swargadwar area) |

Both rows resolve to `country_code = 'IN'`, `state_code = 'OD'` (Odisha) — every seeded postal
code today is in Odisha, matching where NSS's three seeded organizations physically are.

---

### database/ddl/02_organization/01_organization_type_master.sql

**Requirement**

Defines `nss.organization_type_master` — the fixed catalogue of organizational unit types
(Kendra, Anchalika, Zilla, Sakha, etc.). Depth 0. Without it, `organization` (Depth 3) has no
type to classify itself by, and there would be no frozen, database-backed answer to "what kinds
of organizational units exist in NSS's structure."

**Line-by-line explanation**

```sql
CREATE TABLE nss.organization_type_master
(
    organization_type_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    organization_type_code VARCHAR(30) NOT NULL,

    organization_type_name VARCHAR(100) NOT NULL,

    description VARCHAR(500) NULL,

    sort_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

Columns: `organization_type_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`;
`organization_type_code VARCHAR(30) NOT NULL`; `organization_type_name VARCHAR(100) NOT NULL`;
`description VARCHAR(500) NULL` — note this is a bounded `VARCHAR(500)`, not `TEXT`, unlike most
other `description` columns in the schema; `sort_order INTEGER NOT NULL DEFAULT 0`; standard
four-column audit block (`created_at`/`updated_at`/`deleted_at`/`is_active`).

```sql
    CONSTRAINT uq_organization_type_code
        UNIQUE (organization_type_code),

    CONSTRAINT uq_organization_type_name
        UNIQUE (organization_type_name),

    CONSTRAINT chk_organization_type_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_organization_type_active
    ON nss.organization_type_master (is_active);
```

Constraints: `uq_organization_type_code UNIQUE (organization_type_code)`,
`uq_organization_type_name UNIQUE (organization_type_name)`, `chk_organization_type_soft_delete`
standard invariant.

Indexes: only `idx_organization_type_active (is_active)` — no code-lookup index, unlike most
other master tables in this document (a minor asymmetry, since `organization_type_code` is a
`UNIQUE` column and Postgres does create an implicit index for the unique constraint itself,
which likely explains why a redundant explicit index wasn't added).

---

### database/ddl/02_organization/02_organization_status_master.sql

**Requirement**

Defines `nss.organization_status_master` — the fixed catalogue of organizational lifecycle
statuses (Proposed → Approved → Active → Inactive/Suspended → Archived). Depth 0, sibling to
`organization_type_master`. Without it, `organization` has no way to express current lifecycle
state.

**Line-by-line explanation**

```sql
CREATE TABLE nss.organization_status_master
(
    organization_status_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    organization_status_code VARCHAR(30) NOT NULL,

    organization_status_name VARCHAR(100) NOT NULL,

    description VARCHAR(500) NULL,

    sort_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

Identical column shape to `organization_type_master`: `organization_status_pk UUID PRIMARY KEY
DEFAULT gen_random_uuid()`; `organization_status_code VARCHAR(30) NOT NULL`;
`organization_status_name VARCHAR(100) NOT NULL`; `description VARCHAR(500) NULL`; `sort_order
INTEGER NOT NULL DEFAULT 0`; standard four-column audit block.

```sql
    CONSTRAINT uq_organization_status_code
        UNIQUE (organization_status_code),

    CONSTRAINT uq_organization_status_name
        UNIQUE (organization_status_name),

    CONSTRAINT chk_organization_status_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX idx_organization_status_active
    ON nss.organization_status_master (is_active);
```

Constraints: `uq_organization_status_code UNIQUE (organization_status_code)`,
`uq_organization_status_name UNIQUE (organization_status_name)`,
`chk_organization_status_soft_delete` standard invariant.

Indexes: `idx_organization_status_active (is_active)` only — same pattern as the type master.

---

### database/ddl/02_organization/03_organization.sql

**Requirement**

Defines `nss.organization` — every physical/administrative organizational unit in NSS's
hierarchy (Kendra, Anchalika Sangha, Zilla Sangha, Sakha Sangha, Sakha Asana, Patha Chakra,
Nilachala Kutira, Smruti Mandira), self-referencing to express parent/child structure. Depth 3
(depends on `organization_type_master`, `organization_status_master`, and the location tables
`country`/`state`/`district`/`city_village`/`postal_code`, plus itself via the self-referencing
FK). Without this table, NSS's organizational structure — the entire reason the "Organization"
module exists — has no physical representation at all.

**Line-by-line explanation**

Identity, classification, and hierarchy columns:

```sql
CREATE TABLE nss.organization
(
    organization_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- Business identifier (system-generated for multi-instance
    -- org types; NULL for unique organizations identified by
    -- organization_code alone)
    organization_id VARCHAR(20) NULL,

    organization_name VARCHAR(200) NOT NULL,

    -- Classification
    organization_type_pk UUID NOT NULL,

    -- Current lifecycle status
    organization_status_pk UUID NOT NULL,

    -- Hierarchy: immediate parent (NULL = apex)
    parent_organization_pk UUID NULL,

    -- Organization short code (3-5 chars, unique)
    organization_code VARCHAR(10) NULL,
```

- `organization_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`.
- `organization_id VARCHAR(20) NULL` — a *system-generated business identifier*, used only for
  multi-instance organization types (e.g. many Sakhas each need their own sequential ID via
  `id_sequence_master`'s `SAKHA` sequence); left `NULL` for the three unique, one-off
  organizations (Kendra, Nilachala Kutira, Smruti Mandira) that are identified by
  `organization_code` alone.
- `organization_name VARCHAR(200) NOT NULL`.
- `organization_type_pk UUID NOT NULL` — FK, classification.
- `organization_status_pk UUID NOT NULL` — FK, current lifecycle state.
- `parent_organization_pk UUID NULL` — self-referencing FK; `NULL` means this organization is
  an apex node (has no parent).
- `organization_code VARCHAR(10) NULL` — a short, hand-assigned unique code (e.g. `KEN`, `NKT`,
  `SMR` in the seed data below); nullable, but unique when present.

Inline address/location and coordinate columns:

```sql
    -- Inline address (current address, v1 design)
    address_line_1 VARCHAR(200) NULL,

    address_line_2 VARCHAR(200) NULL,

    district_pk UUID NULL,

    state_pk UUID NULL,

    country_pk UUID NULL,

    city_village_pk UUID NULL,

    postal_code_pk UUID NULL,

    -- Physical coordinates of this organization
    latitude NUMERIC(10,7) NULL,

    longitude NUMERIC(10,7) NULL,
```

- `address_line_1 VARCHAR(200) NULL`, `address_line_2 VARCHAR(200) NULL` — inline address
  fields; the file's header note explicitly records the frozen design decision that
  Organization does **not** get a separate `organization_address` table (unlike Person's
  prototype, which does have `person_address`).
- `district_pk UUID NULL`, `state_pk UUID NULL`, `country_pk UUID NULL`, `city_village_pk UUID
  NULL`, `postal_code_pk UUID NULL` — five separate, independently nullable location FKs (not a
  single FK to a combined location-map row) — an organization can specify as much or as little
  of its address hierarchy as is known.
- `latitude NUMERIC(10,7) NULL`, `longitude NUMERIC(10,7) NULL` — physical coordinates, bounded
  by CHECK constraints below.

Audit block, constraints, and indexes:

```sql
    -- Audit
    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    -- Unique constraints
    CONSTRAINT uq_organization_id
        UNIQUE (organization_id),

    CONSTRAINT uq_organization_code
        UNIQUE (organization_code),

    -- Foreign keys: classification + lifecycle
    CONSTRAINT fk_organization_type
        FOREIGN KEY (organization_type_pk)
        REFERENCES nss.organization_type_master (organization_type_pk),

    CONSTRAINT fk_organization_status
        FOREIGN KEY (organization_status_pk)
        REFERENCES nss.organization_status_master (organization_status_pk),

    -- Self-referencing FK: hierarchy
    CONSTRAINT fk_organization_parent
        FOREIGN KEY (parent_organization_pk)
        REFERENCES nss.organization (organization_pk),

    -- Location FKs (Foundation tables)
    CONSTRAINT fk_organization_district
        FOREIGN KEY (district_pk)
        REFERENCES nss.district (district_pk),

    CONSTRAINT fk_organization_state
        FOREIGN KEY (state_pk)
        REFERENCES nss.state (state_pk),

    CONSTRAINT fk_organization_country
        FOREIGN KEY (country_pk)
        REFERENCES nss.country (country_pk),

    CONSTRAINT fk_organization_city_village
        FOREIGN KEY (city_village_pk)
        REFERENCES nss.city_village (city_village_pk),

    CONSTRAINT fk_organization_postal_code
        FOREIGN KEY (postal_code_pk)
        REFERENCES nss.postal_code (postal_code_pk),

    -- Coordinate range validation
    CONSTRAINT chk_organization_latitude
        CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <= 90)),

    CONSTRAINT chk_organization_longitude
        CHECK (longitude IS NULL OR (longitude >= -180 AND longitude <= 180)),

    -- Soft-delete consistency
    CONSTRAINT chk_organization_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

-- Indexes
CREATE INDEX idx_organization_type
    ON nss.organization (organization_type_pk);

CREATE INDEX idx_organization_status
    ON nss.organization (organization_status_pk);

CREATE INDEX idx_organization_parent
    ON nss.organization (parent_organization_pk);

CREATE INDEX idx_organization_country
    ON nss.organization (country_pk);

CREATE INDEX idx_organization_state
    ON nss.organization (state_pk);

CREATE INDEX idx_organization_district
    ON nss.organization (district_pk);

CREATE INDEX idx_organization_city_village
    ON nss.organization (city_village_pk);

CREATE INDEX idx_organization_postal_code
    ON nss.organization (postal_code_pk);

CREATE INDEX idx_organization_active
    ON nss.organization (is_active);

CREATE INDEX idx_organization_name
    ON nss.organization USING gin (organization_name gin_trgm_ops);
```

- Standard four-column audit block (`created_at`/`updated_at`/`deleted_at`/`is_active`) — no
  actor columns, consistent with the rest of Organization/Foundation.
- `uq_organization_id UNIQUE (organization_id)` and `uq_organization_code UNIQUE
  (organization_code)` — both unique when non-`NULL` (multiple `NULL`s are permitted by
  standard SQL unique-constraint semantics, which is exactly what allows all three seeded
  unique organizations to share `organization_id = NULL`).
- `fk_organization_type FOREIGN KEY (organization_type_pk) REFERENCES
  nss.organization_type_master (organization_type_pk)`.
- `fk_organization_status FOREIGN KEY (organization_status_pk) REFERENCES
  nss.organization_status_master (organization_status_pk)`.
- `fk_organization_parent FOREIGN KEY (parent_organization_pk) REFERENCES nss.organization
  (organization_pk)` — the self-referencing FK; the file's header explains this is only
  possible in the base `CREATE TABLE` (rather than needing a later `ALTER TABLE`, as with
  Bootstrap's Pass-2 actor FKs) because the table already exists by the time this constraint is
  declared, even though it's declared inline in the same statement that creates the table.
- `fk_organization_district`, `fk_organization_state`, `fk_organization_country`,
  `fk_organization_city_village`, `fk_organization_postal_code` — five FKs to the Foundation
  location tables, each referencing the location table's own PK.
- `chk_organization_latitude CHECK (latitude IS NULL OR (latitude >= -90 AND latitude <=
  90))` and `chk_organization_longitude CHECK (longitude IS NULL OR (longitude >= -180 AND
  longitude <= 180))` — standard geographic coordinate range validation, each independently
  optional.
- `chk_organization_soft_delete` — standard invariant.

The file's header also documents a design decision that is explicitly **not** expressed as a
column: `hierarchical_level` is not stored — an organization's "level" is fully derived from
`organization_type_pk` (which type it is) combined with walking the `parent_organization_pk`
chain, rather than being cached as a denormalized integer.

Indexes: `idx_organization_type (organization_type_pk)`, `idx_organization_status
(organization_status_pk)`, `idx_organization_parent (parent_organization_pk)`,
`idx_organization_country (country_pk)`, `idx_organization_state (state_pk)`,
`idx_organization_district (district_pk)`, `idx_organization_city_village (city_village_pk)`,
`idx_organization_postal_code (postal_code_pk)`, `idx_organization_active (is_active)`, and
`idx_organization_name USING gin (organization_name gin_trgm_ops)` (fuzzy search) — every single
FK column gets its own index, reflecting how central hierarchy/location traversal is expected to
be for this table.

---

### database/seed/02_organization/01_organization_type_master.sql

**Requirement**

Seeds the 8 frozen organization types that every `organization` row must classify itself under.

**Line-by-line explanation**

```sql
INSERT INTO nss.organization_type_master
    (organization_type_code, organization_type_name, description, sort_order)
VALUES (...)
```

**Row count: 8** (all rows listed):

| organization_type_code | organization_type_name | description | sort_order |
|---|---|---|---|
| `KENDRA` | Kendra Sangha | Central Body — apex organization | 1 |
| `NILACHALA_KUTIRA` | Nilachala Kutira | Eternal Abode - Puri | 2 |
| `SMRUTI_MANDIRA` | Smruti Mandira | Nigamananda Smruti Mandir | 3 |
| `ANCHALIKA_SANGHA` | Anchalika Sangha | Administrative unit — intermediate organizational level | 4 |
| `ZILLA_SANGHA` | Zilla Sangha | Administrative unit — intermediate organizational level | 5 |
| `SAKHA_SANGHA` | Sakha Sangha | Physical Sangha location — branch with own building | 6 |
| `SAKHA_ASANA` | Sakha Asana | Approved Sakha without own building | 7 |
| `PATHA_CHAKRA` | Patha Chakra | Study Circle | 8 |

Notable: three of the eight types (`KENDRA`, `NILACHALA_KUTIRA`, `SMRUTI_MANDIRA`) are
**singleton** types — exactly one organization of each will ever exist (seeded in
`03_organization.sql` below) — while the other five (`ANCHALIKA_SANGHA` through
`PATHA_CHAKRA`) are multi-instance types intended for many future organization rows each, which
is why `organization.organization_id` (the sequence-generated business ID) only makes sense for
those five.

---

### database/seed/02_organization/02_organization_status_master.sql

**Requirement**

Seeds the 6 frozen organizational lifecycle statuses every `organization` row's
`organization_status_pk` must reference.

**Line-by-line explanation**

```sql
INSERT INTO nss.organization_status_master
    (organization_status_code, organization_status_name, description, sort_order)
VALUES (...)
```

**Row count: 6** (all rows listed):

| organization_status_code | organization_status_name | sort_order |
|---|---|---|
| `PROPOSED` | Proposed | 1 |
| `APPROVED` | Approved | 2 |
| `ACTIVE` | Active | 3 |
| `INACTIVE` | Inactive | 4 |
| `SUSPENDED` | Suspended | 5 |
| `ARCHIVED` | Archived | 6 |

The six statuses form a linear lifecycle progression from proposal through governance approval
to operation, with `INACTIVE`/`SUSPENDED` as two distinct non-operational states (temporary vs.
governance-imposed) and `ARCHIVED` as the permanent terminal state — consistent with the
project's "History Never Deleted" principle (an archived organization's row is retained
forever, never hard-deleted).

---

### database/seed/02_organization/03_organization.sql

**Requirement**

Seeds the three actual, named, unique organizations that exist in NSS's structure today: the
apex Kendra Sangha itself, Nilachala Kutira (Puri), and Smruti Mandira (the Nigamananda
memorial temple). These are the only organization rows that exist prior to any live
administrative data entry — every other Anchalika/Zilla/Sakha/Patha Chakra will be created at
runtime through the (not-yet-built) Organization module UI.

**Line-by-line explanation**

Representative block (Kendra Sangha — the other two blocks, Nilachala Kutira and Smruti
Mandira, follow the identical shape with different literal values and `WHERE` filters):

```sql
-- -------------------------------------------------
-- Kendra Sangha (apex governing body)
-- -------------------------------------------------

INSERT INTO nss.organization
    (organization_name, organization_type_pk,
     organization_status_pk, parent_organization_pk,
     organization_code,
     address_line_1, address_line_2, postal_code_pk, country_pk)
SELECT
    'Nilachala Saraswata Sangha',
    ot.organization_type_pk,
    os.organization_status_pk,
    NULL,
    'KEN',
    'Satsikshya Mandir, A/4, Unit-9',
    'Bhubaneswar',
    pc.postal_code_pk,
    c.country_pk
FROM nss.organization_type_master ot
CROSS JOIN nss.organization_status_master os
CROSS JOIN nss.country c
CROSS JOIN nss.postal_code pc
WHERE ot.organization_type_code = 'KENDRA'
  AND os.organization_status_code = 'ACTIVE'
  AND c.country_code = 'IN'
  AND pc.postal_code = '751022'
  AND pc.country_pk = c.country_pk;
```

A four-way `CROSS JOIN` across all four parent lookup tables, each narrowed to exactly one row
by the `WHERE` clause, so the `SELECT` resolves to exactly one row of PKs to insert. All three
blocks explicitly pass `parent_organization_pk = NULL` — the file's header confirms all three
are peers (no parent/child relationship among them) and all three are seeded with
`organization_status_code = 'ACTIVE'` from the start. `city_village_pk` is left unset (omitted
from the column list, so it defaults to `NULL`) because, per the header comment, Foundation's
`city_village` seed data doesn't exist yet.

**Row count: 3** (all rows listed):

| organization_name | type | organization_code | address_line_1 | address_line_2 | postal_code |
|---|---|---|---|---|---|
| Nilachala Saraswata Sangha | KENDRA | `KEN` | Satsikshya Mandir, A/4, Unit-9 | Bhubaneswar | `751022` |
| Nilachala Kutira | NILACHALA_KUTIRA | `NKT` | Puri | `NULL` | `752001` |
| Sri Shri Nigamananda Smruti Mandir | SMRUTI_MANDIRA | `SMR` | Swargadwar | Puri | `752001` |

Notable: the Kendra Sangha row's `organization_name` ("Nilachala Saraswata Sangha") is the
*full organizational name of NSS itself*, not literally the word "Kendra" — the apex
organization row represents the whole Sangha's central body, distinct from its
`organization_type_code = 'KENDRA'` classification. The file's own header also explicitly notes
all seeded addresses are editable at runtime — these are initial values only, not frozen facts.

---

### database/ddl/03_person/01_person_master_tables.sql

> **SUPERSEDED PROTOTYPE — not executed by `02_build.sh`/`02_build.ps1`, kept for reference
> only.** Uses dedicated per-domain master tables instead of the generic
> `master_category`/`master_data` pattern that Foundation actually implements — the values this
> file's tables would hold (gender, marital status, address type) are already covered by
> `master_data` rows seeded under the `GENDER`, `MARITAL_STATUS`, and `ADDRESS_TYPE` categories.
> This duplication is precisely why the prototype was superseded.

**Requirement (as originally written)**

Defines three small per-domain lookup tables (`gender_master`, `marital_status_master`,
`address_type_master`) intended to back the prototype `person` table's `gender_pk` and
`marital_status_pk` FKs, and the prototype `person_address` table's `address_type_pk` FK.

**Line-by-line explanation**

All three tables share an identical shape and a notable difference from every Foundation table:
none of the `CREATE TABLE` statements are schema-qualified (`CREATE TABLE gender_master`, not
`CREATE TABLE nss.gender_master`) — they would land in whatever the connecting session's default
schema is, not explicitly `nss`, unlike every other table in this document.

```sql
CREATE TABLE gender_master
(
gender_pk UUID PRIMARY KEY
DEFAULT gen_random_uuid(),


gender_code VARCHAR(20) NOT NULL,

gender_name VARCHAR(50) NOT NULL,

display_order INTEGER NOT NULL,

created_at TIMESTAMPTZ NOT NULL
    DEFAULT CURRENT_TIMESTAMP,

is_active BOOLEAN NOT NULL
    DEFAULT TRUE,

CONSTRAINT uq_gender_master_code
    UNIQUE (gender_code),

CONSTRAINT uq_gender_master_name
    UNIQUE (gender_name)


);

CREATE INDEX idx_gender_master_active
ON gender_master (is_active);
```

- **`gender_master`**: `gender_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`; `gender_code
  VARCHAR(20) NOT NULL`; `gender_name VARCHAR(50) NOT NULL`; `display_order INTEGER NOT NULL`
  — **no `DEFAULT`** on `display_order` here, unlike every Foundation equivalent (`DEFAULT 0`),
  meaning every insert must supply it explicitly or fail; `created_at TIMESTAMPTZ NOT NULL
  DEFAULT CURRENT_TIMESTAMP`; `is_active BOOLEAN NOT NULL DEFAULT TRUE`. Constraints:
  `uq_gender_master_code UNIQUE (gender_code)`, `uq_gender_master_name UNIQUE (gender_name)`.
  Notably **no `updated_at`, no `deleted_at`, and no soft-delete CHECK constraint** — `is_active`
  exists but nothing enforces that `is_active = FALSE` correlates with any deletion timestamp,
  because there is no deletion timestamp column at all. Index: `idx_gender_master_active
  (is_active)`.

```sql
CREATE TABLE marital_status_master
(
marital_status_pk UUID PRIMARY KEY
DEFAULT gen_random_uuid(),


marital_status_code VARCHAR(30) NOT NULL,

marital_status_name VARCHAR(100) NOT NULL,

display_order INTEGER NOT NULL,

created_at TIMESTAMPTZ NOT NULL
    DEFAULT CURRENT_TIMESTAMP,

is_active BOOLEAN NOT NULL
    DEFAULT TRUE,

CONSTRAINT uq_marital_status_code
    UNIQUE (marital_status_code),

CONSTRAINT uq_marital_status_name
    UNIQUE (marital_status_name)


);

CREATE INDEX idx_marital_status_active
ON marital_status_master (is_active);
```

- **`marital_status_master`**: identical shape — `marital_status_pk`, `marital_status_code
  VARCHAR(30) NOT NULL`, `marital_status_name VARCHAR(100) NOT NULL`, `display_order INTEGER NOT
  NULL` (no default), `created_at`, `is_active`; unique constraints on both code and name; same
  missing-soft-delete-tracking gap; index on `is_active`.

```sql
CREATE TABLE address_type_master
(
address_type_pk UUID PRIMARY KEY
DEFAULT gen_random_uuid(),


address_type_code VARCHAR(30) NOT NULL,

address_type_name VARCHAR(100) NOT NULL,

display_order INTEGER NOT NULL,

created_at TIMESTAMPTZ NOT NULL
    DEFAULT CURRENT_TIMESTAMP,

is_active BOOLEAN NOT NULL
    DEFAULT TRUE,

CONSTRAINT uq_address_type_code
    UNIQUE (address_type_code),

CONSTRAINT uq_address_type_name
    UNIQUE (address_type_name)


);

CREATE INDEX idx_address_type_active
ON address_type_master (is_active);
```

- **`address_type_master`**: identical shape again — `address_type_pk`, `address_type_code
  VARCHAR(30) NOT NULL`, `address_type_name VARCHAR(100) NOT NULL`, `display_order INTEGER NOT
  NULL` (no default), `created_at`, `is_active`; unique constraints on both; same gap; index on
  `is_active`.

---

### database/ddl/03_person/02_person.sql

> **SUPERSEDED PROTOTYPE — not executed by `02_build.sh`/`02_build.ps1`, kept for reference
> only.** Will be rewritten against the frozen `master_category`/`master_data` pattern (see
> `feature/person-ddl` and `database/README.md` → "Superseded Artifacts").

**Requirement (as originally written)**

Defines the prototype `person` table — the core identity record every human in the system
(member or not) would attach to, per the project's frozen "Person ≠ Member" principle.

**Line-by-line explanation**

```sql
CREATE TABLE person
(
    person_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    person_code VARCHAR(20) NOT NULL,

    first_name VARCHAR(100) NOT NULL,

    middle_name VARCHAR(100) NULL,

    last_name VARCHAR(100) NULL,

    gender_pk UUID NOT NULL,

    date_of_birth DATE NULL,

    country_phone_code VARCHAR(10) NULL,

    mobile_number VARCHAR(20) NULL,

    email VARCHAR(255) NULL,

    marital_status_pk UUID NULL,

    remarks TEXT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

Columns: `person_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`; `person_code VARCHAR(20) NOT
NULL` — intended to be issued from the `PERSON` row in `id_sequence_master`, though nothing in
this DDL enforces that link (it's plain `VARCHAR`, populated by application logic); `first_name
VARCHAR(100) NOT NULL`; `middle_name VARCHAR(100) NULL`; `last_name VARCHAR(100) NULL` —
nullable, allowing single-name persons; `gender_pk UUID NOT NULL` — FK, required; `date_of_birth
DATE NULL`; `country_phone_code VARCHAR(10) NULL`; `mobile_number VARCHAR(20) NULL`; `email
VARCHAR(255) NULL`; `marital_status_pk UUID NULL` — FK, optional; `remarks TEXT NULL`;
`created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP`, `updated_at TIMESTAMPTZ NULL`,
`deleted_at TIMESTAMPTZ NULL`, `is_active BOOLEAN NOT NULL DEFAULT TRUE`.

```sql
    CONSTRAINT uq_person_code
        UNIQUE (person_code),

    CONSTRAINT uq_person_mobile
        UNIQUE
        (
            country_phone_code,
            mobile_number
        ),

    CONSTRAINT fk_person_gender
        FOREIGN KEY (gender_pk)
        REFERENCES gender_master(gender_pk),

    CONSTRAINT fk_person_marital_status
        FOREIGN KEY (marital_status_pk)
        REFERENCES marital_status_master(marital_status_pk),

    CONSTRAINT chk_person_contact_required
        CHECK
        (
            mobile_number IS NOT NULL
            OR
            email IS NOT NULL
        ),

    CONSTRAINT chk_person_mobile_pair
        CHECK
        (
            (
                country_phone_code IS NULL
                AND mobile_number IS NULL
            )
            OR
            (
                country_phone_code IS NOT NULL
                AND mobile_number IS NOT NULL
            )
        )
);

CREATE INDEX idx_person_code
    ON person(person_code);

CREATE INDEX idx_person_first_name
    ON person(first_name);

CREATE INDEX idx_person_last_name
    ON person(last_name);

CREATE INDEX idx_person_mobile
    ON person(country_phone_code, mobile_number);

CREATE INDEX idx_person_email
    ON person(email);

CREATE INDEX idx_person_gender
    ON person(gender_pk);

CREATE INDEX idx_person_marital_status
    ON person(marital_status_pk);

CREATE INDEX idx_person_is_active
    ON person(is_active);
```

Constraints:
- `uq_person_code UNIQUE (person_code)`.
- `uq_person_mobile UNIQUE (country_phone_code, mobile_number)` — a composite uniqueness rule
  (the same raw mobile number is allowed to recur across different country codes, but not
  within the same country code).
- `fk_person_gender FOREIGN KEY (gender_pk) REFERENCES gender_master(gender_pk)` and
  `fk_person_marital_status FOREIGN KEY (marital_status_pk) REFERENCES
  marital_status_master(marital_status_pk)` — both unqualified references (no `nss.` prefix,
  consistent with this prototype's schema-unqualified style throughout).
- `chk_person_contact_required CHECK (mobile_number IS NOT NULL OR email IS NOT NULL)` — at
  least one contact channel is mandatory.
- `chk_person_mobile_pair CHECK ((country_phone_code IS NULL AND mobile_number IS NULL) OR
  (country_phone_code IS NOT NULL AND mobile_number IS NOT NULL))` — the phone code and number
  must be supplied together or not at all; you can't have one without the other.

Notably, unlike every Foundation table, there is **no soft-delete CHECK constraint** here even
though `deleted_at` and `is_active` both exist as columns — the invariant that other tables
enforce mechanically is simply absent in this prototype.

Indexes: `idx_person_code (person_code)`, `idx_person_first_name (first_name)`,
`idx_person_last_name (last_name)`, `idx_person_mobile (country_phone_code, mobile_number)`,
`idx_person_email (email)`, `idx_person_gender (gender_pk)`, `idx_person_marital_status
(marital_status_pk)`, `idx_person_is_active (is_active)`.

---

### database/ddl/03_person/03_person_address.sql

> **SUPERSEDED PROTOTYPE — not executed by `02_build.sh`/`02_build.ps1`, kept for reference
> only.**

**Requirement (as originally written)**

Defines the prototype `person_address` table — one or more addresses per person, each typed
(permanent/current/official) and located via the Foundation `city_village_postal_code_map`
table, with exactly one address per person flaggable as primary.

**Line-by-line explanation**

```sql
CREATE TABLE person_address
(
    person_address_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    person_pk UUID NOT NULL,

    address_type_pk UUID NOT NULL,

    address_line_1 VARCHAR(255) NOT NULL,

    address_line_2 VARCHAR(255) NULL,

    landmark VARCHAR(255) NULL,

    city_village_postal_code_map_pk UUID NOT NULL,

    is_primary BOOLEAN NOT NULL
        DEFAULT FALSE,

    remarks TEXT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,
```

Columns: `person_address_pk UUID PRIMARY KEY DEFAULT gen_random_uuid()`; `person_pk UUID NOT
NULL` — FK to `person`; `address_type_pk UUID NOT NULL` — FK to `address_type_master`;
`address_line_1 VARCHAR(255) NOT NULL`; `address_line_2 VARCHAR(255) NULL`; `landmark
VARCHAR(255) NULL`; `city_village_postal_code_map_pk UUID NOT NULL` — FK, and notably references
the Foundation **map** table directly (not `city_village_pk` and `postal_code_pk` as two
separate FKs) — one address row pins down both the locality and the specific PIN code
simultaneously via a single join-table row; `is_primary BOOLEAN NOT NULL DEFAULT FALSE`;
`remarks TEXT NULL`; standard four-column audit block (`created_at`/`updated_at`/`deleted_at`/
`is_active`).

```sql
    CONSTRAINT fk_person_address_person
        FOREIGN KEY (person_pk)
        REFERENCES person(person_pk),

    CONSTRAINT fk_person_address_type
        FOREIGN KEY (address_type_pk)
        REFERENCES address_type_master(address_type_pk),

    CONSTRAINT fk_person_address_location
        FOREIGN KEY (city_village_postal_code_map_pk)
        REFERENCES city_village_postal_code_map(city_village_postal_code_map_pk)
);

-- =====================================================
-- Indexes
-- =====================================================

CREATE INDEX idx_person_address_person
    ON person_address(person_pk);

CREATE INDEX idx_person_address_type
    ON person_address(address_type_pk);

CREATE INDEX idx_person_address_location
    ON person_address(city_village_postal_code_map_pk);

CREATE INDEX idx_person_address_active
    ON person_address(is_active);

-- =====================================================
-- Only One Primary Address Per Person
-- =====================================================

CREATE UNIQUE INDEX uq_person_primary_address
ON person_address(person_pk)
WHERE is_primary = TRUE;
```

Constraints: `fk_person_address_person FOREIGN KEY (person_pk) REFERENCES person(person_pk)`;
`fk_person_address_type FOREIGN KEY (address_type_pk) REFERENCES
address_type_master(address_type_pk)`; `fk_person_address_location FOREIGN KEY
(city_village_postal_code_map_pk) REFERENCES
city_village_postal_code_map(city_village_postal_code_map_pk)` — this is the one place this
prototype actually reaches into a real (non-superseded) Foundation table. No soft-delete CHECK
constraint here either, same gap as `person`.

Indexes: `idx_person_address_person (person_pk)`, `idx_person_address_type (address_type_pk)`,
`idx_person_address_location (city_village_postal_code_map_pk)`, `idx_person_address_active
(is_active)`.

Additionally: `CREATE UNIQUE INDEX uq_person_primary_address ON person_address(person_pk) WHERE
is_primary = TRUE;` — a **partial unique index**, not a table-level `CONSTRAINT`, because
"at most one row per person with `is_primary = TRUE`" cannot be expressed as an ordinary `CHECK`
(CHECK constraints only see one row at a time; enforcing a cross-row invariant requires either a
partial unique index like this one or a trigger). This is the mechanism that guarantees a person
can never have two primary addresses simultaneously.

---

### database/seed/03_person/01_person_master_tables.sql

> **SUPERSEDED PROTOTYPE — not executed by `02_build.sh`/`02_build.ps1`, kept for reference
> only.** Seeds into the non-existent-in-production tables described above
> (`gender_master`/`marital_status_master`/`address_type_master`), not into `nss.master_data`.

**Requirement (as originally written)**

Seeds the three prototype master tables with the same values Foundation's `master_data` seed
provides under `GENDER`, `MARITAL_STATUS`, and `ADDRESS_TYPE` — illustrating directly why the
prototype was superseded: this data is fully duplicated by the generic pattern, just split
across three dedicated tables instead of one shared `master_data` table filtered by category.

**Line-by-line explanation**

```sql
INSERT INTO gender_master
(
    gender_code,
    gender_name,
    display_order
)
VALUES
('MALE', 'Male', 1),
('FEMALE', 'Female', 2),
('OTHER', 'Other', 3);

INSERT INTO marital_status_master
(
    marital_status_code,
    marital_status_name,
    display_order
)
VALUES
('UNMARRIED', 'Unmarried', 1),
('MARRIED', 'Married', 2),
('WIDOWED', 'Widowed', 3),
('DIVORCED', 'Divorced', 4),
('SEPARATED', 'Separated', 5);

INSERT INTO address_type_master
(
    address_type_code,
    address_type_name,
    display_order
)
VALUES
('PERMANENT', 'Permanent Address', 1),
('CURRENT', 'Current Address', 2),
('OFFICIAL', 'Official Address', 3);
```

Three plain `INSERT INTO <table> (<code_col>, <name_col>, display_order) VALUES (...);`
statements, one per table, all schema-unqualified (consistent with the DDL):

- **`gender_master` (3 rows):** `('MALE', 'Male', 1)`, `('FEMALE', 'Female', 2)`, `('OTHER',
  'Other', 3)` — identical values/order to Foundation's `GENDER` master_data rows.
- **`marital_status_master` (5 rows):** `('UNMARRIED', 'Unmarried', 1)`, `('MARRIED',
  'Married', 2)`, `('WIDOWED', 'Widowed', 3)`, `('DIVORCED', 'Divorced', 4)`, `('SEPARATED',
  'Separated', 5)` — identical to Foundation's `MARITAL_STATUS` master_data rows.
- **`address_type_master` (3 rows):** `('PERMANENT', 'Permanent Address', 1)`, `('CURRENT',
  'Current Address', 2)`, `('OFFICIAL', 'Official Address', 3)` — identical to Foundation's
  `ADDRESS_TYPE` master_data rows.

Total row count: **11** across the three tables (3 + 5 + 3), all values-for-values duplicates of
rows already present in `nss.master_data` once `database/seed/01_foundation/02_master_data.sql`
has run.

---

## 3. Cross-references

- `database/README.md` — canonical execution order, phase table, module implementation status,
  and the Two-Pass DDL Strategy (Pass 1 vs. Pass 2 audit-actor FKs) referenced throughout this
  document.
- `docs/03_Solution/architecture/DDL_CREATION_ORDER.md` (SOL-ARCH-010) — the frozen physical
  `CREATE TABLE` sequence and Depth/Seq# numbering cited in every DDL file's header comment.
- `docs/03_Solution/architecture/FK_DEPENDENCY_GRAPH.md` (SOL-ARCH-009) — the full table-to-table
  FK dependency graph that determines the Depth values used throughout this document.
- `docs/03_Solution/architecture/BOOTSTRAP_ARCHITECTURE.md` (SOL-ARCH-011) — the bootstrap
  sequence rationale, the `nss_db_owner`/`NSS_ERP_ADMIN` identity distinction, and the Two-Pass
  DDL Strategy's origin (the circular dependency between audited operations and the actor
  identity they require).
