# database/migrations/

**This is not a migration-tool folder.** The project's DDL/seed convention (`CLAUDE.md` →
Database, SOL-ARCH-010/011) is unchanged: hand-written PostgreSQL DDL under `database/ddl/` in
numeric folder order, hand-written reference data under `database/seed/`, both run via `psql`,
with no Alembic/Flyway/Django-migrations-style framework anywhere in this repo. Nothing here
introduces one.

What lives in this folder instead is a narrow escape valve: **one-off, ad-hoc data-fix scripts**
for databases that were already bootstrapped (via `database/scripts/02_build.sh` or the Render
build step) *before* a seed-data correction landed in `database/seed/`. A fresh
`02_build.sh` run against a brand-new database never needs anything in this folder — the
corrected value is already in the seed file it runs. These scripts exist purely for whoever is
holding an already-seeded database with the stale value baked in.

Because of that, this folder does not follow the `NN_module/` numbered-phase convention used
under `database/ddl/` and `database/seed/` — there is no phase order to preserve, no dependency
chain, and no expectation that these scripts run as part of `02_build.sh` (they don't, and never
should). Each file here is self-contained and named for what it fixes, not for a build phase.

## Files

| File | Fixes | When you need it |
|---|---|---|
| `update_darshaka.sql` | `nss.master_data` row `value_code = 'PROBATIONARY'` (category `MEMBERSHIP_TYPE`): updates `value_name` from `'Probationary Member'` to `'Darshaka'` (NSS Bye-Law §B naming) | **Only** if your database was bootstrapped before this fix landed in `database/seed/01_foundation/02_master_data.sql` — i.e. it still shows `value_name = 'Probationary Member'` for that row. A database built fresh from the current `02_build.sh` already seeds `'Darshaka'` directly and does not need this script. |

## Running a script here

These are plain `psql` scripts, run manually and individually — never via `02_build.sh`/`.ps1`
or the Render build step:

```bash
psql -h <host> -p <port> -U nss_db_owner -d nss_erp -f database/migrations/update_darshaka.sql
```

Check first (e.g. `SELECT value_name FROM nss.master_data WHERE value_code = 'PROBATIONARY';`)
whether your database actually has the stale value before running — the script is not harmful
to re-run (it's an idempotent `UPDATE ... WHERE`), but if the seed already produced the correct
value there's nothing for it to do.

## Adding a new file here

Only add a script to this folder if it fixes a **seed-data value** that has already been
corrected at its source (the relevant file under `database/seed/`) for future builds, and only
databases bootstrapped before that correction need the fix applied retroactively. If what you're
adding is a schema change (new column, new table, new constraint), it belongs under
`database/ddl/` following the Two-Pass DDL Strategy (`database/README.md`), not here — this
folder is for data corrections only, never schema migrations.
