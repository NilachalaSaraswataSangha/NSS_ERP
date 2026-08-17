# NSS ERP Sevak Sangha ERD

Document ID: SOL-SEV-002
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

Subject to final operational validation.

---

# 2. Logical ERD

```mermaid
erDiagram
    PERSON ||--o{ SEVAK_MEMBERSHIP : participates
    SEVAK_SANGHA ||--o{ SEVAK_MEMBERSHIP : contains
    SEVAK_SANGHA ||--o{ SEVAK_TRAINING_PROGRAM : conducts
    SEVAK_TRAINING_PROGRAM ||--o{ SEVAK_TRAINING_ATTENDANCE : records
    SEVAK_MEMBERSHIP ||--o{ SEVAK_TRAINING_ATTENDANCE : attends
    SEVAK_SANGHA ||--o{ SEVAK_ORIENTATION_BATCH : conducts
    SEVAK_SANGHA ||--o{ SEVAK_ACTIVITY : conducts
    SEVAK_ACTIVITY ||--o{ SEVAK_ACTIVITY_PARTICIPANT : has
    SEVAK_MEMBERSHIP ||--o{ SEVAK_ACTIVITY_PARTICIPANT : participates
    SANGHA_SEVI ||--o{ BODY_MEMBER_ASSIGNMENT : serves
```

---

# 3. Common Tables Reused

person, family_group, sangha_sevi, organization, body_master, body_member_assignment, position_master

---

# 4. Key Relationships

- Person to Sevak Membership (participation, not NSS Membership)
- Sevak Sangha to Training Programs (1 to many)
- Sevak Sangha to Activities (1 to many)
- Governance via common body_member_assignment

---

# 5. Data Ownership

| Data | Owner |
|------|-------|
| Person | Person Module |
| Family | Family Module |
| NSS Membership | Membership Module |
| Sevak Participation | Sevak Module |
| Training | Sevak Module |
| Service Activity | Sevak Module |
| Governance | Governance Module |
| UPBS Volunteer | UPBS Module |

---

# 6. ERD Status

Foundation: APPROVED
Operational Design: PARTIALLY FROZEN

---

# End of Document
