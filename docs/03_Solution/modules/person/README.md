# NSS ERP Person Module

Version: 1.0.0

Status: DRAFT — SOURCE ALIGNED. All five documents below carry document-level
`Status: DRAFT — SOURCE ALIGNED` — despite being described as "complete," this is a content
version tag, not a promotion out of DRAFT (matches the pattern used by kumari/kishor).

---

## Documents

`01_person_design.md` (SOL-PER-001) — high-level Person module design; establishes
**Person ≠ Member** as the architectural foundation (§74) — a Person may be a Member,
non-member, family member, applicant, or historical record, all under one table.

`02_person_erd.md` — entity relationship design.

`03_person_lifecycle.md` (SOL-PER-005) — 3 Person states (ACTIVE, ACTIVE-DECEASED, INACTIVE),
merge workflow, death handling (death does not delete — PER-BR-026), document lifecycle.

`04_person_business_rules.md` — business rules, PER-BR-001–PER-BR-107.

`05_person_table_design.md` (SOL-PER-004) — logical table design. **One table: `person`.**
`document_master` was reassigned to Foundation (`DOC-ARCH-001`, see below) — Person remains a
consumer via FK, not the owner.

---

## Key decisions (frozen)

UUID internal PKs, centralized `person_id` generation (permanent, unique, human-readable
business identifier — see naming note below), mobile number unique when supplied, email not
globally unique, at least one contact (mobile or email) required.

## Explicitly left OPEN (not silently frozen)

Exact physical address structure, Aadhaar, photo, and blood-group handling — this document set
deliberately does **not** invent a final design for these; see `05_person_table_design.md`
§47-48, §94.

## Known discrepancies — flagged, not resolved here

- **`database/ddl/03_person/` is a superseded prototype, not the target implementation.** It
  uses per-domain master tables (`gender_master`, `marital_status_master`, `address_type_master`)
  instead of the generic `master_category`/`master_data` pattern implemented in
  `database/ddl/01_foundation/`, and will be rewritten against that pattern (see
  `database/ddl/03_person/README.md`, `database/README.md` "Superseded Artifacts", and
  `CLAUDE.md`). Don't build on it, and don't treat the discrepancies below as things to reconcile
  against it — they describe a prototype that itself will be discarded.
- **Business identifier naming:** this doc set names the business identifier `person_id`
  (`05_person_table_design.md` §7-9), but the superseded prototype DDL
  (`database/ddl/03_person/02_person.sql`) names the column `person_code`
  (`uq_person_code`, `idx_person_code`) — matching the project-wide `_code` convention for
  business identifiers. Needs reconciliation before either is treated as final; the rewrite
  against the generic Foundation master-data pattern is the point at which this should be
  settled, not a patch to the current prototype.
- **Address model:** this doc set marks the address structure OPEN (see above), but the
  superseded prototype's `database/ddl/03_person/03_person_address.sql` already implements a
  `person_address` table supporting multiple addresses per person with one enforced primary
  (`uq_person_primary_address`). Don't assume multi-address support is a closed design decision
  just because a (superseded) prototype implements it.

## Ownership reassignment

`document_master` was originally designed here as Person's second table. Project-wide
`CROSS_MODULE_PRINCIPLES.md` (`DOC-ARCH-001`, FROZEN) reassigned it to **Foundation** as a
shared document registry — Person, Heritage, and Publications all consume it as FKs rather
than each owning their own copy. `05_person_table_design.md` §53 keeps the original logical
design for reference (Foundation is now the authoritative DDL owner); the exact FK pattern
(direct FK vs. junction table) is still TBD during Person's own DDL design. `document_master`
itself still has no SQL counterpart anywhere, under either module.

---

## Current Status

Design Complete · ERD Complete · Lifecycle Documented (SOL-PER-005) · Business Rules Complete
(SOURCE ALIGNED) · Table Design Complete (SOURCE ALIGNED, now 1 table — see Ownership
reassignment above) · SQL Implementation: **superseded prototype only** —
`database/ddl/03_person/` implements `person` and `person_address` (using `person_code`, not
`person_id`) against a per-domain master-table pattern that predates the Foundation
`master_category`/`master_data` pattern; it will be rewritten, not extended (see Known
discrepancies above and `CLAUDE.md`).

---

## Target Release

v0.5.0
