# database/seed/

Reference/lookup data, mirroring `database/ddl/` (run after the corresponding DDL).

| Folder | Contents |
|---|---|
| `00_bootstrap/` | **Partial** — `role_master`: 8 roles seeded; `permission_master`/`role_permission`: empty, blocked on the permission catalogue being frozen |
| `01_foundation/` | **Implemented** — 8 files: master categories (13), master data values (82, across GENDER/MARITAL_STATUS/ADDRESS_TYPE/DOCUMENT_TYPE/MEMBERSHIP_TYPE/STATUS/RELATIONSHIP_TYPE/ORGANIZATION_TYPE/BLOOD_GROUP), `id_sequence_master` rows (9, `PERSON` padded to 10 digits), country (5), state (112), district (~770, India only), system settings (4), postal codes |
| `02_organization/` | **Implemented** — type masters (8 organization types) + status master + 3 unique named organizations (Kendra, Nilachala Kutira, Smruti Mandira) |
| `03_person/` | No seed data — `person`/`person_address` are seeded with zero rows. `01_person_master_tables.sql` is a superseded documentation stub (gender/marital status/address type values now live in Foundation's `master_data` seed) |

## Standalone top-level scripts

Two files live directly under `database/seed/` rather than in a numbered `NN_module/` folder —
a deliberate deviation from the convention above. They're cross-cutting *additions* to
already-seeded Tier 4 verification data (Family/Membership), not a new module's own seed, so
they don't get a module number. **Neither is run by `database/scripts/02_build.sh`** — both are
manual/standalone scripts, run individually with `psql` only if needed.

| File | Purpose |
|---|---|
| `99_extended_test_data.sql` | Adds 2 more families, 4 new persons, and cross-Sakha memberships on top of the Tier 4 verification seed, specifically to exercise org-admin drill-down, Sakha-alignment majority-rule badges, and cross-Sakha member-mismatch badges (business rules FAM-036/FAM-037). Depends on `02_tier4_verification_persons.sql`, `01_tier4_verification_family.sql`, and `01_tier4_verification_membership.sql` already having been run. |
| `99_fix_memberships.sql` | A partial-recovery patch, not a general-purpose script — per its own header, it re-runs only the sections (`sangha_sevi`/affiliation/credential inserts) that failed on a first attempt at running `99_extended_test_data.sql`, because the earlier sections (persons, families, relationships, links, heads) had already succeeded. Only relevant if you hit that exact partial-failure scenario; a clean run of `99_extended_test_data.sql` doesn't need it. |

```bash
psql -h <host> -p <port> -U nss_db_owner -d nss_erp -f database/seed/99_extended_test_data.sql
```
