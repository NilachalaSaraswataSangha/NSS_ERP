-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 16_festival_master.sql
-- Table: festival_master
-- Depth: 0 (Root — no FK dependencies)
-- Version: 1.0
-- Authority: SOL-ARCH-013 (Festival Reference Calendar Architecture)
-- Owner: NSS_ERP_ADMIN
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.festival_master
(
    festival_master_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    festival_code VARCHAR(50) NOT NULL,

    festival_name VARCHAR(150) NOT NULL,

    festival_name_odia VARCHAR(150) NULL,

    -- Descriptive only (e.g. 'Phalguna Purnima'). Documents why the
    -- Gregorian date shifts year to year. NOTHING PARSES THIS — the
    -- observed date in festival_calendar_date is always authoritative
    -- data entered by an administrator, never computed from this column
    -- (SOL-ARCH-013 §3).
    lunar_basis VARCHAR(100) NULL,

    -- TRUE when a business rule keys off this festival's date (Dola
    -- Purnima: MBR-011A, MBR-029, membership renewal deadline).
    is_erp_reference_date BOOLEAN NOT NULL
        DEFAULT FALSE,

    description TEXT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT uq_festival_master_code
        UNIQUE (festival_code),

    CONSTRAINT uq_festival_master_name
        UNIQUE (festival_name),

    CONSTRAINT chk_festival_master_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_festival_master_code
    ON nss.festival_master (festival_code);

CREATE INDEX IF NOT EXISTS idx_festival_master_active
    ON nss.festival_master (is_active);
