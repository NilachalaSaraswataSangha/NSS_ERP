# database/seed/01_foundation/

Foundation Module seed data — initial reference values required before
any downstream module can operate.

Authority: SOL-FND-004 §29–§31, SOL-ARCH-010 §8

## Seed Execution Order

Execute AFTER all DDL in `database/ddl/01_foundation/` has completed.
Files must be run in numeric order (each may depend on data from earlier files).

| # | File | Seeds Into | Depends On |
|--:|------|-----------|-----------|
| 01 | `01_master_category.sql` | `master_category` | DDL complete |
| 02 | `02_master_data.sql` | `master_data` | `01_master_category.sql` |
| 03 | `03_id_sequence_master.sql` | `id_sequence_master` | DDL complete |
| 04 | `04_country.sql` | `country` | DDL complete |
| 05 | `05_state.sql` | `state` | `04_country.sql` |
| 06 | `06_district.sql` | `district` | `05_state.sql` |
| 07 | `07_system_setting.sql` | `system_setting` | DDL complete |

## Execution Command

```bash
# As NSS_ADMIN against the nss_erp database:
for f in database/seed/01_foundation/0*.sql; do
    psql -U nss_admin -d nss_erp -f "$f"
done
```

## Seed Categories

Categories seeded in `01_master_category.sql`:

```
GENDER, RELATIONSHIP_TYPE, MEMBERSHIP_TYPE, MEMBERSHIP_STATUS,
LOGIN_ROLE, STATUS_REASON, WORKFLOW_STATUS, DOCUMENT_TYPE,
APPLICATION_TYPE, MARITAL_STATUS, ADDRESS_TYPE
```

## Geographic Seed Scope

- Countries: India, US, GB, AU, CA (5)
- States/Provinces/Territories:
  - India: all 28 states + 8 Union Territories (36)
  - US: all 50 states + DC (51)
  - UK: 4 countries/regions
  - Australia: 6 states + 2 territories (8)
  - Canada: 10 provinces + 3 territories (13)
  - **Total: 112 state-level entries**
- Districts (India only — all districts for all states/UTs):
  - Odisha: 30, AP: 26, Arunachal: 26, Assam: 35, Bihar: 38,
    Chhattisgarh: 33, Goa: 2, Gujarat: 33, Haryana: 22, HP: 12,
    Jharkhand: 24, Karnataka: 31, Kerala: 14, MP: 55, Maharashtra: 36,
    Manipur: 16, Meghalaya: 12, Mizoram: 11, Nagaland: 16, Punjab: 23,
    Rajasthan: 50, Sikkim: 6, TN: 38, Telangana: 33, Tripura: 8,
    UP: 75, Uttarakhand: 13, WB: 23, Delhi: 11, J&K: 20, Ladakh: 2,
    Chandigarh: 1, Puducherry: 4, A&N: 3, DN/DD: 3, Lakshadweep: 1
  - **Total: ~770 district-level entries**
- Cities/Villages: none seeded (populated during deployment or data migration)
- Non-India countries: district-level populated at runtime as needed

## Notes

- Seed data uses `CROSS JOIN ... VALUES` with subqueries to resolve parent PKs
  by code — no hardcoded UUIDs.
- Additional categories and values will be added by downstream module seeds
  (e.g., Organization adds organization-type values to `master_data`).
