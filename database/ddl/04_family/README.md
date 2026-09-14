# database/ddl/04_family/

Family Module DDL — 4 tables per SOL-FAM-005, SOL-FAM-003, SOL-ARCH-010.

Authority: SOL-FAM-005 (Family Table Design), SOL-FAM-003, SOL-ARCH-010 (DDL Creation Order)

## DDL Execution Order

Execute AFTER all Foundation DDL (`database/ddl/01_foundation/`), Organization DDL
(`database/ddl/02_organization/`), and Person DDL (`database/ddl/03_person/`) — `family_group`
references `organization`, and `family_relationship`/`family_head_history`/
`family_transition_history` all reference `person`.

| # | File | Table | Depth | Sequence |
|--:|------|-------|------:|:--------:|
| 01 | `01_family_group.sql` | `family_group` | 2 | #36 |
| 02 | `02_family_relationship.sql` | `family_relationship` | 3 | #56 |
| 03 | `03_family_head_history.sql` | `family_head_history` | 3 | #57 |
| 04 | `04_family_transition_history.sql` | `family_transition_history` | 3 | #58 |

## What These Tables Are For

Per the frozen "Family First Model" principle, a family is a first-class entity independent of
membership — a Person may belong to a Family without ever becoming an NSS Member. These four
tables implement that:

- **`family_group`** — the family record itself: a `family_name`, the Sakha `organization` it is
  registered under (`sakha_organization_pk`), a lifecycle status resolved through Foundation's
  unified `STATUS` category (not a dedicated Family status master), and an optional
  `formed_date`. This is the root of the module — every other table hangs off
  `family_group_pk`.
- **`family_relationship`** — the membership-of-a-family-unit table: one row per (family, person,
  relationship type) linking a `person` into a `family_group` with a relationship type resolved
  through Foundation's `RELATIONSHIP_TYPE` master_data category (FATHER, MOTHER, SPOUSE, SON,
  DAUGHTER, etc. — the same category Person's emergency-contact relationship field also draws
  from) and an effective-dated period (`effective_from`/`effective_to`/`is_current`).
- **`family_head_history`** — an append-only log of who has headed a family and when
  (`effective_from`/`effective_to`), never overwritten in place — this is the "History Never
  Deleted" principle applied to family headship.
- **`family_transition_history`** — an append-only log of a person moving from one family group to
  another (marriage, new family formation, change of family unit), preserving both the
  `old_family_group_pk` and `new_family_group_pk` rather than mutating `family_relationship` rows
  in place.

## Key FK Relationships

- `family_group.sakha_organization_pk` → `nss.organization(organization_pk)` — the Sakha a family
  is registered under.
- `family_group.family_status_master_data_pk` → `nss.master_data(master_data_pk)` — the unified
  `STATUS` category, same pattern as `organization.status_master_data_pk`. No dedicated
  `family_status_master` table exists — per the frozen "Master Data Driven" principle, one
  generic `master_category`/`master_data` pair serves every module's classification needs.
- `family_relationship.family_group_pk` → `family_group(family_group_pk)`; `person_pk` →
  `nss.person(person_pk)`; `relationship_type_master_data_pk` → `nss.master_data(master_data_pk)`
  (category `RELATIONSHIP_TYPE`).
- `family_head_history.family_group_pk` → `family_group(family_group_pk)`; `person_pk` →
  `nss.person(person_pk)`.
- `family_transition_history.old_family_group_pk` and `.new_family_group_pk` both →
  `family_group(family_group_pk)` (two separate FKs to the same table); `person_pk` →
  `nss.person(person_pk)`.

Like `organization` and `person`, audit-actor FKs (`created_by_sangha_sevi_pk`,
`updated_by_sangha_sevi_pk`, `deleted_by_sangha_sevi_pk`) are nullable columns in this pass —
their FK constraints against `sangha_sevi` are deferred to Pass 2, after that table exists
(Governance/Membership tier).

## Non-Obvious Constraints

- **`chk_family_group_soft_delete`** — the standard `(is_active = TRUE AND deleted_at IS NULL) OR
  (is_active = FALSE AND deleted_at IS NOT NULL)` pattern shared with `organization`.
- **`uq_family_rel_person_current`** — a **partial unique index**, not a table-level constraint:
  `UNIQUE (family_group_pk, person_pk) WHERE is_current = TRUE`. A person may have multiple
  historical relationship rows in the same family (e.g. a status change), but only one row per
  (family, person) pair may be flagged current at a time — the same partial-unique-index
  technique Person uses for `uq_person_primary_address`.
- **`chk_family_rel_current_consistency`** — ties `is_current` to `effective_to`: a current
  relationship must have `effective_to IS NULL`, and a historical one must have it set. This
  keeps "is this relationship active right now" derivable from either column without them
  drifting out of sync.
- **`uq_family_head_current`** — another partial unique index: `UNIQUE (family_group_pk) WHERE
  effective_to IS NULL`. At most one row per family group may be the *current* head (no
  `effective_to`); every past head has an `effective_to` set and is never deleted, only
  superseded by a new row.
- **`chk_family_trans_different_families`** — `CHECK (old_family_group_pk <> new_family_group_pk)`
  on `family_transition_history`: a transition record must actually move a person between two
  distinct family groups; a no-op "transition" to the same family is rejected at the DB level.
- **`chk_family_trans_type`** — a `CHECK (transition_type IN ('MARRIAGE',
  'NEW_FAMILY_FORMATION', 'CHANGE_OF_FAMILY_UNIT', 'OTHER'))` enumeration. Unlike relationship
  type or family status, transition type is **not** resolved through Foundation `master_data` —
  it's a plain `VARCHAR(50)` with a CHECK constraint, since it's a closed, small, code-only set
  with no display-name/description/sort-order metadata worth modeling as reference data.
- **Business identifier format** — `family_group.family_id` (e.g. `F1`) follows the project-wide
  unpadded ID convention adopted across this branch (see
  `docs/00_Project_Governance/STD/01_project_standards.md` and
  `docs/03_Solution/database/DATABASE_DESIGN_STANDARDS.md`) — not zero-padded (`F00000001`), per
  the `id_sequence_master` DDL's loosened `CHECK (padding_length BETWEEN 0 AND 12)` constraint.

Matches `docs/03_Solution/modules/family/05_family_table_design.md` (SOL-FAM-005) closely — see
that doc for full design rationale. As of this writing that module doc set is still `Status:
DRAFT` (v1.0/v1.0.0), even though its table/column shapes already match this implemented DDL
1:1; it has not yet been reconciled to `FROZEN` the way Person's module docs were before
`03_person/` was built. See also `docs/PROJECT_DOCUMENTATION.md` for the tier-by-tier plan.
