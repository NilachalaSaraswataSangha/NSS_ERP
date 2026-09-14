-- =====================================================
-- NSS ERP
-- Module: Family
-- Seed File: 01_tier4_verification_family.sql
-- Version: 1.0
-- Authority: Tier 4 verification seed
-- Owner: NSS_ERP_ADMIN
-- Note: Creates one family group (Mishra family) at
--       Ekamra Sakha with 3 relationships (father,
--       spouse, son) and one family head assignment.
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
