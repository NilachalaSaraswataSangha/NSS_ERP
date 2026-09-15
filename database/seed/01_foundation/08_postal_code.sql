-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 08_postal_code.sql
-- Version: 1.1 — every INSERT is now an upsert (ON CONFLICT ... DO UPDATE),
--          so a partial re-run no longer silently skips every block after
--          the first pre-existing row it hits
-- Authority: SOL-FND-004, SOL-ARCH-010 §8
-- Owner: NSS_ERP_ADMIN
-- Note: Seed postal codes referenced by Organization
--       seed data. This is a minimal bootstrap set —
--       full postal code data loading is a future task.
-- =====================================================

-- Bhubaneswar — Kendra (Satsikshya Mandir, Unit-9)
INSERT INTO nss.postal_code (country_pk, state_pk, postal_code, post_office_name)
SELECT c.country_pk, s.state_pk, '751022', 'Unit 9 SO'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (country_pk, postal_code) DO UPDATE SET
    state_pk          = EXCLUDED.state_pk,
    post_office_name  = EXCLUDED.post_office_name;

-- Puri — Nilachala Kutira, Smruti Mandira (Swargadwar area)
INSERT INTO nss.postal_code (country_pk, state_pk, postal_code, post_office_name)
SELECT c.country_pk, s.state_pk, '752001', 'Puri HO'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (country_pk, postal_code) DO UPDATE SET
    state_pk          = EXCLUDED.state_pk,
    post_office_name  = EXCLUDED.post_office_name;

-- Cuttack — Tier 4 verification (second Sakha location)
INSERT INTO nss.postal_code (country_pk, state_pk, postal_code, post_office_name)
SELECT c.country_pk, s.state_pk, '753001', 'Cuttack HO'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (country_pk, postal_code) DO UPDATE SET
    state_pk          = EXCLUDED.state_pk,
    post_office_name  = EXCLUDED.post_office_name;
