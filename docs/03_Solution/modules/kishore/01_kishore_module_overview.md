# NSS ERP Kishore Puja Module Overview

Version: 1.0
Status: DRAFT

---

# 1. Purpose

The Kishore Puja Module manages Kishore participants, Kishore identity, annual Kishore Puja events, registration, Sakha association, Guardian assignment, year-wise participation, participation history, and transition to NSS Membership.

Kishore Puja is modeled as an annual NSS event/activity for boys.
It is not a permanent organizational unit like Kumari Sangha.

---

# 2. Core Principle

Kishore Puja Participation is not equal to NSS Membership.
A Kishore participant may participate without being an NSS Member.

---

# 3. Kishore Identity

Every Kishore participant receives a Kishore ID. Examples: KH000001, KH000002.
The ID is: Unique, Permanent, Never Reused, Retained across years.
Kishore ID is separate from Sangha Sevi ID.

---

# 4. Annual Event Model

Kishore Puja is annual. A participant may participate in multiple years using the same Kishore ID.

---

# 5. Guardian Model (Frozen)

Every Kishore participant must have an assigned Guardian.
Guardian must be an NSS Member of the participant's Sakha.
Guardian is assigned by the Sakha.
Guardian is not necessarily the parent.

---

# 6. Registration Sources

Parent Nomination or Sakha Nomination. Both result in Sakha-associated registration.

---

# 7. Membership Transition

A Kishore participant may later apply for NSS Membership.
KH000123 -> Application -> Assessment -> Approval -> SS000456.
Kishore ID remains unchanged. Both identities linked.

---

# 8. Frozen Table Set

kishore_participant, kishore_event, kishore_event_registration, kishore_membership_transition

---

# 9. Frozen Decisions

- Kishore Puja is an annual event/activity.
- Not a permanent organizational unit like Kumari Sangha.
- Every participant receives a Kishore ID (permanent, never reused).
- Kishore ID is separate from Sangha Sevi ID.
- Every registration is associated with a Sakha.
- Every participant must have an assigned Guardian.
- Guardian must be NSS Member of participant's Sakha.
- Guardian assigned by Sakha.
- Parent and Sakha nomination supported.
- Participation does not automatically create NSS Membership.
- History is never physically deleted.

---

# End of Document
