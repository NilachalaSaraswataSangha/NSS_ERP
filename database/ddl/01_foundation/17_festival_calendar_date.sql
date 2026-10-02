-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 17_festival_calendar_date.sql
-- Table: festival_calendar_date
-- Depth: 1 (depends on festival_master)
-- Version: 1.0
-- Authority: SOL-ARCH-013 (Festival Reference Calendar Architecture)
-- Owner: NSS_ERP_ADMIN
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.festival_calendar_date
(
    festival_calendar_date_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    festival_master_pk UUID NOT NULL,

    calendar_year INTEGER NOT NULL,

    -- The authoritative observed civil date for this festival/year. Always
    -- entered data, never computed (SOL-ARCH-013 §3).
    observed_date DATE NOT NULL,

    -- FALSE = provisional/projected (safe for display/forecasting only).
    -- TRUE  = confirmed by the Kendra Sangha; required before any business
    --         rule may create a legally significant record keyed to this
    --         date (MBR-011A, MBR-029, credential valid_from/valid_to —
    --         SOL-ARCH-013 FC-DECISION-01).
    is_confirmed BOOLEAN NOT NULL
        DEFAULT FALSE,

    -- Provenance: almanac/panchang, Kendra Sangha circular, or meeting
    -- minute reference.
    source_reference VARCHAR(200) NULL,

    remarks TEXT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_festival_calendar_date_festival
        FOREIGN KEY (festival_master_pk)
        REFERENCES nss.festival_master (festival_master_pk),

    -- One authoritative date per festival per year.
    CONSTRAINT uq_festival_calendar_date_festival_year
        UNIQUE (festival_master_pk, calendar_year),

    CONSTRAINT chk_festival_calendar_date_year_range
        CHECK (calendar_year BETWEEN 1900 AND 2200),

    -- Keeps the stored calendar_year consistent with observed_date. Valid
    -- only for festivals that cannot straddle 1 January — true for Dola
    -- Purnima (late Feb–March). See SOL-ARCH-013 OPEN-FC-04 if a future
    -- festival needs to cross the year boundary.
    CONSTRAINT chk_festival_calendar_date_year_matches
        CHECK (EXTRACT(YEAR FROM observed_date) = calendar_year),

    CONSTRAINT chk_festival_calendar_date_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_festival_calendar_date_festival
    ON nss.festival_calendar_date (festival_master_pk);

CREATE INDEX IF NOT EXISTS idx_festival_calendar_date_year
    ON nss.festival_calendar_date (calendar_year);

-- Supports "next reference date on or after X" — the dominant query shape
-- for MBR-011A / MBR-029 / credential-validity resolution.
CREATE INDEX IF NOT EXISTS idx_festival_calendar_date_observed
    ON nss.festival_calendar_date (observed_date);
