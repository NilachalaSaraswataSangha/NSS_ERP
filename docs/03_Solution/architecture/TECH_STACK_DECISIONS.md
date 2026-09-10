# NSS ERP — Technology Stack and Decision Matrix

**Document Type:** Solution Architecture Decision Record
**Version:** 1.3
**Date:** 2026-09-08
**Status:** Approved
**Branch:** develop

**Revision History:**

| Version | Date | Change |
|---------|------|--------|
| 1.0 | 2026-08-16 | Initial approved decision record |
| 1.1 | 2026-08-20 | §6 Deployment and Git reconciled to live remote state: removed `pie` (Apple-internal remote, removed from the repo 2026-08-15); `org` — github.com/NilachalaSaraswataSangha/NSS_ERP is now an actual configured git remote (added 2026-08-18), not just a description — the Production remote row and Flow row now use the `org` alias consistently. No other section changed. |
| 1.2 | 2026-08-28 | §4 Mobile Strategy: replaced PWA-first/Capacitor/conditional-Flutter with Flutter (Android + iOS) from day one (TECH-MOB-001 FROZEN). §5 Offline: added mobile-specific storage (Hive/Drift) and sync. §7 Architecture: updated client diagram. §8 Phase 5: Flutter app phases replace PWA+Capacitor. |
| 1.3 | 2026-09-08 | Django-to-FastAPI migration: §2 Backend rewritten (Django removed, FastAPI sole framework, raw psycopg2, python-dotenv). §3 Frontend updated (static HTML served by FastAPI, not Django Templates). §1 Database hosting updated (Neon.dev production, not generic "PostgreSQL"). §6 Deployment updated (Render.com app + Neon.dev database, infrastructure-as-code). §7 Architecture diagram rewritten. §8 Implementation order updated (Django Models phase removed). §10 Alternatives: Django added as considered-and-departed. Architectural rationale for the migration documented throughout. |

---

## 1. Database

| Parameter | Decision | Rationale |
|-----------|----------|-----------|
| Engine | PostgreSQL 16 | Best constraint/integrity tooling for governance-driven schema; UUID support, CHECK constraints, partial indexes, RLS, self-referencing FKs |
| Hosting (Production) | Neon.dev (free tier) | 512 MB, no inactivity pause, no expiry, SSL required, branching support, scales to zero without data loss |
| Hosting (Development) | Local PostgreSQL | `.env` configured per machine |
| Schema authority | Hand-written DDL (`database/ddl/`) | Governance-aligned, traceable to REF/GOV/REQ/SOLUTION. The DDL is the single source of truth — no ORM or migration tool competes with it. |
| PK strategy | UUID (`gen_random_uuid()`, suffix `_pk`) | Security, no sequential enumeration |
| Business identifiers | `_code` suffix (e.g. `person_code`, `sangha_sevi_code`) | Permanent, human-readable, never reused |
| Audit columns | `created_at`, `updated_at`, `deleted_at`, `is_active` | Full lifecycle tracking |
| Soft delete | `deleted_at` pattern | History never deleted (frozen principle) |
| Naming | `snake_case` tables and columns | Existing DDL convention |

---

## 2. Backend

| Parameter | Decision | Rationale |
|-----------|----------|-----------|
| Language | Python | Existing expertise, mature ecosystem |
| Web/API framework | FastAPI 0.136.3 | API-first architecture; JSON endpoints consumed by web frontend and future Flutter mobile app; async-capable |
| Server | Uvicorn (ASGI) | Async-capable, lightweight, serves FastAPI directly |
| Database access | Direct PostgreSQL access (no ORM) | Hand-written DDL is the database source of truth; an ORM/migration layer would compete with it. Tier 0 uses psycopg2; the driver may evolve to psycopg3 or asyncpg if concurrency demands it — the principle is **no ORM**, not a specific driver. |
| Hosting | Render.com (free tier) | Auto-deploy from GitHub, HTTPS provisioned automatically, no nginx/gunicorn needed |
| Environment | python-dotenv (`.env` file) | Secrets never in git; Render injects env vars in production |
| Testing | pytest, configured (`pytest.ini`, `tests/`) | Integration tests via `fastapi.testclient.TestClient` against a real local Postgres — `pytest`/`httpx` pinned in `requirements.txt` |

### Why FastAPI, not Django

NSS ERP uses FastAPI as the sole backend framework because:

1. **PostgreSQL hand-written DDL is authoritative.** An ORM-driven migration layer (Django's `makemigrations` / `migrate`) would create a competing source of truth for the database schema. The NSS architecture requires that DDL changes flow from governance documents through hand-written SQL, not from Python model definitions.

2. **API-first architecture.** The web frontend, future Flutter mobile app, and offline sync endpoints all consume the same JSON API. FastAPI is purpose-built for this; Django's value proposition centres on its integrated ORM + admin + template stack, which NSS does not use.

3. **Deliberate separation of concerns.** Authentication, authorization, and business services are being designed as explicit NSS ERP modules (Tier 5+), not inherited from a framework. Django's built-in auth would introduce framework coupling that the architecture deliberately avoids.

4. **No Django Admin dependency.** NSS ERP's administrative UI is purpose-built per the governance model, not a generic CRUD admin.

5. **Service evolution.** A FastAPI service can later split into multiple services without first dismantling a Django monolith.

This is an architectural alignment decision, not a framework popularity claim. Django is legitimate industry practice for CRUD-dominant ERP systems where ORM productivity outweighs schema independence. It is not the right fit for NSS ERP's governance-driven, DDL-authoritative architecture.

### Previous architecture (superseded)

The Django prototype (`backend/`) was implemented during initial development and removed in the `feature/fastapi-tier0` branch. It is preserved in Git history for provenance but no longer influences the implementation. Django ORM, Django authentication, Django templates, Django admin, and Django migrations are all excluded from the active architecture.

---

## 3. Frontend

| Parameter | Decision | Rationale |
|-----------|----------|-----------|
| Serving | Static HTML served by FastAPI | Single process, no separate frontend server, no CORS configuration needed |
| CSS framework | Tailwind CSS + DaisyUI (CDN) | Modern SaaS look, color-coded domains, theme system, dark mode built-in; no Node.js build step |
| Interactivity | Alpine.js (CDN) | Reactive data binding, dropdowns, modals, toggles — tiny, no build step |
| API communication | Vanilla `fetch()` | JSON API consumption; no HTMX in Tier 0 (may be evaluated for later tiers if server-rendered partials become valuable) |
| Design language | Saffron (#DC7831) accent, institutional/spiritual, accessible to elderly | NSS identity, not corporate ERP |
| Previous (replaced) | Django Templates + HTMX | Removed with Django; static HTML + Alpine.js achieves the same result without framework coupling |

---

## 4. Mobile Strategy

| Parameter | Decision | Rationale |
|-----------|----------|-----------|
| Framework | Flutter (Dart) | Camera access, Play Store / App Store presence, native performance |
| Platforms | Android + iOS (both from day one) | Full user coverage; single codebase via Flutter |
| Distribution | Google Play Store + Apple App Store | Discoverable, updatable, trusted install path |
| API contract | Consumes same FastAPI JSON endpoints as web UI | Single backend, no duplication |
| Offline | Local DB (Hive/Drift) → sync on connect | Attendance marking at venues with poor connectivity |
| Camera | Document scanning, photo verification | Requires native — PWA camera APIs insufficient |
| Development sequence | DB → API → Web UI → Flutter UI (per module) | Flutter begins after API for Tier 1–2 is stable |
| Push notifications | Firebase Cloud Messaging (FCM) | Cross-platform, free tier sufficient |

**Decision ID:** TECH-MOB-001
**Status:** FROZEN
**Supersedes:** Previous PWA-first / Capacitor / "Flutter only if needed" position

---

## 5. Offline Capability

| Parameter | Decision | Rationale |
|-----------|----------|-----------|
| Scope | Generic Event Engine (not UPBS-specific) | Any NSS event at a venue with poor connectivity |
| Web storage | IndexedDB (browser) | Local data persistence, event-scoped |
| Mobile storage | Hive or Drift (Flutter local DB) | Structured offline cache with typed models |
| Web sync | Service Worker + Background Sync | Queue writes offline, replay when connected |
| Mobile sync | Dart background isolate → FastAPI | Same queue-and-replay pattern as web |
| Conflict resolution | Server-authoritative + audit trail | Server assigns final IDs; conflicts flagged for manual review |
| Offline-capable modules | On-site registration, delegate/participant cards, venue attendance, receipt collection, weekly attendance |
| Online-only modules | Membership, Governance, Family, Admin, Finance |

---

## 6. Deployment and Git

| Parameter | Decision | Rationale |
|-----------|----------|-----------|
| Development remote | `personal` — github.com/sandeeppanda22/NSS_ERP | Daily pushes |
| Production remote | `org` — github.com/NilachalaSaraswataSangha/NSS_ERP | Org account, deployment source |
| App hosting | Render.com (free tier) | Auto-deploy from `org/main`; HTTPS, SSL certs, edge proxy provided — no nginx/gunicorn needed |
| Database hosting | Neon.dev (free tier) | 512 MB PostgreSQL 16, no inactivity pause, no expiry, SSL required |
| Infrastructure-as-code | `render.yaml` in repo root | Defines Render web service; DB credentials set as env vars pointing to Neon |
| Build script | `render_build.sh` in repo root | Installs deps, idempotent DB bootstrap (DDL + seed if fresh) |
| Start command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` | Render sets `$PORT`; no gunicorn wrapper needed for ASGI |
| Flow | feature/* → develop (`personal`) → main → push to `org` → Render auto-deploys |
| Branch policy | Complete current branch, merge to develop, then create next |

### Production architecture

```
Browser / Flutter App
       |
       v
Render.com (free tier)
  HTTPS / SSL (Render edge proxy)
       |
       v
  Uvicorn (ASGI)
       |
       v
  FastAPI
    ├── /                    → Bootstrap Verification UI (static HTML)
    ├── /assets/*            → CSS, JS, images (StaticFiles)
    ├── /docs                → Swagger UI (auto-generated)
    └── /api/v1/*            → JSON API endpoints
       |
       v
Neon.dev (free tier)
  PostgreSQL 16
  512 MB, SSL required, no expiry
  nss.* schema (hand-written DDL)
```

### Why not nginx / gunicorn?

- **Nginx** handles TLS termination, static file serving, and reverse proxying. Render's edge proxy provides all three — nginx is unnecessary on a managed platform. It becomes relevant only if self-hosting on a VM (Tier 5+ concern).
- **Gunicorn** is a WSGI process manager for Django. FastAPI is ASGI — Uvicorn serves it directly. Multiple Uvicorn workers can be added later if concurrency demands it (`uvicorn --workers N`), but on the free tier's limited memory, a single worker is appropriate.

---

## 7. Architecture Diagram

```
CLIENTS
  Browser (Desktop/Mobile)
    Static HTML + Tailwind CSS + DaisyUI + Alpine.js
    fetch() → JSON API
  Flutter App (Android + iOS)
    Dart + Material/Cupertino widgets
    Camera, Push Notifications (FCM)
    Offline DB (Hive/Drift) → background sync
       |                         |
       v                         v
RENDER.COM (Free Tier)
  Uvicorn (ASGI)
    FastAPI
      Static frontend serving (/, /assets/*)
      JSON APIs (CRUD, search, reports)
      Sync endpoints (offline upload/download)
      Authentication (Tier 5 — designed, not inherited)
      Authorization (role + permission + scope)
       |
       v
NEON.DEV (Free Tier)
  PostgreSQL 16
    UUID PKs + Business Codes
    CHECK constraints
    Row-Level Security (RLS)
    Soft delete + Audit trail
    Hand-written DDL (source of truth)
    ~100-130 tables (estimated final)
```

### Database/API boundary principle

```
PostgreSQL (authoritative)
   ↑
Hand-written DDL (governance-traced)
   ↑
FastAPI (API layer)
   ↑
Direct SQL / psycopg2 (no ORM)
```

The API layer reads and writes the database through direct SQL. It does not own the schema, generate migrations, or maintain model definitions that could diverge from the DDL. This boundary is a frozen architectural principle — the specific SQL driver (psycopg2, psycopg3, asyncpg) may evolve, but the no-ORM constraint does not.

---

## 8. Implementation Order

### Phase 1 — Database (DDL)

```
~~02_organization (implement 0-byte placeholders from design doc)~~ — done
  ("Organization Vertical Slice")
04_membership
05_family
06_governance
07_attendance
08_authentication
Seed data for all masters
```

### Phase 2 — API (FastAPI)

```
Person CRUD
Membership lifecycle
Organization hierarchy
Sync endpoints (for offline)
```

### Phase 3 — UI (Static HTML + Tailwind + DaisyUI + Alpine.js)

```
UI-001 Login
UI-002 Kendra Dashboard
UI-003 Sakha Dashboard
UI-004 Member Search
UI-005 Member Profile
UI-006 Family Dashboard
```

### Phase 4 — Flutter App (after API for Tiers 1–2 is stable)

```
Flutter project scaffold + auth integration
Attendance module (camera + offline sync)
Member search + profile view
Event registration (on-site, offline-capable)
Push notification integration (FCM)
Play Store + App Store submission
```

---

## 9. Color Language (UI Design System)

| Color | Hex | Domain |
|-------|-----|--------|
| Saffron | #DC7831 | NSS brand accent, primary buttons, login |
| Indigo | #6366F1 | People/Members |
| Green | #22C55E | Families/Success/Active |
| Amber | #F97316 | Renewals/Warnings/Sakha |
| Blue | #0284C7 | Attendance/Information |
| Pink | #EC4899 | Mahila Sangha |
| Purple | #7C3AED | Governance/Transfer |
| Red | #DC2626 | Errors/Admin/Critical |

---

## 10. Alternatives Considered and Rejected

| Alternative | Rejected Because |
|-------------|-----------------|
| Django (full stack) | NSS ERP's hand-written DDL is the database source of truth; Django ORM's migration system creates a competing schema authority. Django's integrated auth/admin/templates bundle couples concerns that the NSS architecture deliberately separates. The Django prototype was implemented and subsequently removed — this is an informed departure, not an uninvestigated one. Django remains legitimate industry practice for ORM-centric CRUD systems; it is not the right fit for NSS ERP's governance-driven architecture. |
| Next.js frontend | Wrong paradigm for ERP; doubles codebase; requires React/TypeScript learning |
| Vercel hosting | Serverless model fights long-running processes (cold starts, timeout limits, no persistent process) |
| MongoDB | Data is highly relational (person to membership to organization to hierarchy); document DBs fight this shape |
| Supabase (database) | Free tier pauses after 7 days inactivity; Neon does not |
| Render PostgreSQL (database) | Free tier expires after 90 days; Neon has no expiry |
| React SPA | Doubles development time; requires separate build tooling; no benefit for the user base (elderly office bearers) |
| Bootstrap 5 (alone) | Functional but visually flat; Tailwind + DaisyUI achieves modern look without extra complexity |
| SQLite | No concurrent writes, no RLS, no UUID type — too limited for multi-user ERP |
| PWA-only mobile | No camera access, no Play Store presence, limited push notification reliability on Android |
| React Native | JavaScript bridge overhead; Flutter's Dart AOT compilation is faster; single-language consistency |
| Capacitor wrapper | Still a web view — same PWA limitations (camera, background sync) with extra tooling overhead |

---

## 11. Governance Traceability

This document is a SOLUTION-layer artifact per the frozen governance lifecycle:

```
REF (Statutory source)
  AUTH (Reference management)
    GOV (Governance interpretation)
      REQ (Business requirements)
        SOLUTION (This document) <--
          CODE (Implementation)
            TEST (Validation)
              RELEASE (Publication)
```

Technology decisions recorded here must not contradict frozen governance principles (GOV-ORG-001 through GOV-LIFE-002) or frozen module architectures (Person, Membership, Organization, Family, Governance).

---

# End of Document
