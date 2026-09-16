# =====================================================
# NSS ERP — Full Database Build (PowerShell)
# =====================================================
#
# Executes all DDL and seed scripts in the frozen
# SOL-ARCH-011 phase order for currently implemented
# modules only.
#
# Authority: SOL-ARCH-010, SOL-ARCH-011
# Version: 2.1  - idempotent re-run (SKIP on "already exists")
#
# Usage:
#   .\database\scripts\02_build.ps1 [-DbName nss_erp] [-DbUser nss_db_owner] [-DbHost localhost] [-DbPort 5432]
#
# Prerequisites:
#   - PostgreSQL running and accessible
#   - Database and roles created (see 00_create_database.sql)
#   - Extensions installed (see 01_extensions.sql)
#   - Run from the repository root directory
#
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
Write-Host "[Phase 1] Foundation - DDL (12 tables)" -ForegroundColor Cyan
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
    @("city_village",                 "11_city_village.sql"),
    @("postal_code",                  "12_postal_code.sql"),
    @("city_village_postal_code_map", "13_city_village_postal_code_map.sql")
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
    @("postal_code (seed)",        "08_postal_code.sql")
)
foreach ($entry in $foundationSeed) {
    Invoke-Sql $entry[0] "$SeedBase\01_foundation\$($entry[1])"
}
Write-Host ""

# Phase 3: Organization DDL (1 table — type/status now in Foundation master_data)
Write-Host "[Phase 3] Organization - DDL (1 table)" -ForegroundColor Cyan
Invoke-Sql "organization"               "$DdlBase\02_organization\03_organization.sql"
Write-Host ""

# Phase 4: Organization Seed
Write-Host "[Phase 4] Organization - Seed Data" -ForegroundColor Cyan
Invoke-Sql "organization (seed)"               "$SeedBase\02_organization\03_organization.sql"
Write-Host ""

# Phase 5: Person DDL
# Note: 01_person_master_tables.sql is SUPERSEDED -
#       gender/marital_status/address_type data is now
#       in Foundation master_data seed.
Write-Host "[Phase 5] Person - DDL (2 tables)" -ForegroundColor Cyan
Invoke-Sql "person"         "$DdlBase\03_person\02_person.sql"
Invoke-Sql "person_address" "$DdlBase\03_person\03_person_address.sql"
Write-Host ""

# Phase 6: Family DDL (5 tables)
# Note: family_link stores only direct PARENT_OF/
#       SPOUSE_OF edges; all other relationship labels
#       are computed dynamically via BFS traversal.
Write-Host "[Phase 6] Family - DDL (5 tables)" -ForegroundColor Cyan
Invoke-Sql "family_group"              "$DdlBase\04_family\01_family_group.sql"
Invoke-Sql "family_relationship"       "$DdlBase\04_family\02_family_relationship.sql"
Invoke-Sql "family_head_history"       "$DdlBase\04_family\03_family_head_history.sql"
Invoke-Sql "family_transition_history" "$DdlBase\04_family\04_family_transition_history.sql"
Invoke-Sql "family_link"               "$DdlBase\04_family\05_family_link.sql"
Write-Host ""

# Phase 7: Membership DDL (12 tables)
# Note: sangha_sevi must be created first - all
#       other membership tables depend on it.
Write-Host "[Phase 7] Membership - DDL (12 tables)" -ForegroundColor Cyan
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
Write-Host ""

# Phase 8: Tier 4 Verification Seed Data
# Order: Organization -> Person -> Family -> Membership
Write-Host "[Phase 8] Tier 4 Verification - Seed Data" -ForegroundColor Cyan
Invoke-Sql "tier4 organizations (seed)"    "$SeedBase\02_organization\04_tier4_verification_orgs.sql"
Invoke-Sql "tier4 persons (seed)"          "$SeedBase\03_person\02_tier4_verification_persons.sql"
Invoke-Sql "tier4 family (seed)"           "$SeedBase\04_family\01_tier4_verification_family.sql"
Invoke-Sql "tier4 family_link (seed)"      "$SeedBase\04_family\02_tier4_verification_family_links.sql"
Invoke-Sql "tier4 membership (seed)"       "$SeedBase\05_membership\01_tier4_verification_membership.sql"
Write-Host ""

# Phase 8b: Performance Indexes (migrations)
# Composite partial indexes for the family_majority
# CTE hot path (used by family list + org stats).
Write-Host "[Phase 8b] Performance Indexes" -ForegroundColor Cyan
Invoke-Sql "performance indexes" "$RepoRoot\database\migrations\add_performance_indexes.sql"
Write-Host ""

# Phase 9: Grant nss_db_backend read-only access
Write-Host "[Phase 9] Grant nss_db_backend read-only access" -ForegroundColor Cyan
Invoke-Sql "grant_backend" "$ScriptDir\04_grant_backend.sql"
Write-Host ""

# Summary
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
    Write-Host "    - Person seed (03_person/ is superseded - data in Foundation seed)"
    Write-Host "    - Authentication, Administration, remaining modules"
    Write-Host "    - Pass 2 audit-actor FK constraints"
    exit 0
} else {
    Write-Host "  Database build FAILED ($failed errors)." -ForegroundColor Red
    exit 1
}
