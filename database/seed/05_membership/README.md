# database/seed/05_membership/

Membership has **real verification seed data** — unlike `database/seed/03_person/` (zero rows),
`01_tier4_verification_membership.sql` populates 5 of the 12 Membership tables with a small,
hand-crafted set of members chosen to exercise every membership type, the transfer workflow, and
the Kumari-transition enrolment path, not just to prove the schema accepts inserts.

- `01_tier4_verification_membership.sql` — Version 2.1. Creates **5 `sangha_sevi` records**
  (`SS1`–`SS5`) against 5 of the 8 test persons seeded by
  `database/seed/03_person/02_tier4_verification_persons.sql`, plus matching rows in
  `membership_sakha_affiliation`, `parichaya_patra`, `anumati_patra`,
  `membership_transfer_history`, `membership_journey_event`, and
  `membership_status_history`. **Not seeded:** `membership_renewal_request`,
  `membership_renewal_history` (2 renewal rows are seeded, but the *request* workflow table is
  left empty), `probationary_member_review`, `parichaya_patra_history`,
  `anumati_patra_history` — these five tables exist with zero rows after running this file.

## What's Seeded

| Sangha Sevi ID | Person | Type | Sakha | Notable |
|---|---|---|---|---|
| `SS1` | Ramesh Mishra (`P1`) | REGULAR | SKH1 (Ekamra Sakha) | Full history: promoted from Probationary (2013), renewed FY 2026–2027, has both an EXPIRED Anumati Patra (pre-promotion) and an ACTIVE Parichaya Patra (`345/2026/2027`) |
| `SS2` | Aniket Mishra (`P3`) | PROBATIONARY | SKH1 (Ekamra Sakha) | ACTIVE Anumati Patra (`AP/2025/42`), no Parichaya Patra (Probationary members don't receive one) |
| `SS3` | Suresh Patel (`P4`) | REGULAR | SKH2 (Cuttack Sakha) — transferred from SKH1 | Demonstrates the full transfer workflow (MBR-027–MBR-031): 2 affiliation rows (one `ARCHIVED` at SKH1 with `ESS1100`, one `ACTIVE` at SKH2 with `CTC1`), a `membership_transfer_history` row, a `TRANSFER` journey event, and an EXPIRED Anumati Patra from its Probationary period |
| `SS4` | Debasis Rath (`P5`) | ASSOCIATE | SKH1 (Ekamra Sakha) | Enrolled directly by Parichalak (MBR-017); has a Parichaya Patra (MBR-019A) but **no** Anumati Patra (MBR-019B — Associate members don't get one) |
| `SS5` | Smita Sahoo (`P8`) | PROBATIONARY | SKH1 (Ekamra Sakha) | Kumari Transition — a former Kumari participant enrolled as a formal NSS member; has a `KUMARI_TRANSITION`-flavoured `MEMBERSHIP_CREATED` journey event and an ACTIVE Anumati Patra |

**Non-members seeded elsewhere but deliberately left unlinked here** (validates the "Person ≠
Member" frozen principle — see the seed file's own header comment): `P2` (Sushma Mishra, a
non-member family member), `P6` (Priyanka Das, Kumari participant), `P7` (Soumya Nayak, Kishor
participant). `P8`'s prior Kumari-side record is out of scope — deferred to the future Kumari
module DDL.

**Deliberately not modelled in this seed** (cross-module concerns, per the seed file's own header
comment): cross-Sakha attendance (Darshak — an Attendance Module concept), Sevak Sangha, and
Mahila Sangha (separate modules).

Note: `database/scripts/03_validate.sh`/`.ps1` does not yet include Membership-specific
row-count/FK checks (its Membership coverage stops at a `document_master.uploaded_by_sangha_sevi_pk`
column-existence check) — the table above is the authoritative record of what's actually seeded
for this module. 5 of 12 Membership tables have real rows; the remaining 7 have zero rows by
design at this stage, not by omission.
