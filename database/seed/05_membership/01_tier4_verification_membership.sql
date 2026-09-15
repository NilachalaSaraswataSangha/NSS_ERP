-- =====================================================
-- NSS ERP
-- Module: Membership
-- Seed File: 01_tier4_verification_membership.sql
-- Version: 2.1
-- Authority: Tier 4 verification seed
-- Owner: NSS_ERP_ADMIN
-- Note: Creates membership records for 5 of the 8
--       test persons:
--
--       Three-tier identity model per MBR-030B:
--         Tier 1: Sangha Sevi ID (SS1) — NSS-wide, permanent
--         Tier 2: Local Sakha ERP Number (ESS1192) — Sakha-scoped
--                 (= ERP Number; Local Sakha Number = ERP Number)
--         Tier 3: Kendra Number (345/2026/2027) — via
--                 parichaya_patra.document_number
--
--       SS1 — Ramesh Mishra: Regular member at SKH1.
--              Tier 1: SS1
--              Tier 2: ESS1192 (Ekamra Sakha)
--              Tier 3: 345/2026/2027 (Parichaya Patra)
--              Renewal history, journey events.
--
--       SS2 — Aniket Mishra: Probationary member at SKH1.
--              Tier 1: SS2
--              Tier 2: ESS1250 (Ekamra Sakha)
--              Anumati Patra (MBR-010), journey events.
--
--       SS3 — Suresh Patel: Regular member, transferred
--              from SKH1 → SKH2. Demonstrates MBR-027
--              to MBR-031 (transfer identity preserved,
--              Sangha Sevi ID unchanged, old affiliation
--              archived, new affiliation at target Sakha,
--              transfer_history record, Dola Purnima
--              effective date per MBR-029).
--              Tier 1: SS3 (unchanged on transfer)
--              Tier 2: ESS1100 → CTC1 (changed on transfer)
--              Tier 3: 512/2026/2027 (Parichaya Patra)
--
--       SS4 — Debasis Rath: Associate member at SKH1.
--              Enrolled by Parichalak (MBR-017). May
--              attend functions of Sakha Sanghas and
--              Kendra Sangha (MBR-018). No elected-post
--              voting/election rights (MBR-019).
--              Parichaya Patra yes (MBR-019A), Anumati
--              Patra no (MBR-019B).
--              Tier 1: SS4
--              Tier 2: ESS1300 (Ekamra Sakha)
--              Tier 3: 789/2026/2027 (Parichaya Patra)
--
--       SS5 — Smita Sahoo: Probationary member at SKH1.
--              Former Kumari participant who transitioned
--              to formal NSS Membership (Kumari Transition
--              — 01_membership_module_overview.md §6).
--              Tier 1: SS5
--              Tier 2: ESS1260 (Ekamra Sakha)
--              Anumati Patra, journey events.
--
--       Non-member Persons (validates Person ≠ Member):
--         P2 — Sushma Mishra: Non-member family member
--               (FAM-004 Family First model).
--         P6 — Priyanka Das: Kumari participant
--               (01_membership_module_overview.md §2).
--         P7 — Soumya Nayak: Kishor participant
--               (01_membership_module_overview.md §2).
--
--       Note: P8 (Smita Sahoo) was formerly a Kumari
--       participant but has transitioned to NSS Membership
--       (SS5). Kumari-side transition record deferred to
--       Kumari DDL phase.
--
--       Cross-sangha attendance (Darshak) is an
--       Attendance Module concept (MBR-035, §27.1) —
--       not modelled in this Membership seed.
--
--       Sevak Sangha and Mahila Sangha are separate
--       modules (§27.1 cross-module note) — not
--       modelled in this Membership seed.
-- =====================================================

-- =========================================================
-- SECTION 1: SANGHA SEVI RECORDS
-- =========================================================

-- -------------------------------------------------
-- SS1: Ramesh Mishra — Regular Member at SKH1
-- -------------------------------------------------

INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT
    'SS1',
    p.person_pk,
    mt.master_data_pk,
    ms.master_data_pk,
    sakha.organization_pk,
    '2012-04-01',
    '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P1'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'REGULAR'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- SS2: Aniket Mishra — Probationary Member at SKH1
-- -------------------------------------------------

INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT
    'SS2',
    p.person_pk,
    mt.master_data_pk,
    ms.master_data_pk,
    sakha.organization_pk,
    '2025-04-01',
    '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P3'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'PROBATIONARY'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- SS3: Suresh Patel — Regular Member, now at SKH2
-- (transferred from SKH1 → SKH2, MBR-027)
-- Current organization_pk points to SKH2 (post-transfer).
-- -------------------------------------------------

INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT
    'SS3',
    p.person_pk,
    mt.master_data_pk,
    ms.master_data_pk,
    sakha.organization_pk,
    '2015-04-01',
    '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P4'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'REGULAR'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH2';

-- -------------------------------------------------
-- SS4: Debasis Rath — Associate Member at SKH1
-- Enrolled by Parichalak (MBR-017).
-- May attend Sakha/Kendra functions (MBR-018).
-- No elected-post voting rights (MBR-019).
-- -------------------------------------------------

INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT
    'SS4',
    p.person_pk,
    mt.master_data_pk,
    ms.master_data_pk,
    sakha.organization_pk,
    '2020-04-01',
    '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P5'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'ASSOCIATE'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- SS5: Smita Sahoo — Probationary Member at SKH1
-- Former Kumari participant who transitioned to
-- NSS Membership (01_membership_module_overview.md §6:
-- "Kumari Transition" is a documented membership source).
-- Kumari-side record (kumari_membership_transition)
-- deferred to Kumari DDL phase.
-- -------------------------------------------------

INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT
    'SS5',
    p.person_pk,
    mt.master_data_pk,
    ms.master_data_pk,
    sakha.organization_pk,
    '2025-04-01',
    '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P8'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'PROBATIONARY'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH1';

-- =========================================================
-- SECTION 2: SAKHA AFFILIATIONS
-- =========================================================

-- -------------------------------------------------
-- Ramesh — Ekamra Sakha #1192 (ACTIVE, ENROLLMENT)
-- -------------------------------------------------

INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT
    ss.sangha_sevi_pk,
    sakha.organization_pk,
    'ESS1192',
    '2012-04-01',
    'ACTIVE',
    'ENROLLMENT'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS1'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- Aniket — Ekamra Sakha #1250 (ACTIVE, ENROLLMENT)
-- -------------------------------------------------

INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT
    ss.sangha_sevi_pk,
    sakha.organization_pk,
    'ESS1250',
    '2025-04-01',
    'ACTIVE',
    'ENROLLMENT'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS2'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- Suresh — Ekamra Sakha #1100 (ARCHIVED, ENROLLMENT)
-- Original affiliation at SKH1 before transfer.
-- Closed on Dola Purnima 2025 (transfer effective date).
-- Per §27.1: old row closed, affiliation_status = ARCHIVED.
-- -------------------------------------------------

INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, effective_to, affiliation_status,
     source_event_type)
SELECT
    ss.sangha_sevi_pk,
    sakha.organization_pk,
    'ESS1100',
    '2015-04-01',
    '2025-03-14',
    'ARCHIVED',
    'ENROLLMENT'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS3'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- Suresh — Cuttack Sakha #1 (ACTIVE, TRANSFER)
-- Tier 2 changed: ESS1100 → CTC1 (MBR-030).
-- Per §27.1: new row at new Sakha, new local ERP number.
-- Dola Purnima 2025 = effective date (MBR-029).
-- -------------------------------------------------

INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT
    ss.sangha_sevi_pk,
    sakha.organization_pk,
    'CTC1',
    '2025-03-14',
    'ACTIVE',
    'TRANSFER'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS3'
  AND sakha.organization_code = 'SKH2';

-- -------------------------------------------------
-- Debasis — Ekamra Sakha #1300 (ACTIVE, ENROLLMENT)
-- Associate member affiliation.
-- -------------------------------------------------

INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT
    ss.sangha_sevi_pk,
    sakha.organization_pk,
    'ESS1300',
    '2020-04-01',
    'ACTIVE',
    'ENROLLMENT'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS4'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- Smita — Ekamra Sakha #1260 (ACTIVE, ENROLLMENT)
-- Kumari Transition — enrolled as Probationary.
-- -------------------------------------------------

INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT
    ss.sangha_sevi_pk,
    sakha.organization_pk,
    'ESS1260',
    '2025-04-01',
    'ACTIVE',
    'ENROLLMENT'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS5'
  AND sakha.organization_code = 'SKH1';

-- =========================================================
-- SECTION 3: IDENTITY DOCUMENTS
-- =========================================================

-- -------------------------------------------------
-- Parichaya Patra: Ramesh — FY 2026-2027
-- Tier 3 Kendra number: 345/2026/2027
-- Tier 2 snapshot: ESS1192 (Ekamra Sakha)
-- Regular member credential (MBR-014).
-- -------------------------------------------------

INSERT INTO nss.parichaya_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status,
     affiliated_organization_pk, local_sakha_erp_id)
SELECT
    ss.sangha_sevi_pk,
    '345/2026/2027',
    '2026-04-15',
    '2026-04-01',
    '2027-03-31',
    'ACTIVE',
    sakha.organization_pk,
    'ESS1192'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS1'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- Parichaya Patra: Suresh — FY 2026-2027
-- Tier 3 Kendra number: 512/2026/2027
-- Tier 2 snapshot: CTC1 (Cuttack Sakha)
-- Issued at new Sakha after transfer.
-- -------------------------------------------------

INSERT INTO nss.parichaya_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status,
     affiliated_organization_pk, local_sakha_erp_id)
SELECT
    ss.sangha_sevi_pk,
    '512/2026/2027',
    '2026-04-15',
    '2026-04-01',
    '2027-03-31',
    'ACTIVE',
    sakha.organization_pk,
    'CTC1'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS3'
  AND sakha.organization_code = 'SKH2';

-- -------------------------------------------------
-- Parichaya Patra: Debasis — FY 2026-2027
-- Tier 3 Kendra number: 789/2026/2027
-- Tier 2 snapshot: ESS1300 (Ekamra Sakha)
-- Associate member credential (MBR-019A: Associate
-- members receive Parichaya Patra).
-- -------------------------------------------------

INSERT INTO nss.parichaya_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status,
     affiliated_organization_pk, local_sakha_erp_id)
SELECT
    ss.sangha_sevi_pk,
    '789/2026/2027',
    '2026-04-15',
    '2026-04-01',
    '2027-03-31',
    'ACTIVE',
    sakha.organization_pk,
    'ESS1300'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS4'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- Anumati Patra: Ramesh — FY 2012-2013 (EXPIRED)
-- Historical probationary credential before Regular
-- promotion (2013-06-15). Now Regular with Parichaya
-- Patra — Anumati Patra retained for history.
-- -------------------------------------------------

INSERT INTO nss.anumati_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status)
SELECT
    ss.sangha_sevi_pk,
    'AP/2012/15',
    '2012-04-20',
    '2012-04-01',
    '2013-03-31',
    'EXPIRED'
FROM nss.sangha_sevi ss
WHERE ss.sangha_sevi_id = 'SS1';

-- -------------------------------------------------
-- Anumati Patra: Suresh — FY 2015-2016 (EXPIRED)
-- Historical probationary credential before Regular
-- promotion (2016-06-10). Now Regular with Parichaya
-- Patra — Anumati Patra retained for history.
-- -------------------------------------------------

INSERT INTO nss.anumati_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status)
SELECT
    ss.sangha_sevi_pk,
    'AP/2015/28',
    '2015-04-20',
    '2015-04-01',
    '2016-03-31',
    'EXPIRED'
FROM nss.sangha_sevi ss
WHERE ss.sangha_sevi_id = 'SS3';

-- -------------------------------------------------
-- Anumati Patra: Aniket — FY 2025-2026
-- Probationary member credential (MBR-010).
-- Bye-Law §B(a): issued after enrollment.
-- -------------------------------------------------

INSERT INTO nss.anumati_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status)
SELECT
    ss.sangha_sevi_pk,
    'AP/2025/42',
    '2025-04-15',
    '2025-04-01',
    '2026-03-31',
    'ACTIVE'
FROM nss.sangha_sevi ss
WHERE ss.sangha_sevi_id = 'SS2';

-- -------------------------------------------------
-- Anumati Patra: Smita — FY 2025-2026
-- Kumari Transition enrollee — Probationary member
-- credential (MBR-010). Bye-Law §B(a): issued after
-- enrollment.
-- -------------------------------------------------

INSERT INTO nss.anumati_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status)
SELECT
    ss.sangha_sevi_pk,
    'AP/2025/50',
    '2025-04-15',
    '2025-04-01',
    '2026-03-31',
    'ACTIVE'
FROM nss.sangha_sevi ss
WHERE ss.sangha_sevi_id = 'SS5';

-- =========================================================
-- SECTION 4: TRANSFER HISTORY (MBR-027 to MBR-031)
-- =========================================================

-- -------------------------------------------------
-- Suresh Patel: SKH1 → SKH2
-- Effective date = Dola Purnima 2025 (MBR-029).
-- Tier 1: Sangha Sevi ID unchanged (MBR-027).
-- Tier 2: Local Sakha ERP Number changed ESS1100 → CTC1 (MBR-030).
-- Old affiliation preserved (MBR-031).
-- -------------------------------------------------

INSERT INTO nss.membership_transfer_history
    (sangha_sevi_pk, old_organization_pk, new_organization_pk,
     transfer_type, transfer_reason, requested_date,
     approved_date, effective_date,
     old_local_sakha_erp_id, new_local_sakha_erp_id,
     remarks)
SELECT
    ss.sangha_sevi_pk,
    old_sakha.organization_pk,
    new_sakha.organization_pk,
    'INTER_ANCHALIKA',
    'Relocated to Cuttack for work',
    '2025-01-15',
    '2025-02-20',
    '2025-03-14',
    'ESS1100',
    'CTC1',
    'Transfer approved. Effective Dola Purnima 2025 (MBR-029).'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization old_sakha
CROSS JOIN nss.organization new_sakha
WHERE ss.sangha_sevi_id = 'SS3'
  AND old_sakha.organization_code = 'SKH1'
  AND new_sakha.organization_code = 'SKH2';

-- =========================================================
-- SECTION 5: MEMBERSHIP JOURNEY EVENTS
-- =========================================================

-- --- Ramesh (SS1) ---

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'MEMBERSHIP_CREATED', '2012-04-01',
       'Enrolled as probationary member at Ekamra Sakha'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS1';

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'REGULAR_ENROLMENT', '2013-06-15',
       'Promoted to Regular member after training completion'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS1';

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'RENEWAL', '2026-04-15',
       'Parichaya Patra renewed for FY 2026-2027'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS1';

-- --- Aniket (SS2) ---

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'MEMBERSHIP_CREATED', '2025-04-01',
       'Enrolled as probationary member at Ekamra Sakha'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS2';

-- --- Suresh (SS3) — transfer journey ---

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'MEMBERSHIP_CREATED', '2015-04-01',
       'Enrolled as probationary member at Ekamra Sakha'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS3';

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'REGULAR_ENROLMENT', '2016-06-10',
       'Promoted to Regular member at Ekamra Sakha'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS3';

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'TRANSFER', '2025-03-14',
       'Transferred from Ekamra Sakha (SKH1) to Cuttack Sakha (SKH2). Effective Dola Purnima 2025.'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS3';

-- --- Debasis (SS4) — associate enrolment ---

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'ASSOCIATE_ENROLMENT', '2020-04-01',
       'Enrolled as Associate member by Parichalak (MBR-017)'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS4';

-- --- Smita (SS5) — Kumari Transition ---

INSERT INTO nss.membership_journey_event
    (sangha_sevi_pk, event_type, event_date, remarks)
SELECT ss.sangha_sevi_pk, 'MEMBERSHIP_CREATED', '2025-04-01',
       'Kumari Transition (01_membership_module_overview.md §6). Former active Kumari participant enrolled as Probationary member at Ekamra Sakha.'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS5';

-- =========================================================
-- SECTION 6: MEMBERSHIP STATUS HISTORY
-- =========================================================

-- Ramesh: ACTIVE from joining
INSERT INTO nss.membership_status_history
    (sangha_sevi_pk, membership_status_master_data_pk,
     effective_from, reason)
SELECT
    ss.sangha_sevi_pk,
    ms.master_data_pk,
    '2012-04-01',
    'Initial enrollment'
FROM nss.sangha_sevi ss
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc ON mc.master_category_pk = ms.master_category_pk
WHERE ss.sangha_sevi_id = 'SS1'
  AND mc.category_code = 'STATUS' AND ms.value_code = 'ACTIVE';

-- Suresh: ACTIVE from joining (original)
INSERT INTO nss.membership_status_history
    (sangha_sevi_pk, membership_status_master_data_pk,
     effective_from, reason)
SELECT
    ss.sangha_sevi_pk,
    ms.master_data_pk,
    '2015-04-01',
    'Initial enrollment'
FROM nss.sangha_sevi ss
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc ON mc.master_category_pk = ms.master_category_pk
WHERE ss.sangha_sevi_id = 'SS3'
  AND mc.category_code = 'STATUS' AND ms.value_code = 'ACTIVE';

-- Debasis: ACTIVE from associate enrollment
INSERT INTO nss.membership_status_history
    (sangha_sevi_pk, membership_status_master_data_pk,
     effective_from, reason)
SELECT
    ss.sangha_sevi_pk,
    ms.master_data_pk,
    '2020-04-01',
    'Associate enrollment by Parichalak'
FROM nss.sangha_sevi ss
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc ON mc.master_category_pk = ms.master_category_pk
WHERE ss.sangha_sevi_id = 'SS4'
  AND mc.category_code = 'STATUS' AND ms.value_code = 'ACTIVE';

-- Smita: ACTIVE from enrollment (Kumari Transition)
INSERT INTO nss.membership_status_history
    (sangha_sevi_pk, membership_status_master_data_pk,
     effective_from, reason)
SELECT
    ss.sangha_sevi_pk,
    ms.master_data_pk,
    '2025-04-01',
    'Kumari Transition enrollment'
FROM nss.sangha_sevi ss
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc ON mc.master_category_pk = ms.master_category_pk
WHERE ss.sangha_sevi_id = 'SS5'
  AND mc.category_code = 'STATUS' AND ms.value_code = 'ACTIVE';

-- =========================================================
-- SECTION 7: RENEWAL HISTORY
-- =========================================================

-- Ramesh — latest renewal (FY 2026-2027)
INSERT INTO nss.membership_renewal_history
    (sangha_sevi_pk, renewal_date, valid_from, valid_to)
SELECT
    ss.sangha_sevi_pk,
    '2026-04-15',
    '2026-04-01',
    '2027-03-31'
FROM nss.sangha_sevi ss
WHERE ss.sangha_sevi_id = 'SS1';

-- Suresh — renewal at new Sakha (FY 2026-2027)
INSERT INTO nss.membership_renewal_history
    (sangha_sevi_pk, renewal_date, valid_from, valid_to)
SELECT
    ss.sangha_sevi_pk,
    '2026-04-15',
    '2026-04-01',
    '2027-03-31'
FROM nss.sangha_sevi ss
WHERE ss.sangha_sevi_id = 'SS3';
