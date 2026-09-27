-- =====================================================
-- NSS ERP
-- Module: Authentication & Security
-- File: 01_user_account.sql
-- Table: nss.user_account
-- Depth: 2 (depends on person)
-- Version: 1.0
-- Authority: SOL-AUTH-001, SOL-AUTH-002, SOL-AUTH-004 §7,
--            SOL-AUTH-005, Tier 5 decisions (2026-09-15)
-- Owner: Authentication & Security
--
-- Design decisions:
--   - person_pk UNIQUE NOT NULL: one account per person
--   - Login identity: sangha_sevi_id looked up via
--     person FK at authentication time, not stored here
--   - Account states: ACTIVE / LOCKED / INACTIVE / PENDING_APPROVAL
--   - force_password_change: admin-reset flow
--   - ERP account requires valid Parichay Patra or
--     Anumati Patra (application-level check, not FK)
--   - Password: Argon2 hash, 8-128 chars, 365-day expiry
--   - Lockout: 5 attempts, 30-second auto-unlock
--
-- Note: Audit actor FKs (*_by_sangha_sevi_pk) are
--       NULLABLE columns included in Pass 1. Their FK
--       constraints are deferred to Pass 2 (after
--       sangha_sevi table exists).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.user_account
(
    -- ── Identity ────────────────────────────────────────

    user_account_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    person_pk UUID NOT NULL,

    -- ── Credential ──────────────────────────────────────

    password_hash VARCHAR(255) NOT NULL,

    -- ── Account State ───────────────────────────────────

    account_status VARCHAR(20) NOT NULL
        DEFAULT 'ACTIVE',

    force_password_change BOOLEAN NOT NULL
        DEFAULT FALSE,

    -- ── Password Policy ─────────────────────────────────

    password_changed_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    password_expires_at TIMESTAMPTZ NOT NULL
        DEFAULT (CURRENT_TIMESTAMP + INTERVAL '365 days'),

    -- ── Lockout ─────────────────────────────────────────

    failed_login_attempts INTEGER NOT NULL
        DEFAULT 0,

    locked_until TIMESTAMPTZ NULL,

    last_failed_login_at TIMESTAMPTZ NULL,

    -- ── Session Tracking ────────────────────────────────

    last_login_at TIMESTAMPTZ NULL,

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

    CONSTRAINT fk_user_account_person
        FOREIGN KEY (person_pk)
        REFERENCES nss.person (person_pk),

    -- ── Unique Constraints ──────────────────────────────

    CONSTRAINT uq_user_account_person
        UNIQUE (person_pk),

    -- ── CHECK Constraints ───────────────────────────────

    CONSTRAINT chk_user_account_status
        CHECK (account_status IN ('ACTIVE', 'LOCKED', 'INACTIVE', 'PENDING_APPROVAL')),

    CONSTRAINT chk_user_account_failed_attempts
        CHECK (failed_login_attempts >= 0),

    CONSTRAINT chk_user_account_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_user_account_person
    ON nss.user_account (person_pk);

CREATE INDEX IF NOT EXISTS idx_user_account_status
    ON nss.user_account (account_status);

CREATE INDEX IF NOT EXISTS idx_user_account_active
    ON nss.user_account (is_active);

CREATE INDEX IF NOT EXISTS idx_user_account_locked_until
    ON nss.user_account (locked_until)
    WHERE locked_until IS NOT NULL;
