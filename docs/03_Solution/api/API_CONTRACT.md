# NSS ERP — API Contract Reference

---

## Document Metadata

| Item | Value |
|---|---|
| Document Name | API Contract Reference |
| Document ID | SOL-API-001 |
| Domain | Cross-Module |
| Repository Path | docs/03_Solution/api/API_CONTRACT.md |
| Version | 1.0.0 |
| Status | Draft |
| Authority | NSS ERP Architecture |
| Effective Date | TBD |

---

# 1. Overview

The NSS ERP exposes a **read-only REST API** for data verification.
All endpoints are `GET` requests. No authentication is enforced (deferred
to Tier 5). The API connects as `nss_db_backend` with SELECT-only
privileges on the `nss.*` schema.

**Base URL:** `http://localhost:8001`

**API prefix:** `/api/v1/<module>`

**Content type:** `application/json`

---

# 2. Common Conventions

## 2.1 Pagination

All list endpoints support:

| Parameter | Type | Default | Constraint |
|---|---|---|---|
| `limit` | int | 100 | 1 ≤ limit ≤ 500 |
| `offset` | int | 0 | offset ≥ 0 |

- `limit=0` or `limit > 500` → `422 Unprocessable Entity`
- `offset=-1` → `422`
- `offset` beyond total rows → empty list `[]`, not error

## 2.2 Error Responses

| Status | Meaning |
|---|---|
| 200 | Success |
| 404 | Resource not found (valid UUID, no match) |
| 422 | Validation error (bad UUID, bad parameter) |
| 429 | Rate limit exceeded |

## 2.3 Audit Column Exclusion

No endpoint returns audit columns:

```text
created_at, updated_at, deleted_at,
created_by_sangha_sevi_pk, updated_by_sangha_sevi_pk, deleted_by_sangha_sevi_pk
```

## 2.4 Sensitive Data

- `aadhaar_encrypted` and `aadhaar_hash` are never returned.
- `aadhaar_last4` appears only in Person detail, not list/search.

## 2.5 UUID Path Parameters

All `{pk}` parameters expect a valid UUID v4. Malformed UUIDs return `422`.

---

# 3. Tier 0 — Bootstrap

**Router prefix:** `/api/v1/bootstrap`

| # | Method | Path | Description | Response Model |
|---|---|---|---|---|
| 1 | GET | `/health` | Database connectivity check | `HealthResponse` |
| 2 | GET | `/roles` | List RBAC roles | `list[RoleResponse]` |
| 3 | GET | `/permissions` | List RBAC permissions | `list[PermissionResponse]` |
| 4 | GET | `/roles/{role_pk}/permissions` | Permissions assigned to a role (404 if role not found) | `list[PermissionResponse]` |

---

# 4. Tier 1 — Foundation

**Router prefix:** `/api/v1/foundation`

| # | Method | Path | Filters | Description | Response Model |
|---|---|---|---|---|---|
| 5 | GET | `/categories` | — | List master categories | `list[CategoryResponse]` |
| 6 | GET | `/categories/{pk}` | — | Category detail | `CategoryResponse` |
| 7 | GET | `/master-data` | `category_code`, `limit`, `offset` | List master data | `list[MasterDataResponse]` |
| 8 | GET | `/master-data/{pk}` | — | Master data detail | `MasterDataResponse` |
| 9 | GET | `/settings` | — | List system settings | `list[SettingResponse]` |
| 10 | GET | `/settings/{key}` | — | Setting by key | `SettingResponse` |
| 11 | GET | `/sequences` | — | List ID sequences | `list[SequenceResponse]` |
| 12 | GET | `/countries` | — | List countries | `list[CountryResponse]` |
| 13 | GET | `/countries/{pk}` | — | Country detail | `CountryResponse` |
| 14 | GET | `/states` | `country_pk`, `limit`, `offset` | List states | `list[StateResponse]` |
| 15 | GET | `/states/{pk}` | — | State detail | `StateResponse` |
| 16 | GET | `/districts` | `state_pk`, `limit`, `offset` | List districts | `list[DistrictResponse]` |
| 17 | GET | `/districts/{pk}` | — | District detail | `DistrictResponse` |
| 18 | GET | `/cities` | `district_pk`, `limit`, `offset` | List cities/villages | `list[CityVillageResponse]` |
| 19 | GET | `/postal-codes` | `district_pk`, `limit`, `offset` | List postal codes | `list[PostalCodeResponse]` |
| 20 | GET | `/postal-code-mappings` | `postal_code_pk`, `city_village_pk`, `limit`, `offset` | List postal code mappings | `list[PostalCodeMappingResponse]` |
| 21 | GET | `/documents` | `category_code`, `limit`, `offset` | List document masters | `list[DocumentResponse]` |

---

# 5. Tier 2 — Organization

**Router prefix:** `/api/v1/organization`

| # | Method | Path | Filters | Description | Response Model |
|---|---|---|---|---|---|
| 22 | GET | `/types` | — | List organization types | `list[OrganizationTypeResponse]` |
| 23 | GET | `/statuses` | — | List lifecycle statuses | `list[StatusResponse]` |
| 24 | GET | `/organizations` | `type_code`, `status_code`, `limit`, `offset` | List organizations | `list[OrganizationResponse]` |
| 25 | GET | `/organizations/{pk}` | — | Organization detail | `OrganizationResponse` |
| 26 | GET | `/organizations/{pk}/children` | — | Direct children of org | `list[OrganizationResponse]` |
| 27 | GET | `/hierarchy` | `limit`, `offset` | Recursive org tree | `list[OrganizationHierarchyNodeResponse]` |

---

# 6. Tier 3 — Person

**Router prefix:** `/api/v1/person`

| # | Method | Path | Filters | Description | Response Model |
|---|---|---|---|---|---|
| 28 | GET | `/persons` | `gender_code`, `marital_status_code`, `blood_group_code`, `limit`, `offset` | List persons (summary) | `list[PersonSummaryResponse]` |
| 29 | GET | `/persons/{pk}` | — | Person detail (with aadhaar_last4) | `PersonDetailResponse` |
| 30 | GET | `/persons/{pk}/addresses` | — | Person addresses | `list[PersonAddressResponse]` |
| 31 | GET | `/search?q=` | `q` (min 2 chars, required) | Trigram + prefix search across name + ID + contact | `list[PersonSummaryResponse]` (max 50) |

**Security notes:**

- Summary endpoints exclude `aadhaar_last4`, `aadhaar_encrypted`, `aadhaar_hash`
- Detail includes `aadhaar_last4` (masked in UI as `XXXX XXXX <last4>`)
- `aadhaar_encrypted` and `aadhaar_hash` are never exposed via API

---

# 7. Tier 4 — Family

**Router prefix:** `/api/v1/family`

| # | Method | Path | Filters | Description | Response Model |
|---|---|---|---|---|---|
| 32 | GET | `/families` | `sakha_code`, `status_code`, `limit`, `offset` | List families | `list[FamilyGroupResponse]` |
| 33 | GET | `/families/{pk}` | — | Family detail | `FamilyGroupResponse` |
| 34 | GET | `/families/{pk}/members` | — | Current family members | `list[FamilyMemberResponse]` |
| 35 | GET | `/families/{pk}/head-history` | — | Family head history | `list[FamilyHeadHistoryResponse]` |

**Notes:**

- Members endpoint returns only `is_current=TRUE` relationships
- Head history ordered by `effective_from DESC` (most recent first)
- Sub-resource endpoints return `404` if the parent family does not exist

---

# 8. Tier 4 — Membership

**Router prefix:** `/api/v1/membership`

| # | Method | Path | Filters | Description | Response Model |
|---|---|---|---|---|---|
| 36 | GET | `/members` | `type_code`, `status_code`, `org_code`, `limit`, `offset` | List members | `list[MemberResponse]` |
| 37 | GET | `/members/{pk}` | — | Member detail | `MemberResponse` |
| 38 | GET | `/search?q=` | `q` (min 2 chars, required) | Trigram + prefix search across all 3 identity tiers + name + contact | `list[MemberResponse]` (max 50) |
| 39 | GET | `/members/{pk}/affiliations` | — | Sakha affiliation history | `list[SakhaAffiliationResponse]` |
| 40 | GET | `/members/{pk}/parichaya-patra` | — | Parichaya Patra records | `list[ParichayaPatraResponse]` |
| 41 | GET | `/members/{pk}/anumati-patra` | — | Anumati Patra records | `list[AnumatiPatraResponse]` |
| 42 | GET | `/members/{pk}/journey` | — | Journey events (chronological) | `list[JourneyEventResponse]` |

**Search fields (endpoint #31 — Person):**

| Field | Match Type | Source Table |
|---|---|---|
| `person_id` (P1) | Prefix (ILIKE) | `person` |
| `first_name`, `last_name` | Trigram (`pg_trgm`, threshold 0.45) | `person` |
| `mobile_number` | Prefix (ILIKE) | `person` |
| `email` | Prefix (ILIKE) | `person` |

**Search fields (endpoint #38 — Membership):**

| Field | Match Type | Source Table |
|---|---|---|
| `sangha_sevi_id` (SS1) | Prefix (ILIKE) | `sangha_sevi` |
| `person_id` (P1) | Prefix (ILIKE) | `person` |
| `local_sakha_erp_id` (ESS1192) | Prefix (ILIKE) | `membership_sakha_affiliation` (active) |
| `first_name`, `last_name` | Trigram (`pg_trgm`) | `person` |
| `mobile_number` | Prefix (ILIKE) | `person` |
| `email` | Prefix (ILIKE) | `person` |
| `document_number` (345/2026/2027) | Prefix (ILIKE) | `parichaya_patra` (any status) |

**Three-tier identity in responses:**

```text
Tier 1: sangha_sevi_id        — on MemberResponse (permanent)
Tier 2: local_sakha_erp_id    — on MemberResponse (current, from active affiliation)
                                 on SakhaAffiliationResponse (per-period)
                                 on ParichayaPatraResponse (snapshot at issuance)
Tier 3: document_number       — on ParichayaPatraResponse (Kendra Number)
```

**Notes:**

- Email-like queries (containing `.` or `@`) use `re.split(r'[.@]', q)[0]` for
  trigram comparison parameters, preventing false positives (e.g. "aniket.mishra"
  would otherwise trigram-match "Ramesh Mishra" via the surname component)
- Affiliations ordered by `effective_from DESC`
- Parichaya Patra ordered by `valid_from DESC`
- Anumati Patra ordered by `valid_from DESC` — includes EXPIRED records for members
  who progressed from Probationary to Regular
- Journey events ordered by `event_date ASC` (chronological)
- Sub-resource endpoints return `404` if the parent member does not exist
- `membership_type_code` is returned as `PROBATIONARY` (UI displays as "Darshaka")

---

# 9. Frontend Routes

| Path | Description | HTML File |
|---|---|---|
| `/` | Bootstrap Verification UI | `index.html` |
| `/foundation` | Foundation Verification UI | `foundation.html` |
| `/organization` | Organization Verification UI | `organization.html` |
| `/person` | Person Verification UI | `person.html` |
| `/family` | Family Verification UI | `family.html` |
| `/membership` | Membership Verification UI | `membership.html` |
| `/docs` | Swagger UI (OpenAPI) | auto-generated |
| `/redoc` | ReDoc | auto-generated |

Frontend routes are excluded from OpenAPI schema (`include_in_schema=False`).

`/docs` and `/redoc` can be disabled via `DISABLE_DOCS=true` environment variable.

---

# 10. Endpoint Count Summary

| Tier | Module | Endpoints |
|---|---|---|
| 0 | Bootstrap | 4 |
| 1 | Foundation | 17 |
| 2 | Organization | 6 |
| 3 | Person | 4 |
| 4 | Family | 4 |
| 4 | Membership | 7 |
| **Total** | | **42** |

---

# End of Document
