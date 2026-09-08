# NSS ERP Foundation Module

Status: DRAFT — SOURCE ALIGNED, v1.0.0. Full Solution design complete (4 files).

**Naming collision (historical) — read before assuming anything.** This Solution-layer
"Foundation" module was never the same thing as the now-removed `backend/foundation/` Django app
(the entire Django prototype was archived and removed from the repository — see
`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md`). They shared a name but covered
different scope:

- **This doc set** (`SOL-FND-001`…`004`) designs shared technical/master-data infrastructure —
  master data catalog, system settings, ID sequencing, and the geographic reference hierarchy
  (Country → State → District → City/Village). It matches `database/ddl/01_foundation/`
  (`id_sequence_master`, `country`/`state`/`district`/`city_village`), not the former Django app.
- **`backend/foundation/`** (former Django app, removed) implemented `OrganizationType`,
  `Organization`, `Address`, `Person` models — i.e. the *Person* and *Organization* domains,
  which have their **own**, separate Solution doc sets: `docs/03_Solution/modules/person/` and
  `.../organization/`.

Person and Organization design content does **not** live in this folder — see those two module
folders instead.

---

## Documents

01_foundation_module_overview.md (`SOL-FND-001`) — Version 1.0.0
Purpose: Shared technical/business foundation for other modules — "Configure Once" master-data
and infrastructure capabilities, not a business-operation module itself.

02_foundation_erd.md — Version 1.0.0
Purpose: Entity relationship design for the original eight foundation tables.

03_foundation_business_rules.md — Version 1.0.0, FND-BR-001–FND-BR-084
Purpose: Business rules — Master Data Driven architecture, Configuration Over Hardcoding,
central ID sequence infrastructure. No invented columns/data types — exact VARCHAR lengths,
setting-value representation, and sequence implementation are all marked pending.

04_foundation_table_design.md — Version 1.1.0
Purpose: Physical table design — **twelve** tables (see Key facts): the original eight, two
shared-infrastructure tables added by `CROSS_MODULE_PRINCIPLES.md`
(`DOC-ARCH-001`, `ARCH-CROSS-001`): `document_master` (reassigned here from Person) and
`field_change_log` (new), plus two PIN code geographic tables added by the SOL-ARCH-010
amendment: `postal_code` and `city_village_postal_code_map`. §40/§41 of this document record the
`document_master`/`field_change_log` reassignment and note that those two tables' logical column
designs are defined by Person (for `document_master`) and the Data Change Architecture (for
`field_change_log`) respectively, while Foundation owns the physical DDL for both.

---

## Key facts

- **Twelve tables**: the original eight — `master_category`, `master_data`, `system_setting`,
  `id_sequence_master`, `country`, `state`, `district`, `city_village` — plus two
  shared-infrastructure tables: `document_master` (a common document registry;
  Person, Heritage, and Publications are consumers, not owners) and `field_change_log`
  (business-significant field-level change tracking, distinct from module-owned `_history`
  tables) — plus two PIN code geographic tables added by the SOL-ARCH-010 amendment:
  `postal_code` and `city_village_postal_code_map`.
- Geographic hierarchy (Country→State→District→City/Village) is explicitly **separate** from
  the NSS organizational hierarchy (Kendra→Anchalika→Zilla→Sakha). Do not conflate the two.
- Central RBAC consumption and History Never Deleted / soft delete established here as
  foundation-level principles other modules build on.

## Note — SQL status

**All twelve designed tables have SQL** — the Foundation Vertical Slice is implemented as
`database/ddl/01_foundation/02_master_category.sql` … `13_city_village_postal_code_map.sql`:
`master_category`, `system_setting`, `id_sequence_master`, `country`,
`document_master`, `field_change_log`, `master_data`, `state`, `district`, `city_village`,
`postal_code`, `city_village_postal_code_map`. `04_foundation_table_design.md` (v1.1.0) has
been updated to describe all twelve. **`02_foundation_erd.md` remains at v1.0.0 and has not
been updated** — it still only covers the original eight tables and omits `document_master`,
`field_change_log`, `postal_code`, and `city_village_postal_code_map`. Treat the implementation
and table-design doc as ahead of the ERD until the ERD is updated to match (not done here — see
`docs/PROJECT_DOCUMENTATION.md` → "Open questions / TODOs"). Full seed data also exists under
`database/seed/01_foundation/` — see
`database/seed/01_foundation/README.md` for exact seeded rows (11 master categories, ~40 master
data values, 9 ID sequences, 5 countries, 112 states, ~770 districts, 5 system settings).

---

## Current Status

Design Complete · ERD Complete (ERD does not yet cover `document_master`, `field_change_log`,
`postal_code`, or `city_village_postal_code_map` — see Note above) · Business Rules Drafted
(SOURCE ALIGNED) · Table Design Drafted (SOURCE ALIGNED, describes all 12 implemented tables) ·
**SQL Implementation Complete** (12 tables + seed data — see Note above). No code has ever
consumed it directly (the Django prototype that referenced a same-named but unrelated
`backend/foundation/` app has since been removed from the repository entirely).
