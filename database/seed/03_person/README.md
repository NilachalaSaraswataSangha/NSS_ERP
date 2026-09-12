# database/seed/03_person/

Person has **no seed data** of its own — `nss.person` and `nss.person_address` (created by
`database/ddl/03_person/02_person.sql` and `03_person_address.sql`) are seeded with zero rows.
`database/scripts/03_validate.sh`/`.ps1` check table existence and zero row counts for these two
tables rather than FK integrity against seeded rows.

- `01_person_master_tables.sql` — **superseded** (documentation stub, no seed data generated).
  It originally seeded `gender_master` (MALE, FEMALE, OTHER), `marital_status_master`
  (UNMARRIED, MARRIED, WIDOWED, DIVORCED, SEPARATED), and `address_type_master` (PERMANENT,
  CURRENT, OFFICIAL) — those values now live in Foundation's `master_data` seed
  (`database/seed/01_foundation/02_master_data.sql`, categories `GENDER`, `MARITAL_STATUS`,
  `ADDRESS_TYPE`). See `database/README.md` "Superseded Artifacts".
