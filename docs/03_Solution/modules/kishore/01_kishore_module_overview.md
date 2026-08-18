# NSS ERP — Kishore Puja Module Overview

**Document ID:** SOL-KISH-001  
**Version:** 1.0.0  
**Status:** DRAFT — SOURCE ALIGNED  
**Module:** Kishore Puja  
**Parent System:** Nilachala Saraswata Sangha ERP

---

# 1. Purpose

The Kishore Puja Module manages the NSS Kishore Puja program as an annual, event-based youth participation program for boys.

The module provides structured management of:

- Kishore identity
- Event registration
- Year-wise participation
- Sakha association
- Guardian assignment
- Event participation history
- Family visibility
- Future transition to NSS Membership

Kishore Puja is intentionally modeled differently from Kumari Sangha.

---

# 2. Institutional Position

Kishore Puja is not modeled as a permanent organizational unit equivalent to Kumari Sangha.

The frozen project position is:

```text
Kishore Puja
=
Annual Event / Activity
for Boys
```

Participants may come from different Sanghas and participate through the annual Kishore Puja event model.

---

# 3. Kishore vs Kumari

The two youth programs have different business models.

## Kumari Sangha

```text
Continuous Development Program

Own identity

Ongoing participation

Training

Dina-Lipi

Niyam Panchak

Dasa Sheela
```

## Kishore Puja

```text
Annual Event

Event Registration

Year-wise Participation

Guardian-Based

Sakha-Based Registration

Future Membership Pipeline
```

This distinction is frozen in the NSS V2 baseline.

---

# 4. Target Participants

The frozen Kishore model identifies the intended participants as boys, including:

* Boys from NSS families
* Sons of NSS members
* Boys nominated by parents
* Boys nominated by Sangha

Eligibility shall follow the approved Kishore rules.

The module shall not assume that every participant must already be an NSS member.

---

# 5. Kishore Identity

Every Kishore participant receives a dedicated Kishore ID.

Example:

```text
KH000001
KH000002
KH000003
```

The Kishore ID is:

* Unique
* Permanent
* Never reused
* Retained across years

The same Kishore ID is used when the participant attends Kishore Puja in subsequent years.

---

# 6. Kishore ID vs Sangha Sevi ID

Kishore ID and NSS Sangha Sevi ID are separate identities.

Example:

```text
Kishore ID

KH000123
```

Later:

```text
NSS Membership

SS000456
```

The relationship is permanently preserved.

A Kishore participant does not automatically receive an NSS Sangha Sevi ID.

---

# 7. Person Foundation

Every Kishore participant shall be associated with the common Person foundation.

Conceptually:

```text
PERSON
   │
   └── Kishore Participation
```

The Kishore module shall not create a duplicate Person identity.

The common principle remains:

```text
Person ≠ Member
```

---

# 8. Family Integration

Kishore participants may be connected to their family through the common Family module.

Conceptually:

```text
Family
   │
   └── Son
        │
        ▼
   Kishore Participant
        │
        ▼
      KH000123
```

The Family module remains the owner of:

* Family
* Family relationships
* Parent/child relationships
* Marriage relationships
* Family history

Kishore does not duplicate these structures.

---

# 9. Family Nomination

The frozen Kishore model supports nomination through the Family Portal.

Conceptually:

```text
Parent
   ↓
Nominate Son
   ↓
Kishore Registration
```

This provides a family-driven registration path.

---

# 10. Sakha Nomination

Kishore registration may also originate from the Sakha.

Conceptually:

```text
Sakha
   ↓
Nominate Boy
   ↓
Kishore Registration
```

The Sakha association is retained for operational ownership and reporting.

---

# 11. Sakha Association

Every Kishore registration shall be associated with a Sakha for operational ownership and reporting.

This does not mean Kishore Puja itself becomes a permanent Sakha-level organization.

The Sakha provides the participant's organizational context for the registration.

---

# 12. Cross-Sangha Participation

Participants may come from different Sanghas.

Therefore:

```text
Participant's Home Sakha
        ≠
Kishore Event Host
```

where applicable.

Participation in an event does not automatically transfer the participant's Sakha association.

---

# 13. Annual Event Model

Kishore Puja operates on a year-wise event model.

Example:

```text
KH000123

2026 Kishore Puja
2027 Kishore Puja
2028 Kishore Puja
```

The participant retains:

```text
KH000123
```

across all years.

Only event-specific participation changes.

---

# 14. Event Identity

Each Kishore Puja occurrence is represented as a distinct event.

Conceptually:

```text
Kishore Event
      │
      ├── Year
      ├── Event Date
      ├── Host Organization
      └── Registrations
```

The event remains historically identifiable.

---

# 15. Core Kishore Entities

The current frozen Kishore logical model identifies:

```text
kishore_participant

kishore_event

kishore_event_registration

kishore_membership_transition
```

These form the Kishore-specific domain model.

---

# 16. `kishore_participant`

Represents the permanent Kishore participant identity.

Conceptually:

```text
PERSON
   │
   ▼
KISHORE PARTICIPANT
   │
   ▼
KH000123
```

The participant record persists across multiple Kishore Puja years.

---

# 17. `kishore_event`

Represents an annual Kishore Puja event.

Examples:

```text
Kishore Puja 2026
Kishore Puja 2027
Kishore Puja 2028
```

The event is the central unit of year-wise participation.

---

# 18. `kishore_event_registration`

Represents the registration of a Kishore participant for a particular Kishore event.

Conceptually:

```text
KH000123
    ↓
Kishore Puja 2026
    ↓
Registration
```

The same participant may have multiple registration records across different annual events.

---

# 19. `kishore_membership_transition`

Represents the future transition from Kishore participation to NSS Membership.

Conceptually:

```text
KH000123
    ↓
NSS Membership Application
    ↓
Membership Approval
    ↓
SS000456
```

The relationship remains permanently traceable.

---

# 20. Guardian Model

Every Kishore participant must have an assigned Guardian.

This is a frozen rule.

The Guardian is:

```text
NSS Member
+
Member of the participant's Sakha
+
Assigned by the Sakha
```

The latest frozen Guardian Model supersedes earlier generic guardian proposals.

---

# 21. Guardian Assignment

Guardian assignment is operationally performed by the Sakha.

Conceptually:

```text
Kishore Participant
        ↓
Guardian Required
        ↓
Sakha Assigns Guardian
        ↓
NSS Member of Same Sakha
```

---

# 22. Guardian Identity

The Guardian reference shall point to the common NSS Sangha Sevi identity.

The frozen database impact identifies:

```text
guardian_sangha_sevi_pk
assigned_by_sakha_pk
guardian_assigned_date
```

and the Guardian references:

```text
sangha_sevi
```

rather than a generic Person record.

---

# 23. Guardian Responsibilities

The assigned Guardian is responsible for:

* Guidance
* Supervision
* Participation monitoring
* Communication with family
* Support during Kishore Puja
* Support during related activities

These responsibilities are part of the frozen Guardian Model.

---

# 24. Guardian and Parent Are Different Concepts

The Family module identifies the participant's family/parents.

The Kishore Guardian is an operational NSS role.

Therefore:

```text
Parent
   ≠
Assigned Kishore Guardian
```

unless the same person independently satisfies the Guardian rule.

The Guardian must satisfy the frozen NSS-member/Sakha assignment requirement.

---

# 25. Guardian Assignment History

Guardian assignment shall be historically traceable.

At minimum the system must preserve:

```text
Guardian
Assigned Sakha
Assignment Date
Assignment Authority
```

If the Guardian changes, the previous assignment shall remain historically available.

---

# 26. Guardian Change

A Guardian may be changed by the authorized Sakha process.

The new Guardian must satisfy the current Guardian eligibility rule.

Changing the Guardian shall not create:

```text
New Kishore ID
```

or:

```text
New Person
```

for the participant.

---

# 27. Event Registration

Registration connects:

```text
Kishore Participant
        ↓
Kishore Event
```

The registration may also retain the participant's operational Sakha and Guardian context as required by the frozen design.

---

# 28. Year-wise Participation

A participant may register in multiple annual Kishore Puja events.

Example:

```text
KH000123

2026 → Registered
2027 → Registered
2028 → Registered
```

The system must preserve each year's registration independently.

---

# 29. No New KH ID Each Year

The following is prohibited:

```text
2026 → KH000123
2027 → KH000456
```

for the same participant.

Instead:

```text
2026 → KH000123
2027 → KH000123
2028 → KH000123
```

The KH ID is permanent.

---

# 30. Event Participation History

The system shall preserve:

* Event
* Year
* Registration
* Guardian
* Sakha
* Participation status
* Relevant attendance/participation information
* Historical changes

where applicable.

---

# 31. Attendance Boundary

Kishore registration and attendance are different concepts.

```text
Registration
     ≠
Attendance
```

A registered participant may or may not attend.

The common Attendance framework shall be reused where attendance tracking is required.

---

# 32. Event Participation Boundary

Participation in one annual Kishore Puja does not automatically imply participation in the next year's event.

Each annual event has its own registration/participation record.

---

# 33. Event Host

A Kishore event may be hosted/organized by the relevant NSS organizational authority.

The host organization is part of the event context.

Hosting an event does not automatically change a participant's Sakha.

---

# 34. Participant's Sakha

The participant's Sakha remains the organizational context used for:

* Registration
* Guardian assignment
* Reporting
* Operational ownership

The participant does not become a member of the host Sakha merely by attending an event.

---

# 35. Kendra Visibility

Kendra-authorized users may view Kishore participants across all Sakhas.

This supports Kendra-wide monitoring and reporting.

---

# 36. Sakha Visibility

A Sakha-authorized user may view Kishore participants belonging to that Sakha.

The frozen visibility rule is:

```text
Sakha Secretary
      ↓
Only their Sakha's boys

Kendra
      ↓
All boys across all Sakhas
```

---

# 37. Guardian Visibility

An assigned Guardian may view the Kishore participants assigned to that Guardian, subject to common RBAC and privacy rules.

---

# 38. Family Visibility

Family members may view authorized Kishore information for their own family.

Potential information includes:

* Participant details
* Registration details
* Participation history
* Guardian details
* Participation status
* Membership transition status

Family access is restricted to the user's own family records.

---

# 39. Family Dashboard Integration

The Family Dashboard may show:

```text
Son
KH000456

Guardian
Assigned NSS Guardian

Participation
2025
2026

Status
Active / Applicable Status
```

This is part of the frozen Family First visibility model.

---

# 40. Future Membership Pipeline

Kishore Puja provides a potential pathway toward future NSS Membership.

Conceptually:

```text
Kishore
   ↓
Participation
   ↓
Development
   ↓
NSS Membership Application
   ↓
Membership Approval
   ↓
Sangha Sevi
```

This is a transition pathway, not automatic membership.

---

# 41. NSS Membership Application

A Kishore participant may later apply for NSS Membership where eligible.

The application is handled by the common Membership module.

Kishore does not approve NSS Membership.

---

# 42. Membership Approval

After NSS Membership approval:

```text
KH000123
      ↓
Membership Approved
      ↓
SS000456
```

The official Sangha Sevi identity is generated according to the common Membership rules.

---

# 43. Membership Transition History

The transition shall create a permanent historical link:

```text
KH000123
      │
      ▼
kishore_membership_transition
      │
      ▼
SS000456
```

The original Kishore history remains preserved.

---

# 44. Membership Type

The transition may preserve the membership type granted through the common Membership process.

Examples may include:

```text
REGULAR_MEMBER
PROBATIONARY_MEMBER
```

The Membership module remains authoritative for these types.

---

# 45. Kishore History After Membership

Becoming an NSS member shall not delete the participant's Kishore history.

The system shall preserve:

* KH ID
* Annual event registrations
* Participation history
* Guardian history
* Sakha history
* Membership transition

---

# 46. Kishore ID Permanence

The KH ID remains permanently associated with the participant's Kishore history.

Example:

```text
KH000123

2026
2027
2028
NSS Membership transition
```

All remain linked to the same KH ID.

---

# 47. No Duplicate Person on Transition

Transition to NSS Membership shall not create another Person.

The same Person remains associated with:

```text
Kishore History
+
NSS Membership
```

---

# 48. Kishore Status

Kishore participant status is distinct from NSS Membership status.

The exact final status master shall be defined in the Business Rules document.

The module shall not conflate:

```text
Kishore Participation Status
```

with:

```text
NSS Membership Status
```

---

# 49. Event Status

Kishore events shall have their own event lifecycle.

The exact common Event status model shall be used where applicable.

The event lifecycle shall remain distinct from the participant lifecycle.

---

# 50. Cancellation and Historical Integrity

If an annual Kishore event is cancelled or otherwise changed, its historical identity shall remain preserved.

Participant registration history shall not be silently deleted.

Detailed cancellation/rescheduling rules shall be finalized in the Kishore Business Rules document.

---

# 51. Common Module Integration

Kishore integrates with:

```text
Person
Family
Organization
Membership
Sangha Sevi
Attendance
Event
Reports
Administration/RBAC
Audit
```

Kishore-specific functionality shall not duplicate common foundation capabilities.

---

# 52. Governance Integration

If Kishore event organization requires governance or committee assignments, the common Governance framework shall be reused.

Kishore shall not create a separate governance architecture.

---

# 53. Security

Kishore access shall use the common NSS RBAC framework.

Authorization shall consider:

```text
User
+
Role
+
Organization Scope
+
Permission
```

No separate Kishore authentication system shall be created.

---

# 54. Audit

Kishore administrative actions shall use the common Audit framework.

Auditable actions include:

* Participant creation
* KH ID generation
* Event creation
* Registration
* Guardian assignment
* Guardian change
* Sakha association
* Membership transition
* Administrative corrections

---

# 55. Master Data

Kishore shall use master data where appropriate for:

```text
Event Type
Participant Status
Registration Status
Participation Status
Transition Type
Membership Type
```

The final Master Data Catalog remains authoritative.

---

# 56. Reports

The Kishore module shall support reporting such as:

```text
Total Kishore Participants
Annual Registrations
Participation by Sakha
Participation by Year
Guardian Assignment
Guardian Distribution
Family Participation
Membership Transitions
```

Reports shall respect RBAC and organizational scope.

---

# 57. Kishore Puja Portal

The UI baseline identifies a dedicated Kishore Puja portal.

Conceptually:

```text
Kishore Puja

Current Year Registrations

By Sakha

By Guardian

KH000101
KH000102
KH000103

Participation History
```

This is aligned with the annual-event Kishore model.

---

# 58. Family Portal

The Family Portal may provide:

```text
Kishore Registration
Participation History
Guardian Information
Status
Membership Transition
```

for the family's own Kishore participants.

---

# 59. No Permanent Kishore Sangha Requirement

The system shall not require creation of a permanent:

```text
Kishore Sangha
```

organizational unit merely to operate Kishore Puja.

The frozen source explicitly distinguishes Kishore Puja from the continuous organizational model of Kumari Sangha.

---

# 60. No Unified Youth Identity

Kishore shall retain its own:

```text
KH ID
```

It shall not be replaced by a generic:

```text
Youth ID
```

The project baseline explicitly preserves:

```text
Kumari ID ≠ Sangha Sevi ID
Kishore ID ≠ Sangha Sevi ID
```

and keeps the two youth domains distinct.

---

# 61. No Unified Youth Event Model

Kishore and Kumari may reuse common technical infrastructure, but their business models remain separate.

Kumari:

```text
Continuous Development
```

Kishore:

```text
Annual Event
```

The Solution layer shall preserve this distinction.

---

# 62. Core Kishore Architecture

```text
PERSON
   │
   ▼
KISHORE PARTICIPANT
   │
   │ KH000123
   │
   ├──────────────► KISHORE EVENT
   │                     │
   │                     ▼
   │             EVENT REGISTRATION
   │
   └──────────────► MEMBERSHIP TRANSITION
                         │
                         ▼
                    SANGHA SEVI
                         │
                         ▼
                      SS000456
```

Guardian and Sakha context are associated with the Kishore participation/registration model.

---

# 63. Core Entity Summary

```text
kishore_participant
    ↓
Permanent KH identity

kishore_event
    ↓
Annual Kishore Puja event

kishore_event_registration
    ↓
Year-specific participation

kishore_membership_transition
    ↓
KH → SS historical transition
```

---

# 64. Common Foundation Summary

```text
person
family_group
family_relationship
organization
membership
sangha_sevi
attendance
governance
audit
rbac
```

These remain common NSS modules.

---

# 65. Architectural Boundaries

The following distinctions are mandatory:

```text
Kishore Participant
        ≠
NSS Member

KH ID
        ≠
SS ID

Registration
        ≠
Attendance

Parent
        ≠
Operational Guardian

Participant's Sakha
        ≠
Event Host

Kishore Puja
        ≠
Kumari Sangha
```

---

# 66. History Preservation

The Kishore module follows:

```text
History Never Deleted
```

The system shall preserve:

* KH identity
* Annual registration history
* Guardian assignment history
* Sakha association history
* Participation history
* Membership transition history
* Audit history

---

# 67. Future Expansion

The architecture may later support additional Kishore-related activities/events without changing the permanent participant identity model.

Possible future events may be added through the common Event framework where approved.

No future event shall automatically create a new KH ID.

---

# 68. Out of Scope for This Overview

The following require detailed rules in later Kishore documents:

* Exact age eligibility
* Detailed registration approval workflow
* Detailed Guardian replacement workflow
* Event scheduling rules
* Event cancellation/rescheduling
* Attendance rules
* Event completion
* Detailed membership eligibility
* Detailed membership approval workflow
* Detailed reports
* Detailed permissions
* Physical database constraints

These shall not be invented in this overview.

---

# 69. Related Documents

The Kishore Solution documentation set is:

```text
docs/03_Solution/modules/kishore/

├── 01_kishore_module_overview.md
├── 02_kishore_erd.md
├── 03_kishore_lifecycle.md
├── 04_kishore_business_rules.md
└── 05_kishore_table_design.md
```

---

# 70. Source-Aligned Frozen Decisions

The following decisions are already frozen in the project source:

```text
✓ Kishore is annual/event-based
✓ Kishore is for boys
✓ KH identity
✓ KH ID is permanent
✓ KH ID retained across years
✓ Sakha-based registration/ownership
✓ Parent nomination
✓ Sakha nomination
✓ Mandatory assigned Guardian
✓ Guardian is NSS member of participant's Sakha
✓ Guardian assigned by Sakha
✓ Family visibility
✓ Kendra-wide visibility
✓ Sakha-scoped visibility
✓ Future KH → NSS Membership transition
✓ Permanent KH → SS relationship
✓ Kishore remains separate from Kumari
```

---

# 71. Status

```text
DOCUMENT STATUS:
DRAFT — SOURCE ALIGNED

VERSION:
1.0.0
```

The Kishore Module Overview establishes the following fundamental model:

```text
                  PERSON
                    │
                    ▼
             KISHORE PARTICIPANT
                    │
                  KH ID
                    │
          ┌─────────┴─────────┐
          │                   │
          ▼                   ▼
   ANNUAL EVENTS          GUARDIAN
          │                   │
          ▼                   ▼
   REGISTRATION          NSS MEMBER
          │
          │
          ▼
   FUTURE MEMBERSHIP
          │
          ▼
      SANGHA SEVI
          │
          ▼
       SS ID
```

---

# End of Document
