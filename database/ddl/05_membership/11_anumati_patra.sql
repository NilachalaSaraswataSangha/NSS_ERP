-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 11_anumati_patra.sql
-- Table: nss.anumati_patra
-- Depth: 3 (depends on sangha_sevi)
-- Version: 1.0
-- Authority: SOL-MEM-005 §12, SOL-MEM-003
--            Bye-Law §B(a) — Probationary members
--            are issued an Anumati Patra (Admit Card)
--            by the Kendra Sangha.
-- Owner: NSS_ERP_ADMIN
-- Note: Anumati Patra is the probationary member's
--       credential. Must be valid for at least one
--       year before Regular enrolment (Bye-Law
--       §B(b)(i)).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.anumati_patra
(
    anumati_patra_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    document_number VARCHAR(30) NOT NULL,

    issue_date DATE NOT NULL,

    valid_from DATE NOT NULL,

    valid_to DATE NOT NULL,

    -- ACTIVE, EXPIRED, CANCELLED, REPLACED
    status VARCHAR(20) NOT NULL
        DEFAULT 'ACTIVE',

    document_reference VARCHAR(255) NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_ap_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk),

    CONSTRAINT chk_ap_validity_range
        CHECK (valid_to > valid_from),

    CONSTRAINT chk_ap_status
        CHECK
        (
            status IN ('ACTIVE', 'EXPIRED', 'CANCELLED', 'REPLACED')
        ),

    CONSTRAINT uq_ap_document_number
        UNIQUE (document_number)
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_ap_sevi
    ON nss.anumati_patra (sangha_sevi_pk);

CREATE INDEX IF NOT EXISTS idx_ap_status
    ON nss.anumati_patra (status);

CREATE INDEX IF NOT EXISTS idx_ap_valid_range
    ON nss.anumati_patra (valid_from, valid_to);

-- Only one active Anumati Patra per member at any time.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ap_active_per_member
    ON nss.anumati_patra (sangha_sevi_pk)
    WHERE status = 'ACTIVE';
