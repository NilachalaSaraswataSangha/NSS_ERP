-- =====================================================
-- NSS ERP
-- Module: Family
-- Seed File: 02_tier4_verification_family_links.sql
-- Version: 1.0
-- Authority: Tier 4 verification seed
-- Owner: NSS_ERP_ADMIN
-- Note: Populates nss.family_link with direct edges
--       for the Mishra family (F1).
--
--       Only two link types are used:
--         PARENT_OF — person_a is parent of person_b
--         SPOUSE_OF — bidirectional spousal link
--
--       Edges (10 total):
--         Harekrushna (P9)  PARENT_OF  Ramesh (P1)
--         Harekrushna (P9)  PARENT_OF  Rajesh (P12)
--         Saraswati   (P10) PARENT_OF  Ramesh (P1)
--         Saraswati   (P10) PARENT_OF  Rajesh (P12)
--         Harekrushna (P9)  SPOUSE_OF  Saraswati (P10)
--         Ramesh      (P1)  SPOUSE_OF  Sushma (P2)
--         Rajesh      (P12) SPOUSE_OF  Kabita (P13)
--         Ramesh      (P1)  PARENT_OF  Aniket (P3)
--         Ramesh      (P1)  PARENT_OF  Anita (P11)
--         Sushma      (P2)  PARENT_OF  Aniket (P3)
--         Sushma      (P2)  PARENT_OF  Anita (P11)
--
--       From these 11 edges, the graph engine computes
--       all kinship labels relative to any viewer.
-- =====================================================

-- Helper: resolve person_pk by person_id
-- Using subqueries to keep each INSERT self-contained.

-- ── Spouse links ────────────────────────────────────

-- Harekrushna (P9) SPOUSE_OF Saraswati (P10)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'SPOUSE_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P9'
  AND pb.person_id = 'P10';

-- Ramesh (P1) SPOUSE_OF Sushma (P2)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'SPOUSE_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P1'
  AND pb.person_id = 'P2';

-- Rajesh (P12) SPOUSE_OF Kabita (P13)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'SPOUSE_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P12'
  AND pb.person_id = 'P13';

-- ── Parent links ────────────────────────────────────

-- Harekrushna (P9) PARENT_OF Ramesh (P1)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'PARENT_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P9'
  AND pb.person_id = 'P1';

-- Harekrushna (P9) PARENT_OF Rajesh (P12)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'PARENT_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P9'
  AND pb.person_id = 'P12';

-- Saraswati (P10) PARENT_OF Ramesh (P1)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'PARENT_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P10'
  AND pb.person_id = 'P1';

-- Saraswati (P10) PARENT_OF Rajesh (P12)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'PARENT_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P10'
  AND pb.person_id = 'P12';

-- Ramesh (P1) PARENT_OF Aniket (P3)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'PARENT_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P1'
  AND pb.person_id = 'P3';

-- Ramesh (P1) PARENT_OF Anita (P11)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'PARENT_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P1'
  AND pb.person_id = 'P11';

-- Sushma (P2) PARENT_OF Aniket (P3)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'PARENT_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P2'
  AND pb.person_id = 'P3';

-- Sushma (P2) PARENT_OF Anita (P11)
INSERT INTO nss.family_link
    (family_group_pk, person_a_pk, person_b_pk, link_type, effective_from)
SELECT
    fg.family_group_pk,
    pa.person_pk,
    pb.person_pk,
    'PARENT_OF',
    '2010-04-01'
FROM nss.family_group fg
CROSS JOIN nss.person pa
CROSS JOIN nss.person pb
WHERE fg.family_id = 'F1'
  AND pa.person_id = 'P2'
  AND pb.person_id = 'P11';
