-- =====================================================
-- NSS ERP
-- Module: Person
-- File: 03_person_address.sql
-- Table: nss.person_address
-- Depth: 3 (depends on person, master_data,
--         city_village_postal_code_map)
-- Version: 2.0
-- Authority: SOL-PER-001 §37–38, SOL-PER-003
--            PER-BR-064/065/066
-- Owner: NSS_ERP_ADMIN
-- Note: address_type now references Foundation
--       master_data (category ADDRESS_TYPE) instead
--       of the superseded address_type_master table.
-- =====================================================

CREATE TABLE nss.person_address
(
    person_address_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    person_pk UUID NOT NULL,

    address_type_master_data_pk UUID NOT NULL,

    address_line_1 VARCHAR(255) NOT NULL,

    address_line_2 VARCHAR(255) NULL,

    landmark VARCHAR(255) NULL,

    city_village_postal_code_map_pk UUID NOT NULL,

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

    CONSTRAINT fk_person_address_location
        FOREIGN KEY (city_village_postal_code_map_pk)
        REFERENCES nss.city_village_postal_code_map
            (city_village_postal_code_map_pk),

    CONSTRAINT chk_person_address_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_person_address_person
    ON nss.person_address (person_pk);

CREATE INDEX idx_person_address_type
    ON nss.person_address (address_type_master_data_pk);

CREATE INDEX idx_person_address_location
    ON nss.person_address (city_village_postal_code_map_pk);

CREATE INDEX idx_person_address_active
    ON nss.person_address (is_active);

-- ── Only One Primary Address Per Person ─────────────────

CREATE UNIQUE INDEX uq_person_primary_address
    ON nss.person_address (person_pk)
    WHERE is_primary = TRUE AND is_active = TRUE;
