# NSS ERP Membership Table Design

Version: 1.0

Status: FROZEN

Source Documents:

* 04_MEMBERSHIP_BUSINESS_RULES.md v4.0
* 00_membership_decision_register.md
* 02_membership_business_rules.md
* 03_membership_lifecycle.md

Branch:

feature/membership-design

---

# Purpose

Defines the physical database design for the NSS ERP Membership Module.

Business Rules and Lifecycle documents must be approved before modifying this document.

---

# Design Principles

* Person ≠ Member
* One Person = One Membership
* One Membership = One Sangha Sevi ID
* Membership Type separate from Membership Status
* History Never Deleted
* Audit Enabled
* Dola Purnima Driven Lifecycle
* Transfer History Preserved
* Suspension History Preserved
* Membership Type Restoration History Preserved

---

# Table 1: membership_type_master

## Purpose

Stores Membership Types.

---

## Columns

membership_type_pk UUID PRIMARY KEY

membership_type_code VARCHAR(50) NOT NULL

membership_type_name VARCHAR(100) NOT NULL

display_order INTEGER NOT NULL

created_at TIMESTAMPTZ NOT NULL

is_active BOOLEAN NOT NULL DEFAULT TRUE

---

## Seed Data

PROBATIONARY_MEMBER

REGULAR_MEMBER

ASSOCIATE_MEMBER

---

## Unique Constraints

membership_type_code

membership_type_name

---

## Indexes

membership_type_code

is_active

---

# Table 2: membership_status_master

## Purpose

Stores Membership Status values.

---

## Columns

membership_status_pk UUID PRIMARY KEY

membership_status_code VARCHAR(50) NOT NULL

membership_status_name VARCHAR(100) NOT NULL

display_order INTEGER NOT NULL

created_at TIMESTAMPTZ NOT NULL

is_active BOOLEAN NOT NULL DEFAULT TRUE

---

## Seed Data

ACTIVE

SUSPENDED

DECEASED

DISCIPLINARY_REVIEW

---

## Unique Constraints

membership_status_code

membership_status_name

---

## Indexes

membership_status_code

is_active

---

# Table 3: membership

## Purpose

Stores NSS Membership records.

One Person may have only one Membership.

---

## Columns

membership_pk UUID PRIMARY KEY

membership_code VARCHAR(20) NOT NULL

person_pk UUID NOT NULL

membership_type_pk UUID NOT NULL

membership_status_pk UUID NOT NULL

anumati_patra_number VARCHAR(50) NULL

anumati_patra_date DATE NULL

parichaya_patra_number VARCHAR(50) NULL

parichaya_patra_date DATE NULL

membership_start_date DATE NOT NULL

remarks TEXT NULL

created_at TIMESTAMPTZ NOT NULL

updated_at TIMESTAMPTZ NULL

deleted_at TIMESTAMPTZ NULL

is_active BOOLEAN NOT NULL DEFAULT TRUE

---

## Foreign Keys

person_pk
→ person.person_pk

membership_type_pk
→ membership_type_master.membership_type_pk

membership_status_pk
→ membership_status_master.membership_status_pk

---

## Unique Constraints

membership_code

person_pk

---

## Business Rules

One Person = One Membership

Membership Code = Sangha Sevi ID

Examples:

SS00000001

SS00000002

SS00000003

Membership Code never changes.

Membership Code never reused.

---

## Indexes

membership_code

person_pk

membership_type_pk

membership_status_pk

is_active

---

# Table 4: membership_review

## Purpose

Stores Membership reviews.

Supports:

* Regular Membership Approval
* Membership Type Restoration

---

## Columns

membership_review_pk UUID PRIMARY KEY

membership_pk UUID NOT NULL

review_date DATE NOT NULL

review_type VARCHAR(50) NOT NULL

review_result VARCHAR(50) NOT NULL

recommended_by_person_pk UUID NULL

approved_by_person_pk UUID NOT NULL

remarks TEXT NULL

created_at TIMESTAMPTZ NOT NULL

---

## Review Types

REGULAR_MEMBERSHIP

TYPE_RESTORATION

---

## Review Results

APPROVED

PROBATION_EXTENDED

REJECTED

---

# Table 5: membership_renewal

## Purpose

Stores Membership renewal history.

---

## Columns

membership_renewal_pk UUID PRIMARY KEY

membership_pk UUID NOT NULL

renewal_year INTEGER NOT NULL

renewal_date DATE NOT NULL

renewal_fee NUMERIC(12,2) NOT NULL

receipt_number VARCHAR(50) NULL

recorded_by_person_pk UUID NULL

remarks TEXT NULL

created_at TIMESTAMPTZ NOT NULL

---

## Business Rules

Renewal history never deleted.

One renewal record per Membership per renewal cycle.

---

# Table 6: membership_transfer

## Purpose

Stores Membership transfer history.

---

## Columns

membership_transfer_pk UUID PRIMARY KEY

membership_pk UUID NOT NULL

from_organization_pk UUID NOT NULL

to_organization_pk UUID NOT NULL

request_date DATE NOT NULL

approval_date DATE NULL

effective_date DATE NOT NULL

approved_by_person_pk UUID NOT NULL

remarks TEXT NULL

created_at TIMESTAMPTZ NOT NULL

---

## Business Rules

Transfer does not create new Membership.

Transfer does not create new Sangha Sevi ID.

Transfer history permanently preserved.

---

# Table 7: membership_type_history

## Purpose

Stores Membership Type changes.

---

## Columns

membership_type_history_pk UUID PRIMARY KEY

membership_pk UUID NOT NULL

old_membership_type_pk UUID NOT NULL

new_membership_type_pk UUID NOT NULL

change_date DATE NOT NULL

change_reason VARCHAR(100) NOT NULL

approved_by_person_pk UUID NULL

remarks TEXT NULL

created_at TIMESTAMPTZ NOT NULL

---

## Examples

PROBATIONARY_MEMBER
→ REGULAR_MEMBER

REGULAR_MEMBER
→ PROBATIONARY_MEMBER

---

# Table 8: membership_honorary_recognition

## Purpose

Stores Honorary Recognition history.

---

## Columns

membership_honorary_recognition_pk UUID PRIMARY KEY

membership_pk UUID NOT NULL

recognition_title VARCHAR(200) NOT NULL

recognition_date DATE NOT NULL

approved_by_person_pk UUID NULL

remarks TEXT NULL

created_at TIMESTAMPTZ NOT NULL

---

## Business Rules

Honorary Recognition does not affect:

* Membership Type
* Membership Status
* Sangha Sevi ID

---

# Table 9: membership_suspension_history

## Purpose

Stores disciplinary decisions.

---

## Columns

membership_suspension_history_pk UUID PRIMARY KEY

membership_pk UUID NOT NULL

decision_date DATE NOT NULL

decision_type VARCHAR(50) NOT NULL

approved_by_person_pk UUID NOT NULL

restoration_date DATE NULL

remarks TEXT NULL

created_at TIMESTAMPTZ NOT NULL

---

## Decision Types

WARNING

SUSPENSION

RESTORATION

---

## Business Rules

Suspension affects Membership Status only.

Membership Type remains unchanged.

Suspension history permanently preserved.

---

# Deferred Tables

The following are intentionally excluded from Membership v1:

* Membership Card History
* Digital Membership Credentials
* Automated Renewal Notifications
* Membership Appeals
* Advanced Disciplinary Workflow

---

# Future Modules

## Governance Module

Will consume:

* Membership Status
* Membership Type

---

## Attendance Module

Will consume:

* Membership Reviews
* Attendance Reviews

---

## Reporting Module

Will consume:

* Membership History
* Renewal History
* Transfer History
* Recognition History
* Suspension History

---

# Related Documents

* 00_membership_decision_register.md
* 01_membership_module_overview.md
* 02_membership_business_rules.md
* 03_membership_lifecycle.md
