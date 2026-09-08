# NSS ERP Family Module

Status: DRAFT — full Solution design complete, **not yet implemented in SQL**. No `backend/`
Django app exists anymore (the Django prototype was fully removed from the codebase); the design
below describes a frozen 4-table set — see Note below.

---

## Documents

01_family_module_overview.md — Version 1.0, DRAFT
Purpose: High-level Family module overview (Family Dashboard, Family Tree, Relationship
Management).

02_family_erd.md — Version 1.0.0, DRAFT
Purpose: Entity relationship design for the family group/head/relationship model.

03_family_lifecycle.md — Version 1.0.0, DRAFT, Document ID `SOL-FAM-005`
Purpose: Family Group (ACTIVE/INACTIVE) and Relationship (CURRENT/ENDED) states, append-only
head/transition history, marriage transition, Person-death cascade effects.

04_family_business_rules.md — Version 1.0.0, DRAFT
Purpose: Business rules governing family grouping, headship, and relationship management,
including the frozen Marriage and Family Transition decision. (Was `03_...` before the
lifecycle doc was inserted and file numbers shifted down one slot.)

05_family_table_design.md — Version 1.0.0, DRAFT, Document ID `SOL-FAM-005`
Purpose: Physical table design — a frozen 4-table set: `family_group`, `family_head_history`,
`family_relationship`, `family_transition_history` (the last tied to the frozen Marriage and
Family Transition decision). (Was `04_...`, filename shifted; Document ID `SOL-FAM-005` is
shared with the lifecycle doc above — not yet disambiguated in the source docs.)

---

## Current Status

Design Complete

ERD Complete

Lifecycle Documented (SOL-FAM-005)

Business Rules Drafted (4-table set Frozen at table-design level)

Table Design Frozen

SQL Implementation Not Started

---

## Note

No implementation of this design exists yet. The previous Django prototype's `FamilyGroup` and
`FamilyMembership` models have been removed along with the rest of `backend/` — there is nothing
to reconcile against.
