-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 07_field_change_log.sql
-- Table: field_change_log
-- Depth: 0 (Root — no FK dependencies)
-- Sequence: #6 of 87
-- Version: 1.0
-- Authority: SOL-ARCH-010, SOL-FND-004 §41,
--            Data Change Architecture (2026-08-26)
-- Owner: NSS_ERP_ADMIN
-- Note: Shared field-level change tracking.
--       No FK dependencies — references are stored as
--       UUID values without constraints to avoid
--       circular dependencies. Application layer
--       enforces referential integrity.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.field_change_log
(
    field_change_log_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- Which DB operation produced this row. Set by
    -- nss.fn_audit_trigger(); NULL only for rows written
    -- directly (e.g. tests). On CREATE old_value is NULL;
    -- on DELETE new_value is NULL. Explicit rather than
    -- inferred, because an UPDATE that sets a field from
    -- NULL to a value is indistinguishable from a CREATE
    -- by looking at old_value alone.
    action VARCHAR(20) NULL
        CONSTRAINT chk_field_change_log_action
        CHECK (action IN ('CREATE', 'UPDATE', 'DELETE')),

    table_name VARCHAR(100) NOT NULL,

    record_pk UUID NOT NULL,

    field_name VARCHAR(100) NOT NULL,

    old_value TEXT NULL,

    new_value TEXT NULL,

    change_reason TEXT NULL,

    changed_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    changed_by_sangha_sevi_pk UUID NULL,

    -- Second actor identity. A user_account always exists
    -- for an authenticated write, but sangha_sevi_pk does
    -- not (accounts without a Sangha Sevi record), so this
    -- keeps "who" answerable in that case. Both are NULL
    -- for public/unauthenticated writes (registration) and
    -- for system/seed operations.
    changed_by_user_account_pk UUID NULL
);

CREATE INDEX IF NOT EXISTS idx_field_change_log_table_record
    ON nss.field_change_log (table_name, record_pk);

CREATE INDEX IF NOT EXISTS idx_field_change_log_changed_at
    ON nss.field_change_log (changed_at);

CREATE INDEX IF NOT EXISTS idx_field_change_log_field
    ON nss.field_change_log (table_name, field_name);

-- "Who changed what, when" lookups from the audit screen.
CREATE INDEX IF NOT EXISTS idx_field_change_log_actor
    ON nss.field_change_log (changed_by_sangha_sevi_pk, changed_at);

CREATE INDEX IF NOT EXISTS idx_field_change_log_action
    ON nss.field_change_log (action);
