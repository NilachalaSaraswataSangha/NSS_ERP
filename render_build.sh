#!/usr/bin/env bash
# ==========================================================
# render_build.sh — Render.com build script
# ==========================================================
#
# Runs on every deploy. Installs Python dependencies, then
# bootstraps the Neon.dev PostgreSQL database (DDL + seed)
# if tables don't already exist.
#
# Database: Neon.dev (per TECH_STACK_DECISIONS.md §1)
# App host: Render.com (per TECH_STACK_DECISIONS.md §2)
#
# Required env vars (set in Render dashboard):
#   DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
# ==========================================================

set -euo pipefail

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "=== Checking database state (Neon.dev) ==="

# Neon uses standard PostgreSQL wire protocol — psql works directly.
export PGPASSWORD="${DB_PASSWORD}"
PSQL="psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -v ON_ERROR_STOP=1"

# Neon requires SSL
export PGSSLMODE="require"

# Check if the nss schema and role_master table exist.
# If they do, skip DB bootstrap (idempotent deploys).
TABLE_EXISTS=$(${PSQL} -tAc "
    SELECT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'nss' AND table_name = 'role_master'
    );
" 2>/dev/null || echo "f")

if [ "${TABLE_EXISTS}" = "t" ]; then
    echo "  Database already bootstrapped — skipping DDL/seed."
else
    echo "  Fresh database detected — running bootstrap..."
    echo ""

    # Step 1: Create nss schema + extensions
    # Neon supports pgcrypto and pg_trgm on free tier.
    # btree_gin may be available. postgis is not on free tier.
    echo "--- Creating nss schema ---"
    ${PSQL} -c "CREATE SCHEMA IF NOT EXISTS nss;"
    ${PSQL} -c "ALTER DATABASE ${DB_NAME} SET search_path TO nss, public;"
    ${PSQL} -c "SET search_path TO nss, public;"

    echo "--- Installing extensions (best-effort) ---"
    ${PSQL} -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" 2>/dev/null || echo "  pgcrypto not available — skipping"
    ${PSQL} -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>/dev/null || echo "  pg_trgm not available — skipping"
    ${PSQL} -c "CREATE EXTENSION IF NOT EXISTS btree_gin;" 2>/dev/null || echo "  btree_gin not available — skipping"

    # Step 2: Run DDL + Seed (same order as 02_build.sh)
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    DDL_BASE="${REPO_ROOT}/database/ddl"
    SEED_BASE="${REPO_ROOT}/database/seed"

    run_sql() {
        local label="$1"
        local file="$2"
        if ${PSQL} -f "${file}" > /dev/null 2>&1; then
            echo "  [OK]   ${label}"
        else
            echo "  [FAIL] ${label}"
            ${PSQL} -f "${file}" 2>&1 | head -20
            exit 1
        fi
    }

    echo ""
    echo "--- Phase 0: Bootstrap RBAC — DDL ---"
    run_sql "role_master"       "${DDL_BASE}/00_bootstrap/01_role_master.sql"
    run_sql "permission_master" "${DDL_BASE}/00_bootstrap/02_permission_master.sql"
    run_sql "role_permission"   "${DDL_BASE}/00_bootstrap/03_role_permission.sql"

    echo "--- Phase 0: Bootstrap RBAC — Seed ---"
    run_sql "permission_master (seed)" "${SEED_BASE}/00_bootstrap/01_permission_master.sql"
    run_sql "role_master (seed)"       "${SEED_BASE}/00_bootstrap/02_role_master.sql"
    run_sql "role_permission (seed)"   "${SEED_BASE}/00_bootstrap/03_role_permission.sql"

    echo ""
    echo "--- Phase 1: Foundation — DDL ---"
    run_sql "master_category"                "${DDL_BASE}/01_foundation/02_master_category.sql"
    run_sql "system_setting"                 "${DDL_BASE}/01_foundation/03_system_setting.sql"
    run_sql "id_sequence_master"             "${DDL_BASE}/01_foundation/04_id_sequence_master.sql"
    run_sql "country"                        "${DDL_BASE}/01_foundation/05_country.sql"
    run_sql "document_master"                "${DDL_BASE}/01_foundation/06_document_master.sql"
    run_sql "field_change_log"               "${DDL_BASE}/01_foundation/07_field_change_log.sql"
    run_sql "master_data"                    "${DDL_BASE}/01_foundation/08_master_data.sql"
    run_sql "state"                          "${DDL_BASE}/01_foundation/09_state.sql"
    run_sql "district"                       "${DDL_BASE}/01_foundation/10_district.sql"
    run_sql "city_village"                   "${DDL_BASE}/01_foundation/11_city_village.sql"
    run_sql "postal_code"                    "${DDL_BASE}/01_foundation/12_postal_code.sql"
    run_sql "city_village_postal_code_map"   "${DDL_BASE}/01_foundation/13_city_village_postal_code_map.sql"

    echo ""
    echo "--- Phase 2: Foundation — Seed ---"
    run_sql "master_category (seed)"    "${SEED_BASE}/01_foundation/01_master_category.sql"
    run_sql "master_data (seed)"        "${SEED_BASE}/01_foundation/02_master_data.sql"
    run_sql "id_sequence_master (seed)" "${SEED_BASE}/01_foundation/03_id_sequence_master.sql"
    run_sql "country (seed)"            "${SEED_BASE}/01_foundation/04_country.sql"
    run_sql "state (seed)"              "${SEED_BASE}/01_foundation/05_state.sql"
    run_sql "district (seed)"           "${SEED_BASE}/01_foundation/06_district.sql"
    run_sql "system_setting (seed)"     "${SEED_BASE}/01_foundation/07_system_setting.sql"
    run_sql "postal_code (seed)"        "${SEED_BASE}/01_foundation/08_postal_code.sql"

    echo ""
    echo "--- Phase 3: Organization — DDL ---"
    run_sql "organization_type_master"   "${DDL_BASE}/02_organization/01_organization_type_master.sql"
    run_sql "organization_status_master" "${DDL_BASE}/02_organization/02_organization_status_master.sql"
    run_sql "organization"               "${DDL_BASE}/02_organization/03_organization.sql"

    echo ""
    echo "--- Phase 4: Organization — Seed ---"
    run_sql "organization_type_master (seed)"   "${SEED_BASE}/02_organization/01_organization_type_master.sql"
    run_sql "organization_status_master (seed)" "${SEED_BASE}/02_organization/02_organization_status_master.sql"
    run_sql "organization (seed)"               "${SEED_BASE}/02_organization/03_organization.sql"

    echo ""
    echo "=== Database bootstrap complete (Neon.dev) ==="
fi

echo ""
echo "=== Build finished ==="
