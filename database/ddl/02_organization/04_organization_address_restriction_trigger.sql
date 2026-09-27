-- =====================================================
-- NSS ERP
-- Module: Organization
-- File: 04_organization_address_restriction_trigger.sql
-- Object: nss.fn_enforce_organization_address_restriction() +
--         trigger on nss.organization
-- Depth: 2 (depends on organization, master_data)
-- Version: 1.0
-- Authority: ORG-BR-099 (governance decision, 2026-09-26)
-- Owner: NSS_ERP_ADMIN
--
-- Purpose:
--   ANCHALIKA_SANGHA, ZILLA_SANGHA, and PATHA_CHAKRA are purely
--   administrative/organizational units with no premises of their
--   own (ORG-BR-099) — unlike SAKHA_SANGHA, which represents a
--   physical location. This trigger makes that a real invariant
--   rather than a UI convention: any INSERT/UPDATE on
--   nss.organization that would leave one of these three types
--   with a non-NULL address-bearing column is rejected.
--
-- Address-bearing columns covered (per ORG-BR-099):
--   address_line_1, address_line_2, district_pk, state_pk,
--   country_pk, city_village_pk, postal_code_pk, latitude,
--   longitude.
--
-- Not covered — always allowed regardless of type:
--   organization_name, organization_code, short_code, contact
--   fields (phone/mobile/email/website/youtube), and
--   has_own_premises (ORG-BR-098, meaningless outside
--   SAKHA_SANGHA but not address data).
--
-- No migration/fix script: this ships as DDL, re-runnable via
-- the standard build (DROP ... IF EXISTS makes it idempotent).
-- =====================================================

CREATE OR REPLACE FUNCTION nss.fn_enforce_organization_address_restriction()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_org_type_code VARCHAR(50);
BEGIN
    SELECT md.value_code INTO v_org_type_code
    FROM nss.master_data md
    WHERE md.master_data_pk = NEW.organization_type_master_data_pk;

    IF v_org_type_code NOT IN ('ANCHALIKA_SANGHA', 'ZILLA_SANGHA', 'PATHA_CHAKRA') THEN
        RETURN NEW;
    END IF;

    IF NEW.address_line_1 IS NOT NULL
        OR NEW.address_line_2 IS NOT NULL
        OR NEW.district_pk IS NOT NULL
        OR NEW.state_pk IS NOT NULL
        OR NEW.country_pk IS NOT NULL
        OR NEW.city_village_pk IS NOT NULL
        OR NEW.postal_code_pk IS NOT NULL
        OR NEW.latitude IS NOT NULL
        OR NEW.longitude IS NOT NULL
    THEN
        RAISE EXCEPTION
            'ORG-BR-099 violation: organizations of type % may never carry a physical address (address_line_1, address_line_2, district_pk, state_pk, country_pk, city_village_pk, postal_code_pk, latitude, longitude must all be NULL).',
            v_org_type_code
            USING ERRCODE = 'check_violation';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_enforce_organization_address_restriction
    ON nss.organization;

CREATE TRIGGER trg_enforce_organization_address_restriction
    BEFORE INSERT OR UPDATE OF
        organization_type_master_data_pk,
        address_line_1, address_line_2,
        district_pk, state_pk, country_pk, city_village_pk, postal_code_pk,
        latitude, longitude
    ON nss.organization
    FOR EACH ROW
    EXECUTE FUNCTION nss.fn_enforce_organization_address_restriction();
