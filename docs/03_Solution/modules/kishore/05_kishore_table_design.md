# NSS ERP — Kishore Puja Table Design

**Document ID:** SOL-KISH-005  
**Version:** 1.0.0  
**Status:** DRAFT — SOURCE ALIGNED  
**Module:** Kishore Puja  
**Parent System:** Nilachala Saraswata Sangha ERP

---

# 1. Purpose

This document defines the logical table design for the Kishore Puja module.

It translates the approved:

- Kishore Module Overview
- Kishore ERD
- Kishore Lifecycle
- Kishore Business Rules

into a structured relational table design.

This document does not generate SQL.

---

# 2. Design Principles

The Kishore table design follows the NSS ERP principles:

```text
Person ≠ Member

Kishore ≠ NSS Member

KH ID ≠ Sangha Sevi ID

Registration ≠ Attendance

History Never Deleted

Common Foundation First

Master Data Driven

Common Modules Own Their Domains
```

---

# 3. Kishore Domain Tables

The Kishore domain consists of four primary tables:

```text
kishore_participant

kishore_event

kishore_event_registration

kishore_membership_transition
```

This matches the frozen Kishore architecture.

---

# 4. Common Tables Used

Kishore integrates with existing common tables, including:

```text
person

family_group

family_relationship

organization

sangha_sevi

membership

attendance

audit
```

Kishore shall not duplicate these common domains.

---

# 5. Table Ownership

| Table                           | Owner                          | Purpose                     |
| ------------------------------- | ------------------------------ | --------------------------- |
| `kishore_participant`           | Kishore                        | Permanent KH identity       |
| `kishore_event`                 | Kishore/Event                  | Annual Kishore Puja         |
| `kishore_event_registration`    | Kishore                        | Event-specific registration |
| `kishore_membership_transition` | Kishore/Membership integration | KH → SS transition          |

---

# 6. `kishore_participant`

## Purpose

Stores the permanent identity of a Kishore participant.

One Person may have one Kishore identity.

The identity remains valid across multiple Kishore Puja years.

---

# 7. `kishore_participant` — Columns

| Column                    | Logical Type     | Required | Key    | Description                               |
| ------------------------- | ---------------- | -------: | ------ | ----------------------------------------- |
| `kishore_participant_pk`  | BIGINT           |      Yes | PK     | Internal primary key                      |
| `kishore_id`              | VARCHAR          |      Yes | UNIQUE | Permanent participant-facing KH ID        |
| `person_pk`               | BIGINT           |      Yes | FK     | Reference to `person`                     |
| `sakha_organization_pk`   | BIGINT           |      Yes | FK     | Participant's operational Sakha           |
| `guardian_sangha_sevi_pk` | BIGINT           |      Yes | FK     | Current assigned NSS Guardian             |
| `assigned_by_sakha_pk`    | BIGINT           |      Yes | FK     | Sakha responsible for Guardian assignment |
| `guardian_assigned_date`  | DATE             |      Yes | —      | Effective Guardian assignment date        |
| `registration_date`       | DATE             |      Yes | —      | Initial Kishore registration date         |
| `status`                  | Master/Data Type |      Yes | FK     | Participant status                        |
| `remarks`                 | TEXT             |       No | —      | Administrative remarks                    |
| `created_at`              | TIMESTAMP        |      Yes | —      | Creation timestamp                        |
| `created_by`              | BIGINT           |      Yes | FK     | Creating user                             |
| `updated_at`              | TIMESTAMP        |      Yes | —      | Last update timestamp                     |
| `updated_by`              | BIGINT           |      Yes | FK     | Updating user                             |

The Guardian-related fields are based on the frozen v2.1 Guardian Model. The Guardian reference is to `sangha_sevi`, not merely `person`.

---

# 8. `kishore_participant_pk`

Internal database primary key.

Characteristics:

```text
Unique
System Generated
Immutable
Never Reused
```

This is not the public KH ID.

---

# 9. `kishore_id`

Permanent participant-facing identifier.

Example:

```text
KH000001
KH000002
KH000123
```

Rules:

```text
Unique
Permanent
Immutable
Never Reused
```

The same KH ID is retained across years.

---

# 10. `person_pk`

Foreign key to the common Person table.

Relationship:

```text
person
   ↓
kishore_participant
```

The Kishore module does not duplicate Person information.

---

# 11. `sakha_organization_pk`

References the participant's operational Sakha.

Purpose:

* Sakha ownership
* Sakha reporting
* Sakha visibility
* Guardian assignment context

The Organization module remains authoritative for the Sakha.

---

# 12. `guardian_sangha_sevi_pk`

References the assigned NSS Guardian.

The reference shall be:

```text
kishore_participant.guardian_sangha_sevi_pk
        ↓
sangha_sevi
```

It shall not use a generic `guardian_person_pk` as the authoritative Guardian relationship.

This reflects the frozen v2.1 Guardian Model.

---

# 13. `assigned_by_sakha_pk`

References the Sakha responsible for assigning the Guardian.

This preserves assignment authority.

---

# 14. `guardian_assigned_date`

Records the effective date of the current Guardian assignment.

Guardian history shall be preserved through the project's history/audit mechanisms.

---

# 15. `registration_date`

Records the date on which the participant first entered the Kishore system.

This is distinct from individual annual event registrations.

---

# 16. `status`

Represents the current Kishore participant status.

The final allowable values shall come from the approved master-data/business-rule definitions.

This field shall not be confused with:

```text
Registration Status
Participation Status
Attendance Status
Membership Status
```

---

# 17. `remarks`

Optional administrative notes.

Remarks shall not be used to store structured business data that belongs in dedicated columns or related tables.

---

# 18. Audit Columns

All Kishore domain tables shall follow the common project audit standard.

At minimum:

```text
created_at
created_by
updated_at
updated_by
```

---

# 19. `kishore_event`

## Purpose

Represents an annual Kishore Puja event.

Examples:

```text
Kishore Puja 2026
Kishore Puja 2027
Kishore Puja 2028
```

---

# 20. `kishore_event` — Columns

| Column                 | Logical Type     | Required | Key | Description            |
| ---------------------- | ---------------- | -------: | --- | ---------------------- |
| `kishore_event_pk`     | BIGINT           |      Yes | PK  | Event primary key      |
| `event_name`           | VARCHAR          |      Yes | —   | Event name             |
| `financial_year`       | VARCHAR/SMALLINT |      Yes | —   | Applicable year        |
| `event_date`           | DATE             |      Yes | —   | Event date             |
| `host_organization_pk` | BIGINT           |      Yes | FK  | Host organization      |
| `location_pk`          | BIGINT           |       No | FK  | Event location         |
| `status`               | Master/Data Type |      Yes | FK  | Event status           |
| `description`          | TEXT             |       No | —   | Event description      |
| `remarks`              | TEXT             |       No | —   | Administrative remarks |
| `created_at`           | TIMESTAMP        |      Yes | —   | Creation timestamp     |
| `created_by`           | BIGINT           |      Yes | FK  | Creating user          |
| `updated_at`           | TIMESTAMP        |      Yes | —   | Last update timestamp  |
| `updated_by`           | BIGINT           |      Yes | FK  | Updating user          |

The earlier frozen source identifies the event around `kishore_event_pk`, `event_name`, `financial_year`, `event_date`, and `host_organization_pk`.

---

# 21. `kishore_event_pk`

Internal primary key for the Kishore event.

It uniquely identifies one annual Kishore Puja occurrence.

---

# 22. `event_name`

Human-readable event name.

Examples:

```text
Kishore Puja 2026
Kishore Puja 2027
```

---

# 23. `financial_year`

Identifies the applicable year.

This supports:

* Annual reporting
* Historical participation
* Year-wise dashboards
* Event search

---

# 24. `event_date`

Scheduled date of the Kishore Puja.

---

# 25. `host_organization_pk`

References the common Organization module.

The host organization is not necessarily the same as every participant's Sakha.

---

# 26. `location_pk`

Where applicable, references the common Location framework.

Kishore shall not create a duplicate location master.

---

# 27. `status`

Represents the lifecycle state of the event.

The exact status master shall follow the common Event framework.

Potential examples may include:

```text
DRAFT
PUBLISHED
COMPLETED
CANCELLED
```

These examples are illustrative unless separately frozen by the common Event framework.

---

# 28. `description`

Optional event description.

---

# 29. `remarks`

Optional administrative notes.

---

# 30. `kishore_event_registration`

## Purpose

Represents registration of one Kishore participant for one Kishore event.

Relationship:

```text
kishore_participant
        ↓
kishore_event_registration
        ↑
kishore_event
```

---

# 31. `kishore_event_registration` — Columns

| Column                          | Logical Type     | Required | Key | Description                         |
| ------------------------------- | ---------------- | -------: | --- | ----------------------------------- |
| `kishore_event_registration_pk` | BIGINT           |      Yes | PK  | Registration primary key            |
| `kishore_participant_pk`        | BIGINT           |      Yes | FK  | Kishore participant                 |
| `kishore_event_pk`              | BIGINT           |      Yes | FK  | Kishore event                       |
| `registration_date`             | DATE             |      Yes | —   | Registration date                   |
| `registration_status`           | Master/Data Type |      Yes | FK  | Registration state                  |
| `sakha_organization_pk`         | BIGINT           |      Yes | FK  | Sakha associated with registration  |
| `guardian_sangha_sevi_pk`       | BIGINT           |       No | FK  | Guardian applicable to registration |
| `participation_status`          | Master/Data Type |       No | FK  | Event participation state           |
| `remarks`                       | TEXT             |       No | —   | Administrative remarks              |
| `created_at`                    | TIMESTAMP        |      Yes | —   | Creation timestamp                  |
| `created_by`                    | BIGINT           |      Yes | FK  | Creating user                       |
| `updated_at`                    | TIMESTAMP        |      Yes | —   | Last update timestamp               |
| `updated_by`                    | BIGINT           |      Yes | FK  | Updating user                       |

---

# 32. Registration Primary Key

`kishore_event_registration_pk` uniquely identifies one registration record.

---

# 33. Participant Foreign Key

```text
kishore_event_registration.kishore_participant_pk
        ↓
kishore_participant.kishore_participant_pk
```

---

# 34. Event Foreign Key

```text
kishore_event_registration.kishore_event_pk
        ↓
kishore_event.kishore_event_pk
```

---

# 35. One Participant — One Registration Per Event

The logical business key is:

```text
kishore_participant_pk
+
kishore_event_pk
```

A participant shall not have duplicate active registrations for the same event.

The physical uniqueness constraint will be finalized during database implementation.

---

# 36. `registration_date`

Date on which the participant was registered for the specific Kishore event.

This differs from:

```text
kishore_participant.registration_date
```

which represents the participant's initial entry into Kishore.

---

# 37. `registration_status`

Represents the state of the event registration.

It is distinct from participant status.

---

# 38. `sakha_organization_pk`

Records the Sakha context applicable to the event registration.

This supports historical reporting and organizational ownership.

---

# 39. `guardian_sangha_sevi_pk`

Optional historical Guardian context for the particular event registration.

This is useful when the participant's Guardian changes between annual events.

The authoritative current Guardian remains on `kishore_participant`.

---

# 40. `participation_status`

Records the participant's event-specific participation state where required.

It is not the same as attendance.

---

# 41. Registration vs Attendance

The table shall not store attendance details as a substitute for the common Attendance module.

Conceptually:

```text
Registration
    ≠
Attendance
```

If attendance is required, the common Attendance framework shall be used.

---

# 42. Historical Registration

Completed annual registrations shall remain historically available.

Example:

```text
KH000123

2026 Registration
2027 Registration
2028 Registration
```

---

# 43. `kishore_membership_transition`

## Purpose

Records the transition between Kishore participation and approved NSS Membership.

---

# 44. `kishore_membership_transition` — Columns

| Column                    | Logical Type     | Required | Key | Description               |
| ------------------------- | ---------------- | -------: | --- | ------------------------- |
| `transition_pk`           | BIGINT           |      Yes | PK  | Transition primary key    |
| `kishore_participant_pk`  | BIGINT           |      Yes | FK  | Kishore participant       |
| `sangha_sevi_pk`          | BIGINT           |      Yes | FK  | Resulting NSS Sangha Sevi |
| `transition_date`         | DATE             |      Yes | —   | Transition date           |
| `membership_type_granted` | Master/Data Type |      Yes | FK  | Membership type granted   |
| `remarks`                 | TEXT             |       No | —   | Administrative remarks    |
| `created_at`              | TIMESTAMP        |      Yes | —   | Creation timestamp        |
| `created_by`              | BIGINT           |      Yes | FK  | Creating user             |
| `updated_at`              | TIMESTAMP        |      Yes | —   | Last update timestamp     |
| `updated_by`              | BIGINT           |      Yes | FK  | Updating user             |

The source explicitly identifies the transition structure around:

```text
transition_pk
kishore_participant_pk
sangha_sevi_pk
transition_date
membership_type_granted
```

---

# 45. `transition_pk`

Internal primary key for the transition record.

---

# 46. `sangha_sevi_pk`

References the common Sangha Sevi identity created/approved through the Membership module.

Kishore does not generate the Sangha Sevi ID independently.

---

# 47. `transition_date`

Date on which the approved transition relationship became effective.

---

# 48. `membership_type_granted`

Records the Membership type associated with the approved transition.

The Membership module remains authoritative for allowable membership types.

---

# 49. KH → SS Relationship

The permanent historical relationship is:

```text
kishore_participant
        ↓
kishore_membership_transition
        ↓
sangha_sevi
```

Example:

```text
KH000123
   ↓
Transition
   ↓
SS000456
```

---

# 50. No Automatic Membership

A Kishore participant shall not receive a Sangha Sevi ID merely by:

* Registration
* Attendance
* Participation
* Completion of Kishore Puja

Membership requires the common Membership approval process.

---

# 51. No Duplicate Person

Membership transition shall not create another Person record.

The same Person remains connected to:

```text
Kishore History
+
NSS Membership
```

---

# 52. Foreign-Key Summary

```text
kishore_participant.person_pk
        ↓
person

kishore_participant.sakha_organization_pk
        ↓
organization

kishore_participant.guardian_sangha_sevi_pk
        ↓
sangha_sevi

kishore_participant.assigned_by_sakha_pk
        ↓
organization

kishore_event.host_organization_pk
        ↓
organization

kishore_event.location_pk
        ↓
location framework

kishore_event_registration.kishore_participant_pk
        ↓
kishore_participant

kishore_event_registration.kishore_event_pk
        ↓
kishore_event

kishore_event_registration.sakha_organization_pk
        ↓
organization

kishore_event_registration.guardian_sangha_sevi_pk
        ↓
sangha_sevi

kishore_membership_transition.kishore_participant_pk
        ↓
kishore_participant

kishore_membership_transition.sangha_sevi_pk
        ↓
sangha_sevi
```

---

# 53. Logical Relationship Cardinalities

```text
Person
  1
  |
  0..1
Kishore Participant
```

```text
Kishore Participant
  1
  |
  N
Kishore Event Registration
```

```text
Kishore Event
  1
  |
  N
Kishore Event Registration
```

```text
Kishore Participant
  1
  |
  N
Membership Transition
```

---

# 54. Permanent Identity Model

```text
PERSON
   ↓
KISHORE_PARTICIPANT
   ↓
KH000123
```

The KH ID remains permanent.

---

# 55. Annual Event Model

```text
KISHORE_PARTICIPANT
       |
       +---- REGISTRATION 2026
       |
       +---- REGISTRATION 2027
       |
       +---- REGISTRATION 2028
```

---

# 56. Guardian Model

```text
SANGHA_SEVI
     |
     | Guardian
     ↓
KISHORE_PARTICIPANT
```

The Guardian must be an NSS Member belonging to the participant's Sakha.

The Sakha assigns the Guardian.

---

# 57. Guardian Assignment Fields

The frozen Guardian requirement is represented by:

```text
guardian_sangha_sevi_pk
assigned_by_sakha_pk
guardian_assigned_date
```

These fields shall not be replaced by a generic free-text Guardian field.

---

# 58. Current vs Historical Guardian

Current participant Guardian:

```text
kishore_participant.guardian_sangha_sevi_pk
```

Historical event Guardian, where required:

```text
kishore_event_registration.guardian_sangha_sevi_pk
```

This prevents later Guardian changes from destroying historical event context.

---

# 59. Family Integration

The Kishore module uses the common Family relationship:

```text
family_group
    ↓
family_relationship
    ↓
person
    ↓
kishore_participant
```

No Kishore-specific family table is introduced.

---

# 60. Family Visibility

Family users may access their own family's Kishore information, including:

```text
Participant Details
Registration Details
Activity History
Training History
Participation Status
Guardian Details
Membership Transition Status
```

Access remains restricted to the user's own family.

---

# 61. Sakha Visibility

Sakha users access Kishore records within their authorized Sakha scope.

The Sakha scope is based on:

```text
sakha_organization_pk
```

---

# 62. Kendra Visibility

Kendra users may access Kishore records across Sakhas according to RBAC.

No separate Kendra-specific Kishore table is required.

---

# 63. Common Attendance Integration

Kishore does not introduce:

```text
kishore_attendance
```

as a core table.

Where required:

```text
kishore event
       ↓
common attendance framework
```

The Attendance module remains authoritative.

---

# 64. Common Audit Integration

Kishore uses the common Audit framework.

No:

```text
kishore_audit
```

table is introduced.

---

# 65. Common Organization Integration

Kishore uses:

```text
organization
```

for:

* Participant Sakha
* Guardian assignment Sakha
* Event host organization

No Kishore-specific organization master is introduced.

---

# 66. Common Membership Integration

Kishore uses:

```text
membership
sangha_sevi
```

for the Membership transition and Guardian identity.

---

# 67. Status Fields

Status fields shall use approved master data where the project standard requires master-driven values.

Potential status categories include:

```text
Participant Status
Registration Status
Participation Status
Event Status
```

These shall remain separate.

---

# 68. No Combined Status

The table design shall not create a generic field such as:

```text
status
```

that attempts to represent:

```text
Registration
Attendance
Membership
Participation
```

simultaneously.

---

# 69. Unique Identity Constraints

Logical uniqueness requirements:

```text
kishore_id
```

must be unique.

The participant identity:

```text
person_pk
```

must not produce multiple active Kishore identities.

The event registration combination:

```text
kishore_participant_pk
+
kishore_event_pk
```

must not produce duplicate active registrations.

---

# 70. Referential Integrity

All foreign keys shall enforce valid references to their owning modules.

Examples:

```text
person_pk → person

sangha_sevi_pk → sangha_sevi

organization_pk → organization
```

No orphaned Kishore references shall be permitted.

---

# 71. Historical Integrity

Completed records shall remain available for:

* Historical reports
* Family dashboards
* Sakha reports
* Kendra reports
* Membership transition traceability
* Audit

---

# 72. Soft Deletion / Deactivation

The physical implementation shall follow the project-wide soft-delete/history standard.

The business rules do not authorize physical deletion of historical Kishore participation records.

---

# 73. Indexing Requirements

The final PostgreSQL implementation should provide efficient lookup for:

```text
kishore_id

person_pk

sakha_organization_pk

guardian_sangha_sevi_pk

kishore_event_pk

registration_date

financial_year

sangha_sevi_pk
```

Exact indexes shall be finalized during physical database optimization.

---

# 74. Search Requirements

The table design should support searches by:

```text
KH ID
Participant Name
Person ID
Sakha
Guardian
Event Year
Event
Registration Status
Participation Status
Membership Transition
```

Name search remains a Person-module concern.

---

# 75. Reporting Requirements

The design supports:

```text
Total Kishore Participants

Participants by Sakha

Annual Registrations

Annual Participation

Guardian Distribution

Participants by Event

Family Participation

KH → SS Transitions
```

---

# 76. Family Dashboard Data

Family Dashboard can derive:

```text
Person
   +
Family Relationship
   +
Kishore Participant
   +
Event Registration
   +
Guardian
   +
Membership Transition
```

No separate family-facing Kishore table is required.

---

# 77. Sakha Dashboard Data

Sakha Dashboard can derive:

```text
Kishore Participants
+
Event Registrations
+
Guardian Assignments
+
Participation
```

filtered by the authorized Sakha.

---

# 78. Kendra Dashboard Data

Kendra Dashboard can aggregate:

```text
All Kishore Participants
+
All Events
+
All Registrations
+
All Sakhas
+
Guardian Assignments
+
Membership Transitions
```

---

# 79. Table Boundary — Person

Kishore shall not store duplicate:

```text
Name
Gender
DOB
Mobile
Email
Address
```

when those values belong to Person.

---

# 80. Table Boundary — Family

Kishore shall not store duplicate:

```text
Father
Mother
Spouse
Children
Family Head
Family Address
```

Family relationships belong to the Family module.

---

# 81. Table Boundary — Organization

Kishore shall not store duplicate Sakha master information.

The Organization module owns organizational identity and hierarchy.

---

# 82. Table Boundary — Membership

Kishore shall not store duplicate:

```text
Sangha Sevi ID
Membership Status
Membership Renewal
Membership Transfer
Membership History
```

The Membership module owns these domains.

---

# 83. Table Boundary — Attendance

Kishore shall not duplicate the Attendance engine.

---

# 84. Table Boundary — Event

If a common Event framework becomes authoritative, Kishore-specific event data shall contain only the additional Kishore-specific information required by the approved architecture.

This document preserves the current logical `kishore_event` entity.

---

# 85. No SQL Schema

This document intentionally does not contain:

```text
CREATE TABLE
ALTER TABLE
CREATE INDEX
CREATE TRIGGER
CREATE SEQUENCE
Django migration
```

Those belong to the physical database implementation stage.

---

# 86. No Premature Physical Constraint

Where the business requirement is clear but the exact PostgreSQL implementation has not been frozen, this document records the logical requirement without prescribing SQL syntax.

---

# 87. Core Table Summary

```text
1. kishore_participant
   Permanent Kishore identity

2. kishore_event
   Annual Kishore Puja event

3. kishore_event_registration
   Participant registration for an event

4. kishore_membership_transition
   KH → NSS Membership relationship
```

---

# 88. Complete Logical Model

```text
                         PERSON
                           |
                           v
                  KISHORE_PARTICIPANT
                   |       |       |
                   |       |       |
                   |       |       +---- Guardian ----> SANGHA_SEVI
                   |       |
                   |       +---- Sakha -------------> ORGANIZATION
                   |
                   +----< KISHORE_EVENT_REGISTRATION >---- KISHORE_EVENT
                   |
                   +----< KISHORE_MEMBERSHIP_TRANSITION >- SANGHA_SEVI
```

---

# 89. Final Table Design

```text
kishore_participant
        |
        +---- kishore_event_registration ---- kishore_event
        |
        +---- kishore_membership_transition ---- sangha_sevi
        |
        +---- guardian_sangha_sevi ---- sangha_sevi
        |
        +---- sakha_organization ---- organization
        |
        +---- person ---- family
```

---

# 90. Final Architecture Rules

The physical implementation shall preserve:

```text
One Person
   ↓
One Kishore Identity
   ↓
One Permanent KH ID
   ↓
Many Annual Registrations
   ↓
Many Participation Records through event/attendance integration
   ↓
Optional Membership Transition
   ↓
Sangha Sevi
```

Guardian:

```text
Sakha
   ↓
Assigns
   ↓
NSS Member / Sangha Sevi
   ↓
Kishore Participant
```

---

# 91. Source Alignment

This table design reflects the currently frozen Kishore source:

```text
Annual Event-Based Kishore Puja

Permanent KH ID

Sakha-Based Registration

Sakha-Assigned NSS Guardian

Family Visibility

Year-wise Participation

KH → SS Membership Transition
```

The source identifies Kishore Puja as an annual event/activity rather than a permanent organizational unit.

---

# 92. Status

```text
DOCUMENT STATUS:
DRAFT — SOURCE ALIGNED

VERSION:
1.0.0
```

---

# End of Document
