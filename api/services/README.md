# api/services/

Logic behind the routers/dependencies; no FastAPI route declarations here.

| File | Purpose |
|------|---------|
| `family_graph.py` | In-memory kinship graph built from `nss.family_link` rows (`PARENT_OF` directed, `SPOUSE_OF` bidirectional). `build_family_graph(person_rows, link_rows)` → `FamilyGraph`; `compute_relationships(viewer_pk, max_depth=6)` BFS-walks from the viewer and maps each step-path (`UP`/`DOWN`/`SPOUSE`) through the `PATH_LABELS` table to a gendered label and a generation offset. Only direct edges are stored; every other term is derived. Used only by `family.py`'s `/graph`. |
| `auth_service.py` | Argon2 `hash_password()`/`verify_password()`; `create_access_token()`/`create_refresh_token()`/`decode_token()` (HS256; lifetimes from `JWT_ACCESS_TOKEN_MINUTES`/`JWT_REFRESH_TOKEN_DAYS`; `decode_token()` also enforces the `JWT_ABSOLUTE_SESSION_DAYS` cap from the `session_start` claim); `validate_password_policy()`; `is_account_locked()`/`calculate_lockout_until()`. |
| `rbac_service.py` | `ScopeInfo`/`UserContext` dataclasses and `load_user_context(conn, user_account_pk)` (permissions = union of active roles' `role_permission`; scopes from active `user_role` + `admin_scope`; returns `None` for an unknown/inactive account). `UserContext.is_super_admin()` is true only for `NSS_ERP_ADMIN`. Scope helpers used inside handlers: `actor_scope_org_pks()`, `org_in_scope()`, `require_org_in_scope()`, `require_person_in_scope()`, `require_account_in_scope()`. |

Constants for lockout, password policy and OTP come from `api/config.py`'s `Settings`, not from
this folder.
