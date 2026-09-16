#!/usr/bin/env bash
# =====================================================
# NSS ERP — Full Database Build
# =====================================================
#
# Executes all DDL and seed scripts in the frozen
# SOL-ARCH-011 phase order for currently implemented
# modules only.
#
# Authority: SOL-ARCH-010 (DDL Creation Order),
#            SOL-ARCH-011 (Bootstrap Architecture)
# Version: 2.1  — idempotent re-run (SKIP on "already exists")
#
# Usage:
#   ./database/scripts/02_build.sh [DB_NAME] [DB_USER] [DB_HOST] [DB_PORT]
#
# Defaults:
#   DB_NAME  = nss_erp
#   DB_USER  = nss_db_owner
#   DB_HOST  = localhost
#   DB_PORT  = 5432
#
# Prerequisites:
#   - PostgreSQL running and accessible
#   - Database and roles created (see 00_create_database.sql)
#   - Extensions installed (see 01_extensions.sql)
#   - Run from the repository root directory
#
# Implemented phases:
#   Phase 0  — Bootstrap RBAC (3 tables + seed)
#   Phase 1  — Foundation DDL (12 tables)
#   Phase 2  — Foundation seed data (incl. ORGANIZATION_TYPE
#              category and unified STATUS category in master_data)
#   Phase 3  — Organization DDL (1 table)
#   Phase 4  — Organization seed data
#   Phase 5  — Person DDL (2 tables)
#   Phase 6  — Family DDL (5 tables)
#   Phase 7  — Membership DDL (12 tables)
#   Phase 8  — Tier 4 Verification Seed Data
#   Phase 8b — Performance Indexes (migrations)
#   Phase 9  — Grant nss_db_backend read-only access
#
# NOT executed:
#   - database/ddl/03_person/01_person_master_tables.sql (superseded)
#   - database/seed/03_person/ (superseded — data in Foundation seed)
#   - Pass 2 audit-actor FK constraints (deferred)
# =====================================================

set -euo pipefail

DB_NAME="${1:-nss_erp}"
DB_USER="${2:-nss_db_owner}"
DB_HOST="${3:-localhost}"
DB_PORT="${4:-5432}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DDL_BASE="${REPO_ROOT}/database/ddl"
SEED_BASE="${REPO_ROOT}/database/seed"

# Prompt for password once; export so all psql calls reuse it.
if [ -z "${PGPASSWORD:-}" ]; then
    read -rsp "Password for ${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}: " PGPASSWORD
    echo ""
    export PGPASSWORD
fi

PSQL="psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -v ON_ERROR_STOP=1"

# -- colours -----------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

total=0
failed=0
skipped=0

run_sql() {
    local label="$1"
    local file="$2"
    local output
    total=$((total + 1))
    if output=$(${PSQL} -f "${file}" 2>&1); then
        echo -e "  ${GREEN}[OK]${NC}   ${label}"
    else
        # Check for idempotent-safe errors (table/index already exists,
        # duplicate seed rows).  These are expected on re-runs and should
        # not abort the build.
        if echo "${output}" | grep -qiE 'already exists|duplicate key value violates unique constraint'; then
            echo -e "  ${YELLOW}[SKIP]${NC} ${label}  (already exists)"
            skipped=$((skipped + 1))
        else
            echo -e "  ${RED}[FAIL]${NC} ${label}"
            echo -e "  ${RED}Error:${NC}"
            echo "${output}" | sed 's/^/         /'
            failed=$((failed + 1))
            echo -e "  ${RED}Aborting — fix the above error before continuing.${NC}"
            exit 1
        fi
    fi
}

echo ""
echo -e "${CYAN}=============================================${NC}"
echo -e "${CYAN}  NSS ERP — Full Database Build${NC}"
echo -e "${CYAN}=============================================${NC}"
echo "  Database: ${DB_NAME}"
echo "  User:     ${DB_USER}"
echo "  Host:     ${DB_HOST}:${DB_PORT}"
echo -e "${CYAN}=============================================${NC}"
echo ""

# -------------------------------------------------
# Phase 0: Bootstrap RBAC (SOL-ARCH-011 §4)
# -------------------------------------------------
echo -e "${CYAN}[Phase 0] Bootstrap RBAC — DDL${NC}"
run_sql "role_master"       "${DDL_BASE}/00_bootstrap/01_role_master.sql"
run_sql "permission_master" "${DDL_BASE}/00_bootstrap/02_permission_master.sql"
run_sql "role_permission"   "${DDL_BASE}/00_bootstrap/03_role_permission.sql"
echo ""

echo -e "${CYAN}[Phase 0] Bootstrap RBAC — Seed${NC}"
run_sql "permission_master (seed)" "${SEED_BASE}/00_bootstrap/01_permission_master.sql"
run_sql "role_master (seed)"       "${SEED_BASE}/00_bootstrap/02_role_master.sql"
run_sql "role_permission (seed)"   "${SEED_BASE}/00_bootstrap/03_role_permission.sql"
echo ""

# -------------------------------------------------
# Phase 1: Foundation DDL (12 tables, Depths 0–4)
# -------------------------------------------------
echo -e "${CYAN}[Phase 1] Foundation — DDL (12 tables)${NC}"
FOUNDATION_DDL=(
    "master_category|02_master_category.sql"
    "system_setting|03_system_setting.sql"
    "id_sequence_master|04_id_sequence_master.sql"
    "country|05_country.sql"
    "document_master|06_document_master.sql"
    "field_change_log|07_field_change_log.sql"
    "master_data|08_master_data.sql"
    "state|09_state.sql"
    "district|10_district.sql"
    "city_village|11_city_village.sql"
    "postal_code|12_postal_code.sql"
    "city_village_postal_code_map|13_city_village_postal_code_map.sql"
)
for entry in "${FOUNDATION_DDL[@]}"; do
    label="${entry%%|*}"
    file="${entry##*|}"
    run_sql "${label}" "${DDL_BASE}/01_foundation/${file}"
done
echo ""

# -------------------------------------------------
# Phase 2: Foundation Seed Data
# (includes ORGANIZATION_TYPE + unified STATUS
#  categories and values in master_data)
# -------------------------------------------------
echo -e "${CYAN}[Phase 2] Foundation — Seed Data${NC}"
FOUNDATION_SEED=(
    "master_category (seed)|01_master_category.sql"
    "master_data (seed)|02_master_data.sql"
    "id_sequence_master (seed)|03_id_sequence_master.sql"
    "country (seed)|04_country.sql"
    "state (seed)|05_state.sql"
    "district (seed)|06_district.sql"
    "system_setting (seed)|07_system_setting.sql"
    "postal_code (seed)|08_postal_code.sql"
)
for entry in "${FOUNDATION_SEED[@]}"; do
    label="${entry%%|*}"
    file="${entry##*|}"
    run_sql "${label}" "${SEED_BASE}/01_foundation/${file}"
done
echo ""

# -------------------------------------------------
# Phase 3: Organization DDL (1 table, Depth 1)
# Note: organization_type_master and
#       organization_status_master are retired —
#       type/status now use Foundation master_data.
# -------------------------------------------------
echo -e "${CYAN}[Phase 3] Organization — DDL (1 table)${NC}"
run_sql "organization"               "${DDL_BASE}/02_organization/03_organization.sql"
echo ""

# -------------------------------------------------
# Phase 4: Organization Seed Data
# -------------------------------------------------
echo -e "${CYAN}[Phase 4] Organization — Seed Data${NC}"
run_sql "organization (seed)"               "${SEED_BASE}/02_organization/03_organization.sql"
echo ""

# -------------------------------------------------
# Phase 5: Person DDL (2 tables, Depths 2–3)
# Note: 01_person_master_tables.sql is SUPERSEDED —
#       gender/marital_status/address_type data is now
#       in Foundation master_data seed.
# -------------------------------------------------
echo -e "${CYAN}[Phase 5] Person — DDL (2 tables)${NC}"
run_sql "person"         "${DDL_BASE}/03_person/02_person.sql"
run_sql "person_address" "${DDL_BASE}/03_person/03_person_address.sql"
echo ""

# -------------------------------------------------
# Phase 6: Family DDL (5 tables, Depths 2–3)
# Note: family_link stores only direct PARENT_OF/
#       SPOUSE_OF edges; every other relationship
#       label is computed dynamically (BFS traversal
#       in api/services/family_graph.py), not stored.
# -------------------------------------------------
echo -e "${CYAN}[Phase 6] Family — DDL (5 tables)${NC}"
run_sql "family_group"              "${DDL_BASE}/04_family/01_family_group.sql"
run_sql "family_relationship"       "${DDL_BASE}/04_family/02_family_relationship.sql"
run_sql "family_head_history"       "${DDL_BASE}/04_family/03_family_head_history.sql"
run_sql "family_transition_history" "${DDL_BASE}/04_family/04_family_transition_history.sql"
run_sql "family_link"               "${DDL_BASE}/04_family/05_family_link.sql"
echo ""

# -------------------------------------------------
# Phase 7: Membership DDL (12 tables, Depths 2–4)
# Note: sangha_sevi must be created first — all
#       other membership tables depend on it.
# -------------------------------------------------
echo -e "${CYAN}[Phase 7] Membership — DDL (12 tables)${NC}"
run_sql "sangha_sevi"                    "${DDL_BASE}/05_membership/01_sangha_sevi.sql"
run_sql "membership_status_history"      "${DDL_BASE}/05_membership/02_membership_status_history.sql"
run_sql "membership_renewal_request"     "${DDL_BASE}/05_membership/03_membership_renewal_request.sql"
run_sql "membership_renewal_history"     "${DDL_BASE}/05_membership/04_membership_renewal_history.sql"
run_sql "membership_transfer_history"    "${DDL_BASE}/05_membership/05_membership_transfer_history.sql"
run_sql "membership_sakha_affiliation"   "${DDL_BASE}/05_membership/06_membership_sakha_affiliation.sql"
run_sql "membership_journey_event"       "${DDL_BASE}/05_membership/07_membership_journey_event.sql"
run_sql "probationary_member_review"     "${DDL_BASE}/05_membership/08_probationary_member_review.sql"
run_sql "parichaya_patra"                "${DDL_BASE}/05_membership/09_parichaya_patra.sql"
run_sql "parichaya_patra_history"        "${DDL_BASE}/05_membership/10_parichaya_patra_history.sql"
run_sql "anumati_patra"                  "${DDL_BASE}/05_membership/11_anumati_patra.sql"
run_sql "anumati_patra_history"          "${DDL_BASE}/05_membership/12_anumati_patra_history.sql"
echo ""

# -------------------------------------------------
# Phase 8: Tier 4 Verification Seed Data
# Order: Organization → Person → Family → Membership
# (dependency chain respected)
# -------------------------------------------------
echo -e "${CYAN}[Phase 8] Tier 4 Verification — Seed Data${NC}"
run_sql "tier4 organizations (seed)"    "${SEED_BASE}/02_organization/04_tier4_verification_orgs.sql"
run_sql "tier4 persons (seed)"          "${SEED_BASE}/03_person/02_tier4_verification_persons.sql"
run_sql "tier4 family (seed)"           "${SEED_BASE}/04_family/01_tier4_verification_family.sql"
run_sql "tier4 family_link (seed)"      "${SEED_BASE}/04_family/02_tier4_verification_family_links.sql"
run_sql "tier4 membership (seed)"       "${SEED_BASE}/05_membership/01_tier4_verification_membership.sql"
echo ""

# -------------------------------------------------
# Phase 8b: Performance Indexes (migrations)
# Composite partial indexes for the family_majority
# CTE hot path (used by family list + org stats).
# Must run after DDL phases create the base tables.
# -------------------------------------------------
echo -e "${CYAN}[Phase 8b] Performance Indexes${NC}"
run_sql "performance indexes" "${REPO_ROOT}/database/migrations/add_performance_indexes.sql"
echo ""

# -------------------------------------------------
# Phase 9: Grant nss_db_backend read-only access
# Must run AFTER all DDL so GRANT SELECT ON ALL
# TABLES covers every table just created.
# -------------------------------------------------
echo -e "${CYAN}[Phase 9] Grant nss_db_backend read-only access${NC}"
run_sql "grant_backend" "${SCRIPT_DIR}/04_grant_backend.sql"
echo ""

# -------------------------------------------------
# Summary
# -------------------------------------------------
echo -e "${CYAN}=============================================${NC}"
echo -e "${CYAN}  BUILD SUMMARY${NC}"
echo -e "${CYAN}=============================================${NC}"
echo -e "  Scripts executed: ${total}"
echo -e "  Skipped:          ${skipped}  (already existed)"
echo -e "  Failed:           ${failed}"
echo ""

if [ "$failed" -eq 0 ]; then
    echo -e "  ${GREEN}Database build completed successfully.${NC}"
    echo ""
    echo -e "  ${YELLOW}Not executed (future phases):${NC}"
    echo "    - Authentication, Administration, remaining modules"
    echo "    - Pass 2 audit-actor FK constraints"
    exit 0
else
    echo -e "  ${RED}Database build FAILED (${failed} errors).${NC}"
    exit 1
fi
