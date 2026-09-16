# NSS ERP — Performance Tuning Guide

**Document Type:** Solution Architecture / Operations
**Version:** 1.0
**Date:** 2026-09-16
**Status:** Active
**Audience:** Project maintainer

---

## Overview

This document records the performance optimizations applied to the NSS ERP
application, the rationale behind each tuning parameter, and scaling
guidance for when the application moves beyond Render/Neon free tiers.

All changes were driven by a specific symptom: slow page loading on the
Family and Membership verification pages after the Tier 4 dynamic Sakha
computation (FAM-036) was introduced.

---

## 1. Root Cause Analysis

Three bottlenecks were identified, in order of user-visible impact:

| Layer | Bottleneck | Impact |
|-------|-----------|--------|
| Frontend (JS) | Sequential `await` chains in `init()` — health check blocked data fetch | ~200-500 ms wasted on every page load |
| Frontend (JS) | `fetchOrgChildren()` awaited both children list AND heavy stats query before rendering anything | Org cards invisible until the slowest query finished |
| Database | `family_majority` CTE joined 3 tables with single-column indexes; full-table scans on every family list/org stats request | Query time scaled linearly with total family count |

Secondary factors:

| Layer | Issue | Impact |
|-------|-------|--------|
| Server | Single Uvicorn worker — parallel browser requests serialized | Stats query blocked children query on the server side |
| Database | `minconn=1` — first request after startup paid connection creation cost | Cold-start latency on first page load |

---

## 2. Frontend Optimizations

### 2.1 Health Check: Fire-and-Forget

**Files:** `frontend/assets/js/family.js`, `frontend/assets/js/membership.js`

**Before:**
```js
async init() {
    await this.fetchHealth();    // blocks ~200-500ms
    await this.fetchMembers();   // only starts after health completes
}
```

**After:**
```js
async init() {
    this.fetchHealth();          // fire-and-forget (no await)
    await this.fetchMembers();   // starts immediately
}
```

**Rationale:** The health check updates a status indicator in the UI. It
does not gate any data loading — if the DB is down, the data fetch will
fail on its own. Removing `await` lets the data fetch start immediately
while the health badge updates in the background.

### 2.2 Non-Blocking Org Stats

**File:** `frontend/assets/js/family.js`

**Before:** `fetchOrgChildren()` used `Promise.all([children, stats])` then
`await`-ed both. The fast children query (~50ms) was held hostage by the
heavy `_CHILDREN_STATS_SQL` recursive CTE (~500ms+).

**After:** Split into two phases:

1. `fetchOrgChildren(orgPk)` — fetches children list, renders cards
   immediately, sets `orgChildrenLoading = false`.
2. `_fetchOrgChildrenStats(orgPk)` — runs in background; when stats
   arrive, Alpine reactivity populates the count badges.

**User experience:** Org cards appear instantly. Family/member/person
count numbers fill in a moment later.

---

## 3. Server Optimizations

### 3.1 Uvicorn Workers

**File:** `render.yaml`

```yaml
startCommand: uvicorn api.main:app --host 0.0.0.0 --port $PORT --workers 2
```

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `--workers` | 2 | Render free tier: 512 MB RAM. Each worker process ~50-80 MB. 2 workers = ~160 MB, leaving ~350 MB for query buffers, OS, etc. Enough to handle parallel requests (children + children-stats) without serialization. |

**Scaling guidance:**

| Render Plan | RAM | Recommended Workers | Notes |
|-------------|-----|-------------------|-------|
| Free | 512 MB | 2 | Current setting |
| Starter (paid) | 1 GB | 3-4 | Standard `2N+1` formula (N=1 CPU) |
| Standard | 2 GB | 4-5 | Monitor memory before adding more |

Workers beyond 4-5 yield diminishing returns on a single-CPU plan. If
concurrency demands exceed that, consider async database access
(psycopg3 / asyncpg) instead of more processes.

### 3.2 Connection Pool

**File:** `api/database.py`

```python
_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=2,
    maxconn=5,
    ...
)
```

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `minconn` | 2 | Pre-warms 2 connections at pool init. With 2 workers, that is 2 x 2 = 4 connections ready at startup. Eliminates cold-start latency on first requests. |
| `maxconn` | 5 | Peak burst per worker. Total max across 2 workers = 10 connections. Neon free tier supports ~100 concurrent connections — well within budget. |

**Scaling guidance:**

- `minconn` should match typical concurrent requests per worker (currently 2:
  page load fires children + children-stats in parallel).
- `maxconn` should match peak burst per worker. Keep total
  (`maxconn x workers`) under Neon's connection limit.
- If upgrading to paid Neon (higher connection limits), consider:
  `minconn=3, maxconn=10` with 4 workers = 40 max connections.

**Rule of thumb:**
```
minconn = typical concurrent requests per worker
maxconn = peak burst per worker
Total connections = maxconn x workers < Neon connection limit
```

---

## 4. Database Optimizations

### 4.1 Composite Partial Indexes

**File:** `database/migrations/add_performance_indexes.sql`

The `family_majority` CTE is the hot path — it runs on every family list
query (`_FAMILY_SELECT` in `family.py`) and every org children-stats
query (`_CHILDREN_STATS_SQL` in `organization.py`). It joins three tables:

```
family_relationship (is_current=TRUE)
  → sangha_sevi (is_active=TRUE, via person_pk)
    → membership_sakha_affiliation (effective_to IS NULL, via sangha_sevi_pk)
```

**Before:** Each table had only single-column indexes. PostgreSQL performed
sequential scans or inefficient index lookups requiring heap access.

**After:** Four composite partial indexes that cover the CTE join columns:

| Index | Table | Columns | Partial Filter | Purpose |
|-------|-------|---------|---------------|---------|
| `idx_family_rel_current_person_family` | `family_relationship` | `(person_pk, family_group_pk)` | `WHERE is_current = TRUE` | CTE joins on person_pk, groups by family_group_pk |
| `idx_sangha_sevi_active_person` | `sangha_sevi` | `(person_pk, sangha_sevi_pk)` | `WHERE is_active = TRUE` | CTE joins on person_pk, needs sangha_sevi_pk for next join |
| `idx_mem_sakha_aff_active_covering` | `membership_sakha_affiliation` | `(sangha_sevi_pk, organization_pk)` | `WHERE effective_to IS NULL` | CTE joins on sangha_sevi_pk, groups by organization_pk |
| `idx_organization_parent_active` | `organization` | `(parent_organization_pk)` | `WHERE is_active = TRUE` | Recursive CTE: `org_tree` joins on parent_organization_pk |

**Why partial indexes:** The CTE always filters on the same boolean/null
conditions. Partial indexes exclude inactive/archived rows from the index
entirely, making them smaller and faster to scan.

**Why composite:** The CTE needs both the join column and the group-by
column. A composite index lets PostgreSQL do an index-only scan —
it reads everything it needs from the index without touching the heap.

### 4.2 Build Pipeline Integration

The indexes are applied automatically on every deploy/build:

| Script | Phase | Command |
|--------|-------|---------|
| `render_build.sh` | Phase 8b | `run_sql "performance indexes" "${REPO_ROOT}/database/migrations/add_performance_indexes.sql"` |
| `database/scripts/02_build.sh` | Phase 8b | Same |
| `database/scripts/02_build.ps1` | Phase 8b | Same |

All use `CREATE INDEX IF NOT EXISTS` — idempotent on re-runs.

### 4.3 Manual Application (Local Dev)

macOS / Linux:
```bash
psql -U nss_db_owner -d nss_erp -f database/migrations/add_performance_indexes.sql
```

Windows (PowerShell):
```powershell
psql -h localhost -p 5432 -U nss_db_owner -d nss_erp -f database\migrations\add_performance_indexes.sql
```

Or run the full build script which now includes Phase 8b:
```bash
./database/scripts/02_build.sh
```

---

## 5. Cache Busting

Static JS assets use `?v=N` query strings to force browser cache
invalidation after code changes:

| File | Current Version | Updated In |
|------|----------------|------------|
| `family.js` | `?v=24` | `frontend/family.html` |
| `membership.js` | `?v=4.0` | `frontend/membership.html` |

Increment the version number whenever the JS file changes. The HTML
`<script>` tag is the only place this is set — no build tool involved.

---

## 6. Performance Testing

No formal benchmarks have been run (the dataset is seed-level: ~50
families, ~100 members). The optimizations are structural and will scale
with data growth. When the dataset grows to production size (1000+
families), consider:

1. **EXPLAIN ANALYZE** on `_FAMILY_SELECT` and `_CHILDREN_STATS_SQL` to
   verify index usage.
2. **pg_stat_user_indexes** to confirm the new indexes are being used
   (not dead weight).
3. **Connection pool monitoring** — if `maxconn` is regularly exhausted,
   bump it or switch to an async driver.
4. **Materialized view** for org children stats if the recursive CTE
   becomes too slow even with indexes. Refresh on family/membership
   mutations (write-side, Tier 5+).

---

## 7. Summary of All Changes

| File | Change | Category |
|------|--------|----------|
| `frontend/assets/js/family.js` | Health check fire-and-forget; non-blocking stats; `?v=24` | Frontend |
| `frontend/assets/js/membership.js` | Health check fire-and-forget; `?v=4.0` | Frontend |
| `frontend/family.html` | Cache bump `?v=24` | Frontend |
| `frontend/membership.html` | Cache bump `?v=4.0` | Frontend |
| `render.yaml` | `--workers 2` on start command | Server |
| `api/database.py` | `minconn=2` (was 1) | Server |
| `database/migrations/add_performance_indexes.sql` | 4 composite partial indexes | Database |
| `render_build.sh` | Phase 8b — performance indexes | Build pipeline |
| `database/scripts/02_build.sh` | Phase 8b — performance indexes | Build pipeline |
| `database/scripts/02_build.ps1` | Phases 6-9 + Phase 8b (was missing) | Build pipeline |

---

## Related Documents

- `TECH_STACK_DECISIONS.md` — Architecture rationale (Section 2 Backend, Section 6 Deployment)
- `DEPLOYMENT_PROCEDURE.md` — Deploy and bootstrap procedure
- `database/migrations/add_performance_indexes.sql` — Index DDL (annotated)
- `database/migrations/README.md` — Migration file conventions

---

# End of Document
