-- =====================================================
-- NSS ERP
-- Script: 00_create_database.sql
-- Purpose: Create database and PostgreSQL technical roles
-- Authority: SOL-ARCH-011 §7.2
-- Version: 2.0
-- =====================================================
--
-- Run ONCE as a PostgreSQL SUPERUSER (e.g. postgres)
-- against the postgres database:
--
--   psql -U postgres -d postgres -f database/scripts/00_create_database.sql
--
-- This script creates:
--   1. Extension: dblink (in postgres DB, for idempotent DB creation)
--   2. Role: nss_db_owner   — owns all schema objects, executes DDL/seed
--   3. Role: nss_db_backend — runtime read/write for the application layer
--   4. Database: nss_erp    — owned by nss_db_owner (idempotent via dblink)
--   5. GRANT CONNECT on nss_erp to nss_db_backend
--
-- NAMING CONVENTION (SOL-ARCH-011 §7.2):
--   nss_db_*    = PostgreSQL infrastructure roles (lowercase)
--   NSS_ERP_*   = Application RBAC roles (UPPERCASE, stored in role_master)
--
--   PostgreSQL role "nss_db_owner" is the DATABASE-LEVEL DDL owner.
--   ERP role "NSS_ERP_ADMIN" is an APPLICATION-LEVEL RBAC role
--   (a row in role_master, enforced by the application layer).
--   These are separate security boundaries.
--
-- This script is fully idempotent — safe to re-run.
-- It does NOT drop any existing objects.
--
-- No credentials are stored here; set passwords externally
-- via ALTER ROLE or .pgpass / environment variables.
--
-- nss_db_owner is intentionally NOT a SUPERUSER. It owns the
-- NSS ERP database/schema objects without PostgreSQL-wide
-- superuser privileges.
--
-- After running this script, run:
--   psql -U postgres -d nss_erp -f database/scripts/01_extensions.sql
-- to install application extensions (pgcrypto, pg_trgm, btree_gin, postgis)
-- and create the nss schema.
-- =====================================================

-- -------------------------------------------------
-- 1. Extension: dblink (in postgres DB)
--    Required for idempotent CREATE DATABASE below.
-- -------------------------------------------------
CREATE EXTENSION IF NOT EXISTS dblink;

-- -------------------------------------------------
-- 2. PostgreSQL role: nss_db_owner (DDL / schema owner)
--    NOLOGIN — grant LOGIN separately per environment.
--    NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT.
-- -------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'nss_db_owner'
    ) THEN
        CREATE ROLE nss_db_owner
            NOLOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
        RAISE NOTICE 'Role nss_db_owner created.';
    ELSE
        RAISE NOTICE 'Role nss_db_owner already exists — skipping.';
    END IF;
END
$$;

-- -------------------------------------------------
-- 3. PostgreSQL role: nss_db_backend (runtime)
--    NOLOGIN — grant LOGIN separately per environment.
-- -------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'nss_db_backend'
    ) THEN
        CREATE ROLE nss_db_backend
            NOLOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
        RAISE NOTICE 'Role nss_db_backend created.';
    ELSE
        RAISE NOTICE 'Role nss_db_backend already exists — skipping.';
    END IF;
END
$$;

-- -------------------------------------------------
-- 4. Database: nss_erp (owned by nss_db_owner)
--    Idempotent via dblink — safe to re-run.
-- -------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_database WHERE datname = 'nss_erp'
    ) THEN
        PERFORM dblink_exec(
            'dbname=postgres',
            'CREATE DATABASE nss_erp OWNER nss_db_owner'
        );
        RAISE NOTICE 'Database nss_erp created.';
    ELSE
        RAISE NOTICE 'Database nss_erp already exists — skipping.';
    END IF;
END
$$;

-- -------------------------------------------------
-- 5. Grant nss_db_backend CONNECT on nss_erp
-- -------------------------------------------------
-- Additional table-level GRANTs for nss_db_backend will be
-- added when the API layer is implemented.
-- -------------------------------------------------
GRANT CONNECT ON DATABASE nss_erp TO nss_db_backend;
