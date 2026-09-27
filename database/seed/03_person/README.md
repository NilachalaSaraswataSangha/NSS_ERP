# database/seed/03_person/

`nss.person_address` (created by `database/ddl/03_person/03_person_address.sql`) has no seed
data — it remains at zero rows. `nss.person` is also not pre-seeded — persons are created
at runtime through the registration flow (`POST /api/v1/register`).

- `01_person_master_tables.sql` — **superseded** (documentation stub, no seed data generated).
  It originally seeded `gender_master` (MALE, FEMALE, OTHER), `marital_status_master`
  (UNMARRIED, MARRIED, WIDOWED, DIVORCED, SEPARATED), and `address_type_master` (PERMANENT,
  CURRENT, OFFICIAL) — those values now live in Foundation's `master_data` seed
  (`database/seed/01_foundation/02_master_data.sql`, categories `GENDER`, `MARITAL_STATUS`,
  `ADDRESS_TYPE`). See `database/README.md` "Superseded Artifacts".

> **Removed:** The former `02_tier4_verification_persons.sql` (13 test persons P1-P13)
> has been deleted. Real persons are now created through the registration API.
