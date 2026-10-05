-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 04_country.sql
-- Version: 3.1 — ON CONFLICT DO NOTHING, not DO UPDATE (2026-10-05): a
--          re-run must never overwrite a country row an admin has edited.
--          Insert-if-missing only.
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
ON CONFLICT (country_code) DO NOTHING;
