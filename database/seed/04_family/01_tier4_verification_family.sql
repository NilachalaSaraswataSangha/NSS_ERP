-- =====================================================
-- NSS ERP
-- Module: Family
-- Seed File: 01_tier4_verification_family.sql
-- Version: 2.0
-- Authority: Tier 4 verification seed
-- Owner: NSS_ERP_ADMIN
-- Note: Creates one family group (Mishra family) at
--       Ekamra Sakha with 8 relationships spanning
--       3 generations and one family head assignment.
--
--       Gen -1 (Parents):      P9 Harekrushna (FATHER), P10 Saraswati (MOTHER)
--       Gen  0 (Head row):     P1 Ramesh (HEAD), P2 Sushma (SPOUSE),
--                              P12 Rajesh (BROTHER), P13 Kabita (SISTER_IN_LAW)
--       Gen +1 (Children):     P3 Aniket (SON), P11 Anita (DAUGHTER)
-- =====================================================

-- -------------------------------------------------
-- Family Group: Mishra Family at Ekamra Sakha
-- -------------------------------------------------

INSERT INTO nss.family_group
    (family_id, family_name, family_status_master_data_pk,
     sakha_organization_pk, formed_date)
SELECT
    'F1',
    'Mishra Paribara',
    st.master_data_pk,
    sakha.organization_pk,
    '2010-04-01'
FROM nss.master_data st
JOIN nss.master_category mc ON mc.master_category_pk = st.master_category_pk
CROSS JOIN nss.organization sakha
WHERE mc.category_code = 'STATUS' AND st.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH1';

-- -------------------------------------------------
-- Family Relationships
-- -------------------------------------------------

-- Ramesh Mishra — FATHER (family head)
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT
    fg.family_group_pk,
    p.person_pk,
    rt.master_data_pk,
    '2010-04-01',
    TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P1'
  AND mc.category_code = 'RELATIONSHIP_TYPE'
  AND rt.value_code = 'FATHER';

-- Sushma Mishra — SPOUSE
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT
    fg.family_group_pk,
    p.person_pk,
    rt.master_data_pk,
    '2010-04-01',
    TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P2'
  AND mc.category_code = 'RELATIONSHIP_TYPE'
  AND rt.value_code = 'SPOUSE';

-- Aniket Mishra — SON
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT
    fg.family_group_pk,
    p.person_pk,
    rt.master_data_pk,
    '2010-04-01',
    TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P3'
  AND mc.category_code = 'RELATIONSHIP_TYPE'
  AND rt.value_code = 'SON';

-- Anita Mishra — DAUGHTER
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT
    fg.family_group_pk,
    p.person_pk,
    rt.master_data_pk,
    '2010-04-01',
    TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P11'
  AND mc.category_code = 'RELATIONSHIP_TYPE'
  AND rt.value_code = 'DAUGHTER';

-- Harekrushna Mishra — FATHER (of the HEAD)
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT
    fg.family_group_pk,
    p.person_pk,
    rt.master_data_pk,
    '2010-04-01',
    TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P9'
  AND mc.category_code = 'RELATIONSHIP_TYPE'
  AND rt.value_code = 'FATHER';

-- Saraswati Mishra — MOTHER (of the HEAD)
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT
    fg.family_group_pk,
    p.person_pk,
    rt.master_data_pk,
    '2010-04-01',
    TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P10'
  AND mc.category_code = 'RELATIONSHIP_TYPE'
  AND rt.value_code = 'MOTHER';

-- Rajesh Mishra — BROTHER
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT
    fg.family_group_pk,
    p.person_pk,
    rt.master_data_pk,
    '2010-04-01',
    TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P12'
  AND mc.category_code = 'RELATIONSHIP_TYPE'
  AND rt.value_code = 'BROTHER';

-- Kabita Mishra — SISTER_IN_LAW
INSERT INTO nss.family_relationship
    (family_group_pk, person_pk, relationship_type_master_data_pk,
     effective_from, is_current)
SELECT
    fg.family_group_pk,
    p.person_pk,
    rt.master_data_pk,
    '2010-04-01',
    TRUE
FROM nss.family_group fg
CROSS JOIN nss.person p
CROSS JOIN nss.master_data rt
JOIN nss.master_category mc ON mc.master_category_pk = rt.master_category_pk
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P13'
  AND mc.category_code = 'RELATIONSHIP_TYPE'
  AND rt.value_code = 'SISTER_IN_LAW';

-- -------------------------------------------------
-- Family Head History: Ramesh is current head
-- -------------------------------------------------

INSERT INTO nss.family_head_history
    (family_group_pk, person_pk, effective_from)
SELECT
    fg.family_group_pk,
    p.person_pk,
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person p
WHERE fg.family_id = 'F1'
  AND p.person_id = 'P1';
