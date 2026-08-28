# database/ddl/01_foundation/

Foundation Module DDL — 12 tables (Depths 0–4).

Authority: SOL-ARCH-010 (DDL Creation Order) + Amendment (PIN Code Geographic
Model, 2026-08-28), SOL-FND-004 (Foundation Table Design)

## File Execution Order

Execute files in numeric order. Each file depends only on tables created
by earlier-numbered files in this directory.

| # | File | Table | Depth | Global Seq |
|--:|------|-------|------:|-----------:|
| 01 | `01_extensions.sql` | — (pgcrypto, pg_trgm, btree_gin) | — | — |
| 02 | `02_master_category.sql` | `master_category` | 0 | #1 |
| 03 | `03_system_setting.sql` | `system_setting` | 0 | #2 |
| 04 | `04_id_sequence_master.sql` | `id_sequence_master` | 0 | #3 |
| 05 | `05_country.sql` | `country` | 0 | #4 |
| 06 | `06_document_master.sql` | `document_master` | 0 | #5 |
| 07 | `07_field_change_log.sql` | `field_change_log` | 0 | #6 |
| 08 | `08_master_data.sql` | `master_data` | 1 | #18 |
| 09 | `09_state.sql` | `state` | 1 | #19 |
| 10 | `10_district.sql` | `district` | 2 | #26 |
| 11 | `11_city_village.sql` | `city_village` | 3 | #32 |
| 12 | `12_postal_code.sql` | `postal_code` | 1 | #87 (amendment) |
| 13 | `13_city_village_postal_code_map.sql` | `city_village_postal_code_map` | 4 | #88 (amendment) |

**Note:** Files 12–13 depend on `country` (Depth 0) and `city_village` (Depth 3)
respectively. They are numbered after the original 11 files for clarity but
execute correctly in sequence because their dependencies are already created
by earlier files.

## Execution Command

```bash
# As NSS_ADMIN against the nss_erp database:
for f in database/ddl/01_foundation/0*.sql database/ddl/01_foundation/1*.sql; do
    psql -U nss_admin -d nss_erp -f "$f"
done
```

## Design Decisions

- **No audit-actor FKs** — `created_by_sangha_sevi_pk` / `updated_by_sangha_sevi_pk` /
  `deleted_by_sangha_sevi_pk` are NOT included in Foundation tables. They will be added
  via ALTER TABLE in Pass 2 after `sangha_sevi` exists (SOL-ARCH-010 §5).
- **`document_master`** — owned by Foundation (DOC-ARCH-001); logical design from Person §54.
  Person-specific FKs (`person_pk`, `uploaded_by_sangha_sevi_pk`) deferred to Pass 2.
- **`field_change_log`** — stores references as UUID values without FK constraints to avoid
  circular dependencies. Application layer enforces referential integrity.
- **PIN Code Model (Amendment 2026-08-28)** — `postal_code` and `city_village_postal_code_map`
  added to support searchable geographic hierarchy and map visualization. PIN codes are
  country-scoped with M:N relationship to `city_village`. Organization stores `postal_code`
  as VARCHAR (denormalized for display) plus `latitude`/`longitude` for exact coordinates.
- **Supersedes** — this replaces the previous `country_master`, `state_province_master`,
  `district_region_master`, `city_village_master` tables from the prototype iteration.
  The new `postal_code` and `city_village_postal_code_map` tables preserve the same
  M:N model from the prototype but with corrected naming.
