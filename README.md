# NSS ERP

Nilachala Saraswata Sangha Enterprise Resource Planning (NSS ERP)

---

## Overview

NSS ERP is a comprehensive web-based management platform being developed for Nilachala Saraswata Sangha.

The system is designed to support membership management, family management, governance, attendance tracking, Kumari Sangha, Kishore Puja, Founder & Heritage records, UPBS operations, reporting, and future NSS operational activities.

The project follows a **Database First → API First → UI First** design philosophy, ensuring that business rules are frozen before implementation.

---

## Project Objectives

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

---

## Technology Stack

### Frontend

* Django Templates
* Bootstrap 5
* HTMX

### Backend

* Django
* FastAPI

### Database

* PostgreSQL

### Authentication

* Django Authentication
* JWT (Future)

### Deployment

* Ubuntu
* Nginx
* Gunicorn

### Future Enhancements

* Redis Cache
* Background Workers
* Mobile Application
* API Integrations

---

## Project Architecture

```text
Browser
   │
   ▼
Django Templates
   │
   ▼
FastAPI Services
   │
   ▼
Django ORM
   │
   ▼
PostgreSQL
```

---

## Core Principles

### Person ≠ Member

A person may exist without being a member.

Examples:

* Family member
* Kumari participant
* Kishore participant
* Future applicant
* Historical person

### Family First

Family relationships are maintained independently of membership status.

### History Never Deleted

Business records are preserved permanently.

Physical deletion is avoided.

### Audit First

All critical changes are auditable.

### Master Data Driven

Business configuration is controlled through master tables rather than hardcoded values.

---

## Organization Hierarchy

```text
KENDRA
├── ANCHALIKA
│   └── SAKHA
├── ZILLA
│   └── SAKHA
└── PATHA_CHAKRA
```

---

## Module Structure

### Foundation

* Organization Management
* Person Management
* Master Data
* Authentication & RBAC
* Audit & History

### Membership

* Member Registration
* Membership Types
* Renewal
* Transfer
* Membership Journey

### Family

* Family Dashboard
* Family Tree
* Relationship Management

### Governance

* General Body
* Governing Body
* Advisory Board
* Committees
* Position Assignment

### Attendance

* Weekly Attendance
* Attendance Review
* Attendance Reports

### Mahila Sangha

* Membership
* Activities
* Governance

### Kumari Sangha

* KM Identity
* Activities
* Training
* Membership Transition

### Kishore Puja

* KH Identity
* Registration
* Guardian Assignment

### Sevak Sangha

* Volunteer Development
* Training
* Activities

### Founder & Heritage

* Biography
* Philosophy
* Teachings
* Publications

### UPBS

* Registration
* Accommodation
* Committee Management
* Reports

### Reports & Analytics

* Membership Reports
* Attendance Reports
* Governance Reports
* UPBS Reports

### Administration

* Users
* Roles
* Permissions
* System Settings

---

## Development Workflow

### Branch Strategy

```text
main
 └── develop
      └── feature/*
```

### Feature Development

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

## Release Management

Every version must include:

* Git Tag
* Release Notes Document
* GitHub Release

Release Notes Location:

```text
docs/releases/
```

Examples:

```text
v0.1.0.md
v0.2.0.md
v0.2.1.md
v0.3.0.md
v0.4.0.md
```

---

## Repository Structure

```text
NSS_ERP
│
├── backend
├── database
├── docs
│   ├── standards
│   ├── modules
│   └── releases
│
├── frontend
│
└── README.md
```

---

## Current Stable Version

Current Stable Release:

```text
v0.4.0
```

Organization Module Frozen

---

## License

Internal NSS ERP Project

All rights reserved.
