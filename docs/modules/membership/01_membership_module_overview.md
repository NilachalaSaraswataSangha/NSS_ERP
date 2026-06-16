# NSS ERP Membership Module Overview

Version: 1.0

Status: DRAFT

Branch:
feature/membership-design

---

# Purpose

The Membership Module manages the complete NSS Membership lifecycle.

The module establishes Membership identity, Membership progression, Membership renewal, Membership transfer, attendance-related reviews, disciplinary actions, and Membership history.

Membership is built upon the Person Module and serves as the foundation for Governance, Attendance, and future NSS operational modules.

---

# Module Objectives

The Membership Module shall:

* Manage Membership identity.
* Manage Sangha Sevi IDs.
* Support Probationary Membership.
* Support Regular Membership.
* Support Associate Membership.
* Support Membership renewal.
* Support Membership Type Restoration.
* Support Membership transfers.
* Support Attendance Review processes.
* Support disciplinary actions.
* Preserve Membership history permanently.

---

# Core Principles

## Person ≠ Member

A Person may exist without Membership.

Examples:

* Family Member
* Kumari Participant
* Kishore Participant
* Guardian
* Guest

A Member must always be a Person.

---

## One Person = One Membership

Each Person may possess only one Membership.

Each Membership belongs to exactly one Person.

---

## One Membership = One Sangha Sevi ID

Each Membership shall have exactly one Sangha Sevi ID.

The Sangha Sevi ID is:

* Unique
* Permanent
* Never Reused

---

## History Never Deleted

Membership records shall never be physically deleted.

Historical information shall remain permanently available.

---

# Membership Types

The NSS Membership model supports:

* PROBATIONARY_MEMBER
* REGULAR_MEMBER
* ASSOCIATE_MEMBER

Membership Types are controlled through Membership business rules and Bye-Law provisions.

---

# Membership Status

The NSS Membership model supports:

* ACTIVE
* SUSPENDED
* DECEASED
* DISCIPLINARY_REVIEW

Membership Status represents the operational standing of a Member.

Membership Status is separate from Membership Type.

Example:

REGULAR_MEMBER + ACTIVE

REGULAR_MEMBER + SUSPENDED

PROBATIONARY_MEMBER + ACTIVE

---

# Membership Identity Model

Membership identity is established through:

Person
↓
Membership
↓
Sangha Sevi ID

A Membership identity remains constant throughout the lifetime of the Member.

Membership transfers, renewals, suspensions, and Membership Type changes do not create new identities.

---

# Membership Documents

## Anumati Patra

Official Membership document for Probationary Members.

Issuance of Anumati Patra establishes Probationary Membership.

---

## Parichaya Patra

Official Membership document for Regular Members.

Issuance of Parichaya Patra establishes Regular Membership.

---

# Membership Lifecycle Overview

## Admission

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

---

## Regular Membership Progression

Probationary Member
↓
Renewal Cycle Review
↓
Sakha President Recommendation
↓
Parichalak Approval
↓
Parichaya Patra Issued
↓
Regular Member

---

## Renewal Failure

Regular Member
↓
Fails To Renew
↓
Probationary Member

---

## Membership Type Restoration

Probationary Member
↓
Review
↓
Parichalak Approval
↓
Regular Member

---

## Membership Transfer

Member
↓
Transfer Request
↓
Verification
↓
Parichalak Approval
↓
Transfer Effective On Dola Purnima

---

# Renewal Model

Membership renewal occurs annually.

Official renewal deadline:

Dola Purnima

There is no grace period after Dola Purnima.

Failure to renew results in Membership Type change according to Membership business rules.

---

# Attendance Integration

Membership attendance is based primarily on:

Weekly Sangha Puja

Attendance reviews may be triggered according to NSS policy.

Attendance reviews do not automatically suspend Membership.

---

# Disciplinary Integration

The Membership Module supports:

* Warning
* Suspension
* Restoration

Disciplinary decisions affect Membership Status.

Disciplinary decisions do not affect Membership identity.

---

# Governance Integration

Governance eligibility depends upon Membership standing.

Membership alone does not automatically grant Governance authority.

Governance rules are defined within the Governance Module.

---

# Module Dependencies

Depends On:

* Foundation Module
* Person Module
* Organization Module

Supports:

* Governance Module
* Attendance Module
* Family Module
* Kumari Module
* Kishore Module
* Reporting Module

---

# Future Enhancements

Future Membership enhancements may include:

* Digital Membership Cards
* Online Renewal
* Automated Notifications
* Mobile Application Integration
* Advanced Membership Analytics

---

# Related Documents

Membership Design Documents:

* 00_membership_decision_register.md
* 02_membership_business_rules.md
* 03_membership_lifecycle.md
* 04_membership_table_design.md

Project Source Documents:

* 03_NSS_MEMBERSHIP_RULES.md
* 04_MEMBERSHIP_BUSINESS_RULES.md
