# NSS ERP Kumari Sangha Module Overview

Version: 1.0
Status: DRAFT

---

# 1. Purpose

The Kumari Sangha Module manages Kumari Sangha participants, Kumari identity, Sakha association, family integration, activities, training, participation history, and transition to NSS Membership.

Kumari Sangha is a separate organizational/developmental institution and is not an NSS Membership category.

---

# 2. Core Principle

Kumari Participation is not equal to NSS Membership.

A Kumari participant may exist in the ERP without being an NSS Member.
A Kumari participant does not automatically receive a Sangha Sevi ID.

---

# 3. Kumari Identity

Every Kumari participant shall receive a separate Kumari ID.
Examples: KM000001, KM000002, KM000003

The Kumari ID is: Unique, Permanent, Never Reused, Valid within the Kumari Sangha context.
The Kumari ID is distinct from the NSS Sangha Sevi ID.

---

# 4. Frozen Table Baseline

kumari_sangha
kumari_membership
kumari_activity
kumari_activity_participant
kumari_membership_transition

---

# 5. Activities

Kumari activities include: Dina-Lipi, Niyam Panchak, Dasa Sheela, Training, Orientation.

---

# 6. Membership Transition

A Kumari participant may later become an NSS Member (Regular or Probationary).
The transition is explicit and recorded. Both identities remain preserved.

---

# 7. Marriage Rule

Only unmarried girls may remain active participants. After marriage: status becomes MARRIED_OUT.

---

# 8. Kumari Status Values

ACTIVE, MARRIED_OUT, BECAME_NSS_MEMBER, WITHDRAWN, DECEASED

---

# 9. Frozen Decisions

- Kumari Sangha is separate from NSS Membership.
- Every Kumari participant receives a Kumari ID.
- Kumari ID is separate from Sangha Sevi ID.
- Sangha Sevi ID is generated only after NSS Membership approval.
- Kumari history is preserved after Membership transition.
- Marriage is an explicit Kumari exit condition.
- Family integration uses the existing Person and Family foundation.
- Physical deletion of Kumari history is prohibited.

---

# End of Document
