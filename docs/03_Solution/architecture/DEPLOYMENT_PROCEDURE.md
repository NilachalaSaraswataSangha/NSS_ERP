# NSS ERP — Deployment Procedure

**Document Type:** Operations / Deployment Guide
**Version:** 1.0
**Date:** 2026-09-09
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
   - **Start command:** `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
   - **Python version:** 3.12.4

---

## Step 3: Set Environment Variables

In Render dashboard → **Environment** tab, add the 6 variables from Neon:

| Key | Value | Notes |
|-----|-------|-------|
| `DB_NAME` | (from Neon) | e.g. `neondb` |
| `DB_USER` | (from Neon) | e.g. `nss-erp_owner` |
| `DB_PASSWORD` | (from Neon) | Secret — Render masks it |
| `DB_HOST` | (from Neon) | e.g. `ep-xxxxx.us-east-2.aws.neon.tech` |
| `DB_PORT` | (from Neon) | Usually `5432` |
| `DATABASE_URL` | (from Neon) | Full connection string with `?sslmode=require` |

These are referenced by both `render_build.sh` (for `psql` bootstrap) and `api/main.py` (for FastAPI database connections).

---

## Step 4: Deploy

1. **Trigger manual deploy** in Render dashboard (or push to `org/main`).
2. `render_build.sh` runs automatically:
   - Installs Python dependencies (`pip install -r requirements.txt`)
   - Checks if `nss.role_master` exists on Neon
   - If **fresh database**: creates `nss` schema, installs extensions, runs all DDL + seed in order:
     - Phase 0: Bootstrap RBAC (3 tables + seed)
     - Phase 1: Foundation (12 tables + seed)
     - Phase 2: Organization (3 tables + seed)
   - If **already bootstrapped**: skips DDL/seed (idempotent)
3. Uvicorn starts serving FastAPI.

---

## Step 5: Verify

| Check | URL | Expected |
|-------|-----|----------|
| Health endpoint | `https://nss-erp.onrender.com/api/v1/bootstrap/health` | `{"status": "ok", ...}` |
| Swagger UI | `https://nss-erp.onrender.com/docs` | Interactive API docs |
| Bootstrap Verification UI | `https://nss-erp.onrender.com/` | Roles/Permissions/Role Permissions grid |
| Roles API | `https://nss-erp.onrender.com/api/v1/bootstrap/roles` | 8 frozen roles JSON |

---

## Subsequent Deployments

Render auto-deploys on every push to `org/main`. The flow:

```
feature/* → develop (personal remote)
         → main (merge when tier complete)
         → push to org remote
         → Render auto-deploys
```

Since `render_build.sh` is idempotent, subsequent deploys only install dependencies and restart Uvicorn — the database is not re-bootstrapped.

### Adding new tiers to the database

When a new tier's DDL + seed are committed (e.g. Tier 3 Person):

1. Add the new DDL + seed `run_sql` calls to `render_build.sh` (in the `else` branch).
2. **Manually run** the new DDL against Neon using `psql` or the Neon SQL Editor, since the bootstrap check (`role_master` exists?) will skip DDL on an already-bootstrapped database.
3. Alternatively, reset the Neon branch to force a full re-bootstrap on next deploy.

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
- The FastAPI backend connects as `nss_db_backend` (SELECT-only role for Tier 0).
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
- `render.yaml` — Render infrastructure-as-code definition
- `render_build.sh` — Build + bootstrap script (annotated)
- `docs/05_Releases/v0.6.0.md` — First deployable release notes
