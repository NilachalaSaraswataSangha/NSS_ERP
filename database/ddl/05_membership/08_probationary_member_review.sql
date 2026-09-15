-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 08_probationary_member_review.sql
-- Table: nss.probationary_member_review
-- Depth: 3 (depends on sangha_sevi)
-- Version: 1.0
-- Authority: SOL-MEM-005 §11, SOL-MEM-003
--            MBR-008 through MBR-015
-- Owner: NSS_ERP_ADMIN
-- Note: Preserves progression history of probationary
--       members. Does not replace the membership record.
--       At least one year probationary + one year
--       training required for Regular enrolment
--       (Bye-Law §B(b)(i)-(ii)).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.probationary_member_review
(
    probationary_member_review_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sangha_sevi_pk UUID NOT NULL,

    review_date DATE NOT NULL,

    reviewed_by_sangha_sevi_pk UUID NULL,

    -- PERIODIC, FINAL, SPECIAL
    review_type VARCHAR(20) NOT NULL,

    -- PASS, FAIL, DEFERRED
    outcome VARCHAR(20) NOT NULL,

    training_completed BOOLEAN NOT NULL
        DEFAULT FALSE,

    -- Sakha recommendation for Regular enrolment.
    sakha_recommendation BOOLEAN NULL,

    remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_prob_review_sevi
        FOREIGN KEY (sangha_sevi_pk)
        REFERENCES nss.sangha_sevi (sangha_sevi_pk),

    CONSTRAINT chk_prob_review_type
        CHECK
        (
            review_type IN ('PERIODIC', 'FINAL', 'SPECIAL')
        ),

    CONSTRAINT chk_prob_review_outcome
        CHECK
        (
            outcome IN ('PASS', 'FAIL', 'DEFERRED')
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_prob_review_sevi
    ON nss.probationary_member_review (sangha_sevi_pk);

CREATE INDEX IF NOT EXISTS idx_prob_review_date
    ON nss.probationary_member_review (review_date);

CREATE INDEX IF NOT EXISTS idx_prob_review_outcome
    ON nss.probationary_member_review (outcome);
