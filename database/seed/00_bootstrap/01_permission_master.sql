-- =====================================================
-- NSS ERP
-- Module: Bootstrap RBAC
-- File: 01_permission_master.sql (seed)
-- Seed: 20 frozen permissions (Tier 5 decision 2026-09-15)
-- Version: 1.0
-- Authority: SOL-ARCH-011 §4, SOL-ADMIN-004 §9.5,
--            SOL-BOOT-001 §5
--
-- PERMISSION CODE CONVENTION: <MODULE>_<ACTION>
--   MODULE = BOOTSTRAP | FOUNDATION | ORGANIZATION |
--            PERSON | FAMILY | MEMBERSHIP | ADMIN |
--            AUDIT | REPORT
--   ACTION = VIEW | MANAGE | VIEW_SENSITIVE | APPROVE |
--            USER_VIEW | USER_MANAGE | ROLE_MANAGE |
--            SCOPE_MANAGE | PERMISSION_VIEW
--
-- Granularity: Option B hybrid — VIEW + MANAGE per
--   module, with finer-grained splits where business
--   requires (Person sensitive, Membership approve,
--   Administration sub-actions).
--
-- Future tiers add permissions progressively using the
-- same <MODULE>_<ACTION> pattern.
-- =====================================================

INSERT INTO nss.permission_master
    (permission_code, permission_name, module_code, description, display_order)
VALUES
    -- ── Bootstrap ───────────────────────────────────────
    ('BOOTSTRAP_VIEW',
     'View Bootstrap Data',
     'BOOTSTRAP',
     'Read-only access to bootstrap RBAC tables (roles, permissions, role-permission mappings)',
     1),

    -- ── Foundation ──────────────────────────────────────
    ('FOUNDATION_VIEW',
     'View Foundation Data',
     'FOUNDATION',
     'Read-only access to foundation master data, system settings, locations, documents',
     2),

    ('FOUNDATION_MANAGE',
     'Manage Foundation Data',
     'FOUNDATION',
     'Create, edit, and deactivate foundation master data and system settings. ADMIN + KENDRA only.',
     3),

    -- ── Organization ────────────────────────────────────
    ('ORGANIZATION_VIEW',
     'View Organizations',
     'ORGANIZATION',
     'Read-only access to organization records, hierarchy, and statistics',
     4),

    ('ORGANIZATION_MANAGE',
     'Manage Organizations',
     'ORGANIZATION',
     'Create, edit, and deactivate organization records. ADMIN + KENDRA only.',
     5),

    -- ── Person ──────────────────────────────────────────
    ('PERSON_VIEW',
     'View Person Records',
     'PERSON',
     'Read-only access to person records (excluding sensitive fields)',
     6),

    ('PERSON_MANAGE',
     'Manage Person Records',
     'PERSON',
     'Create, edit, and deactivate person records',
     7),

    ('PERSON_VIEW_SENSITIVE',
     'View Sensitive Person Data',
     'PERSON',
     'Access to Aadhaar and other sensitive identity fields. ADMIN + KENDRA + AUDITOR only.',
     8),

    -- ── Family ──────────────────────────────────────────
    ('FAMILY_VIEW',
     'View Family Groups',
     'FAMILY',
     'Read-only access to family groups, members, and relationships',
     9),

    ('FAMILY_MANAGE',
     'Manage Family Groups',
     'FAMILY',
     'Create, edit, and deactivate family groups and member assignments',
     10),

    -- ── Membership ──────────────────────────────────────
    ('MEMBERSHIP_VIEW',
     'View Membership Records',
     'MEMBERSHIP',
     'Read-only access to membership, affiliations, credentials, journey events',
     11),

    ('MEMBERSHIP_MANAGE',
     'Manage Membership Records',
     'MEMBERSHIP',
     'Create, edit, and deactivate membership records, affiliations, credentials',
     12),

    ('MEMBERSHIP_APPROVE',
     'Approve Membership Actions',
     'MEMBERSHIP',
     'Approve new enrolments, renewals, and membership transitions within scope. All unit-level admin roles.',
     13),

    -- ── Administration ──────────────────────────────────
    ('ADMIN_USER_VIEW',
     'View User Accounts',
     'ADMIN',
     'Read-only access to user account records. ADMIN + KENDRA + AUDITOR.',
     14),

    ('ADMIN_USER_MANAGE',
     'Manage User Accounts',
     'ADMIN',
     'Create, edit, deactivate, lock, unlock user accounts. Reset passwords. ADMIN + KENDRA only.',
     15),

    ('ADMIN_ROLE_MANAGE',
     'Manage Role Assignments',
     'ADMIN',
     'Assign and revoke roles to/from user accounts. ADMIN + KENDRA only.',
     16),

    ('ADMIN_SCOPE_MANAGE',
     'Manage Scope Assignments',
     'ADMIN',
     'Assign and modify organizational scope for user-role assignments. ADMIN + KENDRA only.',
     17),

    ('ADMIN_PERMISSION_VIEW',
     'View Permission Configuration',
     'ADMIN',
     'Read-only access to permission catalogue and role-permission mappings. ADMIN + KENDRA + AUDITOR.',
     18),

    -- ── Audit ───────────────────────────────────────────
    ('AUDIT_VIEW',
     'View Audit Logs',
     'AUDIT',
     'Read-only access to field change logs and audit trail. ADMIN + KENDRA + AUDITOR.',
     19),

    -- ── Reports ─────────────────────────────────────────
    ('REPORT_VIEW',
     'View Reports',
     'REPORT',
     'Read-only access to reports and dashboards',
     20)

ON CONFLICT (permission_code) DO UPDATE SET
    permission_name = EXCLUDED.permission_name,
    module_code     = EXCLUDED.module_code,
    description     = EXCLUDED.description,
    display_order   = EXCLUDED.display_order;
