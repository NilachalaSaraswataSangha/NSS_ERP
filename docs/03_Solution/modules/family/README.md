# NSS ERP Family Module

Status: DRAFT — full Solution design complete, **not yet implemented in SQL or reconciled with
Django code**. The `backend/family/` Django app already has real models (`FamilyGroup`,
`FamilyMembership`); see `backend/family/README.md`. The design below describes a richer,
frozen 4-table set — see Note below.

---

## Documents

01_family_module_overview.md — Version 1.0, DRAFT
Purpose: High-level Family module overview (Family Dashboard, Family Tree, Relationship
Management).

02_family_erd.md — Version 1.0.0, DRAFT
Purpose: Entity relationship design for the family group/head/relationship model.

03_family_business_rules.md — Version 1.0.0, DRAFT
Purpose: Business rules governing family grouping, headship, and relationship management,
including the frozen Marriage and Family Transition decision.

04_family_table_design.md — Version 1.0.0, DRAFT, Document ID `SOL-FAM-004`
Purpose: Physical table design — a frozen 4-table set: `family_group`, `family_head_history`,
`family_relationship`, `family_transition_history` (the last tied to the frozen Marriage and
Family Transition decision).

---

## Current Status

Design Complete

ERD Complete

Business Rules Drafted (4-table set Frozen at table-design level)

Table Design Frozen

SQL Implementation Not Started

---

## Note

`backend/family/models.py` currently has only `FamilyGroup` and `FamilyMembership` — no
`family_head_history` or `family_transition_history` equivalents exist in code yet. Same
two-track gap already tracked for `organization`/`person` in `docs/PROJECT_DOCUMENTATION.md` →
Conventions & gotchas.
