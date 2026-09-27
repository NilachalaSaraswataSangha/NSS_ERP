"""
NSS ERP — RBAC dependency.

Permission-checking dependency factories for FastAPI endpoints.

Usage:
    @router.post("/users")
    def create_user(
        user: UserContext = Depends(require_permission("ADMIN_USER_MANAGE")),
    ):
        ...

    @router.get("/users")
    def list_users(
        user: UserContext = Depends(require_any_permission(
            "ADMIN_USER_VIEW", "ADMIN_USER_MANAGE"
        )),
    ):
        ...
"""

from fastapi import Depends, HTTPException, status

from api.dependencies.auth import get_current_user
from api.services.rbac_service import UserContext


def require_permission(permission_code: str):
    """
    Dependency factory: require exactly one permission.

    Returns a FastAPI dependency that:
      1. Authenticates the user (via get_current_user)
      2. Checks the user has the specified permission
      3. Returns the UserContext on success
      4. Raises 403 on failure
    """

    def _check(user: UserContext = Depends(get_current_user)) -> UserContext:
        if not user.has_permission(permission_code):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission_code}",
            )
        return user

    return _check


def require_any_permission(*permission_codes: str):
    """
    Dependency factory: require at least one of the listed permissions.

    Returns a FastAPI dependency that:
      1. Authenticates the user
      2. Checks the user has any of the specified permissions
      3. Returns the UserContext on success
      4. Raises 403 on failure
    """

    def _check(user: UserContext = Depends(get_current_user)) -> UserContext:
        if not user.has_any_permission(*permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"One of these permissions required: {', '.join(permission_codes)}",
            )
        return user

    return _check
