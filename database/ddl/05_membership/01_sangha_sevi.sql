-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 01_sangha_sevi.sql
-- Table: nss.sangha_sevi
-- Depth: 2 (depends on person, master_data,
--         organization)
-- Version: 1.0
-- Authority: SOL-MEM-005 §4–§5, SOL-MEM-003
--            MBR-001, MBR-002, MBR-003
-- Owner: NSS_ERP_ADMIN
-- Note: One Person = One Membership (UNIQUE on
--       person_pk). Sangha Sevi ID is permanent,
--       NSS-wide, never reused, never changed.
--       Local Sakha ERP ID is NOT on this table —
--       it resides on membership_sakha_affiliation
--       (MEM-PENDING-001 FROZEN).
-- Note: Audit actor FKs (*_by_sangha_sevi_pk) are
--       self-referencing — deferred to Pass 2 for
--       initial bootstrap (first member creation).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.sangha_sevi
(
    -- ── Identity ────────────────────────────────────────

    sangha_sevi_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- Permanent NSS-wide business identifier.
    -- Format: SS1, SS2, ... SS99999999 (prefix SS + up to 8-digit sequence).
    -- No zero-padding. Never reused, never changed.
    sangha_sevi_id VARCHAR(20) NOT NULL,

    -- ── Relationships ───────────────────────────────────

    -- One Person = One Membership (enforced by UNIQUE).
    person_pk UUID NOT NULL,

    -- Membership type: PROBATIONARY, REGULAR, ASSOCIATE,
    -- HONORARY (Foundation master_data, category
    -- MEMBERSHIP_TYPE).
    membership_type_master_data_pk UUID NOT NULL,

    -- Current membership status: ACTIVE, SUSPENDED,
    -- LAPSED, etc. (Foundation master_data, unified
    -- STATUS category).
    membership_status_master_data_pk UUID NOT NULL,

    -- Current Sakha / organizational unit the member
    -- belongs to. Authoritative affiliation history
    -- is on membership_sakha_affiliation.
    organization_pk UUID NOT NULL,

    -- ── Dates ───────────────────────────────────────────

    joining_date DATE NOT NULL,

    renewal_due_date DATE NULL,

    -- ── Other ───────────────────────────────────────────

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

    CONSTRAINT uq_sangha_sevi_id
        UNIQUE (sangha_sevi_id),

    CONSTRAINT uq_sangha_sevi_person
        UNIQUE (person_pk),

    CONSTRAINT fk_sangha_sevi_person
        FOREIGN KEY (person_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT fk_sangha_sevi_membership_type
        FOREIGN KEY (membership_type_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT fk_sangha_sevi_status
        FOREIGN KEY (membership_status_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT fk_sangha_sevi_organization
        FOREIGN KEY (organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT chk_sangha_sevi_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        ),

    CONSTRAINT chk_sangha_sevi_renewal_after_joining
        CHECK
        (
            renewal_due_date IS NULL
            OR renewal_due_date >= joining_date
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_sangha_sevi_id
    ON nss.sangha_sevi (sangha_sevi_id);

CREATE INDEX IF NOT EXISTS idx_sangha_sevi_person
    ON nss.sangha_sevi (person_pk);

CREATE INDEX IF NOT EXISTS idx_sangha_sevi_type
    ON nss.sangha_sevi (membership_type_master_data_pk);

CREATE INDEX IF NOT EXISTS idx_sangha_sevi_status
    ON nss.sangha_sevi (membership_status_master_data_pk);

CREATE INDEX IF NOT EXISTS idx_sangha_sevi_organization
    ON nss.sangha_sevi (organization_pk);

CREATE INDEX IF NOT EXISTS idx_sangha_sevi_is_active
    ON nss.sangha_sevi (is_active);

CREATE INDEX IF NOT EXISTS idx_sangha_sevi_joining_date
    ON nss.sangha_sevi (joining_date);

CREATE INDEX IF NOT EXISTS idx_sangha_sevi_renewal_due
    ON nss.sangha_sevi (renewal_due_date)
    WHERE renewal_due_date IS NOT NULL;
