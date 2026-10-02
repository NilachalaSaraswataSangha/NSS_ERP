-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 10_festival_calendar.sql
-- Version: 1.0
-- Authority: SOL-ARCH-013 (Festival Reference Calendar Architecture),
--            FC-DECISION-02
-- Owner: NSS_ERP_ADMIN
--
-- Dola Purnima dates are entered data (SOL-ARCH-013 §3 — never
-- computed). The dates below were cross-referenced against public
-- panchang/Odisha-calendar sources on 2026-10-01 and against the one
-- date already anchored in this repository (2025-03-14, from the
-- seeded membership_transfer_history remarks — confirmed match).
--
-- 2027 was initially seeded with is_confirmed = FALSE (public sources
-- disagreed between 21 and 22 March 2027). Confirmed 2026-10-01 as
-- 22 March 2027 (DD/MM/YYYY) by project decision — now TRUE below.
--
-- Years outside 2024-2028 are intentionally not seeded. Add them with
-- the same INSERT shape when needed — this is data entry, not DDL.
-- =====================================================

-- ── Festival identity ────────────────────────────────

INSERT INTO nss.festival_master
(
    festival_code,
    festival_name,
    festival_name_odia,
    lunar_basis,
    is_erp_reference_date,
    description,
    display_order
)
VALUES
(
    'DOLA_PURNIMA',
    'Dola Purnima',
    'ଦୋଳ ପୂର୍ଣ୍ଣିମା',
    'Phalguna Purnima',
    TRUE,
    'Annual reference date for the Probationary-to-Regular conversion '
    '(MBR-011A), Membership Transfer effective date (MBR-029), and the '
    'Parichaya/Anumati Patra renewal deadline and validity window '
    '(SOL-ARCH-013 FC-DECISION-01). A lunisolar festival date — '
    'observed_date is always Kendra-Sangha-confirmed data, never computed.',
    1
)
ON CONFLICT (festival_code) DO UPDATE SET
    festival_name       = EXCLUDED.festival_name,
    festival_name_odia  = EXCLUDED.festival_name_odia,
    lunar_basis          = EXCLUDED.lunar_basis,
    is_erp_reference_date = EXCLUDED.is_erp_reference_date,
    description          = EXCLUDED.description,
    display_order        = EXCLUDED.display_order;

-- ── Per-year observed dates ──────────────────────────

INSERT INTO nss.festival_calendar_date
(
    festival_master_pk, calendar_year, observed_date, is_confirmed,
    source_reference, remarks
)
SELECT fm.festival_master_pk, v.calendar_year, v.observed_date,
       v.is_confirmed, v.source_reference, v.remarks
FROM nss.festival_master fm
CROSS JOIN (VALUES
    (2024, DATE '2024-03-25', TRUE,
     'Public panchang/Odisha calendar cross-reference, seeded 2026-10-01',
     NULL),
    (2025, DATE '2025-03-14', TRUE,
     'Public panchang/Odisha calendar cross-reference, seeded 2026-10-01',
     'Matches the pre-existing anchor in membership_transfer_history '
     'seed remarks ("Dola Purnima 2025") — independently corroborated.'),
    (2026, DATE '2026-03-03', TRUE,
     'Public panchang/Odisha calendar cross-reference, seeded 2026-10-01',
     NULL),
    (2027, DATE '2027-03-22', TRUE,
     'Confirmed 2026-10-01 by project decision (resolves prior public-source '
     'disagreement between 21 and 22 March 2027).',
     NULL),
    (2028, DATE '2028-03-11', TRUE,
     'Public panchang/Odisha calendar cross-reference, seeded 2026-10-01',
     NULL)
) AS v(calendar_year, observed_date, is_confirmed, source_reference, remarks)
WHERE fm.festival_code = 'DOLA_PURNIMA'
ON CONFLICT (festival_master_pk, calendar_year) DO UPDATE SET
    observed_date     = EXCLUDED.observed_date,
    is_confirmed      = EXCLUDED.is_confirmed,
    source_reference  = EXCLUDED.source_reference,
    remarks           = EXCLUDED.remarks;
