# database/seed/02_organization/

Organization Module seed data — the three unique organizations required
before downstream modules.

Authority: SOL-ORG-005 §48, SOL-ARCH-010 §8

## Seed Execution Order

Execute AFTER:
- All Foundation DDL + seed (`database/ddl/01_foundation/`, `database/seed/01_foundation/`)
- All Organization DDL (`database/ddl/02_organization/`)

| # | File | Seeds Into | Depends On |
|--:|------|-----------|-----------|
| 03 | `03_organization.sql` | `organization` | Foundation `master_category`/`master_data` seed, Foundation `country`/`postal_code` seed, Organization DDL complete |

> **Moved:** The former `01_organization_type_master.sql` and
> `02_organization_status_master.sql` seed files are gone. Type and status
> seed data now live in Foundation's generic master-data seed files —
> `database/seed/01_foundation/01_master_category.sql` (categories) and
> `database/seed/01_foundation/02_master_data.sql` (the `ORGANIZATION_TYPE`
> and `STATUS` value rows). `03_organization.sql` looks these up at insert
> time via joins on `master_data`/`master_category` (`category_code` +
> `value_code`) rather than FK'ing to dedicated master tables.

## Execution Command

```bash
# As nss_db_owner against the nss_erp database:
for f in database/seed/02_organization/0*.sql; do
    psql -U nss_db_owner -d nss_erp -f "$f"
done
```

---

## Seed File Descriptions

### 03_organization.sql

Seeds the 3 unique organizations of NSS. No `organization_id` — unique
organizations are identified by `organization_code` alone. Sequence-generated
IDs are for multi-instance org types (Sakha, Anchalika, etc.). Type and
status are resolved per row via joins against `nss.master_data`/
`nss.master_category` on `category_code = 'ORGANIZATION_TYPE'` /
`'STATUS'` and the relevant `value_code`.

| # | `organization_code` | Name | Type (`value_code`) | Parent |
|--:|---------------------|------|------|--------|
| 1 | `KEN` | Nilachala Saraswata Sangha | `KENDRA` | NULL (apex governing body) |
| 2 | `NKT` | Nilachala Kutira | `NILACHALA_KUTIRA` | NULL (Eternal Abode, Puri) |
| 3 | `SMR` | Sri Shri Nigamananda Smruti Mandir | `SMRUTI_MANDIRA` | NULL (memorial temple, Puri) |

All three are seeded with status `ACTIVE` and country = IN (India).
Kendra's representative office address is seeded inline: Satsikshya Mandir,
A/4, Unit-9, Bhubaneswar - 751022, Odisha, India.

---

## Notes

- Organization types and statuses are frozen per SOL-ORG-005 §48 / GOV-002,
  but the seed rows themselves now live in Foundation's `master_data`
  (see "Moved" note above) — not in this folder.
- **Unique org hierarchy (ERP-FROZEN):**
  KEN, NKT, SMR are peer root organizations (`parent = NULL`).
  KEN remains the apex governing body. Physical location/operational
  association ≠ organizational parent-child relationship.
  Constitutional/functional roles are distinguished by
  `organization_type_master_data_pk`.
- Unique organizations have no `organization_id` — identified by
  `organization_code` alone. `organization_id` (sequence-generated via
  `id_sequence_master`) is for multi-instance types only.
- Additional organizations (Anchalika, Zilla, Sakha, etc.) are created
  at runtime through governance workflows, not seeded.
- Foundation seed data (`master_category`, `master_data`, `country`,
  `postal_code`) must be loaded before Organization seed.
- All addresses are editable at runtime — seed values are initial state only.
