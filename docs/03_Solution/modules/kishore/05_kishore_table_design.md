# NSS ERP Kishore Puja Table Design

Document ID: SOL-KIS-005
Status: DRAFT

---

# 1. Frozen Table Set

kishore_participant
kishore_event
kishore_event_registration
kishore_membership_transition

---

# 2. kishore_participant

Purpose: Stores permanent Kishore identity.

Main Columns:
kishore_participant_pk, kishore_id, person_pk, family_group_pk, guardian_sangha_sevi_pk, assigned_by_sakha_pk, guardian_assigned_date, registration_date, status, created_at, updated_at

Kishore ID Example: KH000001
Status: System generated, unique, permanent, never reused.

---

# 3. kishore_event

Purpose: Stores an annual Kishore Puja event.

Main Columns:
kishore_event_pk, event_name, financial_year, event_date, registration_start_date, registration_end_date, host_organization_pk, status, remarks, created_at, updated_at

Examples: Kishore Puja 2026, Kishore Puja 2027, Kishore Puja 2028

---

# 4. kishore_event_registration

Purpose: Stores a participant's registration for a specific annual event.

Main Columns:
registration_pk, kishore_participant_pk, kishore_event_pk, sakha_pk, guardian_sangha_sevi_pk, registration_source, registration_date, status, participation_status, remarks, created_at, updated_at

Registration Source: PARENT_NOMINATION, SAKHA_NOMINATION

Sakha on registration: Preserves year-specific Sakha association.

Participation Status examples: REGISTERED, CONFIRMED, PARTICIPATED, ABSENT, CANCELLED

---

# 5. kishore_membership_transition

Purpose: Stores transition from Kishore to NSS Membership.

Main Columns:
transition_pk, kishore_participant_pk, sangha_sevi_pk, transition_date, membership_type_granted, remarks, created_at, created_by

membership_type_granted: REGULAR or PROBATIONARY

Example: KH000123 -> SS000456

---

# 6. Guardian Model

guardian_sangha_sevi_pk references sangha_sevi (NSS Member).
Guardian must belong to participant's Sakha.
assigned_by_sakha_pk identifies assigning Sakha.
guardian_assigned_date records effective date.

---

# 7. Primary Key Standard

All tables use UUID internal primary keys.

---

# 8. Business Identifier

kishore_id (KH000123) — distinct from Sangha Sevi ID.
Not replaced after Membership transition.

---

# 9. Foreign Keys

person_pk, family_group_pk, guardian_sangha_sevi_pk, assigned_by_sakha_pk, kishore_participant_pk, kishore_event_pk, sakha_pk, sangha_sevi_pk

All reference internal primary keys.

---

# 10. Audit Columns

created_at, created_by, updated_at, updated_by

---

# 11. History

Never physically deleted: Kishore Identity, Annual Registration, Sakha Association, Guardian Assignment, Participation History, Membership Transition.

---

# 12. Database Principles

- Kishore Puja Is Annual/Event Based
- Kishore ID Is Permanent
- Kishore ID is not Sangha Sevi ID
- Registration Is Event Specific
- Sakha Association Is Preserved
- Guardian Is an NSS Member
- Guardian Is Sakha Assigned
- Membership Transition Is Explicit
- History Is Never Deleted
- Auditability

---

# End of Document
