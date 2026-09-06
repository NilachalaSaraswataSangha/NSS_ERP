# =====================================================
# NSS ERP — Post-Build Validation (PowerShell)
# =====================================================
#
# Validates that all implemented modules were built
# correctly. Does NOT execute any DDL or seed scripts -
# run 02_build.ps1 first.
#
# Authority: SOL-ARCH-010, SOL-ARCH-011
# Version: 1.0
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
$foundationTables = @("master_category","system_setting","id_sequence_master","country","document_master","field_change_log","master_data","state","district","city_village","postal_code","city_village_postal_code_map")
foreach ($t in $foundationTables) { Check-TableExists $t }

Write-Host "  Row counts:"
Check-RowCount "master_category" 11
Check-RowCount "master_data" 40
Check-RowCount "id_sequence_master" 9
Check-RowCount "country" 5
Check-RowCount "state" 112
Check-RowCount "district" 700
Check-RowCount "system_setting" 5
Check-RowCount "postal_code" 2

Write-Host "  Unique constraints:"
Check-NoDuplicates "master_category" "category_code"
Check-NoDuplicates "country" "country_code"
Check-NoDuplicates "id_sequence_master" "sequence_code"

Write-Host "  FK integrity:"
Check-FkIntegrity "master_data -> master_category" "SELECT COUNT(*) FROM nss.master_data md LEFT JOIN nss.master_category mc ON md.master_category_pk = mc.master_category_pk WHERE mc.master_category_pk IS NULL;"
Check-FkIntegrity "state -> country" "SELECT COUNT(*) FROM nss.state s LEFT JOIN nss.country c ON s.country_pk = c.country_pk WHERE c.country_pk IS NULL;"
Check-FkIntegrity "district -> state" "SELECT COUNT(*) FROM nss.district d LEFT JOIN nss.state s ON d.state_pk = s.state_pk WHERE s.state_pk IS NULL;"
Check-FkIntegrity "postal_code -> country" "SELECT COUNT(*) FROM nss.postal_code p LEFT JOIN nss.country c ON p.country_pk = c.country_pk WHERE c.country_pk IS NULL;"
Check-FkIntegrity "postal_code -> state" "SELECT COUNT(*) FROM nss.postal_code p LEFT JOIN nss.state s ON p.state_pk = s.state_pk WHERE s.state_pk IS NULL;"

Write-Host "  Deferred columns:"
Check-ColumnExists "document_master" "person_pk"
Check-ColumnExists "document_master" "uploaded_by_sangha_sevi_pk"
Write-Host ""

# Organization
Write-Host "--- Organization ---" -ForegroundColor Cyan
Write-Host "  Tables:"
Check-TableExists "organization_type_master"
Check-TableExists "organization_status_master"
Check-TableExists "organization"

Write-Host "  Row counts:"
Check-RowCount "organization_type_master" 8
Check-RowCount "organization_status_master" 6
Check-RowCount "organization" 3

Write-Host "  Unique constraints:"
Check-NoDuplicates "organization_type_master" "organization_type_code"
Check-NoDuplicates "organization_status_master" "organization_status_code"
Check-NoDuplicates "organization" "organization_code"

Write-Host "  FK integrity:"
Check-FkIntegrity "organization -> organization_type_master" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.organization_type_master otm ON o.organization_type_pk = otm.organization_type_pk WHERE otm.organization_type_pk IS NULL;"
Check-FkIntegrity "organization -> organization_status_master" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.organization_status_master osm ON o.organization_status_pk = osm.organization_status_pk WHERE osm.organization_status_pk IS NULL;"
Check-FkIntegrity "organization -> country" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.country c ON o.country_pk = c.country_pk WHERE o.country_pk IS NOT NULL AND c.country_pk IS NULL;"
Check-FkIntegrity "organization -> city_village" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.city_village cv ON o.city_village_pk = cv.city_village_pk WHERE o.city_village_pk IS NOT NULL AND cv.city_village_pk IS NULL;"
Check-FkIntegrity "organization -> postal_code" "SELECT COUNT(*) FROM nss.organization o LEFT JOIN nss.postal_code pc ON o.postal_code_pk = pc.postal_code_pk WHERE o.postal_code_pk IS NOT NULL AND pc.postal_code_pk IS NULL;"
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
