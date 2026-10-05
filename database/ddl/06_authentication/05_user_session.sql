-- =====================================================
-- NSS ERP
-- Module: Authentication & Security
-- File: 05_user_session.sql
-- Table: nss.user_session
-- Depth: 3 (depends on user_account)
-- Version: 1.0
-- Authority: Tier 5 advisory A4 resolution (2026-10-05) —
--            session/device tracking + revocation
-- Owner: Authentication & Security
--
-- Purpose:
--   Stateful session record created at login and updated
--   on every access-token refresh, so a "logged-in
--   devices" UI can list and individually revoke a user's
--   active sessions. Chosen over a stateless
--   credentials_changed_at approach specifically because
--   that UI requirement cannot be met statelessly.
--
-- Design decisions:
--   - One row per login (per device/browser), not per user
--   - issued_at: set once at login; last_seen_at: bumped on
--     each access-token refresh (liveness/"last active")
--   - expires_at mirrors the refresh token's exp so expired
--     sessions can be filtered without decoding the JWT
--   - revoked_at: set on logout or explicit "sign out this
--     device" action; NULL means still active
--   - No soft-delete columns (no is_active/deleted_at) —
--     sessions are transient, not business records; their
--     entire lifecycle is expressed through revoked_at
--     (and expires_at), so a separate soft-delete flag
--     would be redundant
--   - user_agent/device_label captured at login only, for
--     display in the devices UI (device_label is a
--     server-computed human-readable summary, e.g.
--     "Chrome on macOS")
--
-- Dependencies:
--   - 06_authentication/01_user_account.sql
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.user_session
(
    -- ── Identity ────────────────────────────────────────

    user_session_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    user_account_pk UUID NOT NULL,

    -- ── Lifecycle ───────────────────────────────────────

    issued_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    last_seen_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    expires_at TIMESTAMPTZ NOT NULL,

    revoked_at TIMESTAMPTZ NULL,

    -- ── Device Info ─────────────────────────────────────

    user_agent VARCHAR(500) NULL,

    ip_address VARCHAR(45) NULL,

    device_label VARCHAR(200) NULL,

    -- ── Foreign Keys ────────────────────────────────────

    CONSTRAINT fk_user_session_user_account
        FOREIGN KEY (user_account_pk)
        REFERENCES nss.user_account (user_account_pk)
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_user_session_user_account
    ON nss.user_session (user_account_pk);

-- Active-sessions-list lookup ("logged-in devices" UI)
CREATE INDEX IF NOT EXISTS idx_user_session_user_active
    ON nss.user_session (user_account_pk, revoked_at)
    WHERE revoked_at IS NULL;

-- Cleanup: find expired sessions for periodic purge
CREATE INDEX IF NOT EXISTS idx_user_session_expires
    ON nss.user_session (expires_at);
