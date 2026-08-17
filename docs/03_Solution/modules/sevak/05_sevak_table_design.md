# NSS ERP Sevak Sangha Table Design

Document ID: SOL-SEV-005
Status: PARTIALLY FROZEN

---

# 1. Proposed Core Tables

sevak_sangha
sevak_membership
sevak_training_program
sevak_training_attendance
sevak_orientation_batch
sevak_activity
sevak_activity_participant

These are proposed, not yet final frozen PostgreSQL schema.

---

# 2. Common Foundation Reused

person, family_group, sangha_sevi, organization, body_master, body_member_assignment, position_master

---

# 3. sevak_sangha

Sevak Sangha organizational context.
Fields: sevak_sangha_pk, organization_pk, name, status, formed_date, remarks, created_at, created_by, updated_at, updated_by

---

# 4. sevak_membership

Participation in Sevak Sangha (NOT NSS Membership).
Fields: sevak_membership_pk, person_pk, sevak_sangha_pk, sangha_sevi_pk, start_date, end_date, status, participation_type, remarks, created_at, created_by, updated_at, updated_by

---

# 5. sevak_training_program

Training programs.
Fields: sevak_training_program_pk, sevak_sangha_pk, program_type, program_name, description, start_date, end_date, status, level, remarks, created_at, created_by, updated_at, updated_by

Types: ORIENTATION, SADACHARA, SEVA_TRAINING, UPBS_VOLUNTEER_TRAINING, LEADERSHIP_DEVELOPMENT

---

# 6. sevak_training_attendance

Training participation records.
Fields: sevak_training_attendance_pk, sevak_training_program_pk, sevak_membership_pk, attendance_date, attendance_status, remarks, created_at, created_by, updated_at, updated_by

---

# 7. sevak_orientation_batch

Orientation batches.
Fields: sevak_orientation_batch_pk, sevak_sangha_pk, batch_name, orientation_type, start_date, end_date, status, remarks, created_at, created_by, updated_at, updated_by

---

# 8. sevak_activity

Service and volunteer activities.
Fields: sevak_activity_pk, sevak_sangha_pk, activity_type, activity_name, activity_date, start_date, end_date, location_pk, status, description, remarks, created_at, created_by, updated_at, updated_by

---

# 9. sevak_activity_participant

Links participants to activities.
Fields: sevak_activity_participant_pk, sevak_activity_pk, sevak_membership_pk, participation_status, participation_date, remarks, created_at, created_by, updated_at, updated_by

---

# 10. Governance (Shared)

Uses body_master, body_member_assignment, position_master.
Body type: SEVAK_SANGHA_EXECUTIVE (provisional).

---

# 11. No Separate Sevak ID

No SV000001 identity frozen. Participant uses Person ID + Sangha Sevi ID where applicable.

---

# 12. Database Principles

- Person Shared, Membership Shared, Organization Shared, Governance Shared
- Training Is Module-Specific
- Activities Are Module-Specific
- UPBS Ops Are UPBS-Owned
- History Never Deleted
- Auditability
- Configuration Over Hardcoding

---

# 13. Schema Freeze Status

Core Concept: FROZEN
Proposed Table Set: WORKING
Training Hierarchy: PENDING
Executive Structure: PENDING
Age Criteria: PENDING
Certification: PENDING

Physical PostgreSQL schema finalized only after remaining decisions approved.

---

# End of Document
