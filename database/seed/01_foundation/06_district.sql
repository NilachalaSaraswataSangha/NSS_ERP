-- =====================================================
-- NSS ERP
-- Module: Foundation
-- Seed File: 06_district.sql
-- Version: 5.1 — ON CONFLICT DO NOTHING, not DO UPDATE (2026-10-05): a
--          re-run must never overwrite a district row an admin has edited
--          or approved via the geo-approval workflow. Insert-if-missing only.
-- Authority: SOL-ARCH-010 Amendment (Simplified Geography Model, 2026-10-02)
-- Owner: NSS_ERP_ADMIN
-- Source: 4 government LGD files (Village, Urban, District, ULB), 2026-10-01/02.
-- Note: All-India districts keyed on the numeric LGD district code. district_code is globally unique so city_village can resolve district by code (not fragile name match).
-- =====================================================

-- ---- AN — 3 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('603', 'Nicobars', 1),
    ('632', 'North And Middle Andaman', 2),
    ('602', 'South Andamans', 3)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'AN'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- AP — 28 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('745', 'Alluri Sitharama Raju', 1),
    ('744', 'Anakapalli', 2),
    ('502', 'Ananthapuramu', 3),
    ('753', 'Annamayya', 4),
    ('750', 'Bapatla', 5),
    ('503', 'Chittoor', 6),
    ('747', 'Dr. B.R. Ambedkar Konaseema', 7),
    ('505', 'East Godavari', 8),
    ('748', 'Eluru', 9),
    ('506', 'Guntur', 10),
    ('746', 'Kakinada', 11),
    ('510', 'Krishna', 12),
    ('511', 'Kurnool', 13),
    ('790', 'Markapuram', 14),
    ('755', 'Nandyal', 15),
    ('749', 'Ntr', 16),
    ('751', 'Palnadu', 17),
    ('743', 'Parvathipuram Manyam', 18),
    ('791', 'Polavaram', 19),
    ('517', 'Prakasam', 20),
    ('515', 'Sri Potti Sriramulu Nellore', 21),
    ('754', 'Sri Sathya Sai', 22),
    ('519', 'Srikakulam', 23),
    ('752', 'Tirupati', 24),
    ('520', 'Visakhapatnam', 25),
    ('521', 'Vizianagaram', 26),
    ('523', 'West Godavari', 27),
    ('504', 'Y.S.R. Kadapa', 28)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'AP'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- AR — 27 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('628', 'Anjaw', 1),
    ('787', 'Bichom', 2),
    ('229', 'Changlang', 3),
    ('230', 'Dibang Valley', 4),
    ('231', 'East Kameng', 5),
    ('232', 'East Siang', 6),
    ('718', 'Kamle', 7),
    ('786', 'Keyi Panyor', 8),
    ('677', 'Kra Daadi', 9),
    ('233', 'Kurung Kumey', 10),
    ('724', 'Leparada', 11),
    ('234', 'Lohit', 12),
    ('666', 'Longding', 13),
    ('235', 'Lower Dibang Valley', 14),
    ('719', 'Lower Siang', 15),
    ('236', 'Lower Subansiri', 16),
    ('678', 'Namsai', 17),
    ('723', 'Pakke Kessang', 18),
    ('237', 'Papum Pare', 19),
    ('725', 'Shi Yomi', 20),
    ('679', 'Siang', 21),
    ('238', 'Tawang', 22),
    ('239', 'Tirap', 23),
    ('240', 'Upper Siang', 24),
    ('241', 'Upper Subansiri', 25),
    ('242', 'West Kameng', 26),
    ('243', 'West Siang', 27)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'AR'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- AS — 35 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('739', 'Bajali', 1),
    ('616', 'Baksa', 2),
    ('280', 'Barpeta', 3),
    ('705', 'Biswanath', 4),
    ('281', 'Bongaigaon', 5),
    ('282', 'Cachar', 6),
    ('708', 'Charaideo', 7),
    ('612', 'Chirang', 8),
    ('283', 'Darrang', 9),
    ('284', 'Dhemaji', 10),
    ('285', 'Dhubri', 11),
    ('286', 'Dibrugarh', 12),
    ('299', 'Dima Hasao', 13),
    ('287', 'Goalpara', 14),
    ('288', 'Golaghat', 15),
    ('289', 'Hailakandi', 16),
    ('709', 'Hojai', 17),
    ('290', 'Jorhat', 18),
    ('291', 'Kamrup', 19),
    ('618', 'Kamrup Metro', 20),
    ('292', 'Karbi Anglong', 21),
    ('294', 'Kokrajhar', 22),
    ('295', 'Lakhimpur', 23),
    ('706', 'Majuli', 24),
    ('296', 'Marigaon', 25),
    ('297', 'Nagaon', 26),
    ('298', 'Nalbari', 27),
    ('300', 'Sivasagar', 28),
    ('301', 'Sonitpur', 29),
    ('707', 'South Salmara Mancachar', 30),
    ('293', 'Sribhumi', 31),
    ('756', 'Tamulpur', 32),
    ('302', 'Tinsukia', 33),
    ('617', 'Udalguri', 34),
    ('710', 'West Karbi Anglong', 35)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'AS'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- BR — 38 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('188', 'Araria', 1),
    ('611', 'Arwal', 2),
    ('189', 'Aurangabad', 3),
    ('190', 'Banka', 4),
    ('191', 'Begusarai', 5),
    ('192', 'Bhagalpur', 6),
    ('193', 'Bhojpur', 7),
    ('194', 'Buxar', 8),
    ('195', 'Darbhanga', 9),
    ('196', 'Gaya', 10),
    ('197', 'Gopalganj', 11),
    ('198', 'Jamui', 12),
    ('199', 'Jehanabad', 13),
    ('200', 'Kaimur (Bhabua)', 14),
    ('201', 'Katihar', 15),
    ('202', 'Khagaria', 16),
    ('203', 'Kishanganj', 17),
    ('204', 'Lakhisarai', 18),
    ('205', 'Madhepura', 19),
    ('206', 'Madhubani', 20),
    ('207', 'Munger', 21),
    ('208', 'Muzaffarpur', 22),
    ('209', 'Nalanda', 23),
    ('210', 'Nawada', 24),
    ('211', 'Pashchim Champaran', 25),
    ('212', 'Patna', 26),
    ('213', 'Purbi Champaran', 27),
    ('214', 'Purnia', 28),
    ('215', 'Rohtas', 29),
    ('216', 'Saharsa', 30),
    ('217', 'Samastipur', 31),
    ('218', 'Saran', 32),
    ('219', 'Sheikhpura', 33),
    ('220', 'Sheohar', 34),
    ('221', 'Sitamarhi', 35),
    ('222', 'Siwan', 36),
    ('223', 'Supaul', 37),
    ('224', 'Vaishali', 38)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'BR'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- CG — 33 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('646', 'Balod', 1),
    ('644', 'Balodabazar-Bhatapara', 2),
    ('649', 'Balrampur-Ramanujganj', 3),
    ('374', 'Bastar', 4),
    ('650', 'Bemetara', 5),
    ('636', 'Bijapur', 6),
    ('375', 'Bilaspur', 7),
    ('376', 'Dakshin Bastar Dantewada', 8),
    ('377', 'Dhamtari', 9),
    ('378', 'Durg', 10),
    ('645', 'Gariyaband', 11),
    ('734', 'Gaurela-Pendra-Marwahi', 12),
    ('379', 'Janjgir-Champa', 13),
    ('380', 'Jashpur', 14),
    ('382', 'Kabeerdham', 15),
    ('759', 'Khairagarh-Chhuikhadan-Gandai', 16),
    ('643', 'Kondagaon', 17),
    ('383', 'Korba', 18),
    ('384', 'Korea', 19),
    ('385', 'Mahasamund', 20),
    ('760', 'Manendragarh-Chirmiri-Bharatpur(M C B)', 21),
    ('761', 'Mohla-Manpur-Ambagarh Chouki', 22),
    ('647', 'Mungeli', 23),
    ('637', 'Narayanpur', 24),
    ('386', 'Raigarh', 25),
    ('387', 'Raipur', 26),
    ('388', 'Rajnandgaon', 27),
    ('762', 'Sakti', 28),
    ('763', 'Sarangarh-Bilaigarh', 29),
    ('642', 'Sukma', 30),
    ('648', 'Surajpur', 31),
    ('389', 'Surguja', 32),
    ('381', 'Uttar Bastar Kanker', 33)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'CG'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- CH — 1 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('44', 'Chandigarh', 1)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'CH'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- DL — 14 districts ----
-- 2026-10-02: added Shahdara (LGD code 671) — the original 13-row load
-- omitted it; two live orphan PINs (110095, 110151) carry district
-- "SHAHDARA" in the India Post directory with no match until this row
-- exists (SOL-ARCH-010 Amendment, urban-recovery follow-up).
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('77', 'Central', 1),
    ('796', 'Central North', 2),
    ('78', 'East', 3),
    ('79', 'New Delhi', 4),
    ('80', 'North', 5),
    ('81', 'North East', 6),
    ('82', 'North West', 7),
    ('795', 'Old Delhi', 8),
    ('794', 'Outer North', 9),
    ('83', 'South', 10),
    ('670', 'South East', 11),
    ('84', 'South West', 12),
    ('85', 'West', 13),
    ('671', 'Shahdara', 14)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'DL'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- DN — 3 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('465', 'Dadra And Nagar Haveli', 1),
    ('463', 'Daman', 2),
    ('464', 'Diu', 3)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'DN'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- GA — 3 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('793', 'Kushavati', 1),
    ('551', 'North Goa', 2),
    ('552', 'South Goa', 3)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'GA'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- GJ — 34 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('438', 'Ahmedabad', 1),
    ('439', 'Amreli', 2),
    ('440', 'Anand', 3),
    ('672', 'Arvalli', 4),
    ('441', 'Banas Kantha', 5),
    ('442', 'Bharuch', 6),
    ('443', 'Bhavnagar', 7),
    ('676', 'Botad', 8),
    ('668', 'Chhotaudepur', 9),
    ('445', 'Dahod', 10),
    ('444', 'Dangs', 11),
    ('674', 'Devbhumi Dwarka', 12),
    ('446', 'Gandhinagar', 13),
    ('675', 'Gir Somnath', 14),
    ('447', 'Jamnagar', 15),
    ('448', 'Junagadh', 16),
    ('449', 'Kachchh', 17),
    ('450', 'Kheda', 18),
    ('451', 'Mahesana', 19),
    ('669', 'Mahisagar', 20),
    ('673', 'Morbi', 21),
    ('452', 'Narmada', 22),
    ('453', 'Navsari', 23),
    ('454', 'Panch Mahals', 24),
    ('455', 'Patan', 25),
    ('456', 'Porbandar', 26),
    ('457', 'Rajkot', 27),
    ('458', 'Sabar Kantha', 28),
    ('459', 'Surat', 29),
    ('460', 'Surendranagar', 30),
    ('641', 'Tapi', 31),
    ('461', 'Vadodara', 32),
    ('462', 'Valsad', 33),
    ('789', 'Vav-Tharad', 34)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'GJ'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- HP — 12 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('15', 'Bilaspur', 1),
    ('16', 'Chamba', 2),
    ('17', 'Hamirpur', 3),
    ('18', 'Kangra', 4),
    ('19', 'Kinnaur', 5),
    ('20', 'Kullu', 6),
    ('21', 'Lahaul And Spiti', 7),
    ('22', 'Mandi', 8),
    ('23', 'Shimla', 9),
    ('24', 'Sirmaur', 10),
    ('25', 'Solan', 11),
    ('26', 'Una', 12)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'HP'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- HR — 23 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('58', 'Ambala', 1),
    ('59', 'Bhiwani', 2),
    ('701', 'Charkhi Dadri', 3),
    ('60', 'Faridabad', 4),
    ('61', 'Fatehabad', 5),
    ('62', 'Gurugram', 6),
    ('792', 'Hansi', 7),
    ('63', 'Hisar', 8),
    ('64', 'Jhajjar', 9),
    ('65', 'Jind', 10),
    ('66', 'Kaithal', 11),
    ('67', 'Karnal', 12),
    ('68', 'Kurukshetra', 13),
    ('69', 'Mahendragarh', 14),
    ('604', 'Nuh', 15),
    ('619', 'Palwal', 16),
    ('70', 'Panchkula', 17),
    ('71', 'Panipat', 18),
    ('72', 'Rewari', 19),
    ('73', 'Rohtak', 20),
    ('74', 'Sirsa', 21),
    ('75', 'Sonipat', 22),
    ('76', 'Yamunanagar', 23)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'HR'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- JH — 24 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('322', 'Bokaro', 1),
    ('323', 'Chatra', 2),
    ('324', 'Deoghar', 3),
    ('325', 'Dhanbad', 4),
    ('326', 'Dumka', 5),
    ('327', 'East Singhbum', 6),
    ('328', 'Garhwa', 7),
    ('329', 'Giridih', 8),
    ('330', 'Godda', 9),
    ('331', 'Gumla', 10),
    ('332', 'Hazaribagh', 11),
    ('333', 'Jamtara', 12),
    ('606', 'Khunti', 13),
    ('334', 'Koderma', 14),
    ('335', 'Latehar', 15),
    ('336', 'Lohardaga', 16),
    ('337', 'Pakur', 17),
    ('338', 'Palamu', 18),
    ('607', 'Ramgarh', 19),
    ('339', 'Ranchi', 20),
    ('340', 'Sahebganj', 21),
    ('341', 'Saraikela Kharsawan', 22),
    ('342', 'Simdega', 23),
    ('343', 'West Singhbhum', 24)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'JH'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- JK — 20 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('1', 'Anantnag', 1),
    ('623', 'Bandipora', 2),
    ('3', 'Baramulla', 3),
    ('2', 'Budgam', 4),
    ('4', 'Doda', 5),
    ('626', 'Ganderbal', 6),
    ('5', 'Jammu', 7),
    ('7', 'Kathua', 8),
    ('620', 'Kishtwar', 9),
    ('622', 'Kulgam', 10),
    ('8', 'Kupwara', 11),
    ('10', 'Poonch', 12),
    ('11', 'Pulwama', 13),
    ('12', 'Rajouri', 14),
    ('621', 'Ramban', 15),
    ('627', 'Reasi', 16),
    ('624', 'Samba', 17),
    ('625', 'Shopian', 18),
    ('13', 'Srinagar', 19),
    ('14', 'Udhampur', 20)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'JK'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- KA — 31 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('524', 'Bagalkote', 1),
    ('528', 'Ballari', 2),
    ('527', 'Belagavi', 3),
    ('526', 'Bengaluru Rural', 4),
    ('631', 'Bengaluru South', 5),
    ('525', 'Bengaluru Urban', 6),
    ('529', 'Bidar', 7),
    ('531', 'Chamarajanagar', 8),
    ('630', 'Chikkaballapura', 9),
    ('532', 'Chikkamagaluru', 10),
    ('533', 'Chitradurga', 11),
    ('534', 'Dakshina Kannada', 12),
    ('535', 'Davanagere', 13),
    ('536', 'Dharwad', 14),
    ('537', 'Gadag', 15),
    ('539', 'Hassan', 16),
    ('540', 'Haveri', 17),
    ('538', 'Kalaburagi', 18),
    ('541', 'Kodagu', 19),
    ('542', 'Kolar', 20),
    ('543', 'Koppal', 21),
    ('544', 'Mandya', 22),
    ('545', 'Mysuru', 23),
    ('546', 'Raichur', 24),
    ('547', 'Shivamogga', 25),
    ('548', 'Tumakuru', 26),
    ('549', 'Udupi', 27),
    ('550', 'Uttara Kannada', 28),
    ('738', 'Vijayanagara', 29),
    ('530', 'Vijayapura', 30),
    ('635', 'Yadgir', 31)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'KA'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- KL — 14 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('554', 'Alappuzha', 1),
    ('555', 'Ernakulam', 2),
    ('556', 'Idukki', 3),
    ('557', 'Kannur', 4),
    ('558', 'Kasaragod', 5),
    ('559', 'Kollam', 6),
    ('560', 'Kottayam', 7),
    ('561', 'Kozhikode', 8),
    ('562', 'Malappuram', 9),
    ('563', 'Palakkad', 10),
    ('564', 'Pathanamthitta', 11),
    ('565', 'Thiruvananthapuram', 12),
    ('566', 'Thrissur', 13),
    ('567', 'Wayanad', 14)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'KL'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- LA — 2 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('6', 'Kargil', 1),
    ('9', 'Leh Ladakh', 2)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'LA'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- LD — 1 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('553', 'Lakshadweep District', 1)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'LD'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- MH — 36 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('466', 'Ahilyanagar', 1),
    ('467', 'Akola', 2),
    ('468', 'Amravati', 3),
    ('470', 'Beed', 4),
    ('471', 'Bhandara', 5),
    ('472', 'Buldhana', 6),
    ('473', 'Chandrapur', 7),
    ('469', 'Chhatrapati Sambhajinagar', 8),
    ('488', 'Dharashiv', 9),
    ('474', 'Dhule', 10),
    ('475', 'Gadchiroli', 11),
    ('476', 'Gondia', 12),
    ('477', 'Hingoli', 13),
    ('478', 'Jalgaon', 14),
    ('479', 'Jalna', 15),
    ('480', 'Kolhapur', 16),
    ('481', 'Latur', 17),
    ('482', 'Mumbai', 18),
    ('483', 'Mumbai Suburban', 19),
    ('484', 'Nagpur', 20),
    ('485', 'Nanded', 21),
    ('486', 'Nandurbar', 22),
    ('487', 'Nashik', 23),
    ('665', 'Palghar', 24),
    ('489', 'Parbhani', 25),
    ('490', 'Pune', 26),
    ('491', 'Raigad', 27),
    ('492', 'Ratnagiri', 28),
    ('493', 'Sangli', 29),
    ('494', 'Satara', 30),
    ('495', 'Sindhudurg', 31),
    ('496', 'Solapur', 32),
    ('497', 'Thane', 33),
    ('498', 'Wardha', 34),
    ('499', 'Washim', 35),
    ('500', 'Yavatmal', 36)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'MH'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- ML — 12 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('273', 'East Garo Hills', 1),
    ('657', 'East Jaintia Hills', 2),
    ('274', 'East Khasi Hills', 3),
    ('740', 'Eastern West Khasi Hills', 4),
    ('656', 'North Garo Hills', 5),
    ('276', 'Ri Bhoi', 6),
    ('277', 'South Garo Hills', 7),
    ('663', 'South West Garo Hills', 8),
    ('658', 'South West Khasi Hills', 9),
    ('278', 'West Garo Hills', 10),
    ('275', 'West Jaintia Hills', 11),
    ('279', 'West Khasi Hills', 12)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'ML'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- MN — 16 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('252', 'Bishnupur', 1),
    ('253', 'Chandel', 2),
    ('254', 'Churachandpur', 3),
    ('255', 'Imphal East', 4),
    ('256', 'Imphal West', 5),
    ('713', 'Jiribam', 6),
    ('711', 'Kakching', 7),
    ('717', 'Kamjong', 8),
    ('712', 'Kangpokpi', 9),
    ('714', 'Noney', 10),
    ('715', 'Pherzawl', 11),
    ('257', 'Senapati', 12),
    ('258', 'Tamenglong', 13),
    ('716', 'Tengnoupal', 14),
    ('259', 'Thoubal', 15),
    ('260', 'Ukhrul', 16)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'MN'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- MP — 55 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('667', 'Agar-Malwa', 1),
    ('639', 'Alirajpur', 2),
    ('390', 'Anuppur', 3),
    ('391', 'Ashoknagar', 4),
    ('392', 'Balaghat', 5),
    ('393', 'Barwani', 6),
    ('394', 'Betul', 7),
    ('395', 'Bhind', 8),
    ('396', 'Bhopal', 9),
    ('397', 'Burhanpur', 10),
    ('398', 'Chhatarpur', 11),
    ('399', 'Chhindwara', 12),
    ('400', 'Damoh', 13),
    ('401', 'Datia', 14),
    ('402', 'Dewas', 15),
    ('403', 'Dhar', 16),
    ('404', 'Dindori', 17),
    ('406', 'Guna', 18),
    ('407', 'Gwalior', 19),
    ('408', 'Harda', 20),
    ('410', 'Indore', 21),
    ('411', 'Jabalpur', 22),
    ('412', 'Jhabua', 23),
    ('413', 'Katni', 24),
    ('405', 'Khandwa (East Nimar)', 25),
    ('414', 'Khargone (West Nimar)', 26),
    ('766', 'MAUGANJ', 27),
    ('784', 'Maihar', 28),
    ('415', 'Mandla', 29),
    ('416', 'Mandsaur', 30),
    ('417', 'Morena', 31),
    ('409', 'Narmadapuram', 32),
    ('418', 'Narsimhapur', 33),
    ('419', 'Neemuch', 34),
    ('722', 'Niwari', 35),
    ('785', 'Pandhurna', 36),
    ('420', 'Panna', 37),
    ('421', 'Raisen', 38),
    ('422', 'Rajgarh', 39),
    ('423', 'Ratlam', 40),
    ('424', 'Rewa', 41),
    ('425', 'Sagar', 42),
    ('426', 'Satna', 43),
    ('427', 'Sehore', 44),
    ('428', 'Seoni', 45),
    ('429', 'Shahdol', 46),
    ('430', 'Shajapur', 47),
    ('431', 'Sheopur', 48),
    ('432', 'Shivpuri', 49),
    ('433', 'Sidhi', 50),
    ('638', 'Singrauli', 51),
    ('434', 'Tikamgarh', 52),
    ('435', 'Ujjain', 53),
    ('436', 'Umaria', 54),
    ('437', 'Vidisha', 55)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'MP'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- MZ — 11 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('261', 'Aizawl', 1),
    ('262', 'Champhai', 2),
    ('726', 'Hnahthial', 3),
    ('728', 'Khawzawl', 4),
    ('263', 'Kolasib', 5),
    ('264', 'Lawngtlai', 6),
    ('265', 'Lunglei', 7),
    ('266', 'Mamit', 8),
    ('727', 'Saitual', 9),
    ('268', 'Serchhip', 10),
    ('267', 'Siaha', 11)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'MZ'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- NL — 17 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('758', 'Chumoukedima', 1),
    ('244', 'Dimapur', 2),
    ('614', 'Kiphire', 3),
    ('245', 'Kohima', 4),
    ('615', 'Longleng', 5),
    ('788', 'Meluri', 6),
    ('246', 'Mokokchung', 7),
    ('247', 'Mon', 8),
    ('764', 'Niuland', 9),
    ('736', 'Noklak', 10),
    ('613', 'Peren', 11),
    ('248', 'Phek', 12),
    ('765', 'Shamator', 13),
    ('757', 'Tseminyu', 14),
    ('249', 'Tuensang', 15),
    ('250', 'Wokha', 16),
    ('251', 'Zunheboto', 17)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'NL'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- OD — 30 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('344', 'Anugola', 1),
    ('345', 'Balangir', 2),
    ('346', 'Baleshwar', 3),
    ('347', 'Baragada', 4),
    ('348', 'Bhadrak', 5),
    ('349', 'Boudh', 6),
    ('351', 'Debagada', 7),
    ('352', 'Dhenkanal', 8),
    ('353', 'Gajapati', 9),
    ('354', 'Ganjam', 10),
    ('355', 'Jagatsinghapur', 11),
    ('356', 'Jajpur', 12),
    ('357', 'Jharsuguda', 13),
    ('358', 'Kalahandi', 14),
    ('359', 'Kandhamala', 15),
    ('350', 'Kataka', 16),
    ('360', 'Kendrapada', 17),
    ('361', 'Kendujhar', 18),
    ('362', 'Khordha', 19),
    ('363', 'Koraput', 20),
    ('364', 'Malkangiri', 21),
    ('365', 'Mayurbhanj', 22),
    ('366', 'Nabarangpur', 23),
    ('367', 'Nayagada', 24),
    ('368', 'Nuapada', 25),
    ('369', 'Puri', 26),
    ('370', 'Rayagada', 27),
    ('371', 'Sambalpur', 28),
    ('372', 'Subarnapur', 29),
    ('373', 'Sundaragada', 30)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'OD'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- PB — 23 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('27', 'Amritsar', 1),
    ('605', 'Barnala', 2),
    ('28', 'Bathinda', 3),
    ('29', 'Faridkot', 4),
    ('30', 'Fatehgarh Sahib', 5),
    ('651', 'Fazilka', 6),
    ('31', 'Ferozepur', 7),
    ('32', 'Gurdaspur', 8),
    ('33', 'Hoshiarpur', 9),
    ('34', 'Jalandhar', 10),
    ('35', 'Kapurthala', 11),
    ('36', 'Ludhiana', 12),
    ('737', 'Malerkotla', 13),
    ('37', 'Mansa', 14),
    ('38', 'Moga', 15),
    ('662', 'Pathankot', 16),
    ('41', 'Patiala', 17),
    ('42', 'Rupnagar', 18),
    ('608', 'S.A.S Nagar', 19),
    ('43', 'Sangrur', 20),
    ('40', 'Shahid Bhagat Singh Nagar', 21),
    ('39', 'Sri Muktsar Sahib', 22),
    ('609', 'Tarn Taran', 23)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'PB'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- PY — 2 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('598', 'Karaikal', 1),
    ('600', 'Puducherry', 2)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'PY'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- RJ — 41 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('86', 'Ajmer', 1),
    ('87', 'Alwar', 2),
    ('775', 'Balotra', 3),
    ('88', 'Banswara', 4),
    ('89', 'Baran', 5),
    ('90', 'Barmer', 6),
    ('774', 'Beawar', 7),
    ('91', 'Bharatpur', 8),
    ('92', 'Bhilwara', 9),
    ('93', 'Bikaner', 10),
    ('94', 'Bundi', 11),
    ('95', 'Chittorgarh', 12),
    ('96', 'Churu', 13),
    ('97', 'Dausa', 14),
    ('767', 'Deeg', 15),
    ('98', 'Dholpur', 16),
    ('768', 'Didwana-Kuchaman', 17),
    ('99', 'Dungarpur', 18),
    ('100', 'Ganganagar', 19),
    ('101', 'Hanumangarh', 20),
    ('102', 'Jaipur', 21),
    ('103', 'Jaisalmer', 22),
    ('104', 'Jalore', 23),
    ('105', 'Jhalawar', 24),
    ('106', 'Jhunjhunu', 25),
    ('107', 'Jodhpur', 26),
    ('108', 'Karauli', 27),
    ('770', 'Khairthal-Tijara', 28),
    ('109', 'Kota', 29),
    ('782', 'Kotputli-Behror', 30),
    ('110', 'Nagaur', 31),
    ('111', 'Pali', 32),
    ('772', 'Phalodi', 33),
    ('629', 'Pratapgarh', 34),
    ('112', 'Rajsamand', 35),
    ('777', 'Salumbar', 36),
    ('113', 'Sawai Madhopur', 37),
    ('114', 'Sikar', 38),
    ('115', 'Sirohi', 39),
    ('116', 'Tonk', 40),
    ('117', 'Udaipur', 41)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'RJ'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- SK — 6 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('225', 'Gangtok', 1),
    ('228', 'Gyalshing', 2),
    ('226', 'Mangan', 3),
    ('227', 'Namchi', 4),
    ('741', 'Pakyong', 5),
    ('742', 'Soreng', 6)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'SK'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- TN — 38 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('610', 'Ariyalur', 1),
    ('730', 'Chengalpattu', 2),
    ('568', 'Chennai', 3),
    ('569', 'Coimbatore', 4),
    ('570', 'Cuddalore', 5),
    ('571', 'Dharmapuri', 6),
    ('572', 'Dindigul', 7),
    ('573', 'Erode', 8),
    ('729', 'Kallakurichi', 9),
    ('574', 'Kancheepuram', 10),
    ('575', 'Kanniyakumari', 11),
    ('576', 'Karur', 12),
    ('577', 'Krishnagiri', 13),
    ('578', 'Madurai', 14),
    ('735', 'Mayiladuthurai', 15),
    ('579', 'Nagapattinam', 16),
    ('580', 'Namakkal', 17),
    ('581', 'Perambalur', 18),
    ('582', 'Pudukkottai', 19),
    ('583', 'Ramanathapuram', 20),
    ('731', 'Ranipet', 21),
    ('584', 'Salem', 22),
    ('585', 'Sivaganga', 23),
    ('733', 'Tenkasi', 24),
    ('586', 'Thanjavur', 25),
    ('587', 'The Nilgiris', 26),
    ('588', 'Theni', 27),
    ('589', 'Thiruvallur', 28),
    ('590', 'Thiruvarur', 29),
    ('594', 'Thoothukkudi', 30),
    ('591', 'Tiruchirappalli', 31),
    ('592', 'Tirunelveli', 32),
    ('732', 'Tirupathur', 33),
    ('634', 'Tiruppur', 34),
    ('593', 'Tiruvannamalai', 35),
    ('595', 'Vellore', 36),
    ('596', 'Viluppuram', 37),
    ('597', 'Virudhunagar', 38)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'TN'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- TR — 8 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('269', 'Dhalai', 1),
    ('654', 'Gomati', 2),
    ('652', 'Khowai', 3),
    ('270', 'North Tripura', 4),
    ('653', 'Sepahijala', 5),
    ('271', 'South Tripura', 6),
    ('655', 'Unakoti', 7),
    ('272', 'West Tripura', 8)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'TR'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- TS — 33 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('501', 'Adilabad', 1),
    ('690', 'Bhadradri Kothagudem', 2),
    ('686', 'Hanumakonda', 3),
    ('507', 'Hyderabad', 4),
    ('681', 'Jagitial', 5),
    ('689', 'Jangoan', 6),
    ('687', 'Jayashankar Bhupalapally', 7),
    ('695', 'Jogulamba Gadwal', 8),
    ('685', 'Kamareddy', 9),
    ('508', 'Karimnagar', 10),
    ('509', 'Khammam', 11),
    ('699', 'Kumuram Bheem Asifabad', 12),
    ('688', 'Mahabubabad', 13),
    ('512', 'Mahabubnagar', 14),
    ('684', 'Mancherial', 15),
    ('513', 'Medak', 16),
    ('700', 'Medchal Malkajgiri', 17),
    ('720', 'Mulugu', 18),
    ('694', 'Nagarkurnool', 19),
    ('514', 'Nalgonda', 20),
    ('721', 'Narayanpet', 21),
    ('680', 'Nirmal', 22),
    ('516', 'Nizamabad', 23),
    ('682', 'Peddapalli', 24),
    ('683', 'Rajanna Sircilla', 25),
    ('518', 'Ranga Reddy', 26),
    ('691', 'Sangareddy', 27),
    ('692', 'Siddipet', 28),
    ('696', 'Suryapet', 29),
    ('698', 'Vikarabad', 30),
    ('693', 'Wanaparthy', 31),
    ('522', 'Warangal', 32),
    ('697', 'Yadadri Bhuvanagiri', 33)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'TS'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- UK — 13 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('45', 'Almora', 1),
    ('46', 'Bageshwar', 2),
    ('47', 'Chamoli', 3),
    ('48', 'Champawat', 4),
    ('49', 'Dehradun', 5),
    ('50', 'Haridwar', 6),
    ('51', 'Nainital', 7),
    ('52', 'Pauri Garhwal', 8),
    ('53', 'Pithoragarh', 9),
    ('54', 'Rudraprayag', 10),
    ('55', 'Tehri Garhwal', 11),
    ('56', 'Udham Singh Nagar', 12),
    ('57', 'Uttarkashi', 13)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'UK'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- UP — 75 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('118', 'Agra', 1),
    ('119', 'Aligarh', 2),
    ('121', 'Ambedkar Nagar', 3),
    ('640', 'Amethi', 4),
    ('154', 'Amroha', 5),
    ('122', 'Auraiya', 6),
    ('140', 'Ayodhya', 7),
    ('123', 'Azamgarh', 8),
    ('124', 'Baghpat', 9),
    ('125', 'Bahraich', 10),
    ('126', 'Ballia', 11),
    ('127', 'Balrampur', 12),
    ('128', 'Banda', 13),
    ('129', 'Bara Banki', 14),
    ('130', 'Bareilly', 15),
    ('131', 'Basti', 16),
    ('179', 'Bhadohi', 17),
    ('132', 'Bijnor', 18),
    ('133', 'Budaun', 19),
    ('134', 'Bulandshahr', 20),
    ('135', 'Chandauli', 21),
    ('136', 'Chitrakoot', 22),
    ('137', 'Deoria', 23),
    ('138', 'Etah', 24),
    ('139', 'Etawah', 25),
    ('141', 'Farrukhabad', 26),
    ('142', 'Fatehpur', 27),
    ('143', 'Firozabad', 28),
    ('144', 'Gautam Buddha Nagar', 29),
    ('145', 'Ghaziabad', 30),
    ('146', 'Ghazipur', 31),
    ('147', 'Gonda', 32),
    ('148', 'Gorakhpur', 33),
    ('149', 'Hamirpur', 34),
    ('661', 'Hapur', 35),
    ('150', 'Hardoi', 36),
    ('163', 'Hathras', 37),
    ('151', 'Jalaun', 38),
    ('152', 'Jaunpur', 39),
    ('153', 'Jhansi', 40),
    ('155', 'Kannauj', 41),
    ('156', 'Kanpur Dehat', 42),
    ('157', 'Kanpur Nagar', 43),
    ('633', 'Kasganj', 44),
    ('158', 'Kaushambi', 45),
    ('159', 'Kheri', 46),
    ('160', 'Kushinagar', 47),
    ('161', 'Lalitpur', 48),
    ('162', 'Lucknow', 49),
    ('165', 'Mahoba', 50),
    ('164', 'Mahrajganj', 51),
    ('166', 'Mainpuri', 52),
    ('167', 'Mathura', 53),
    ('168', 'Mau', 54),
    ('169', 'Meerut', 55),
    ('170', 'Mirzapur', 56),
    ('171', 'Moradabad', 57),
    ('172', 'Muzaffarnagar', 58),
    ('173', 'Pilibhit', 59),
    ('174', 'Pratapgarh', 60),
    ('120', 'Prayagraj', 61),
    ('175', 'Rae Bareli', 62),
    ('176', 'Rampur', 63),
    ('177', 'Saharanpur', 64),
    ('659', 'Sambhal', 65),
    ('178', 'Sant Kabir Nagar', 66),
    ('180', 'Shahjahanpur', 67),
    ('660', 'Shamli', 68),
    ('181', 'Shrawasti', 69),
    ('182', 'Siddharthnagar', 70),
    ('183', 'Sitapur', 71),
    ('184', 'Sonbhadra', 72),
    ('185', 'Sultanpur', 73),
    ('186', 'Unnao', 74),
    ('187', 'Varanasi', 75)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'UP'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- ---- WB — 23 districts ----
INSERT INTO nss.district (state_pk, district_code, district_name, display_order)
SELECT s.state_pk, v.dcode, v.dname, v.ord
FROM nss.state s
JOIN nss.country c ON c.country_pk = s.country_pk AND c.country_code = 'IN'
CROSS JOIN (VALUES
    ('664', 'Alipurduar', 1),
    ('305', 'Bankura', 2),
    ('307', 'Birbhum', 3),
    ('308', 'Cooch Behar', 4),
    ('310', 'Dakshin Dinajpur', 5),
    ('309', 'Darjeeling', 6),
    ('312', 'Hooghly', 7),
    ('313', 'Howrah', 8),
    ('314', 'Jalpaiguri', 9),
    ('703', 'Jhargram', 10),
    ('702', 'Kalimpong', 11),
    ('315', 'Kolkata', 12),
    ('316', 'Malda', 13),
    ('319', 'Murshidabad', 14),
    ('320', 'Nadia', 15),
    ('303', 'North 24 Parganas', 16),
    ('704', 'Paschim Bardhaman', 17),
    ('318', 'Paschim Medinipur', 18),
    ('306', 'Purba Bardhaman', 19),
    ('317', 'Purba Medinipur', 20),
    ('321', 'Purulia', 21),
    ('304', 'South 24 Parganas', 22),
    ('311', 'Uttar Dinajpur', 23)
) AS v(dcode, dname, ord)
WHERE s.state_code = 'WB'
ON CONFLICT (state_pk, district_code)
    WHERE entry_status = 'APPROVED' AND is_active = TRUE
    DO NOTHING;

-- END OF DOCUMENT
