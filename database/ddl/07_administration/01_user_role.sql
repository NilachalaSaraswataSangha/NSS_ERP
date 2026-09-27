-- =====================================================
-- NSS ERP
-- Module: Administration
-- File: 01_user_role.sql
-- Table: nss.user_role
-- Depth: 3 (depends on user_account, role_master)
-- Version: 1.0
-- Authority: SOL-ADMIN-004 §11, SOL-AUTH-004 §12,
--            Tier 5 decisions (2026-09-15)
-- Owner: Administration
--
-- Design decisions:
--   - Multi-role per user supported (user_role is 1:N)
--   - A user can have the same role with different scopes
--     (e.g. SAKHA_ADMIN for Sakha A and Sakha B)
--   - Duplicate-scope prevention is handled in the API
--     layer (checking role + scope_level + organization_pk)
--   - Soft delete with is_active: revoking a role sets
--     is_active = FALSE, preserving historical evidence
--   - No separate role_history table (frozen decision)
--   - Role assignment is manual in Tier 5; automated
--     via Governance module in future tier
--
-- Note: Audit actor FKs (*_by_sangha_sevi_pk) are
--       NULLABLE columns included in Pass 1. Their FK
--       constraints are deferred to Pass 2.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.user_role
(
    -- ── Identity ────────────────────────────────────────

    user_role_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    user_account_pk UUID NOT NULL,

    role_master_pk UUID NOT NULL,

    -- ── Assignment Metadata ─────────────────────────────

    assigned_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    revoked_at TIMESTAMPTZ NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    deleted_at TIMESTAMPTZ NULL,

    deleted_by_sangha_sevi_pk UUID NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    -- ── Foreign Keys ────────────────────────────────────

    CONSTRAINT fk_user_role_user_account
        FOREIGN KEY (user_account_pk)
        REFERENCES nss.user_account (user_account_pk),

    CONSTRAINT fk_user_role_role_master
        FOREIGN KEY (role_master_pk)
        REFERENCES nss.role_master (role_master_pk),

    -- ── Unique Constraints ──────────────────────────────
    -- No UNIQUE on (user_account_pk, role_master_pk) —
    -- a user can have the same role with different scopes.
    -- Duplicate prevention is in the API layer.

    -- ── CHECK Constraints ───────────────────────────────

    CONSTRAINT chk_user_role_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        ),

    CONSTRAINT chk_user_role_revocation
        CHECK
        (
            (is_active = TRUE AND revoked_at IS NULL)
            OR
            (is_active = FALSE)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_user_role_user_account
    ON nss.user_role (user_account_pk);

CREATE INDEX IF NOT EXISTS idx_user_role_role_master
    ON nss.user_role (role_master_pk);

CREATE INDEX IF NOT EXISTS idx_user_role_active
    ON nss.user_role (is_active);

CREATE INDEX IF NOT EXISTS idx_user_role_user_active
    ON nss.user_role (user_account_pk)
    WHERE is_active = TRUE;
