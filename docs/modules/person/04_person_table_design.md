# NSS ERP Person Table Design

Version: 1.0

Status: DRAFT

---

# Purpose

Defines the physical table structure for the Person Module.

Business Rules and ERD must be approved before modifying this document.

---

# Table 1: gender_master

Purpose:

Stores supported genders.

Columns:

gender_pk UUID PRIMARY KEY

gender_code VARCHAR(20) NOT NULL

gender_name VARCHAR(50) NOT NULL

display_order INTEGER NOT NULL

created_at TIMESTAMPTZ NOT NULL

is_active BOOLEAN NOT NULL DEFAULT TRUE

---

Seed Data

MALE

FEMALE

OTHER

---

Unique Constraints

gender_code

gender_name

---

# Table 2: marital_status_master

Purpose:

Stores marital status values.

Columns:

marital_status_pk UUID PRIMARY KEY

marital_status_code VARCHAR(30) NOT NULL

marital_status_name VARCHAR(100) NOT NULL

display_order INTEGER NOT NULL

created_at TIMESTAMPTZ NOT NULL

is_active BOOLEAN NOT NULL DEFAULT TRUE

---

Seed Data

UNMARRIED

MARRIED

WIDOWED

DIVORCED

SEPARATED

---

Unique Constraints

marital_status_code

marital_status_name

---

# Table 3: address_type_master

Purpose:

Stores address classifications.

Columns:

address_type_pk UUID PRIMARY KEY

address_type_code VARCHAR(30) NOT NULL

address_type_name VARCHAR(100) NOT NULL

display_order INTEGER NOT NULL

created_at TIMESTAMPTZ NOT NULL

is_active BOOLEAN NOT NULL DEFAULT TRUE

---

Seed Data

PERMANENT

CURRENT

OFFICIAL

---

Unique Constraints

address_type_code

address_type_name

---

# Table 4: person

Purpose:

Stores every individual known to NSS.

A Person may or may not be a Member.

---

Columns

person_pk UUID PRIMARY KEY

person_code VARCHAR(20) NOT NULL

first_name VARCHAR(100) NOT NULL

middle_name VARCHAR(100) NULL

last_name VARCHAR(100) NULL

gender_pk UUID NOT NULL

date_of_birth DATE NULL

mobile_number VARCHAR(20) NULL

email VARCHAR(255) NULL

marital_status_pk UUID NULL

photo_path VARCHAR(500) NULL

remarks TEXT NULL

created_at TIMESTAMPTZ NOT NULL

created_by_sangha_sevi_pk UUID NULL

updated_at TIMESTAMPTZ NULL

updated_by_sangha_sevi_pk UUID NULL

deleted_at TIMESTAMPTZ NULL

deleted_by_sangha_sevi_pk UUID NULL

is_active BOOLEAN NOT NULL DEFAULT TRUE

---

Foreign Keys

gender_pk
→ gender_master

marital_status_pk
→ marital_status_master

---

Unique Constraints

person_code

mobile_number

---

Check Constraints

At least one contact method required:

CHECK (
mobile_number IS NOT NULL
OR
email IS NOT NULL
)

---

Indexes

person_code

first_name

last_name

mobile_number

email

gender_pk

marital_status_pk

is_active

---

Business ID Examples

P00000001

P00000002

P00000003

Generated through:

id_sequence_master

---

# Table 5: person_address

Purpose:

Stores person addresses.

A Person may have multiple addresses.

---

Columns

person_address_pk UUID PRIMARY KEY

person_pk UUID NOT NULL

address_type_pk UUID NOT NULL

address_line_1 VARCHAR(200) NOT NULL

address_line_2 VARCHAR(200) NULL

district_pk UUID NOT NULL

state_pk UUID NOT NULL

country_pk UUID NOT NULL

postal_code VARCHAR(20) NULL

created_at TIMESTAMPTZ NOT NULL

updated_at TIMESTAMPTZ NULL

deleted_at TIMESTAMPTZ NULL

is_active BOOLEAN NOT NULL DEFAULT TRUE

---

Foreign Keys

person_pk
→ person

address_type_pk
→ address_type_master

district_pk
→ district_master

state_pk
→ state_master

country_pk
→ country_master

---

Indexes

person_pk

address_type_pk

district_pk

state_pk

country_pk

is_active

---

Future Tables

person_document

person_contact_history

person_merge_history

person_photo_history

These are outside Person Module v1 scope.
