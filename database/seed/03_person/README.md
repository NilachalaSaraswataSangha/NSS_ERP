# database/seed/03_person/

`nss.person_address` (created by `database/ddl/03_person/03_person_address.sql`) has no seed
data — it remains at zero rows. `nss.person` (created by `02_person.sql`) is seeded with 8 Tier
4 verification persons by `02_tier4_verification_persons.sql` (see below); it is not otherwise
seeded from production data.

- `01_person_master_tables.sql` — **superseded** (documentation stub, no seed data generated).
  It originally seeded `gender_master` (MALE, FEMALE, OTHER), `marital_status_master`
  (UNMARRIED, MARRIED, WIDOWED, DIVORCED, SEPARATED), and `address_type_master` (PERMANENT,
  CURRENT, OFFICIAL) — those values now live in Foundation's `master_data` seed
  (`database/seed/01_foundation/02_master_data.sql`, categories `GENDER`, `MARITAL_STATUS`,
  `ADDRESS_TYPE`). See `database/README.md` "Superseded Artifacts".

### 02_tier4_verification_persons.sql

Seeds 8 test persons (`P1`–`P8`) into `nss.person` for Family + Membership verification.
Gender and marital status are resolved via a `master_data`/`master_category` subquery (same
pattern as Organization's `03_organization.sql`). No Aadhaar data is seeded (all NULL). Must
run after Foundation `master_data` seed (Phase 2); no dependency on Organization seed.

| `person_id` | Name | Role in Tier 4 verification |
|---|---|---|
| `P1` | Ramesh Mishra | Family head; Regular member (`SS1`) |
| `P2` | Sushma Mishra | Spouse; non-member |
| `P3` | Aniket Mishra | Son; Probationary member (`SS2`) |
| `P4` | Suresh Patel | Regular member, transferred `SKH1` → `SKH2` (`SS3`) |
| `P5` | Debasis Rath | Associate member, enrolled by Parichalak (`SS4`) |
| `P6` | Priyanka Das | Kumari participant — Person without Membership |
| `P7` | Soumya Nayak | Kishor participant — Person without Membership |
| `P8` | Smita Sahoo | Former Kumari participant, transitioned to Probationary member (`SS5`) |

`person_id` values here are unpadded (`P1`…`P8`) — consistent with the project's ID-format
direction (see `database/seed/01_foundation/README.md` § `03_id_sequence_master.sql`); they are
literal seed values, not generated through the `PERSON` `id_sequence_master` row (which still
has `padding_length = 10`). `SS1`–`SS5` sangha_sevi IDs referenced above are seeded by
`database/seed/05_membership/01_tier4_verification_membership.sql`, not by this file.
