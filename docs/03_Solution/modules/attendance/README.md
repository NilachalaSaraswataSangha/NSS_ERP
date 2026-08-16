# NSS ERP Attendance Module

Status: NOT STARTED (Solution design) — `backend/attendance/` exists as a Django app stub
(empty `models.py`/`views.py`, no `urls.py`, not in `INSTALLED_APPS`).

## Contents

- **`DARSHAK_BUSINESS_RULE.md`** (added 2026-08-16) — ERP implementation decision correcting an
  earlier project Rule Book's informal "Darshak → Full Member" model against the actual Bye-Law
  (`REF-002`): the official categories are Probationary/Regular/Associate Member, and "Darshak"
  is an operational/UI display label only, never a `membership_type_master` database value.

Full module design (`01_design` / `02_erd` / `03_business_rules` / `04_table_design`, following
the same pattern used by `docs/03_Solution/modules/organization/` and `.../person/`) has not
been written yet.
