-- =====================================================
-- NSS ERP
-- Module: Authentication & Security
-- File: 04_password_reset_token.sql
-- Table: nss.password_reset_token
-- Depth: 3 (depends on user_account)
-- Version: 1.0
-- Authority: Tier 5.1 (Self-service password reset)
-- Owner: Authentication & Security
--
-- Purpose:
--   Stores time-limited, single-use OTPs for the
--   "Forgot Password" self-service flow.
--
--   Each OTP:
--     - 6-digit numeric code, stored as Argon2 hash
--     - Valid for 15 minutes (configurable in app settings)
--     - Single-use: consumed on first successful reset
--     - Max 3 active tokens per user (older ones auto-expire)
--
-- Design decisions:
--   - OTP hash stored (not plaintext) — same Argon2 as passwords
--   - is_used flag prevents replay attacks
--   - expires_at enforced at query time
--   - Rate-limited at the API layer (max 3 per hour)
--
-- Dependencies:
--   - 06_authentication/01_user_account.sql
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.password_reset_token
(
    -- ── Identity ────────────────────────────────────────

    password_reset_token_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    user_account_pk UUID NOT NULL,

    -- ── Token ───────────────────────────────────────────

    otp_hash VARCHAR(255) NOT NULL,

    -- ── Lifecycle ───────────────────────────────────────

    expires_at TIMESTAMPTZ NOT NULL,

    is_used BOOLEAN NOT NULL
        DEFAULT FALSE,

    used_at TIMESTAMPTZ NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    ip_address VARCHAR(45) NULL,

    -- ── Foreign Keys ────────────────────────────────────

    CONSTRAINT fk_password_reset_token_user_account
        FOREIGN KEY (user_account_pk)
        REFERENCES nss.user_account (user_account_pk)
);

-- ── Indexes ─────────────────────────────────────────────

-- Lookup by user + active (not used, not expired)
CREATE INDEX IF NOT EXISTS idx_password_reset_token_user_active
    ON nss.password_reset_token (user_account_pk, is_used, expires_at);

-- Cleanup: find expired tokens for periodic purge
CREATE INDEX IF NOT EXISTS idx_password_reset_token_expires
    ON nss.password_reset_token (expires_at)
    WHERE is_used = FALSE;
