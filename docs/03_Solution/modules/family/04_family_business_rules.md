# NSS ERP Family Business Rules

---

# Document Metadata

| Item | Value |
|---|---|
| Document Name | Family Business Rules |
| Document ID | SOL-FAM-003 |
| Domain | Family |
| Repository Path | docs/03_Solution/modules/family/04_family_business_rules.md |
| Version | 1.1.0 |
| Status | DRAFT |
| Parent Document | 01_family_module_overview.md |

---

# 1. Purpose

This document defines the business rules governing the NSS ERP Family Module.

## Revision Note — 1.1.0

Added section 22 (FAM-053 … FAM-057), the Family Authorization Model. These
rules were not previously written down; the implementation in
`api/routers/family.py` is gated on them, and the ownership path is covered by
`tests/api/test_family_ownership.py`.

The Repository Path above was also corrected — it read
`03_family_business_rules.md`, which is the lifecycle document's slot.

---

# 2. Family Identity Rules

## FAM-001 — Family Identity

Every registered NSS Family shall have a unique Family ID.

---

## FAM-002 — Family ID Permanence

Family ID shall be:

* System generated.
* Globally unique.
* Permanent.
* Never reused.
* Never changed.

---

# 3. Person and Family Rules

## FAM-003 — Person Independent of Membership

A Person may exist without Membership.

```text
Person is not equal to Member
```

---

## FAM-004 — Family May Contain Non-Members

A Family may contain Persons who are not NSS Members.

Examples:

* Spouse
* Child
* Guardian
* Kumari Participant
* Kishor Participant
* Future Applicant
* Historical Person

---

## FAM-005 — Person Data Ownership

Person identity information shall remain owned by the Person Module.

The Family Module shall reference Person records.

---

# 4. Family Relationship Rules

## FAM-006 — Relationship Ownership

Family relationships shall be maintained by the Family Module.

---

## FAM-007 — Controlled Relationship Types

Family relationship types shall be maintained through controlled master data where applicable.

Examples:

```text
FATHER
MOTHER
HUSBAND
WIFE
SON
DAUGHTER
```

---

## FAM-008 — Relationship History

Changes to important Family relationships shall preserve historical information where required.

---

# 5. Family Head Rules

## FAM-009 — Family Head

A Family may have a designated Family Head.

---

## FAM-010 — Family Head History

Changes to Family Head shall be historically recorded.

Historical Family Head assignments shall not be deleted.

---

# 6. Family Transition Rules

## FAM-011 — Family Transition

The ERP shall support Family transitions.

Examples:

* Marriage
* New Family Formation
* Change of Family Unit
* Other approved transitions

---

## FAM-012 — Transition History

Family transitions shall be stored in:

```text
family_transition_history
```

---

## FAM-013 — Historical Family Preservation

A previous Family shall remain historically traceable after a transition.

The system shall not destroy the old Family record merely because a Person joins a new Family.

---

# 7. Marriage Rules

## FAM-014 — Marriage Transition

Marriage may result in the formation of a new Family Group.

Example:

```text
Original Family
    |
Marriage
    |
New Family
```

---

## FAM-015 — Historical Link

The new Family shall maintain a historical relationship with the previous Family where applicable.

---

## FAM-016 — Person Reuse

The ERP shall not create a duplicate Person record merely because the Person changes Family.

The existing Person record shall continue to be used.

---

# 8. Membership Relationship Rules

## FAM-017 — Membership Ownership

Membership information shall remain owned by the Membership Module.

---

## FAM-018 — Family Membership View

The Family Module may display Membership information for family members.

Displayed information may include:

```text
Sangha Sevi ID
Membership Type
Membership Status
```

---

## FAM-019 — No Duplicate Membership

Family shall not create a separate Family Membership ID.

The authoritative Membership identity remains the Sangha Sevi ID.

---

# 9. Youth Program Rules

## FAM-020 — Kumari Visibility

Authorized Family users may view relevant Kumari participation information for members of their own Family.

---

## FAM-021 — Kishor Visibility

Authorized Family users may view relevant Kishor participation information for members of their own Family.

---

## FAM-022 — Future Youth Programs

The Family visibility model shall be extensible to future youth programs.

---

## FAM-023 — Family Access Scope

Family users shall only access authorized records belonging to their own Family.

The project explicitly froze this restriction.

---

# 10. Family Visibility Rules

## FAM-024 — Participation Information

Where authorized, Family users may view:

* Participant Details
* Registration Details
* Activity History
* Training History
* Participation Status
* Assigned Guardian
* Membership Transition Status

---

## FAM-025 — Data Ownership

Family visibility shall aggregate information from the authoritative module.

The Family Module shall not duplicate the complete source records of:

* Membership
* Kumari
* Kishor
* Mahila
* Attendance

---

# 11. Family Dashboard Rules

## FAM-026 — Family Dashboard

The Family Dashboard shall provide:

```text
Family Information

Family Members

Membership Summary

Kumari Participation

Kishor Participation

Family Activities

Family Tree

Family Transition History
```

---

# 12. Family History Rules

## FAM-027 — History Preservation

Family history shall be preserved.

---

## FAM-028 — No Physical Deletion

Physical deletion of historical Family relationships or transitions is prohibited.

---

# 13. Audit Rules

## FAM-029 — Auditability

Family actions shall preserve applicable:

```text
Created By
Created At
Updated By
Updated At
```

---

## FAM-030 — Historical Traceability

Family changes shall remain traceable throughout the lifecycle.

---

# 14. Module Boundary Rules

## FAM-031 — Person Boundary

Person identity belongs to Person Module.

---

## FAM-032 — Membership Boundary

Membership identity belongs to Membership Module.

---

## FAM-033 — Kumari Boundary

Kumari participation belongs to Kumari Module.

---

## FAM-034 — Kishor Boundary

Kishor participation and guardian assignment belong to Kishor Module.

---

## FAM-035 — Mahila Boundary

Mahila participation belongs to Mahila Module.

---

# 15. Frozen Family Principles

```text
Family First Model

Person is not equal to Member

Family is not equal to Membership

Family May Contain Members and Non-Members

Family ID Permanent

Family ID Never Reused

Family Head History Preserved

Family Transition History Preserved

Marriage Transition Preserved

No Duplicate Person Records

Youth Visibility Restricted to Authorized Family

Family History Never Physically Deleted
```

---

# 16. Sakha Alignment Rules (Operational Convention)

## FAM-036 — Family-Sakha Majority Rule (Dynamic)

A family belongs to the Sakha where the majority of its members hold
active affiliation (via ``membership_sakha_affiliation``).

```text
Family Effective Sakha = Sakha with most active member affiliations
```

This is computed dynamically on every read — there is no manual
assignment or hardcoded Sakha on the family record.  The
``family_group.sakha_organization_pk`` column stores the registration
Sakha at creation time and serves as a fallback when no members have
affiliations.  The API overrides it with the computed majority via a
CTE in every family query.

When the majority shifts (e.g. a member transfers), the family
automatically appears under the new Sakha in org navigation — no
manual update is required.

**Rule maturity:** ERP-OPERATIONAL

---

## FAM-037 — Cross-Sakha Family Members

A family may contain members affiliated with different Sakhas.

Example: A family assigned to Sakha A may include members whose
Parichaya Patra was issued by Sakha B or Sakha C.  Those members
appear in the family tree and are full family members; only their
individual Sakha affiliation differs.

The ERP shall display a visual mismatch indicator (warning badge)
when a member's active Sakha affiliation differs from the family's
assigned home Sakha.

---

## FAM-038 — Family Split Principle

Members from a minority Sakha within a family may create their own
family.  The new family's Sakha is determined by the same majority
principle (FAM-036).

```text
Original Family (Sakha A: 3 members, Sakha B: 2 members)
    |
Split
    |
Family 1 (Sakha A: 3 members)
Family 2 (Sakha B: 2 members)
```

---

# 17. Relationship Model Rules

## FAM-039 — Graph-Based Dynamic Relationships

Family relationships are computed dynamically via BFS graph
traversal, not stored as static labels.

The ``family_link`` table stores only two edge types:

```text
PARENT_OF
SPOUSE_OF
```

All other kinship labels (Father, Mother, Uncle, Aunt, Grandson,
Cousin, etc.) are derived at query time relative to a viewer.
Changing the viewer recomputes all labels without any data changes.

**Rationale:** Static HEAD-relative labels (e.g. ``SON_OF_HEAD``)
break when the head changes or when viewing from a non-head
perspective.  The graph model is viewer-independent.

---

## FAM-040 — Dual-View Family Navigation

The family UI provides two views:

1. **Member View ("My Family"):** A family member sees their own
   family tree, detail panel, and "View As" selector.

2. **Org Admin View ("Org View"):** An administrator navigates the
   organizational hierarchy (Kendra -> Anchalika -> Sakha) to browse
   families under a selected Sakha.

Both views share the same family detail panel, tree rendering, and
person selection.  The difference is only in how families are
discovered (direct access vs. org drill-down).

---

# 18. Document Visibility Rules

## FAM-041 — Parichaya Patra Visibility

Parichaya Patra (identity card) is displayed for all membership
types.

```text
NSS.showParichayaPatra(typeCode) -> true  (all types)
```

---

## FAM-042 — Anumati Patra Visibility

Anumati Patra (permission letter) is displayed for Darshaka
(PROBATIONARY) members only.  It is hidden for Associate (ASSOCIATE)
members.

```text
NSS.showAnumatiPatra(typeCode) -> typeCode !== "ASSOCIATE"
```

**Authority:** MBR-019A/B (membership document rules)

---

# 19. Identity Display Rules

## FAM-043 — Three-Tier Identity Display

The ERP uses a three-tier identity hierarchy displayed with
consistent styling across all pages:

```text
Tier 1: Sangha Sevi ID    (primary / blue)      .data-sevi-id
Tier 2: Sakha Sangha ID   (secondary / purple)   .data-erp-no
Tier 3: Kendra Number     (accent)                .data-kendra-no
```

The label "Sangha Sevi ID" is authoritative.  Shortened forms
("Sevi ID") are prohibited.

---

## FAM-044 — Membership Type Terminology

The membership type "Darshaka" is the authoritative NSS term for
probationary members.  The label "Probationary Member" shall not
appear in user-facing UI.

---

# 20. Authority Hierarchy

Family implementation shall follow:

```text
NSS Bye-Law / Authoritative References
        |
Approved Governance Decisions
        |
Approved Family Business Rules
        |
Solution Design
        |
Implementation
```

Where an authoritative source does not define an implementation detail, the project decision shall be explicitly treated as an ERP implementation decision.

---

# 21. Family Admin Rules

## FAM-045 — Family Admin Role

A Family may have one or more designated Family Admins.

Family Admin is a distinct concept from Family Head.  A person may
be both Head and Admin, but the two roles are independent.

```text
Head ≠ Admin
Head may also be Admin
Admin may not be Head (unless separately designated)
```

---

## FAM-046 — Family Admin Appointment

Only the current Family Head may appoint or remove Family Admins.

The "Assign Admin" and "Revoke Admin" actions shall be visible
only to the current Family Head in the Family dashboard.

---

## FAM-047 — Family Admin Self-Assignment

The Family Head may assign themselves as Family Admin.

---

## FAM-048 — Family Admin Privileges

Family Admin may perform the following actions that regular
family members cannot:

```text
Edit family details (family name, remarks)
Add members to the family
Remove members from the family
View family financial records
```

> **Implementation note (as of the Tier 5):** the shipped
> `api/routers/family.py` does not yet match this rule exactly. `DELETE
> /families/{pk}/members` (`remove_family_member`) correctly restricts to Head-or-Admin,
> per FAM-048. But `POST /families/{pk}/members` (`add_family_member`) only checks that the
> requester is a *current member* of the family — any member can add members today, not just
> Head/Admin, contradicting the "Add members" bullet above. There is also no `PATCH
> /families/{pk}` endpoint at all yet, so "Edit family details" and "View family financial
> records" are entirely unimplemented (no financial-records table/endpoint exists in this
> module either). Flagging rather than resolving — whether to tighten `add_family_member`'s
> authorization or loosen this rule is a product decision, not a docs fix.

---

## FAM-049 — Family Head Transfer

The current Family Head may transfer headship to another
family member using the "Make Head" action.

On transfer:
1. The current head's `family_head_history` record is closed
   (effective_to = today)
2. A new `family_head_history` record is created for the
   new head (effective_from = today)
3. The previous head does NOT automatically lose Admin role
   (if they had one)

---

## FAM-050 — Family Head Exclusive Actions

Only the Family Head may perform:

```text
Make Head (transfer headship)
Assign Admin
Revoke Admin
```

Family Admins cannot perform these actions unless they are also
the Head.

---

## FAM-051 — One Head per Family

A family shall have exactly one current Head at any time.

This is enforced by the partial unique index on
`family_head_history(family_group_pk) WHERE effective_to IS NULL`.

---

## FAM-052 — Family Admin History

Family Admin assignments shall be historically recorded.
Revoked admin records shall retain effective_from and
effective_to for audit traceability.

---

# 22. Family Authorization Model

## FAM-053 — Family Authority Derives from Relationship, Not Permission

Authority over a family shall derive from a person's **relationship** to that
family — Head, Family Admin, or Member — and not from a system-wide RBAC
permission.

Rationale, and why this rule is stated explicitly:

An ordinary Sangha Sevi holds **no role**. The nine seeded roles
(`database/seed/00_bootstrap/02_role_master.sql`) are all administrative:
three SYSTEM roles and six ORGANIZATIONAL roles. Registration creates a
`user_account` in `PENDING_APPROVAL` with no role; claim approval creates the
`sangha_sevi` row and affiliation and flips the account to `ACTIVE` — still
with no role. The only place the API inserts into `nss.user_role` is manual
assignment by an administrator.

Therefore an ordinary member's permission set is **empty**. Gating the family
endpoints on `FAMILY_VIEW` / `FAMILY_MANAGE` alone would lock every ordinary
member out of their own family tree. Ownership is the only mechanism that can
admit them.

---

## FAM-054 — FAMILY_VIEW / FAMILY_MANAGE Are the Organisational Override

`FAMILY_VIEW` and `FAMILY_MANAGE` shall not be the primary gate on
family-scoped operations. They shall act as the **organisational override**
that allows an administrator to reach families they do not belong to — the
org-level family browser.

`FAMILY_MANAGE` shall additionally satisfy the Head-only rules (FAM-046,
FAM-050) so that a family whose Head is lost — deceased, departed, account
disabled — is not permanently unable to appoint a successor.

---

## FAM-055 — Authorization Matrix

| Operation | Required authority |
|---|---|
| View one family — detail, members, head history, graph, admin list, Sakha alignment | Current **member** of that family, or `FAMILY_VIEW` |
| View a person's family list / membership summary | **Self**, a current **relative** (shares a current family), or `FAMILY_VIEW` |
| Browse **all** families (org-level browser) | `FAMILY_VIEW` only — "all families" is nobody's own family |
| Create a family | Any authenticated member (self-service; see FAM-056) |
| Add member, remove member, create family link | That family's **Head or Family Admin**, or `FAMILY_MANAGE` |
| Appoint / revoke a Family Admin, transfer headship | That family's **Head** only, or `FAMILY_MANAGE` |

Two consequences are deliberate and must not be softened:

* Being **merely a member** is not sufficient to change membership. A member
  can see their family; they cannot alter who is in it.
* A **Family Admin cannot appoint further admins or transfer headship.** Those
  remain Head-exclusive (FAM-046, FAM-050), so admin authority cannot be used
  to escalate itself.

The relative case in row 2 is required, not a convenience: the member
dashboard fetches a membership summary for every person in the viewer's own
family tree. A self-only check would break the tree panel.

---

## FAM-056 — Family Creation Is Self-Service

Creating a family shall require authentication only. It shall not require
`FAMILY_MANAGE`.

There is no existing family for an ownership check to consult at the moment of
creation — the caller becomes the founding member and the first Head by the
act of creating it. Requiring an administrative permission here would mean no
member could ever form their own family unit, which FAM-011 and FAM-014
(marriage resulting in the formation of a new Family Group) require the system
to support.

---

## FAM-057 — Caller-Supplied Identifiers Are Never the Authorization Subject

Where an endpoint accepts a person identifier as input — for example the
`viewer_person_pk` query parameter on the family graph endpoint, which selects
whose perspective kinship labels are computed from — that identifier shall
serve presentation only. Authorization shall always be evaluated against the
authenticated identity carried by the token.

---

# 23. Frozen Family Admin Principles

```text
Head and Admin are independent roles

Head may also be Admin

One Head per family at any time

Multiple Admins per family allowed

Only Head can appoint/remove Admins

Only Head can transfer headship

Admin can edit family, add/remove members, view financials

Head transfer does not revoke previous head's Admin role

Admin history preserved (never physically deleted)

Authority comes from relationship, not from RBAC permission

An ordinary member holds no role and no permission

A member may view their own family but not change its membership

FAMILY_VIEW / FAMILY_MANAGE are the organisational override only

Family creation requires authentication only
```

---
