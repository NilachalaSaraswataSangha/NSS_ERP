-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 04_country.sql
-- Version: 3.0 — INSERT is now an upsert (ON CONFLICT ... DO UPDATE), so a
--          partial re-run no longer silently skips every row after the
--          first pre-existing row it hits
-- Authority: SOL-FND-004 §30
-- Owner: NSS_ERP_ADMIN
-- =====================================================

INSERT INTO nss.country
(
    country_code,
    country_name,
    display_order
)
VALUES
('IN', 'India',          1),
('US', 'United States',  2),
('GB', 'United Kingdom', 3),
('AU', 'Australia',      4),
('CA', 'Canada',         5)
ON CONFLICT (country_code) DO UPDATE SET
    country_name  = EXCLUDED.country_name,
    display_order = EXCLUDED.display_order;
