# =====================================================
# NSS ERP — Post-Build Validation (PowerShell)
# =====================================================
#
# Validates that all implemented modules were built
# correctly. Does NOT execute any DDL or seed scripts -
# run 02_build.ps1 first.
#
# Authority: SOL-ARCH-010, SOL-ARCH-011
# Version: 1.1 — add Auth (4 tables), Admin (2 tables),
#                 person address FK columns
#
# Usage:
#   .\database\scripts\03_validate.ps1 [-DbName nss_erp] [-DbUser nss_db_owner] [-DbHost localhost] [-DbPort 5432]
#
# =====================================================

param(
    [string]$DbName = "nss_erp",
    [string]$DbUser = "nss_db_owner",
    [string]$DbHost = "localhost",
    [int]$DbPort = 5432
)

# Prompt for password once; export so all psql calls reuse it.
if (-not $env:PGPASSWORD) {
    $securePass = Read-Host "Password for ${DbUser}@${DbHost}:${DbPort}/${DbName}" -AsSecureString
    $env:PGPASSWORD = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePass)
    )
}

$pass_count = 0
$fail_count = 0
$warn_count = 0

function Invoke-PsqlQuery {
    param([string]$Query)
    $result = & psql -h $DbHost -p $DbPort -U $DbUser -d $DbName -t -A -c $Query 2>&1
    if ($LASTEXITCODE -ne 0) { return "ERROR" }
    return ($result | Out-String).Trim()
}

function Log-Pass { param([string]$Msg); Write-Host "  [PASS] $Msg" -ForegroundColor Green; $script:pass_count++ }
function Log-Fail { param([string]$Msg); Write-Host "  [FAIL] $Msg" -ForegroundColor Red; $script:fail_count++ }
function Log-Warn { param([string]$Msg); Write-Host "  [WARN] $Msg" -ForegroundColor Yellow; $script:warn_count++ }

function Check-TableExists {
    param([string]$Table)
    $result = Invoke-PsqlQuery "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'nss' AND table_name = '$Table');"
    if ($result -eq "t") { Log-Pass "$Table exists" } else { Log-Fail "$Table MISSING" }
}

function Check-RowCount {
    param([string]$Table, [int]$Expected)
    $count = Invoke-PsqlQuery "SELECT COUNT(*) FROM nss.$Table;"
    if ($count -eq "ERROR") { Log-Fail "${Table}: query failed" }
    elseif ([int]$count -ge $Expected) { Log-Pass "${Table}: $count rows (expected >= $Expected)" }
    else { Log-Warn "${Table}: $count rows (expected >= $Expected)" }
}

function Check-NoDuplicates {
    param([string]$Table, [string]$Column)
    $dups = Invoke-PsqlQuery "SELECT COUNT(*) FROM (SELECT $Column FROM nss.$Table GROUP BY $Column HAVING COUNT(*) > 1) x;"
    if ($dups -eq "0") { Log-Pass "${Table}: no duplicate $Column" }
    elseif ($dups -eq "ERROR") { Log-Fail "${Table}: duplicate check failed" }
    else { Log-Fail "${Table}: $dups duplicate $Column values" }
}

function Check-FkIntegrity {
    param([string]$Label, [string]$Query)
    $orphans = Invoke-PsqlQuery $Query
    if ($orphans -eq "0") { Log-Pass "${Label}: FK integrity valid" }
    elseif ($orphans -eq "ERROR") { Log-Fail "${Label}: FK check failed" }
    else { Log-Fail "${Label}: $orphans orphaned rows" }
}

function Check-ColumnExists {
    param([string]$Table, [string]$Column)
    $result = Invoke-PsqlQuery "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'nss' AND table_name = '$Table' AND column_name = '$Column');"
    if ($result -eq "t") { Log-Pass "${Table}.${Column} present" } else { Log-Fail "${Table}.${Column} MISSING" }
}

function Check-MinPercentage {
    param([string]$Label, [string]$Query, [double]$MinPct)
    $pct = Invoke-PsqlQuery $Query
    if ($pct -eq "ERROR") { Log-Fail "${Label}: query failed" }
    elseif ([double]$pct -ge $MinPct) { Log-Pass "${Label}: ${pct}% (expected >= ${MinPct}%)" }
    else { Log-Fail "${Label}: ${pct}% (expected >= ${MinPct}%)" }
}

# Header
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  NSS ERP - Post-Build Validation" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Database: $DbName"
Write-Host "  User:     $DbUser"
Write-Host "  Host:     ${DbHost}:${DbPort}"
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Bootstrap RBAC
Write-Host "--- Bootstrap RBAC ---" -ForegroundColor Cyan
Write-Host "  Tables:"
Check-TableExists "role_master"
Check-TableExists "permission_master"
Check-TableExists "role_permission"

Write-Host "  Row counts:"
Check-RowCount "role_master" 8

Write-Host "  Unique constraints:"
Check-NoDuplicates "role_master" "role_code"

Write-Host "  FK integrity:"
Check-FkIntegrity "role_permission -> role_master" "SELECT COUNT(*) FROM nss.role_permission rp LEFT JOIN nss.role_master rm ON rp.role_master_pk = rm.role_master_pk WHERE rm.role_master_pk IS NULL;"
Check-FkIntegrity "role_permission -> permission_master" "SELECT COUNT(*) FROM nss.role_permission rp LEFT JOIN nss.permission_master pm ON rp.permission_master_pk = pm.permission_master_pk WHERE pm.permission_master_pk IS NULL;"
Write-Host ""

# Foundation
Write-Host "--- Foundation ---" -ForegroundColor Cyan
Write-Host "  Tables:"
$foundationTables = @("master_category","system_setting","id_sequence_master","country","document_master","field_change_log","master_data","state","district","city_village","postal_code")
foreach ($t in $foundationTables) { Check-TableExists $t }

Write-Host "  Row counts:"
Check-RowCount "master_category" 13
Check-RowCount "master_data" 82
Check-RowCount "id_sequence_master" 11
Check-RowCount "country" 5
Check-RowCount "state" 112
Check-RowCount "district" 780
Check-RowCount "system_setting" 4
Check-RowCount "postal_code" 17800
Check-RowCount "city_village" 673000

Write-Host "  Unique constraints:"
Check-NoDuplicates "master_category" "category_code"
Check-NoDuplicates "country" "country_code"
Check-NoDuplicates "id_sequence_master" "sequence_code"
Check-NoDuplicates "postal_code" "postal_code"

Write-Host "  FK integrity:"
Check-FkIntegrity "master_data -> master_category" "SELECT COUNT(*) FROM nss.master_data md LEFT JOIN nss.master_category mc ON md.master_category_pk = mc.master_category_pk WHERE mc.master_category_pk IS NULL;"
Check-FkIntegrity "state -> country" "SELECT COUNT(*) FROM nss.state s LEFT JOIN nss.country c ON s.country_pk = c.country_pk WHERE c.country_pk IS NULL;"
Check-FkIntegrity "district -> state" "SELECT COUNT(*) FROM nss.district d LEFT JOIN nss.state s ON d.state_pk = s.state_pk WHERE s.state_pk IS NULL;"
Check-FkIntegrity "postal_code -> state" "SELECT COUNT(*) FROM nss.postal_code p LEFT JOIN nss.state s ON p.state_pk = s.state_pk WHERE s.state_pk IS NULL;"
Check-FkIntegrity "city_village -> postal_code" "SELECT COUNT(*) FROM nss.city_village cv LEFT JOIN nss.postal_code pc ON cv.postal_code_pk = pc.postal_code_pk WHERE cv.postal_code_pk IS NOT NULL AND pc.postal_code_pk IS NULL;"
Check-FkIntegrity "city_village -> district" "SELECT COUNT(*) FROM nss.city_village cv LEFT JOIN nss.district d ON cv.district_pk = d.district_pk WHERE cv.district_pk IS NOT NULL AND d.district_pk IS NULL;"

Write-Host "  Geography model (SOL-ARCH-010 Amendment, 2026-10-02 - district at city_village grain):"
Check-ColumnExists "city_village" "district_pk"
Check-MinPercentage "city_village district_pk coverage" "SELECT ROUND(COUNT(*) FILTER (WHERE district_pk IS NOT NULL) * 100.0 / NULLIF(COUNT(*),0), 2) FROM nss.city_village;" 98

Write-Host "  Deferred columns:"
Check-ColumnExists "document_master" "person_pk"
Check-ColumnExists "document_master" "uploaded_by_sangha_sevi_pk"
Write-Host ""

# Organization (1 table - type/status via master_data)
Write-Host "--- Organization ---" -ForegroundColor Cyan
Write-Host "  Tables:"
Check-TableExists "organization"

Write-Host "  Row counts:"
Check-RowCount "organization" 3

Write-Host "  Unique constraints:"
Check-NoDuplicates "organization" "organization_code"

Write-Host "  FK integrity:"
Check-FkIntegrity "organization -> master_data (type)" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.master_data md ON o.organization_type_master_data_pk = md.master_data_pk WHERE md.master_data_pk IS NULL;"
Check-FkIntegrity "organization -> master_data (status)" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.master_data md ON o.status_master_data_pk = md.master_data_pk WHERE md.master_data_pk IS NULL;"
Check-FkIntegrity "organization -> country" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.country c ON o.country_pk = c.country_pk WHERE o.country_pk IS NOT NULL AND c.country_pk IS NULL;"
Check-FkIntegrity "organization -> city_village" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.city_village cv ON o.city_village_pk = cv.city_village_pk WHERE o.city_village_pk IS NOT NULL AND cv.city_village_pk IS NULL;"
Check-FkIntegrity "organization -> postal_code" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.postal_code pc ON o.postal_code_pk = pc.postal_code_pk WHERE o.postal_code_pk IS NOT NULL AND pc.postal_code_pk IS NULL;"
Write-Host ""

# Person (2 tables - no seed data)
Write-Host "--- Person ---" -ForegroundColor Cyan
Write-Host "  Tables:"
Check-TableExists "person"
Check-TableExists "person_address"

Write-Host "  Row counts (no seed - expect 0):"
Check-RowCount "person" 0
Check-RowCount "person_address" 0

Write-Host "  FK integrity:"
Check-FkIntegrity "person -> master_data (gender)" "SELECT COUNT(*) FROM nss.person p LEFT JOIN nss.master_data md ON p.gender_master_data_pk = md.master_data_pk WHERE p.gender_master_data_pk IS NOT NULL AND md.master_data_pk IS NULL;"
Check-FkIntegrity "person -> master_data (marital_status)" "SELECT COUNT(*) FROM nss.person p LEFT JOIN nss.master_data md ON p.marital_status_master_data_pk = md.master_data_pk WHERE p.marital_status_master_data_pk IS NOT NULL AND md.master_data_pk IS NULL;"
Check-FkIntegrity "person -> master_data (blood_group)" "SELECT COUNT(*) FROM nss.person p LEFT JOIN nss.master_data md ON p.blood_group_master_data_pk = md.master_data_pk WHERE p.blood_group_master_data_pk IS NOT NULL AND md.master_data_pk IS NULL;"
Check-FkIntegrity "person_address -> person" "SELECT COUNT(*) FROM nss.person_address pa LEFT JOIN nss.person p ON pa.person_pk = p.person_pk WHERE p.person_pk IS NULL;"
Check-FkIntegrity "person_address -> master_data (address_type)" "SELECT COUNT(*) FROM nss.person_address pa LEFT JOIN nss.master_data md ON pa.address_type_master_data_pk = md.master_data_pk WHERE md.master_data_pk IS NULL;"

Write-Host "  Person address FK columns:"
Check-ColumnExists "person" "country_pk"
Check-ColumnExists "person" "state_pk"
Check-ColumnExists "person" "district_pk"
Check-ColumnExists "person" "city_village_pk"
Check-ColumnExists "person" "postal_code_pk"
Write-Host ""

# Authentication (4 tables)
Write-Host "--- Authentication ---" -ForegroundColor Cyan
Write-Host "  Tables:"
Check-TableExists "user_account"
Check-TableExists "password_history"
Check-TableExists "registration_claim"
Check-TableExists "password_reset_token"

Write-Host "  Row counts:"
Check-RowCount "user_account" 1
Check-RowCount "password_history" 0

Write-Host "  Key columns:"
Check-ColumnExists "user_account" "person_pk"
Check-ColumnExists "user_account" "password_hash"
Check-ColumnExists "user_account" "account_status"
Check-ColumnExists "user_account" "is_active"
Check-ColumnExists "user_account" "failed_login_attempts"
Check-ColumnExists "user_account" "locked_until"
Check-ColumnExists "user_account" "password_expires_at"
Check-ColumnExists "user_account" "force_password_change"
Check-ColumnExists "user_account" "last_login_at"
Check-ColumnExists "password_history" "user_account_pk"
Check-ColumnExists "password_history" "password_hash"

Write-Host "  Unique constraints:"
Check-NoDuplicates "user_account" "person_pk"

Write-Host "  FK integrity:"
Check-FkIntegrity "user_account -> person" "SELECT COUNT(*) FROM nss.user_account ua LEFT JOIN nss.person p ON ua.person_pk = p.person_pk WHERE p.person_pk IS NULL;"
Check-FkIntegrity "password_history -> user_account" "SELECT COUNT(*) FROM nss.password_history ph LEFT JOIN nss.user_account ua ON ph.user_account_pk = ua.user_account_pk WHERE ua.user_account_pk IS NULL;"
Write-Host ""

# Administration (2 tables)
Write-Host "--- Administration ---" -ForegroundColor Cyan
Write-Host "  Tables:"
Check-TableExists "user_role"
Check-TableExists "admin_scope"

Write-Host "  Row counts:"
Check-RowCount "user_role" 1
Check-RowCount "admin_scope" 1

Write-Host "  Key columns:"
Check-ColumnExists "user_role" "user_account_pk"
Check-ColumnExists "user_role" "role_master_pk"
Check-ColumnExists "user_role" "is_active"
Check-ColumnExists "admin_scope" "user_role_pk"
Check-ColumnExists "admin_scope" "scope_level"
Check-ColumnExists "admin_scope" "organization_pk"

Write-Host "  FK integrity:"
Check-FkIntegrity "user_role -> user_account" "SELECT COUNT(*) FROM nss.user_role ur LEFT JOIN nss.user_account ua ON ur.user_account_pk = ua.user_account_pk WHERE ua.user_account_pk IS NULL;"
Check-FkIntegrity "user_role -> role_master" "SELECT COUNT(*) FROM nss.user_role ur LEFT JOIN nss.role_master rm ON ur.role_master_pk = rm.role_master_pk WHERE rm.role_master_pk IS NULL;"
Check-FkIntegrity "admin_scope -> user_role" "SELECT COUNT(*) FROM nss.admin_scope asc2 LEFT JOIN nss.user_role ur ON asc2.user_role_pk = ur.user_role_pk WHERE ur.user_role_pk IS NULL;"
Check-FkIntegrity "admin_scope -> organization" "SELECT COUNT(*) FROM nss.admin_scope asc2 LEFT JOIN nss.organization o ON asc2.organization_pk = o.organization_pk WHERE asc2.organization_pk IS NOT NULL AND o.organization_pk IS NULL;"
Write-Host ""

# Summary
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  VALIDATION RESULTS" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Passed:   $pass_count" -ForegroundColor Green
Write-Host "  Warnings: $warn_count" -ForegroundColor Yellow
Write-Host "  Failed:   $fail_count" -ForegroundColor Red
Write-Host ""

if ($fail_count -eq 0 -and $warn_count -eq 0) {
    Write-Host "  All validations PASSED" -ForegroundColor Green
    exit 0
} elseif ($fail_count -eq 0) {
    Write-Host "  Passed with warnings ($warn_count)" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "  Validation FAILED ($fail_count failures)" -ForegroundColor Red
    exit 1
}
