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
-- The dblink_exec call below (step 4) opens its own connection back to this
-- server using an explicit host/port/user/password connection string (dblink
-- does NOT inherit the invoking psql session's authentication). The password
-- is hardcoded to a local-dev placeholder ('root') — change it to match your
-- actual `postgres` superuser password before running this against any
-- shared/non-local environment.
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
-- IMPORTANT: After running this script, set passwords for
-- both roles before proceeding:
--
--   ALTER ROLE nss_db_owner PASSWORD 'your_password_here';
--   ALTER ROLE nss_db_backend PASSWORD 'your_password_here';
--
-- Or use .pgpass / PGPASSWORD environment variable.
-- Never commit real passwords to the repository.
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
--    LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT.
--    Password must be set separately per environment.
-- -------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'nss_db_owner'
    ) THEN
        CREATE ROLE nss_db_owner
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
        RAISE NOTICE 'Role nss_db_owner created (LOGIN, no password — set one before use).';
    ELSE
        -- Ensure LOGIN is granted even if role existed from an older script version
        ALTER ROLE nss_db_owner LOGIN;
        RAISE NOTICE 'Role nss_db_owner already exists — ensured LOGIN.';
    END IF;
END
$$;

-- -------------------------------------------------
-- 3. PostgreSQL role: nss_db_backend (runtime)
--    LOGIN, NOSUPERUSER — used by FastAPI application.
--    Password must be set separately per environment.
-- -------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'nss_db_backend'
    ) THEN
        CREATE ROLE nss_db_backend
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
        RAISE NOTICE 'Role nss_db_backend created (LOGIN, no password — set one before use).';
    ELSE
        ALTER ROLE nss_db_backend LOGIN;
        RAISE NOTICE 'Role nss_db_backend already exists — ensured LOGIN.';
    END IF;
END
$$;

-- -------------------------------------------------
-- 4. Database: nss_erp (owned by nss_db_owner)
--    Idempotent via dblink — safe to re-run.
--    Connection string hardcoded to localhost/postgres with a
--    local-dev placeholder password — change before shared use.
-- -------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_database WHERE datname = 'nss_erp'
    ) THEN
        PERFORM dblink_exec(
            'dbname=postgres host=localhost port=5432 user=postgres password=root',
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
