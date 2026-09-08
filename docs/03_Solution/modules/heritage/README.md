# NSS ERP Founder & Heritage Module

Status: DRAFT — SOURCE ALIGNED (Solution design complete, v1.0.0). SQL implementation not
started for any of the 8 designed tables — see Note below.

Complete 5-document Solution-level design set, following the same
`01_module_overview` / `02_erd` / `03_lifecycle` / `04_business_rules` / `05_table_design`
pattern used by `docs/03_Solution/modules/organization/`, `person/`, `membership/`, etc.

## Documents

- `01_founder_heritage_module_overview.md` (SOL-HER-001) — module purpose and scope
- `02_founder_heritage_erd.md` — entity relationship design
- `03_founder_heritage_lifecycle.md` — lifecycle states
- `04_founder_heritage_business_rules.md` — HER-001–HER-100
- `05_founder_heritage_table_design.md` — logical table design, 8 tables

## Tables designed (8)

`founder_master` (single immutable record — Founder = Swami Nigamananda Paramahansa Dev),
`founder_teaching`, `nss_objective_master`, `nss_historical_milestone`, `nss_publication`
(v1.1 — mandatory language, free/donation/fixed-price models, physical+digital coexistence,
multiple editions, digitization support), `historical_office_bearer`, `publication_type_master`,
`publication_language_master`.

## Note — design/code gap

No code implementation exists yet for any of the 8 designed tables. The Django prototype, which
previously implemented only `founder_master` as a `Founder` singleton model, was removed from
the repository entirely (see `docs/03_Solution/architecture/TECH_STACK_DECISIONS.md`) — the
Heritage module has no representation in the current FastAPI/hand-written-DDL codebase. Future
entities beyond this frozen 8-table scope are explicitly excluded per the business rules
document.
