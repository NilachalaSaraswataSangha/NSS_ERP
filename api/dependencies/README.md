# api/dependencies/

FastAPI `Depends()` factories (Tier 5). Distinct from `api/services/`, which holds
the logic these call. `__init__.py` exports nothing — import from the submodules.

| File | Provides |
|------|----------|
| `auth.py` | `get_current_user()` — HTTP Bearer JWT → `UserContext`. 401 on missing/invalid/expired token, a refresh token presented as an access token, or an unknown/inactive account. Also sets the `nss.actor_user_account_pk`/`nss.actor_sangha_sevi_pk` session variables (`set_config(..., TRUE)`) that the DB `fn_audit_trigger()` reads. `get_optional_user()` — same but returns `None`; currently unused by any router. |
| `rbac.py` | `require_permission(code)` and `require_any_permission(*codes)` — dependency factories wrapping `get_current_user()`; 403 (`Permission required: ...` / `One of these permissions required: ...`) otherwise. Permissions are the union across all of a user's active roles. |

Both depend on `get_connection` (the read pool) — the actor session variables are therefore set on
a read-pool connection, not on the `nss_db_writer` connection write endpoints use (see "Known
gaps" in `api/README.md`).

Usage: `user: UserContext = Depends(require_permission("ADMIN_USER_MANAGE"))`. Scope-based checks
(`require_org_in_scope()` and friends) are not dependencies — they live in
`api/services/rbac_service.py` and are called inside handlers.
