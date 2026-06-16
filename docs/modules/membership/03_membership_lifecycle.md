# NSS ERP Membership Lifecycle

Version: 1.0

Status: FROZEN

Source Documents:

* 04_MEMBERSHIP_BUSINESS_RULES.md v4.0
* 00_membership_decision_register.md
* 02_membership_business_rules.md

Branch:

feature/membership-design

---

# 1. Purpose

Defines all Membership lifecycle transitions within NSS ERP.

This document describes how Membership Types, Membership Statuses, and Membership-related processes change over time.

This document does not define database implementation.

---

# 2. Membership Identity Lifecycle

Every Membership lifecycle begins with a Person.

Lifecycle:

Person
↓
Membership
↓
Sangha Sevi ID

Rules:

* One Person may have only one Membership.
* One Membership may have only one Sangha Sevi ID.
* Sangha Sevi ID is permanent.
* Sangha Sevi ID is never reused.
* Membership identity never changes.

---

# 3. Membership Admission Lifecycle

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
PROBATIONARY_MEMBER

Rules:

* Membership begins upon issuance of Anumati Patra.
* Membership Status becomes ACTIVE.
* Sangha Sevi ID is generated.
* Membership history begins.

---

# 4. Probationary Membership Lifecycle

PROBATIONARY_MEMBER
↓
Participation
↓
Renewal Cycle Review

Possible Outcomes:

A)

PROBATIONARY_MEMBER
↓
Approved
↓
REGULAR_MEMBER

B)

PROBATIONARY_MEMBER
↓
Review
↓
PROBATIONARY_MEMBER

Rules:

* Probationary Membership does not automatically become Regular Membership.
* Review is required.
* Approval is required.

---

# 5. Regular Membership Lifecycle

PROBATIONARY_MEMBER
↓
Renewal Cycle Review
↓
Sakha President Recommendation
↓
Parichalak Approval
↓
Parichaya Patra Issued
↓
REGULAR_MEMBER

Rules:

* Regular Membership is established upon issuance of Parichaya Patra.
* Membership identity remains unchanged.
* Sangha Sevi ID remains unchanged.

---

# 6. Membership Renewal Lifecycle

Member
↓
Renewal Due
↓
Renewal Payment
↓
Renewal Recorded
↓
Membership Continues

Official Renewal Date:

Dola Purnima

Rules:

* Renewal occurs annually.
* Renewal fees are configurable.
* Renewal history is preserved permanently.

---

# 7. Renewal Failure Lifecycle

REGULAR_MEMBER
↓
Fails To Renew
↓
PROBATIONARY_MEMBER

Rules:

* Same Membership retained.
* Same Sangha Sevi ID retained.
* Membership history preserved.
* Renewal history preserved.
* No new Membership created.
* No new Sangha Sevi ID generated.
* No grace period exists.

---

# 8. Membership Type Restoration Lifecycle

PROBATIONARY_MEMBER
↓
Next Dola Purnima Renewal Cycle
↓
Review
↓
Parichalak Approval
↓
REGULAR_MEMBER

Rules:

* Same Membership retained.
* Same Sangha Sevi ID retained.
* Membership history preserved.
* No new Membership created.

---

# 9. Associate Membership Lifecycle

Applicant
↓
Associate Membership Approval
↓
ASSOCIATE_MEMBER

Rules:

* Associate Membership is a separate Membership Type.
* Associate Membership follows NSS Bye-Law provisions.
* Membership identity remains permanent.

---

# 10. Membership Transfer Lifecycle

Member
↓
Transfer Request
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

* Sangha Sevi ID unchanged.
* Membership unchanged.
* Transfer history preserved permanently.
* Membership identity preserved.

---

# 11. Attendance Review Lifecycle

GOOD_STANDING
↓
WATCH_LIST
↓
ATTENDANCE_REVIEW

Possible Outcomes:

ATTENDANCE_REVIEW
↓
DEFERRED_REVIEW

OR

ATTENDANCE_REVIEW
↓
LONG_TERM_CONCERN

Rules:

* Attendance Review does not automatically suspend Membership.
* Attendance Review does not automatically change Membership Type.
* Attendance Review does not automatically change Membership Status.

---

# 12. Disciplinary Lifecycle

Concern Raised
↓
Parichalak Review
↓
Decision

Possible Decisions:

* No Action
* Warning
* Suspension

Rules:

* Recommendations do not constitute disciplinary action.
* Only the Parichalak may approve disciplinary action.

---

# 13. Suspension Lifecycle

ACTIVE
↓
DISCIPLINARY_REVIEW
↓
SUSPENDED

Rules:

* Suspension affects Membership Status only.
* Membership Type remains unchanged.
* Membership identity remains unchanged.
* Sangha Sevi ID remains unchanged.

Examples:

REGULAR_MEMBER + ACTIVE
↓
REGULAR_MEMBER + SUSPENDED

PROBATIONARY_MEMBER + ACTIVE
↓
PROBATIONARY_MEMBER + SUSPENDED

ASSOCIATE_MEMBER + ACTIVE
↓
ASSOCIATE_MEMBER + SUSPENDED

---

# 14. Suspension Restoration Lifecycle

SUSPENDED
↓
Parichalak Approval
↓
ACTIVE

Rules:

* Membership Type unchanged.
* Membership retained.
* Sangha Sevi ID retained.
* History preserved permanently.

---

# 15. Deceased Member Lifecycle

ACTIVE
↓
DECEASED

Rules:

* Membership identity preserved.
* Sangha Sevi ID preserved.
* Membership history preserved permanently.
* Historical reporting remains available.

---

# 16. Lifecycle Principles

* One Person = One Membership
* One Membership = One Sangha Sevi ID
* Sangha Sevi ID Permanent
* Membership Identity Permanent
* History Never Deleted
* Audit Required
* Dola Purnima Driven Renewal Cycle
* Membership Type Separate From Membership Status
* Transfer Does Not Create New Membership
* Suspension Does Not Affect Membership Type

---

# Related Documents

* 00_membership_decision_register.md
* 01_membership_module_overview.md
* 02_membership_business_rules.md
* 04_membership_table_design.md
