-- =====================================================
-- NSS ERP
-- Module: Person
-- File: 01_person_master_tables.sql
-- Version: 1.0
-- =====================================================

-- =====================================================
-- gender_master
-- =====================================================

INSERT INTO gender_master
(
    gender_code,
    gender_name,
    display_order
)
VALUES
('MALE', 'Male', 1),
('FEMALE', 'Female', 2),
('OTHER', 'Other', 3);

-- =====================================================
-- marital_status_master
-- =====================================================

INSERT INTO marital_status_master
(
    marital_status_code,
    marital_status_name,
    display_order
)
VALUES
('UNMARRIED', 'Unmarried', 1),
('MARRIED', 'Married', 2),
('WIDOWED', 'Widowed', 3),
('DIVORCED', 'Divorced', 4),
('SEPARATED', 'Separated', 5);

-- =====================================================
-- address_type_master
-- =====================================================

INSERT INTO address_type_master
(
    address_type_code,
    address_type_name,
    display_order
)
VALUES
('PERMANENT', 'Permanent Address', 1),
('CURRENT', 'Current Address', 2),
('OFFICIAL', 'Official Address', 3);