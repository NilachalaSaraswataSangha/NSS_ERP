-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 02_membership_status_history.sql
-- Table: nss.membership_status_history
-- Depth: 3 (depends on sangha_sevi, master_data)
-- Version: 1.0
-- Authority: SOL-MEM-005 §6, SOL-MEM-003
-- Owner: NSS_ERP_ADMIN
-- Note: Historical records are never deleted.
--       Current status is on sangha_sevi; this table
--       preserves the full status change timeline.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.membership_status_history
(
    membership_status_history_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    -- Status value from unified STATUS category.
    membership_status_master_data_pk UUID NOT NULL,

    effective_from TIMESTAMPTZ NOT NULL,

    effective_to TIMESTAMPTZ NULL,

    reason VARCHAR(500) NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_mem_status_hist_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk),

    CONSTRAINT fk_mem_status_hist_status
        FOREIGN KEY (membership_status_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT chk_mem_status_hist_range
        CHECK
        (
            effective_to IS NULL
            OR effective_to >= effective_from
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_mem_status_hist_sevi
    ON nss.membership_status_history (sangha_sevi_pk);

CREATE INDEX IF NOT EXISTS idx_mem_status_hist_status
    ON nss.membership_status_history (membership_status_master_data_pk);

CREATE INDEX IF NOT EXISTS idx_mem_status_hist_effective
    ON nss.membership_status_history (effective_from);
