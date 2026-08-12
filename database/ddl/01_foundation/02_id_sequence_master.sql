-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 02_id_sequence_master.sql
-- Version: 1.0
-- =====================================================

CREATE TABLE id_sequence_master
(
    id_sequence_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    sequence_code VARCHAR(50) NOT NULL,

    sequence_name VARCHAR(100) NOT NULL,

    prefix VARCHAR(20) NOT NULL,

    current_value BIGINT NOT NULL
        DEFAULT 0,

    padding_length INTEGER NOT NULL
        DEFAULT 8,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT uq_id_sequence_code
        UNIQUE (sequence_code),

    CONSTRAINT uq_id_sequence_name
        UNIQUE (sequence_name)
);

CREATE INDEX idx_id_sequence_active
    ON id_sequence_master(is_active);