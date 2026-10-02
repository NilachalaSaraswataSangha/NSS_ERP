-- =====================================================
-- NSS ERP
-- Module: Authentication & Security
-- File: 03_registration_claim.sql
-- Table: nss.registration_claim
-- Depth: 3 (depends on user_account, person, organization, master_data)
-- Version: 1.0
-- Authority: SOL-AUTH-006 (Registration Claim Business Rules),
--            SOL-AUTH-007 (Registration Claim Table Design)
-- Owner: Authentication & Security
--
-- Design decisions:
--   - Stores self-declared membership claims pending admin approval
--   - One PENDING claim per user_account at a time (partial unique index)
--   - claimed_local_sakha_number is NOT validated at registration
--   - Claim lifecycle: PENDING -> APPROVED | REJECTED
--   - Approval triggers sangha_sevi + affiliation creation (API-level)
--   - person_pk is a denormalized FK for query convenience
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.registration_claim
(
    -- ── Identity ────────────────────────────────────────

    registration_claim_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- ── Relationships ───────────────────────────────────

    user_account_pk UUID NOT NULL,

    person_pk UUID NOT NULL,

    -- ── Claimed Membership Details ──────────────────────

    claimed_organization_pk UUID NOT NULL,

    claimed_membership_type_master_data_pk UUID NOT NULL,

    claimed_local_sakha_number VARCHAR(20) NULL,

    claimed_joining_date DATE NULL,

    -- Existing Parichaya Patra / Anumati Patra document number, for a
    -- registrant who already holds one (legacy member). Distinct from
    -- claimed_local_sakha_number (Tier 2 identity) — this is the Tier 3
    -- annual Kendra/Sakha-wide credential number (MEM-PENDING-001 /
    -- Tier 4 Frozen Decisions "Three-tier member identity"). NULL means
    -- a new one is auto-generated for the current FY at approval time
    -- (see api/helpers.py::issue_membership_credential()).
    claimed_credential_document_number VARCHAR(30) NULL,

    -- ── Darshak Attendance ──────────────────────────────

    darshak_organization_pk UUID NULL,

    -- Local Sakha Number at the darshak_organization_pk (attending) Sakha —
    -- separate namespace from claimed_local_sakha_number, which is the
    -- home Sakha's number. NULL while the attending Sakha hasn't assigned
    -- one yet; required at approval once darshak_organization_pk is set
    -- (mirrors claimed_local_sakha_number's own requirement).
    darshak_local_sakha_number VARCHAR(20) NULL,

    -- ── Claim Status ────────────────────────────────────

    claim_status VARCHAR(20) NOT NULL
        DEFAULT 'PENDING',

    -- ── Review ──────────────────────────────────────────

    reviewed_by_user_account_pk UUID NULL,

    reviewed_at TIMESTAMPTZ NULL,

    admin_remarks TEXT NULL,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    -- ── Foreign Keys ────────────────────────────────────

    CONSTRAINT fk_registration_claim_user_account
        FOREIGN KEY (user_account_pk)
        REFERENCES nss.user_account (user_account_pk),

    CONSTRAINT fk_registration_claim_person
        FOREIGN KEY (person_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT fk_registration_claim_organization
        FOREIGN KEY (claimed_organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT fk_registration_claim_membership_type
        FOREIGN KEY (claimed_membership_type_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT fk_registration_claim_darshak_org
        FOREIGN KEY (darshak_organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT fk_registration_claim_reviewer
        FOREIGN KEY (reviewed_by_user_account_pk)
        REFERENCES nss.user_account (user_account_pk),

    -- ── CHECK Constraints ───────────────────────────────

    CONSTRAINT chk_registration_claim_status
        CHECK (claim_status IN ('PENDING', 'APPROVED', 'REJECTED')),

    CONSTRAINT chk_registration_claim_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_registration_claim_user_account
    ON nss.registration_claim (user_account_pk);

CREATE INDEX IF NOT EXISTS idx_registration_claim_person
    ON nss.registration_claim (person_pk);

CREATE INDEX IF NOT EXISTS idx_registration_claim_status
    ON nss.registration_claim (claim_status);

CREATE INDEX IF NOT EXISTS idx_registration_claim_organization
    ON nss.registration_claim (claimed_organization_pk);

-- Partial unique index: one PENDING claim per user_account (AUTH-BR-083)
CREATE UNIQUE INDEX IF NOT EXISTS uq_registration_claim_one_pending
    ON nss.registration_claim (user_account_pk)
    WHERE claim_status = 'PENDING';
