# database/ddl/

Hand-written PostgreSQL DDL, run in numeric folder order.

| Folder | Status |
|---|---|
| `00_bootstrap/` | **Implemented** — 3 tables: `role_master`, `permission_master`, `role_permission` (RBAC definitions, created before Foundation since they have no FK dependencies) |
| `01_foundation/` | **Implemented** — 12 tables: extensions, master category/data, system settings, ID sequence registry, location hierarchy (country/state/district/city_village/postal_code + mapping), document registry, field change log |
| `02_organization/` | **Implemented** — 1 table: `organization` (self-referencing hierarchy, address inline). Type/status masters retired in favor of Foundation's generic `master_category`/`master_data` (categories `ORGANIZATION_TYPE`, `STATUS`) |
| `03_person/` | **Implemented** — 2 tables: `person` (28 columns) and `person_address`, both resolving gender/marital status/blood group/address type via Foundation's `master_category`/`master_data` pattern. `01_person_master_tables.sql` is superseded (per-domain masters replaced by Foundation `master_data`; see `database/README.md` Superseded Artifacts) |

See `database/README.md` and `docs/PROJECT_DOCUMENTATION.md` for the full schema breakdown.
