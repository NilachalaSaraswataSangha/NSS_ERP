# NSS ERP Membership Business Rules

Version: 1.0

Status: FROZEN

Source Documents:

* 03_NSS_MEMBERSHIP_RULES.md
* 04_MEMBERSHIP_BUSINESS_RULES.md v4.0
* 00_membership_decision_register.md

Branch:

feature/membership-design

---

# 1. Purpose

Defines the business rules governing Membership records in NSS ERP.

These rules take precedence over database implementation.

---

# 2. Core Principles

## Person ≠ Member

A Person may exist without Membership.

A Member must always be a Person.

---

## One Person = One Membership

Each Person may possess only one Membership.

---

## One Membership = One Sangha Sevi ID

Each Membership shall have exactly one Sangha Sevi ID.

---

## History Never Deleted

Membership history shall remain permanently available.

Physical deletion is prohibited.

---

# 3. Membership Identity Rule

Every Member shall have:

* One Membership Record
* One Sangha Sevi ID

Sangha Sevi ID is:

* Unique
* Permanent
* Never Reused
* Never Changed

---

# 4. Sangha Sevi ID Rule

Examples:

SS00000001

SS00000002

SS00000003

The Sangha Sevi ID is the official Membership identity of a Member.

The Sangha Sevi ID shall remain unchanged throughout the Member's lifetime.

---

# 5. Membership Type Rule

Allowed Membership Types:

* PROBATIONARY_MEMBER
* REGULAR_MEMBER
* ASSOCIATE_MEMBER

No additional Membership Types shall be created without formal NSS approval.

---

# 6. Membership Status Rule

Allowed Membership Status values:

* ACTIVE
* SUSPENDED
* DECEASED
* DISCIPLINARY_REVIEW

Membership Status is separate from Membership Type.

Examples:

REGULAR_MEMBER + ACTIVE

REGULAR_MEMBER + SUSPENDED

PROBATIONARY_MEMBER + ACTIVE

---

# 7. Membership Admission Rule

Probationary Membership shall be established through:

Applicant
↓
Sakha Review
↓
Sakha President Recommendation
↓
Parichalak Approval
↓
Anumati Patra Issued
↓
Probationary Member

Membership begins upon issuance of Anumati Patra.

---

# 8. Probationary Membership Rule

Probationary Membership is the entry Membership Type within NSS.

Probationary Membership does not automatically become Regular Membership.

Probationary Membership shall be reviewed according to NSS policy.

Possible outcomes:

* Approved for Regular Membership
* Probation Extended

---

# 9. Regular Membership Rule

Regular Membership requires:

* Renewal Cycle Review
* Sakha President Recommendation
* Parichalak Approval
* Parichaya Patra Issuance

Parichaya Patra establishes Regular Membership.

---

# 10. Associate Membership Rule

Associate Membership is a separate Membership Type recognized by NSS.

Associate Membership follows the rules established by NSS Bye-Laws.

---

# 11. Honorary Recognition Rule

Honorary Recognition is not a Membership Type.

Honorary Recognition may be granted to an existing Member.

Honorary Recognition does not change:

* Membership Type
* Membership Status
* Sangha Sevi ID

Recognition history shall be preserved permanently.

---

# 12. Renewal Rule

Membership Renewal occurs annually.

Official Renewal Deadline:

Dola Purnima

Renewal fees shall be configurable.

The system shall not hardcode renewal fees.

---

# 13. Renewal Failure Rule

Failure to renew by Dola Purnima shall result in:

REGULAR_MEMBER
↓
PROBATIONARY_MEMBER

Rules:

* Same Membership retained
* Same Sangha Sevi ID retained
* Membership History preserved
* Renewal History preserved
* No new Membership created

There is no renewal grace period.

---

# 14. Membership Type Restoration Rule

Membership Type Restoration may restore:

PROBATIONARY_MEMBER
↓
REGULAR_MEMBER

Requirements:

* Renewal Cycle Review
* Parichalak Approval

Rules:

* Same Membership retained
* Same Sangha Sevi ID retained
* History preserved

---

# 15. Membership Transfer Rule

Membership Transfer workflow:

Member
↓
Current Sakha Verification
↓
Target Sakha Verification
↓
Parichalak Approval
↓
Transfer Approved
↓
Effective On Dola Purnima

Rules:

* Sangha Sevi ID unchanged
* Transfer history preserved
* Membership identity preserved

---

# 16. Attendance Rule

Primary attendance source:

Weekly Sangha Puja

Attendance shall be recorded according to NSS policy.

---

# 17. Attendance Review Rule

Attendance Categories:

* GOOD_STANDING
* WATCH_LIST
* ATTENDANCE_REVIEW
* DEFERRED_REVIEW
* LONG_TERM_CONCERN

Three consecutive absences may trigger Attendance Review.

Attendance Review does not automatically suspend Membership.

---

# 18. Disciplinary Rule

Disciplinary concerns may be raised by NSS office bearers.

Only the Parichalak may approve disciplinary actions affecting Membership.

Possible decisions:

* No Action
* Warning
* Suspension

---

# 19. Suspension Rule

Suspension affects Membership Status only.

Examples:

REGULAR_MEMBER + ACTIVE
↓
REGULAR_MEMBER + SUSPENDED

PROBATIONARY_MEMBER + ACTIVE
↓
PROBATIONARY_MEMBER + SUSPENDED

Suspension does not affect:

* Membership Type
* Membership Record
* Sangha Sevi ID

Suspended Members:

* Cannot renew Membership
* Cannot exercise Membership privileges

---

# 20. Suspension Restoration Rule

Only the Parichalak may restore suspended Membership.

Upon restoration:

SUSPENDED
↓
ACTIVE

Rules:

* Membership Type unchanged
* Same Membership retained
* Same Sangha Sevi ID retained
* History preserved

---

# 21. Membership Documents Rule

Official Membership documents:

## Anumati Patra

Issued to Probationary Members.

Establishes Probationary Membership.

---

## Parichaya Patra

Issued to Regular Members.

Establishes Regular Membership.

---

# 22. Audit Rule

The system shall maintain audit records for:

* Membership Reviews
* Membership Type Restoration
* Membership Transfers
* Suspensions
* Suspension Restorations
* Attendance Reviews

Audit records shall capture:

* Decision Date
* Decision Type
* Approved By
* Remarks

---

# 23. History Preservation Rule

The system shall permanently preserve:

* Membership History
* Renewal History
* Transfer History
* Attendance Review History
* Recognition History
* Suspension History
* Membership Type Restoration History

No historical Membership information shall be physically deleted.

---

# 24. Deletion Rule

Membership records shall not be physically deleted.

Only status changes and historical records are permitted.

---

# 25. Design Principles

* Person First
* Membership Separate
* One Membership
* One Sangha Sevi ID
* Parichalak Authority
* History Preserved
* Audit Enabled
* Dola Purnima Driven Lifecycle
* By-Law Supremacy

---

# Related Documents

* 00_membership_decision_register.md
* 01_membership_module_overview.md
* 03_membership_lifecycle.md
* 04_membership_table_design.md
