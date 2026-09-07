-- =====================================================
-- NSS ERP
-- Script: 04_grant_backend.sql
-- Purpose: Grant nss_db_backend the minimum privileges
--          required by the FastAPI application layer.
--
-- Run as: nss_db_owner (or superuser)
-- Target DB: nss_erp
--
-- Tier 0: SELECT-only on all nss.* tables.
-- Later tiers will add INSERT/UPDATE as write
-- endpoints are implemented.
--
-- This script is idempotent — safe to re-run.
-- =====================================================

-- Schema access
GRANT USAGE ON SCHEMA nss TO nss_db_backend;

-- Read-only access to all existing tables
GRANT SELECT ON ALL TABLES IN SCHEMA nss TO nss_db_backend;

-- Ensure future tables in nss are also readable
ALTER DEFAULT PRIVILEGES IN SCHEMA nss
    GRANT SELECT ON TABLES TO nss_db_backend;
