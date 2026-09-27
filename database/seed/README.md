# database/seed/

Reference/lookup data, mirroring `database/ddl/` (run after the corresponding DDL).

| Folder | Contents |
|---|---|
| `00_bootstrap/` | **Implemented** — `role_master`: 9 roles seeded; `permission_master`/`role_permission`: also populated (~20 permissions, ~110 mappings) |
| `01_foundation/` | **Implemented** — 8 files: master categories (13), master data values (82, across GENDER/MARITAL_STATUS/ADDRESS_TYPE/DOCUMENT_TYPE/MEMBERSHIP_TYPE/STATUS/RELATIONSHIP_TYPE/ORGANIZATION_TYPE/BLOOD_GROUP), `id_sequence_master` rows (9, `PERSON` padded to 10 digits), country (5), state (112), district (~770, India only), system settings (4), postal codes |
| `02_organization/` | **Implemented** — type masters (13 organization types) + status master + 3 unique named organizations (Kendra, Nilachala Kutira, Smruti Mandira) + 175 real Sakha Sangha branches |
| `03_person/` | No seed data — `person`/`person_address` are seeded with zero rows. `01_person_master_tables.sql` is a superseded documentation stub (gender/marital status/address type values now live in Foundation's `master_data` seed) |
| `04_family/` | No seed data — all test family seeds removed |
| `05_membership/` | No seed data — all test membership seeds removed |
| `06_authentication/` | No seed data — test user account seed removed |
| `07_administration/` | No seed data — test admin role seed removed |
| `04_admin/` | **New, uncommitted (Tier 5 branch)** — seeds one admin superuser (`P1`/`SS1`, `NSS_ERP_ADMIN` role, `NSS-WIDE` scope). Run via `python3 scripts/bootstrap_admin.py`, not plain `psql` — see `database/seed/04_admin/README.md` |

> **Removed:** All Tier 4/5 verification seed data and extended test data
> (`99_extended_test_data.sql`, `99_fix_memberships.sql`) have been deleted.
> Person, Family, Membership, Authentication, and Administration test seeds
> are no longer present. Real data will be created at runtime through the
> registration flow and governance workflows.
