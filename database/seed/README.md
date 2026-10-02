# database/seed/

Reference/lookup data, mirroring `database/ddl/` (run after the corresponding DDL, driven by
`database/scripts/02_build.sh`/`.ps1`).

| Folder | Contents |
|---|---|
| `00_bootstrap/` | **Implemented** — `role_master`: 9 roles; `permission_master`: 20 permissions; `role_permission`: 112 role-to-permission mappings |
| `01_foundation/` | **Implemented** — 9 files: master categories (13), master data values (89, across GENDER/MARITAL_STATUS/ADDRESS_TYPE/DOCUMENT_TYPE/MEMBERSHIP_TYPE/STATUS/RELATIONSHIP_TYPE/ORGANIZATION_TYPE/BLOOD_GROUP), `id_sequence_master` rows (14; `PERSON` padded to 10 digits, `SAKHA` unpadded), country (5), state (112), districts (India only), system settings (5), postal codes (3 in `08_postal_code.sql` + 56 Sakha-branch PINs in `09_sakha_postal_codes.sql`, which runs in build Phase 4) |
| `02_organization/` | **Implemented** — 3 unique named organizations (Kendra `KEN`, Nilachala Kutira `NKT`, Smruti Mandira `SMR`) + 175 real Sakha Sangha branches (`SKH1`–`SKH175`) + `06_id_sequence_org_sync.sql` (advances org-code counters). The 13 organization types and the status values live in Foundation `master_data`, not here |
| `03_person/` | No seed data — `person`/`person_address` start with zero rows. Only the superseded `01_person_master_tables.sql` stub remains (not run) |
| `04_admin/` | **Tier 5** — `01_admin_bootstrap.sql`: one admin superuser (`P1`/`SS1`, `NSS_ERP_ADMIN` role, `NSS-WIDE` scope). Run via `python3 scripts/bootstrap_admin.py` (build Phase 13), not plain `psql` — see `04_admin/README.md` |
| `04_family/` | No seed data (README only) — unrelated to `04_admin/`; the shared `04_` prefix just mirrors `ddl/04_family/` |
| `05_membership/` | No seed data (README only) |

There are no `06_authentication/` or `07_administration/` seed folders (those modules' only seed
data is the `04_admin/` bootstrap), and no `99_*.sql` scripts.

> **Removed:** All Tier 4/5 verification seed data and extended test data
> (`02_tier4_verification_*`, `01_tier4_verification_*`, `99_extended_test_data.sql`,
> `99_fix_memberships.sql`) have been deleted. A fresh build yields zero demo Person, Family, or
> Membership rows; real data is created at runtime through the registration flow and governance
> workflows.
