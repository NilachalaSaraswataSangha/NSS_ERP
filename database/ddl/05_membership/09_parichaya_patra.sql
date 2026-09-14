-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 09_parichaya_patra.sql
-- Table: nss.parichaya_patra
-- Depth: 3 (depends on sangha_sevi, organization)
-- Version: 1.0
-- Authority: SOL-MEM-005 §14, SOL-MEM-003
--            Bye-Law §B(b)(iii), §B(d)(i)
-- Owner: NSS_ERP_ADMIN
-- Note: Parichaya Patra (Identity Card) issued
--       annually by Kendra Sangha. document_number
--       is the Kendra number (e.g., 345/2024/2025).
--       affiliated_organization_pk and
--       local_sakha_erp_id are point-in-time snapshots
--       of what was printed on the card — the
--       authoritative current affiliation remains on
--       membership_sakha_affiliation.
-- =====================================================

CREATE TABLE nss.parichaya_patra
(
    parichaya_patra_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    -- Kendra number for this year's card.
    -- Format: <seq>/<start_year>/<end_year>
    -- Example: 345/2024/2025
    document_number VARCHAR(30) NOT NULL,

    issue_date DATE NOT NULL,

    -- Financial year validity (1 April – 31 March).
    valid_from DATE NOT NULL,

    valid_to DATE NOT NULL,

    -- ACTIVE, EXPIRED, CANCELLED, REPLACED
    status VARCHAR(20) NOT NULL
        DEFAULT 'ACTIVE',

    -- ── Card Snapshot Fields ────────────────────────────
    -- Point-in-time copy of what was printed on this
    -- year's Parichaya Patra card.

    -- Sakha at time of issuance.
    affiliated_organization_pk UUID NULL,

    -- Local Sakha number at time of issuance.
    -- Same value year after year unless transferred.
    local_sakha_erp_id VARCHAR(30) NULL,

    -- ── Other ───────────────────────────────────────────

    document_reference VARCHAR(255) NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_pp_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk),

    CONSTRAINT fk_pp_affiliated_org
        FOREIGN KEY (affiliated_organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT chk_pp_validity_range
        CHECK (valid_to > valid_from),

    CONSTRAINT chk_pp_status
        CHECK
        (
            status IN ('ACTIVE', 'EXPIRED', 'CANCELLED', 'REPLACED')
        ),

    -- Kendra number is unique per document.
    CONSTRAINT uq_pp_document_number
        UNIQUE (document_number)
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_pp_sevi
    ON nss.parichaya_patra (sangha_sevi_pk);

CREATE INDEX idx_pp_status
    ON nss.parichaya_patra (status);

CREATE INDEX idx_pp_valid_range
    ON nss.parichaya_patra (valid_from, valid_to);

CREATE INDEX idx_pp_affiliated_org
    ON nss.parichaya_patra (affiliated_organization_pk)
    WHERE affiliated_organization_pk IS NOT NULL;

-- Only one active Parichaya Patra per member at any time.
CREATE UNIQUE INDEX uq_pp_active_per_member
    ON nss.parichaya_patra (sangha_sevi_pk)
    WHERE status = 'ACTIVE';
