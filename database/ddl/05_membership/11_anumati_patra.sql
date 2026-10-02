-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 11_anumati_patra.sql
-- Table: nss.anumati_patra
-- Depth: 3 (depends on sangha_sevi, organization)
-- Version: 1.1
-- Authority: SOL-MEM-005 §12, SOL-MEM-003
--            Bye-Law §B(a) — Probationary members
--            are issued an Anumati Patra (Admit Card)
--            by the Kendra Sangha.
-- Owner: NSS_ERP_ADMIN
-- Note: Anumati Patra is the probationary member's
--       credential. Must be valid for at least one
--       year before Regular enrolment (Bye-Law
--       §B(b)(i)).
-- Changelog:
--   1.1 — document_number scoped per issuing Sakha
--         (issuing_organization_pk + composite
--         uq_ap_document_number), replacing the global
--         single-column unique that collided across
--         Sakhas on the first issue of each FY.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.anumati_patra
(
    anumati_patra_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    -- Issuing Sakha (organization) that minted this document_number.
    -- Anumati Patra numbering is per-Sakha: each Sakha runs its own FY
    -- sequence (nss.credential_sequence_counter scoped by this org), so two
    -- Sakhas legitimately produce the same "<seq>/<fy>/<fy>" string in the
    -- same year. document_number is therefore unique only WITHIN an issuing
    -- Sakha — see uq_ap_document_number below (SOL-MEM-005 §12).
    issuing_organization_pk UUID NOT NULL,

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

    CONSTRAINT fk_ap_issuing_org
        FOREIGN KEY (issuing_organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT chk_ap_validity_range
        CHECK (valid_to > valid_from),

    CONSTRAINT chk_ap_status
        CHECK
        (
            status IN ('ACTIVE', 'EXPIRED', 'CANCELLED', 'REPLACED')
        ),

    -- Per-Sakha uniqueness. The old global UNIQUE(document_number) collided
    -- (HTTP 409) whenever two Sakhas each issued their first Anumati Patra of
    -- a financial year, since both minted the identical "1/<fy>/<fy>" string
    -- from their own independent counters. Scoping by issuing_organization_pk
    -- keeps each Sakha's numbers unique without forcing a global sequence.
    CONSTRAINT uq_ap_document_number
        UNIQUE (issuing_organization_pk, document_number)
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_ap_sevi
    ON nss.anumati_patra (sangha_sevi_pk);

CREATE INDEX IF NOT EXISTS idx_ap_issuing_org
    ON nss.anumati_patra (issuing_organization_pk);

CREATE INDEX IF NOT EXISTS idx_ap_status
    ON nss.anumati_patra (status);

CREATE INDEX IF NOT EXISTS idx_ap_valid_range
    ON nss.anumati_patra (valid_from, valid_to);

-- Only one active Anumati Patra per member at any time.
CREATE UNIQUE INDEX IF NOT EXISTS uq_ap_active_per_member
    ON nss.anumati_patra (sangha_sevi_pk)
    WHERE status = 'ACTIVE';
