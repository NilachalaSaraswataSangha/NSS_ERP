-- =====================================================
-- NSS ERP
-- Module: Organization
-- Seed File: 06_id_sequence_org_sync.sql
-- Version: 1.0
-- Authority: SOL-FND-004 §11, ORG-BR-105
-- Owner: NSS_ERP_ADMIN
-- =====================================================
-- Counter sync for organization-code sequences (ORG-BR-105).
--
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
--
-- Must run AFTER Organization DDL (Phase 3) and Organization seed, incl.
-- Sakha branches (Phase 4) — it was previously the tail end of Foundation's
-- 01_foundation/03_id_sequence_master.sql (Phase 2), which failed on a
-- clean build because nss.organization didn't exist yet at that point.

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
