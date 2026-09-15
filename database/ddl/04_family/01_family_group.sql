-- =====================================================
-- NSS ERP
-- Module: Family
-- File: 01_family_group.sql
-- Table: nss.family_group
-- Depth: 2 (depends on organization, master_data)
-- Version: 1.0
-- Authority: SOL-FAM-005 §3–§4, SOL-FAM-003
--            FAM-001, FAM-002
-- Owner: NSS_ERP_ADMIN
-- Note: Audit actor FKs (*_by_sangha_sevi_pk) are
--       NULLABLE columns included in Pass 1. Their FK
--       constraints are deferred to Pass 2 (after
--       sangha_sevi table exists).
-- =====================================================

CREATE TABLE nss.family_group
(
    -- ── Identity ────────────────────────────────────────

    family_group_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    family_id VARCHAR(20) NOT NULL,

    -- ── Details ─────────────────────────────────────────

    family_name VARCHAR(200) NOT NULL,

    -- Family status references the unified STATUS
    -- category in Foundation master_data.
    family_status_master_data_pk UUID NOT NULL,

    -- The Sakha this family is registered under.
    sakha_organization_pk UUID NOT NULL,

    formed_date DATE NULL,

    remarks TEXT NULL,

    -- ── Lifecycle ───────────────────────────────────────

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    deleted_at TIMESTAMPTZ NULL,

    deleted_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT uq_family_id
        UNIQUE (family_id),

    CONSTRAINT fk_family_group_status
        FOREIGN KEY (family_status_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT fk_family_group_sakha
        FOREIGN KEY (sakha_organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT chk_family_group_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_family_group_family_id
    ON nss.family_group (family_id);

CREATE INDEX idx_family_group_sakha
    ON nss.family_group (sakha_organization_pk);

CREATE INDEX idx_family_group_status
    ON nss.family_group (family_status_master_data_pk);

CREATE INDEX idx_family_group_is_active
    ON nss.family_group (is_active);

CREATE INDEX idx_family_group_family_name
    ON nss.family_group (family_name);
