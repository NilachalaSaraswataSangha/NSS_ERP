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
| `02_role_master.sql` | 8 roles seeded (3 SYSTEM: `NSS_ERP_ADMIN`, `NSS_ERP_AUDITOR`, `NSS_ERP_REPORT_VIEWER`; 5 ORGANIZATIONAL, one per scope level: `NSS_ERP_KENDRA_ADMIN`, `NSS_ERP_ANCHALIKA_ADMIN`, `NSS_ERP_ZILLA_ADMIN`, `NSS_ERP_SAKHA_ADMIN`, `NSS_ERP_PATHA_CHAKRA_ADMIN`) |
| `01_permission_master.sql` | Empty — permission catalogue not yet frozen |
| `03_role_permission.sql` | Empty — depends on the permission catalogue above |

Numbered `01`/`02`/`03` reflects the DDL file numbering (`permission_master` before
`role_master` before `role_permission`), not execution readiness — `02_role_master.sql`
is the only one with actual data right now.

## Design Notes

The 8 seeded roles match the frozen catalogue in SOL-ADMIN-004 §8.7
(updated to 8 roles / 5 scope levels). `NSS_ERP_PATHA_CHAKRA_ADMIN`
(scope `PATHA_CHAKRA`) was added to both the seed and the design doc
to align with the organizational hierarchy and the `scope_level` CHECK
constraint on `role_master`.

Role assignment is independent of governance position — see §8.7 for
the full rationale.
