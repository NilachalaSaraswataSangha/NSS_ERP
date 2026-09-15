-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 12_anumati_patra_history.sql
-- Table: nss.anumati_patra_history
-- Depth: 4 (depends on anumati_patra)
-- Version: 1.0
-- Authority: SOL-MEM-005 §13, SOL-MEM-003
-- Owner: NSS_ERP_ADMIN
-- Note: Stores historical changes to Anumati Patra
--       records. Historical records are never deleted.
-- =====================================================

CREATE TABLE nss.anumati_patra_history
(
    anumati_patra_history_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    anumati_patra_pk UUID NOT NULL,

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

    CONSTRAINT fk_ap_hist_ap
        FOREIGN KEY (anumati_patra_pk)
        REFERENCES nss.anumati_patra (anumati_patra_pk),

    CONSTRAINT chk_ap_hist_change_type
        CHECK
        (
            change_type IN ('ISSUED', 'RENEWED', 'EXPIRED', 'CANCELLED', 'REPLACED')
        ),

    CONSTRAINT chk_ap_hist_new_status
        CHECK
        (
            new_status IN ('ACTIVE', 'EXPIRED', 'CANCELLED', 'REPLACED')
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_ap_hist_ap
    ON nss.anumati_patra_history (anumati_patra_pk);

CREATE INDEX idx_ap_hist_change_date
    ON nss.anumati_patra_history (change_date);
