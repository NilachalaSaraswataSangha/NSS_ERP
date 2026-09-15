-- =====================================================
-- NSS ERP
-- Module: Family
-- File: 04_family_transition_history.sql
-- Table: nss.family_transition_history
-- Depth: 3 (depends on family_group x2, person)
-- Version: 1.0
-- Authority: SOL-FAM-005 §10–§12, SOL-FAM-003
--            FAM-011, FAM-012, FAM-013, FAM-014,
--            FAM-015, FAM-016
-- Owner: NSS_ERP_ADMIN
-- Note: Records transitions between family groups
--       (e.g., marriage, new family formation).
--       Both old and new family groups are preserved
--       (FAM-013). Historical records are never
--       deleted (FAM-028).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.family_transition_history
(
    -- ── Identity ────────────────────────────────────────

    family_transition_history_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- ── Relationships ───────────────────────────────────

    person_pk UUID NOT NULL,

    old_family_group_pk UUID NOT NULL,

    new_family_group_pk UUID NOT NULL,

    -- ── Transition Details ──────────────────────────────
    -- transition_type: MARRIAGE, NEW_FAMILY_FORMATION,
    --   CHANGE_OF_FAMILY_UNIT, OTHER

    transition_type VARCHAR(50) NOT NULL,

    transition_reason VARCHAR(500) NULL,

    effective_date DATE NOT NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_family_trans_person
        FOREIGN KEY (person_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT fk_family_trans_old_family
        FOREIGN KEY (old_family_group_pk)
        REFERENCES nss.family_group (family_group_pk),

    CONSTRAINT fk_family_trans_new_family
        FOREIGN KEY (new_family_group_pk)
        REFERENCES nss.family_group (family_group_pk),

    CONSTRAINT chk_family_trans_different_families
        CHECK (old_family_group_pk <> new_family_group_pk),

    CONSTRAINT chk_family_trans_type
        CHECK
        (
            transition_type IN
            (
                'MARRIAGE',
                'NEW_FAMILY_FORMATION',
                'CHANGE_OF_FAMILY_UNIT',
                'OTHER'
            )
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_family_trans_person
    ON nss.family_transition_history (person_pk);

CREATE INDEX IF NOT EXISTS idx_family_trans_old_family
    ON nss.family_transition_history (old_family_group_pk);

CREATE INDEX IF NOT EXISTS idx_family_trans_new_family
    ON nss.family_transition_history (new_family_group_pk);

CREATE INDEX IF NOT EXISTS idx_family_trans_effective_date
    ON nss.family_transition_history (effective_date);

CREATE INDEX IF NOT EXISTS idx_family_trans_type
    ON nss.family_transition_history (transition_type);
