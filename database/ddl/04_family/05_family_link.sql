-- =====================================================
-- NSS ERP
-- Module: Family
-- File: 05_family_link.sql
-- Table: nss.family_link
-- Depth: 3 (depends on family_group, person)
-- Version: 1.0
-- Authority: ERP-DECISION — Graph-based dynamic
--            relationship model
-- Owner: NSS_ERP_ADMIN
-- Note: Stores only direct biological/legal edges
--       between family members. All extended
--       relationships (grandfather, uncle, cousin,
--       etc.) are computed dynamically via graph
--       traversal relative to the viewer.
--
--       link_type semantics:
--         PARENT_OF — person_a is parent of person_b
--         SPOUSE_OF — person_a and person_b are spouses
--                     (bidirectional; store one row)
-- =====================================================

CREATE TABLE nss.family_link
(
    -- ── Identity ────────────────────────────────────────

    family_link_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- ── Relationships ───────────────────────────────────

    family_group_pk UUID NOT NULL,

    -- The "from" person in the directed edge
    person_a_pk UUID NOT NULL,

    -- The "to" person in the directed edge
    person_b_pk UUID NOT NULL,

    -- Only two link types allowed
    link_type VARCHAR(20) NOT NULL,

    -- ── Effective Period ────────────────────────────────

    effective_from DATE NOT NULL,

    effective_to DATE NULL,

    is_current BOOLEAN NOT NULL
        DEFAULT TRUE,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_family_link_family_group
        FOREIGN KEY (family_group_pk)
        REFERENCES nss.family_group (family_group_pk),

    CONSTRAINT fk_family_link_person_a
        FOREIGN KEY (person_a_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT fk_family_link_person_b
        FOREIGN KEY (person_b_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT chk_family_link_type
        CHECK (link_type IN ('PARENT_OF', 'SPOUSE_OF')),

    CONSTRAINT chk_family_link_no_self
        CHECK (person_a_pk <> person_b_pk),

    CONSTRAINT chk_family_link_effective_range
        CHECK
        (
            effective_to IS NULL
            OR effective_to >= effective_from
        ),

    CONSTRAINT chk_family_link_current_consistency
        CHECK
        (
            (is_current = TRUE AND effective_to IS NULL)
            OR
            (is_current = FALSE AND effective_to IS NOT NULL)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_family_link_family_group
    ON nss.family_link (family_group_pk);

CREATE INDEX idx_family_link_person_a
    ON nss.family_link (person_a_pk);

CREATE INDEX idx_family_link_person_b
    ON nss.family_link (person_b_pk);

CREATE INDEX idx_family_link_is_current
    ON nss.family_link (is_current);

-- A given directed edge should not be duplicated
-- while current.
CREATE UNIQUE INDEX uq_family_link_current
    ON nss.family_link (family_group_pk, person_a_pk, person_b_pk, link_type)
    WHERE is_current = TRUE;
