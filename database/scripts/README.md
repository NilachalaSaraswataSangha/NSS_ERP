# database/scripts/

Executable bootstrap/build/validate scripts for the raw-SQL DDL track.
Run from the repository root.

> **Getting started?** See `docs/03_Solution/architecture/GETTING_STARTED.md` for the full
> step-by-step setup sequence (database, API, tests, and database rebuild). This file is the
> detailed script reference.

## Script Reference

| File | Run as | Target DB | Purpose |
|---|---|---|---|
| `00_create_database.sql` | superuser (`postgres`) | `postgres` | Creates `nss_erp` database, `nss_db_owner`/`nss_db_backend` roles (both with LOGIN, no password). Installs `dblink`. Fully idempotent. |
| `01_extensions.sql` | superuser (`postgres`) | `nss_erp` | Installs `pgcrypto`, `pg_trgm`, `btree_gin`, `postgis`. Creates `nss` schema owned by `nss_db_owner`. Idempotent. |
| `02_build.sh` / `.ps1` | `nss_db_owner` | `nss_erp` | Runs all implemented DDL + seed (Bootstrap RBAC, Foundation, Organization, Person, Family, Membership) plus Tier 4 verification seed data. Not idempotent — drop/recreate DB for clean rebuild. |
| `03_validate.sh` / `.ps1` | `nss_db_owner` | `nss_erp` | Post-build checks: table existence, row counts, unique constraints, FK integrity. Run after build; does not execute any DDL/seed. |
| `04_grant_backend.sql` | `nss_db_owner` | `nss_erp` | Grants `nss_db_backend` read-only access: `USAGE` on `nss` schema, `SELECT` on all tables, `ALTER DEFAULT PRIVILEGES` for future tables. Idempotent. |

Build and validate scripts accept optional args:

- **bash:** `DB_NAME DB_USER DB_HOST DB_PORT` (positional, defaults: `nss_erp nss_db_owner localhost 5432`)
- **PowerShell:** `-DbName -DbUser -DbHost -DbPort` (named, same defaults)

## Build Phases (internal execution order)

The build script (`02_build.sh` / `.ps1`) executes DDL and seed files in the frozen
SOL-ARCH-011 phase order. Authority: SOL-ARCH-010 (DDL Creation Order), SOL-ARCH-011
(Bootstrap Architecture).

### Phase 0 — Bootstrap RBAC (SOL-ARCH-011 §4)

| Step | File | Table | Depth |
|-----:|------|-------|------:|
| DDL | `ddl/00_bootstrap/01_role_master.sql` | `role_master` | 0 |
| DDL | `ddl/00_bootstrap/02_permission_master.sql` | `permission_master` | 0 |
| DDL | `ddl/00_bootstrap/03_role_permission.sql` | `role_permission` | 1 |
| Seed | `seed/00_bootstrap/01_permission_master.sql` | *(empty — catalogue not frozen)* | — |
| Seed | `seed/00_bootstrap/02_role_master.sql` | 8 frozen roles | — |
| Seed | `seed/00_bootstrap/03_role_permission.sql` | *(empty — depends on permissions)* | — |

### Phase 1 — Foundation DDL (12 tables, Depths 0–4)

| Step | File | Table | Depth |
|-----:|------|-------|------:|
| DDL | `ddl/01_foundation/02_master_category.sql` | `master_category` | 0 |
| DDL | `ddl/01_foundation/03_system_setting.sql` | `system_setting` | 0 |
| DDL | `ddl/01_foundation/04_id_sequence_master.sql` | `id_sequence_master` | 0 |
| DDL | `ddl/01_foundation/05_country.sql` | `country` | 0 |
| DDL | `ddl/01_foundation/06_document_master.sql` | `document_master` | 0 |
| DDL | `ddl/01_foundation/07_field_change_log.sql` | `field_change_log` | 0 |
| DDL | `ddl/01_foundation/08_master_data.sql` | `master_data` | 1 |
| DDL | `ddl/01_foundation/09_state.sql` | `state` | 1 |
| DDL | `ddl/01_foundation/10_district.sql` | `district` | 2 |
| DDL | `ddl/01_foundation/11_city_village.sql` | `city_village` | 3 |
| DDL | `ddl/01_foundation/12_postal_code.sql` | `postal_code` | 2 |
| DDL | `ddl/01_foundation/13_city_village_postal_code_map.sql` | `city_village_postal_code_map` | 4 |

### Phase 2 — Foundation Seed Data

| Step | File | Seeds |
|-----:|------|-------|
| Seed | `seed/01_foundation/01_master_category.sql` | 13 master categories (incl. ORGANIZATION_TYPE, unified STATUS, BLOOD_GROUP) |
| Seed | `seed/01_foundation/02_master_data.sql` | Master data rows (incl. 10 org types + 13 unified statuses + 8 blood groups) |
| Seed | `seed/01_foundation/03_id_sequence_master.sql` | ID sequence definitions |
| Seed | `seed/01_foundation/04_country.sql` | Countries |
| Seed | `seed/01_foundation/05_state.sql` | States |
| Seed | `seed/01_foundation/06_district.sql` | Districts |
| Seed | `seed/01_foundation/07_system_setting.sql` | System settings |
| Seed | `seed/01_foundation/08_postal_code.sql` | Postal codes |

### Phase 3 — Organization DDL (1 table, Depth 1)

Organization type and status are now stored in Foundation `master_data`
(category `ORGANIZATION_TYPE` for types, unified `STATUS` for lifecycle
statuses). The standalone `organization_type_master` and
`organization_status_master` tables are retired.

| Step | File | Table | Depth |
|-----:|------|-------|------:|
| DDL | `ddl/02_organization/03_organization.sql` | `organization` | 1 |

### Phase 4 — Organization Seed Data

| Step | File | Seeds |
|-----:|------|-------|
| Seed | `seed/02_organization/03_organization.sql` | 3 organizations (resolves type/status via master_data) |

### Phase 5 — Person DDL (2 tables, Depths 2–3)

| Step | File | Table | Depth |
|-----:|------|-------|------:|
| DDL | `ddl/03_person/02_person.sql` | `person` | 2 |
| DDL | `ddl/03_person/03_person_address.sql` | `person_address` | 3 |

`ddl/03_person/01_person_master_tables.sql` is superseded — gender/marital
status/address type data now lives in Foundation `master_data` seed (Phase 2)
and is not run.

### Phase 6 — Family DDL (4 tables, Depths 2–3)

| Step | File | Table |
|-----:|------|-------|
| DDL | `ddl/04_family/01_family_group.sql` | `family_group` |
| DDL | `ddl/04_family/02_family_relationship.sql` | `family_relationship` |
| DDL | `ddl/04_family/03_family_head_history.sql` | `family_head_history` |
| DDL | `ddl/04_family/04_family_transition_history.sql` | `family_transition_history` |

### Phase 7 — Membership DDL (12 tables, Depths 2–4)

`sangha_sevi` is created first — all other membership tables depend on it.

| Step | File | Table |
|-----:|------|-------|
| DDL | `ddl/05_membership/01_sangha_sevi.sql` | `sangha_sevi` |
| DDL | `ddl/05_membership/02_membership_status_history.sql` | `membership_status_history` |
| DDL | `ddl/05_membership/03_membership_renewal_request.sql` | `membership_renewal_request` |
| DDL | `ddl/05_membership/04_membership_renewal_history.sql` | `membership_renewal_history` |
| DDL | `ddl/05_membership/05_membership_transfer_history.sql` | `membership_transfer_history` |
| DDL | `ddl/05_membership/06_membership_sakha_affiliation.sql` | `membership_sakha_affiliation` |
| DDL | `ddl/05_membership/07_membership_journey_event.sql` | `membership_journey_event` |
| DDL | `ddl/05_membership/08_probationary_member_review.sql` | `probationary_member_review` |
| DDL | `ddl/05_membership/09_parichaya_patra.sql` | `parichaya_patra` |
| DDL | `ddl/05_membership/10_parichaya_patra_history.sql` | `parichaya_patra_history` |
| DDL | `ddl/05_membership/11_anumati_patra.sql` | `anumati_patra` |
| DDL | `ddl/05_membership/12_anumati_patra_history.sql` | `anumati_patra_history` |

### Phase 8 — Tier 4 Verification Seed Data

Order respects the dependency chain: Organization → Person → Family →
Membership.

| Step | File | Seeds |
|-----:|------|-------|
| Seed | `seed/02_organization/04_tier4_verification_orgs.sql` | Verification organizations |
| Seed | `seed/03_person/02_tier4_verification_persons.sql` | Verification persons |
| Seed | `seed/04_family/01_tier4_verification_family.sql` | Verification family groups/relationships |
| Seed | `seed/05_membership/01_tier4_verification_membership.sql` | Verification membership records |

### Phase 9 — Grant Backend Access

| Step | File | Purpose |
|-----:|------|---------|
| Grant | `04_grant_backend.sql` | Grants `nss_db_backend` read-only access. Must run after all DDL so `GRANT SELECT ON ALL TABLES` covers every table just created. |

### Not executed (future phases)

- Pass 2 audit-actor FK constraints (deferred until `sangha_sevi`'s own audit
  columns are wired to authenticated actors — Tier 5)
- All remaining modules (Authentication, Administration Phase 4+, Governance, etc.)

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

## Starting the API

See `docs/03_Solution/architecture/GETTING_STARTED.md` → Sections 3–5 for API setup, startup, and testing.
