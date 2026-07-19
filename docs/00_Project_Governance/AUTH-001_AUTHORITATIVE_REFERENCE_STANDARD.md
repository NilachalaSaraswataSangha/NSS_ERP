# AUTH-001 — Authoritative Reference Repository Standard

---

## Document Metadata

| Item | Value |
|------|-------|
| Document Name | Authoritative Reference Repository Standard |
| Document ID | AUTH-001 |
| Repository Path | docs/01_Authoritative_References/ |
| Version | 1.0.0 |
| Status | Approved |
| Authority | NSS ERP Documentation Governance |
| Owner | NSS ERP Documentation Team |
| Applies To | All Authoritative Reference (REF) Documents |
| Effective Date | 2026-07-19 |

---

# Revision History

| Version | Date | Author | Description |
|----------|------|--------|-------------|
| 1.0.0 | 2026-07-19 | NSS ERP Documentation Team | Initial repository standard |

---

# Table of Contents

1. Purpose
2. Scope
3. Guiding Principles
4. Repository Architecture
5. Folder Structure
6. REF Family Structure
7. Official Bye-Law Mapping
8. Document Identification Standard
9. File Naming Standard
10. Folder Naming Standard
11. REF Document Creation Rules
12. Metadata Standard
13. Traceability Standard
14. Cross Reference Standard
15. Source Authority
16. Verification Requirements
17. Editorial Standards
18. Repository Governance
19. Future Expansion
20. Compliance Requirements
21. Appendix A – REF Family Mapping
22. Appendix B – Repository Structure
23. Appendix C – File Naming Examples

---

# 1. Purpose

This document establishes the governing standards for the Authoritative Reference Repository used by the NSS ERP Project.

The objective is to ensure that every constitutional and Bye-Law reference document is:

- Accurate
- Traceable
- Maintainable
- Consistent
- Version controlled
- Directly mapped to the officially approved Constitution and Bye-Laws.

This document serves as the governing standard for all REF documents maintained within the repository.

---

# 2. Scope

This standard applies to:

- Repository organization
- Folder hierarchy
- REF document families
- Document identifiers
- File names
- Cross references
- Traceability
- Verification
- Future additions

---

# 3. Guiding Principles

The Authoritative Reference Repository shall follow the following principles.

## GP-001

The official Constitution and Bye-Laws are the primary governing authority.

## GP-002

REF documents are repository reference documents.

They shall never replace, reinterpret or supersede the official governing documents.

## GP-003

Every REF document shall preserve the official legal structure.

## GP-004

Official section lettering and numbering shall never be modified.

## GP-005

Repository identifiers shall exist only to organize documentation.

They shall not alter the legal meaning of any provision.

---

# 4. Repository Architecture

```
docs/
└── 01_Authoritative_References/
```

The repository is organized according to the official Constitution and Bye-Law sections.

Each official section has its own folder.

Each official section has its own REF family.

---

# 5. Folder Structure

```
docs/
└── 01_Authoritative_References/
    ├── AUTH-001_AUTHORITATIVE_REFERENCE_STANDARD.md
    ├── SECTION-A_PRELIMINARY_AND_GENERAL_PROVISIONS/
    ├── SECTION-B_MEMBERSHIPS/
    ├── SECTION-C_CONSTITUTION_OF_THE_KENDRA_SANGHA/
    ├── SECTION-D_ADVISORY_BOARD/
    ├── SECTION-E_GENERAL_BODY/
    ├── SECTION-F_FUNDS_OF_THE_KENDRA_SANGHA/
    ├── SECTION-G_ACCOUNTS_AND_AUDIT/
    ├── SECTION-H_POWER_TO_AMEND/
    ├── SECTION-I_DISSOLUTION/
    └── SECTION-J_RESOLUTIONS/
```

No intermediate grouping folders shall exist.

---

# 6. REF Family Structure

Each official Bye-Law section is assigned one REF family.

| REF Family | Official Section |
|------------|------------------|
| REF-001 | Section A |
| REF-002 | Section B |
| REF-003 | Section C |
| REF-004 | Section D |
| REF-005 | Section E |
| REF-006 | Section F |
| REF-007 | Section G |
| REF-008 | Section H |
| REF-009 | Section I |
| REF-010 | Section J |

These identifiers are permanent.

REF family numbers shall never be reused.

---

# 7. Official Bye-Law Mapping

Repository organization mirrors the official Constitution and Bye-Law structure exactly.

The repository shall never introduce alternative numbering systems.

Official section references shall always be used.

Examples:

```
A
B
C
C(1)
C(2)
F(a)
F(b)
F(c)
J
```

---

# 8. Document Identification Standard

Each REF document has two identifiers.

## Repository Identifier

Example

```
REF-006
```

This identifies the repository document family.

---

## Official Reference

Example

```
F(c)
```

This identifies the official legal provision.

---

Combined identifier

```
REF-006-F(c)
```

---

# 9. File Naming Standard

Every REF document shall use the following format.

```
REF-XXX-<Official Reference>_<DOCUMENT_NAME>.md
```

Examples

```
REF-001-A_NSS_CONSTITUTION.md

REF-002-B_MEMBERSHIP_BYLAWS.md

REF-003-C(1)_GOVERNING_BODY.md

REF-003-C(2)_FUNCTIONS_OF_THE_GOVERNING_BODY.md

REF-003-C(3)_DUTIES_OF_THE_PRESIDENT.md

REF-006-F(a)_FUNDS_OF_THE_KENDRA_SANGHA.md

REF-006-F(b)_MAINTENANCE_OF_THE_FUNDS.md

REF-006-F(c)_UTILISATION_OF_THE_FUNDS.md

REF-010-J_ADDITIONAL_RESOLUTIONS_1975.md
```

Official Bye-Law references shall be preserved exactly.

Parentheses shall not be removed or substituted.

---

# 10. Folder Naming Standard

Folders shall use the following convention.

```
SECTION-<LETTER>_<SECTION_NAME>
```

Example

```
SECTION-F_FUNDS_OF_THE_KENDRA_SANGHA
```

---

# 11. REF Document Creation Rules

REF documents shall only be created for provisions containing substantive constitutional, legal, procedural, explanatory or governing content.

Headings used solely as organizational containers shall not receive standalone REF documents.

Example

Official Bye-Law

```
F

(a)

(b)

(c)
```

Repository

```
REF-006-F(a)

REF-006-F(b)

REF-006-F(c)
```

No standalone

```
REF-006-F
```

shall exist unless the official Bye-Law contains substantive content directly under Section F.

---

# 12. Metadata Standard

Every REF document shall contain:

- Document Metadata
- Repository Path
- Document ID
- Official Bye-Law Reference
- Source Reference
- Version
- Status
- Revision History
- Authority
- Verification
- Related References
- Document Authority

---

# 13. Traceability Standard

Every REF document shall be traceable to:

- Official Constitution
- Official Bye-Laws
- Repository location
- Official legal reference

No repository document shall exist without traceability.

---

# 14. Cross Reference Standard

Cross references shall use both

- Official Bye-Law reference

and

- REF document identifier.

Example

```
Section C(2)

REF-003-C(2)_FUNCTIONS_OF_THE_GOVERNING_BODY.md
```

---

# 15. Source Authority

The official Constitution and Bye-Laws remain the governing authority.

REF documents are maintained solely for repository reference purposes.

Where ambiguity, inconsistency or conflict exists, the officially approved Constitution and Bye-Laws shall prevail.

---

# 16. Verification Requirements

Every REF document shall be verified against the official governing document before approval.

Verification shall confirm:

- Section reference
- Numbering
- Text
- Formatting
- Cross references

---

# 17. Editorial Standards

Editorial additions shall never alter legal meaning.

Editorial material may include:

- Introductions
- Metadata
- Traceability
- Repository notes
- Cross references

Official legal wording shall remain unchanged.

---

# 18. Repository Governance

Changes affecting repository organization require:

- Documentation review
- Repository impact assessment
- Approval through NSS ERP documentation governance

---

# 19. Future Expansion

New REF families shall only be created when official governing documents introduce additional sections.

Existing REF families shall never be renumbered or reassigned.

---

# 20. Compliance Requirements

All contributors shall comply with this standard.

Non-compliant REF documents shall be corrected before approval.

---

# Appendix A – REF Family Mapping

| REF | Official Section |
|------|------------------|
| REF-001 | A |
| REF-002 | B |
| REF-003 | C |
| REF-004 | D |
| REF-005 | E |
| REF-006 | F |
| REF-007 | G |
| REF-008 | H |
| REF-009 | I |
| REF-010 | J |

---

# Appendix B – Repository Structure

```
docs/
└── 01_Authoritative_References/
    ├── AUTH-001_AUTHORITATIVE_REFERENCE_STANDARD.md
    ├── SECTION-A_PRELIMINARY_AND_GENERAL_PROVISIONS/
    ├── SECTION-B_MEMBERSHIPS/
    ├── SECTION-C_CONSTITUTION_OF_THE_KENDRA_SANGHA/
    ├── SECTION-D_ADVISORY_BOARD/
    ├── SECTION-E_GENERAL_BODY/
    ├── SECTION-F_FUNDS_OF_THE_KENDRA_SANGHA/
    ├── SECTION-G_ACCOUNTS_AND_AUDIT/
    ├── SECTION-H_POWER_TO_AMEND/
    ├── SECTION-I_DISSOLUTION/
    └── SECTION-J_RESOLUTIONS/
```

---

# Appendix C – File Naming Examples

```
REF-001-A_NSS_CONSTITUTION.md

REF-002-B_MEMBERSHIP_BYLAWS.md

REF-003-C(1)_GOVERNING_BODY.md

REF-003-C(2)_FUNCTIONS_OF_THE_GOVERNING_BODY.md

REF-003-C(3)_DUTIES_OF_THE_PRESIDENT.md

REF-003-C(4)_DUTIES_OF_THE_VICE_PRESIDENT.md

REF-003-C(5)_DUTIES_OF_THE_SECRETARY.md

REF-003-C(6)_DUTIES_OF_THE_ASSISTANT_SECRETARY.md

REF-003-C(7)_DUTIES_OF_THE_TREASURER.md

REF-003-C(8)_DUTIES_OF_THE_PARICHALAK.md

REF-004-D_ADVISORY_BOARD.md

REF-005-E_GENERAL_BODY.md

REF-006-F(a)_FUNDS_OF_THE_KENDRA_SANGHA.md

REF-006-F(b)_MAINTENANCE_OF_THE_FUNDS.md

REF-006-F(c)_UTILISATION_OF_THE_FUNDS.md

REF-007-G_ACCOUNTS_AND_AUDIT.md

REF-008-H_POWER_TO_AMEND.md

REF-009-I_DISSOLUTION.md

REF-010-J_ADDITIONAL_RESOLUTIONS_1975.md
```

---

**End of Document**