-- Fix: run only the sections that failed on first attempt
-- (persons, families, relationships, links, heads all succeeded)

-- SS6: Meera Patel — Regular member at SKH2
INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT 'SS6', p.person_pk, mt.master_data_pk, ms.master_data_pk,
       sakha.organization_pk, '2016-04-01', '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P14'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'REGULAR'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH2';

-- SS7: Laxmi Rath — Regular member at SKH2
INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date, renewal_due_date)
SELECT 'SS7', p.person_pk, mt.master_data_pk, ms.master_data_pk,
       sakha.organization_pk, '2013-04-01', '2027-03-31'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P16'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'REGULAR'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH2';

-- SS8: Pallavi Rath — Probationary at SKH2
INSERT INTO nss.sangha_sevi
    (sangha_sevi_id, person_pk, membership_type_master_data_pk,
     membership_status_master_data_pk, organization_pk,
     joining_date)
SELECT 'SS8', p.person_pk, mt.master_data_pk, ms.master_data_pk,
       sakha.organization_pk, '2020-04-01'
FROM nss.person p
CROSS JOIN nss.master_data mt
JOIN nss.master_category mc_mt ON mc_mt.master_category_pk = mt.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
CROSS JOIN nss.organization sakha
WHERE p.person_id = 'P17'
  AND mc_mt.category_code = 'MEMBERSHIP_TYPE' AND mt.value_code = 'PROBATIONARY'
  AND mc_ms.category_code = 'STATUS' AND ms.value_code = 'ACTIVE'
  AND sakha.organization_code = 'SKH2';

-- Affiliations
INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT ss.sangha_sevi_pk, o.organization_pk, 'CTC2', '2016-04-01', 'ACTIVE', 'ENROLLMENT'
FROM nss.sangha_sevi ss CROSS JOIN nss.organization o
WHERE ss.sangha_sevi_id = 'SS6' AND o.organization_code = 'SKH2';

INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT ss.sangha_sevi_pk, o.organization_pk, 'CTC3', '2013-04-01', 'ACTIVE', 'ENROLLMENT'
FROM nss.sangha_sevi ss CROSS JOIN nss.organization o
WHERE ss.sangha_sevi_id = 'SS7' AND o.organization_code = 'SKH2';

INSERT INTO nss.membership_sakha_affiliation
    (sangha_sevi_pk, organization_pk, local_sakha_erp_id,
     effective_from, affiliation_status, source_event_type)
SELECT ss.sangha_sevi_pk, o.organization_pk, 'CTC4', '2020-04-01', 'ACTIVE', 'ENROLLMENT'
FROM nss.sangha_sevi ss CROSS JOIN nss.organization o
WHERE ss.sangha_sevi_id = 'SS8' AND o.organization_code = 'SKH2';

-- Parichaya Patra
INSERT INTO nss.parichaya_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status, affiliated_organization_pk, local_sakha_erp_id)
SELECT ss.sangha_sevi_pk, '601/2026/2027', '2026-04-15',
       '2026-04-01', '2027-03-31', 'ACTIVE', sakha.organization_pk, 'CTC2'
FROM nss.sangha_sevi ss CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS6' AND sakha.organization_code = 'SKH2';

INSERT INTO nss.parichaya_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status, affiliated_organization_pk, local_sakha_erp_id)
SELECT ss.sangha_sevi_pk, '602/2026/2027', '2026-04-15',
       '2026-04-01', '2027-03-31', 'ACTIVE', sakha.organization_pk, 'CTC3'
FROM nss.sangha_sevi ss CROSS JOIN nss.organization sakha
WHERE ss.sangha_sevi_id = 'SS7' AND sakha.organization_code = 'SKH2';

-- Anumati Patra for Darshaka Pallavi
INSERT INTO nss.anumati_patra
    (sangha_sevi_pk, document_number, issue_date,
     valid_from, valid_to, status)
SELECT ss.sangha_sevi_pk, 'AP/2026/03', '2026-04-20',
       '2026-04-01', '2027-03-31', 'ACTIVE'
FROM nss.sangha_sevi ss WHERE ss.sangha_sevi_id = 'SS8';
