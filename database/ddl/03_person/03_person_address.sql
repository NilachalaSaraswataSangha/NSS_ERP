-- =====================================================
-- NSS ERP
-- Module: Person
-- File: 03_person_address.sql
-- Version: 1.1
-- =====================================================

CREATE TABLE person_address
(
    person_address_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    person_pk UUID NOT NULL,

    address_type_pk UUID NOT NULL,

    address_line_1 VARCHAR(255) NOT NULL,

    address_line_2 VARCHAR(255) NULL,

    landmark VARCHAR(255) NULL,

    city_village_postal_code_map_pk UUID NOT NULL,

    is_primary BOOLEAN NOT NULL
        DEFAULT FALSE,

    remarks TEXT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_person_address_person
        FOREIGN KEY (person_pk)
        REFERENCES person(person_pk),

    CONSTRAINT fk_person_address_type
        FOREIGN KEY (address_type_pk)
        REFERENCES address_type_master(address_type_pk),

    CONSTRAINT fk_person_address_location
        FOREIGN KEY (city_village_postal_code_map_pk)
        REFERENCES city_village_postal_code_map(city_village_postal_code_map_pk)
);

-- =====================================================
-- Indexes
-- =====================================================

CREATE INDEX idx_person_address_person
    ON person_address(person_pk);

CREATE INDEX idx_person_address_type
    ON person_address(address_type_pk);

CREATE INDEX idx_person_address_location
    ON person_address(city_village_postal_code_map_pk);

CREATE INDEX idx_person_address_active
    ON person_address(is_active);

-- =====================================================
-- Only One Primary Address Per Person
-- =====================================================

CREATE UNIQUE INDEX uq_person_primary_address
ON person_address(person_pk)
WHERE is_primary = TRUE;
