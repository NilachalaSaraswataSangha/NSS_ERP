# database/ddl/02_organization/

Organization Module DDL — 1 table (Depth 1) per SOL-ORG-005, SOL-ARCH-010.

Authority: SOL-ORG-005 v1.2.0, SOL-ARCH-010

## DDL Execution Order

Execute AFTER all Foundation DDL (`database/ddl/01_foundation/`).

| # | File | Table | Depth | Sequence |
|--:|------|-------|------:|:--------:|
| 03 | `03_organization.sql` | `organization` | 1 | #33 |

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
