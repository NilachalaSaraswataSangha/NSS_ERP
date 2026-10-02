-- =====================================================
-- NSS ERP
-- Module: Foundation
-- File: 11_city_village.sql
-- Table: city_village
-- Depth: 3 (depends on district, postal_code)
-- Sequence: #32 of 87
-- Version: 2.0 — SOL-ARCH-010 Amendment (2026-10-01):
--          simplified geographic FK model for all-India scale.
--          district_pk is now OPTIONAL (best-effort name match;
--          India's census/post romanizations drift at the
--          district level, so an unresolved district should
--          not block a locality from being loaded). A direct
--          nullable postal_code_pk FK is added as the primary
--          location anchor (village → PIN → state), replacing
--          the city_village_postal_code_map M:N junction, which
--          is retired (see 13_city_village_postal_code_map.sql).
--          Villages are 1:1 with PIN; the junction only ever
--          earned its keep for a handful of multi-PIN urban
--          localities, which now simply store one representative
--          PIN (same HO>PO>BO dedup rule used for postal_code).
-- Authority: SOL-ARCH-010, SOL-ARCH-010 Amendment (2026-10-01),
--            SOL-FND-004 §16
-- Owner: NSS_ERP_ADMIN
-- =====================================================

CREATE TABLE IF NOT EXISTS nss.city_village
(
    city_village_pk UUID PRIMARY KEY
        DEFAULT gen_random_uuid(),

    district_pk UUID NULL,

    postal_code_pk UUID NULL,

    city_village_code VARCHAR(20) NOT NULL,

    city_village_name VARCHAR(150) NOT NULL,

    city_village_type VARCHAR(20) NOT NULL,

    display_order INTEGER NOT NULL
        DEFAULT 0,

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NULL,

    deleted_at TIMESTAMPTZ NULL,

    is_active BOOLEAN NOT NULL
        DEFAULT TRUE,

    CONSTRAINT fk_city_village_district
        FOREIGN KEY (district_pk)
        REFERENCES nss.district (district_pk),

    CONSTRAINT fk_city_village_postal_code
        FOREIGN KEY (postal_code_pk)
        REFERENCES nss.postal_code (postal_code_pk),

    CONSTRAINT uq_city_village_district_code
        UNIQUE (district_pk, city_village_code),

    CONSTRAINT uq_city_village_district_name
        UNIQUE (district_pk, city_village_name),

    CONSTRAINT uq_city_village_postal_code_name
        UNIQUE (postal_code_pk, city_village_name),

    CONSTRAINT chk_city_village_type
        CHECK
        (
            city_village_type IN
            (
                'CITY',
                'TOWN',
                'VILLAGE'
            )
        ),

    CONSTRAINT chk_city_village_soft_delete
        CHECK
        (
            (is_active = TRUE AND deleted_at IS NULL)
            OR
            (is_active = FALSE AND deleted_at IS NOT NULL)
        )
);

CREATE INDEX IF NOT EXISTS idx_city_village_district
    ON nss.city_village (district_pk);

CREATE INDEX IF NOT EXISTS idx_city_village_postal_code
    ON nss.city_village (postal_code_pk);

CREATE INDEX IF NOT EXISTS idx_city_village_active
    ON nss.city_village (is_active);

CREATE INDEX IF NOT EXISTS idx_city_village_name
    ON nss.city_village USING gin (city_village_name gin_trgm_ops);
