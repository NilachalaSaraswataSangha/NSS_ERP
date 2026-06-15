-- =====================================================
-- NSS ERP
-- Module: Person
-- File: 02_person.sql
-- Version: 1.1
-- =====================================================

CREATE TABLE person
(
    person_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    person_code VARCHAR(20) NOT NULL,

    first_name VARCHAR(100) NOT NULL,

    middle_name VARCHAR(100) NULL,

    last_name VARCHAR(100) NULL,

    gender_pk UUID NOT NULL,

    date_of_birth DATE NULL,

    country_phone_code VARCHAR(10) NULL,

    mobile_number VARCHAR(20) NULL,

    email VARCHAR(255) NULL,

    marital_status_pk UUID NULL,

    remarks TEXT NULL,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT uq_person_code
        UNIQUE (person_code),

    CONSTRAINT uq_person_mobile
        UNIQUE
        (
            country_phone_code,
            mobile_number
        ),

    CONSTRAINT fk_person_gender
        FOREIGN KEY (gender_pk)
        REFERENCES gender_master(gender_pk),

    CONSTRAINT fk_person_marital_status
        FOREIGN KEY (marital_status_pk)
        REFERENCES marital_status_master(marital_status_pk),

    CONSTRAINT chk_person_contact_required
        CHECK
        (
            mobile_number IS NOT NULL
            OR
            email IS NOT NULL
        ),

    CONSTRAINT chk_person_mobile_pair
        CHECK
        (
            (
                country_phone_code IS NULL
                AND mobile_number IS NULL
            )
            OR
            (
                country_phone_code IS NOT NULL
                AND mobile_number IS NOT NULL
            )
        )
);

CREATE INDEX idx_person_code
    ON person(person_code);

CREATE INDEX idx_person_first_name
    ON person(first_name);

CREATE INDEX idx_person_last_name
    ON person(last_name);

CREATE INDEX idx_person_mobile
    ON person(country_phone_code, mobile_number);

CREATE INDEX idx_person_email
    ON person(email);

CREATE INDEX idx_person_gender
    ON person(gender_pk);

CREATE INDEX idx_person_marital_status
    ON person(marital_status_pk);

CREATE INDEX idx_person_is_active
    ON person(is_active);