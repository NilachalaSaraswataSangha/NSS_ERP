# NSS ERP Membership Module

Status: DRAFT — full Solution design complete, **not yet implemented in SQL**. A prior Django
prototype app (`backend/membership/`, with plain-integer-PK models `MembershipType`,
`MembershipStatus`, `SanghaSevi` and no audit/soft-delete columns) existed early in the project
but was removed along with the rest of the Django prototype (`backend/`) — see CLAUDE.md and
`docs/03_Solution/architecture/TECH_STACK_DECISIONS.md`. It is preserved in Git history only,
not on disk. The design below describes a much richer intended schema than that removed
prototype ever had — see Note below.

---

## Documents

01_membership_module_overview.md — Version 1.0, DRAFT
Purpose: High-level Membership module overview (Member Registration, Membership Types,
Approval, Renewal, Transfer, Membership Journey, Sangha Sevi ID Management).

02_membership_erd.md — Version 1.0.0, DRAFT
Purpose: Entity relationship design across the membership lifecycle.

03_membership_lifecycle.md — Version 1.0.0, DRAFT
Purpose: Membership state machine — Probationary → Regular → Associate, renewal (Dola Purnima
deadline, no grace period), transfer, reinstatement touchpoints.

04_membership_business_rules.md — Version 1.0.0, DRAFT
Purpose: Business rules governing membership approval, renewal, transfer, and journey tracking.

05_membership_table_design.md — Version 1.0.0, DRAFT, Document ID `SOL-MEM-005`
Purpose: Physical table design — `sangha_sevi`, `anumati_patra` (+ history), `parichaya_patra`
(+ history), `membership_status_history`, `membership_renewal_request`/`history`,
`membership_transfer_history`, `membership_journey_event`, `probationary_member_review` — UUID
`_pk` internal keys, full audit columns.

---

## Current Status

Design Complete

ERD Complete

Lifecycle Documented

Business Rules Drafted (not yet Frozen)

Table Design Drafted (not yet Frozen)

SQL Implementation Not Started

---

## Note

The removed `backend/membership/models.py` (`MembershipType`, `MembershipStatus`, `SanghaSevi`)
was a much simpler placeholder that predated this design — plain auto-increment PKs, no UUID, no
`created_by_sangha_sevi_pk`-style audit trail, and none of the ~10 supporting history/journey
tables in `05_membership_table_design.md`. Same two-track gap already tracked for
`organization`/`person` in `docs/PROJECT_DOCUMENTATION.md` → Conventions & gotchas — don't
assume the removed Django model and this design describe the same schema.
