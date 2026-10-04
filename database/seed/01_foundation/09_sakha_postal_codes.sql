-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 09_sakha_postal_codes.sql
-- Version: 1.0
-- Authority: NSS Branches directory
-- Owner: NSS_ERP_ADMIN
-- Note: Postal codes referenced by Sakha branch
--       addresses. Minimal bootstrap — only PINs
--       that appear in the branch directory.
--       Total: 56 unique codes.
-- =====================================================

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '110068'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'DL'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '249201'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'UK'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '27243'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'US'
  AND s.state_code = 'NC'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '394221'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'GJ'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '410206'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'MH'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '412110'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'MH'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '491111'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'CT'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '502032'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'TS'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '562114'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'KA'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '600116'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'TN'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '711203'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'WB'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '751022'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '752061'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '752062'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '752066'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754004'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754008'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754025'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754032'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754037'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754110'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754114'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754140'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754142'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754203'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754215'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754223'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754224'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754225'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754244'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754246'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '754282'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '755009'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '755019'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '756045'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '756046'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '756048'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '756100'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '757001'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '757056'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '757167'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '758034'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '759021'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '759106'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '759107'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '759122'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '759131'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '759132'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '761029'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '761133'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '764051'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '764085'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '766118'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '767035'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '770016'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '831005'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'JH'
ON CONFLICT (postal_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;
