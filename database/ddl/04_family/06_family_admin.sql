-- =====================================================
-- NSS ERP
-- Module: Family
-- File: 06_family_admin.sql
-- Table: nss.family_admin
-- Depth: 3 (depends on family_group, person)
-- Version: 1.0
-- Authority: SOL-FAM-003 — FAM-045 through FAM-052
-- Owner: NSS_ERP_ADMIN
-- Note: Tracks Family Admin role assignments.
--       Multiple admins per family allowed.
--       Head and Admin are independent roles — a person
--       may hold both. Only the Family Head can assign
--       or revoke Admin. Historical records preserved
--       (FAM-052, FAM-028).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.family_admin
(
    -- ── Identity ────────────────────────────────────────

    family_admin_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- ── Relationships ───────────────────────────────────

    family_group_pk UUID NOT NULL,

    -- The person designated as Family Admin
    person_pk UUID NOT NULL,

    -- ── Effective Period ────────────────────────────────

    effective_from DATE NOT NULL,

    -- NULL = currently active admin
    effective_to DATE NULL,

    -- ── Details ─────────────────────────────────────────

    -- Who appointed this admin (must be the Head at the time)
    appointed_by_person_pk UUID NOT NULL,

    -- Reason for appointment or revocation
    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_family_admin_family_group
        FOREIGN KEY (family_group_pk)
        REFERENCES nss.family_group (family_group_pk),

    CONSTRAINT fk_family_admin_person
        FOREIGN KEY (person_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT fk_family_admin_appointed_by
        FOREIGN KEY (appointed_by_person_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT chk_family_admin_effective_range
        CHECK
        (
            effective_to IS NULL
            OR effective_to >= effective_from
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_family_admin_family_group
    ON nss.family_admin (family_group_pk);

CREATE INDEX IF NOT EXISTS idx_family_admin_person
    ON nss.family_admin (person_pk);

-- A person can be active admin of a given family only once at a time.
CREATE UNIQUE INDEX IF NOT EXISTS uq_family_admin_current
    ON nss.family_admin (family_group_pk, person_pk)
    WHERE effective_to IS NULL;
