-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 07_system_setting.sql
-- Version: 1.1 — INSERT is now an upsert (ON CONFLICT ... DO UPDATE),
--          so a partial re-run no longer silently skips rows after
--          the first pre-existing row it hits
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
ON CONFLICT (setting_key) DO UPDATE SET
    setting_value = EXCLUDED.setting_value,
    description   = EXCLUDED.description,
    data_type     = EXCLUDED.data_type;
