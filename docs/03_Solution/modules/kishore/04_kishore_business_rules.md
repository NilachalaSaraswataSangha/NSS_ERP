# NSS ERP Kishore Puja Business Rules

Document ID: SOL-KIS-004
Status: DRAFT

---

# 1. Identity Rules

## KIS-001 — Kishore Identity
Every participant shall have a unique Kishore ID.

## KIS-002 — Kishore ID Permanence
System generated, unique, permanent, never reused, retained across years.

## KIS-003 — Kishore ID and Sangha Sevi ID
Separate identities. KH000123 is not SS000456.

---

# 2. Event Rules

## KIS-004 — Annual Event Model
Kishore Puja is an annual event/activity.

## KIS-005 — Event-Specific Registration
Participation recorded separately for each annual event.

## KIS-006 — Multi-Year Participation
Same Kishore ID participates across multiple years.

---

# 3. Sakha Rules

## KIS-007 — Sakha Association
Every registration must be associated with a Sakha.

## KIS-008 — Sakha Historical Integrity
Sakha per registration preserved. Allows year-wise Sakha reporting.

## KIS-009 — Sakha Visibility
Sakha views its own participants only.

## KIS-010 — Kendra Visibility
Kendra views all participants across Sakhas.

---

# 4. Registration Rules

## KIS-011 — Parent Nomination
Parent may nominate a boy.

## KIS-012 — Sakha Nomination
Sakha may nominate a boy.

## KIS-013 — Registration Ownership
Regardless of source, participant must be Sakha-associated.

---

# 5. Guardian Rules (Frozen)

## KIS-014 — Mandatory Guardian
Every participant must have an assigned Guardian.

## KIS-015 — Guardian Membership
Guardian must be an NSS Member of participant's Sakha.

## KIS-016 — Guardian Assignment Authority
Guardian is assigned by the Sakha.

## KIS-017 — Guardian Identity
guardian_sangha_sevi_pk references sangha_sevi.

## KIS-018 — Guardian Is Not Necessarily Parent
Operational Guardian is the assigned NSS Member.

## KIS-019 — Guardian Responsibilities
Guidance, Supervision, Participation Monitoring, Communication with Family, Support during events.

---

# 6. Family Rules

## KIS-020 — Family Integration
Participant may be associated with NSS Family.

## KIS-021 — Family Visibility
Family users view their own family's participants only.

## KIS-022 — Family Scope
Strictly restricted to user's own Family records.

---

# 7. Membership Rules

## KIS-026 — No Automatic Membership
Participation does not automatically create NSS Membership.

## KIS-027 — Membership Application
Participant may later apply for NSS Membership.

## KIS-028 — Membership Assessment
Follows Membership Module's approved process.

## KIS-029 — Membership Type
Membership Module determines resulting type.

## KIS-030 — Membership Transition
Preserves: Kishore ID + Sangha Sevi ID + Transition Date + Type Granted.

---

# 8. History and Audit

## KIS-031 — History Never Deleted
Participation history never physically deleted.

## KIS-032 — Identity Link Preservation
Kishore ID to Sangha Sevi ID link permanently traceable.

## KIS-036 — Auditability
Registration and Guardian assignment preserve audit info.

---

# 9. Frozen Principles

- Kishore Puja Is Annual Event Model
- Kishore ID Is Permanent
- Kishore ID is not Sangha Sevi ID
- Every Registration Belongs to a Sakha
- Every Participant Has Assigned Guardian
- Guardian Is NSS Member of Participant's Sakha
- Guardian Assigned by Sakha
- Parent and Sakha Nomination Supported
- Participation Does Not Create Membership
- Membership Transition Is Explicit
- History Never Deleted

---

# End of Document
