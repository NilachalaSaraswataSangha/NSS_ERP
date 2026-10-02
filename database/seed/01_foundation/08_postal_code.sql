-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 08_postal_code.sql
-- Version: 2.0 — SOL-ARCH-010 Amendment (Simplified Geography
--          Model, 2026-10-02): postal_code no longer carries
--          country_pk or post_office_name. These 3 PINs are
--          also present in the all-India 08b bulk load (same
--          PIN, same state) — this file is now effectively a
--          no-op safety net for the Organization seed, kept so
--          08b is not a hard prerequisite.
-- Authority: SOL-FND-004, SOL-ARCH-010 §8
-- Owner: NSS_ERP_ADMIN
-- Note: Seed postal codes referenced by Organization
--       seed data. This is a minimal bootstrap set —
--       full postal code data loading is a future task.
-- =====================================================

-- Bhubaneswar — Kendra (Satsikshya Mandir, Unit-9)
INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '751022'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code) DO UPDATE SET
    state_pk = EXCLUDED.state_pk;

-- Puri — Nilachala Kutira, Smruti Mandira (Swargadwar area)
INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '752001'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code) DO UPDATE SET
    state_pk = EXCLUDED.state_pk;

-- Cuttack — Tier 4 verification (second Sakha location)
INSERT INTO nss.postal_code (state_pk, postal_code)
SELECT s.state_pk, '753001'
FROM nss.country c
JOIN nss.state s ON s.country_pk = c.country_pk
WHERE c.country_code = 'IN'
  AND s.state_code = 'OD'
ON CONFLICT (postal_code) DO UPDATE SET
    state_pk = EXCLUDED.state_pk;
