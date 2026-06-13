# NSS ERP Organization Table Design

Version: 1.0

Status: DRAFT

---

# 1. organization_type_master

Purpose:

Defines organization categories.

Columns:

organization_type_pk UUID PK

organization_type_code VARCHAR(30)

organization_type_name VARCHAR(100)

display_order INTEGER

created_at TIMESTAMPTZ

is_active BOOLEAN

---

Seed Data

KENDRA

ANCHALIKA

ZILLA

SAKHA

PATHA_CHAKRA

---

Unique Constraints

organization_type_code

organization_type_name

---

# 2. organization_status_master

Purpose:

Defines organization lifecycle status.

Columns:

organization_status_pk UUID PK

status_code VARCHAR(30)

status_name VARCHAR(100)

display_order INTEGER

created_at TIMESTAMPTZ

is_active BOOLEAN

---

Seed Data

ACTIVE

INACTIVE

UNDER_FORMATION

DISSOLVED

---

Unique Constraints

status_code

status_name

---

# 3. organization

Purpose:

Stores all NSS organizational entities.

Columns:

organization_pk UUID PK

organization_id VARCHAR(20)

organization_name VARCHAR(200)

organization_type_pk UUID FK

parent_organization_pk UUID FK

organization_status_pk UUID FK

established_date DATE

remarks TEXT

created_at TIMESTAMPTZ

created_by_sangha_sevi_pk UUID

updated_at TIMESTAMPTZ

updated_by_sangha_sevi_pk UUID

deleted_at TIMESTAMPTZ

deleted_by_sangha_sevi_pk UUID

is_active BOOLEAN

---

Unique Constraints

organization_id

(parent_organization_pk, organization_name)

---

Business Rules

Only one active KENDRA

ANCHALIKA parent = KENDRA

ZILLA parent = KENDRA

SAKHA parent = ANCHALIKA or ZILLA

PATHA_CHAKRA parent = KENDRA

---

Indexes

organization_id

organization_name

organization_type_pk

parent_organization_pk

organization_status_pk

---

# 4. organization_address

Purpose:

Stores organization address details.

Columns:

organization_address_pk UUID PK

organization_pk UUID FK

address_line_1 VARCHAR(200)

address_line_2 VARCHAR(200)

district_pk UUID FK

state_pk UUID FK

country_pk UUID FK

postal_code VARCHAR(20)

created_at TIMESTAMPTZ

created_by_sangha_sevi_pk UUID

updated_at TIMESTAMPTZ

updated_by_sangha_sevi_pk UUID

deleted_at TIMESTAMPTZ

deleted_by_sangha_sevi_pk UUID

is_active BOOLEAN

---

Indexes

organization_pk

district_pk

state_pk

country_pk

---

Future Tables

organization_contact

organization_history

organization_document

organization_asset

organization_office_bearer
