-- =====================================================
-- NSS ERP
-- Module: Person
-- File: 01_person_master_tables.sql
-- Version: 1.0
-- =====================================================

-- =====================================================
-- TABLE: gender_master
-- =====================================================

CREATE TABLE gender_master
(
gender_pk UUID PRIMARY KEY
DEFAULT gen_random_uuid(),

```
gender_code VARCHAR(20) NOT NULL,

gender_name VARCHAR(50) NOT NULL,

display_order INTEGER NOT NULL,

created_at TIMESTAMPTZ NOT NULL
    DEFAULT CURRENT_TIMESTAMP,

is_active BOOLEAN NOT NULL
    DEFAULT TRUE,

CONSTRAINT uq_gender_master_code
    UNIQUE (gender_code),

CONSTRAINT uq_gender_master_name
    UNIQUE (gender_name)
```

);

CREATE INDEX idx_gender_master_active
ON gender_master (is_active);

-- =====================================================
-- TABLE: marital_status_master
-- =====================================================

CREATE TABLE marital_status_master
(
marital_status_pk UUID PRIMARY KEY
DEFAULT gen_random_uuid(),

```
marital_status_code VARCHAR(30) NOT NULL,

marital_status_name VARCHAR(100) NOT NULL,

display_order INTEGER NOT NULL,

created_at TIMESTAMPTZ NOT NULL
    DEFAULT CURRENT_TIMESTAMP,

is_active BOOLEAN NOT NULL
    DEFAULT TRUE,

CONSTRAINT uq_marital_status_code
    UNIQUE (marital_status_code),

CONSTRAINT uq_marital_status_name
    UNIQUE (marital_status_name)
```

);

CREATE INDEX idx_marital_status_active
ON marital_status_master (is_active);

-- =====================================================
-- TABLE: address_type_master
-- =====================================================

CREATE TABLE address_type_master
(
address_type_pk UUID PRIMARY KEY
DEFAULT gen_random_uuid(),

```
address_type_code VARCHAR(30) NOT NULL,

address_type_name VARCHAR(100) NOT NULL,

display_order INTEGER NOT NULL,

created_at TIMESTAMPTZ NOT NULL
    DEFAULT CURRENT_TIMESTAMP,

is_active BOOLEAN NOT NULL
    DEFAULT TRUE,

CONSTRAINT uq_address_type_code
    UNIQUE (address_type_code),

CONSTRAINT uq_address_type_name
    UNIQUE (address_type_name)
```

);

CREATE INDEX idx_address_type_active
ON address_type_master (is_active);
