-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 07_system_setting.sql
-- Version: 1.2 — ON CONFLICT DO NOTHING (2026-10-05), not DO UPDATE: a
--          re-run (e.g. adding a new tier's seed to a live database) must
--          never overwrite a setting_value an admin has since changed
--          through the Settings screen. Insert-if-missing only.
-- Authority: SOL-FND-004 §10
-- Owner: NSS_ERP_ADMIN
-- Note: Initial system settings. Values are
--       illustrative defaults; actual production
--       values configured during deployment.
-- =====================================================

INSERT INTO nss.system_setting
(
    setting_key,
    setting_value,
    description,
    data_type
)
VALUES
(
    'CURRENT_MEMBERSHIP_YEAR',
    '2026-2027',
    'Active membership year (financial year format)',
    'STRING'
),
(
    'DEFAULT_COUNTRY',
    'IN',
    'Default country code for new records',
    'STRING'
),
(
    'PASSWORD_EXPIRY_DAYS',
    '90',
    'Number of days before password expiry',
    'INTEGER'
),
(
    'MAX_LOGIN_ATTEMPTS',
    '5',
    'Maximum consecutive failed login attempts before lockout',
    'INTEGER'
),
(
    'MEMBERSHIP_DARSHAK_LOCAL_ID_MARKER',
    'D',
    'Namespace marker inserted between the Sakha short code and the local '
    'number for Darshak/Probationary local Sakha identifiers, per MBR-030C '
    '(e.g. ESSD000045 vs the Regular ESS000123). Kept configurable so the '
    'marker is never hardcoded in application code. Changing it does not '
    'rewrite identifiers already issued.',
    'STRING'
)
ON CONFLICT (setting_key) DO NOTHING;
