-- =====================================================
-- NSS ERP
-- Module: Person
-- File: 03_person_address.sql
-- Table: nss.person_address
-- Depth: 3 (depends on person, master_data,
--         city_village, postal_code)
-- Version: 3.0 — SOL-ARCH-010 Amendment (2026-10-01):
--          simplified geographic FK model. The bundled
--          city_village_postal_code_map_pk FK is replaced by
--          two direct, independently-nullable FKs
--          (city_village_pk, postal_code_pk), matching the
--          pattern already used by nss.organization. The
--          city_village_postal_code_map junction is retired
--          (see Foundation 13_city_village_postal_code_map.sql).
--          This table has no live write path and no seed data
--          yet, so the change is additive risk-free.
-- Authority: SOL-PER-001 §37–38, SOL-PER-003
--            PER-BR-064/065/066, SOL-ARCH-010 Amendment
--            (2026-10-01)
-- Owner: NSS_ERP_ADMIN
-- Note: address_type now references Foundation
--       master_data (category ADDRESS_TYPE) instead
--       of the superseded address_type_master table.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.person_address
(
    person_address_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    person_pk UUID NOT NULL,

    address_type_master_data_pk UUID NOT NULL,

    address_line_1 VARCHAR(255) NOT NULL,

    address_line_2 VARCHAR(255) NULL,

    landmark VARCHAR(255) NULL,

    city_village_pk UUID NULL,

    postal_code_pk UUID NULL,

    is_primary BOOLEAN NOT NULL
        DEFAULT FALSE,

    remarks TEXT NULL,

    -- ── Lifecycle ───────────────────────────────────────

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT fk_person_address_person
        FOREIGN KEY (person_pk)
        REFERENCES nss.person (person_pk),

    CONSTRAINT fk_person_address_type
        FOREIGN KEY (address_type_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT fk_person_address_city_village
        FOREIGN KEY (city_village_pk)
        REFERENCES nss.city_village (city_village_pk),

    CONSTRAINT fk_person_address_postal_code
        FOREIGN KEY (postal_code_pk)
        REFERENCES nss.postal_code (postal_code_pk),

    CONSTRAINT chk_person_address_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_person_address_person
    ON nss.person_address (person_pk);

CREATE INDEX IF NOT EXISTS idx_person_address_type
    ON nss.person_address (address_type_master_data_pk);

CREATE INDEX IF NOT EXISTS idx_person_address_city_village
    ON nss.person_address (city_village_pk);

CREATE INDEX IF NOT EXISTS idx_person_address_postal_code
    ON nss.person_address (postal_code_pk);

CREATE INDEX IF NOT EXISTS idx_person_address_active
    ON nss.person_address (is_active);

-- ── Only One Primary Address Per Person ─────────────────

CREATE UNIQUE INDEX IF NOT EXISTS uq_person_primary_address
    ON nss.person_address (person_pk)
    WHERE is_primary = TRUE AND is_active = TRUE;
