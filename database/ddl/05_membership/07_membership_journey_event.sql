-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 07_membership_journey_event.sql
-- Table: nss.membership_journey_event
-- Depth: 3 (depends on sangha_sevi)
-- Version: 1.0
-- Authority: SOL-MEM-005 §10, SOL-MEM-003
-- Owner: NSS_ERP_ADMIN
-- Note: Chronological timeline of membership lifecycle
--       events. Event catalogue controlled via
--       application layer (not FK to master_data —
--       event types are extensible and module-specific).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.membership_journey_event
(
    membership_journey_event_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    -- Event type: MEMBERSHIP_CREATED,
    -- PROBATIONARY_STARTED, TRAINING_STARTED,
    -- PROBATIONARY_REVIEW, REGULAR_ENROLMENT,
    -- ASSOCIATE_ENROLMENT, RENEWAL, TRANSFER,
    -- STATUS_CHANGE, etc.
    event_type VARCHAR(50) NOT NULL,

    event_date DATE NOT NULL,

    -- Optional reference to related record
    -- (e.g., transfer PK, renewal PK).
    event_reference VARCHAR(255) NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_mem_journey_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk)
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_mem_journey_sevi
    ON nss.membership_journey_event (sangha_sevi_pk);

CREATE INDEX IF NOT EXISTS idx_mem_journey_event_type
    ON nss.membership_journey_event (event_type);

CREATE INDEX IF NOT EXISTS idx_mem_journey_event_date
    ON nss.membership_journey_event (event_date);
