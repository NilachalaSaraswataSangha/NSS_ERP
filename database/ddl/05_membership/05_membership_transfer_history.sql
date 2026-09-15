-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 05_membership_transfer_history.sql
-- Table: nss.membership_transfer_history
-- Depth: 3 (depends on sangha_sevi, organization x2)
-- Version: 1.0
-- Authority: SOL-MEM-005 §9, SOL-MEM-003
-- Owner: NSS_ERP_ADMIN
-- Note: Transfer history is never deleted.
--       Sangha Sevi ID does not change on transfer.
--       old/new_local_sakha_erp_id are historical
--       transition snapshots — the authoritative
--       current ID resides on
--       membership_sakha_affiliation (§27.1).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.membership_transfer_history
(
    membership_transfer_history_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    old_organization_pk UUID NOT NULL,

    new_organization_pk UUID NOT NULL,

    -- INTRA_ANCHALIKA, INTER_ANCHALIKA, INTER_ZILLA, etc.
    transfer_type VARCHAR(50) NOT NULL,

    transfer_reason VARCHAR(500) NULL,

    requested_date DATE NULL,

    approved_date DATE NULL,

    effective_date DATE NOT NULL,

    -- Historical snapshot of Local Sakha ERP IDs at the
    -- time of transfer. Not the authoritative source.
    old_local_sakha_erp_id VARCHAR(30) NULL,

    new_local_sakha_erp_id VARCHAR(30) NULL,

    approved_by_sangha_sevi_pk UUID NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_mem_transfer_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk),

    CONSTRAINT fk_mem_transfer_old_org
        FOREIGN KEY (old_organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT fk_mem_transfer_new_org
        FOREIGN KEY (new_organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT chk_mem_transfer_different_orgs
        CHECK (old_organization_pk <> new_organization_pk)
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_mem_transfer_sevi
    ON nss.membership_transfer_history (sangha_sevi_pk);

CREATE INDEX IF NOT EXISTS idx_mem_transfer_old_org
    ON nss.membership_transfer_history (old_organization_pk);

CREATE INDEX IF NOT EXISTS idx_mem_transfer_new_org
    ON nss.membership_transfer_history (new_organization_pk);

CREATE INDEX IF NOT EXISTS idx_mem_transfer_effective
    ON nss.membership_transfer_history (effective_date);
