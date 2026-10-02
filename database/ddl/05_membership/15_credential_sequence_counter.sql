-- =====================================================
-- NSS ERP
-- Module: Membership
-- File: 15_credential_sequence_counter.sql
-- Table: nss.credential_sequence_counter
-- Depth: 3 (depends on organization)
-- Version: 1.0
-- Authority: MBR-010, MBR-014, MBR-019A/B, MBR-030A
-- Owner: NSS_ERP_ADMIN
-- Note: Backs api/helpers.py::next_credential_document_number(), which
--       mints parichaya_patra.document_number / anumati_patra.document_number
--       ("Kendra Number") in the <seq>/<fy_start>/<fy_end> format (MBR-030A,
--       e.g. "345/2026/2027"). Unlike id_sequence_master (one flat,
--       never-reset counter per business ID), this counter is scoped by
--       BOTH credential type and financial year, and resets to 1 every
--       1 April:
--         PARICHAYA_PATRA — one Kendra-wide counter (scope_organization_pk
--           is always the single KENDRA org) — the Kendra Sangha issues
--           every Parichaya Patra / Kendra Number itself.
--         ANUMATI_PATRA   — one counter PER SAKHA (scope_organization_pk =
--           that Sakha's organization_pk) — each Sakha issues its own
--           Anumati Patra numbers.
--       Rows are created on demand (upsert), not pre-seeded — there is no
--       fixed list of (credential_type, org, FY) combinations to seed.
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.credential_sequence_counter
(
    credential_sequence_counter_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    -- PARICHAYA_PATRA (Kendra-wide) or ANUMATI_PATRA (per-Sakha)
    credential_type VARCHAR(20) NOT NULL,

    -- Kendra's own organization_pk for PARICHAYA_PATRA rows;
    -- the issuing Sakha's organization_pk for ANUMATI_PATRA rows.
    scope_organization_pk UUID NOT NULL,

    -- Start year of the financial year this counter covers
    -- (e.g. 2026 for FY 2026-2027, which runs 1 Apr 2026 - 31 Mar 2027).
    financial_year_start INTEGER NOT NULL,

    current_value INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    CONSTRAINT chk_credential_sequence_type
        CHECK (credential_type IN ('PARICHAYA_PATRA', 'ANUMATI_PATRA')),

    CONSTRAINT chk_credential_sequence_fy
        CHECK (financial_year_start >= 2000),

    CONSTRAINT fk_credential_sequence_org
        FOREIGN KEY (scope_organization_pk)
        REFERENCES nss.organization (organization_pk),

    CONSTRAINT uq_credential_sequence_scope
        UNIQUE (credential_type, scope_organization_pk, financial_year_start)
);

CREATE INDEX IF NOT EXISTS idx_credential_sequence_scope
    ON nss.credential_sequence_counter (scope_organization_pk);
