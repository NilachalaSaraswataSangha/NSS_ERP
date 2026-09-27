# scripts/

Top-level, repo-root operational Python scripts — distinct from `database/scripts/` (SQL/shell
bootstrap scripts). **New (uncommitted)** on branch `feature/tier5-authentication-administration`.

| File | Purpose |
|---|---|
| `bootstrap_admin.py` | Seeds the NSS Admin superuser account (`P1`/`SS1`, `NSS_ERP_ADMIN` role, `NSS-WIDE` scope) — see `database/seed/04_admin/README.md`. Run as `python3 scripts/bootstrap_admin.py` (optionally `--password <pw>`) from the repository root, after the database has been built through Phase 12 (Administration DDL + `nss_db_writer` grant). Requires `api/.env` with working DB credentials — it imports `api.services.auth_service.hash_password` and `api.database.get_write_pool` directly, so it must run with the repo root on `sys.path` (it inserts this itself via `Path(__file__).resolve().parent.parent`). |

This script exists as Python (not plain `psql -f ...`) specifically because
`nss.user_account.password_hash` needs a runtime-generated Argon2 hash — there is no SQL-only
way to produce one, and the project's "no hardcoded credentials" rule means the hash cannot be
pre-computed and pasted into a seed file either.

Called automatically as Phase 13 of `database/scripts/02_build.sh`/`.ps1` and
`render_build.sh` — you don't need to run it by hand unless bootstrapping a database outside
those scripts (e.g. after a manual `03_validate.sh` run, or re-seeding a dropped-and-recreated
local dev DB).
