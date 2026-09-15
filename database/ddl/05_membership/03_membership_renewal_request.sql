-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 03_membership_renewal_request.sql
-- Table: nss.membership_renewal_request
-- Depth: 3 (depends on sangha_sevi)
-- Version: 1.0
-- Authority: SOL-MEM-005 §7, SOL-MEM-003
-- Owner: NSS_ERP_ADMIN
-- Note: Stores renewal requests before approval.
--       Approved renewals create a row in
--       membership_renewal_history.
-- =====================================================

CREATE TABLE nss.membership_renewal_request
(
    membership_renewal_request_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    requested_date DATE NOT NULL,

    requested_by_sangha_sevi_pk UUID NULL,

    -- Workflow status: PENDING, APPROVED, REJECTED
    status VARCHAR(20) NOT NULL
        DEFAULT 'PENDING',

    reviewed_by_sangha_sevi_pk UUID NULL,

    reviewed_date DATE NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_mem_renewal_req_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk),

    CONSTRAINT chk_mem_renewal_req_status
        CHECK
        (
            status IN ('PENDING', 'APPROVED', 'REJECTED')
        ),

    CONSTRAINT chk_mem_renewal_req_review_consistency
        CHECK
        (
            (status = 'PENDING' AND reviewed_by_sangha_sevi_pk IS NULL AND reviewed_date IS NULL)
            OR
            (status IN ('APPROVED', 'REJECTED') AND reviewed_date IS NOT NULL)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_mem_renewal_req_sevi
    ON nss.membership_renewal_request (sangha_sevi_pk);

CREATE INDEX idx_mem_renewal_req_status
    ON nss.membership_renewal_request (status);

CREATE INDEX idx_mem_renewal_req_date
    ON nss.membership_renewal_request (requested_date);
