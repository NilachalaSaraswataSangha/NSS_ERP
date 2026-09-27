-- =====================================================
-- NSS ERP
-- Module: Foundation / Audit
-- File: 14_system_event_log.sql
-- Table: system_event_log
-- Depth: 0 (Root — no FK constraints; references stored
--         as UUID values to avoid circular dependencies)
-- Version: 1.0
-- Authority: SOL-AUDIT-004 §8, §9
--            Data Change Architecture (2026-09-22)
-- Owner: NSS_ERP_ADMIN
-- Note: Centralized, immutable audit trail.
--       Every authenticated write operation (INSERT,
--       UPDATE, soft-DELETE) is logged here by the
--       application layer. Rows are INSERT-only —
--       no UPDATE or DELETE permitted on this table.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.system_event_log
(
    -- ── Identity ────────────────────────────────────
    system_event_log_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- ── Timestamp ───────────────────────────────────
    event_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    -- ── Actor ───────────────────────────────────────
    -- The Sangha Sevi who performed the action.
    -- NULL for unauthenticated / system-initiated events.
    actor_sangha_sevi_pk UUID NULL,

    -- The user account (for cross-reference / login events
    -- where sangha_sevi may not exist yet).
    actor_user_account_pk UUID NULL,

    -- ── Action ──────────────────────────────────────
    -- One of: CREATE, UPDATE, DELETE, APPROVE, REJECT,
    -- STATUS_CHANGE, LOGIN, PASSWORD_CHANGE, etc.
    action VARCHAR(50) NOT NULL,

    -- ── Target ──────────────────────────────────────
    -- Schema-qualified table name, e.g. 'person', 'sangha_sevi'.
    table_name VARCHAR(100) NOT NULL,

    -- PK of the affected record.
    record_pk UUID NOT NULL,

    -- ── Context ─────────────────────────────────────
    -- Module or functional area, e.g. 'admin', 'auth',
    -- 'claim_approval', 'family', 'registration'.
    module VARCHAR(50) NULL,

    -- Human-readable summary of what happened.
    summary VARCHAR(500) NULL,

    -- Optional JSON payload: changed fields, before/after
    -- values, request metadata, etc.
    detail JSONB NULL,

    -- ── Result ──────────────────────────────────────
    -- TRUE = success, FALSE = failure (e.g. rejected
    -- approval). NULL = not applicable.
    is_success BOOLEAN NULL DEFAULT TRUE
);

-- ── Indexes ─────────────────────────────────────────
-- Primary lookup: "show me all events for this record"
CREATE INDEX IF NOT EXISTS idx_sel_table_record
    ON nss.system_event_log (table_name, record_pk);

-- Actor lookup: "show me everything this person did"
CREATE INDEX IF NOT EXISTS idx_sel_actor
    ON nss.system_event_log (actor_sangha_sevi_pk)
    WHERE actor_sangha_sevi_pk IS NOT NULL;

-- Timeline: "show me events in this time range"
CREATE INDEX IF NOT EXISTS idx_sel_event_at
    ON nss.system_event_log (event_at);

-- Module filter: "all admin events", "all auth events"
CREATE INDEX IF NOT EXISTS idx_sel_module
    ON nss.system_event_log (module, event_at);

-- Action filter: "all APPROVE events"
CREATE INDEX IF NOT EXISTS idx_sel_action
    ON nss.system_event_log (action, event_at);
