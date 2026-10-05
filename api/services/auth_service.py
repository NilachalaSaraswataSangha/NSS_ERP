"""
NSS ERP — Authentication service.

Core auth operations:
  - Password hashing (Argon2) and verification
  - JWT token creation and validation
  - Login chain: sangha_sevi_id → person_pk → user_account
  - Lockout logic (5 attempts, 30-second auto-unlock)
  - Password policy validation

Authority: SOL-AUTH-001, SOL-AUTH-002, SOL-AUTH-004,
           Tier 5 design decisions (2026-09-15)
"""

import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from api.config import settings

# ── Argon2 hasher (default params are production-grade) ──────────────────

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2."""
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify a plaintext password against an Argon2 hash."""
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


# ── Password policy validation ───────────────────────────────────────────

def validate_password_policy(password: str) -> list[str]:
    """
    Validate password against frozen policy (Tier 5 decision #3).

    Returns a list of violation messages (empty = valid).

    Policy:
      - 8–128 characters
      - At least 1 uppercase letter
      - At least 1 digit
    """
    errors = []
    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(
            f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters."
        )
    if len(password) > settings.PASSWORD_MAX_LENGTH:
        errors.append(
            f"Password must be at most {settings.PASSWORD_MAX_LENGTH} characters."
        )
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least 1 uppercase letter.")
    if not re.search(r"\d", password):
        errors.append("Password must contain at least 1 digit.")
    return errors


# ── JWT token creation ───────────────────────────────────────────────────

def create_access_token(
    user_account_pk: UUID,
    person_pk: UUID,
    sangha_sevi_id: str,
    session_start: datetime | None = None,
    session_pk: UUID | None = None,
) -> str:
    """
    Create a short-lived access token (default 30 min).

    Claims:
      sub: user_account_pk (string)
      person_pk: person_pk (string)
      sangha_sevi_id: login identifier
      token_type: "access"
      session_start: original session start (for absolute max)
      session_pk: nss.user_session row backing this login (Tier 5 A4),
                  when the caller has one — omitted for backward
                  compatibility with pre-session tokens.
      iat: issued at
      exp: expiration
    """
    now = datetime.now(timezone.utc)
    if session_start is None:
        session_start = now

    payload = {
        "sub": str(user_account_pk),
        "person_pk": str(person_pk),
        "sangha_sevi_id": sangha_sevi_id,
        "token_type": "access",
        "session_start": session_start.isoformat(),
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_MINUTES),
    }
    if session_pk is not None:
        payload["session_pk"] = str(session_pk)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_account_pk: UUID,
    session_start: datetime | None = None,
    session_pk: UUID | None = None,
) -> str:
    """
    Create a longer-lived refresh token (default 7 days).

    Claims:
      sub: user_account_pk (string)
      token_type: "refresh"
      session_start: original session start (for absolute max)
      session_pk: nss.user_session row backing this login (Tier 5 A4),
                  when the caller has one — omitted for backward
                  compatibility with pre-session tokens.
      iat: issued at
      exp: expiration
    """
    now = datetime.now(timezone.utc)
    if session_start is None:
        session_start = now

    payload = {
        "sub": str(user_account_pk),
        "token_type": "refresh",
        "session_start": session_start.isoformat(),
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_DAYS),
    }
    if session_pk is not None:
        payload["session_pk"] = str(session_pk)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


# ── JWT token validation ─────────────────────────────────────────────────

def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Returns the payload dict on success.
    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.

    Also enforces the absolute session max (30 days from session_start).
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )

    # Enforce absolute session max
    session_start_str = payload.get("session_start")
    if session_start_str:
        session_start = datetime.fromisoformat(session_start_str)
        absolute_max = session_start + timedelta(days=settings.JWT_ABSOLUTE_SESSION_DAYS)
        if datetime.now(timezone.utc) > absolute_max:
            raise jwt.ExpiredSignatureError(
                "Session has exceeded the absolute maximum duration."
            )

    return payload


# ── Lockout helpers ──────────────────────────────────────────────────────

def is_account_locked(
    failed_login_attempts: int,
    locked_until: datetime | None,
) -> bool:
    """
    Check if an account is currently locked.

    Locked if:
      - failed_login_attempts >= MAX_FAILED_ATTEMPTS AND
      - locked_until is in the future
    """
    if failed_login_attempts < settings.MAX_FAILED_ATTEMPTS:
        return False
    if locked_until is None:
        return False
    now = datetime.now(timezone.utc)
    return locked_until > now


def calculate_lockout_until() -> datetime:
    """Calculate the locked_until timestamp (now + lockout duration)."""
    return datetime.now(timezone.utc) + timedelta(
        seconds=settings.LOCKOUT_DURATION_SECONDS
    )
