# database/ddl/05_membership/

Membership Module DDL — 12 tables (Depth 2–4) per SOL-MEM-005, SOL-MEM-003.

Authority: SOL-MEM-005 v1.0 (Physical Table Design), SOL-MEM-003 (Business Rules), MBR-001
through MBR-035 (business-rule identifiers cited in table comments)

> **Design-doc status note:** `docs/03_Solution/modules/membership/README.md` still reads
> "Status: DRAFT — full Solution design complete, **not yet implemented in SQL**" / "SQL
> Implementation Not Started." That status predates this DDL — all 12 tables below are real,
> implemented, and executed by `database/scripts/02_build.sh`/`02_build.ps1`. The module design
> docs themselves are out of scope for this pass (a separate governance/design update); treat the
> tables in this folder, not that README, as the current source of truth for what exists in the
> database.

## DDL Execution Order

Execute AFTER Foundation, Organization, and Person DDL (`database/ddl/01_foundation/`,
`02_organization/`, `03_person/`) — every table here has at least one FK into `person`,
`master_data`, or `organization`, and most depend on `nss.sangha_sevi` itself (Depth 2).

| # | File | Table | Depth | Depends on |
|--:|------|-------|------:|------------|
| 01 | `01_sangha_sevi.sql` | `sangha_sevi` | 2 | `person`, `master_data` (×2), `organization` |
| 02 | `02_membership_status_history.sql` | `membership_status_history` | 3 | `sangha_sevi`, `master_data` |
| 03 | `03_membership_renewal_request.sql` | `membership_renewal_request` | 3 | `sangha_sevi` |
| 04 | `04_membership_renewal_history.sql` | `membership_renewal_history` | 3 | `sangha_sevi` |
| 05 | `05_membership_transfer_history.sql` | `membership_transfer_history` | 3 | `sangha_sevi`, `organization` (×2) |
| 06 | `06_membership_sakha_affiliation.sql` | `membership_sakha_affiliation` | 3 | `sangha_sevi`, `organization` |
| 07 | `07_membership_journey_event.sql` | `membership_journey_event` | 3 | `sangha_sevi` |
| 08 | `08_probationary_member_review.sql` | `probationary_member_review` | 3 | `sangha_sevi` |
| 09 | `09_parichaya_patra.sql` | `parichaya_patra` | 3 | `sangha_sevi`, `organization` |
| 10 | `10_parichaya_patra_history.sql` | `parichaya_patra_history` | 4 | `parichaya_patra` |
| 11 | `11_anumati_patra.sql` | `anumati_patra` | 3 | `sangha_sevi` |
| 12 | `12_anumati_patra_history.sql` | `anumati_patra_history` | 4 | `anumati_patra` |

## What Each Table Is For

- **`sangha_sevi`** — the member record itself. One row per membership, one membership per
  person (`UNIQUE (person_pk)` — "One Person = One Membership"). Carries the permanent,
  NSS-wide **Sangha Sevi ID** (`sangha_sevi_id`, format `SS1`, `SS2`, … — no zero-padding, per
  the project-wide loosened `id_sequence_master.padding_length` change), current membership
  type (Probationary/Regular/Associate/Honorary via `master_data` category
  `MEMBERSHIP_TYPE`), current status (via the unified `STATUS` category), and current Sakha
  (`organization_pk`). The Sangha Sevi ID never changes and is never reused, including across
  transfers.
- **`membership_status_history`** — append-only timeline of every status change
  (ACTIVE/SUSPENDED/LAPSED/…) with `effective_from`/`effective_to`. The *current* status still
  lives on `sangha_sevi`; this table exists purely so status history is never lost.
- **`membership_renewal_request`** — a request/approval workflow row (`PENDING` →
  `APPROVED`/`REJECTED`) created before a renewal is granted. A CHECK constraint
  (`chk_mem_renewal_req_review_consistency`) enforces that `PENDING` rows have no reviewer/date
  yet, and `APPROVED`/`REJECTED` rows always have a `reviewed_date`.
- **`membership_renewal_history`** — one row per *completed* renewal (financial-year validity,
  1 April–31 March). Distinct from the request table: a request is a workflow artifact that may
  be rejected; a history row is a permanent, never-deleted record that a renewal actually
  happened.
- **`membership_transfer_history`** — one row per Sakha-to-Sakha transfer
  (`old_organization_pk` → `new_organization_pk`, `chk_mem_transfer_different_orgs` guarantees
  they differ). Sangha Sevi ID is unchanged by a transfer; `old_local_sakha_erp_id`/
  `new_local_sakha_erp_id` are point-in-time snapshots for audit purposes only — the
  authoritative current/historical Local Sakha ERP IDs live on `membership_sakha_affiliation`.
- **`membership_sakha_affiliation`** — the **authoritative source of the Local Sakha ERP ID**
  (Tier 2 identity, e.g. `ESS1192`). One row per person per Sakha, never reassigned to a
  different person once issued. A partial unique index
  (`uq_mem_sakha_aff_active WHERE effective_to IS NULL`) enforces exactly one *active*
  affiliation per member at any time; on transfer, the old row is closed
  (`effective_to` set, `affiliation_status = 'ARCHIVED'`) and a new row is opened at the new
  Sakha with a new `local_sakha_erp_id` — the old row is archived, never deleted, and can be
  reactivated (`affiliation_status = 'REACTIVATED'`) if the member later returns to the same
  Sakha.
- **`membership_journey_event`** — a free-form, chronological timeline of lifecycle events
  (`MEMBERSHIP_CREATED`, `PROBATIONARY_STARTED`, `REGULAR_ENROLMENT`, `TRANSFER`,
  `STATUS_CHANGE`, `KUMARI_TRANSITION`, etc.). `event_type` is a plain `VARCHAR`, not an FK to
  `master_data` — the event catalogue is extensible and module-specific, controlled at the
  application layer rather than frozen as reference data.
- **`probationary_member_review`** — periodic/final/special review checkpoints for a
  Probationary member working toward Regular enrolment (Bye-Law §B(b): at least one year
  probationary + one year training). Records outcome (`PASS`/`FAIL`/`DEFERRED`), training
  completion, and the Sakha's recommendation — without overwriting or replacing the membership
  record itself.
- **`parichaya_patra`** — the annual Identity Card issued by Kendra Sangha. `document_number`
  is the **Kendra Number** (Tier 3 identity, format `<seq>/<FY start>/<FY end>`, e.g.
  `345/2026/2027`), globally unique (`uq_pp_document_number`). `affiliated_organization_pk` and
  `local_sakha_erp_id` are **point-in-time snapshots** of what was printed on that year's card —
  the live/authoritative affiliation still lives on `membership_sakha_affiliation`. A partial
  unique index (`uq_pp_active_per_member`) enforces at most one `ACTIVE` card per member.
- **`parichaya_patra_history`** — change log for a `parichaya_patra` row (`ISSUED`/`RENEWED`/
  `EXPIRED`/`CANCELLED`/`REPLACED`) with previous/new status. Historical records are never
  deleted.
- **`anumati_patra`** — the Probationary member's credential ("Admit Card," Bye-Law §B(a)),
  structurally identical to `parichaya_patra` (own `document_number`, validity range, status,
  partial unique "one ACTIVE per member" index) but with no Sakha-snapshot columns — it isn't
  tied to a specific Sakha the way the Identity Card is. Must be valid at least one year before
  Regular enrolment (Bye-Law §B(b)(i)).
- **`anumati_patra_history`** — change log for an `anumati_patra` row, same shape and rationale
  as `parichaya_patra_history`.

## The "Current State + History" Pairing Pattern

Membership is the first module to lean heavily on a recurring design idiom used throughout this
DDL: a **mutable "current state" table** paired with an **append-only history table** that
records every transition into or out of that state. This shows up three times:

1. `sangha_sevi.membership_status_master_data_pk` (current) ↔ `membership_status_history`
   (every change, with `effective_from`/`effective_to`).
2. `parichaya_patra` (current + past cards, since `status` distinguishes `ACTIVE` from
   `EXPIRED`/`CANCELLED`/`REPLACED`) ↔ `parichaya_patra_history` (the *events* that changed a
   given card's status — issuance, renewal, expiry, cancellation, replacement).
3. `anumati_patra` ↔ `anumati_patra_history` — identical shape to the Parichaya Patra pair.

The same idiom appears once more at a *relationship* granularity rather than a single-table
granularity: `membership_sakha_affiliation` is itself a "current + history" table for a
member's Sakha affiliation (no separate history table needed — old rows are simply closed via
`effective_to`, and `membership_transfer_history` records the *transfer events* between
affiliation periods). Two other tables — `membership_renewal_request` and
`membership_renewal_history` — split what could have been one table into a workflow table
(mutable until approved/rejected) and a permanent completed-renewal ledger, the same
history-never-overwritten principle applied to a process rather than a status field.

Why this pattern instead of just overwriting the current-state column: "History Never Deleted"
is a frozen project-wide principle (see `CLAUDE.md`); status/affiliation/document changes are
exactly the kind of business fact that must remain reconstructable for governance and
audit purposes (e.g. proving when a member transferred Sakhas, or when a Parichaya Patra was
replaced), not just what the *current* value happens to be.

## Non-Obvious Constraints

- **Three-tier identity split across three different tables.** Tier 1 (Sangha Sevi ID) lives on
  `sangha_sevi`; Tier 2 (Local Sakha ERP ID) lives on `membership_sakha_affiliation`, **not** on
  `sangha_sevi` — this was an explicit frozen decision (`MEM-PENDING-001 FROZEN`, referenced in
  `01_sangha_sevi.sql`'s own header comment) precisely because the Local Sakha ERP ID changes on
  transfer while the Sangha Sevi ID does not; Tier 3 (Kendra Number) lives on
  `parichaya_patra.document_number`.
- **`chk_mem_sakha_aff_status_consistency`** ties `effective_to` nullability to
  `affiliation_status`: open-ended rows (`effective_to IS NULL`) must be `ACTIVE` or
  `REACTIVATED`; closed rows (`effective_to IS NOT NULL`) must be `ARCHIVED`. This is enforced
  at the DB level, not just in application code.
- **`uq_mem_sakha_aff_local_id UNIQUE (organization_pk, local_sakha_erp_id)`** — a Local Sakha
  ERP ID is unique *within* a Sakha (not globally); the same numeric suffix can recur at a
  different Sakha (seed data shows `ESS1100` at SKH1 vs. `CTC1` at SKH2 for the same member,
  Suresh Patel, before/after his transfer).
- **Two partial unique indexes enforcing "at most one active X per member"** —
  `uq_mem_sakha_aff_active` (one open affiliation), `uq_pp_active_per_member` (one active
  Parichaya Patra), `uq_ap_active_per_member` (one active Anumati Patra) — all implemented as
  `CREATE UNIQUE INDEX ... WHERE <condition>`, not table-level `CHECK` constraints, because the
  invariant spans multiple rows (a `CHECK` constraint can only see one row at a time).
- **Audit-actor FKs deferred to Pass 2.** Every `*_by_sangha_sevi_pk` column
  (`created_by_sangha_sevi_pk`, etc.) is a nullable `UUID` with no FK constraint in this pass —
  the same "Two-Pass DDL Strategy" gap noted for `role_master`/`permission_master` and
  Organization/Person, now finally resolvable in a later pass because `sangha_sevi` (the table
  those FKs would reference) exists as of this module. `01_sangha_sevi.sql`'s own header comment
  calls this out explicitly ("deferred to Pass 2 for initial bootstrap — first member
  creation").
- **`event_type` on `membership_journey_event` is a plain `VARCHAR`, not an FK** — deliberately
  not constrained to `master_data`, since the event catalogue is extensible at the application
  layer (unlike, say, membership type or status, which are frozen reference data).
- **No zero-padding on any business identifier in this module** — `sangha_sevi_id` (`SS1`),
  `local_sakha_erp_id` (`ESS1192`), and Kendra/Anumati document numbers all follow the
  project-wide loosened ID-format decision (`id_sequence_master`'s `padding_length` CHECK now
  allows `0`), documented in `docs/00_Project_Governance/STD/01_project_standards.md` and
  `docs/03_Solution/database/DATABASE_DESIGN_STANDARDS.md`.

See `docs/03_Solution/modules/membership/05_membership_table_design.md` (`SOL-MEM-005`) for the
full design rationale — noting the design-doc status caveat at the top of this file. See also
`docs/PROJECT_DOCUMENTATION.md` for the tier-by-tier plan and
`docs/03_Solution/api/API_CONTRACT.md` §8 for how these tables are exposed over HTTP.
