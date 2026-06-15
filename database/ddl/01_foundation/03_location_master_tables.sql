-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 03_location_master_tables.sql
-- Version: 1.1
-- =====================================================

-- =====================================================
-- COUNTRY MASTER
-- =====================================================

CREATE TABLE country_master
(
    country_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    country_code CHAR(2) NOT NULL,

    country_name VARCHAR(100) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT uq_country_code
        UNIQUE (country_code),

    CONSTRAINT uq_country_name
        UNIQUE (country_name)
);

CREATE INDEX idx_country_active
    ON country_master(is_active);

-- =====================================================
-- STATE / PROVINCE MASTER
-- =====================================================

CREATE TABLE state_province_master
(
    state_province_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    country_pk UUID NOT NULL,

    state_province_code VARCHAR(20) NOT NULL,

    state_province_name VARCHAR(100) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_state_country
        FOREIGN KEY (country_pk)
        REFERENCES country_master(country_pk),

    CONSTRAINT uq_state_country_code
        UNIQUE (country_pk, state_province_code),

    CONSTRAINT uq_state_country_name
        UNIQUE (country_pk, state_province_name)
);

CREATE INDEX idx_state_country
    ON state_province_master(country_pk);

CREATE INDEX idx_state_active
    ON state_province_master(is_active);

-- =====================================================
-- DISTRICT / REGION MASTER
-- =====================================================

CREATE TABLE district_region_master
(
    district_region_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    state_province_pk UUID NOT NULL,

    district_region_code VARCHAR(20) NULL,

    district_region_name VARCHAR(100) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_district_state
        FOREIGN KEY (state_province_pk)
        REFERENCES state_province_master(state_province_pk),

    CONSTRAINT uq_district_state_name
        UNIQUE (state_province_pk, district_region_name)
);

CREATE INDEX idx_district_state
    ON district_region_master(state_province_pk);

CREATE INDEX idx_district_active
    ON district_region_master(is_active);

-- =====================================================
-- CITY / VILLAGE MASTER
-- =====================================================

CREATE TABLE city_village_master
(
    city_village_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    district_region_pk UUID NOT NULL,

    city_village_name VARCHAR(150) NOT NULL,

    city_village_type VARCHAR(20) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_city_district
        FOREIGN KEY (district_region_pk)
        REFERENCES district_region_master(district_region_pk),

    CONSTRAINT uq_city_district_name
        UNIQUE (district_region_pk, city_village_name),

    CONSTRAINT chk_city_village_type
        CHECK
        (
            city_village_type IN
            (
                'CITY',
                'TOWN',
                'VILLAGE'
            )
        )
);

CREATE INDEX idx_city_district
    ON city_village_master(district_region_pk);

CREATE INDEX idx_city_active
    ON city_village_master(is_active);

-- =====================================================
-- POSTAL CODE MASTER
-- =====================================================

CREATE TABLE postal_code_master
(
    postal_code_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    country_pk UUID NOT NULL,

    postal_code VARCHAR(20) NOT NULL,

    post_office_name VARCHAR(150) NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_postal_country
        FOREIGN KEY (country_pk)
        REFERENCES country_master(country_pk),

    CONSTRAINT uq_country_postal_code
        UNIQUE (country_pk, postal_code)
);

CREATE INDEX idx_postal_country
    ON postal_code_master(country_pk);

CREATE INDEX idx_postal_active
    ON postal_code_master(is_active);

CREATE INDEX idx_postal_code
    ON postal_code_master(postal_code);

-- =====================================================
-- CITY/VILLAGE ↔ POSTAL CODE MAP
-- =====================================================

CREATE TABLE city_village_postal_code_map
(
    city_village_postal_code_map_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    city_village_pk UUID NOT NULL,

    postal_code_pk UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_map_city
        FOREIGN KEY (city_village_pk)
        REFERENCES city_village_master(city_village_pk),

    CONSTRAINT fk_map_postal_code
        FOREIGN KEY (postal_code_pk)
        REFERENCES postal_code_master(postal_code_pk),

    CONSTRAINT uq_city_postal_code
        UNIQUE
        (
            city_village_pk,
            postal_code_pk
        )
);

CREATE INDEX idx_map_city
    ON city_village_postal_code_map(city_village_pk);

CREATE INDEX idx_map_postal_code
    ON city_village_postal_code_map(postal_code_pk);