-- =====================================================
-- NSS ERP
-- Extended Test Data — Incremental Seed
-- Version: 1.0
-- Authority: Verification test data
-- Owner: NSS_ERP_ADMIN
-- Note: Adds 2 more families, 4 new persons, and
--       cross-Sakha memberships to exercise:
--
--       1. Org admin drill-down (multiple families
--          under different Sakhas)
--       2. Sakha alignment / majority rule (FAM-036)
--       3. Cross-Sakha member mismatch badges (FAM-037)
--
--       F2: Patel Paribara at SKH1 (Ekamra)
--           Suresh (P4, SS3) — affiliated SKH2 (transferred)
--           Meera  (P14, SS6) — affiliated SKH2
--           Arjun  (P15) — no membership (child)
--           => FAMILY-LEVEL MISMATCH: assigned SKH1,
--              majority SKH2 (both members at SKH2)
--
--       F3: Rath Paribara at SKH2 (Cuttack)
--           Debasis  (P5, SS4) — affiliated SKH1
--           Laxmi    (P16, SS7) — affiliated SKH2
--           Pallavi  (P17, SS8) — affiliated SKH2
--           => Aligned (majority SKH2 = assigned SKH2),
--              but Debasis has INDIVIDUAL MISMATCH badge
--
-- Depends on: 02_tier4_verification_persons.sql,
--             01_tier4_verification_family.sql,
--             01_tier4_verification_membership.sql
-- =====================================================

-- ─────────────────────────────────────────────────────
-- 1. NEW PERSONS (P14–P17)
-- ─────────────────────────────────────────────────────

-- P14: Meera Patel (Suresh's wife)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P14', 'Meera', 'Patel', '1982-09-12',
    g.master_data_pk, ms.master_data_pk,
    '+91', '9437100014', 'meera.patel@example.com'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'FEMALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'MARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number,
    email                          = EXCLUDED.email;

-- P15: Arjun Patel (Suresh & Meera's son — no membership)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number)
SELECT
    'P15', 'Arjun', 'Patel', '2008-03-25',
    g.master_data_pk, ms.master_data_pk,
    '+91', '9437100015'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'MALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'UNMARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number;

-- P16: Laxmi Rath (Debasis's wife)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P16', 'Laxmi', 'Rath', '1968-11-30',
    g.master_data_pk, ms.master_data_pk,
    '+91', '9437100016', 'laxmi.rath@example.com'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'FEMALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'MARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number,
    email                          = EXCLUDED.email;

-- P17: Pallavi Rath (Debasis & Laxmi's daughter)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P17', 'Pallavi', 'Rath', '1995-05-14',
    g.master_data_pk, ms.master_data_pk,
    '+91', '9437100017', 'pallavi.rath@example.com'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'FEMALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'UNMARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number,
    email                          = EXCLUDED.email;


-- ─────────────────────────────────────────────────────
-- 2. NEW FAMILIES (F2, F3)
-- ─────────────────────────────────────────────────────

-- F2: Patel Paribara at SKH1 (Ekamra Sakha)
-- Note: Assigned to SKH1, but both members are
--       affiliated with SKH2 → family-level mismatch
INSERT INTO nss.family_group
    (family_id, family_name, family_status_master_data_pk,
     sakha_organization_pk, formed_date)
SELECT
    'F2', 'Patel Paribara',
    st.master_data_pk, sakha.organization_pk, '2015-04-01'
FROM nss.master_data st
JOIN nss.master_category mc ON mc.master_category_pk = st.master_category_pk
CROSS JOIN nss.organization sakha
WHERE mc.category_code = 'STATUS' AND st.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH1'
ON CONFLICT (family_id) DO UPDATE SET
    family_name                  = EXCLUDED.family_name,
    family_status_master_data_pk = EXCLUDED.family_status_master_data_pk,
    sakha_organization_pk        = EXCLUDED.sakha_organization_pk,
    formed_date                  = EXCLUDED.formed_date;

-- F3: Rath Paribara at SKH2 (Cuttack Sakha)
-- Note: Assigned to SKH2, majority at SKH2 (aligned),
--       but Debasis has individual mismatch (SKH1)
INSERT INTO nss.family_group
    (family_id, family_name, family_status_master_data_pk,
     sakha_organization_pk, formed_date)
SELECT
    'F3', 'Rath Paribara',
    st.master_data_pk, sakha.organization_pk, '2012-04-01'
FROM nss.master_data st
JOIN nss.master_category mc ON mc.master_category_pk = st.master_category_pk
CROSS JOIN nss.organization sakha
WHERE mc.category_code = 'STATUS' AND st.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH2'
ON CONFLICT (family_id) DO UPDATE SET
    family_name                  = EXCLUDED.family_name,
    family_status_master_data_pk = EXCLUDED.family_status_master_data_pk,
    sakha_organization_pk        = EXCLUDED.sakha_organization_pk,
    formed_date                  = EXCLUDED.formed_date;


-- ─────────────────────────────────────────────────────
-- 3. FAMILY RELATIONSHIPS
-- ─────────────────────────────────────────────────────

-- F2: Suresh Patel — FATHER (head)
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT fg.family_group_pk, p.person_pk, rt.master_data_pk,
       '2015-04-01', TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F2' AND p.person_id = 'P4'
  AND mc.category_code = 'RELATIONSHIP_TYPE' AND rt.value_code = 'FATHER'
ON CONFLICT (family_group_pk, person_pk) WHERE is_current = TRUE DO UPDATE SET
    relationship_type_master_data_pk = EXCLUDED.relationship_type_master_data_pk,
    effective_from                   = EXCLUDED.effective_from,
    is_current                       = EXCLUDED.is_current;

-- F2: Meera Patel — SPOUSE
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT fg.family_group_pk, p.person_pk, rt.master_data_pk,
       '2015-04-01', TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F2' AND p.person_id = 'P14'
  AND mc.category_code = 'RELATIONSHIP_TYPE' AND rt.value_code = 'SPOUSE'
ON CONFLICT (family_group_pk, person_pk) WHERE is_current = TRUE DO UPDATE SET
    relationship_type_master_data_pk = EXCLUDED.relationship_type_master_data_pk,
    effective_from                   = EXCLUDED.effective_from,
    is_current                       = EXCLUDED.is_current;

-- F2: Arjun Patel — SON
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT fg.family_group_pk, p.person_pk, rt.master_data_pk,
       '2015-04-01', TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F2' AND p.person_id = 'P15'
  AND mc.category_code = 'RELATIONSHIP_TYPE' AND rt.value_code = 'SON'
ON CONFLICT (family_group_pk, person_pk) WHERE is_current = TRUE DO UPDATE SET
    relationship_type_master_data_pk = EXCLUDED.relationship_type_master_data_pk,
    effective_from                   = EXCLUDED.effective_from,
    is_current                       = EXCLUDED.is_current;

-- F3: Debasis Rath — FATHER (head)
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT fg.family_group_pk, p.person_pk, rt.master_data_pk,
       '2012-04-01', TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F3' AND p.person_id = 'P5'
  AND mc.category_code = 'RELATIONSHIP_TYPE' AND rt.value_code = 'FATHER'
ON CONFLICT (family_group_pk, person_pk) WHERE is_current = TRUE DO UPDATE SET
    relationship_type_master_data_pk = EXCLUDED.relationship_type_master_data_pk,
    effective_from                   = EXCLUDED.effective_from,
    is_current                       = EXCLUDED.is_current;

-- F3: Laxmi Rath — SPOUSE
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT fg.family_group_pk, p.person_pk, rt.master_data_pk,
       '2012-04-01', TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F3' AND p.person_id = 'P16'
  AND mc.category_code = 'RELATIONSHIP_TYPE' AND rt.value_code = 'SPOUSE'
ON CONFLICT (family_group_pk, person_pk) WHERE is_current = TRUE DO UPDATE SET
    relationship_type_master_data_pk = EXCLUDED.relationship_type_master_data_pk,
    effective_from                   = EXCLUDED.effective_from,
    is_current                       = EXCLUDED.is_current;

-- F3: Pallavi Rath — DAUGHTER
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT fg.family_group_pk, p.person_pk, rt.master_data_pk,
       '2012-04-01', TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F3' AND p.person_id = 'P17'
  AND mc.category_code = 'RELATIONSHIP_TYPE' AND rt.value_code = 'DAUGHTER'
ON CONFLICT (family_group_pk, person_pk) WHERE is_current = TRUE DO UPDATE SET
    relationship_type_master_data_pk = EXCLUDED.relationship_type_master_data_pk,
    effective_from                   = EXCLUDED.effective_from,
    is_current                       = EXCLUDED.is_current;


-- ─────────────────────────────────────────────────────
-- 4. FAMILY HEAD HISTORY
-- ─────────────────────────────────────────────────────

-- F2: Suresh Patel is current head
INSERT INTO nss.family_head_history
    (family_group_pk, person_pk, effective_from)
SELECT fg.family_group_pk, p.person_pk, '2015-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person p
WHERE fg.family_id = 'F2' AND p.person_id = 'P4'
ON CONFLICT (family_group_pk) WHERE effective_to IS NULL DO UPDATE SET
    person_pk      = EXCLUDED.person_pk,
    effective_from = EXCLUDED.effective_from;

-- F3: Debasis Rath is current head
INSERT INTO nss.family_head_history
    (family_group_pk, person_pk, effective_from)
SELECT fg.family_group_pk, p.person_pk, '2012-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person p
WHERE fg.family_id = 'F3' AND p.person_id = 'P5'
ON CONFLICT (family_group_pk) WHERE effective_to IS NULL DO UPDATE SET
    person_pk      = EXCLUDED.person_pk,
    effective_from = EXCLUDED.effective_from;


-- ─────────────────────────────────────────────────────
-- 5. FAMILY LINKS (graph edges for tree rendering)
-- ─────────────────────────────────────────────────────

-- F2: Suresh (P4) SPOUSE_OF Meera (P14)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT fg.family_group_pk, pa.person_pk, pb.person_pk,
       'SPOUSE_OF', '2015-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa CROSS JOIN nss.person pb
WHERE fg.family_id = 'F2' AND pa.person_id = 'P4' AND pb.person_id = 'P14'
ON CONFLICT (family_group_pk, person_a_pk, person_b_pk, link_type) WHERE is_current = TRUE DO UPDATE SET
    effective_from = EXCLUDED.effective_from;

-- F2: Suresh (P4) PARENT_OF Arjun (P15)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT fg.family_group_pk, pa.person_pk, pb.person_pk,
       'PARENT_OF', '2015-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa CROSS JOIN nss.person pb
WHERE fg.family_id = 'F2' AND pa.person_id = 'P4' AND pb.person_id = 'P15'
ON CONFLICT (family_group_pk, person_a_pk, person_b_pk, link_type) WHERE is_current = TRUE DO UPDATE SET
    effective_from = EXCLUDED.effective_from;

-- F2: Meera (P14) PARENT_OF Arjun (P15)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT fg.family_group_pk, pa.person_pk, pb.person_pk,
       'PARENT_OF', '2015-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa CROSS JOIN nss.person pb
WHERE fg.family_id = 'F2' AND pa.person_id = 'P14' AND pb.person_id = 'P15'
ON CONFLICT (family_group_pk, person_a_pk, person_b_pk, link_type) WHERE is_current = TRUE DO UPDATE SET
    effective_from = EXCLUDED.effective_from;

-- F3: Debasis (P5) SPOUSE_OF Laxmi (P16)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT fg.family_group_pk, pa.person_pk, pb.person_pk,
       'SPOUSE_OF', '2012-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa CROSS JOIN nss.person pb
WHERE fg.family_id = 'F3' AND pa.person_id = 'P5' AND pb.person_id = 'P16'
ON CONFLICT (family_group_pk, person_a_pk, person_b_pk, link_type) WHERE is_current = TRUE DO UPDATE SET
    effective_from = EXCLUDED.effective_from;

-- F3: Debasis (P5) PARENT_OF Pallavi (P17)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT fg.family_group_pk, pa.person_pk, pb.person_pk,
       'PARENT_OF', '2012-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa CROSS JOIN nss.person pb
WHERE fg.family_id = 'F3' AND pa.person_id = 'P5' AND pb.person_id = 'P17'
ON CONFLICT (family_group_pk, person_a_pk, person_b_pk, link_type) WHERE is_current = TRUE DO UPDATE SET
    effective_from = EXCLUDED.effective_from;

-- F3: Laxmi (P16) PARENT_OF Pallavi (P17)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT fg.family_group_pk, pa.person_pk, pb.person_pk,
       'PARENT_OF', '2012-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa CROSS JOIN nss.person pb
WHERE fg.family_id = 'F3' AND pa.person_id = 'P16' AND pb.person_id = 'P17'
ON CONFLICT (family_group_pk, person_a_pk, person_b_pk, link_type) WHERE is_current = TRUE DO UPDATE SET
    effective_from = EXCLUDED.effective_from;


-- ─────────────────────────────────────────────────────
-- 6. NEW MEMBERSHIPS (SS6, SS7, SS8)
-- ─────────────────────────────────────────────────────

-- SS6: Meera Patel — Regular member at SKH2 (Cuttack)
-- Note: She lives with family at SKH1 area but her
--       membership is registered at SKH2 (Cuttack)
INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT
    'SS6', p.person_pk,
    mt.master_data_pk, ms.master_data_pk,
    sakha.organization_pk,
    '2016-04-01', '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P14'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'REGULAR'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH2'
ON CONFLICT (sangha_sevi_id) DO UPDATE SET
    person_pk                        = EXCLUDED.person_pk,
    membership_type_master_data_pk   = EXCLUDED.membership_type_master_data_pk,
    membership_status_master_data_pk = EXCLUDED.membership_status_master_data_pk,
    organization_pk                  = EXCLUDED.organization_pk,
    joining_date                     = EXCLUDED.joining_date,
    renewal_due_date                 = EXCLUDED.renewal_due_date;

-- SS7: Laxmi Rath — Regular member at SKH2 (Cuttack)
INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT
    'SS7', p.person_pk,
    mt.master_data_pk, ms.master_data_pk,
    sakha.organization_pk,
    '2013-04-01', '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P16'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'REGULAR'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH2'
ON CONFLICT (sangha_sevi_id) DO UPDATE SET
    person_pk                        = EXCLUDED.person_pk,
    membership_type_master_data_pk   = EXCLUDED.membership_type_master_data_pk,
    membership_status_master_data_pk = EXCLUDED.membership_status_master_data_pk,
    organization_pk                  = EXCLUDED.organization_pk,
    joining_date                     = EXCLUDED.joining_date,
    renewal_due_date                 = EXCLUDED.renewal_due_date;

-- SS8: Pallavi Rath — Darshaka (Probationary) at SKH2
INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date)
SELECT
    'SS8', p.person_pk,
    mt.master_data_pk, ms.master_data_pk,
    sakha.organization_pk,
    '2020-04-01'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P17'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'PROBATIONARY'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH2'
ON CONFLICT (sangha_sevi_id) DO UPDATE SET
    person_pk                        = EXCLUDED.person_pk,
    membership_type_master_data_pk   = EXCLUDED.membership_type_master_data_pk,
    membership_status_master_data_pk = EXCLUDED.membership_status_master_data_pk,
    organization_pk                  = EXCLUDED.organization_pk,
    joining_date                     = EXCLUDED.joining_date;


-- ─────────────────────────────────────────────────────
-- 7. SAKHA AFFILIATIONS for new members
-- ─────────────────────────────────────────────────────

-- SS6: Meera Patel — active at SKH2 (Cuttack), ERP# CTC2
INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT
    ss.sangha_sevi_pk, o.organization_pk,
    'CTC2', '2016-04-01', 'ACTIVE', 'ENROLLMENT'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization o
WHERE ss.sangha_sevi_id = 'SS6'
  AND o.organization_code = 'SKH2'
ON CONFLICT (organization_pk, local_sakha_erp_id) DO UPDATE SET
    sangha_sevi_pk    = EXCLUDED.sangha_sevi_pk,
    effective_from    = EXCLUDED.effective_from,
    affiliation_status = EXCLUDED.affiliation_status,
    source_event_type = EXCLUDED.source_event_type;

-- SS7: Laxmi Rath — active at SKH2 (Cuttack), ERP# CTC3
INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT
    ss.sangha_sevi_pk, o.organization_pk,
    'CTC3', '2013-04-01', 'ACTIVE', 'ENROLLMENT'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization o
WHERE ss.sangha_sevi_id = 'SS7'
  AND o.organization_code = 'SKH2'
ON CONFLICT (organization_pk, local_sakha_erp_id) DO UPDATE SET
    sangha_sevi_pk    = EXCLUDED.sangha_sevi_pk,
    effective_from    = EXCLUDED.effective_from,
    affiliation_status = EXCLUDED.affiliation_status,
    source_event_type = EXCLUDED.source_event_type;

-- SS8: Pallavi Rath — active at SKH2 (Cuttack), ERP# CTC4
INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT
    ss.sangha_sevi_pk, o.organization_pk,
    'CTC4', '2020-04-01', 'ACTIVE', 'ENROLLMENT'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization o
WHERE ss.sangha_sevi_id = 'SS8'
  AND o.organization_code = 'SKH2'
ON CONFLICT (organization_pk, local_sakha_erp_id) DO UPDATE SET
    sangha_sevi_pk    = EXCLUDED.sangha_sevi_pk,
    effective_from    = EXCLUDED.effective_from,
    affiliation_status = EXCLUDED.affiliation_status,
    source_event_type = EXCLUDED.source_event_type;


-- ─────────────────────────────────────────────────────
-- 8. PARICHAYA PATRA / ANUMATI PATRA for new members
-- ─────────────────────────────────────────────────────

-- Meera Patel — Parichaya Patra
INSERT INTO nss.parichaya_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status,
     affiliated_organization_pk, local_sakha_erp_id)
SELECT
    ss.sangha_sevi_pk,
    '601/2026/2027', '2026-04-15',
    '2026-04-01', '2027-03-31', 'ACTIVE',
    sakha.organization_pk, 'CTC2'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS6'
  AND sakha.organization_code = 'SKH2'
ON CONFLICT (document_number) DO UPDATE SET
    sangha_sevi_pk             = EXCLUDED.sangha_sevi_pk,
    issue_date                 = EXCLUDED.issue_date,
    valid_from                 = EXCLUDED.valid_from,
    valid_to                   = EXCLUDED.valid_to,
    status                     = EXCLUDED.status,
    affiliated_organization_pk = EXCLUDED.affiliated_organization_pk,
    local_sakha_erp_id         = EXCLUDED.local_sakha_erp_id;

-- Laxmi Rath — Parichaya Patra
INSERT INTO nss.parichaya_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status,
     affiliated_organization_pk, local_sakha_erp_id)
SELECT
    ss.sangha_sevi_pk,
    '602/2026/2027', '2026-04-15',
    '2026-04-01', '2027-03-31', 'ACTIVE',
    sakha.organization_pk, 'CTC3'
FROM nss.sangha_sevi ss
CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS7'
  AND sakha.organization_code = 'SKH2'
ON CONFLICT (document_number) DO UPDATE SET
    sangha_sevi_pk             = EXCLUDED.sangha_sevi_pk,
    issue_date                 = EXCLUDED.issue_date,
    valid_from                 = EXCLUDED.valid_from,
    valid_to                   = EXCLUDED.valid_to,
    status                     = EXCLUDED.status,
    affiliated_organization_pk = EXCLUDED.affiliated_organization_pk,
    local_sakha_erp_id         = EXCLUDED.local_sakha_erp_id;

-- Pallavi Rath — Anumati Patra (Darshaka gets Anumati Patra)
INSERT INTO nss.anumati_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status)
SELECT
    ss.sangha_sevi_pk,
    'AP/2026/03', '2026-04-20',
    '2026-04-01', '2027-03-31', 'ACTIVE'
FROM nss.sangha_sevi ss
WHERE ss.sangha_sevi_id = 'SS8'
ON CONFLICT (document_number) DO UPDATE SET
    sangha_sevi_pk = EXCLUDED.sangha_sevi_pk,
    issue_date     = EXCLUDED.issue_date,
    valid_from     = EXCLUDED.valid_from,
    valid_to       = EXCLUDED.valid_to,
    status         = EXCLUDED.status;


-- =====================================================
-- VERIFICATION SUMMARY
-- =====================================================
-- After running this seed:
--
-- Families: 3
--   F1: Mishra Paribara (SKH1) — 8 members, aligned
--   F2: Patel Paribara  (SKH1) — 3 members, MISALIGNED
--       (Suresh@SKH2, Meera@SKH2 → majority SKH2 != assigned SKH1)
--   F3: Rath Paribara   (SKH2) — 3 members, aligned
--       (Debasis@SKH1 = individual mismatch, Laxmi+Pallavi@SKH2)
--
-- Org admin drill-down:
--   Kendra → Puri Anchalika → Ekamra Sakha (SKH1) → 2 families
--   Kendra → Cuttack Anchalika → Cuttack Sakha (SKH2) → 1 family
--
-- Persons: 17 (P1–P17)
-- Memberships: 8 (SS1–SS8)
-- =====================================================
