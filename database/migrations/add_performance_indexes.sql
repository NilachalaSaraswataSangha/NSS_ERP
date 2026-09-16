-- =====================================================
-- NSS ERP — Performance indexes for family_majority CTE
-- Date: 2026-09-16
-- Purpose: Add composite indexes to speed up the
--          family_majority CTE used in _FAMILY_SELECT
--          (family.py) and _CHILDREN_STATS_SQL
--          (organization.py). These CTEs join
--          family_relationship → sangha_sevi →
--          membership_sakha_affiliation with filters
--          on is_current, is_active, and effective_to.
--
-- Impact: Reduces full-table scans to index-only scans
--         on the hot path (family list, org children-stats).
-- =====================================================

-- 1. family_relationship: CTE filters is_current=TRUE, joins on person_pk,
--    groups by family_group_pk. Partial composite index covers all three.
CREATE INDEX IF NOT EXISTS idx_family_rel_current_person_family
    ON nss.family_relationship (person_pk, family_group_pk)
    WHERE is_current = TRUE;

-- 2. sangha_sevi: CTE filters is_active=TRUE, joins on person_pk,
--    needs sangha_sevi_pk for next join. Covering partial index.
CREATE INDEX IF NOT EXISTS idx_sangha_sevi_active_person
    ON nss.sangha_sevi (person_pk, sangha_sevi_pk)
    WHERE is_active = TRUE;

-- 3. membership_sakha_affiliation: CTE filters effective_to IS NULL,
--    joins on sangha_sevi_pk, needs organization_pk for grouping.
--    Covering partial index (extends the existing uq_mem_sakha_aff_active).
CREATE INDEX IF NOT EXISTS idx_mem_sakha_aff_active_covering
    ON nss.membership_sakha_affiliation (sangha_sevi_pk, organization_pk)
    WHERE effective_to IS NULL;

-- 4. organization: recursive CTE joins on parent_organization_pk
--    with is_active=TRUE. Partial composite for the recursive step.
CREATE INDEX IF NOT EXISTS idx_organization_parent_active
    ON nss.organization (parent_organization_pk)
    WHERE is_active = TRUE;
