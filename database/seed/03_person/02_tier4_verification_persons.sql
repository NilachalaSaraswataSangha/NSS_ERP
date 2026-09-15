-- =====================================================
-- NSS ERP
-- Module: Person
-- Seed File: 02_tier4_verification_persons.sql
-- Version: 2.0
-- Authority: Tier 4 verification seed
-- Owner: NSS_ERP_ADMIN
-- Note: Adds 8 test persons for Family + Membership
--       verification. Gender and marital status
--       resolved via Foundation master_data subquery.
--       No Aadhaar data (all NULL — consistent).
--
--       P1: Ramesh Mishra  — Regular member (SS1)
--       P2: Sushma Mishra  — Non-member spouse
--       P3: Aniket Mishra  — Probationary member (SS2)
--       P4: Suresh Patel   — Regular member, transferred
--                             SKH1 → SKH2 (SS3)
--       P5: Debasis Rath   — Associate member (SS4)
--       P6: Priyanka Das   — Kumari participant
--                             (Person without Membership)
--       P7: Soumya Nayak   — Kishor participant
--                             (Person without Membership)
--       P8: Smita Sahoo    — Former Kumari participant,
--                             now Probationary member (SS5).
--                             Kumari Transition
--                             (01_membership_module_overview.md §6)
--       P9: Harekrushna Mishra — Ramesh's father (grandfather
--                                 in Mishra family tree)
--       P10: Saraswati Mishra  — Ramesh's mother (grandmother)
--       P11: Anita Mishra      — Ramesh's daughter
--       P12: Rajesh Mishra     — Ramesh's brother
--       P13: Kabita Mishra     — Rajesh's wife (sister-in-law)
-- =====================================================

-- Person 1: Ramesh Mishra (father / family head)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P1',
    'Ramesh',
    'Mishra',
    '1975-06-15',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100001',
    'ramesh.mishra@example.com'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'MALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'MARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number,
    email                         = EXCLUDED.email;

-- Person 2: Sushma Mishra (spouse)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P2',
    'Sushma',
    'Mishra',
    '1978-03-22',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100002',
    'sushma.mishra@example.com'
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
    email                         = EXCLUDED.email;

-- Person 3: Aniket Mishra (son — unmarried, probationary member)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P3',
    'Aniket',
    'Mishra',
    '2000-11-10',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100003',
    'aniket.mishra@example.com'
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
    mobile_number                 = EXCLUDED.mobile_number,
    email                         = EXCLUDED.email;

-- Person 4: Suresh Patel (Regular member, transferred SKH1 → SKH2)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P4',
    'Suresh',
    'Patel',
    '1980-02-14',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100004',
    'suresh.patel@example.com'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'MALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'MARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number,
    email                         = EXCLUDED.email;

-- Person 5: Debasis Rath (Associate member — enrolled by Parichalak)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P5',
    'Debasis',
    'Rath',
    '1965-07-20',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100005',
    'debasis.rath@example.com'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'MALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'MARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number,
    email                         = EXCLUDED.email;

-- Person 6: Priyanka Das (Kumari participant — Person without Membership)
-- Per 01_membership_module_overview.md §2: Kumari Participants
-- are Persons without Membership.
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number)
SELECT
    'P6',
    'Priyanka',
    'Das',
    '2012-03-08',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100006'
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
    mobile_number                 = EXCLUDED.mobile_number;

-- Person 7: Soumya Nayak (Kishor participant — Person without Membership)
-- Per 01_membership_module_overview.md §2: Kishor Participants
-- are Persons without Membership.
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number)
SELECT
    'P7',
    'Soumya',
    'Nayak',
    '2011-09-15',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100007'
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

-- Person 8: Smita Sahoo (Former Kumari participant → NSS member)
-- Per 01_membership_module_overview.md §6: Kumari Transition is
-- a documented Membership source. She was an active Kumari
-- participant who transitioned to formal NSS Membership.
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number, email)
SELECT
    'P8',
    'Smita',
    'Sahoo',
    '2003-05-20',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100008',
    'smita.sahoo@example.com'
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
    email                         = EXCLUDED.email;

-- -------------------------------------------------
-- Persons 9–13: Extended Mishra family for tree
-- -------------------------------------------------

-- Person 9: Harekrushna Mishra (Ramesh's father — grandfather in family tree)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number)
SELECT
    'P9',
    'Harekrushna',
    'Mishra',
    '1945-01-10',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100009'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'MALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'MARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number;

-- Person 10: Saraswati Mishra (Ramesh's mother — grandmother in family tree)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number)
SELECT
    'P10',
    'Saraswati',
    'Mishra',
    '1948-08-25',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100010'
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
    mobile_number                 = EXCLUDED.mobile_number;

-- Person 11: Anita Mishra (Ramesh & Sushma's daughter)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number)
SELECT
    'P11',
    'Anita',
    'Mishra',
    '2003-04-18',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100011'
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
    mobile_number                 = EXCLUDED.mobile_number;

-- Person 12: Rajesh Mishra (Ramesh's younger brother)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number)
SELECT
    'P12',
    'Rajesh',
    'Mishra',
    '1978-12-05',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100012'
FROM nss.master_data g
JOIN nss.master_category mc_g ON mc_g.master_category_pk = g.master_category_pk
CROSS JOIN nss.master_data ms
JOIN nss.master_category mc_ms ON mc_ms.master_category_pk = ms.master_category_pk
WHERE mc_g.category_code = 'GENDER' AND g.value_code = 'MALE'
  AND mc_ms.category_code = 'MARITAL_STATUS' AND ms.value_code = 'MARRIED'
ON CONFLICT (person_id) DO UPDATE SET
    first_name                    = EXCLUDED.first_name,
    last_name                     = EXCLUDED.last_name,
    date_of_birth                 = EXCLUDED.date_of_birth,
    gender_master_data_pk         = EXCLUDED.gender_master_data_pk,
    marital_status_master_data_pk = EXCLUDED.marital_status_master_data_pk,
    country_phone_code            = EXCLUDED.country_phone_code,
    mobile_number                 = EXCLUDED.mobile_number;

-- Person 13: Kabita Mishra (Rajesh's wife — sister-in-law to Ramesh)
INSERT INTO nss.person
    (person_id, first_name, last_name, date_of_birth,
     gender_master_data_pk, marital_status_master_data_pk,
     country_phone_code, mobile_number)
SELECT
    'P13',
    'Kabita',
    'Mishra',
    '1980-06-20',
    g.master_data_pk,
    ms.master_data_pk,
    '+91',
    '9437100013'
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
    mobile_number                 = EXCLUDED.mobile_number;
