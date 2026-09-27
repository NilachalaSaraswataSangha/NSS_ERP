# database/seed/00_bootstrap/

Bootstrap RBAC seed data — role catalogue, permission catalogue, and role-permission
mappings, per SOL-BOOT-001.

Authority: SOL-BOOT-001, SOL-ARCH-011 §4

## Seed Execution Order

Execute AFTER `database/ddl/00_bootstrap/` (all 3 tables) — this is the first seed
data loaded, before Foundation.

## Status

| File | Status |
|---|---|
| `02_role_master.sql` | 9 roles seeded (3 SYSTEM: `NSS_ERP_ADMIN`, `NSS_ERP_AUDITOR`, `NSS_ERP_REPORT_VIEWER`; 6 ORGANIZATIONAL, one per scope level: `NSS_ERP_KENDRA_ADMIN`, `NSS_ERP_ANCHALIKA_ADMIN`, `NSS_ERP_ZILLA_ADMIN`, `NSS_ERP_SAKHA_ADMIN`, `NSS_ERP_PATHA_CHAKRA_ADMIN`, `NSS_ERP_KENDRA_MAHILA_SANGHA_ADMIN`) |
| `01_permission_master.sql` | Populated — ~20 permissions across every module (Foundation/Organization/Person/Family/Membership `*_VIEW`, `AUDIT_VIEW`, admin/user-management, etc.) |
| `03_role_permission.sql` | Populated — ~110 role-to-permission mappings |

Numbered `01`/`02`/`03` reflects the DDL file numbering (`permission_master` before
`role_master` before `role_permission`), not execution readiness — dependency order at
execution time is `02_role_master.sql` and `01_permission_master.sql` first (either order,
no cross-dependency), then `03_role_permission.sql` last (depends on both).

## Design Notes

The 9 seeded roles match the frozen catalogue in SOL-ADMIN-004 §8.7
(updated to 9 roles / 6 scope levels). `NSS_ERP_PATHA_CHAKRA_ADMIN`
(scope `PATHA_CHAKRA`) and, later, `NSS_ERP_KENDRA_MAHILA_SANGHA_ADMIN`
(scope `KENDRA_MAHILA_SANGHA`) were added to both the seed and the design doc
to align with the organizational hierarchy (see
`docs/03_Solution/modules/organization/04_organization_business_rules.md` §28) and the
`scope_level` CHECK
constraint on `role_master`. The 3 SYSTEM roles carry `scope_level = 'NSS-WIDE'`
(an explicit value, not NULL) — the CHECK constraint on `role_master` was widened
accordingly.

Role assignment is independent of governance position — see §8.7 for
the full rationale.
