#!/usr/bin/env bash
# ==========================================================
# render_build.sh — Render.com build script
# ==========================================================
#
# Runs on every deploy. Installs Python dependencies, and —
# ONLY when explicitly requested — bootstraps the PostgreSQL
# database (DDL + seed).
#
# RUN_DB_BOOTSTRAP (decided 2026-10-05): the full DDL+seed
# bootstrap below is now gated behind this env var and SKIPPED
# by default. It used to run on every deploy (idempotent,
# skip-on-exists), which was fine for early iteration but is
# the wrong default now — day-to-day deploys should only ship
# app code, not re-touch the database. The full bootstrap is
# kept, unchanged, for the one real use case it's still needed
# for: standing up the database from scratch on the org server.
# Set RUN_DB_BOOTSTRAP=true in the Render/host dashboard only
# for that run, then unset it again.
#
# Idempotent re-run, same as database/scripts/02_build.sh
# (Version 2.1): every phase runs on every deploy; any SQL
# statement that fails with "already exists" or a duplicate
# key violation is treated as expected on a re-run and
# SKIPPED rather than aborting the build. This means a
# redeploy against an already-bootstrapped database safely
# picks up any phases added since the last deploy (e.g. a
# new tier's DDL/seed) without needing to drop and recreate
# anything.
#
# Database: Neon.dev (per TECH_STACK_DECISIONS.md §1)
# App host: Render.com (per TECH_STACK_DECISIONS.md §2)
#
# Required env vars (set in Render dashboard):
#   DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
#   DB_WRITE_USER, DB_WRITE_PASSWORD (Tier 5 nss_db_writer pool)
#   JWT_SECRET_KEY (Tier 5 auth)
#   RUN_DB_BOOTSTRAP (optional; "true" to run DDL+seed, default: skipped)
#
# Keep phase order in sync with database/scripts/02_build.sh
# if it changes.
# ==========================================================

set -euo pipefail

echo "=== Building Tailwind CSS (tree-shaken + DaisyUI) ==="
npm install
npx tailwindcss -i frontend/assets/css/tailwind-input.css -o frontend/assets/css/tailwind.min.css --minify

echo ""
echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo ""
if [ "${RUN_DB_BOOTSTRAP:-false}" != "true" ]; then
    echo "=== Skipping database bootstrap (RUN_DB_BOOTSTRAP not set to true) ==="
    echo ""
    echo "=== Build finished ==="
    exit 0
fi

echo "=== Bootstrapping database (Neon.dev) ==="

# Neon uses standard PostgreSQL wire protocol — psql works directly.
export PGPASSWORD="${DB_PASSWORD}"
PSQL="psql -h ${DB_HOST} -p ${DB_PORT} -U ${DB_USER} -d ${DB_NAME} -v ON_ERROR_STOP=1"

# Neon requires SSL
export PGSSLMODE="require"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DDL_BASE="${REPO_ROOT}/database/ddl"
SEED_BASE="${REPO_ROOT}/database/seed"

run_sql() {
    local label="$1"
    local file="$2"
    local output
    if output=$(${PSQL} -f "${file}" 2>&1); then
        echo "  [OK]   ${label}"
    else
        # Idempotent-safe errors (table/index already exists, duplicate
        # seed rows) are expected on re-runs and should not abort the
        # build — matches database/scripts/02_build.sh's behaviour.
        if echo "${output}" | grep -qiE 'already exists|duplicate key value violates unique constraint'; then
            echo "  [SKIP] ${label}  (already exists)"
        else
            echo "  [FAIL] ${label}"
            echo "${output}" | sed 's/^/         /'
            exit 1
        fi
    fi
}

echo "--- Creating nss schema ---"
${PSQL} -c "CREATE SCHEMA IF NOT EXISTS nss;"
${PSQL} -c "ALTER DATABASE ${DB_NAME} SET search_path TO nss, public;"
${PSQL} -c "SET search_path TO nss, public;"

echo "--- Installing extensions (best-effort) ---"
${PSQL} -c "CREATE EXTENSION IF NOT EXISTS pgcrypto;" 2>/dev/null || echo "  pgcrypto not available — skipping"
${PSQL} -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;" 2>/dev/null || echo "  pg_trgm not available — skipping"
${PSQL} -c "CREATE EXTENSION IF NOT EXISTS btree_gin;" 2>/dev/null || echo "  btree_gin not available — skipping"

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
echo "--- Phase 1: Foundation — DDL (14 tables) ---"
run_sql "master_category"                "${DDL_BASE}/01_foundation/02_master_category.sql"
run_sql "system_setting"                 "${DDL_BASE}/01_foundation/03_system_setting.sql"
run_sql "id_sequence_master"             "${DDL_BASE}/01_foundation/04_id_sequence_master.sql"
run_sql "country"                        "${DDL_BASE}/01_foundation/05_country.sql"
run_sql "document_master"                "${DDL_BASE}/01_foundation/06_document_master.sql"
run_sql "field_change_log"               "${DDL_BASE}/01_foundation/07_field_change_log.sql"
run_sql "master_data"                    "${DDL_BASE}/01_foundation/08_master_data.sql"
run_sql "state"                          "${DDL_BASE}/01_foundation/09_state.sql"
run_sql "district"                       "${DDL_BASE}/01_foundation/10_district.sql"
run_sql "postal_code"                    "${DDL_BASE}/01_foundation/12_postal_code.sql"
run_sql "post_office"                    "${DDL_BASE}/01_foundation/13_post_office.sql"
run_sql "city_village"                   "${DDL_BASE}/01_foundation/11_city_village.sql"
run_sql "festival_master"                "${DDL_BASE}/01_foundation/16_festival_master.sql"
run_sql "festival_calendar_date"         "${DDL_BASE}/01_foundation/17_festival_calendar_date.sql"

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
run_sql "postal_code bulk (seed)"   "${SEED_BASE}/01_foundation/08b_postal_code_bulk.sql"
run_sql "post_office bulk (seed)"   "${SEED_BASE}/01_foundation/08c_post_office_bulk.sql"
run_sql "city_village (seed)"       "${SEED_BASE}/01_foundation/11_city_village.sql"
run_sql "city_village urban recovery (seed)" "${SEED_BASE}/01_foundation/11b_city_village_urban_recovery.sql"
run_sql "festival_calendar (seed)"  "${SEED_BASE}/01_foundation/10_festival_calendar.sql"

echo ""
echo "--- Phase 3: Organization — DDL (1 table + address-restriction trigger + Kumari/Sevak one-per-Sakha trigger; type via ORGANIZATION_TYPE, status via unified STATUS in Foundation master_data) ---"
run_sql "organization"               "${DDL_BASE}/02_organization/03_organization.sql"
run_sql "organization_address_restriction_trigger" "${DDL_BASE}/02_organization/04_organization_address_restriction_trigger.sql"
run_sql "organization_kumari_sevak_uniqueness_trigger" "${DDL_BASE}/02_organization/05_organization_kumari_sevak_uniqueness_trigger.sql"

echo ""
echo "--- Phase 4: Organization — Seed ---"
run_sql "organization (seed)"               "${SEED_BASE}/02_organization/03_organization.sql"
run_sql "sakha postal codes (seed)"          "${SEED_BASE}/01_foundation/09_sakha_postal_codes.sql"
run_sql "sakha branches (seed)"              "${SEED_BASE}/02_organization/05_sakha_branches.sql"
run_sql "id_sequence_master (org sync)"      "${SEED_BASE}/02_organization/06_id_sequence_org_sync.sql"

echo ""
echo "--- Phase 5: Person — DDL (2 tables) ---"
run_sql "person"         "${DDL_BASE}/03_person/02_person.sql"
run_sql "person_address" "${DDL_BASE}/03_person/03_person_address.sql"

echo ""
echo "--- Phase 6: Family — DDL (6 tables + move-transition guard) ---"
run_sql "family_group"              "${DDL_BASE}/04_family/01_family_group.sql"
run_sql "family_relationship"       "${DDL_BASE}/04_family/02_family_relationship.sql"
run_sql "family_head_history"       "${DDL_BASE}/04_family/03_family_head_history.sql"
run_sql "family_transition_history" "${DDL_BASE}/04_family/04_family_transition_history.sql"
run_sql "family_link"               "${DDL_BASE}/04_family/05_family_link.sql"
run_sql "family_admin"              "${DDL_BASE}/04_family/06_family_admin.sql"
run_sql "family_move_transition_guard" "${DDL_BASE}/04_family/07_family_move_transition_guard.sql"

echo ""
echo "--- Phase 7: Membership — DDL (14 tables + Sakha-only trigger) ---"
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
run_sql "darshak_attendance_registration" "${DDL_BASE}/05_membership/13_darshak_attendance_registration.sql"
run_sql "sakha_only_membership_trigger"  "${DDL_BASE}/05_membership/14_sakha_only_membership_trigger.sql"
run_sql "credential_sequence_counter"    "${DDL_BASE}/05_membership/15_credential_sequence_counter.sql"

echo ""
echo "--- Phase 7b: Deferred Foundation Audit FKs ---"
# Wires the real FK constraints on district/postal_code/post_office/
# city_village's submitted_by/reviewed_by columns to sangha_sevi, now
# that sangha_sevi exists. Not a migration — runs every full rebuild
# against brand-new, empty tables (circular-dependency handling).
run_sql "foundation_audit_fk" "${DDL_BASE}/05_membership/16_foundation_audit_fk.sql"

echo ""
echo "--- Ensuring nss_db_owner, nss_db_backend, and nss_db_writer roles exist ---"
# database/scripts/00_create_database.sql normally creates both roles,
# but that script requires a true Postgres superuser + dblink back to
# localhost -- meaningless on managed Neon -- so it's never been run
# there. Created here instead, idempotently, so the naming convention
# matches local dev and Phase 9's GRANT has a target role. Both reuse
# DB_PASSWORD since Render only configures one credential set for this
# service; note the running API here connects as whatever DB_USER is
# (the Neon-provided owner role used to run this whole build), not as
# nss_db_backend -- so the grant below is not yet actually enforcing
# least-privilege access in this deployment, only preparing for it.
${PSQL} <<SQL
DO \$do\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'nss_db_owner') THEN
        CREATE ROLE nss_db_owner LOGIN PASSWORD '${DB_PASSWORD}';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'nss_db_backend') THEN
        CREATE ROLE nss_db_backend LOGIN PASSWORD '${DB_PASSWORD}';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = 'nss_db_writer') THEN
        CREATE ROLE nss_db_writer LOGIN PASSWORD '${DB_WRITE_PASSWORD:-${DB_PASSWORD}}';
    END IF;
END
\$do\$;
SQL

echo ""
echo "--- Phase 9: Grant nss_db_backend read-only access ---"
run_sql "grant_backend" "${REPO_ROOT}/database/scripts/04_grant_backend.sql"

echo ""
echo "--- Phase 10: Authentication — DDL (4 tables) ---"
run_sql "user_account"           "${DDL_BASE}/06_authentication/01_user_account.sql"
run_sql "password_history"       "${DDL_BASE}/06_authentication/02_password_history.sql"
run_sql "registration_claim"     "${DDL_BASE}/06_authentication/03_registration_claim.sql"
run_sql "password_reset_token"   "${DDL_BASE}/06_authentication/04_password_reset_token.sql"

echo ""
echo "--- Phase 11: Administration — DDL (2 tables) ---"
run_sql "user_role"    "${DDL_BASE}/07_administration/01_user_role.sql"
run_sql "admin_scope"  "${DDL_BASE}/07_administration/02_admin_scope.sql"

echo ""
echo "--- Phase 12: Grant nss_db_writer write access ---"
run_sql "create_writer_role" "${REPO_ROOT}/database/scripts/05_create_writer_role.sql"

echo ""
echo "--- Phase 13: Admin Bootstrap Seed ---"
python3 "${REPO_ROOT}/scripts/bootstrap_admin.py" || echo "  [WARN] admin_bootstrap (may already exist)"

echo ""
echo "--- Phase 14: Audit — DDL (1 table + trigger) ---"
run_sql "system_event_log"  "${DDL_BASE}/01_foundation/14_system_event_log.sql"
run_sql "audit_trigger"     "${DDL_BASE}/01_foundation/15_audit_trigger.sql"

echo ""
echo "=== Database bootstrap complete (Neon.dev) ==="
echo ""
echo "=== Build finished ==="
