-- =====================================================
-- NSS ERP
-- Module: Organization
-- File: 04_organization_address_restriction_trigger.sql
-- Object: nss.fn_enforce_organization_address_restriction() +
--         trigger on nss.organization
-- Depth: 2 (depends on organization, master_data)
-- Version: 1.1
-- Authority: ORG-BR-099 (governance decision, 2026-09-26;
--            narrowed 2026-09-28 — see amendment below)
-- Owner: NSS_ERP_ADMIN
--
-- Purpose:
--   ANCHALIKA_SANGHA, ZILLA_SANGHA, and PATHA_CHAKRA are purely
--   administrative/organizational units with no premises of their
--   own (ORG-BR-099) — unlike SAKHA_SANGHA, which represents a
--   physical location. This trigger makes that a real invariant
--   rather than a UI convention: any INSERT/UPDATE on
--   nss.organization that would leave one of these three types
--   with a non-NULL premises-address column is rejected.
--
-- v1.1 amendment (2026-09-28): country_pk/state_pk/district_pk
--   removed from the restriction. These three types DO correspond
--   to a real administrative jurisdiction (which state/district a
--   Zilla Sangha or Patha Chakra covers) even though they have no
--   physical premises of their own — so jurisdiction is no longer
--   conflated with a street address. Only the premises-specific
--   columns below remain prohibited.
--
-- Premises-address columns covered (per ORG-BR-099, narrowed):
--   address_line_1, address_line_2, city_village_pk, postal_code_pk,
--   latitude, longitude.
--
-- Not covered — always allowed regardless of type:
--   organization_name, organization_code, short_code, jurisdiction
--   fields (country_pk, state_pk, district_pk — v1.1), contact
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
        OR NEW.city_village_pk IS NOT NULL
        OR NEW.postal_code_pk IS NOT NULL
        OR NEW.latitude IS NOT NULL
        OR NEW.longitude IS NOT NULL
    THEN
        RAISE EXCEPTION
            'ORG-BR-099 violation: organizations of type % may never carry a physical premises address (address_line_1, address_line_2, city_village_pk, postal_code_pk, latitude, longitude must all be NULL). country_pk/state_pk/district_pk are jurisdiction, not premises, and are allowed.',
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
        city_village_pk, postal_code_pk,
        latitude, longitude
    ON nss.organization
    FOR EACH ROW
    EXECUTE FUNCTION nss.fn_enforce_organization_address_restriction();
