# =====================================================
# NSS ERP — Full Database Build (PowerShell)
# =====================================================
#
# Executes all DDL and seed scripts in the frozen
# SOL-ARCH-011 phase order for currently implemented
# modules only.
#
# Authority: SOL-ARCH-010, SOL-ARCH-011
# Version: 2.6  - reinstate post_office (SOL-ARCH-010 Amendment, 2026-10-03:
#          Member-Assisted Geographic Entry). A PIN can hold many post
#          offices; post_office is one of the four member-writable
#          geographic levels. Supersedes the v2.5 retirement note below.
# Version: 2.5  - drop post_office (retired 2026-10-02: Simplified Geography
#          Model - district now lives on city_village, not a separate
#          office-grain table)
#
# Usage:
#   .\database\scripts\02_build.ps1 [-DbName nss_erp] [-DbUser nss_db_owner] [-DbHost localhost] [-DbPort 5432]
#
# Prerequisites:
#   - PostgreSQL running and accessible
#   - Database and roles created (see 00_create_database.sql)
#   - Extensions installed (see 01_extensions.sql)
#   - Role passwords set and api/.env generated (see 06_setup_env.sh)
#   - Run from the repository root directory
#
# Implemented phases:
#   Phase 0  - Bootstrap RBAC (3 tables + seed)
#   Phase 1  - Foundation DDL (14 tables: 02-13 + 16-17; system_event_log is
#              created separately in Phase 14)
#   Phase 2  - Foundation seed data (incl. ORGANIZATION_TYPE
#              category and unified STATUS category in master_data)
#   Phase 3  - Organization DDL (1 table)
#   Phase 4  - Organization seed data
#   Phase 5  - Person DDL (2 tables)
#   Phase 6  - Family DDL (6 tables)
#   Phase 7  - Membership DDL (14 tables)
#   Phase 7b - Deferred Foundation audit FKs (16_foundation_audit_fk.sql)
#   Phase 8  - Tier 4 Verification Seed Data (removed - no demo data)
#   Phase 9  - Grant nss_db_backend read-only access
#   Phase 10 - Authentication DDL (4 tables: user_account,
#              password_history, registration_claim, password_reset_token)
#   Phase 11 - Administration DDL (2 tables)
#   Phase 12 - Grant nss_db_writer write access (Tier 5)
#   Phase 13 - Admin bootstrap seed (NSS Admin superuser)
#   Phase 14 - Audit DDL (system_event_log table + DB trigger)
#
# NOT executed:
#   - database/seed/03_person/ (no seed data - Person data lives in
#     Foundation master_data; the superseded 01_person_master_tables.sql
#     DDL/seed were removed 2026-10-01, dead code with zero references)
#   - Pass 2 audit-actor FK constraints (deferred)
# =====================================================

param(
    [string]$DbName = "nss_erp",
    [string]$DbUser = "nss_db_owner",
    [string]$DbHost = "localhost",
    [int]$DbPort = 5432
)

$ErrorActionPreference = "Stop"

# Prompt for password once; export so all psql calls reuse it.
if (-not $env:PGPASSWORD) {
    $securePass = Read-Host "Password for ${DbUser}@${DbHost}:${DbPort}/${DbName}" -AsSecureString
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
    )
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path "$ScriptDir\..\..").Path
$DdlBase = "$RepoRoot\database\ddl"
$SeedBase = "$RepoRoot\database\seed"

# -------------------------------------------------
# Install Python dependencies
# -------------------------------------------------
Write-Host "=== Installing Python dependencies ===" -ForegroundColor Cyan
& python3 -m pip install -r "$RepoRoot\requirements.txt"
Write-Host ""

$total = 0
$failed = 0
$skipped = 0

function Invoke-Sql {
    param([string]$Label, [string]$File)
    $script:total++
    $output = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -v ON_ERROR_STOP=1 -f $File 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]   $Label" -ForegroundColor Green
    } else {
        # Check for idempotent-safe errors (table/index already exists,
        # duplicate seed rows).  These are expected on re-runs and should
        # not abort the build.
        $outputText = ($output | Out-String)
        if ($outputText -match 'already exists|duplicate key value violates unique constraint') {
            Write-Host "  [SKIP] $Label  (already exists)" -ForegroundColor Yellow
            $script:skipped++
        } else {
            Write-Host "  [FAIL] $Label" -ForegroundColor Red
            Write-Host "  Error:" -ForegroundColor Red
            $output | ForEach-Object { Write-Host "         $_" }
            $script:failed++
            Write-Host "  Aborting - fix the above error before continuing." -ForegroundColor Red
            exit 1
        }
    }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  NSS ERP - Full Database Build" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Database: $DbName"
Write-Host "  User:     $DbUser"
Write-Host "  Host:     ${DbHost}:${DbPort}"
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Phase 0: Bootstrap RBAC
Write-Host "[Phase 0] Bootstrap RBAC - DDL" -ForegroundColor Cyan
Invoke-Sql "role_master"       "$DdlBase\00_bootstrap\01_role_master.sql"
Invoke-Sql "permission_master" "$DdlBase\00_bootstrap\02_permission_master.sql"
Invoke-Sql "role_permission"   "$DdlBase\00_bootstrap\03_role_permission.sql"
Write-Host ""

Write-Host "[Phase 0] Bootstrap RBAC - Seed" -ForegroundColor Cyan
Invoke-Sql "permission_master (seed)" "$SeedBase\00_bootstrap\01_permission_master.sql"
Invoke-Sql "role_master (seed)"       "$SeedBase\00_bootstrap\02_role_master.sql"
Invoke-Sql "role_permission (seed)"   "$SeedBase\00_bootstrap\03_role_permission.sql"
Write-Host ""

# Phase 1: Foundation DDL
# Note: festival_master/festival_calendar_date (16/17) are
#       file-numbered after system_event_log/audit_trigger
#       (14/15) but run here in Phase 1 so the Phase 14 audit
#       trigger (which enumerates pg_tables at execution time)
#       still attaches to them.
Write-Host "[Phase 1] Foundation - DDL (14 tables)" -ForegroundColor Cyan
$foundationDdl = @(
    @("master_category",              "02_master_category.sql"),
    @("system_setting",               "03_system_setting.sql"),
    @("id_sequence_master",           "04_id_sequence_master.sql"),
    @("country",                      "05_country.sql"),
    @("document_master",              "06_document_master.sql"),
    @("field_change_log",             "07_field_change_log.sql"),
    @("master_data",                  "08_master_data.sql"),
    @("state",                        "09_state.sql"),
    @("district",                     "10_district.sql"),
    @("postal_code",                  "12_postal_code.sql"),
    @("post_office",                  "13_post_office.sql"),
    @("city_village",                "11_city_village.sql"),
    @("festival_master",              "16_festival_master.sql"),
    @("festival_calendar_date",       "17_festival_calendar_date.sql")
)
foreach ($entry in $foundationDdl) {
    Invoke-Sql $entry[0] "$DdlBase\01_foundation\$($entry[1])"
}
Write-Host ""

# Phase 2: Foundation Seed (includes ORGANIZATION_TYPE + unified STATUS in master_data)
Write-Host "[Phase 2] Foundation - Seed Data" -ForegroundColor Cyan
$foundationSeed = @(
    @("master_category (seed)",    "01_master_category.sql"),
    @("master_data (seed)",        "02_master_data.sql"),
    @("id_sequence_master (seed)", "03_id_sequence_master.sql"),
    @("country (seed)",            "04_country.sql"),
    @("state (seed)",              "05_state.sql"),
    @("district (seed)",           "06_district.sql"),
    @("system_setting (seed)",     "07_system_setting.sql"),
    @("postal_code (seed)",        "08_postal_code.sql"),
    @("postal_code bulk (seed)",   "08b_postal_code_bulk.sql"),
    @("post_office bulk (seed)",   "08c_post_office_bulk.sql"),
    @("festival_calendar (seed)",  "10_festival_calendar.sql"),
    @("city_village (seed)",       "11_city_village.sql"),
    @("city_village urban recovery (seed)", "11b_city_village_urban_recovery.sql")
)
foreach ($entry in $foundationSeed) {
    Invoke-Sql $entry[0] "$SeedBase\01_foundation\$($entry[1])"
}
Write-Host ""

# Phase 3: Organization DDL (1 table — type/status now in Foundation master_data)
Write-Host "[Phase 3] Organization - DDL (1 table + address-restriction trigger + Kumari/Sevak one-per-Sakha trigger)" -ForegroundColor Cyan
Invoke-Sql "organization"               "$DdlBase\02_organization\03_organization.sql"
Invoke-Sql "organization_address_restriction_trigger" "$DdlBase\02_organization\04_organization_address_restriction_trigger.sql"
Invoke-Sql "organization_kumari_sevak_uniqueness_trigger" "$DdlBase\02_organization\05_organization_kumari_sevak_uniqueness_trigger.sql"
Write-Host ""

# Phase 4: Organization Seed
Write-Host "[Phase 4] Organization - Seed Data" -ForegroundColor Cyan
Invoke-Sql "organization (seed)"               "$SeedBase\02_organization\03_organization.sql"
Invoke-Sql "sakha postal codes (seed)"          "$SeedBase\01_foundation\09_sakha_postal_codes.sql"
Invoke-Sql "sakha branches (seed)"              "$SeedBase\02_organization\05_sakha_branches.sql"
Invoke-Sql "id_sequence_master (org sync)"      "$SeedBase\02_organization\06_id_sequence_org_sync.sql"
Write-Host ""

# Phase 5: Person DDL
# Note: the superseded 01_person_master_tables.sql DDL/seed
#       were removed 2026-10-01 - dead code, zero references.
#       gender/marital_status/address_type data lives in
#       Foundation master_data seed.
Write-Host "[Phase 5] Person - DDL (2 tables)" -ForegroundColor Cyan
Invoke-Sql "person"         "$DdlBase\03_person\02_person.sql"
Invoke-Sql "person_address" "$DdlBase\03_person\03_person_address.sql"
Write-Host ""

# Phase 6: Family DDL (6 tables)
# Note: family_link stores only direct PARENT_OF/
#       SPOUSE_OF edges; all other relationship labels
#       are computed dynamically via BFS traversal.
Write-Host "[Phase 6] Family - DDL (6 tables + move-transition guard)" -ForegroundColor Cyan
Invoke-Sql "family_group"              "$DdlBase\04_family\01_family_group.sql"
Invoke-Sql "family_relationship"       "$DdlBase\04_family\02_family_relationship.sql"
Invoke-Sql "family_head_history"       "$DdlBase\04_family\03_family_head_history.sql"
Invoke-Sql "family_transition_history" "$DdlBase\04_family\04_family_transition_history.sql"
Invoke-Sql "family_link"               "$DdlBase\04_family\05_family_link.sql"
Invoke-Sql "family_admin"              "$DdlBase\04_family\06_family_admin.sql"
Invoke-Sql "family_move_transition_guard" "$DdlBase\04_family\07_family_move_transition_guard.sql"
Write-Host ""

# Phase 7: Membership DDL (14 tables)
# Note: sangha_sevi must be created first - all
#       other membership tables depend on it.
Write-Host "[Phase 7] Membership - DDL (14 tables + Sakha-only trigger)" -ForegroundColor Cyan
Invoke-Sql "sangha_sevi"                    "$DdlBase\05_membership\01_sangha_sevi.sql"
Invoke-Sql "membership_status_history"      "$DdlBase\05_membership\02_membership_status_history.sql"
Invoke-Sql "membership_renewal_request"     "$DdlBase\05_membership\03_membership_renewal_request.sql"
Invoke-Sql "membership_renewal_history"     "$DdlBase\05_membership\04_membership_renewal_history.sql"
Invoke-Sql "membership_transfer_history"    "$DdlBase\05_membership\05_membership_transfer_history.sql"
Invoke-Sql "membership_sakha_affiliation"   "$DdlBase\05_membership\06_membership_sakha_affiliation.sql"
Invoke-Sql "membership_journey_event"       "$DdlBase\05_membership\07_membership_journey_event.sql"
Invoke-Sql "probationary_member_review"     "$DdlBase\05_membership\08_probationary_member_review.sql"
Invoke-Sql "parichaya_patra"                "$DdlBase\05_membership\09_parichaya_patra.sql"
Invoke-Sql "parichaya_patra_history"        "$DdlBase\05_membership\10_parichaya_patra_history.sql"
Invoke-Sql "anumati_patra"                  "$DdlBase\05_membership\11_anumati_patra.sql"
Invoke-Sql "anumati_patra_history"          "$DdlBase\05_membership\12_anumati_patra_history.sql"
Invoke-Sql "darshak_attendance_registration" "$DdlBase\05_membership\13_darshak_attendance_registration.sql"
Invoke-Sql "sakha_only_membership_trigger"  "$DdlBase\05_membership\14_sakha_only_membership_trigger.sql"
Invoke-Sql "credential_sequence_counter"    "$DdlBase\05_membership\15_credential_sequence_counter.sql"
Write-Host ""

# Phase 7b: Deferred Foundation Audit FKs
# Wires the real FK constraints on district/postal_code/
# post_office/city_village's submitted_by/reviewed_by
# columns to sangha_sevi, now that sangha_sevi exists.
Write-Host "[Phase 7b] Deferred Foundation Audit FKs" -ForegroundColor Cyan
Invoke-Sql "foundation_audit_fk" "$DdlBase\05_membership\16_foundation_audit_fk.sql"
Write-Host ""

# Phase 8: Tier 4 Verification Seed Data
# Order: Organization -> Person -> Family -> Membership
# Phase 8: (Tier 4 test seeds removed — no demo data)
Write-Host ""

# Phase 9: Grant nss_db_backend read-only access
Write-Host "[Phase 9] Grant nss_db_backend read-only access" -ForegroundColor Cyan
Invoke-Sql "grant_backend" "$ScriptDir\04_grant_backend.sql"
Write-Host ""

# -------------------------------------------------
# Phase 10: Authentication DDL (4 tables, Depths 3-5)
# user_account FK -> person (Depth 3)
# password_history FK -> user_account (Depth 4)
# registration_claim FK -> user_account, person, organization, master_data (Depth 5)
# password_reset_token FK -> user_account (Depth 4)
# -------------------------------------------------
Write-Host "[Phase 10] Authentication - DDL (4 tables)" -ForegroundColor Cyan
Invoke-Sql "user_account"           "$DdlBase\06_authentication\01_user_account.sql"
Invoke-Sql "password_history"       "$DdlBase\06_authentication\02_password_history.sql"
Invoke-Sql "registration_claim"     "$DdlBase\06_authentication\03_registration_claim.sql"
Invoke-Sql "password_reset_token"   "$DdlBase\06_authentication\04_password_reset_token.sql"
Write-Host ""

# -------------------------------------------------
# Phase 11: Administration DDL (2 tables, Depths 4-5)
# user_role FK -> user_account + role_master (Depth 4)
# admin_scope FK -> user_role + organization (Depth 5)
# -------------------------------------------------
Write-Host "[Phase 11] Administration - DDL (2 tables)" -ForegroundColor Cyan
Invoke-Sql "user_role"    "$DdlBase\07_administration\01_user_role.sql"
Invoke-Sql "admin_scope"  "$DdlBase\07_administration\02_admin_scope.sql"
Write-Host ""

# -------------------------------------------------
# Phase 12: Grant nss_db_writer write access (Tier 5)
# Must run AFTER Auth + Admin DDL so the tables exist.
# Grants SELECT on ALL tables (login lookups) +
# INSERT/UPDATE on ALL nss tables, incl. future ones
# (no DELETE, no DDL).
# -------------------------------------------------
Write-Host "[Phase 12] Grant nss_db_writer write access" -ForegroundColor Cyan
Invoke-Sql "create_writer_role" "$ScriptDir\05_create_writer_role.sql"
Write-Host ""

# -------------------------------------------------
# Phase 13: Admin Bootstrap Seed
# Seeds NSS Admin superuser (P1 / SS1 / Admin@123)
# with NSS_ERP_ADMIN role and NSS-WIDE scope.
# Must run AFTER Auth + Admin DDL (Phases 10-11)
# and AFTER Foundation + Organization seeds.
#
# Uses the Python bootstrap script (not psql) because
# the user_account INSERT requires an Argon2 password
# hash generated at runtime.
# -------------------------------------------------
Write-Host "[Phase 13] Admin Bootstrap Seed" -ForegroundColor Cyan
$script:total++
try {
    $output = & python3 "$RepoRoot\scripts\bootstrap_admin.py" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK]   admin_bootstrap" -ForegroundColor Green
    } else {
        Write-Host "  [FAIL] admin_bootstrap" -ForegroundColor Red
        Write-Host "  Error: $output"
        $script:failed++
    }
} catch {
    Write-Host "  [FAIL] admin_bootstrap" -ForegroundColor Red
    Write-Host "  Error: $_"
    $script:failed++
}
Write-Host ""

# -------------------------------------------------
# Phase 14: Audit DDL (system_event_log + DB trigger)
# Must run AFTER all other DDL so the trigger can
# attach to every table in the nss schema.
# -------------------------------------------------
Write-Host "[Phase 14] Audit - DDL (1 table + trigger)" -ForegroundColor Cyan
Invoke-Sql "system_event_log"  "$DdlBase\01_foundation\14_system_event_log.sql"
Invoke-Sql "audit_trigger"     "$DdlBase\01_foundation\15_audit_trigger.sql"
Write-Host ""

# -------------------------------------------------
# Summary
# -------------------------------------------------
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  BUILD SUMMARY" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Scripts executed: $total"
Write-Host "  Skipped:          $skipped  (already existed)"
Write-Host "  Failed:           $failed"
Write-Host ""

if ($failed -eq 0) {
    Write-Host "  Database build completed successfully." -ForegroundColor Green
    Write-Host ""
    Write-Host "  Not executed (future phases):" -ForegroundColor Yellow
    Write-Host "    - Pass 2 audit-actor FK constraints"
    exit 0
} else {
    Write-Host "  Database build FAILED ($failed errors)." -ForegroundColor Red
    exit 1
}
