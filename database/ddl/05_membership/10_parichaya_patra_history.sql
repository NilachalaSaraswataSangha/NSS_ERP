-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 10_parichaya_patra_history.sql
-- Table: nss.parichaya_patra_history
-- Depth: 4 (depends on parichaya_patra)
-- Version: 1.0
-- Authority: SOL-MEM-005 §15, SOL-MEM-003
-- Owner: NSS_ERP_ADMIN
-- Note: Stores historical changes to Parichaya Patra
--       records (status changes, replacements, etc.).
--       Historical records are never deleted.
-- =====================================================

CREATE TABLE nss.parichaya_patra_history
(
    parichaya_patra_history_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    parichaya_patra_pk UUID NOT NULL,

    -- ISSUED, RENEWED, EXPIRED, CANCELLED, REPLACED
    change_type VARCHAR(20) NOT NULL,

    change_date DATE NOT NULL,

    previous_status VARCHAR(20) NULL,

    new_status VARCHAR(20) NOT NULL,

    document_reference VARCHAR(255) NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_pp_hist_pp
        FOREIGN KEY (parichaya_patra_pk)
        REFERENCES nss.parichaya_patra (parichaya_patra_pk),

    CONSTRAINT chk_pp_hist_change_type
        CHECK
        (
            change_type IN ('ISSUED', 'RENEWED', 'EXPIRED', 'CANCELLED', 'REPLACED')
        ),

    CONSTRAINT chk_pp_hist_new_status
        CHECK
        (
            new_status IN ('ACTIVE', 'EXPIRED', 'CANCELLED', 'REPLACED')
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_pp_hist_pp
    ON nss.parichaya_patra_history (parichaya_patra_pk);

CREATE INDEX idx_pp_hist_change_date
    ON nss.parichaya_patra_history (change_date);
