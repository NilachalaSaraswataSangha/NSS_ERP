# NSS ERP Membership Decision Register

Version: 1.0

Status: FROZEN

Source Version:
04_MEMBERSHIP_BUSINESS_RULES.md v4.0

Branch:
feature/membership-design

---

---

# Purpose

Records all frozen Membership decisions approved for NSS ERP implementation.

This document serves as the authoritative bridge between NSS source documents and ERP design documents.

---

# Membership Identity Decisions

## MEM-001

Decision:

Person ≠ Member

Status:

FROZEN

---

## MEM-002

Decision:

One Person = One Membership = One Sangha Sevi ID

Status:

FROZEN

---

## MEM-003

Decision:

Sangha Sevi ID is permanent and never reused.

Status:

FROZEN

---

# Membership Type Decisions

## MEM-010

Membership Types:

* PROBATIONARY_MEMBER
* REGULAR_MEMBER
* ASSOCIATE_MEMBER

Status:

FROZEN

---

## MEM-011

Honorary Recognition is not a Membership Type.

Status:

FROZEN

---

# Membership Admission Decisions

## MEM-020

Probationary Membership requires:

* Sakha Review
* Sakha President Recommendation
* Parichalak Approval
* Anumati Patra Issuance

Status:

FROZEN

---

## MEM-021

Membership begins upon issuance of Anumati Patra.

Status:

FROZEN

---

# Regular Membership Decisions

## MEM-030

Probationary Membership does not automatically become Regular Membership.

Status:

FROZEN

---

## MEM-031

Regular Membership requires:

* Renewal Cycle Review
* Sakha President Recommendation
* Parichalak Approval
* Parichaya Patra Issuance

Status:

FROZEN

---

## MEM-032

Possible outcomes:

* Approved For Regular Membership
* Probation Extended

Status:

FROZEN

---

# Renewal Decisions

## MEM-040

Renewal deadline:

Dola Purnima

Status:

FROZEN

---

## MEM-041

No renewal grace period exists.

Status:

FROZEN

---

## MEM-042

Renewal fee must be configurable.

Status:

FROZEN

---

## MEM-043

Failure to renew:

REGULAR_MEMBER
↓
PROBATIONARY_MEMBER

Status:

FROZEN

---

## MEM-044

Renewal failure does not create:

* New Membership
* New Sangha Sevi ID

Status:

FROZEN

---

# Membership Type Restoration

## MEM-050

Membership Type Restoration may restore:

PROBATIONARY_MEMBER
↓
REGULAR_MEMBER

Status:

FROZEN

---

## MEM-051

Membership Type Restoration requires:

* Parichalak Review
* Parichalak Approval

Status:

FROZEN

---

## MEM-052

Same Membership retained.

Same Sangha Sevi ID retained.

History preserved.

Status:

FROZEN

---

# Transfer Decisions

## MEM-060

Membership Transfer requires:

* Current Sakha Verification
* Target Sakha Verification
* Parichalak Approval

Status:

FROZEN

---

## MEM-061

Transfer becomes effective on Dola Purnima.

Status:

FROZEN

---

## MEM-062

Transfer does not change Sangha Sevi ID.

Status:

FROZEN

---

# Attendance Decisions

## MEM-070

Attendance source:

Weekly Sangha Puja

Status:

FROZEN

---

## MEM-071

Attendance Categories:

* GOOD_STANDING
* WATCH_LIST
* ATTENDANCE_REVIEW
* DEFERRED_REVIEW
* LONG_TERM_CONCERN

Status:

FROZEN

---

## MEM-072

Attendance Review does not automatically suspend Membership.

Status:

FROZEN

---

# Membership Status Decisions

## MEM-080

Membership Status values:

* ACTIVE
* SUSPENDED
* DECEASED
* DISCIPLINARY_REVIEW

Status:

FROZEN

---

# Disciplinary Decisions

## MEM-090

Only the Parichalak may suspend Membership.

Status:

FROZEN

---

## MEM-091

Only the Parichalak may restore suspended Membership.

Status:

FROZEN

---

## MEM-092

Suspension affects Membership Status only.

Membership Type remains unchanged.

Status:

FROZEN

---

## MEM-093

Suspended Members cannot renew Membership.

Status:

FROZEN

---

## MEM-094

Possible disciplinary decisions:

* No Action
* Warning
* Suspension

Status:

FROZEN

---

# Audit & History Decisions

## MEM-100

Audit required for:

* Membership Review
* Transfer
* Suspension
* Restoration
* Membership Type Restoration

Status:

FROZEN

---

## MEM-101

History shall never be deleted.

Status:

FROZEN

---

# Source Documents

Derived From:

* 03_NSS_MEMBERSHIP_RULES.md
* 04_MEMBERSHIP_BUSINESS_RULES.md v4.0
* Membership Freeze Reviews
* Dola Purnima Decisions

Status:

FROZEN
