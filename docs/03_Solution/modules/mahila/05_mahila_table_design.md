# NSS ERP Mahila Sangha Table Design

Document ID: SOL-MAH-005
Status: DRAFT

---

# 1. Architectural Principle

Mahila Module reuses common foundations. Does not duplicate: Person, Membership, Sangha Sevi, Family, Organization, Governance.

---

# 2. Common Tables Reused

person, family_group, family_relationship, sangha_sevi, organization, body_master, body_member_assignment, position_master

---

# 3. Module-Specific Tables

mahila_participation
mahila_activity
mahila_activity_participant

---

# 4. mahila_participation

Purpose: Records Member's Mahila Sangha association.

Main Columns:
mahila_participation_pk, sangha_sevi_pk, mahila_organization_pk, sakha_pk, start_date, end_date, status, remarks, created_at, created_by, updated_at, updated_by

---

# 5. mahila_activity

Purpose: Stores Mahila-specific activities.

Main Columns:
mahila_activity_pk, mahila_organization_pk, activity_type, activity_name, activity_date, start_date, end_date, status, description, remarks, created_at, created_by, updated_at, updated_by

---

# 6. mahila_activity_participant

Purpose: Links NSS Member to Mahila activity.

Main Columns:
mahila_activity_participant_pk, mahila_activity_pk, sangha_sevi_pk, participation_status, participation_date, remarks, created_at, created_by

---

# 7. Governance (Shared)

Body type: MAHILA_PARICHALANA_MANDALI in body_master.
Assignments via body_member_assignment.
Positions via position_master.

---

# 8. Organization (Shared)

Org types: MAHILA_SANGHA in organization_type_master.
Exists in common organization table.

---

# 9. No Separate Membership Table

No mahila_membership table. Membership is sangha_sevi.

---

# 10. No Separate Mahila ID

No separate Mahila Membership identifier. Sangha Sevi ID is authoritative.

---

# 11. Database Principles

- Person Is Shared
- Family Is Shared
- Membership Is Shared
- Organization Is Shared
- Governance Is Shared
- Mahila Participation Is Separate
- Mahila Activities Are Separate
- History Never Deleted
- Auditability
- Master Data Driven

---

# End of Document
