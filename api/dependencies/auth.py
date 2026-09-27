"""
NSS ERP — Authentication dependency.

Extracts and validates JWT from the Authorization header.
Returns a UserContext with full RBAC information.

Usage in endpoints:
    @router.get("/protected")
    def protected(user: UserContext = Depends(get_current_user)):
        ...

    @router.get("/optional")
    def optional(user: UserContext | None = Depends(get_optional_user)):
        ...
"""

from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.database import get_connection
from api.services.auth_service import decode_token
from api.services.rbac_service import UserContext, load_user_context

# HTTPBearer extracts "Bearer <token>" from the Authorization header
_bearer_scheme = HTTPBearer(auto_error=True)
_bearer_scheme_optional = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    conn=Depends(get_connection),
) -> UserContext:
    """
    Mandatory auth dependency.

    Extracts JWT from Authorization header, validates it, loads
    the user's RBAC context from the database.

    Raises 401 if:
      - No token / invalid format
      - Token expired or invalid
      - Absolute session max exceeded
      - Token is not an access token
      - User account not found or inactive
    """
    token = credentials.credentials

    # Decode and validate JWT
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Must be an access token (not refresh)
    if payload.get("token_type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Access token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Load full RBAC context from database
    user_account_pk = UUID(payload["sub"])
    user_ctx = load_user_context(conn, user_account_pk)

    if user_ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Set session variables for the DB audit trigger.
    # nss.fn_audit_trigger() reads these to identify the actor.
    with conn.cursor() as cur:
        cur.execute(
            "SELECT set_config('nss.actor_user_account_pk', %s, TRUE)",
            (str(user_ctx.user_account_pk),),
        )
        if user_ctx.sangha_sevi_pk:
            cur.execute(
                "SELECT set_config('nss.actor_sangha_sevi_pk', %s, TRUE)",
                (str(user_ctx.sangha_sevi_pk),),
            )

    return user_ctx


def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme_optional),
    conn=Depends(get_connection),
) -> UserContext | None:
    """
    Optional auth dependency.

    Returns UserContext if a valid token is present, None otherwise.
    Does not raise 401 — useful for endpoints that behave differently
    for authenticated vs anonymous users.
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

    if payload.get("token_type") != "access":
        return None

    try:
        user_account_pk = UUID(payload["sub"])
    except (ValueError, KeyError):
        return None

    user_ctx = load_user_context(conn, user_account_pk)

    # Set session variables for the DB audit trigger
    if user_ctx is not None:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT set_config('nss.actor_user_account_pk', %s, TRUE)",
                (str(user_ctx.user_account_pk),),
            )
            if user_ctx.sangha_sevi_pk:
                cur.execute(
                    "SELECT set_config('nss.actor_sangha_sevi_pk', %s, TRUE)",
                    (str(user_ctx.sangha_sevi_pk),),
                )

    return user_ctx
