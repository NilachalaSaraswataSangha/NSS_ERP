-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 10_district.sql
-- Table: district
-- Depth: 2 (depends on state)
-- Sequence: #26 of 87
-- Version: 2.0 — SOL-ARCH-010 Amendment (Member-Assisted
--          Geographic Entry, 2026-10-03). District is now a
--          member-writable level: members may type an unseen
--          district, which is quarantined as PENDING until an
--          admin approves or corrects it. Added the shared
--          member-assisted columns (§16.8) and converted the
--          two table-level UNIQUE constraints to partial unique
--          indexes scoped to APPROVED, active rows (FND-BR-090),
--          so a PENDING member submission never collides with a
--          canonical row.
-- Authority: SOL-ARCH-010, SOL-ARCH-010 Amendment (2026-10-03),
--            SOL-FND-004 §15, §16.8, FND-BR-085 .. FND-BR-090
-- Owner: NSS_ERP_ADMIN
-- Note: submitted_by/reviewed_by reference nss.sangha_sevi.
--       The columns are created here as plain nullable UUID
--       (Foundation builds before Membership — sangha_sevi
--       doesn't exist yet); the real FK constraints are added
--       by 05_membership/16_foundation_audit_fk.sql once
--       sangha_sevi exists (Phase 7b of 02_build.sh).
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.district
(
    district_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    state_pk UUID NOT NULL,

    district_code VARCHAR(20) NOT NULL,

    district_name VARCHAR(100) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    -- ── Member-Assisted Geographic Entry (§16.8) ────────

    entry_status VARCHAR(20) NOT NULL
        DEFAULT 'APPROVED',

    submitted_by_sangha_sevi_pk UUID NULL,

    reviewed_by_sangha_sevi_pk UUID NULL,

    reviewed_at TIMESTAMPTZ NULL,

    admin_remarks TEXT NULL,

    corrected_into_district_pk UUID NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_district_state
        FOREIGN KEY (state_pk)
        REFERENCES nss.state (state_pk),

    CONSTRAINT fk_district_corrected_into
        FOREIGN KEY (corrected_into_district_pk)
        REFERENCES nss.district (district_pk),

    CONSTRAINT chk_district_entry_status
        CHECK (entry_status IN ('PENDING', 'APPROVED', 'CORRECTED')),

    CONSTRAINT chk_district_correction
        CHECK
        (
            (entry_status = 'CORRECTED'
                AND corrected_into_district_pk IS NOT NULL)
            OR
            (entry_status <> 'CORRECTED'
                AND corrected_into_district_pk IS NULL)
        ),

    CONSTRAINT chk_district_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_district_state
    ON nss.district (state_pk);

CREATE INDEX IF NOT EXISTS idx_district_active
    ON nss.district (is_active);

CREATE INDEX IF NOT EXISTS idx_district_entry_status
    ON nss.district (entry_status);

CREATE INDEX IF NOT EXISTS idx_district_name
    ON nss.district USING gin (district_name gin_trgm_ops);

-- ── Canonical Uniqueness Among Approved Rows (FND-BR-090) ─
CREATE UNIQUE INDEX IF NOT EXISTS uq_district_state_code_approved
    ON nss.district (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_district_state_name_approved
    ON nss.district (state_pk, district_name)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE;
