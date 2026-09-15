-- =====================================================
-- NSS ERP
-- Module: Organization
-- Seed File: 04_tier4_verification_orgs.sql
-- Version: 2.0
-- Authority: Tier 4 verification seed
-- Owner: NSS_ERP_ADMIN
-- Note: Adds two Anchalikas and two Sakhas under Kendra
--       for Family + Membership verification.
--       SKH1 (Ekamra) — primary Sakha.
--       SKH2 (Cuttack) — transfer-target Sakha.
--       These are representative test organizations.
-- =====================================================

-- -------------------------------------------------
-- Anchalika Sangha: Puri Anchalika
-- (parent = Kendra Sangha)
-- Note: Anchalika is an administrative grouping,
--       NOT a physical location — no address fields.
-- -------------------------------------------------

INSERT INTO nss.organization
    (organization_name, organization_type_master_data_pk,
     status_master_data_pk, parent_organization_pk,
     organization_code)
SELECT
    'Puri Anchalika Sangha',
    ot.master_data_pk,
    os.master_data_pk,
    kendra.organization_pk,
    'ANC1'
FROM nss.master_data ot
JOIN nss.master_category mc_type
     ON mc_type.master_category_pk = ot.master_category_pk
CROSS JOIN nss.master_data os
JOIN nss.master_category mc_status
     ON mc_status.master_category_pk = os.master_category_pk
CROSS JOIN nss.organization kendra
WHERE mc_type.category_code = 'ORGANIZATION_TYPE'
  AND ot.value_code = 'ANCHALIKA_SANGHA'
  AND mc_status.category_code = 'STATUS'
  AND os.value_code = 'ACTIVE'
  AND kendra.organization_code = 'KEN';

-- -------------------------------------------------
-- Sakha Sangha: Ekamra Sakha
-- (parent = Ekamra Anchalika)
-- -------------------------------------------------

INSERT INTO nss.organization
    (organization_name, organization_type_master_data_pk,
     status_master_data_pk, parent_organization_pk,
     organization_code,
     address_line_1, address_line_2, postal_code_pk, country_pk)
SELECT
    'Ekamra Sakha Sangha',
    ot.master_data_pk,
    os.master_data_pk,
    anch.organization_pk,
    'SKH1',
    'Old Town, Bhubaneswar',
    NULL,
    pc.postal_code_pk,
    c.country_pk
FROM nss.master_data ot
JOIN nss.master_category mc_type
     ON mc_type.master_category_pk = ot.master_category_pk
CROSS JOIN nss.master_data os
JOIN nss.master_category mc_status
     ON mc_status.master_category_pk = os.master_category_pk
CROSS JOIN nss.country c
CROSS JOIN nss.postal_code pc
CROSS JOIN nss.organization anch
WHERE mc_type.category_code = 'ORGANIZATION_TYPE'
  AND ot.value_code = 'SAKHA_SANGHA'
  AND mc_status.category_code = 'STATUS'
  AND os.value_code = 'ACTIVE'
  AND c.country_code = 'IN'
  AND pc.postal_code = '751022'
  AND pc.country_pk = c.country_pk
  AND anch.organization_code = 'ANC1';

-- -------------------------------------------------
-- Anchalika Sangha: Cuttack Anchalika
-- (parent = Kendra Sangha)
-- -------------------------------------------------

INSERT INTO nss.organization
    (organization_name, organization_type_master_data_pk,
     status_master_data_pk, parent_organization_pk,
     organization_code)
SELECT
    'Cuttack Anchalika Sangha',
    ot.master_data_pk,
    os.master_data_pk,
    kendra.organization_pk,
    'ANC2'
FROM nss.master_data ot
JOIN nss.master_category mc_type
     ON mc_type.master_category_pk = ot.master_category_pk
CROSS JOIN nss.master_data os
JOIN nss.master_category mc_status
     ON mc_status.master_category_pk = os.master_category_pk
CROSS JOIN nss.organization kendra
WHERE mc_type.category_code = 'ORGANIZATION_TYPE'
  AND ot.value_code = 'ANCHALIKA_SANGHA'
  AND mc_status.category_code = 'STATUS'
  AND os.value_code = 'ACTIVE'
  AND kendra.organization_code = 'KEN';

-- -------------------------------------------------
-- Sakha Sangha: Cuttack Sakha
-- (parent = Cuttack Anchalika)
-- Transfer-target Sakha for Tier 4 verification.
-- -------------------------------------------------

INSERT INTO nss.organization
    (organization_name, organization_type_master_data_pk,
     status_master_data_pk, parent_organization_pk,
     organization_code,
     address_line_1, address_line_2, postal_code_pk, country_pk)
SELECT
    'Cuttack Sakha Sangha',
    ot.master_data_pk,
    os.master_data_pk,
    anch.organization_pk,
    'SKH2',
    'Buxi Bazar, Cuttack',
    NULL,
    pc.postal_code_pk,
    c.country_pk
FROM nss.master_data ot
JOIN nss.master_category mc_type
     ON mc_type.master_category_pk = ot.master_category_pk
CROSS JOIN nss.master_data os
JOIN nss.master_category mc_status
     ON mc_status.master_category_pk = os.master_category_pk
CROSS JOIN nss.country c
CROSS JOIN nss.postal_code pc
CROSS JOIN nss.organization anch
WHERE mc_type.category_code = 'ORGANIZATION_TYPE'
  AND ot.value_code = 'SAKHA_SANGHA'
  AND mc_status.category_code = 'STATUS'
  AND os.value_code = 'ACTIVE'
  AND c.country_code = 'IN'
  AND pc.postal_code = '753001'
  AND pc.country_pk = c.country_pk
  AND anch.organization_code = 'ANC2';
