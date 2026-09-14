-- =====================================================
-- NSS ERP
-- Module: Family
-- File: 02_family_relationship.sql
-- Table: nss.family_relationship
-- Depth: 3 (depends on family_group, person,
--         master_data)
-- Version: 1.0
-- Authority: SOL-FAM-005 §5–§7, SOL-FAM-003
--            FAM-006, FAM-007, FAM-008
-- Owner: NSS_ERP_ADMIN
-- Note: relationship_type_master_data_pk references
--       Foundation master_data (category
--       RELATIONSHIP_TYPE). The same category is used
--       by Person (emergency contact relationship).
-- =====================================================

CREATE TABLE nss.family_relationship
(
    -- ── Identity ────────────────────────────────────────

    family_relationship_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- ── Relationships ───────────────────────────────────

    family_group_pk UUID NOT NULL,

    person_pk UUID NOT NULL,

    -- Relationship type references Foundation master_data
    -- (category: RELATIONSHIP_TYPE — FATHER, MOTHER,
    -- SPOUSE, SON, DAUGHTER, etc.)
    relationship_type_master_data_pk UUID NOT NULL,

    -- ── Effective Period ────────────────────────────────

    effective_from DATE NOT NULL,

    effective_to DATE NULL,

    is_current BOOLEAN NOT NULL
        DEFAULT TRUE,

    -- ── Other ───────────────────────────────────────────

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_family_rel_family_group
        FOREIGN KEY (family_group_pk)
        REFERENCES nss.family_group (family_group_pk),

    CONSTRAINT fk_family_rel_person
        FOREIGN KEY (person_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT fk_family_rel_type
        FOREIGN KEY (relationship_type_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT chk_family_rel_effective_range
        CHECK
        (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    CONSTRAINT chk_family_rel_current_consistency
        CHECK
        (
            (is_current = TRUE AND effective_to IS NULL)
            OR
            (is_current = FALSE AND effective_to IS NOT NULL)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_family_rel_family_group
    ON nss.family_relationship (family_group_pk);

CREATE INDEX idx_family_rel_person
    ON nss.family_relationship (person_pk);

CREATE INDEX idx_family_rel_type
    ON nss.family_relationship (relationship_type_master_data_pk);

CREATE INDEX idx_family_rel_is_current
    ON nss.family_relationship (is_current);

-- A person can have only one current relationship within
-- a given family group at any point in time.
CREATE UNIQUE INDEX uq_family_rel_person_current
    ON nss.family_relationship (family_group_pk, person_pk)
    WHERE is_current = TRUE;
