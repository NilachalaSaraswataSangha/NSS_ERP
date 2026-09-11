-- =====================================================
-- NSS ERP
-- Module: Person
-- File: 02_person.sql
-- Table: nss.person
-- Depth: 2 (depends on master_data, document_master)
-- Version: 2.0
-- Authority: SOL-PER-001, SOL-PER-003, SOL-PER-004,
--            SOL-PER-005
-- Owner: NSS_ERP_ADMIN
-- Note: Audit actor FKs (*_by_sangha_sevi_pk) are
--       NULLABLE columns included in Pass 1. Their FK
--       constraints are deferred to Pass 2 (after
--       sangha_sevi table exists).
-- =====================================================

CREATE TABLE nss.person
(
    -- ── Identity ────────────────────────────────────────

    person_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    person_id VARCHAR(20) NOT NULL,

    -- ── Demographics ────────────────────────────────────

    first_name VARCHAR(100) NOT NULL,

    middle_name VARCHAR(100) NULL,

    last_name VARCHAR(100) NULL,

    date_of_birth DATE NULL,

    date_of_death DATE NULL,

    gender_master_data_pk UUID NULL,

    marital_status_master_data_pk UUID NULL,

    blood_group_master_data_pk UUID NULL,

    -- ── Contact ─────────────────────────────────────────

    country_phone_code VARCHAR(10) NULL,

    mobile_number VARCHAR(20) NULL,

    email VARCHAR(255) NULL,

    -- ── Sensitive Identity (Aadhaar) ────────────────────
    -- All three columns are all-or-nothing: either all
    -- NULL or all populated. Encrypted value stores the
    -- full Aadhaar; hash enables lookup without
    -- decryption; last4 supports masked display.

    aadhaar_encrypted BYTEA NULL,

    aadhaar_hash VARCHAR(64) NULL,

    aadhaar_last4 VARCHAR(4) NULL,

    -- ── Photo ───────────────────────────────────────────
    -- References Foundation document_master.
    -- The photo binary is stored externally; this FK
    -- points to the document metadata record.

    photo_document_master_pk UUID NULL,

    -- ── Emergency Contact ───────────────────────────────

    emergency_contact_name VARCHAR(200) NULL,

    emergency_contact_phone VARCHAR(20) NULL,

    emergency_relationship_master_data_pk UUID NULL,

    -- ── Other ───────────────────────────────────────────

    remarks TEXT NULL,

    -- ── Lifecycle ───────────────────────────────────────

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    -- ── Audit ───────────────────────────────────────────

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    created_by_sangha_sevi_pk UUID NULL,

    updated_at TIMESTAMPTZ NULL,

    updated_by_sangha_sevi_pk UUID NULL,

    deleted_at TIMESTAMPTZ NULL,

    deleted_by_sangha_sevi_pk UUID NULL,

    -- ── Constraints ─────────────────────────────────────

    CONSTRAINT uq_person_id
        UNIQUE (person_id),

    CONSTRAINT fk_person_gender
        FOREIGN KEY (gender_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT fk_person_marital_status
        FOREIGN KEY (marital_status_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT fk_person_blood_group
        FOREIGN KEY (blood_group_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

    CONSTRAINT fk_person_photo_document
        FOREIGN KEY (photo_document_master_pk)
        REFERENCES nss.document_master (document_master_pk),

    CONSTRAINT fk_person_emergency_relationship
        FOREIGN KEY (emergency_relationship_master_data_pk)
        REFERENCES nss.master_data (master_data_pk),

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
        ),

    CONSTRAINT chk_person_death_after_birth
        CHECK
        (
            date_of_death IS NULL
            OR date_of_birth IS NULL
            OR date_of_death >= date_of_birth
        ),

    CONSTRAINT chk_person_aadhaar_consistency
        CHECK
        (
            (
                aadhaar_encrypted IS NULL
                AND aadhaar_hash IS NULL
                AND aadhaar_last4 IS NULL
            )
            OR
            (
                aadhaar_encrypted IS NOT NULL
                AND aadhaar_hash IS NOT NULL
                AND aadhaar_last4 IS NOT NULL
            )
        ),

    CONSTRAINT chk_person_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        ),

    -- ── Format Validation ───────────────────────────────

    CONSTRAINT chk_person_country_phone_code_format
        CHECK
        (
            country_phone_code IS NULL
            OR country_phone_code ~ '^\+[0-9]{1,4}$'
        ),

    CONSTRAINT chk_person_mobile_number_format
        CHECK
        (
            mobile_number IS NULL
            OR mobile_number ~ '^[0-9]{7,15}$'
        ),

    CONSTRAINT chk_person_email_format
        CHECK
        (
            email IS NULL
            OR email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'
        ),

    CONSTRAINT chk_person_aadhaar_last4_format
        CHECK
        (
            aadhaar_last4 IS NULL
            OR aadhaar_last4 ~ '^[0-9]{4}$'
        ),

    CONSTRAINT chk_person_emergency_phone_format
        CHECK
        (
            emergency_contact_phone IS NULL
            OR emergency_contact_phone ~ '^[0-9]{7,15}$'
        )
);

-- ── Indexes ─────────────────────────────────────────────

CREATE INDEX idx_person_id
    ON nss.person (person_id);

CREATE INDEX idx_person_first_name
    ON nss.person (first_name);

CREATE INDEX idx_person_last_name
    ON nss.person (last_name)
    WHERE last_name IS NOT NULL;

CREATE INDEX idx_person_gender
    ON nss.person (gender_master_data_pk)
    WHERE gender_master_data_pk IS NOT NULL;

CREATE INDEX idx_person_marital_status
    ON nss.person (marital_status_master_data_pk)
    WHERE marital_status_master_data_pk IS NOT NULL;

CREATE INDEX idx_person_blood_group
    ON nss.person (blood_group_master_data_pk)
    WHERE blood_group_master_data_pk IS NOT NULL;

CREATE INDEX idx_person_email
    ON nss.person (email)
    WHERE email IS NOT NULL;

CREATE INDEX idx_person_is_active
    ON nss.person (is_active);

-- NULL-aware mobile uniqueness (PER-BR-030)
CREATE UNIQUE INDEX uq_person_mobile_when_present
    ON nss.person (country_phone_code, mobile_number)
    WHERE mobile_number IS NOT NULL;

-- Aadhaar hash uniqueness — one Aadhaar per person
CREATE UNIQUE INDEX uq_person_aadhaar_hash
    ON nss.person (aadhaar_hash)
    WHERE aadhaar_hash IS NOT NULL;

-- trigram index for name search (PER-BR-039)
CREATE INDEX idx_person_first_name_trgm
    ON nss.person USING gin (first_name gin_trgm_ops);
