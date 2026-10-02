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
-- The database is created idempotently via psql's \gexec (step 3): a
-- conditional SELECT emits the CREATE DATABASE statement only when the
-- database is absent, and \gexec runs it in the SAME authenticated psql
-- session. There is no second connection and no password anywhere in this
-- script — it inherits the superuser auth you already supplied on the psql
-- command line (or via .pgpass / PGPASSWORD).
--
-- This script creates:
--   1. Role: nss_db_owner   — owns all schema objects, executes DDL/seed
--   2. Role: nss_db_backend — runtime read/write for the application layer
--   3. Database: nss_erp    — owned by nss_db_owner (idempotent via \gexec)
--   4. Role: nss_db_writer  — Tier 5 write pool (auth + admin writes)
--   5. GRANT CONNECT on nss_erp to nss_db_backend and nss_db_writer
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
-- 1. PostgreSQL role: nss_db_owner (DDL / schema owner)
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
-- 2. PostgreSQL role: nss_db_backend (runtime)
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
-- 3. Database: nss_erp (owned by nss_db_owner)
--    Idempotent via psql \gexec — the conditional SELECT below emits the
--    CREATE DATABASE statement only when the database is absent, and \gexec
--    runs it in THIS already-authenticated psql session. No second
--    connection, no dblink, and (crucially) no password to hardcode.
--    CREATE DATABASE cannot run inside a transaction/DO block, which is why
--    it is generated at the client level and piped back with \gexec.
-- -------------------------------------------------
SELECT 'CREATE DATABASE nss_erp OWNER nss_db_owner'
WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = 'nss_erp'
)\gexec

-- -------------------------------------------------
-- 4. PostgreSQL role: nss_db_writer (Tier 5 write)
--     LOGIN, NOSUPERUSER — used by FastAPI for auth +
--     admin write operations only.
--     Password must be set separately per environment.
-- -------------------------------------------------
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_roles
        WHERE rolname = 'nss_db_writer'
    ) THEN
        CREATE ROLE nss_db_writer
            LOGIN
            NOSUPERUSER
            NOCREATEDB
            NOCREATEROLE
            NOINHERIT;
        RAISE NOTICE 'Role nss_db_writer created (LOGIN, no password — set one before use).';
    ELSE
        ALTER ROLE nss_db_writer LOGIN;
        RAISE NOTICE 'Role nss_db_writer already exists — ensured LOGIN.';
    END IF;
END
$$;

-- -------------------------------------------------
-- 5. Grant CONNECT on nss_erp to runtime roles
-- -------------------------------------------------
GRANT CONNECT ON DATABASE nss_erp TO nss_db_backend;
GRANT CONNECT ON DATABASE nss_erp TO nss_db_writer;
