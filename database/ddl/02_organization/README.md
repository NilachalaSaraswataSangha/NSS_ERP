# database/ddl/02_organization/

Organization Module DDL — 1 table (Depth 1) plus 2 enforcement triggers, per SOL-ORG-005, SOL-ARCH-010.

Authority: SOL-ORG-005 v1.2.0, SOL-ARCH-010

## DDL Execution Order

Execute AFTER all Foundation DDL (`database/ddl/01_foundation/`).

| # | File | Table | Depth | Sequence |
|--:|------|-------|------:|:--------:|
| 03 | `03_organization.sql` | `organization` | 1 | #33 |
| 04 | `04_organization_address_restriction_trigger.sql` | *(trigger `fn_enforce_organization_address_restriction()`, no table)* | 2 | — |
| 05 | `05_organization_kumari_sevak_uniqueness_trigger.sql` | *(trigger `fn_enforce_kumari_sevak_one_per_sakha()`, no table)* | 2 | — |

File numbers start at 03 because `01`/`02` (the retired type/status master tables, below) no
longer exist. Run as Phase 3 of `02_build.sh`/`.ps1`.

> **Retired:** `01_organization_type_master.sql` and
> `02_organization_status_master.sql` (and the tables they created,
> `organization_type_master` / `organization_status_master`) no longer
> exist. Type and status values now live in Foundation's generic
> `master_category`/`master_data` tables, under categories
> `ORGANIZATION_TYPE` and `STATUS` — one dedicated master-table pair per
> domain concept was redundant with the `master_data` pattern the
> project already committed to (frozen "Master Data Driven" principle).
> `organization.organization_type_master_data_pk` and
> `organization.status_master_data_pk` both reference
> `nss.master_data(master_data_pk)` instead.

## Design Notes

- **Triggers (DB-level invariants, mirrored in `api/routers/admin.py`):**
  - `04_…address_restriction_trigger.sql` (v1.1, ORG-BR-099 narrowed 2026-09-28) — `ANCHALIKA_SANGHA`,
    `ZILLA_SANGHA` and `PATHA_CHAKRA` may never carry a physical premises address
    (`address_line_1`/`address_line_2`/`city_village_pk`/`postal_code_pk`/`latitude`/`longitude`
    must be NULL), but **may** carry `country_pk`/`state_pk`/`district_pk` (administrative
    jurisdiction).
  - `05_…kumari_sevak_uniqueness_trigger.sql` (ORG-BR-102) — at most one active `KUMARI_SANGHA`
    and one active `SEVAK_SANGHA` per Sakha; a BEFORE trigger rather than a partial unique index
    because the predicate needs `master_data.value_code`, and Postgres forbids subqueries in
    index predicates.

- **No `organization_address` table** — address is inline on `organization`
  per frozen design (SOL-ORG-005 §44).
- **No `hierarchical_level` column** — organizational level is determined by
  `organization_type_master_data_pk`; hierarchy depth derived from
  `parent_organization_pk` (SOL-ORG-005 §33).
- **`organization_id` is nullable** — unique organizations (Kendra, Kutira,
  Smruti Mandira) are identified by `organization_code` alone.
  `organization_id` is sequence-generated for multi-instance types only.
- **Self-referencing FK** on `organization.parent_organization_pk` is included
  in the CREATE TABLE statement.
- **Soft-delete** on `organization`: `deleted_at` + `is_active` with
  CHECK constraint ensuring consistency.
- `organization` depends on Foundation tables: `master_data` (type/status),
  `country`, `state`, `district`, `city_village`, `postal_code`.
