-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 02_master_data.sql
-- Version: 1.0
-- Authority: SOL-FND-004 §7, §29
-- Owner: NSS_ERP_ADMIN
-- Note: References master_category by category_code
--       using subquery. Requires 01_master_category.sql
--       to have been executed first.
-- =====================================================

-- -------------------------------------------------
-- GENDER values
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    ('MALE',   'Male',   1),
    ('FEMALE', 'Female', 2),
    ('OTHER',  'Other',  3)
) AS v(value_code, value_name, display_order)
WHERE mc.category_code = 'GENDER';

-- -------------------------------------------------
-- MARITAL_STATUS values
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    ('UNMARRIED', 'Unmarried', 1),
    ('MARRIED',   'Married',   2),
    ('WIDOWED',   'Widowed',   3),
    ('DIVORCED',  'Divorced',  4),
    ('SEPARATED', 'Separated', 5)
) AS v(value_code, value_name, display_order)
WHERE mc.category_code = 'MARITAL_STATUS';

-- -------------------------------------------------
-- ADDRESS_TYPE values
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    ('PERMANENT', 'Permanent Address', 1),
    ('CURRENT',   'Current Address',   2),
    ('OFFICIAL',  'Official Address',  3)
) AS v(value_code, value_name, display_order)
WHERE mc.category_code = 'ADDRESS_TYPE';

-- -------------------------------------------------
-- DOCUMENT_TYPE values
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    ('PHOTO',              'Photograph',           1),
    ('ID_PROOF',           'Identity Proof',       2),
    ('ADDRESS_PROOF',      'Address Proof',        3),
    ('CERTIFICATE',        'Certificate',          4),
    ('CORRESPONDENCE',     'Correspondence',       5),
    ('PROPERTY_DOCUMENT',  'Property Document',    6),
    ('MEETING_MINUTES',    'Meeting Minutes',      7)
) AS v(value_code, value_name, display_order)
WHERE mc.category_code = 'DOCUMENT_TYPE';

-- -------------------------------------------------
-- MEMBERSHIP_TYPE values
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    ('PROBATIONARY', 'Probationary Member', 1),
    ('REGULAR',      'Regular Member',      2),
    ('ASSOCIATE',    'Associate Member',    3),
    ('HONORARY',     'Honorary Member',     4)
) AS v(value_code, value_name, display_order)
WHERE mc.category_code = 'MEMBERSHIP_TYPE';

-- -------------------------------------------------
-- STATUS values (unified ERP-wide lifecycle statuses)
-- Replaces per-module MEMBERSHIP_STATUS and
-- ORGANIZATION_STATUS. Each module picks its
-- applicable subset at the application layer.
-- Authority: NSS Bye-Law §D(d), §12, §I, §C
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, description, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.description, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    ('PROPOSED',    'Proposed',    'Entity proposed but not yet approved',                                1),
    ('APPROVED',    'Approved',    'Approved by governance, pending activation',                          2),
    ('ACTIVE',      'Active',      'Currently operational / active',                                     3),
    ('INACTIVE',    'Inactive',    'Temporarily non-operational',                                        4),
    ('SUSPENDED',   'Suspended',   'Suspended by governance decision',                                   5),
    ('LAPSED',      'Lapsed',      'Lapsed due to non-renewal or non-attendance (Bye-Law §D(d))',        6),
    ('TRANSFERRED', 'Transferred', 'Transferred to another unit',                                        7),
    ('RESIGNED',    'Resigned',    'Voluntarily departed',                                               8),
    ('EXPELLED',    'Expelled',    'Expelled by governance decision (Bye-Law §D(d)(iii))',                9),
    ('DECEASED',    'Deceased',    'Person is deceased (Bye-Law §D(d)(i))',                              10),
    ('DISSOLVED',   'Dissolved',   'Organization permanently dissolved (Bye-Law §I)',                    11),
    ('ARCHIVED',    'Archived',    'Permanently closed, retained for history',                           12),
    ('EXPIRED',     'Expired',     'Term or period has expired (Bye-Law §C(1)(c))',                      13)
) AS v(value_code, value_name, description, display_order)
WHERE mc.category_code = 'STATUS';

-- -------------------------------------------------
-- RELATIONSHIP_TYPE values
-- (Comprehensive for Indian family structure —
--  used by Family module for family_relationship)
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    -- Immediate family
    ('SPOUSE',             'Spouse',                   1),
    ('FATHER',             'Father',                   2),
    ('MOTHER',             'Mother',                   3),
    ('SON',                'Son',                      4),
    ('DAUGHTER',           'Daughter',                 5),
    ('BROTHER',            'Brother',                  6),
    ('SISTER',             'Sister',                   7),
    -- In-laws
    ('FATHER_IN_LAW',      'Father-in-Law',            8),
    ('MOTHER_IN_LAW',      'Mother-in-Law',            9),
    ('SON_IN_LAW',         'Son-in-Law',              10),
    ('DAUGHTER_IN_LAW',    'Daughter-in-Law',          11),
    ('BROTHER_IN_LAW',     'Brother-in-Law',          12),
    ('SISTER_IN_LAW',      'Sister-in-Law',           13),
    -- Grandparents / Grandchildren
    ('GRANDFATHER',        'Grandfather',             14),
    ('GRANDMOTHER',        'Grandmother',             15),
    ('GRANDSON',           'Grandson',                16),
    ('GRANDDAUGHTER',      'Granddaughter',           17),
    -- Uncle / Aunt / Nephew / Niece
    ('UNCLE',              'Uncle',                   18),
    ('AUNT',               'Aunt',                    19),
    ('NEPHEW',             'Nephew',                  20),
    ('NIECE',              'Niece',                   21),
    -- Cousins
    ('COUSIN',             'Cousin',                  22),
    -- Step relations
    ('STEP_FATHER',        'Step-Father',             23),
    ('STEP_MOTHER',        'Step-Mother',             24),
    ('STEP_SON',           'Step-Son',                25),
    ('STEP_DAUGHTER',      'Step-Daughter',           26),
    -- Guardian / Ward
    ('GUARDIAN',           'Guardian',                27),
    ('WARD',               'Ward',                    28),
    -- Other
    ('OTHER',              'Other Relative',          29)
) AS v(value_code, value_name, display_order)
WHERE mc.category_code = 'RELATIONSHIP_TYPE';

-- -------------------------------------------------
-- ORGANIZATION_TYPE values
-- (10 types per NSS Bye-Law hierarchy + preamble)
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, description, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.description, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    ('KENDRA',           'Kendra Sangha',     'Central Body — Apex Organization',                                    1),
    ('NILACHALA_KUTIRA', 'Nilachala Kutira',   'Eternal Abode - Puri',                                               2),
    ('SMRUTI_MANDIRA',   'Smruti Mandira',     'Nigamananda Smruti Mandir',                                          3),
    ('ANCHALIKA_SANGHA', 'Anchalika Sangha',   'Administrative unit — intermediate organizational level',             4),
    ('ZILLA_SANGHA',     'Zilla Sangha',       'Administrative unit — intermediate organizational level',             5),
    ('SAKHA_SANGHA',     'Sakha Sangha',       'Physical Sangha location — branch with own building',                 6),
    ('SAKHA_ASANA',      'Sakha Asana',        'Approved Sakha without own building',                                 7),
    ('PARIBARIK_ASANA',  'Paribarik Asana',    'Family-level Asana — per Parichay Patra holder; renewed with Parichay Patra — Bye-Law §C(2)(iii)', 8),
    ('PARIBARIK_SANGHA', 'Paribarik Sangha',   'Family organisation attached to Kendra — Bye-Law Preamble',             9),
    ('PATHA_CHAKRA',     'Patha Chakra',       'Study Circle',                                                        10)
) AS v(value_code, value_name, description, display_order)
WHERE mc.category_code = 'ORGANIZATION_TYPE';

-- -------------------------------------------------
-- (STATUS values are above — unified ERP-wide category
--  replaces the former per-module ORGANIZATION_STATUS)
-- -------------------------------------------------

-- -------------------------------------------------
-- BLOOD_GROUP values
-- -------------------------------------------------

INSERT INTO nss.master_data (master_category_pk, value_code, value_name, display_order)
SELECT mc.master_category_pk, v.value_code, v.value_name, v.display_order
FROM nss.master_category mc
CROSS JOIN (VALUES
    ('A_POSITIVE',  'A+',  1),
    ('A_NEGATIVE',  'A-',  2),
    ('B_POSITIVE',  'B+',  3),
    ('B_NEGATIVE',  'B-',  4),
    ('AB_POSITIVE', 'AB+', 5),
    ('AB_NEGATIVE', 'AB-', 6),
    ('O_POSITIVE',  'O+',  7),
    ('O_NEGATIVE',  'O-',  8)
) AS v(value_code, value_name, display_order)
WHERE mc.category_code = 'BLOOD_GROUP';
