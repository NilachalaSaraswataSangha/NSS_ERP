# NSS ERP Kumari Sangha Table Design

Document ID: SOL-KUM-005
Status: DRAFT

---

# 1. Frozen Table Set

kumari_sangha
kumari_membership
kumari_activity
kumari_activity_participant
kumari_membership_transition

---

# 2. kumari_sangha

Purpose: Stores the Kumari Sangha organizational/program unit.

Main Columns:
kumari_sangha_pk, sakha_pk, name, status, formed_date, remarks, created_at, updated_at

---

# 3. kumari_membership

Purpose: Stores a Person's participation in a Kumari Sangha. Not an NSS Membership record.

Main Columns:
kumari_membership_pk, kumari_id, person_pk, kumari_sangha_pk, family_group_pk, status, joined_date, exit_date, exit_reason, years_of_participation, training_completed_flag, recommended_for_nss_membership_flag, recommended_membership_type, remarks, created_at, updated_at

Kumari ID Example: KM000001

Status Values: ACTIVE, MARRIED_OUT, BECAME_NSS_MEMBER, WITHDRAWN, DECEASED

---

# 4. kumari_activity

Purpose: Stores Kumari Sangha activities.

Main Columns:
kumari_activity_pk, kumari_sangha_pk, activity_type, activity_name, activity_date, start_date, end_date, description, status, remarks, created_at, updated_at

Activity Examples: Dina-Lipi, Niyam Panchak, Dasa Sheela, Training, Orientation

---

# 5. kumari_activity_participant

Purpose: Links Kumari participants to activities.

Main Columns:
kumari_activity_participant_pk, kumari_activity_pk, kumari_membership_pk, participation_status, participation_date, remarks, created_at, updated_at

---

# 6. kumari_membership_transition

Purpose: Stores transition from Kumari to NSS Membership.

Main Columns:
transition_pk, kumari_membership_pk, sangha_sevi_pk, transition_date, membership_type_granted, remarks, created_at

membership_type_granted: REGULAR or PROBATIONARY

---

# 7. Primary Key Standard

All tables use UUID internal primary keys.

---

# 8. Business Identifier

kumari_id (KM000123) — distinct from Sangha Sevi ID.
Not replaced after Membership transition.

---

# 9. Foreign Keys

person_pk, family_group_pk, kumari_sangha_pk, kumari_membership_pk, kumari_activity_pk, sangha_sevi_pk

All reference internal primary keys.

---

# 10. Audit Columns

created_at, created_by, updated_at, updated_by

---

# 11. Soft Delete

Physical deletion prohibited. Exit represented through status, exit_date, exit_reason.

---

# 12. Database Principles

- Kumari Participation is not NSS Membership
- Kumari ID is not Sangha Sevi ID
- Person Is Reused
- Family Is Reused
- Sakha Association Is Preserved
- Activities Are Historically Recorded
- Training History Is Preserved
- Membership Transition Is Explicit
- History Is Never Physically Deleted
- Auditability

---

# End of Document
