# database/seed/04_family/

Family has **real verification seed data** — despite the filename saying `tier4_verification_family.sql`
rather than a plain numbered name like Foundation's/Organization's seed files, this is not a
naming quirk for something else; it is genuine `INSERT` data loaded by `database/scripts/02_build.sh`/
`.ps1`, the same way every other tier's seed files are. The `tier4_verification` prefix simply
signals its purpose: it exists to give the Family Verification UI (`/family`) and
`tests/test_family.py` something concrete to render/assert against, the same role Organization's
and Bootstrap's seed data play for their own tiers. Unlike `database/seed/03_person/README.md`
(Person has **zero** seed rows), Family's seed file inserts real rows into all three
non-append-only-history-only-by-nature tables that need starter data.

- `01_tier4_verification_family.sql` — creates **one** family group (`F1`, "Mishra Paribara") at
  Ekamra Sakha (`organization_code = 'SKH1'`), **three** `family_relationship` rows (Ramesh
  Mishra `P1` as FATHER, Sushma Mishra `P2` as SPOUSE, Aniket Mishra `P3` as SON — all
  `effective_from = 2010-04-01`, `is_current = TRUE`), and **one** `family_head_history` row
  (Ramesh Mishra `P1`, head since `2010-04-01`, `effective_to` left `NULL` — i.e. still the
  current head). `family_transition_history` is seeded with **zero** rows — it is purely an
  append-only log of *future* family-to-family moves (marriage, new family formation, etc.);
  there is nothing to backfill for a freshly-seeded family with no history yet.

## How the seed resolves its FKs

Every `INSERT` is a `SELECT ... FROM ... JOIN ...` rather than a literal `VALUES (...)` with
hardcoded UUIDs, because every FK target (`family_status_master_data_pk`, `sakha_organization_pk`,
`person_pk`, `relationship_type_master_data_pk`) is a `gen_random_uuid()`-generated UUID assigned
at row-creation time by an earlier phase, not a fixed value known in advance:

- The family group row resolves its status via `nss.master_data`/`nss.master_category` filtered to
  `category_code = 'STATUS'` and `value_code = 'ACTIVE'`, and its Sakha via
  `nss.organization` filtered to `organization_code = 'SKH1'`.
- Each relationship row resolves its person via `nss.person` filtered to `person_id` (`P1`/`P2`/
  `P3` — note the unpadded ID format, not `P00000001`) and its relationship type via
  `nss.master_data`/`nss.master_category` filtered to `category_code = 'RELATIONSHIP_TYPE'` and
  the appropriate `value_code` (`FATHER`/`SPOUSE`/`SON`).

This means the seed file has a hard ordering dependency: it must run **after** Foundation's
`master_data`/`master_category` seed (for `STATUS` and `RELATIONSHIP_TYPE` values), Organization's
seed (for `SKH1`), and Person seed data providing `P1`/`P2`/`P3` — consistent with
`database/ddl/04_family/README.md`'s stated execution order (Family DDL/seed run after Foundation,
Organization, and Person).

## Row counts

| Table | Rows |
|---|---:|
| `family_group` | 1 |
| `family_relationship` | 3 |
| `family_head_history` | 1 |
| `family_transition_history` | 0 |

`tests/test_family.py` asserts these exact counts (`test_list_returns_seeded_families`,
`test_seeded_family_has_correct_data`, `test_members_seeded_count`,
`test_head_history_seeded_count`) — if this seed file's data changes, those tests must be
updated to match.
