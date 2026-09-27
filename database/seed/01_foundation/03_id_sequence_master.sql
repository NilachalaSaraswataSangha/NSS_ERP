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
    0
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

-- =====================================================
-- Counter sync for organization-code sequences (ORG-BR-105)
-- =====================================================
-- Organization codes are the org-type sequence value materialised into
-- organization.organization_code (e.g. SAKHA → SKH1, SKH2 …). Bulk-loaded
-- reference/demo organizations were inserted with their codes directly,
-- WITHOUT advancing id_sequence_master — so the counter can lag the highest
-- code already in use. next_id()/peek_next_id() would then mint a duplicate
-- and violate uq_organization_code.
--
-- This block advances each org-type counter to at least the largest numeric
-- suffix of an existing organization_code of that type (prefix-scoped, so
-- unrelated code formats are ignored). It is idempotent and monotonic —
-- GREATEST() never lowers a counter, so re-running is always safe and a
-- counter already ahead of the data is left untouched.
UPDATE nss.id_sequence_master s
SET current_value = GREATEST(s.current_value, COALESCE((
        SELECT MAX(
                   (regexp_replace(o.organization_code, '^' || s.prefix, ''))::int
               )
        FROM nss.organization o
        JOIN nss.master_data md
          ON md.master_data_pk = o.organization_type_master_data_pk
        WHERE md.value_code = m.type_code
          AND o.organization_code ~ ('^' || s.prefix || '[0-9]+$')
    ), 0)),
    updated_at = NOW()
FROM (VALUES
    ('ANCHALIKA_SANGHA', 'ANCHALIKA'),
    ('ZILLA_SANGHA',     'ZILLA'),
    ('SAKHA_SANGHA',     'SAKHA'),
    ('PATHA_CHAKRA',     'PATHA_CHAKRA')
) AS m(type_code, seq_code)
WHERE s.sequence_code = m.seq_code;
