# database/ddl/03_person/

**Implemented** — 2 tables: `person` (28 columns) and `person_address`. Both follow the
Foundation `master_category`/`master_data` pattern: gender, marital status, blood group, and
emergency relationship resolve via `master_data` (categories `GENDER`, `MARITAL_STATUS`,
`BLOOD_GROUP`), and `person_address.address_type_master_data_pk` resolves via `master_data`
category `ADDRESS_TYPE`.

- `01_person_master_tables.sql` — **superseded** (documentation stub, no DDL generated). The
  per-domain master tables it originally defined (`gender_master`, `marital_status_master`,
  `address_type_master`) are replaced by Foundation's `master_category`/`master_data`. See
  `database/README.md` "Superseded Artifacts".
- `02_person.sql` — `person` table, incl. the `chk_person_contact_required` and
  `chk_person_mobile_pair` CHECK constraints. Audit-actor FKs
  (`created_by_sangha_sevi_pk`/etc.) are nullable columns in this pass; their FK constraints
  are deferred to Pass 2 (after `sangha_sevi` exists).
- `03_person_address.sql` — `person_address` table, incl. the partial unique index
  (`uq_person_primary_address`) enforcing one primary address per person.

Matches `docs/03_Solution/modules/person/05_person_table_design.md` closely — see that doc for
the full design rationale. See also `docs/PROJECT_DOCUMENTATION.md` for the tier-by-tier plan.
