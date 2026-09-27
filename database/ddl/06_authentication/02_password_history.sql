-- =====================================================
-- NSS ERP
-- Module: Authentication & Security
-- File: 02_password_history.sql
-- Table: nss.password_history
-- Depth: 3 (depends on user_account)
-- Version: 1.0
-- Authority: SOL-AUTH-001, SOL-AUTH-002, SOL-AUTH-004 §8,
--            SOL-AUTH-005 §13, Tier 5 decisions (2026-09-15)
-- Owner: Authentication & Security
--
-- Design decisions:
--   - Append-only: records never physically deleted
--   - Stores Argon2 hash of previous passwords
--   - Reuse prevention: current password only (last 1)
--   - password_history is NOT the current credential
--     (AUTH-BR-015); current hash lives in user_account
--
-- Note: Audit actor FKs (*_by_sangha_sevi_pk) are
--       NULLABLE columns included in Pass 1. Their FK
--       constraints are deferred to Pass 2.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.password_history
(
    -- ── Identity ────────────────────────────────────────

    password_history_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    user_account_pk UUID NOT NULL,

    -- ── Historical Credential ───────────────────────────

    password_hash VARCHAR(255) NOT NULL,

    -- ── Metadata ────────────────────────────────────────

    changed_reason VARCHAR(30) NOT NULL
        DEFAULT 'USER_CHANGE',

    -- ── Audit (append-only — no update/delete columns) ──

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    -- ── Foreign Keys ────────────────────────────────────

    CONSTRAINT fk_password_history_user_account
        FOREIGN KEY (user_account_pk)
        REFERENCES nss.user_account (user_account_pk),

    -- ── CHECK Constraints ───────────────────────────────

    CONSTRAINT chk_password_history_reason
        CHECK (changed_reason IN ('USER_CHANGE', 'ADMIN_RESET', 'SELF_RESET', 'EXPIRY', 'INITIAL'))
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_password_history_user_account
    ON nss.password_history (user_account_pk);

CREATE INDEX IF NOT EXISTS idx_password_history_created_at
    ON nss.password_history (user_account_pk, created_at DESC);
