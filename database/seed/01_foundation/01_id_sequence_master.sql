-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 01_id_sequence_master.sql
-- Version: 1.0
-- =====================================================

INSERT INTO id_sequence_master
(
    sequence_code,
    sequence_name,
    prefix,
    current_value,
    padding_length
)
VALUES
(
    'PERSON',
    'Person Code',
    'P',
    0,
    8
),
(
    'SANGHA_SEVI',
    'Sangha Sevi ID',
    'SS',
    0,
    8
),
(
    'ORGANIZATION',
    'Organization Code',
    'ORG',
    0,
    8
),
(
    'FAMILY',
    'Family Code',
    'F',
    0,
    8
);