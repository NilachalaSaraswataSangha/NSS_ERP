# database/ddl/00_bootstrap/

Bootstrap RBAC DDL — 3 tables (Depths 0–1) per SOL-BOOT-001, SOL-ARCH-011, SOL-ARCH-010.

Authority: SOL-BOOT-001, SOL-ARCH-011, SOL-ARCH-010

## Why this runs before Foundation

`role_master` and `permission_master` have zero FK dependencies on any other table,
so per SOL-ARCH-011 they are created and seeded in a "Phase 0" that runs before
Foundation — resolving the audit-actor circular dependency (audit columns need a
`sangha_sevi` identity that itself depends on Foundation/Organization/Person, which
don't exist yet at this point). Audit-actor FKs (`*_by_sangha_sevi_pk`) on these
tables are deferred to Pass 2, same as every other module.

## DDL Execution Order

| # | File | Table | Depth | Sequence |
|--:|------|-------|------:|:--------:|
| 01 | `01_role_master.sql` | `role_master` | 0 | #13 |
| 02 | `02_permission_master.sql` | `permission_master` | 0 | #14 |
| 03 | `03_role_permission.sql` | `role_permission` | 1 | #20 |

## Ownership

Administration owns all 3 tables
(`docs/03_Solution/modules/administration/05_administration_table_design.md` §2,
Table Ownership Declaration) — "Bootstrap" here describes DDL-execution phasing
only, not a separate module or a change of ownership. Column-level design is
frozen in `docs/03_Solution/modules/administration/06_bootstrap_rbac_table_design.md`
(SOL-BOOT-001).

## Design Notes

- **`role_master.scope_level`** CHECK constraint allows `KENDRA`/`ANCHALIKA`/`ZILLA`/
  `SAKHA`/`PATHA_CHAKRA` — 5 values, matching the 8-role frozen catalogue
  in SOL-ADMIN-004 §8.7 (5 organizational roles × 5 scope levels + 3 system roles).
- **`role_permission`** has a reduced audit-column set (no `updated_at`/
  `updated_by_sangha_sevi_pk`) since mappings are never updated in place, only
  soft-deleted and recreated.

## Status

DDL is complete and committed for all 3 tables. Seed data is partial —
see `database/seed/00_bootstrap/README.md`.
