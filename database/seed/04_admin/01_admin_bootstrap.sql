-- =====================================================
-- NSS ERP
-- Module: Authentication & Security
-- Seed File: 04_admin_bootstrap.sql
-- Version: 1.0
-- Authority: SOL-AUTH-006, Tier 5 decisions
-- Owner: NSS_ERP_ADMIN
--
-- Purpose:
--   Seeds the initial NSS Admin superuser account.
--   This account has NSS_ERP_ADMIN role with NSS-WIDE
--   scope — full access to all modules and organizations.
--
--   Person:        NSS Admin (person_id = P1)
--   Gender:        Other (GENDER/OTHER master_data)
--   Sangha Sevi:   SS1 (linked to Kendra org)
--                  is_system_account = TRUE (MBR-038A) —
--                  the single reserved exception permitting
--                  a non-SAKHA_SANGHA organization_pk.
--   Login:         SS1 / NSSAdmin1
--   Role:          NSS_ERP_ADMIN
--   Scope:         NSS-WIDE
--
--   *** CHANGE THE PASSWORD AFTER FIRST LOGIN ***
--
-- Dependencies (must be seeded first):
--   - 01_foundation/02_master_data.sql (STATUS/ACTIVE, MEMBERSHIP_TYPE, GENDER/OTHER)
--   - 02_organization/03_organization.sql (Kendra org)
--   - 00_bootstrap/02_role_master.sql (NSS_ERP_ADMIN role)
--   - 00_bootstrap/03_role_permission.sql (role→permission mappings)
--   - 05_membership/01_sangha_sevi.sql (is_system_account column, MBR-038A)
--   - 05_membership/14_sakha_only_membership_trigger.sql (enforcement trigger)
--
-- Idempotent: Uses ON CONFLICT or WHERE NOT EXISTS guards.
-- =====================================================

-- ── 1. Advance id_sequence_master counters ─────────────────────────────
-- Reserve P1 and SS1 for the admin account.

UPDATE nss.id_sequence_master
SET current_value = GREATEST(current_value, 1)
WHERE sequence_code = 'PERSON';

UPDATE nss.id_sequence_master
SET current_value = GREATEST(current_value, 1)
WHERE sequence_code = 'SANGHA_SEVI';


-- ── 2. Insert person ───────────────────────────────────────────────────

INSERT INTO nss.person (
    person_id,
    first_name,
    last_name,
    email,
    country_phone_code,
    mobile_number,
    gender_master_data_pk
)
SELECT
    'P1',
    'NSS',
    'Admin',
    'admin@nss.example',
    '+91',
    '0000000000',
    (
        SELECT md.master_data_pk
        FROM nss.master_data md
        JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
        WHERE mc.category_code = 'GENDER'
          AND md.value_code = 'OTHER'
          AND md.is_active = TRUE
        LIMIT 1
    )
WHERE NOT EXISTS (
    SELECT 1 FROM nss.person WHERE person_id = 'P1'
);


-- ── 3. Insert sangha_sevi ──────────────────────────────────────────────
-- Membership type: use a generic type (pick first available active type)
-- Status: ACTIVE

INSERT INTO nss.sangha_sevi (
    sangha_sevi_id,
    person_pk,
    membership_type_master_data_pk,
    membership_status_master_data_pk,
    organization_pk,
    joining_date,
    is_system_account
)
SELECT
    'SS1',
    p.person_pk,
    mt.master_data_pk,
    ms.master_data_pk,
    org.organization_pk,
    CURRENT_DATE,
    TRUE
FROM nss.person p
CROSS JOIN (
    SELECT md.master_data_pk
    FROM nss.master_data md
    JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
    WHERE mc.category_code = 'MEMBERSHIP_TYPE'
      AND md.is_active = TRUE
    ORDER BY md.display_order
    LIMIT 1
) mt
CROSS JOIN (
    SELECT md.master_data_pk
    FROM nss.master_data md
    JOIN nss.master_category mc ON mc.master_category_pk = md.master_category_pk
    WHERE mc.category_code = 'STATUS'
      AND md.value_code = 'ACTIVE'
      AND md.is_active = TRUE
    LIMIT 1
) ms
CROSS JOIN (
    SELECT o.organization_pk
    FROM nss.organization o
    WHERE o.organization_code = 'KEN'
      AND o.is_active = TRUE
    LIMIT 1
) org
WHERE p.person_id = 'P1'
  AND NOT EXISTS (
      SELECT 1 FROM nss.sangha_sevi WHERE sangha_sevi_id = 'SS1'
  );


-- ── 4. Insert user_account ─────────────────────────────────────────────
-- Password hash is supplied at runtime by the bootstrap script.
-- *** NEVER hardcode a hash here — use scripts/bootstrap_admin.py ***
-- account_status = ACTIVE (not PENDING_APPROVAL — this is a bootstrap account)

INSERT INTO nss.user_account (
    person_pk,
    password_hash,
    account_status,
    force_password_change,
    password_expires_at
)
SELECT
    p.person_pk,
    %(password_hash)s,
    'ACTIVE',
    TRUE,
    CURRENT_TIMESTAMP + INTERVAL '365 days'
FROM nss.person p
WHERE p.person_id = 'P1'
  AND NOT EXISTS (
      SELECT 1 FROM nss.user_account ua
      JOIN nss.person p2 ON p2.person_pk = ua.person_pk
      WHERE p2.person_id = 'P1'
  );


-- ── 5. Insert password_history ─────────────────────────────────────────

INSERT INTO nss.password_history (
    user_account_pk,
    password_hash,
    changed_reason
)
SELECT
    ua.user_account_pk,
    ua.password_hash,
    'INITIAL'
FROM nss.user_account ua
JOIN nss.person p ON p.person_pk = ua.person_pk
WHERE p.person_id = 'P1'
  AND NOT EXISTS (
      SELECT 1 FROM nss.password_history ph
      WHERE ph.user_account_pk = ua.user_account_pk
  );


-- ── 6. Assign NSS_ERP_ADMIN role ──────────────────────────────────────

INSERT INTO nss.user_role (
    user_account_pk,
    role_master_pk
)
SELECT
    ua.user_account_pk,
    rm.role_master_pk
FROM nss.user_account ua
JOIN nss.person p ON p.person_pk = ua.person_pk
CROSS JOIN nss.role_master rm
WHERE p.person_id = 'P1'
  AND rm.role_code = 'NSS_ERP_ADMIN'
  AND NOT EXISTS (
      SELECT 1 FROM nss.user_role ur
      WHERE ur.user_account_pk = ua.user_account_pk
        AND ur.role_master_pk = rm.role_master_pk
  );


-- ── 7. Assign NSS-WIDE scope ──────────────────────────────────────────

INSERT INTO nss.admin_scope (
    user_role_pk,
    scope_level,
    organization_pk
)
SELECT
    ur.user_role_pk,
    'NSS-WIDE',
    NULL
FROM nss.user_role ur
JOIN nss.user_account ua ON ua.user_account_pk = ur.user_account_pk
JOIN nss.person p ON p.person_pk = ua.person_pk
JOIN nss.role_master rm ON rm.role_master_pk = ur.role_master_pk
WHERE p.person_id = 'P1'
  AND rm.role_code = 'NSS_ERP_ADMIN'
  AND NOT EXISTS (
      SELECT 1 FROM nss.admin_scope asc2
      WHERE asc2.user_role_pk = ur.user_role_pk
  );
