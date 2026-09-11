# docs/04_Testing/

Testing documentation scaffolding. The sub-folders below are reserved for formal test
plans/reports per category — none has content yet.

**Automated tests do exist** in the codebase — `tests/` (repo root) contains **139 integration
tests** across 4 files, all running against a real local PostgreSQL database via
`fastapi.testclient.TestClient` (nothing mocked). See `tests/README.md` for the test inventory
and `docs/03_Solution/code_explanations/` for the security audit reports.

| Folder | Purpose |
|---|---|
| `unit/` | Unit test documentation/plans |
| `integration/` | Integration test documentation/plans |
| `api/` | API test documentation/plans |
| `ui/` | UI test documentation/plans |
| `database/` | Database test documentation/plans |
| `security/` | Security test documentation/plans |
| `acceptance/` | User acceptance test documentation/plans |
