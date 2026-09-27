-- =====================================================
-- NSS ERP
-- Script: 05_create_writer_role.sql
-- Purpose: Grant nss_db_writer privileges for all
--          Tier 5 write operations across modules.
--
-- Run as: nss_db_owner (schema owner)
-- Target DB: nss_erp
--
-- Prerequisite: nss_db_writer role must already exist
-- (created by 00_create_database.sql as superuser).
--
-- Grants schema USAGE, SELECT on all tables, and
-- INSERT/UPDATE on all current + future tables in the
-- nss schema. No DELETE (soft-delete only), no TRUNCATE,
-- no REFERENCES, no TRIGGER.
--
-- This script is idempotent — safe to re-run.
-- =====================================================

-- -------------------------------------------------
-- 1. Schema access
-- -------------------------------------------------
GRANT USAGE ON SCHEMA nss TO nss_db_writer;

-- -------------------------------------------------
-- 2. Read access on all tables (current + future)
-- -------------------------------------------------
GRANT SELECT ON ALL TABLES IN SCHEMA nss TO nss_db_writer;

ALTER DEFAULT PRIVILEGES IN SCHEMA nss
    GRANT SELECT ON TABLES TO nss_db_writer;

-- -------------------------------------------------
-- 3. Write access on all tables (current + future)
--    INSERT + UPDATE only — no DELETE (soft-delete
--    pattern uses UPDATE to set is_current=FALSE).
-- -------------------------------------------------
GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA nss TO nss_db_writer;

ALTER DEFAULT PRIVILEGES IN SCHEMA nss
    GRANT INSERT, UPDATE ON TABLES TO nss_db_writer;

-- -------------------------------------------------
-- NOTE: nss_db_writer intentionally does NOT have:
--   - DELETE on any table (soft-delete only)
--   - TRUNCATE, REFERENCES, TRIGGER privileges
--   - DDL privileges (CREATE, ALTER, DROP)
-- -------------------------------------------------
