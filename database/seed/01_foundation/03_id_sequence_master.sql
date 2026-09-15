-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 03_id_sequence_master.sql
-- Version: 2.2 — INSERT is now an upsert (ON CONFLICT ... DO UPDATE),
--          so a partial re-run no longer silently skips rows after
--          the first pre-existing row it hits
-- Authority: SOL-FND-004 §11
-- Owner: NSS_ERP_ADMIN
-- =====================================================

INSERT INTO nss.id_sequence_master
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
    10
),
(
    'SANGHA_SEVI',
    'Sangha Sevi Code',
    'SS',
    0,
    8
),
(
    'ANCHALIKA',
    'Anchalika Code',
    'ANC',
    0,
    8
),
(
    'ZILLA',
    'Zilla Code',
    'ZL',
    0,
    8
),
(
    'SAKHA',
    'Sakha Code',
    'SKH',
    0,
    8
),
(
    'SAKHA_ASANA',
    'Sakha Asana Code',
    'SA',
    0,
    8
),
(
    'PATHA_CHAKRA',
    'Patha Chakra Code',
    'PC',
    0,
    8
),
(
    'PARIBARIK_ASANA',
    'Paribarik Asana Code',
    'PA',
    0,
    5
),
(
    'PARIBARIK_SANGHA',
    'Paribarik Sangha Code',
    'PS',
    0,
    3
),
(
    'FAMILY',
    'Family Code',
    'F',
    0,
    8
),
(
    'DOCUMENT',
    'Document Code',
    'DOC',
    0,
    8
),
(
    'KUMARI_SANGHA',
    'Kumari Sangha Code',
    'KS',
    0,
    5
),
(
    'SEVAK_SANGHA',
    'Sevak Sangha Code',
    'SEV',
    0,
    5
),
(
    'MAHILA_SANGHA',
    'Mahila Sangha Code',
    'MS',
    0,
    5
)
ON CONFLICT (sequence_code) DO UPDATE SET
    sequence_name  = EXCLUDED.sequence_name,
    prefix         = EXCLUDED.prefix,
    padding_length = EXCLUDED.padding_length;
    -- current_value is deliberately excluded: once ID generation writes
    -- to it at runtime, a re-run of this seed must never reset an
    -- advanced counter back to its seed default.
