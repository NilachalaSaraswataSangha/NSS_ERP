-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 04_membership_renewal_history.sql
-- Table: nss.membership_renewal_history
-- Depth: 3 (depends on sangha_sevi)
-- Version: 1.0
-- Authority: SOL-MEM-005 §8, SOL-MEM-003
-- Owner: NSS_ERP_ADMIN
-- Note: Every completed renewal is permanently
--       traceable. Renewals follow the NSS financial
--       year (1 April – 31 March).
-- =====================================================

CREATE TABLE nss.membership_renewal_history
(
    membership_renewal_history_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    renewal_date DATE NOT NULL,

    valid_from DATE NOT NULL,

    valid_to DATE NOT NULL,

    approved_by_sangha_sevi_pk UUID NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_mem_renewal_hist_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk),

    CONSTRAINT chk_mem_renewal_hist_validity
        CHECK (valid_to > valid_from)
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_mem_renewal_hist_sevi
    ON nss.membership_renewal_history (sangha_sevi_pk);

CREATE INDEX idx_mem_renewal_hist_valid_range
    ON nss.membership_renewal_history (valid_from, valid_to);
