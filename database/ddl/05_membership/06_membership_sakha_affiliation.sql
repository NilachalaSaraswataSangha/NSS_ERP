-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 06_membership_sakha_affiliation.sql
-- Table: nss.membership_sakha_affiliation
-- Depth: 3 (depends on sangha_sevi, organization)
-- Version: 1.0
-- Authority: SOL-MEM-005 §27.1, CROSS_MODULE_PRINCIPLES
--            §20.2, MEM-PENDING-001 (FROZEN)
-- Owner: NSS_ERP_ADMIN
-- Note: Authoritative source for Local Sakha ERP ID.
--       Persistent per person per Sakha — archived on
--       transfer (never reassigned to another person),
--       reactivated on return to same Sakha.
--       One active affiliation per member at any time.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.membership_sakha_affiliation
(
    membership_sakha_affiliation_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    -- The Sakha the member is affiliated with.
    organization_pk UUID NOT NULL,

    -- Local Sakha ERP ID — format:
    -- <3-5 char Sakha short code><numeric sequence>
    -- Example: ESS1192
    -- Persistent per person per Sakha. Never reassigned.
    local_sakha_erp_id VARCHAR(30) NOT NULL,

    effective_from DATE NOT NULL,

    -- NULL = current active affiliation.
    effective_to DATE NULL,

    -- ACTIVE, ARCHIVED, REACTIVATED
    affiliation_status VARCHAR(20) NOT NULL,

    -- ENROLLMENT, TRANSFER, REACTIVATION
    source_event_type VARCHAR(20) NOT NULL,

    -- Optional FK to the source event record
    -- (e.g., membership_transfer_history_pk).
    source_event_pk UUID NULL,

    -- Original Sakha register number before ERP
    -- migration. Only populated on migrated records.
    legacy_sakha_number VARCHAR(30) NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_mem_sakha_aff_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk),

    CONSTRAINT fk_mem_sakha_aff_org
        FOREIGN KEY (organization_pk)
        REFERENCES nss.organization (organization_pk),

    -- No two members share the same local ID within a
    -- Sakha (ID is never reassigned to another person).
    CONSTRAINT uq_mem_sakha_aff_local_id
        UNIQUE (organization_pk, local_sakha_erp_id),

    CONSTRAINT chk_mem_sakha_aff_effective_range
        CHECK
        (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    -- Status/effective_to consistency:
    -- Active or reactivated = open-ended (effective_to NULL).
    -- Archived = closed (effective_to NOT NULL).
    CONSTRAINT chk_mem_sakha_aff_status_consistency
        CHECK
        (
            (effective_to IS NULL AND affiliation_status IN ('ACTIVE', 'REACTIVATED'))
            OR
            (effective_to IS NOT NULL AND affiliation_status = 'ARCHIVED')
        ),

    CONSTRAINT chk_mem_sakha_aff_status
        CHECK
        (
            affiliation_status IN ('ACTIVE', 'ARCHIVED', 'REACTIVATED')
        ),

    CONSTRAINT chk_mem_sakha_aff_event_type
        CHECK
        (
            source_event_type IN ('ENROLLMENT', 'TRANSFER', 'REACTIVATION')
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_mem_sakha_aff_sevi
    ON nss.membership_sakha_affiliation (sangha_sevi_pk);

CREATE INDEX IF NOT EXISTS idx_mem_sakha_aff_org
    ON nss.membership_sakha_affiliation (organization_pk);

CREATE INDEX IF NOT EXISTS idx_mem_sakha_aff_status
    ON nss.membership_sakha_affiliation (affiliation_status);

-- One active affiliation per member at any time.
CREATE UNIQUE INDEX IF NOT EXISTS uq_mem_sakha_aff_active
    ON nss.membership_sakha_affiliation (sangha_sevi_pk)
    WHERE effective_to IS NULL;
