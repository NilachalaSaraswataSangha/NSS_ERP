-- =====================================================
-- NSS ERP
-- Module: Organization
-- Seed File: 05_sakha_branches.sql
-- Version: 2.1 — ON CONFLICT DO NOTHING, not DO UPDATE (2026-10-05): a
--          re-run must never overwrite an admin's edit to a Sakha's
--          name/address. Insert-if-missing only.
-- Authority: NSS Bye-Law, NSS Branches directory
-- Owner: NSS_ERP_ADMIN
-- Note: Seeds 175 Sakha Sangha branches from the
--       official NSS branch directory document.
--       All branches are typed SAKHA_SANGHA with ACTIVE
--       status, parented to Kendra Sangha (KEN).
--
--       Anchalika (regional grouping) assignment is not
--       available in the source data - all branches are
--       parented directly to Kendra for now.
--
--       Organization codes: SKH1-SKH175 (unpadded)
--       
--
--       Postal codes are resolved to postal_code_pk FK
--       where available (121 of 175 branches). Remaining
--       branches have NULL postal_code_pk.
--
--       63 branches carry a PIN directly from the source
--       directory; a further 58 were recovered by matching
--       the branch "Po-<office>" token against the India Post
--       directory (Odisha scope, office-type + district
--       tie-breaking). 54 branches have no safely resolvable
--       PIN (post office absent from the directory or no
--       Po- token in the address) and remain NULL.
--
--       Country: IN for Indian, US for America Sangha.
--       short_code: NULL (admin-assignable via UI).
--
--       Geography (country_pk/state_pk/district_pk) is backfilled after
--       the INSERT. Primary source is the explicit "Dist-<Name>" token
--       in each branch address (165 of 175), resolved through an
--       explicit alias list onto the numeric LGD district_code; the
--       PIN→modal-district derivation is the fallback for the 10
--       metro/overseas branches with no token. SKH16 is special-cased.
--       Only SKH164 (USA) is left without a district. See the comment
--       blocks on each pass below. (Decision 2026-10-04)
--
--       Depends on: 09_sakha_postal_codes.sql (Foundation)
--
--       Idempotent: ON CONFLICT (organization_code) DO NOTHING.
-- =====================================================

-- CTE for compact bulk insertion with master_data + postal_code joins.

WITH branch_data (org_code, org_name, address_line_1, country_code, pin_code) AS (
    VALUES
        ('SKH1', 'Ekamra Saraswata Sangha', 'Sri Sri Nigamananda Asan Mandir, Samantarapur, Bhubaneswar-2, Dist-Khurda', 'IN', ''),
        ('SKH2', 'Angul Sakha Sangha', 'At-Shimilipada, Po-Angul, Dist-Angul, Pin-759122', 'IN', '759122'),
        ('SKH3', 'Bikrampur Sakha Sangha', 'At-Hulurisingha, Po-Hulurisingha, Dist-Angul, Pin-759132', 'IN', '759132'),
        ('SKH4', 'Jagannathpur Sakha Sangha', 'At/Po-Jagannathpur, Dist-Angul, Pin-759131', 'IN', '759131'),
        ('SKH5', 'Talcher Town Sakha Sangha', 'At/Po-Talcher Town, Dist-Angul, Pin-759107', 'IN', '759107'),
        ('SKH6', 'Nalconagar Sakha Sangha', 'Kandasar New Colony, Po-Kandasar, Dist-Angul', 'IN', '759145'),
        ('SKH7', 'Rankasingha Sakha Sangha', 'Qr. No-B/305, H.W.P. Colony, Po-Bikrampur, Dist-Angul, Pin-759106', 'IN', '759106'),
        ('SKH8', 'Samal Barrage Sakha Sangha', 'At/Po-Samal Barrage Township, Via-Talcher, Dist-Angul', 'IN', '759037'),
        ('SKH9', 'NTPC Sakha Sangha', 'Qr.No.-B/469, P.T.S., NTPC, Kaniha, Po-Dipasikha, Dist-Angul', 'IN', ''),
        ('SKH10', 'Athamallik Sakha Sangha', 'At-Titigaan, Po-Aiada, Via-Athamallik, Dist-Angul', 'IN', ''),
        ('SKH11', 'Narsinghpur Sakha Sangha', 'At-Kendupalli, Po-Nukhapada, Dist-Cuttack, Pin-754032', 'IN', '754032'),
        ('SKH12', 'Gopalpur Sakha Sangha', 'At-Gopalpur, Po-Champeswar, Via-Kanpur, Dist-Cuttack, Pin-754037', 'IN', '754037'),
        ('SKH13', 'Athagarh Sakha Sangha', 'Sri Sri Thakur Nigamananda Ashram, At/Po-Athagarh, Dist-Cuttack', 'IN', '754029'),
        ('SKH14', 'Sukarpada Sakha Sangha', 'At/Po-Sukarpada, Dist-Cuttack, Pin-754203', 'IN', '754203'),
        ('SKH15', 'Ashureswar Sakha Sangha', 'Sri Sri Nigamananda Asan Mandir, Nigampuri, At/Po-Ashureswar, Dist-Cuttack', 'IN', ''),
        ('SKH16', 'Cuttack Saraswata Sangha', 'Sri Sri Nigamananda Smrutikutira, Cuttack-3', 'IN', ''),
        ('SKH17', 'Kamarapada Sakha Sangha', 'At-Odapada, Po-Jashapada, Dist-Cuttack', 'IN', ''),
        ('SKH18', 'Kendupatana Sakha Sangha', 'At/Po-Kendupatana, Dist-Cuttack, Pin-754203', 'IN', '754203'),
        ('SKH19', 'Khuntuni Sakha Sangha', 'At-Uasadiha, Po-Nadiali, Dist-Dhenkanal', 'IN', '759027'),
        ('SKH20', 'Bayalish Mouja Sakha Sangha', 'At/Po-Kalapada, Dist-Cuttack', 'IN', '754112'),
        ('SKH21', 'Choudwar Sakha Sangha', 'Sri Sri Nigamananda Asan Mandir, Thermal Road, Po-Kapaleswar, Via-Choudwar, Dist-Cuttack, Pin-754025', 'IN', '754025'),
        ('SKH22', 'Tangi Sakha Sangha', 'At/Po-Rudrapur, Via-Chhatia, Dist-Cuttack', 'IN', ''),
        ('SKH23', 'Barapada Sakha Sangha (Cuttack)', 'At/Po-Khandasahi, Dist-Cuttack, Pin-754282', 'IN', '754282'),
        ('SKH24', 'Niali Sakha Sangha', 'At/Po-Niali, Dist-Cuttack, Pin-754004', 'IN', '754004'),
        ('SKH25', 'Banki Sakha Sangha', 'Near SBI, At/Po-Banki, Dist-Cuttack, Pin-754008', 'IN', '754008'),
        ('SKH26', 'Badamba Sakha Sangha', 'Sri Sri Nigamananda Ashram, At/Po-Badamba, Dist-Cuttack', 'IN', ''),
        ('SKH27', 'Khalarda Sakha Sangha', 'Dist-Cuttack', 'IN', ''),
        ('SKH28', 'Rahama Sakha Sangha (Kendrapara)', 'Nigambihar, At-Raham, Po-Babar, Dist-Kendrapara', 'IN', '754245'),
        ('SKH29', 'Endulapur Sakha Sangha', 'At-Endulapur, Po-Kurunti, Via-Rajnagar, Dist-Kendrapara', 'IN', '754225'),
        ('SKH30', 'Oupada Sakha Sangha', 'At/Po-Oupada, Via-Alava, Dist-Kendrapara', 'IN', '756049'),
        ('SKH31', 'Kayatha Sakha Sangha', 'At-Kayatha, Po-Dera, Via-Rajanagar, Dist-Kendrapara', 'IN', '754225'),
        ('SKH32', 'Mandapara Sakha Sangha', 'At-Bachhara, Po/Via-Pattamundai, Dist-Kendrapara', 'IN', '754215'),
        ('SKH33', 'Chhachina Sakha Sangha', 'At-Chhachina, Po-Nuahat, Via-Derabish, Dist-Kendrapara', 'IN', '754289'),
        ('SKH34', 'Jarimula Sakha Sangha', 'At-Jaduchandrapur, Po-Bhitargada, Via-Rajnagar, Dist-Kendrapara', 'IN', ''),
        ('SKH35', 'Junapangara Sakha Sangha', 'At-Gahmashikhar, Po-Dera, Via-Rajnagar, Dist-Kendrapara', 'IN', '754225'),
        ('SKH36', 'Tulasikshetra Sakha Sangha', 'D.S.Law College, Po-Thakurpatna, Dist-Kendrapara', 'IN', '754250'),
        ('SKH37', 'Deulapara Sakha Sangha', 'At-Oliha, Po-Deulapara, Via-Baladebjio, Dist-Kendrapara', 'IN', ''),
        ('SKH38', 'Nadiabarai Sakha Sangha', 'At-Nadiabarai, Po-Nadiabarai, Via-Karilopatna, Dist-Kendrapara', 'IN', ''),
        ('SKH39', 'Naukana Sakha Sangha', 'At/Po-Bada Naukana, Via-Rajnagar, Dist-Kendrapara, Pin-754246', 'IN', '754246'),
        ('SKH40', 'Rajnagar Sakha Sangha', 'At-Tarpada, Po-Rajnagar, Dist-Kendrapara', 'IN', '754225'),
        ('SKH41', 'Nuagaan Sakha Sangha', 'At-Nuagaan, Po-Gopalpur, Dist-Kendrapara, Pin-754225', 'IN', '754225'),
        ('SKH42', 'Matia Sakha Sangha', 'Sri Sri Nigamananda Ashram, At-Matia, Po-Pattamundai, Dist-Kendrapara', 'IN', '754215'),
        ('SKH43', 'Basudeipur Sakha Sangha', 'At-Basudeipur, Po-Raychand, Via-Karilopatna, Dist-Kendrapara', 'IN', ''),
        ('SKH44', 'Maharasahi Sakha Sangha', 'At/Po-Nadiabarai, Via-Karilopatna, Dist-Kendrapara', 'IN', ''),
        ('SKH45', 'Adhanga Sakha Sangha', 'At-Adhanga, Po-Bhagabanpur, Dist-Kendrapara', 'IN', '754134'),
        ('SKH46', 'Bijayanagar Sakha Sangha', 'At/Po-Bijayanagar, Dist-Kendrapara', 'IN', '754224'),
        ('SKH47', 'Katana Sakha Sangha', 'At-Daenigiri, Po-Katana, Via-Rajnagar, Dist-Kendrapara', 'IN', ''),
        ('SKH48', 'Chandiagari Sakha Sangha', 'At-Chandiagari, Po-Malapatana, Via-Pattamundai, Dist-Kendrapara, Pin-754215', 'IN', '754215'),
        ('SKH49', 'Kurunti Sakha Sangha', 'At/Po-Kurunti, Via-Rajnagar, Dist-Kendrapara', 'IN', '754225'),
        ('SKH50', 'Gopei Sakha Sangha', 'At/Po-Gopei, Via-Karilopatna, Dist-Kendrapara, Pin-754223', 'IN', '754223'),
        ('SKH51', 'Gouda Gan Sakha Sangha', 'At-Goudagan, Po-Jamapada, Dist-Kendrapara, Pin-754244', 'IN', '754244'),
        ('SKH52', 'Tikhiri Sakha Sangha', 'At/Po-Tikhiri, Via-Kujanga, Dist-Kendrapara', 'IN', '754141'),
        ('SKH53', 'Bilikana Sakha Sangha', 'At-Nadhiala, Po-Amber, Via-Pattamundai, Dist-Kendrapara', 'IN', '754215'),
        ('SKH54', 'Mahakalapada Sakha Sangha', 'At/Po-Mahakalapada, Dist-Kendrapara, Pin-754224', 'IN', '754224'),
        ('SKH55', 'Rajakanika Sakha Sangha', 'At-Block Colony, Po/Via-Pattamundai, Dist-Kendrapara', 'IN', '754215'),
        ('SKH56', 'Rajpur Sakha Sangha', 'At-Rajpur, Po-Keradagada, Via-Madanpur, Dist-Kendrapara', 'IN', '754246'),
        ('SKH57', 'Ramnagar Sakha Sangha', 'At/Po-Ramnagar, Via-Mahakalpada, Dist-Kendrapara', 'IN', ''),
        ('SKH58', 'Niala Sakha Sangha', 'At/Po-Niala, Via-Aul, Dist-Kendrapara', 'IN', ''),
        ('SKH59', 'Singhpahar Sakha Sangha', 'At-Singhpahar, Po-Madanpur, Dist-Kendrapara', 'IN', '754246'),
        ('SKH60', 'Naraharipur Sakha Sangha', 'Po-Aripada, Via-Karilopatna, Dist-Kendrapara', 'IN', '754223'),
        ('SKH61', 'Parlakhemundai Sakha Sangha', 'At-Rani Padmabati Sahi, Parlakhemundai, Dist-Gajapati', 'IN', ''),
        ('SKH62', 'Nigam Saraswata Sangha, Badamundilo', 'At/Po-Badamundilo, Via-Mandashi, Dist-Jagatsinghpur, Pin-754114', 'IN', '754114'),
        ('SKH63', 'Jagatsinghpur Sakha Sangha', 'Nigamananda Asan Mandir, At-Chatara, Po-Jagatsinghpur, Dist-Jagatsinghpur', 'IN', '754103'),
        ('SKH64', 'Daradapatana Sakha Sangha', 'At-Titira, Po-Titira, Via-Borikina, Dist-Jagatsinghpur, Pin-754110', 'IN', '754110'),
        ('SKH65', 'Naunga Sakha Sangha', 'At-Mahinsamunda, Po-Nuagnahat, Dist-Jagatsinghpur', 'IN', ''),
        ('SKH66', 'Paradeep Sakha Sangha', 'Qr No-NB-202, Nua Bazar, Paradwipa, Dist-Jagatsinghpur, Pin-754142', 'IN', '754142'),
        ('SKH67', 'Rahama Sakha Sangha (Jagatsinghpur)', 'Sri Sri Nigamananda Asan Mandir, At/Po-Rahama, Dist-Jagatsinghpur, Pin-754140', 'IN', '754140'),
        ('SKH68', 'Bachhasailo Sakha Sangha', 'At-Sanapada, Po-Sithalo, Dist-Cuttack', 'IN', ''),
        ('SKH69', 'Erasama Sakha Sangha', 'Dist-Jagatsinghpur', 'IN', ''),
        ('SKH70', 'Jharasuguda Sakha Sangha', 'Industrial Estate, Dist-Jharasuguda', 'IN', ''),
        ('SKH71', 'Kamakshyanagar Sakha Sangha', 'Nigamananda Asan Mandir, Giridimali, Dist-Dhenkanal, Pin-759021', 'IN', '759021'),
        ('SKH72', 'Dhenkanal Sakha Sangha', 'At-Gengutia, Po-Gengutia, Dist-Dhenkanal', 'IN', ''),
        ('SKH73', 'Balikiari Sakha Sangha', 'At-Balikiari, Po-Chhotapada, Via-Rasol, Dist-Dhenkanal, Pin-759021', 'IN', '759021'),
        ('SKH74', 'Rasol Sakha Sangha', 'At-Rasol, Po-Rasol, Dist-Dhenkanal, Pin-759021', 'IN', '759021'),
        ('SKH75', 'Kandarsingha Sakha Sangha', 'At/Po-Kantor, Dist-Dhenkanal', 'IN', '759120'),
        ('SKH76', 'Indrabati Sakha Sangha', 'Qr No-E/31, Paramabenu Colony, Khatiguda, Dist-Nabarangpur, Pin-764085', 'IN', '764085'),
        ('SKH77', 'Nayagarh Sakha Sangha', 'At-Godisahi, Po-Parapalli, Dist-Nayagarh', 'IN', ''),
        ('SKH78', 'Duajhar Sakha Sangha', 'At/Po-Duajhar, Dist-Nuapara, Pin-766118', 'IN', '766118'),
        ('SKH79', 'Ranimunda Sakha Sangha', 'At/Po-Ranimunda, Dist-Nuapara', 'IN', ''),
        ('SKH80', 'Phulbani Sakha Sangha', 'Nigamananda Asan Mandir, At-Kendupada, Po-Phulabani, Dist-Kandhamal', 'IN', ''),
        ('SKH81', 'Baliguda Sakha Sangha', 'Ladies Corner, Near Patkhanda Mandir, At/Po-Baliguda, Dist-Kandhamal', 'IN', ''),
        ('SKH82', 'Baragarh Sakha Sangha', 'At-B.S.S Nagar, Po-Baragarh, Dist-Baragarh', 'IN', ''),
        ('SKH83', 'Nimapara Sakha Sangha', 'At-Shyamasundarpur, Po-Nimapara, Dist-Puri', 'IN', '752106'),
        ('SKH84', 'Puri Town Sakha Sangha', 'Sri Sri Nigamananda Smruti Mandir, Swargadwar, Dist-Puri', 'IN', ''),
        ('SKH85', 'Balangir Sakha Sangha', 'Khujenpali High School, Po-Khujenpali, Via-Rajendra College, Dist-Balangir', 'IN', '767002'),
        ('SKH86', 'Silanda Sakha Sangha', 'At-Silanda, Po-Parasara, Dist-Balangir, Pin-767035', 'IN', '767035'),
        ('SKH87', 'Raibania Sakha Sangha', 'At/Po-Raibania, Dist-Balasore', 'IN', '756033'),
        ('SKH88', 'Kuagadia Sakha Sangha', 'At-Baduli, Po-Betada, Dist-Balasore', 'IN', '756168'),
        ('SKH89', 'Kupari Nigamananda Asan Mandir', 'At-Raipur, Po-Soro, Dist-Balasore', 'IN', '756045'),
        ('SKH90', 'Garasanga Sakha Sangha', 'At-Garasanga, Po-Garasanga, Dist-Balasore', 'IN', ''),
        ('SKH91', 'Nilagiri Sakha Sangha', 'At-Gangupura, Po-Rajnilagiri, Dist-Balasore', 'IN', ''),
        ('SKH92', 'Antara Sakha Sangha', 'At/Po-Antara, Via-Ada, Dist-Balasore', 'IN', '756134'),
        ('SKH93', 'Chittola Sakha Sangha', 'At-Chittol, Po-Anantapur, Dist-Balasore', 'IN', '756046'),
        ('SKH94', 'Dantia Sakha Sangha', 'At-Gandibed, Po-Gandibed, Dist-Balasore', 'IN', '756050'),
        ('SKH95', 'Gud Sakha Sangha', 'At-Gud, Via-Anantapur, Dist-Balasore, Pin-756046', 'IN', '756046'),
        ('SKH96', 'Balabhadrapur Sakha Sangha', 'At-Khanabada, Po-Khanabada, Dist-Balasore', 'IN', ''),
        ('SKH97', 'Nigam Saraswata Sangha, Mahatipur', 'At-Sarugaon, Po-Mahatipur, Dist-Balasore', 'IN', '756048'),
        ('SKH98', 'Soro Sakha Sangha', 'In front of SBI, Po/Via-Soro, Dist-Balasore, Pin-756045', 'IN', '756045'),
        ('SKH99', 'Gopinathpur Sakha Sangha', 'At-Gopinathpur, Po-Soro (Sadar N.A.C.), Dist-Balasore, Pin-756045', 'IN', '756045'),
        ('SKH100', 'Mahatipur Sakha Sangha', 'At-Harichandanpur, Po-Fatepur, Via-Oupada, Dist-Balasore', 'IN', '756137'),
        ('SKH101', 'Mukteswarpur Sakha Sangha', 'At-Pannada, Po-Balanga, Via-Anantapur, Dist-Balasore, Pin-756045', 'IN', '756045'),
        ('SKH102', 'Fatepur Sakha Sangha', 'At/Po-Fatepur, Via-Khaira, Dist-Balasore, Pin-756048', 'IN', '756048'),
        ('SKH103', 'Barapada Sakha Sangha (Balasore)', 'At-Ranpur, Po-Haripur, Via-B.T. Pur, Dist-Balasore', 'IN', ''),
        ('SKH104', 'Dandi Saraswata Sangha', 'Sri Sri Nigamananda Asan Mandir, At/Po-Dandi, Via-Basta, Dist-Balasore', 'IN', ''),
        ('SKH105', 'Bainanda Sakha Sangha', 'At/Po-Bainanda, Via-Soro, Dist-Balasore', 'IN', ''),
        ('SKH106', 'Balasore Sakha Sangha', 'Sri Sri Nigamananda Asan Mandir, Sardar Ballav Bhai Patel Marg, Rajabagicha, Dist-Balasore', 'IN', ''),
        ('SKH107', 'Matigada Sakha Sangha', 'At-Bhagabanpur Sasan, Po-Oupada, Dist-Balasore', 'IN', '756049'),
        ('SKH108', 'Bachhada Sakha Sangha', 'Dist-Balasore', 'IN', ''),
        ('SKH109', 'Dhusuli Sakha Sangha', 'Po-Sindhia, Dist-Balasore', 'IN', '756003'),
        ('SKH110', 'Jalahari Sakha Sangha', 'At-Jalahari, Po-Bankamunha, Via-Jajpur, Dist-Bhadrak', 'IN', ''),
        ('SKH111', 'Dhusuri Sakha Sangha', 'At/Po-Dhusuri, Dist-Bhadrak', 'IN', '756119'),
        ('SKH112', 'Aradi Sakha Sangha', 'At/Po-Aradi, Dist-Bhadrak', 'IN', '756138'),
        ('SKH113', 'Paliabindha Sakha Sangha', 'At-Palia, Po-Paliabindha, Dist-Bhadrak, Pin-757167', 'IN', '757167'),
        ('SKH114', 'Khadimahara Sakha Sangha', 'At/Po-Khadimahara, Dist-Bhadrak', 'IN', '756119'),
        ('SKH115', 'Bhadrak Sakha Sangha', 'Nigamananda Asan Mandir, At/Po-Kuansa, Dist-Bhadrak, Pin-756100', 'IN', '756100'),
        ('SKH116', 'Basudebpur Sakha Sangha', 'At-Padmapur, Po-Basudebpur, Dist-Bhadrak', 'IN', ''),
        ('SKH117', 'Betada Sakha Sangha', 'At-Tulamtula, Po-Betada, Dist-Bhadrak', 'IN', '756168'),
        ('SKH118', 'Govindapur Sakha Sangha', 'At/Po-Bhadrak, Dist-Bhadrak', 'IN', '756100'),
        ('SKH119', 'Banitia Sakha Sangha', 'Dist-Bhadrak', 'IN', ''),
        ('SKH120', 'Pandupani Sakha Sangha', 'At-Kaymdiha, Po-Pandupani, Via-Tiranga, Dist-Mayurbhanja, Pin-757056', 'IN', '757056'),
        ('SKH121', 'Baripada Sakha Sangha', 'Ganesh Bazar, At/Po-Baripada, Dist-Mayurbhanja, Pin-757001', 'IN', '757001'),
        ('SKH122', 'Kundapatana Sakha Sangha', 'At-Kundapatana, Po-Kundapatana, Dist-Jajpur', 'IN', ''),
        ('SKH123', 'Dharmasala Sakha Sangha', 'At-Naupala, Po-Dharmasala, Dist-Jajpur', 'IN', '755008'),
        ('SKH124', 'Jajpur Town Sakha Sangha', 'At-Barunha, Po-Kabirpur, Dist-Jajpur, Pin-755009', 'IN', '755009'),
        ('SKH125', 'Kabatbandha Sakha Sangha', 'At/Po-Kabatbandha, Via-Jenapur, Dist-Jajpur', 'IN', ''),
        ('SKH126', 'Kantigadia Sakha Sangha', 'At/Po-Kantigadia, Dist-Jajpur', 'IN', '755049'),
        ('SKH127', 'Byasanagar Kanheipur Sakha Sangha', 'At-Chorada, Po-Jajpur Road, Dist-Jajpur, Pin-755019', 'IN', '755019'),
        ('SKH128', 'Dekudi Sakha Sangha', 'At-Sudhadiha Kateni, Po-Baulapur, Dist-Dhenkanal', 'IN', ''),
        ('SKH129', 'Sobara Sakha Sangha', 'At-Sobra, Po-Jajpur Road, Via-Jajpur Road, Dist-Jajpur, Pin-755019', 'IN', '755019'),
        ('SKH130', 'Kalakala Sakha Sangha', 'Sri Sri Nigamananda Asan Mandir, At/Po-Kalakala, Via-Bairi, Dist-Jajpur', 'IN', '754082'),
        ('SKH131', 'Kuakhia Sakha Sangha', 'At-Baransa, Po-Rasulpur, Via-Kabirpur, Dist-Jajpur', 'IN', '755051'),
        ('SKH132', 'Sambalpur Sakha Sangha', 'Sri Sri Nigamananda Asan Mandir, Jail Road, Dist-Sambalpur', 'IN', ''),
        ('SKH133', 'Facimal Sakha Sangha', 'At/Po-Facimal, Via-Jamenkir, Dist-Sambalpur', 'IN', ''),
        ('SKH134', 'Burla Sakha Sangha', 'At-Basamta Bihar, Po/Via-Burla, Dist-Sambalpur', 'IN', '768017'),
        ('SKH135', 'Rourkela Shaktinagar Sakha Sangha', 'Po-Shaktinagar, At-Jagada, Rourkela, Dist-Sundargarh', 'IN', ''),
        ('SKH136', 'Badagaon Sakha Sangha', 'At/Po-Badagaon, Dist-Sundargarh, Pin-770016', 'IN', '770016'),
        ('SKH137', 'Rajgangapur Sakha Sangha', 'I.T. Colony, Qr No-D/4, Po-Rajgangapur, Dist-Sundargarh', 'IN', ''),
        ('SKH138', 'Rourkela Town Sakha Sangha', 'Qr No-MMM-28, Po-Civil Township, Rourkela-4, Dist-Sundargarh', 'IN', '769004'),
        ('SKH139', 'Sundargarh Sakha Sangha', 'Dist-Sundargarh', 'IN', ''),
        ('SKH140', 'Balijodi Sakha Sangha', 'Dist-Sundargarh', 'IN', ''),
        ('SKH141', 'Kendujhar Sakha Sangha', 'At-Kasipur, Po-Kashipur, Dist-Keonjhar', 'IN', '765015'),
        ('SKH142', 'Joda Sakha Sangha', 'Sri Sri Nigamananda Asan Mandir, At/Po-Baneikela, Via-Joda, Dist-Keonjhar, Pin-758034', 'IN', '758034'),
        ('SKH143', 'Atasahi Sakha Sangha', 'At/Po-Atasahi, Via-Ghasipura, Dist-Keonjhar', 'IN', '758015'),
        ('SKH144', 'Anandapur Sakha Sangha', 'At/Po-Anandapur, Via-Anandapur, Dist-Keonjhar', 'IN', '756126'),
        ('SKH145', 'Salabani Sakha Sangha', 'Via-Anandapur, Dist-Keonjhar', 'IN', ''),
        ('SKH146', 'Chenapadi Sakha Sangha', 'At-Math, Po-Chenapadi, Dist-Keonjhar', 'IN', ''),
        ('SKH147', 'Joypur Sakha Sangha', 'Sri Sri Nigamananda Asan Mandir, At-Purunagad, Po-Prasad Rao Peta, Dist-Koraput', 'IN', '764003'),
        ('SKH148', 'Damanjodi Sakha Sangha', 'Qr No A/164, Sector-1, At/Po-Damanjodi, Dist-Koraput', 'IN', '763008'),
        ('SKH149', 'Semiliguda Sakha Sangha', 'Nandapur Road, At/Po-Semiliguda, Dist-Koraput', 'IN', '764036'),
        ('SKH150', 'Balimela Sakha Sangha', 'Sri Sri Nigamananda Asan Mandir, Drug Line-3, Po-Balimela, Dist-Malkanagiri, Pin-764051', 'IN', '764051'),
        ('SKH151', 'Boudha Sakha Sangha', 'Dist-Boudh', 'IN', ''),
        ('SKH152', 'Kendra Sevak Sangha', 'Satsikhya Mandir, Plot No-A/4, Unit-9, Bhubaneswar-751022, Dist-Khurda', 'IN', '751022'),
        ('SKH153', 'Rajadhani Saraswata Sangha', 'L.I.G-165, Brit Colony, Nayapali, Bhubaneswar, Dist-Khurda', 'IN', ''),
        ('SKH154', 'Atri Sakha Sangha', 'At-Atri, Po-Baghamari, Dist-Khurda, Pin-752061', 'IN', '752061'),
        ('SKH155', 'Banamalipur Sakha Sangha', 'At-Dewani Patna, Po-Banamalipur, Dist-Khurda', 'IN', '752103'),
        ('SKH156', 'Begunia Sakha Sangha', 'At/Po-Begunia, Via-Begunia, Dist-Khurda, Pin-752062', 'IN', '752062'),
        ('SKH157', 'Khurda Sakha Sangha', 'At-Atri, Po-Baghamari, Dist-Khurda, Pin-752061', 'IN', '752061'),
        ('SKH158', 'Bolagarh Sakha Sangha', 'At/Po-Bolagarh, Via-Bolagarh, Dist-Khurda, Pin-752066', 'IN', '752066'),
        ('SKH159', 'Sanapadar Sakha Sangha', 'At/Po-Sanapadar, Via-Pichukoli, Dist-Khurda', 'IN', '752064'),
        ('SKH160', 'Lanjia Sakha Sangha', 'At-Lanjia, Po-Dakhinapur, Via-Berhampur, Dist-Ganjam', 'IN', ''),
        ('SKH161', 'Badakheta Sakha Sangha', 'At-Badakheta, Po-Aitipur, Via-Khalikot, Dist-Ganjam, Pin-761029', 'IN', '761029'),
        ('SKH162', 'Tanarada Sakha Sangha', 'At/Po-Baunsalundi, Via-Jilundi, Dist-Ganjam, Pin-761133', 'IN', '761133'),
        ('SKH163', 'Berhampur Sakha Sangha', 'Panda Colony, Near Engineering School, At/Po-Berhampur, Dist-Ganjam', 'IN', '752010'),
        ('SKH164', 'America Saraswata Sangha', '1040 Jayaguru Lane, Efland, North Carolina-27243, United States of America', 'US', '27243'),
        ('SKH165', 'Mumbai Sakha Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, Chindran Village, Taloja MIDC, Taluka Panvel, Dist-Raigad, Navi Mumbai, Maharashtra-410206', 'IN', '410206'),
        ('SKH166', 'Bangalore Saraswata Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, Paramanahalli, Jadigenahalli Hobli, Hosakote Taluk, Bengaluru-562114', 'IN', '562114'),
        ('SKH167', 'Pune Saraswata Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, Village Kolawadi, Manjari-Theur Road, PO Theur, Dist-Pune-412110', 'IN', '412110'),
        ('SKH168', 'Delhi Saraswata Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, N 22-25, Hargovind Enclave, Rajpur Extension, PO Maidangarhi, New Delhi-110068', 'IN', '110068'),
        ('SKH169', 'Chennai Sakha Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, Plot No.13, Phase-I, SH-57, ITI Square, Sriperumbudur, Chennai-600116', 'IN', '600116'),
        ('SKH170', 'Kolkata Saraswata Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, Ghughupara, Bhattanagar, Liluah, Howrah-711203', 'IN', '711203'),
        ('SKH171', 'Surat Sakha Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, Plot No. 118-125, Sai Nagar Society, Gaveni Cross Road, Sonari, Surat-394221', 'IN', '394221'),
        ('SKH172', 'Hyderabad Saraswata Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, Plot No. 24-25, Srivani Nagar, PO Ameenpur, Dist-Medak, Pin-502032', 'IN', '502032'),
        ('SKH173', 'Jamshedpur Sakha Sangha', 'Sri Sri Thakur Nigamananda Asan Mandir, 25 P.G. Path, Via Ashok Path, Bhatia Basti, Kadma, Jamshedpur-831005', 'IN', '831005'),
        ('SKH174', 'Rishikesh Ashram', 'Santi Kutira, Sri Sri Thakur Nigamananda Asan Mandir, Opposite Rajasthan Sevashram, Shisham Jhari, Muni Ki Reti, Rishikesh, Pin-249201', 'IN', '249201'),
        ('SKH175', 'Raipur Sakha Sangha', 'LIG-49, Amleshwar Housing Board, Amleshwar, Raipur, Chhattisgarh-491111', 'IN', '491111')
),
resolved AS (
    SELECT
        bd.org_code,
        bd.org_name,
        ot.master_data_pk   AS type_pk,
        os.master_data_pk   AS status_pk,
        kendra.organization_pk AS parent_pk,
        bd.address_line_1,
        c.country_pk,
        pc.postal_code_pk
    FROM branch_data bd
    CROSS JOIN nss.master_data ot
    JOIN nss.master_category mc_type
         ON mc_type.master_category_pk = ot.master_category_pk
    CROSS JOIN nss.master_data os
    JOIN nss.master_category mc_status
         ON mc_status.master_category_pk = os.master_category_pk
    CROSS JOIN nss.organization kendra
    JOIN nss.country c
         ON c.country_code = bd.country_code
    LEFT JOIN nss.postal_code pc
         ON pc.postal_code = bd.pin_code
        AND bd.pin_code <> ''
    WHERE mc_type.category_code   = 'ORGANIZATION_TYPE'
      AND ot.value_code           = 'SAKHA_SANGHA'
      AND mc_status.category_code = 'STATUS'
      AND os.value_code           = 'ACTIVE'
      AND kendra.organization_code = 'KEN'
)
INSERT INTO nss.organization
    (organization_code, organization_name,
     organization_type_master_data_pk, status_master_data_pk,
     parent_organization_pk, address_line_1, country_pk, postal_code_pk)
SELECT
    r.org_code, r.org_name,
    r.type_pk, r.status_pk,
    r.parent_pk, r.address_line_1, r.country_pk, r.postal_code_pk
FROM resolved r
ON CONFLICT (organization_code) DO NOTHING;

-- ---------------------------------------------------------------------
-- Backfill state_pk / district_pk from each branch's resolved PIN.
--
-- Only country_pk + postal_code_pk are set above; state_pk/district_pk
-- were left NULL, which silently broke every geographic filter that
-- keys off them ("find a Sakha near me" on registration, and the
-- Create-Family modal's state/district narrowing — both matched zero
-- rows). nss.postal_code carries no district FK (the PIN→district link
-- lives on nss.city_village), so derive each branch's district as the
-- modal (most frequent) district among the city_village rows that share
-- its PIN, then take the state from that district.
--
-- Branches with a NULL postal_code_pk (PIN not resolvable from the
-- directory, ~54 of 175) are not reached by this pass.
-- (SOL-ARCH-010 Amendment, 2026-10-01)
--
-- NOTE: this pass is no longer the primary district source. The
-- address-token pass immediately below supersedes it wherever the
-- address states a district explicitly, and also covers the 54
-- PIN-less branches. This pass now only serves as the fallback for
-- the 10 metro/overseas branches that carry no "Dist-" token.
-- ---------------------------------------------------------------------
UPDATE nss.organization o
SET    district_pk = pin_geo.district_pk,
       state_pk    = d.state_pk
FROM (
    SELECT cv.postal_code_pk,
           MODE() WITHIN GROUP (ORDER BY cv.district_pk) AS district_pk
    FROM   nss.city_village cv
    WHERE  cv.postal_code_pk IS NOT NULL
      AND  cv.district_pk    IS NOT NULL
    GROUP  BY cv.postal_code_pk
) AS pin_geo
JOIN   nss.district d ON d.district_pk = pin_geo.district_pk
WHERE  o.postal_code_pk = pin_geo.postal_code_pk
  AND  o.organization_code LIKE 'SKH%';

-- ---------------------------------------------------------------------
-- Backfill country_pk / state_pk / district_pk from the address's
-- explicit "Dist-<Name>" token — AUTHORITATIVE over the PIN pass above.
--
-- The PIN pass derives district *statistically* (the modal city_village
-- district for that PIN), which is wrong wherever a PIN straddles two
-- districts, and fires for only 121 of 175 branches. The other 54 carry
-- no resolvable PIN at all, so their district_pk/state_pk stayed NULL
-- and they were invisible to every district-filtered Sakha lookup —
-- notably GET /api/v1/register/sakhas on the registration form, which
-- is the whole point of mapping them.
--
-- The address, by contrast, states the district explicitly: 165 of 175
-- branches carry a "Dist-<Name>" token, written by the Sangha itself.
-- That is a direct assertion rather than a statistical inference, so it
-- WINS wherever present; the PIN-modal pass above remains the fallback
-- for the 10 metro/overseas branches with no token. (Decision 2026-10-04)
--
-- Name matching uses an EXPLICIT alias list, not trigram similarity.
-- The branch directory uses common English spellings while nss.district
-- is LGD/Odia-transliterated, so 15 of the 26 Odisha spellings differ
-- (119 of 165 branches). An explicit list is deterministic, reviewable,
-- and cannot silently mismap. Each alias resolves to the numeric LGD
-- district_code, which is globally unique (06_district.sql v5.0) — so
-- the join needs no state scoping, and the Raigad/Maharashtra vs
-- Raigarh/Chhattisgarh name collision cannot occur by construction.
--
-- state_pk and country_pk are taken from the matched district so the
-- country → state → district chain stays internally consistent.
--
-- Must run BEFORE the city_village passes below, which read district_pk.
-- Idempotent: only (re)sets SKH% rows, derived from static address text.
-- ---------------------------------------------------------------------
UPDATE nss.organization o
SET    district_pk = d.district_pk,
       state_pk    = s.state_pk,
       country_pk  = s.country_pk
FROM   ( VALUES
             -- address spelling   LGD code      canonical district_name
             ('angul',            '344'),  -- Anugola          (OD)
             ('balangir',         '345'),  -- Balangir         (OD)
             ('balasore',         '346'),  -- Baleshwar        (OD)
             ('baragarh',         '347'),  -- Baragada         (OD)
             ('bhadrak',          '348'),  -- Bhadrak          (OD)
             ('boudh',            '349'),  -- Boudh            (OD)
             ('cuttack',          '350'),  -- Kataka           (OD)
             ('dhenkanal',        '352'),  -- Dhenkanal        (OD)
             ('gajapati',         '353'),  -- Gajapati         (OD)
             ('ganjam',           '354'),  -- Ganjam           (OD)
             ('jagatsinghpur',    '355'),  -- Jagatsinghapur   (OD)
             ('jajpur',           '356'),  -- Jajpur           (OD)
             ('jharasuguda',      '357'),  -- Jharsuguda       (OD)
             ('kandhamal',        '359'),  -- Kandhamala       (OD)
             ('kendrapara',       '360'),  -- Kendrapada       (OD)
             ('keonjhar',         '361'),  -- Kendujhar        (OD)
             ('khurda',           '362'),  -- Khordha          (OD)
             ('koraput',          '363'),  -- Koraput          (OD)
             ('malkanagiri',      '364'),  -- Malkangiri       (OD)
             ('mayurbhanja',      '365'),  -- Mayurbhanj       (OD)
             ('nabarangpur',      '366'),  -- Nabarangpur      (OD)
             ('nayagarh',         '367'),  -- Nayagada         (OD)
             ('nuapara',          '368'),  -- Nuapada          (OD)
             ('puri',             '369'),  -- Puri             (OD)
             ('sambalpur',        '371'),  -- Sambalpur        (OD)
             ('sundargarh',       '373'),  -- Sundaragada      (OD)
             ('pune',             '490'),  -- Pune             (MH)
             ('raigad',           '491'),  -- Raigad           (MH)
             ('medak',            '513')   -- Medak            (TS)
       ) AS dist_alias(addr_name, dcode)
JOIN   nss.district d ON d.district_code = dist_alias.dcode
JOIN   nss.state    s ON s.state_pk      = d.state_pk
WHERE  o.organization_code LIKE 'SKH%'
  AND  lower((regexp_match(o.address_line_1,
                           '[Dd]ist[-.][ ]*([A-Za-z]+)'))[1]) = dist_alias.addr_name;

-- ---------------------------------------------------------------------
-- SKH16 Cuttack Saraswata Sangha — explicit special case.
--
-- Its address ('Sri Sri Nigamananda Smrutikutira, Cuttack-3') carries
-- neither a PIN nor a "Dist-" token, so neither pass above reaches it.
-- "Cuttack-3" is a Cuttack city postal locality, which places it in
-- Kataka district (LGD 350) — confirmed by the Sangha. Treated as an
-- explicit assertion, same tier as a Dist- token. (Decision 2026-10-04)
--
-- SKH164 America Saraswata Sangha is deliberately NOT special-cased:
-- it is a US address and has no Indian district. It stays NULL.
-- ---------------------------------------------------------------------
UPDATE nss.organization o
SET    district_pk = d.district_pk,
       state_pk    = s.state_pk,
       country_pk  = s.country_pk
FROM   nss.district d
JOIN   nss.state s ON s.state_pk = d.state_pk
WHERE  o.organization_code = 'SKH16'
  AND  d.district_code     = '350';

-- ---------------------------------------------------------------------
-- SKH166 / SKH173 — explicit special cases (post-rebuild verification,
-- 2026-10-04). Neither carries a "Dist-" token, and the PIN-modal
-- fallback found no city_village rows for their PINs (both outside the
-- Odisha-heavy city_village seed), so both stayed NULL after the two
-- passes above. Resolved from the address text directly:
--
--   SKH166 Bangalore Saraswata Sangha — address names "Hosakote Taluk,
--   Bengaluru-562114". The postal town "Bengaluru" is NOT the district:
--   PIN 562114 / Hoskote Taluk falls in Bengaluru Rural (LGD 526), not
--   Bengaluru Urban (525) — confirmed against India Post / Wikipedia.
--   Deliberately NOT added to the alias list, since a bare "bengaluru"
--   token would silently mismap every future Bengaluru Urban address.
--
--   SKH173 Jamshedpur Sakha Sangha — address names only the city
--   "Jamshedpur-831005"; Jamshedpur sits in East Singhbum district,
--   Jharkhand (LGD 327 — seed spelling omits the middle "h": "Singhbum",
--   not "Singhbhum"). No district name appears in the address at all,
--   so this cannot be a generic alias entry either.
-- ---------------------------------------------------------------------
UPDATE nss.organization o
SET    district_pk = d.district_pk,
       state_pk    = s.state_pk,
       country_pk  = s.country_pk
FROM   nss.district d
JOIN   nss.state s ON s.state_pk = d.state_pk
WHERE  o.organization_code = 'SKH166'
  AND  d.district_code     = '526';

UPDATE nss.organization o
SET    district_pk = d.district_pk,
       state_pk    = s.state_pk,
       country_pk  = s.country_pk
FROM   nss.district d
JOIN   nss.state s ON s.state_pk = d.state_pk
WHERE  o.organization_code = 'SKH173'
  AND  d.district_code     = '327';

-- ---------------------------------------------------------------------
-- Backfill city_village_pk from each branch's address, where possible.
--
-- country_pk + postal_code_pk (above) and state_pk + district_pk (just
-- above) are set, but city_village_pk was never populated — so a Sakha
-- Sangha could not be matched to a specific locality in the geographic
-- cascade / search (it only resolved down to the PIN). Derive it from the
-- branch's own address_line_1 (the "At-/Po-/Via-" locality tokens), which
-- is the only place the locality name actually lives.
--
-- Two passes, most-specific first; both are address-driven and scoped so
-- they can never pull a city_village from the wrong PIN/district:
--
--   Pass 1 — among the city_village rows anchored to the branch's exact
--            PIN, pick the one whose name appears in the address (if any),
--            else the longest name, deterministic tie-break. This is the
--            common, high-confidence case.
--
--   Pass 2 — for branches still NULL (their PIN has no city_village row
--            anchored to it — typical of a multi-PIN town whose single
--            city_village row is anchored to a different representative
--            PIN), match an address-name token against the city_village
--            rows in the branch's resolved district. The length(name) >= 4
--            guard avoids spurious short-substring matches.
--
-- Branches whose address names no known city_village (or whose PIN never
-- resolved) stay NULL — correct, since their locality is genuinely
-- unknown. Idempotent: re-running only (re)sets SKH% rows and both passes
-- are deterministic. (SOL-ARCH-010 Amendment / request 2026-10-02)
-- ---------------------------------------------------------------------
UPDATE nss.organization o
SET    city_village_pk = best.city_village_pk
FROM (
    SELECT DISTINCT ON (o2.organization_pk)
           o2.organization_pk,
           cv.city_village_pk
    FROM   nss.organization o2
    JOIN   nss.city_village cv
           ON cv.postal_code_pk = o2.postal_code_pk
    WHERE  o2.organization_code LIKE 'SKH%'
      AND  o2.postal_code_pk  IS NOT NULL
      AND  o2.city_village_pk IS NULL
    ORDER  BY o2.organization_pk,
              (lower(o2.address_line_1) LIKE '%' || lower(cv.city_village_name) || '%') DESC,
              length(cv.city_village_name) DESC,
              cv.city_village_name
) AS best
WHERE  o.organization_pk = best.organization_pk;

UPDATE nss.organization o
SET    city_village_pk = best.city_village_pk
FROM (
    SELECT DISTINCT ON (o2.organization_pk)
           o2.organization_pk,
           cv.city_village_pk
    FROM   nss.organization o2
    JOIN   nss.city_village cv
           ON cv.district_pk = o2.district_pk
          AND lower(o2.address_line_1) LIKE '%' || lower(cv.city_village_name) || '%'
    WHERE  o2.organization_code LIKE 'SKH%'
      AND  o2.district_pk     IS NOT NULL
      AND  o2.city_village_pk IS NULL
      AND  length(cv.city_village_name) >= 4
    ORDER  BY o2.organization_pk,
              length(cv.city_village_name) DESC,
              cv.city_village_name
) AS best
WHERE  o.organization_pk = best.organization_pk;
