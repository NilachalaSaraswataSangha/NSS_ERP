# NSS ERP

Nilachala Saraswata Sangha Enterprise Resource Planning (NSS ERP)

---

# Overview

NSS ERP is a comprehensive web-based management platform being developed for Nilachala Saraswata Sangha.

The system is designed to support membership management, family management, governance, attendance tracking, Kumari Sangha, Kishore Puja, Founder & Heritage records, UPBS operations, reporting, and future NSS operational activities.

The project follows a:

```text
Database First
    ↓
API First
    ↓
UI First
```

design philosophy, ensuring that business rules are frozen before implementation.

---

# Project Objectives

* Centralized NSS member management
* Family-first relationship tracking
* Governance and committee management
* Attendance and review workflows
* Kumari Sangha and Kishore Puja management
* Founder & Heritage preservation
* UPBS operational support
* Historical record preservation
* Audit-compliant data management
* Role-based access control
* International branch support

---

# Technology Stack

> **Note:** `docs/03_Solution/architecture/TECH_STACK_DECISIONS.md` (added 2026-08-16) is the
> Approved forward-looking decision record — it replaces Bootstrap 5 with Tailwind CSS +
> DaisyUI + Alpine.js, commits to actually wiring up FastAPI, and adds a hosting/offline plan.
> None of that is implemented in code yet; the stack below reflects the current codebase.

## Frontend

* Django Templates
* Bootstrap 5
* HTMX *(dependency pinned via `django-htmx`; not yet wired into any template as of the current codebase — see `docs/PROJECT_DOCUMENTATION.md` → Gotchas)*

---

## Backend

* Django
* FastAPI *(pinned in `requirements.txt`; no FastAPI app/router exists in `backend/` yet — Django views call the ORM directly, see `docs/PROJECT_DOCUMENTATION.md` → Architecture)*

---

## Database

* PostgreSQL

---

## Authentication

* Django Authentication
* JWT (Future)

---

## Deployment

* Ubuntu
* Nginx
* Gunicorn

---

## Future Enhancements

* Redis Cache
* Background Workers
* Mobile Application
* API Integrations

---

# Project Architecture

```text
Browser
   │
   ▼
Django Templates
   │
   ▼
Django Views (function-based; call the ORM directly)
   │
   ▼
Django ORM
   │
   ▼
PostgreSQL
```

*(Note: FastAPI is pinned as a dependency but has no app/router wired up yet — the diagram
above reflects the actual current request path. See `docs/PROJECT_DOCUMENTATION.md` →
Architecture for the planned two-track Django ORM / raw-SQL-DDL data layer.)*

---

# Core Principles

## Person ≠ Member

A Person may exist without being a Member.

Examples:

* Family Member
* Kumari Participant
* Kishore Participant
* Future Applicant
* Historical Person

A Member must always be a Person.

---

## Family First

Family relationships are maintained independently of membership status.

---

## History Never Deleted

Business records are preserved permanently.

Physical deletion is avoided.

Soft delete is preferred.

---

## Audit First

All critical business operations must be auditable.

---

## Master Data Driven

Business configuration is controlled through master tables rather than hardcoded values.

---

## Global Ready

The system is designed to support NSS activities within India and internationally.

---

# Organization Hierarchy

```text
KENDRA
├── ANCHALIKA
│   └── SAKHA
├── ZILLA
│   └── SAKHA
└── PATHA_CHAKRA
```

Notes:

* PATHA_CHAKRA is an Organization Type.
* PATHA_CHAKRA exists directly under KENDRA.
* PATHA_CHAKRA may operate within India or internationally.
* SAKHA exists under ANCHALIKA or ZILLA.

> **Flag (2026-08-19):** the Organization module's business rules were revised to v1.1.0
> (`docs/03_Solution/modules/organization/04_organization_business_rules.md`, GOVERNANCE
> ALIGNED) and now explicitly leave the exact type-to-type parent compatibility matrix shown
> above as an **open item**, not a frozen decision — only the generic apex + self-referencing
> 3-table structure is frozen. Treat this diagram as the current working assumption, not a
> closed design, until that open item is resolved.

---

# Module Structure

*The sections below describe the full planned module roadmap. As of this writing, only
**Foundation, Membership, Family, Governance (stub), Attendance (stub), and Founder & Heritage**
exist as Django apps under `backend/` — Mahila Sangha, Kumari Sangha, Kishore Puja, Sevak
Sangha, UPBS, Reports & Analytics, and Administration have no app directory yet. Solution-layer
design documentation (overview/ERD/lifecycle/business-rules/table-design) is now complete for
Membership, Family, Attendance, Organization, Person, Founder & Heritage, Kumari Sangha,
Kishore Puja, and Mahila Sangha, and largely complete for Sevak Sangha — ahead of, and not yet
reconciled with, any backend implementation. See `docs/PROJECT_DOCUMENTATION.md` for the
current, code-verified status of each.*

## Foundation

* Organization Management
* Person Management
* Master Data
* Authentication & RBAC
* Audit & History
* Global Location Management

---

## Membership

* Member Registration
* Membership Types
* Membership Approval
* Renewal
* Transfer
* Membership Journey
* Sangha Sevi ID Management

---

## Family

* Family Dashboard
* Family Tree
* Relationship Management

---

## Governance

* General Body
* Governing Body
* Advisory Board
* Committees
* Position Assignment

---

## Attendance

* Weekly Attendance
* Attendance Review
* Attendance Reports

---

## Mahila Sangha

* Membership
* Activities
* Governance

---

## Kumari Sangha

* KM Identity
* Activities
* Training
* Membership Transition

---

## Kishore Puja

* KH Identity
* Registration
* Guardian Assignment

---

## Sevak Sangha

* Volunteer Development
* Training
* Activities

---

## Founder & Heritage

* Biography
* Philosophy
* Teachings
* Publications

---

## UPBS

* Registration
* Accommodation
* Committee Management
* Reports

---

## Reports & Analytics

* Membership Reports
* Attendance Reports
* Governance Reports
* UPBS Reports

---

## Administration

* Users
* Roles
* Permissions
* System Settings

---

# Database Design Principles

## Person Module

```text
Person ≠ Member
```

A Person may exist without Membership.

A Member must always be linked to a Person.

---

## Contact Information

Supports:

* International Phone Numbers
* Country Phone Codes
* Email Addresses

Rules:

* Mobile Number + Country Phone Code must be unique.
* Email is not required to be unique.
* At least one contact method is mandatory.

---

## Address Management

Supports:

* Multiple Addresses
* Primary Address Selection
* Global Locations
* Postal Code Mapping

Rules:

* One Person may have multiple addresses.
* Only one address may be Primary.
* Primary Address may be changed at any time.

---

## Location Hierarchy

```text
Country
    ↓
State / Province
    ↓
District / Region
    ↓
City / Village
```

Postal Codes are maintained separately and linked through mapping tables.

---

# Development Workflow

## Branch Strategy

```text
main
 └── develop
      └── feature/*
```

---

## Feature Development Workflow

```text
Create Feature Branch
        ↓
Implement Changes
        ↓
Commit Changes
        ↓
Merge into develop
        ↓
Create Release Notes
        ↓
Create Git Tag
        ↓
Merge develop into main
        ↓
Create GitHub Release
```

---

# Release Management

Every version must include:

* Git Tag
* Release Notes Document
* GitHub Release

Release Notes Location:

```text
docs/05_Releases/
```

Examples:

```text
v0.1.0.md
v0.2.0.md
v0.2.1.md
v0.3.0.md
v0.4.0.md
v0.5.0.md
v0.5.1.md
```

---

# Completed Milestones

## v0.1.0

Initial Project Setup

---

## v0.2.0

Foundation Models

---

## v0.2.1

Admin Setup

---

## v0.3.0

UI Foundation and Authentication Complete

---

## v0.4.0

Organization Module Design Complete *(design/ERD/business-rules/table-design docs only — SQL DDL under `database/ddl/02_organization/` is not yet implemented; see `docs/PROJECT_DOCUMENTATION.md`)*

---

## v0.5.0

Person Module Design Complete

---

## v0.5.1

Person Database Schema Complete

* Global Location Model
* Person Schema
* Person Address Schema
* International Mobile Support
* Address Mapping Model

---

# Current Development Status

Completed:

* Foundation Architecture
* Authentication Foundation
* Organization Module Design (v1.1.0, GOVERNANCE ALIGNED — restructured 2026-08-19; type-to-type
  parent hierarchy left as an open item, not frozen)
* Person Module Design (v1.0.0, SOURCE ALIGNED — 2 tables: person, document_master)
* Person Database Schema (partial — `person`/`person_address` implemented; `document_master`
  has no SQL counterpart yet, and the docs' `person_id` naming doesn't match the DDL's
  `person_code`)
* Global Location Model
* Membership Module Design
* Family Module Design
* Attendance Module Design (Review Workflow Frozen)
* Founder & Heritage Module Design (v1.0.0, SOURCE ALIGNED — 8 tables designed; backend
  implements only 1, `founder_master`)
* Kumari Sangha Module Design (v1.0.0, SOURCE ALIGNED)
* Kishore Puja Module Design (v1.0.0, SOURCE ALIGNED — Guardian Model frozen v2.1)
* Mahila Sangha Module Design (v2.1.0, Bye-Law-aligned governance model)
* Sevak Sangha Module Design (partially frozen — table design only; see
  `docs/PROJECT_DOCUMENTATION.md`)

Current Focus:

* Reconciling Solution-layer design docs with actual Django/SQL implementation across
  organization, membership, family, attendance, heritage, kumari, kishore, mahila, and sevak —
  all are documented but none has corresponding backend code beyond membership/family/heritage's
  existing minimal models. No release doc has been created yet for the module-doc work landed
  since v0.5.1 (heritage added; organization/person/kumari/kishore expanded or restructured).

Next Release Target:

```text
Not yet decided — the module-documentation backlog (organization through sevak) is now largely
complete at the design level; the next concrete milestone is backend implementation/
reconciliation rather than another design-doc pass. See docs/PROJECT_DOCUMENTATION.md → Open
questions / TODOs.
```

---

# Repository Structure

```text
NSS_ERP
│
├── backend
│
├── database
│   ├── ddl
│   └── seed
│
├── docs
│   ├── 00_Project_Governance
│   ├── 01_Authoritative_References
│   ├── 02_Requirements
│   ├── 03_Solution
│   ├── 04_Testing
│   └── 05_Releases
│
└── README.md
```

See `docs/PROJECT_DOCUMENTATION.md` for the full, code-verified breakdown of each directory.

---

# Current Stable Version

```text
v0.5.1
```

Person Database Schema Complete

---

# License

Internal NSS ERP Project

All Rights Reserved.
