# NSS ERP — Festival Reference Calendar Architecture

**Document ID:** SOL-ARCH-013
**Version:** 1.0.0
**Status:** APPROVED — all design decisions resolved 2026-10-01; implementation in progress
**Module:** Foundation (proposed owner)
**Parent System:** Nilachala Saraswata Sangha ERP
**Related:** SOL-ARCH-010 (DDL Creation Order), SOL-FND-004 (Foundation Table
Design), SOL-MEM-003 (Membership Lifecycle), SOL-MEM-004 (Membership Business
Rules — MBR-011A, MBR-029), SOL-AUDIT-004 (Audit Trigger)

---

# 1. Purpose

This document proposes the table design for an authoritative, per-year source
of NSS festival reference dates — principally **Dola Purnima** — so that the
business rules which key off those dates can be enforced in the database and
API instead of existing only as prose.

This is a **proposal gated on approval**. No DDL file, seed file, or API code
has been created. Section 16 lists exactly what is created on approval.

---

# 2. Problem Statement

Three approved business rules use Dola Purnima as their controlling date.
**None of the three is enforced anywhere in code today**, and all three are
blocked by the same single missing fact: the system does not know what date
Dola Purnima falls on in any given year.

| Rule | Document | What it needs |
|---|---|---|
| MBR-011A — Regular enrollment date | SOL-MEM-004 | The next Dola Purnima on or after a Probationary Member's eligibility date |
| MBR-029 — Transfer effective date | SOL-MEM-004 §(transfer) | The Dola Purnima that a approved transfer takes effect on |
| Membership renewal deadline (no grace period) | SOL-MEM-003 §11, module README | The Dola Purnima that closes the current membership year |

Verified absence (greps across the repository):

- No `nss.*` table, column, or CHECK constraint references a festival or
  Purnima date.
- No `api/` module references Dola Purnima in any form.
- The only representations that exist are **prose in documents** and
  **hard-coded strings in UI mockups** — for example
  `docs/03_Solution/ui/mockups/07_member_profile.html` displays
  "Dola Purnima 2026" / "Dola Purnima 2027" as a credential validity window,
  and `02_kendra_dashboard.html` displays "89 due before Dola Purnima". These
  are static mockup text with no backing data.
- `DATABASE_CODE_EXPLANATIONS.md` documents one seeded transfer row with
  effective date `2025-03-14` annotated "Dola Purnima 2025" in a free-text
  remarks column — i.e. the date exists in the system exactly once, as an
  un-validated literal inside a comment-style field.

The gap is therefore not a Membership-module gap. It is a **missing shared
reference-data capability** that three rules in one module already need and
that other modules (Programmes & Events, UPBS, Finance year-end) will need.

---

# 3. Why Dola Purnima Cannot Be Computed

Dola Purnima is **Phalguna Purnima** — the full-moon day of the Phalguna
month in the Hindu lunisolar calendar. Consequences:

1. **It has no fixed Gregorian month/day.** It drifts across late February
   and March from year to year. No `MAKE_DATE(year, 3, 14)`-style formula is
   correct.
2. **Computing it requires an astronomical ephemeris**, not arithmetic — the
   exact instant of full moon, resolved to a local civil date.
3. **The civil date depends on regional convention.** Which civil day a tithi
   "belongs to" varies by panchanga tradition (sunrise rule, regional
   almanac). Odisha convention governs for NSS.
4. **NSS observance is an institutional decision, not merely an astronomical
   one.** The Kendra Sangha's declared observance date is the date the ERP
   must honour, even in a year where almanacs disagree.

**Conclusion:** the date must be **recorded as authoritative data confirmed by
the Kendra Sangha**, never derived at runtime. Any computed approximation
would silently mis-date membership conversions, transfers, and renewal
deadlines — all legally significant under the Bye-Law. This is the central
design constraint.

---

# 4. Rejected Alternatives

Each was considered and rejected for a stated reason. Recording the rejections
so they are not re-litigated later.

## 4.1 Store in `master_data` — REJECTED

`nss.master_data` is a code→name value list (`value_code`, `value_name`,
`description`, `display_order`). It has:

- no typed `DATE` column — the date would have to be stuffed into
  `description` as text, defeating all validation and all date arithmetic;
- the wrong cardinality — `master_data` is one row per *value*, but a festival
  needs **one row per year**. Modelling it would require abusive codes like
  `DOLA_PURNIMA_2027`, `DOLA_PURNIMA_2028`, growing forever.

`master_data` is correct for enumerations. A dated annual calendar is not an
enumeration.

## 4.2 Store in `system_setting` — REJECTED

Same defects, worse: `system_setting` is single key→value configuration with no
typed date, no per-year row, no uniqueness guarantee per year, and no natural
place for confirmation provenance. A key like
`DOLA_PURNIMA_2027 = '2027-03-13'` is configuration abuse — it makes a
Bye-Law-significant date editable as untyped free text with no audit meaning.

## 4.3 Compute from a lunar algorithm — REJECTED

See section 3. Requires an ephemeris dependency, cannot represent regional
convention, and cannot represent an institutional override. Introduces a
silent-wrong-answer failure mode on dates that govern membership status.

## 4.4 Hard-code a constant or a per-year Python dict — REJECTED

Puts Bye-Law-significant data in application code: requires a code deploy to
add next year's date, is invisible to the database, cannot be audited by the
existing audit trigger, cannot be corrected by an administrator, and would
have to be duplicated in the frontend.

## 4.5 Add a `dola_purnima_date` column to each consuming table — REJECTED

Violates one-owner-per-table and normalisation: the same date would be copied
into `sangha_sevi`, `membership_transfer_history`, and every renewal record,
with no single point of correction. If the Kendra Sangha revises an observance
date, every copy must be chased.

## 4.6 Model it as an Event in Programmes & Events / UPBS — REJECTED

See section 10 (module boundary). A *reference date* is not an *event
occurrence*: it has no venue, registration, budget, attendance, or organiser.
Making Membership depend on the Events module to resolve a renewal deadline
would invert the dependency direction established in MODULE_DEPENDENCY_MAP
(SOL-ARCH-007) and make Foundation-level rules depend on a Tier-higher module.

---

# 5. Recommended Design

**Two Foundation-owned tables, master + per-year instance** — mirroring the
project's existing `master_category` → `master_data` and `postal_code` →
`city_village_postal_code_map` pattern.

```text
nss.festival_master              (one row per festival — WHAT it is)
        |
        | 1 : N
        v
nss.festival_calendar_date       (one row per festival per year — WHEN it falls)
```

Rationale for two tables rather than one flat table:

- The festival's *identity* (code, name, Odia name, lunar basis, whether the
  ERP treats it as a reference date) is stable and must not be repeated on
  every year row.
- The per-year date carries its own **provenance and confirmation state**,
  which the identity row must not.
- `festival_code` becomes a stable FK target that rules and API helpers refer
  to by code (`'DOLA_PURNIMA'`), independent of how many years are loaded.

A single flat table would duplicate name/basis per year and has nowhere
coherent to hang confirmation metadata.

---

# 6. Table — `nss.festival_master`

## 6.1 Purpose

Registry of NSS-significant festivals and observances. Identity only — no
dates.

## 6.2 Primary Key

```
festival_master_pk UUID PRIMARY KEY
```

## 6.3 Logical Business Attributes

```
Festival Code          (stable business code, e.g. DOLA_PURNIMA)
Festival Name          (English/transliterated)
Festival Name (Odia)   (optional, for UI display)
Lunar Basis            (descriptive, e.g. "Phalguna Purnima")
Is ERP Reference Date  (does any business rule key off this festival?)
Description
Display Order
Active State
```

## 6.4 Key Design Points

- `festival_code` is UNIQUE and **stable** — code and API refer to
  `'DOLA_PURNIMA'`, never to a UUID literal or a name string.
- `lunar_basis` is **descriptive text, not a computation input.** It documents
  *why* the date moves, for the administrator entering it. Nothing parses it.
  This is deliberate — see section 3.
- `is_erp_reference_date` distinguishes festivals that *drive business rules*
  (Dola Purnima) from festivals recorded only for the calendar/display. Only
  reference-date festivals are subject to the coverage rule in section 14.1.

---

# 7. Table — `nss.festival_calendar_date`

## 7.1 Purpose

The authoritative observed Gregorian date of a festival in a given year.

## 7.2 Primary Key

```
festival_calendar_date_pk UUID PRIMARY KEY
```

## 7.3 Parent Relationship

```
festival_calendar_date.festival_master_pk -> festival_master.festival_master_pk
```

## 7.4 Logical Business Attributes

```
Festival (FK)
Calendar Year          (Gregorian year the observance falls in)
Observed Date          (the authoritative civil date)
Is Confirmed           (Kendra Sangha confirmed vs provisional/projected)
Source Reference       (almanac / circular / minute reference)
Remarks
Active State
```

## 7.5 Key Design Points

- `UNIQUE (festival_master_pk, calendar_year)` — one authoritative date per
  festival per year. This is the constraint that makes the table a *source of
  truth* rather than a log.
- `CHECK (EXTRACT(YEAR FROM observed_date) = calendar_year)` — keeps the
  denormalised `calendar_year` honest. `calendar_year` is stored (not derived
  at query time) because every rule queries *by year*, and a stored integer
  indexes cleanly. **Edge case flagged:** this CHECK is only valid for
  festivals that cannot straddle 1 January. Dola Purnima (late Feb–March) is
  safe. See OPEN-FC-04.
- `is_confirmed` separates a **projected** future date (so the UI can show
  next year's likely renewal deadline) from a **Kendra-Sangha-confirmed** one.
  Business rules that create legally significant records must require
  `is_confirmed = TRUE`; read-only forecasting may use projected rows. This
  distinction is the reason not to simply trust any row present.
- No `valid_from`/`valid_to` effective-dating. The table *is* the calendar; a
  corrected date is an UPDATE, and the existing audit trigger
  (SOL-AUDIT-004) already captures the before/after on every UPDATE. Adding
  bitemporal columns here would duplicate the audit log.

---

# 8. Proposed DDL

Conforms to existing Foundation DDL conventions: `nss.` prefix, UUID PK with
`gen_random_uuid()`, `created_at`/`updated_at`/`deleted_at`/`is_active` audit
block, soft-delete CHECK, `IF NOT EXISTS` idempotency.

```sql
-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 16_festival_master.sql
-- Table: festival_master
-- Depth: 0 (Root — no FK dependencies)
-- Version: 1.0
-- Authority: SOL-ARCH-013, SOL-FND-004
-- Owner: NSS_ERP_ADMIN
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.festival_master
(
    festival_master_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    festival_code VARCHAR(50) NOT NULL,

    festival_name VARCHAR(150) NOT NULL,

    festival_name_odia VARCHAR(150) NULL,

    -- Descriptive only (e.g. 'Phalguna Purnima'). Documents why the
    -- Gregorian date shifts. NOTHING PARSES THIS — the observed date is
    -- always authoritative data, never computed (SOL-ARCH-013 §3).
    lunar_basis VARCHAR(100) NULL,

    -- TRUE when a business rule keys off this festival's date
    -- (Dola Purnima: MBR-011A, MBR-029, renewal deadline).
    is_erp_reference_date BOOLEAN NOT NULL
        DEFAULT FALSE,

    description TEXT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT uq_festival_master_code
        UNIQUE (festival_code),

    CONSTRAINT uq_festival_master_name
        UNIQUE (festival_name),

    CONSTRAINT chk_festival_master_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_festival_master_code
    ON nss.festival_master (festival_code);

CREATE INDEX IF NOT EXISTS idx_festival_master_active
    ON nss.festival_master (is_active);
```

```sql
-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 17_festival_calendar_date.sql
-- Table: festival_calendar_date
-- Depth: 1 (depends on festival_master)
-- Version: 1.0
-- Authority: SOL-ARCH-013, SOL-FND-004
-- Owner: NSS_ERP_ADMIN
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.festival_calendar_date
(
    festival_calendar_date_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    festival_master_pk UUID NOT NULL,

    calendar_year INTEGER NOT NULL,

    -- The authoritative observed civil date for this festival/year.
    observed_date DATE NOT NULL,

    -- FALSE = provisional/projected (safe for display and forecasting only).
    -- TRUE  = confirmed by the Kendra Sangha; required before any rule may
    --         create a legally significant record keyed to this date.
    is_confirmed BOOLEAN NOT NULL
        DEFAULT FALSE,

    -- Provenance: almanac, Kendra Sangha circular, or meeting-minute ref.
    source_reference VARCHAR(200) NULL,

    remarks TEXT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_festival_calendar_date_festival
        FOREIGN KEY (festival_master_pk)
        REFERENCES nss.festival_master (festival_master_pk),

    -- One authoritative date per festival per year.
    CONSTRAINT uq_festival_calendar_date_festival_year
        UNIQUE (festival_master_pk, calendar_year),

    CONSTRAINT chk_festival_calendar_date_year_range
        CHECK (calendar_year BETWEEN 1900 AND 2200),

    -- Keeps the stored calendar_year consistent with observed_date.
    -- Valid only for festivals that cannot straddle 1 January — true for
    -- Dola Purnima (late Feb–March). See SOL-ARCH-013 OPEN-FC-04.
    CONSTRAINT chk_festival_calendar_date_year_matches
        CHECK (EXTRACT(YEAR FROM observed_date) = calendar_year),

    CONSTRAINT chk_festival_calendar_date_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_festival_calendar_date_festival
    ON nss.festival_calendar_date (festival_master_pk);

CREATE INDEX IF NOT EXISTS idx_festival_calendar_date_year
    ON nss.festival_calendar_date (calendar_year);

-- Supports "next reference date on or after X" — the dominant query
-- shape for MBR-011A / MBR-029 / renewal-deadline resolution.
CREATE INDEX IF NOT EXISTS idx_festival_calendar_date_observed
    ON nss.festival_calendar_date (observed_date);
```

---

# 9. Seed Data Strategy

Proposed `database/seed/01_foundation/10_festival_calendar.sql`:

1. One `festival_master` row:
   `DOLA_PURNIMA` / "Dola Purnima" / `ଦୋଳ ପୂର୍ଣ୍ଣିମା` /
   `lunar_basis = 'Phalguna Purnima'` / `is_erp_reference_date = TRUE`.
2. `festival_calendar_date` rows for the years the ERP must operate over.

**The dates themselves are an input I do not have and will not invent.**
Seeding requires the Kendra-Sangha-confirmed observance date per year. One
anchor already exists in the repository: `2025-03-14`, recorded as "Dola
Purnima 2025" in the seeded transfer-history remarks. Every other year must be
supplied before seeding — I will not populate projected dates and mark them
confirmed.

Recommended coverage: a backfill range covering existing historical membership
records, plus forward years. Rows for unconfirmed future years may be seeded
with `is_confirmed = FALSE` so the UI can forecast without any rule treating
them as authoritative.

Idempotency follows the existing seed convention (`ON CONFLICT DO NOTHING`
against the natural key `(festival_master_pk, calendar_year)`).

---

# 10. Ownership and Module Boundary

**Proposed owner: Foundation** (one-owner-per-table).

| Criterion | Assessment |
|---|---|
| Consumed by more than one module? | Yes — Membership (3 rules); prospectively Programmes & Events, UPBS, Finance year-end |
| Is it reference data? | Yes — stable, administered, non-transactional |
| Is it a business transaction? | No — satisfies SOL-FND-004 §35 "No Generic Transaction Model" |
| Dependency direction | Foundation is Depth 0/1; every consuming module already depends on Foundation. No inversion. |

**Boundary statement — a reference date is not an Event.** `festival_master`
must not acquire venue, organiser, registration, budget, attendance, or
programme columns. If NSS runs a *programme* on Dola Purnima, that programme
is an Events/UPBS row which may **reference** `festival_master` by FK; the
festival row itself stays a date reference. This keeps the Membership renewal
deadline from depending on the Events module.

SOL-FND-004 updates required on approval: §3 Table Inventory (12 → 14),
§32 Table-Level Ownership, §40 Foundation Table Count, and §1's table list.

---

# 11. Build Integration

`database/ddl/01_foundation/15_audit_trigger.sql` attaches audit triggers by
enumerating `pg_tables` at execution time, and `02_build.sh` runs it **last**
(line ~345), after all phases. New tables are therefore picked up
automatically — **provided they are created before that final step**, which
they are.

However, the build uses an **explicit file array**, not a glob:

- `database/scripts/02_build.sh` — add to the `FOUNDATION_DDL` array
  (currently 12 entries) and `FOUNDATION_SEED` array; update the
  "Phase 1 Foundation — DDL (12 tables)" label and its comment.
- `database/scripts/02_build.ps1` — same change, kept in step.

Per the standing DDL-only rule: these are new CREATE files and seed files,
rebuilt from scratch. No migration script.

---

# 12. Resolver Contract (API)

A single shared resolver in `api/helpers.py`, so no router re-implements date
resolution — same single-gatekeeper discipline as
`issue_membership_credential()`:

```python
def festival_date_for_year(cur, festival_code, calendar_year,
                           require_confirmed=True) -> date | None
    """Authoritative observed date, or None if not on file."""

def next_festival_date_on_or_after(cur, festival_code, as_of,
                                   require_confirmed=True) -> date | None
    """Next occurrence on/after as_of — the MBR-011A / MBR-029 primitive."""
```

**Missing-data behaviour is a deliberate design point.** When the required
year is absent, the resolver returns `None` and the caller raises a clear
`422` ("Dola Purnima for 2028 is not recorded; an administrator must add it
before Regular enrollment can be processed"). It must **never** fall back to a
guessed date. A loud, actionable failure is correct here; a silently wrong
membership conversion date is not.

---

# 13. Rule Impacts on Approval

| Rule | Becomes enforceable as |
|---|---|
| MBR-011A | Regular conversion date = `next_festival_date_on_or_after('DOLA_PURNIMA', eligibility_date)`, where eligibility_date = joining_date + 1 year (MBR-011). MBR-015 Direct Regular Enrollment stays exempt. |
| MBR-029 | Transfer effective date = next confirmed Dola Purnima on/after approval date, instead of free-text remarks. |
| Renewal deadline | Membership-year close becomes a queryable date, enabling the "due before Dola Purnima" dashboard counts that mockups currently hard-code. |

These are **documentation-level consequences only** in this proposal. Each
requires its own business-rule revision and API change after approval, in the
standing order.

---

# 14. OPEN ITEMS

## FC-DECISION-01 — Credential Validity: FY for Numbering, Dola Purnima for Validity — RESOLVED (2026-10-01)

**Decision (ERP-FROZEN):** NSS confirmed Option 1 of the former OPEN-FC-01.

- **Document numbering and finance stay on the Indian Financial Year
  (1 April – 31 March)** — `financial_year_bounds()` and MBR-030A's
  `<seq>/<fy>/<fy+1>` numbering are UNCHANGED. This is an accounting
  convenience, not a membership-year boundary, and finance reporting
  continues to key off FY throughout.
- **Validity (`valid_from`/`valid_to`) for Parichaya Patra, Anumati Patra,
  AND Gruhasana (`PARIBARIK_ASANA`) moves to the Dola Purnima membership
  year** — i.e. `valid_from` = the Dola Purnima that starts the membership
  year, `valid_to` = the eve of the next Dola Purnima. This replaces the FY
  window `issue_membership_credential()` currently assigns to
  `valid_from`/`valid_to` for both credential types.
- **Gruhasana explicitly included.** Per ORG-BR-094 (Addendum,
  2026-09-26), a `PARIBARIK_ASANA` organization's lifecycle already tracks
  its attached `sangha_sevi`'s Parichaya Patra lifecycle — it has no
  independent validity window today. This decision confirms that when
  Gruhasana validity is modelled, it inherits the same Dola-Purnima-year
  boundary as the Parichaya Patra it rides on, not FY. No separate
  `valid_from`/`valid_to` resolution is needed for `PARIBARIK_ASANA` — it is
  derived from the member's Parichaya Patra window, consistent with ORG-BR-094
  treating Gruhasana status as a follower, not an independent record.

**Consequence for this document's design:** `festival_calendar_date` is now
confirmed as a hard dependency of `issue_membership_credential()` for BOTH
credential types — not merely a future enhancement. On approval, that
function's `valid_from`/`valid_to` assignment changes from
`financial_year_bounds(issue_date)` to
`next_festival_date_on_or_after('DOLA_PURNIMA', issue_date)` (window start)
and the following year's occurrence (window end), using the section 12
resolver. `financial_year_bounds()` itself is UNCHANGED and continues to govern
`document_number` only.

**Follow-on documentation required on approval (not done by this document):**
MBR-030A (clarify numbering is FY-scoped, validity is not), MBR-014/MBR-010
(Parichaya/Anumati Patra validity definition), ORG-BR-094 (cross-reference
this decision for Gruhasana), and `07_member_profile.html`'s mockup becomes
the correct target shape rather than a guess.

## FC-DECISION-02 — Seed Date Set — RESOLVED (2026-10-01)

Public panchang/Odisha-calendar sources were checked (web search, external —
not an internal NSS record) and cross-verified against the one date already
anchored in the repository (`2025-03-14`, from the seeded
`membership_transfer_history` remarks — confirmed, matches independently).

| Calendar Year | Observed Date | `is_confirmed` | Note |
|---|---|---|---|
| 2024 | 2024-03-25 (Mon) | TRUE | Consistent across sources |
| 2025 | 2025-03-14 (Fri) | TRUE | Matches the pre-existing repo anchor exactly |
| 2026 | 2026-03-03 (Tue) | TRUE | Consistent across sources |
| 2027 | 2027-03-22 (Mon) | TRUE | Initially seeded provisional — sources disagreed between 21 and 22 March because the Purnima tithi straddles both days. **Confirmed 2026-10-01 by project decision as 22 March 2027.** |
| 2028 | 2028-03-11 (Sat) | TRUE | Consistent across sources |

**This does not change the core design principle (§3): the Kendra Sangha's
declared observance is still authoritative over any panchang.** These rows
are seeded as the best available public-source approximation, each carrying
`source_reference = 'Public panchang/Odisha calendar cross-reference, seeded 2026-10-01 — pending Kendra Sangha confirmation'`
(2027's `source_reference` was updated on confirmation — see §9.1 seed file)
so that administrator correction is expected and unsurprising, not a quiet
override of institutional data. 2025 is the only year with independent
in-repo corroboration; 2027 was confirmed 2026-10-01 by project decision as
22 March 2027 (`is_confirmed = TRUE`). The Kendra Sangha should still review
and confirm/correct the remaining years (2024, 2026, 2028) before any of
this range governs a live Regular conversion, transfer, or renewal.

Years before 2024 and after 2028 are left unseeded — add them the same way
once needed; this is ordinary data entry, not a schema change.

## OPEN-FC-03 — Who may maintain the calendar — RESOLVED (2026-10-01)

**Decision:** `NSS_ERP_ADMIN` (NSS-wide) only — not Kendra/Anchalika/Zilla/
Sakha admins, and not the existing `FOUNDATION_MANAGE` permission, which is
already granted to `NSS_ERP_KENDRA_ADMIN` too (see
`database/seed/00_bootstrap/03_role_permission.sql`) and would over-grant.

A new permission, **`FOUNDATION_CALENDAR_MANAGE`**, is added to
`permission_master` (category `FOUNDATION`) and granted only to
`NSS_ERP_ADMIN` in `role_permission`. Rationale: Dola Purnima is a single
NSS-wide fact — unlike most Foundation reference data (geography, master
values), a wrong or disputed entry here directly misdates a Regular
conversion or transfer across every Sakha, so it does not get the same
multi-tier admin delegation as the rest of Foundation. `FOUNDATION_VIEW`
(already NSS-wide-readable) continues to cover read access for all admin
tiers.

## OPEN-FC-04 — Year-straddle CHECK

`chk_festival_calendar_date_year_matches` assumes no festival crosses
1 January. Correct for Dola Purnima. If a future festival can fall in late
December or early January under a different year's observance, the constraint
must be dropped and `calendar_year` redefined as the *observance year*
rather than the Gregorian year of the date.

## OPEN-FC-05 — Table Naming — RESOLVED (2026-10-01)

**Decision: keep `festival_master` / `festival_calendar_date`** (reject the
neutral `reference_calendar_*` alternative), for three reasons:

1. **No second concrete use case exists today.** Fiscal year-end is already
   computed (`financial_year_bounds()`), not looked up — it needs no table.
   A Kendra anniversary date is speculative. Generalising a name for a
   capability nobody has asked for yet is the same mistake as the generic
   event-registration framework your UPBS decision already rejected: don't
   force a specific concept into a generic shape before a second real
   consumer exists.
2. **`festival_master.lunar_basis` and `is_erp_reference_date` are
   festival-shaped, not generic-calendar-shaped.** A `reference_calendar_*`
   name would still carry the same festival-specific columns, so renaming the
   table buys no actual generality — it would just make the table's purpose
   less obvious at the one site that reads it today.
3. **Renaming later is cheap; the opposite isn't.** If NSS later needs a
   genuinely generic reference-date mechanism, that is a new, separate
   decision made when the second use case is concrete — most likely a new
   table, not a rename of this one, since by then `festival_master` may have
   festival-specific columns a generic table shouldn't carry. Nothing here
   blocks that future design.

If a second non-festival reference date becomes a real requirement, open a
new architecture note rather than retrofitting this table — do not pre-decide
its shape now.

---

# 15. Rule Classification

| Item | Tier |
|---|---|
| Dola Purnima governs Regular conversion, transfer effect, renewal deadline | **CONSTITUTIONAL** — Bye-Law-derived and approved-workflow-derived |
| Observance dates are authoritative data, never computed (§3) | **ERP-FROZEN** (on approval of this document) |
| Two-table master + per-year design, Foundation-owned | **ERP-FROZEN** (on approval of this document) |
| FC-DECISION-01 — FY for numbering/finance, Dola Purnima for Parichaya/Anumati Patra + Gruhasana validity | **ERP-FROZEN** (2026-10-01) |
| FC-DECISION-02 — seed date set (2024–2028) | **ERP-FROZEN** (2026-10-01) |
| OPEN-FC-03 — FOUNDATION_CALENDAR_MANAGE granted to NSS_ERP_ADMIN only | **ERP-FROZEN** (2026-10-01) |
| OPEN-FC-05 — table naming kept as `festival_master`/`festival_calendar_date` | **ERP-FROZEN** (2026-10-01) |
| OPEN-FC-04 | **PENDING** (not currently blocking — Dola Purnima does not straddle 1 January) |

---

# 16. Approval Gate

Nothing is created until this document is approved. On approval, in the
standing order (Business Rules → Documentation → Database → API → UI → Tests
→ Freeze):

1. **Documentation** — ✅ DONE (2026-10-01). Updated SOL-FND-004 (§3 Table
   Inventory, §32 Table-Level Ownership, §40 Foundation Table Count — 12→14
   tables); replaced MBR-011A's `ARCHITECTURAL NOTE (OPEN)` with a settled
   reference to this document; applied FC-DECISION-01's follow-on
   cross-references to MBR-010, MBR-014, MBR-030A, and ORG-BR-094.
2. **Database** — ✅ DONE (2026-10-01). Created `16_festival_master.sql`,
   `17_festival_calendar_date.sql`, and
   `seed/01_foundation/10_festival_calendar.sql` (verified against the live
   `01_foundation/` directory — `09` was already taken by
   `09_sakha_postal_codes.sql`); updated both `02_build.sh` and
   `02_build.ps1` (DDL added to Phase 1, seed added to Phase 2 — placed
   there, not after Phase 14, so the Phase 14 audit trigger still attaches
   to the new tables); added `FOUNDATION_CALENDAR_MANAGE` permission
   (NSS_ERP_ADMIN only — OPEN-FC-03) to the bootstrap seed files. Not yet
   rebuilt from scratch against a live database in this session.
3. **API** — ✅ DONE (2026-10-01). Added `festival_date_for_year()`,
   `next_festival_date_on_or_after()`, and
   `dola_purnima_credential_validity_window()` to `api/helpers.py`;
   decoupled `next_credential_document_number()` to return only
   `document_number` (financial-year numbering, unchanged); updated
   `issue_membership_credential()`'s both branches (legacy-document-number
   and auto-generate) to default `valid_from`/`valid_to` from the Dola
   Purnima window instead of `financial_year_bounds()`. Compile-checked
   clean (`python3 -m py_compile`).
4. **Tests** — IN PROGRESS. Resolver unit tests (hit, miss,
   unconfirmed-excluded, next-on-or-after boundary where `as_of` equals the
   festival date), DB constraint tests (duplicate festival/year rejected,
   year-mismatch rejected), and credential-issuance tests asserting
   `valid_from`/`valid_to` now land on Dola Purnima dates while
   `document_number` still reflects FY — per the comprehensive-coverage
   standard.

**All design decisions required for implementation are now resolved**
(FC-DECISION-01, FC-DECISION-02, OPEN-FC-03, OPEN-FC-05). OPEN-FC-04
remains PENDING but does not block Dola Purnima, the only festival in scope
today. Implementation proceeds per steps 1–4 above.

---

# End of Document
