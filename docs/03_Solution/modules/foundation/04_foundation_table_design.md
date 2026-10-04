# NSS ERP — Foundation Table Design

**Document ID:** SOL-FND-004
**Version:** 1.2.0
**Status:** DRAFT — SOURCE ALIGNED
**Module:** Foundation
**Parent System:** Nilachala Saraswata Sangha ERP

---

# 1. Purpose

This document defines the database table-design baseline for the Foundation
Module.

The Foundation Module provides:

- Generic Master Data
- System Settings
- Identifier Sequence Infrastructure
- Geographic Reference Data

The current frozen Foundation schema contains exactly eight original tables,
two shared-infrastructure tables added by architectural decisions, two
PIN code geographic tables added by the SOL-ARCH-010 amendment (one of them
reinstated by the 2026-10-03 Member-Assisted Geographic Entry amendment),
and two festival reference-calendar tables added by the SOL-ARCH-013
amendment:

    master_category
    master_data
    system_setting
    id_sequence_master
    country
    state
    district
    city_village
    document_master                (DOC-ARCH-001 — shared document registry)
    field_change_log               (Data Change Architecture — shared change log)
    postal_code                    (Simplified Geography Model, 2026-10-02)
    post_office                    (reinstated — SOL-ARCH-010 Amendment, 2026-10-03)
    festival_master                (SOL-ARCH-013 — festival identity reference)
    festival_calendar_date         (SOL-ARCH-013 — per-year authoritative observed date)

---

# 2. Source Boundary

The PostgreSQL schema review explicitly identifies the original eight tables
as the Foundation Module.

Two additional shared-infrastructure tables have been assigned to Foundation
by architectural decisions during the pre-DB gate:

- `document_master` — DOC-ARCH-001 (moved from Person; shared document registry)
- `field_change_log` — Data Change Architecture (shared field-change tracking)

The database build plan identifies the implementation sequence as:

    03_master_tables.sql
    04_system_setting.sql
    05_id_sequence_master.sql
    06_geo_tables.sql

---

# 3. Table Inventory

| # | Table | Purpose |
|---:|---|---|
| 1 | `master_category` | Generic master-data category |
| 2 | `master_data` | Generic reusable master values |
| 3 | `system_setting` | Central system configuration |
| 4 | `id_sequence_master` | Business identifier sequence infrastructure |
| 5 | `country` | Geographic country master |
| 6 | `state` | State/province master |
| 7 | `district` | District master |
| 8 | `city_village` | City/village/locality master |
| 9 | `document_master` | Shared document registry (DOC-ARCH-001, moved from Person) |
| 10 | `field_change_log` | Shared field-change tracking (Data Change Architecture) |
| 11 | `postal_code` | PIN code / postal code master (Simplified Geography Model — unique on PIN alone, direct `state_pk`) |
| 12 | `post_office` | Post office master under a PIN code (reinstated 2026-10-03, SOL-ARCH-010 Amendment) |
| 13 | `festival_master` | Festival identity master (e.g. Dola Purnima) — SOL-ARCH-013 |
| 14 | `festival_calendar_date` | Per-year authoritative observed date for a festival — SOL-ARCH-013 |

---

# 4. Common Database Standards

All Foundation tables shall follow the project-wide database standards
where applicable.

## 4.1 Technical Primary Key

The project standard uses:

    <table_name>_pk

Examples:

    master_category_pk
    master_data_pk
    system_setting_pk
    id_sequence_master_pk
    country_pk
    state_pk
    district_pk
    city_village_pk

---

## 4.2 Primary Key Type

The project database architecture uses UUID technical primary keys.

Therefore the Foundation tables shall use UUID-based technical PKs.

---

## 4.3 Business Identifier

Where a Foundation entity requires a human/business identifier, it shall be
separate from the technical PK.

Example:

    country_pk
    country_code

The technical PK remains the relational identifier.

---

# 5. Audit Metadata

The project database standard identifies the following audit/lifecycle
fields for applicable tables:

    created_at
    created_by_sangha_sevi_pk

    updated_at
    updated_by_sangha_sevi_pk

    deleted_at
    deleted_by_sangha_sevi_pk

    is_active

Applicability to each Foundation reference table shall be finalized based on
its lifecycle.

---

# 6. `master_category`

## 6.1 Purpose

Defines a logical category for generic master values.

Relationship:

    master_category
          1
          │
          N
          ▼
    master_data

---

## 6.2 Primary Key

Required:

    master_category_pk UUID PRIMARY KEY

---

## 6.3 Logical Business Attributes

The table requires a stable representation of:

    Category Code
    Category Name
    Description
    Active State

The exact physical column names and lengths are subject to final SQL
approval.

---

## 6.4 Category Code

A category code should provide a stable machine-readable identifier.

Examples from the approved database planning include:

    GENDER
    RELATIONSHIP_TYPE
    MEMBERSHIP_TYPE
    MEMBERSHIP_STATUS
    LOGIN_ROLE
    STATUS_REASON
    WORKFLOW_STATUS
    DOCUMENT_TYPE
    APPLICATION_TYPE

---

## 6.5 Category Uniqueness

Category codes shall be unique.

No two active categories shall represent the same category code.

---

## 6.6 Category Lifecycle

A category that has already been used by business data should not be
physically deleted merely because it is no longer used for new records.

---

# 7. `master_data`

## 7.1 Purpose

Stores reusable values belonging to a master category.

Relationship:

    master_category
          1
          │
          N
          ▼
    master_data

---

## 7.2 Primary Key

Required:

    master_data_pk UUID PRIMARY KEY

---

## 7.3 Foreign Key

Required logical relationship:

    master_data.master_category_pk
              ↓
    master_category.master_category_pk

---

## 7.4 Logical Business Attributes

The table requires a stable representation of:

    Master Category
    Value Code
    Value / Display Name
    Description
    Module Scope (applicable_modules)
    Ordering / Display Sequence
    Active State

The exact physical column catalogue remains subject to final SQL approval.

---

## 7.4a Module-Scoped Status Filtering (`applicable_modules`)

The `applicable_modules` column (`TEXT[] NULL`) enables shared categories
(e.g. STATUS) to be filtered per-module. Each value is tagged with the
modules it applies to:

    NULL                               — applies to all modules (default for
                                         single-module categories like GENDER,
                                         BLOOD_GROUP)
    '{ORGANIZATION}'                   — Organization only
    '{ORGANIZATION,MEMBERSHIP}'        — Organization and Membership
    '{ORGANIZATION,MEMBERSHIP,PERSON}' — all three core modules

API filters use: `WHERE '<MODULE>' = ANY(md.applicable_modules)`.

Current unified STATUS distribution (16 values total):

| Module       | Count | Statuses |
|-------------|------:|----------|
| Organization | 7 | PROPOSED, APPROVED, ACTIVE, INACTIVE, SUSPENDED, DISSOLVED, ARCHIVED |
| Membership   | 12 | ACTIVE, INACTIVE, SUSPENDED, LAPSED, TRANSFERRED, RESIGNED, EXPELLED, ARCHIVED, EXPIRED, RENEWAL_PENDING, ON_HOLD, DISCIPLINARY_REVIEW |
| Person       | 4 | ACTIVE, INACTIVE, DECEASED, ARCHIVED |

EXPIRED is tagged `{MEMBERSHIP}` — it fires when a Parichaya Patra/Anumati Patra lapses from
non-renewal, which is a membership-lifecycle event, not a document-only concern. (An earlier
revision tagged it `{CREDENTIAL}`; that undersold the relationship and has been corrected.)
Note `parichaya_patra.status`/`anumati_patra.status` are each their own inline `VARCHAR` +
`CHECK` column, not an FK into `master_data` — so this STATUS row is a reference/lookup value,
not literally what those two tables store.

---

## 7.5 Value Code

Where a master category uses codes, each code shall be stable within that
category.

---

## 7.6 Value Uniqueness

The logical uniqueness requirement is:

    master_category + value_code

A duplicate value code within the same category shall not be permitted.

---

## 7.7 Category Dependency

A master value cannot exist without a valid master category.

---

## 7.8 Inactive Values

An inactive master value shall not normally be selectable for new business
transactions.

Historical records may continue to reference it.

---

# 8. Master Data Design Example

Conceptually:

```text
master_category
----------------
GENDER
   │
   ├── MALE
   ├── FEMALE
   └── OTHER
```

The exact approved master catalogue is maintained separately.

This document defines the table mechanism, not the complete business-value
catalogue.

---

# 9. Generic Master Boundary

The generic master mechanism must not become a dumping ground for every
possible application constant.

The owning business module determines whether a value should be:

```
Generic Master
Domain Master
Configuration
Database Constraint
Application Constant
```

---

# 10. `system_setting`

## 10.1 Purpose

Stores centrally managed configurable system settings.

The source identifies examples including:

```
PASSWORD_EXPIRY_DAYS
MAX_LOGIN_ATTEMPTS
CURRENT_MEMBERSHIP_YEAR
DEFAULT_COUNTRY
```

These examples demonstrate the intended concept; they are not a final
mandatory seed catalogue.

---

## 10.2 Primary Key

Required:

```
system_setting_pk UUID PRIMARY KEY
```

---

## 10.3 Logical Business Attributes

The table requires a stable representation of:

```
Setting Key
Setting Value
Description
Data Type / Interpretation
Active State
```

The exact physical value representation is not frozen by the current source.

---

## 10.4 Setting Key

A system-setting key shall be unique.

Example:

```
CURRENT_MEMBERSHIP_YEAR
```

shall identify one logical setting.

---

## 10.5 Setting Value

The current source does not freeze whether the value is represented as:

```
VARCHAR
JSON
Separate typed columns
```

Therefore the final physical representation remains pending.

---

## 10.6 Configuration Security

Sensitive configuration values shall not be exposed through ordinary
public/member-facing APIs.

---

## 10.7 Configuration Audit

Important setting changes shall remain auditable through the common Audit
framework.

---

## 10.8 Configuration Lifecycle

A setting may become inactive where the setting is no longer applicable.

Historical configuration changes must remain traceable where required.

---

# 11. `id_sequence_master`

## 11.1 Purpose

Provides centralized sequence infrastructure for business identifiers.

The source explicitly includes this table in Foundation.

---

## 11.2 Primary Key

Required:

```
id_sequence_master_pk UUID PRIMARY KEY
```

---

## 11.3 Logical Business Attributes

The sequence configuration requires a representation of concepts such as:

```
Sequence Name / Code
Current / Next Sequence State
Prefix
Padding / Number Format
Active State
```

The exact physical columns are not completely frozen by the source.

---

## 11.4 Sequence Ownership

Each business identifier sequence shall have one authoritative sequence
definition.

---

## 11.5 Sequence Scope

A sequence definition shall correspond to one defined business identifier
space.

---

## 11.6 Sequence Uniqueness

The sequence identifier/code shall be unique.

---

## 11.7 Permanent IDs

Where an owning business module declares an identifier permanent, sequence
configuration shall not allow accidental reuse of retired identifiers.

---

## 11.8 Concurrent Generation

The final PostgreSQL implementation must guarantee safe concurrent identifier
generation.

The exact mechanism is an implementation/DDL decision.

---

## 11.9 Manual Reset

No unrestricted manual reset of a production business sequence shall be
permitted.

Any approved reset procedure must preserve identifier uniqueness and
historical integrity.

---

# 12. Business ID Ownership

`id_sequence_master` provides sequence infrastructure.

It does not determine the business meaning of an identifier.

For example:

```
Person → owns Person ID rules
Membership → owns Sangha Sevi ID rules
```

Foundation provides the common sequence mechanism where required.

---

# 13. `country`

## 13.1 Purpose

Provides the common country reference master.

---

## 13.2 Primary Key

Required:

```
country_pk UUID PRIMARY KEY
```

---

## 13.3 Logical Business Attributes

The country table requires a representation of:

```
Country Code
Country Name
Active State
```

The exact physical column definition follows the final location-master
design.

---

## 13.4 Country Code

The project has previously established ISO-oriented country-code usage.

The code shall be stable.

---

## 13.5 Country Uniqueness

Country codes shall be unique.

Country names should not be duplicated where they represent the same
country.

---

# 14. `state`

## 14.1 Purpose

Provides state/province geographic reference data.

---

## 14.2 Primary Key

Required:

```
state_pk UUID PRIMARY KEY
```

---

## 14.3 Parent Relationship

Required logical relationship:

```
state
  ↓
country
```

Conceptually:

```
country_pk
    ↑
state.country_pk
```

---

## 14.4 Logical Business Attributes

The table requires:

```
State/Province Code
State/Province Name
Country
Active State
```

Exact physical column names remain subject to final SQL approval.

---

## 14.5 State Uniqueness

A state/province code should be unique within its country.

Logical uniqueness:

```
country + state_code
```

---

# 15. `district`

## 15.1 Purpose

Provides district-level geographic reference data.

---

## 15.2 Primary Key

Required:

```
district_pk UUID PRIMARY KEY
```

---

## 15.3 Parent Relationship

Required logical relationship:

```
district
    ↓
state
```

Conceptually:

```
state_pk
   ↑
district.state_pk
```

---

## 15.4 Logical Business Attributes

The table requires:

```
District Code
District Name
State
Active State
```

> **Amendment (2026-10-03):** `district` is a **writable** geographic level
> (FND-BR-085). It additionally carries the shared member-assisted-entry
> columns defined in §16.8: `entry_status`, `reviewed_by_sangha_sevi_pk`,
> `reviewed_at`, `admin_remarks`, `corrected_into_district_pk`.

Exact physical columns remain subject to final SQL approval.

---

## 15.5 District Uniqueness

A district code should be unique within its state, among **approved, active**
rows only (partial unique index — see §16.8). A PENDING district proposal is
not held to this uniqueness so a member's save never fails on a collision
with the canonical row it may turn out to duplicate.

Logical uniqueness:

```
state + district_code      (WHERE entry_status = 'APPROVED')
state + district_name      (WHERE entry_status = 'APPROVED')
```

---

# 16. `city_village`

## 16.1 Purpose

Provides city/village/locality reference data.

---

## 16.2 Primary Key

Required:

```
city_village_pk UUID PRIMARY KEY
```

---

## 16.3 Parent Relationship

**As actually implemented (`11_city_village.sql`, SOL-ARCH-010 Amendment
2026-10-01 — supersedes the single-parent model below):**

```
city_village.district_pk    → district.district_pk     (NULLABLE — best-effort
                                                           name match; India's
                                                           census/post
                                                           romanizations drift
                                                           at district level)

city_village.postal_code_pk → postal_code.postal_code_pk (NULLABLE — primary
                                                           location anchor:
                                                           village → PIN →
                                                           state)
```

A village is reached primarily through its PIN code; `district_pk` is
best-effort and may be absent. There is no M:N mapping table — the formerly
documented `city_village_postal_code_map` junction (§39 of the original
design) was retired because villages are effectively 1:1 with a PIN (one
representative PIN is stored directly, same HO/PO/BO dedup rule as
`postal_code`).

---

## 16.4 Logical Business Attributes

The table requires:

```
City/Village Code
City/Village Name
District        (optional FK)
Postal Code      (optional FK — primary anchor)
Locality Type     (CITY | TOWN | VILLAGE)
Active State
```

> **Amendment (2026-10-03):** `city_village` is a **writable** geographic
> level (FND-BR-085). It additionally carries the shared member-assisted-entry
> columns defined in §16.8.

---

## 16.5 City/Village Uniqueness

As implemented, among **approved, active** rows only:

```
district_pk + city_village_code       (WHERE entry_status = 'APPROVED')
district_pk + city_village_name       (WHERE entry_status = 'APPROVED')
postal_code_pk + city_village_name    (WHERE entry_status = 'APPROVED')
```

---

## 16.6 `postal_code`

**Purpose.** PIN code / postal code master. One row per PIN nationally.

**As actually implemented (`12_postal_code.sql`, Simplified Geography Model
2026-10-02):**

```
postal_code_pk UUID PRIMARY KEY
state_pk        UUID NOT NULL  → state.state_pk
postal_code     VARCHAR(20) NOT NULL
```

`country_pk` and `post_office_name` were dropped from this table in the
2026-10-02 amendment — `country_pk` is redundant (reachable via
`state_pk → state.country_pk`), and office-level detail now lives in the
reinstated `post_office` table (§16.7) rather than as a column here.
`postal_code` has no `district_pk` of its own — PIN → District is not 1:1
(over 2,000 PINs legitimately span 2+ districts) — so district is reached
only through `city_village`.

**Uniqueness.** One **approved** row per PIN nationally:

```
postal_code    (WHERE entry_status = 'APPROVED')
```

> **Amendment (2026-10-03):** `postal_code` is a **writable** geographic
> level (FND-BR-085). It additionally carries the shared member-assisted-entry
> columns defined in §16.8.

---

## 16.7 `post_office` (reinstated 2026-10-03, SOL-ARCH-010 Amendment)

**Purpose.** Post office master. A PIN code may have multiple post offices
(Head Office, Sub Office, Branch Office).

**Status note.** `post_office` was retired under the 2026-10-02 Simplified
Geography Model and is reinstated here per the 2026-10-03 ERP-DESIGN decision
(FND-BR-089) to let members select and contribute post office names. This is
a deliberate, scoped reversal of that one retirement — the PIN-level and
village-level simplifications it was part of otherwise still stand.

**Table shape:**

```
post_office_pk   UUID PRIMARY KEY
postal_code_pk    UUID NOT NULL  → postal_code.postal_code_pk
post_office_name  VARCHAR(150) NOT NULL
display_order     INTEGER NOT NULL DEFAULT 0
created_at / updated_at / deleted_at / is_active   (standard audit)
```

plus the shared member-assisted-entry columns (§16.8).

**Uniqueness.** One **approved** office name per PIN code:

```
postal_code_pk + post_office_name    (WHERE entry_status = 'APPROVED')
```

---

## 16.8 Member-Assisted Geographic Entry — Shared Columns

Per FND-BR-086/087/088/090, the four writable geographic levels — `district`,
`postal_code`, `post_office`, `city_village` — each additionally carry:

```
entry_status                   VARCHAR(20) NOT NULL DEFAULT 'APPROVED'
                                CHECK (entry_status IN
                                    ('PENDING', 'APPROVED', 'CORRECTED'))

submitted_by_sangha_sevi_pk     UUID NULL   → sangha_sevi.sangha_sevi_pk
                                (who proposed this row; NULL for seeded data)

reviewed_by_sangha_sevi_pk      UUID NULL   → sangha_sevi.sangha_sevi_pk

reviewed_at                     TIMESTAMPTZ NULL

admin_remarks                   TEXT NULL

corrected_into_<table>_pk       UUID NULL   → self-FK to the canonical row
                                this entry was merged into when
                                entry_status = 'CORRECTED'
```

Seed-loaded rows (India Post data) are inserted with `entry_status =
'APPROVED'` and no submitter. A member-typed value is inserted with
`entry_status = 'PENDING'` and `submitted_by_sangha_sevi_pk` set to the
submitting member.

Resolution (FND-BR-087):

```
APPROVE  → entry_status = 'APPROVED', reviewed_by/_at/remarks set.
           Row now appears in the shared dropdown.

CORRECT  → entry_status = 'CORRECTED', reviewed_by/_at/remarks set,
           corrected_into_<table>_pk points at the canonical row.
           Every nss.person_address row referencing the CORRECTED row
           is re-pointed to the canonical row (API-level, not a DB
           cascade — mirrors how claim approval performs its
           side-effect creates in claim_approval.py).
```

Approval/correction authority (FND-BR-088): `FOUNDATION_MANAGE`, scoped to
the submitter's organization unless the actor holds NSS-WIDE scope
(Kendra-level / nssadmin).

---

# 17. Geographic Hierarchy

The final logical relationship is:

```text
country
   │
   └──< state
           │
           ├──< district
           │        │
           │        └──< city_village
           │
           └──< postal_code
                    │
                    ├──< post_office
                    │
                    └──< city_village   (direct anchor; district_pk
                                          on city_village is optional)
```

District, Postal Code, Post Office and City/Village additionally support
member-assisted entry under administrator approval (§16.8, FND-BR-085 —
FND-BR-090 in the business rules document).

---

# 18. Geographic Foreign Keys

The expected foreign keys are:

```text
state.country_pk
        →
country.country_pk

district.state_pk
        →
state.state_pk

city_village.district_pk           (NULLABLE, best-effort)
        →
district.district_pk

postal_code.state_pk
        →
state.state_pk

post_office.postal_code_pk
        →
postal_code.postal_code_pk

city_village.postal_code_pk        (NULLABLE, primary anchor)
        →
postal_code.postal_code_pk
```

---

# 19. Geographic Referential Integrity

A child geographic record shall not reference a nonexistent parent.

Examples:

```
State → valid Country
District → valid State
Postal Code → valid State
Post Office → valid Postal Code
City/Village → valid District (when present)
City/Village → valid Postal Code (when present)
```

---

# 20. Geographic Hierarchy Is Not Organization

The Foundation location hierarchy shall never be used as a replacement for
the Organization hierarchy.

Geography:

```
Country
State
District
Postal Code
Post Office
City/Village
```

Organization:

```
Kendra
Anchalika
Zilla
Sakha
```

These remain separate models.

---

# 21. Geographic Lifecycle

Geographic records that have been referenced by historical business data
should not be physically deleted merely to remove them from future
selection.

The final inactive/retired lifecycle must be defined in the location
implementation.

---

# 22. Audit Columns

Where applicable, Foundation tables should include the project-standard
audit metadata:

```
created_at
created_by_sangha_sevi_pk

updated_at
updated_by_sangha_sevi_pk

deleted_at
deleted_by_sangha_sevi_pk

is_active
```

The project source explicitly recommends these audit fields for major
tables.

---

# 23. Audit FK Consideration

Where:

```
created_by_sangha_sevi_pk
updated_by_sangha_sevi_pk
deleted_by_sangha_sevi_pk
```

are implemented as foreign keys, they must reference the authoritative
membership identity according to the final cross-module database
architecture.

The exact FK timing must avoid circular creation dependencies.

---

# 24. Soft Delete

Applicable Foundation reference records shall use the project soft-delete
principle.

Conceptually:

```
is_active = FALSE
deleted_at = timestamp
```

rather than uncontrolled physical deletion.

---

# 25. Historical Reference Preservation

If a historical record references a master/geographic value that becomes
inactive, the historical record must remain interpretable.

---

# 26. Foreign-Key Delete Behaviour

The final DDL shall explicitly define delete behaviour.

For shared reference data, cascading deletion must not destroy dependent
historical records.

The exact `ON DELETE` strategy is finalized in SQL implementation.

---

# 27. Indexing

The following logical access paths should be indexed:

```
master_data → master_category
state → country
district → state
city_village → district
```

Unique business codes should also receive appropriate indexes through their
unique constraints.

---

# 28. Search Support

Geographic names and commonly searched master values may require optimized
search indexes.

The project architecture includes PostgreSQL search-related extensions such
as:

```
pg_trgm
btree_gin
```

The exact indexes are implementation decisions.

---

# 29. Seed Data

The database build plan identifies initial generic master categories:

```
GENDER
RELATIONSHIP_TYPE
MEMBERSHIP_TYPE
MEMBERSHIP_STATUS
LOGIN_ROLE
STATUS_REASON
WORKFLOW_STATUS
DOCUMENT_TYPE
APPLICATION_TYPE
```

These constitute the source-supported seed candidates.

Additional seed data requires approval.

---

# 30. Country Seed Data

The project has previously established common country seed data including:

```
IN — India
US — United States
GB — United Kingdom
AU — Australia
CA — Canada
```

These seed values belong to the Foundation location master.

---

# 31. Master Category Seed Governance

Seed categories shall not be duplicated across modules.

If a category already exists in Foundation, consuming modules should use it
rather than create an equivalent category.

---

# 32. Table-Level Ownership

| Table                          | Foundation Responsibility          |
| ------------------------------ | ---------------------------------- |
| `master_category`              | Generic category mechanism         |
| `master_data`                  | Generic value mechanism            |
| `system_setting`               | Configuration storage              |
| `id_sequence_master`           | Identifier sequence infrastructure |
| `country`                      | Country reference                  |
| `state`                        | State/province reference           |
| `district`                     | District reference                 |
| `city_village`                 | Locality reference                 |
| `document_master`              | Shared document registry (DOC-ARCH-001) |
| `field_change_log`             | Shared field-change tracking       |
| `postal_code`                  | PIN code / postal code reference (Simplified Geography Model) |
| `post_office`                  | Post office reference under a PIN code (reinstated 2026-10-03) |
| `festival_master`              | Festival identity reference (SOL-ARCH-013) |
| `festival_calendar_date`       | Per-year authoritative observed festival date, admin-maintained only — NSS_ERP_ADMIN (SOL-ARCH-013) |

---

# 33. Tables Not Added

The Foundation table design does not introduce:

```
organization
person
family_group
user_account
role_master
permission_master
audit_master
notification
document_store
```

Those belong to other modules/capabilities.

---

# 34. No Duplicate Location Model

The following generic tables shall not be independently recreated in
business modules:

```
country
state
district
postal_code
post_office
city_village
```

---

# 35. No Generic Transaction Model

Foundation does not contain business transactions.

For example:

```
Membership Renewal
Attendance
Election
Publication Purchase
Sevak Assignment
```

remain outside Foundation.

---

# 36. Data-Type Boundary

The current source does not provide authoritative lengths for:

```
codes
names
descriptions
setting values
```

Therefore exact `VARCHAR(n)` lengths shall not be treated as frozen by this
document.

They must be finalized before DDL generation.

---

# 37. Required Finalization Before SQL

Before generating PostgreSQL DDL, the following remain to be explicitly
confirmed:

```
Exact column names
Exact VARCHAR lengths
Exact NULL/NOT NULL rules
Exact audit-column applicability
Exact setting value representation
Exact sequence implementation
Exact geographic code structure
Exact city/village type representation
Exact delete behaviour
Exact indexes
Exact seed-data catalogue
```

---

# 38. Database-First Rule

No SQL should be generated from assumptions that are not supported by the
Foundation design.

The correct sequence remains:

```
Business Rules
      ↓
ERD
      ↓
Table Design
      ↓
PostgreSQL DDL
```

---

# 39. Final Logical Schema

```text
MASTER DATA

master_category
      │
      └──< master_data


CONFIGURATION

system_setting


IDENTIFIER INFRASTRUCTURE

id_sequence_master


GEOGRAPHY

country
   │
   └──< state
           │
           ├──< district ─────────────────┐
           │                              │
           └──< postal_code ──< post_office
                    │                     │
                    └──────────< city_village
                           (district_pk and postal_code_pk both
                            nullable/best-effort on city_village)

district, postal_code, post_office and city_village additionally support
member-assisted entry (entry_status / review columns — §16.8).


SHARED INFRASTRUCTURE

document_master     (shared document registry — DOC-ARCH-001)
field_change_log    (shared field-change tracking — Data Change Architecture)


FESTIVAL REFERENCE CALENDAR (SOL-ARCH-013)

festival_master
      │
      └──< festival_calendar_date
```

---

# 40. Foundation Table Count

Current count:

```
15 tables
```

```text
1. master_category
2. master_data
3. system_setting
4. id_sequence_master
5. country
6. state
7. district
8. city_village
9. document_master              (DOC-ARCH-001)
10. field_change_log            (Data Change Architecture)
11. postal_code                 (Simplified Geography Model, 2026-10-02)
12. post_office                 (reinstated — SOL-ARCH-010 Amendment, 2026-10-03)
13. festival_master              (SOL-ARCH-013)
14. festival_calendar_date       (SOL-ARCH-013)
```

> **Note (2026-10-03):** the formerly-listed `city_village_postal_code_map`
> (M:N bridge table) is retired — see §16.3. `post_office` replaces it in
> the count. district, postal_code, post_office and city_village each gained
> the member-assisted-entry columns in §16.8 (no new table for that; shared
> columns on the four existing writable tables).

---

# 41. Source Alignment

The source database review identifies the original eight Foundation tables and
explicitly separates them from Person, Membership, Authentication,
Organization, Governance and other modules.

Two additional tables (`document_master`, `field_change_log`) were assigned
to Foundation by architectural decisions made during the pre-DB architecture
gate. Their logical column designs are defined by Person
(for `document_master`) and the Data Change Architecture (for
`field_change_log`); Foundation owns the physical DDL.

Two PIN code geographic tables (`postal_code`, `post_office`) were added by
the SOL-ARCH-010 amendment (Simplified Geography Model, 2026-10-02, and the
Member-Assisted Geographic Entry amendment, 2026-10-03). `postal_code` is a
state-scoped postal reference, unique on the PIN alone; `post_office` is a
writable child of `postal_code` (reinstated 2026-10-03 — see FND-BR-089).
The earlier `city_village_postal_code_map` M:N bridge table described in a
prior revision of this document is retired; `city_village` now anchors
directly to `postal_code` via a nullable `postal_code_pk` FK (§16.2).

The database build plan confirms:

```
master_category
master_data
```

as the generic master framework, provides system-setting examples, and
groups:

```
country
state
district
postal_code
post_office
city_village
```

as the geographic Foundation.

The project-wide database standards establish UUID technical PKs, the
`<table_name>_pk` naming convention, business-ID separation, audit metadata,
and soft-delete principles.

---

# 42. Status

DOCUMENT STATUS:

```
DRAFT — SOURCE ALIGNED
```

VERSION:

```
1.2.0
```

CHANGELOG:

```
1.2.0 (2026-10-03) — Member-Assisted Geographic Entry (SOL-ARCH-010 Amendment)
  - Rewrote §15.4/§15.5 (district) and §16 (city_village) to match the real
    DDL (nullable district_pk/postal_code_pk on city_village, no M:N map).
  - Added §16.6 (postal_code, Simplified Geography Model) and §16.7
    (post_office — reinstated, writable child of postal_code).
  - Added §16.8 (shared member-assisted entry columns: entry_status,
    submitted_by_sangha_sevi_pk, reviewed_by_sangha_sevi_pk, reviewed_at,
    admin_remarks, corrected_into_<table>_pk) applied to district,
    postal_code, post_office, city_village.
  - Rewrote §17 Geographic Hierarchy, §18/§19 Geographic FKs and
    Referential Integrity, §20 Geographic Hierarchy Is Not Organization,
    and §34 No Duplicate Location Model to reflect the above.
  - Rewrote §39 Final Logical Schema, §40 Foundation Table Count (14→15
    tables), and §41 Source Alignment to remove the retired
    `city_village_postal_code_map` and reflect `postal_code` + `post_office`.
1.1.0 — prior Simplified Geography Model revision (2026-10-02).
```

---
