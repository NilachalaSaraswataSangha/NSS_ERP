# NSS ERP — Deployment Procedure

**Document Type:** Operations / Deployment Guide
**Version:** 1.3
**Date:** 2026-09-30
**Status:** Active
**Audience:** Project maintainer

---

## Overview

NSS ERP is deployed on two managed services:

| Component | Service | Tier | Purpose |
|-----------|---------|------|---------|
| Application | [Render.com](https://render.com) | Free | FastAPI + Uvicorn, auto-deployed from GitHub |
| Database | [Neon.dev](https://neon.tech) | Free | PostgreSQL 16, 512 MB, SSL required |

Public URL (after deployment): `https://nss-erp.onrender.com/`

See `TECH_STACK_DECISIONS.md` §6 for architectural rationale.

> **Status:** not yet run in production. The last tagged release (`v0.10.4`) is Tier 4; Tier 5
> (Authentication + Administration) is in progress, uncommitted, on
> `feature/tier5-authentication-administration`, and `render_build.sh`/`render.yaml` already
> carry its changes (writer role, JWT secret, admin bootstrap, audit trigger). This guide
> describes the build as it exists on that branch.

---

## Prerequisites

- GitHub account with push access to the deployment remote (`org` — github.com/NilachalaSaraswataSangha/NSS_ERP)
- Code merged to `main` branch (deploy source)
- The following repo files must exist:
  - `render.yaml` — Render infrastructure-as-code
  - `render_build.sh` — Build + idempotent DB bootstrap script
  - `requirements.txt` — Pinned Python dependencies

---

## Step 1: Create Neon.dev Database

1. Go to [neon.tech](https://neon.tech) and sign up / log in.
2. Create a new project:
   - **Project name:** `nss-erp` (or similar)
   - **PostgreSQL version:** 16
   - **Region:** Choose closest to target users (e.g. `ap-southeast-1` for India)
3. Note the connection details from the dashboard:

   | Variable | Example |
   |----------|---------|
   | `DB_HOST` | `ep-xxxxx.us-east-2.aws.neon.tech` |
   | `DB_PORT` | `5432` |
   | `DB_NAME` | `neondb` |
   | `DB_USER` | `nss-erp_owner` |
   | `DB_PASSWORD` | (from dashboard) |
   | `DATABASE_URL` | `postgresql://<user>:<password>@<host>/<dbname>?sslmode=require` |

4. No manual schema setup needed — `render_build.sh` handles DDL + seed on first deploy.

### Extensions (auto-created by build script)

| Extension | Purpose | Neon Free Tier |
|-----------|---------|----------------|
| `pgcrypto` | `gen_random_uuid()` for UUID PKs | Supported |
| `pg_trgm` | GIN trigram indexes (fuzzy search) | Supported |
| `btree_gin` | Composite GIN indexes | Supported |

PostGIS and dblink are **not used** in current DDL and are not required.

---

## Step 2: Connect Repository to Render.com

1. Go to [render.com](https://render.com) and sign up / log in.
2. **New → Web Service** → connect the GitHub repo:
   - Repository: `NilachalaSaraswataSangha/NSS_ERP` (the `org` remote)
   - Branch: `main`
3. Render will detect `render.yaml` and auto-configure:
   - **Build command:** `./render_build.sh`
   - **Start command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 2`
   - **Plan:** Free
   - **Python version:** 3.12.4

**⚠️ Unverified risk (uncommitted Tier 5 branch):** `render.yaml` declares
`runtime: python`, but `render_build.sh` now runs `npm install` and `npx tailwindcss` as its
first step (Tailwind CDN → CLI migration). Render's native Python runtime environment is not
confirmed to include Node.js/npm — this has **not been tested against an actual Render deploy
yet** (deployment is still "not yet run in production" per `CLAUDE.md`). If `npm`/`npx` aren't
on `PATH` in that runtime, the build will fail immediately with `npm: command not found`.
Options if that happens: switch `runtime` to `docker` with a Dockerfile that installs both
Python and Node, or pre-commit the built `tailwind.min.css` and make the `npm`/`npx` step
conditional (skip if `node`/`npm` aren't found) so a missing Node toolchain degrades gracefully
instead of failing the whole deploy. Not resolved here — flag for whoever runs the first real
Render deploy after this change.

---

## Step 3: Set Environment Variables

In Render dashboard → **Environment** tab, add the 6 variables from Neon plus the 3 Tier 5
variables below (all declared `sync: false` in `render.yaml`, so they must be set by hand):

| Key | Value | Notes |
|-----|-------|-------|
| `DB_NAME` | (from Neon) | e.g. `neondb` |
| `DB_USER` | (from Neon) | e.g. `nss-erp_owner` |
| `DB_PASSWORD` | (from Neon) | Secret — Render masks it |
| `DB_HOST` | (from Neon) | e.g. `ep-xxxxx.us-east-2.aws.neon.tech` |
| `DB_PORT` | (from Neon) | Usually `5432` |
| `DATABASE_URL` | (from Neon) | Full connection string with `?sslmode=require` |

| `DB_WRITE_USER` | `nss_db_writer` | Tier 5 — write-capable pool (`api/database.py::get_write_connection`) |
| `DB_WRITE_PASSWORD` | (choose a secret) | Tier 5 — `render_build.sh` uses it when creating the `nss_db_writer` role (falls back to `DB_PASSWORD` if unset) |
| `JWT_SECRET_KEY` | (random 64-char hex) | Tier 5 — required by `Settings.validate_auth()`; generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |

These are referenced by both `render_build.sh` (for `psql` bootstrap and `scripts/bootstrap_admin.py`) and `api/main.py` (for FastAPI database connections). Optional tuning variables (`CORS_ORIGINS`, `RATE_LIMIT`, `DISABLE_DOCS`, `DB_READ_POOL_MIN/MAX`, `DB_WRITE_POOL_MIN/MAX`, `CSP_*`) are documented in `CLAUDE.md` → Setup; never set `DEBUG_MODE` in production.

---

## Step 4: Deploy

1. **Trigger manual deploy** in Render dashboard (or push to `org/main`).
2. `render_build.sh` runs automatically:
   - Builds Tailwind CSS (`npm install` + `npx tailwindcss -i ... -o
     frontend/assets/css/tailwind.min.css --minify`) — uncommitted as of this writing, see
     `TECH_STACK_DECISIONS.md` §3
   - Installs Python dependencies (`pip install -r requirements.txt`)
   - Creates the `nss` schema and extensions (`pgcrypto`, `pg_trgm`, `btree_gin` — best-effort)
   - Runs **every** DDL + seed phase on **every** deploy, in the same order as
     `database/scripts/02_build.sh`. Each `run_sql` call treats "already exists"/duplicate-key
     errors as `[SKIP]`, so a redeploy against an already-bootstrapped database is safe and
     picks up any newly added phase automatically:
     - Phase 0: Bootstrap RBAC (3 tables + seed: roles, permissions, role-permission mappings)
     - Phase 1-2: Foundation (12 tables + seed)
     - Phase 3-4: Organization (1 table + address-restriction and Kumari/Sevak uniqueness
       triggers; seed incl. 175 Sakha branches and the ID-sequence sync)
     - Phase 5: Person (2 tables)
     - Phase 6: Family (6 tables + move-transition guard)
     - Phase 7: Membership (14 tables + Sakha-only trigger)
     - *(inline)* ensures `nss_db_owner`/`nss_db_backend`/`nss_db_writer` roles exist
     - Phase 9: Grant `nss_db_backend` read-only access
     - Phase 10: Authentication (4 tables)
     - Phase 11: Administration (2 tables)
     - Phase 12: Grant `nss_db_writer` write access (auth + admin tables only)
     - Phase 13: Admin bootstrap (`python3 scripts/bootstrap_admin.py` — seeds the `SS1`/`P1`
       superuser, default password `Admin@123`; change it immediately after first login)
     - Phase 14: Audit (`system_event_log` + `fn_audit_trigger()` on every `nss.*` table)
   - There is no demo data: Phase 8 (Tier 4 verification seeds) was removed.
3. Uvicorn starts serving FastAPI.

---

## Step 5: Verify

| Check | URL | Expected |
|-------|-----|----------|
| Health endpoint | `https://nss-erp.onrender.com/api/v1/bootstrap/health` | `{"status": "ok", ...}` |
| Swagger UI | `https://nss-erp.onrender.com/docs` | Interactive API docs |
| Login page | `https://nss-erp.onrender.com/` | Redirects to `/login` (the standalone Bootstrap Verification UI was retired) |
| Roles API | `https://nss-erp.onrender.com/api/v1/bootstrap/roles` | 9 frozen roles JSON |
| Admin login | `https://nss-erp.onrender.com/login` | `SS1` / `Admin@123` (seeded by Phase 13), then `/admin` |

---

## Subsequent Deployments

Render auto-deploys on every push to `org/main`. The flow:

```
feature/* → develop (personal remote)
         → main (merge when tier complete)
         → push to org remote
         → Render auto-deploys
```

`render_build.sh` is idempotent and re-runs every phase on each deploy (existing objects are skipped), so subsequent deploys rebuild CSS, reinstall dependencies, re-apply any new DDL/seed and restart Uvicorn.

### Adding new tiers to the database

When a new tier's DDL + seed are committed:

1. Add the new DDL + seed `run_sql` calls to `render_build.sh` in the same position as in
   `database/scripts/02_build.sh` (keep the two in sync).
2. Deploy — new files are applied automatically. Only `CREATE ... IF NOT EXISTS`/upsert-style
   files are safe to re-run; a DDL *change* to an existing table (new column, altered
   constraint) is **not** applied by `IF NOT EXISTS` and must be run manually against Neon
   (`psql` or the Neon SQL Editor), or the Neon branch reset to force a full re-bootstrap.

---

## Troubleshooting

### `psql` not found on Render

Render's Python runtime should include `postgresql-client`. If not:

```bash
# Add to top of render_build.sh
apt-get update && apt-get install -y postgresql-client
```

Or switch to a Docker runtime with `psql` pre-installed.

### Extension not available

The build script handles missing extensions gracefully (`2>/dev/null || echo "skipping"`). If a required extension fails, check Neon's supported extensions list for the free tier.

### Connection refused / SSL error

Neon requires SSL. The build script sets `PGSSLMODE="require"`. Ensure `DATABASE_URL` includes `?sslmode=require`.

### Free tier cold start

Render free tier spins down after 15 minutes of inactivity. First request after idle takes ~30–60 seconds. Neon free tier does NOT pause for inactivity — the database is always warm.

---

## Security Notes

- Database credentials are **never** committed to the repository.
- `DB_PASSWORD` and `DATABASE_URL` are set only in Render's environment (masked).
- The `.env` file (local development) is in `.gitignore`.
- The FastAPI backend is designed to connect as `nss_db_backend` (SELECT-only) for reads and `nss_db_writer` (auth/admin write tables only) for writes. On Render today, `DB_USER` is the Neon-provided owner role that also runs the build, so least-privilege separation for the read pool is not yet enforced in that deployment (see the comment in `render_build.sh`).
- Production database requires SSL (`PGSSLMODE=require`).

---

## Neon CLI Setup (Optional)

For local management of the Neon project:

```bash
npm i -g neon@latest
neon login
neon link --project-id <project-id> --branch production -y
neon config init
```

This creates a `.neon` link file in the project directory for CLI operations (branching, SQL editor, etc.).

---

## Related Documents

- `TECH_STACK_DECISIONS.md` — Architecture rationale (§6 Deployment and Git)
- `PERFORMANCE_TUNING.md` — Workers, connection pool, indexes, scaling guidance
- `render.yaml` — Render infrastructure-as-code definition
- `render_build.sh` — Build + bootstrap script (annotated)
- `docs/05_Releases/v0.6.0.md` — First deployable release notes
