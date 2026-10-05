# database/ddl/

Hand-written PostgreSQL DDL, run in numeric folder order (driven by `database/scripts/02_build.sh`/`.ps1`).
47 tables in total (counted from `CREATE TABLE` statements).

| Folder | Status |
|---|---|
| `00_bootstrap/` | **Implemented** — 3 tables: `role_master`, `permission_master`, `role_permission` (RBAC definitions, created before Foundation since they have no FK dependencies) |
| `01_foundation/` | **Implemented** — 15 tables: master category/data, system settings, ID sequence registry, location hierarchy (country/state/district/city_village/postal_code/post_office — the last four member-writable), document registry, field change log (12 tables in files 02–13), `16_festival_master.sql`/`17_festival_calendar_date.sql`, plus `14_system_event_log.sql` (centralized audit trail, Tier 5). `15_audit_trigger.sql` creates no table — it defines `fn_audit_trigger()` and attaches it to every other `nss.*` table, so it must run last in the whole build (Phase 14) |
| `02_organization/` | **Implemented** — 1 table: `organization` (self-referencing hierarchy, address inline) plus 2 triggers (`04_organization_address_restriction_trigger.sql`, `05_organization_kumari_sevak_uniqueness_trigger.sql`). Type/status masters retired in favor of Foundation's generic `master_category`/`master_data` (categories `ORGANIZATION_TYPE`, `STATUS`) |
| `03_person/` | **Implemented** — 2 tables: `person` (32 columns, incl. audit/soft-delete columns) and `person_address`, both resolving gender/marital status/blood group/address type via Foundation's `master_category`/`master_data` pattern. `01_person_master_tables.sql` is superseded and not run (see `database/README.md` Superseded Artifacts) |
| `04_family/` | **Implemented** — 6 tables: `family_group`, `family_relationship`, `family_head_history`, `family_transition_history`, `family_link`, `family_admin` (new, Tier 5), plus `07_family_move_transition_guard.sql` (deferred constraint trigger, no table) |
| `05_membership/` | **Implemented** — 14 tables: `sangha_sevi` and its status/renewal/transfer/affiliation/journey/review/credential history tables, `darshak_attendance_registration` and `credential_sequence_counter` (both new, Tier 5), plus `14_sakha_only_membership_trigger.sql` (MBR-038A, no table) |
| `06_authentication/` | **Implemented (Tier 5, committed on branch, not merged)** — 5 tables: `user_account`, `password_history`, `registration_claim`, `password_reset_token`, `user_session` |
| `07_administration/` | **Implemented (Tier 5, committed on branch, not merged)** — 2 tables: `user_role`, `admin_scope` |

Tables per folder: 3 + 15 + 1 + 2 + 6 + 14 + 4 + 2 = 47.

Build phase numbers differ from folder numbers (Foundation's `14`/`15` run as Phase 14, after
everything else; Authentication is Phase 10, Administration Phase 11) — see
`database/scripts/README.md` for the authoritative phase order.

See `database/README.md` and `docs/PROJECT_DOCUMENTATION.md` for the full schema breakdown.
