-- =====================================================
-- NSS ERP
-- Module: Bootstrap RBAC
-- File: 02_role_master.sql (seed)
-- Seed: 8 frozen roles (SOL-ADMIN-004 §8.7)
-- Authority: SOL-ARCH-011 §4, SOL-ADMIN-004 §8.7
--
-- NAMING CONVENTION:
--   NSS_ERP_*  = Application RBAC roles (this file)
--   nss_db_*   = PostgreSQL infrastructure roles (00_create_database.sql)
-- =====================================================

INSERT INTO nss.role_master
    (role_code, role_name, role_class, scope_level, description, display_order)
VALUES
    ('NSS_ERP_ADMIN',
     'NSS ERP Administrator',
     'SYSTEM',
     'NSS-WIDE',
     'System-wide ERP administrator with all application permissions',
     1),

    ('NSS_ERP_AUDITOR',
     'Auditor',
     'SYSTEM',
     'NSS-WIDE',
     'System-wide read-only auditor for compliance and review',
     2),

    ('NSS_ERP_REPORT_VIEWER',
     'Report Viewer',
     'SYSTEM',
     'NSS-WIDE',
     'System-wide read-only access to reports and dashboards',
     3),

    ('NSS_ERP_KENDRA_ADMIN',
     'Kendra Administrator',
     'ORGANIZATIONAL',
     'KENDRA',
     'Administrative authority scoped to a specific Kendra',
     4),

    ('NSS_ERP_ANCHALIKA_ADMIN',
     'Anchalika Administrator',
     'ORGANIZATIONAL',
     'ANCHALIKA',
     'Administrative authority scoped to a specific Anchalika',
     5),

    ('NSS_ERP_ZILLA_ADMIN',
     'Zilla Administrator',
     'ORGANIZATIONAL',
     'ZILLA',
     'Administrative authority scoped to a specific Zilla',
     6),

    ('NSS_ERP_SAKHA_ADMIN',
     'Sakha Administrator',
     'ORGANIZATIONAL',
     'SAKHA',
     'Administrative authority scoped to a specific Sakha',
     7),

    ('NSS_ERP_PATHA_CHAKRA_ADMIN',
     'Patha Chakra Administrator',
     'ORGANIZATIONAL',
     'PATHA_CHAKRA',
     'Administrative authority scoped to a specific Patha Chakra',
     8);
