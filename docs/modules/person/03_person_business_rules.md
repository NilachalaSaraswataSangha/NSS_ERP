# NSS ERP Person Business Rules

Version: 1.0

Status: DRAFT

---

# 1. Purpose

Defines the business rules governing Person records in NSS ERP.

These rules take precedence over database implementation.

---

# 2. Core Principle

Person ≠ Member

A Person may exist without membership.

A Member must always be a Person.

---

# 3. Person Code Rule

Every Person shall have a unique Person Code.

Examples:

P00000001

P00000002

P00000003

Generated automatically.

Person Code is permanent.

Person Code shall never be reused.

---

# 4. Person Creation Rule

A Person may be created through:

Family Registration

Membership Application

Kumari Registration

Kishore Registration

Administrative Entry

Historical Data Migration

---

# 5. Name Rule

First Name is mandatory.

Middle Name is optional.

Last Name is optional.

Name changes must preserve audit history.

---

# 6. Gender Rule

Gender must be selected from master data.

Allowed values managed through:

gender_master

---

# 7. Date of Birth Rule

Date of Birth may be unknown for historical records.

Partial information may be supported in future versions.

---

# 8. Mobile Number Rule

One primary mobile number per Person.

Mobile number may be blank.

Mobile number is not required to be unique.

Example:

Family members may share a phone number.

---

# 9. Email Rule

One primary email address per Person.

Email is optional.

Email is not required to be unique.

---

# 10. Marital Status Rule

Marital status shall be maintained through master data.

Examples:

UNMARRIED

MARRIED

WIDOWED

DIVORCED

SEPARATED

---

# 11. Address Rule

A Person may have multiple addresses.

Examples:

PERMANENT

CURRENT

OFFICIAL

Address types managed through master data.

---

# 12. Duplicate Detection Rule

Before creating a new Person, the system should check:

Name

Date of Birth

Mobile Number

Email

Potential matches should be flagged for review.

---

# 13. Merge Rule

Duplicate Person records may be merged.

Merge operations must:

Preserve audit history

Preserve references

Maintain historical traceability

---

# 14. Membership Rule

Person records do not contain:

Sangha Sevi ID

Membership Status

Membership Type

These belong to the Membership Module.

---

# 15. Family Rule

Person records do not contain family relationships.

Family relationships belong to the Family Module.

---

# 16. Deletion Rule

Person records shall not be physically deleted.

Soft delete only.

Historical references must remain valid.

---

# 17. Audit Rule

All changes must capture:

Created By

Updated By

Deleted By

Timestamp

Reason

---

# 18. Privacy Rule

Sensitive identity documents shall not be stored in Person v1.

Examples:

Aadhaar

Passport

Voter ID

These will be handled by future Document Management modules.

---

# 19. Design Principles

Person First

Membership Separate

Family First

History Preserved

Audit Enabled

Soft Delete Enabled

Privacy Aware
