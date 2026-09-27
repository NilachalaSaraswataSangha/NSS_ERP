"""
NSS ERP — Authentication Pydantic schemas.

Request/response models for auth endpoints (Tier 5).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """POST /api/v1/auth/login"""
    login_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description=(
            "Sangha Sevi ID (e.g., SS1) or Person ID (e.g., P1). "
            "Case-insensitive."
        ),
        examples=["SS1", "P1"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Plaintext password",
    )


class RefreshRequest(BaseModel):
    """POST /api/v1/auth/refresh"""
    refresh_token: str = Field(
        ...,
        description="Valid refresh token from a previous login",
    )


class ChangePasswordRequest(BaseModel):
    """POST /api/v1/auth/change-password"""
    current_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Current password for verification",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8–128 chars, 1 uppercase, 1 digit)",
    )


class ForgotPasswordRequest(BaseModel):
    """POST /api/v1/auth/forgot-password"""
    login_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description=(
            "Sangha Sevi ID (e.g., SS1) or Person ID (e.g., P1). "
            "Case-insensitive."
        ),
        examples=["SS1", "P1"],
    )


class ResetPasswordRequest(BaseModel):
    """POST /api/v1/auth/reset-password"""
    login_id: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Same login ID used in the forgot-password request.",
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
        description="6-digit OTP received for password reset.",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password (8–128 chars, 1 uppercase, 1 digit)",
    )


# ── Response schemas ─────────────────────────────────────────────────────

class LoginResponse(BaseModel):
    """Successful login response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(
        description="Access token lifetime in seconds"
    )
    force_password_change: bool = Field(
        default=False,
        description="True if the user must change password before proceeding",
    )
    password_expiry_warning: bool = Field(
        default=False,
        description="True if password expires within 30 days",
    )


class RefreshResponse(BaseModel):
    """Successful token refresh response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class ScopeResponse(BaseModel):
    """A single role-scope assignment."""
    role_code: str
    role_name: str | None = None
    scope_level: str
    organization_pk: UUID | None = None
    organization_name: str | None = None
    organization_type_code: str | None = None


class MeResponse(BaseModel):
    """GET /api/v1/auth/me — current user profile."""
    user_account_pk: UUID
    person_pk: UUID
    sangha_sevi_id: str
    person_name: str | None = None
    local_sakha_erp_id: str | None = None
    sakha_name: str | None = None
    account_status: str
    force_password_change: bool
    password_expires_at: datetime | None = None
    last_login_at: datetime | None = None
    permissions: list[str]
    scopes: list[ScopeResponse]


class MessageResponse(BaseModel):
    """Generic success message."""
    message: str


class UpdateProfileRequest(BaseModel):
    """PATCH /api/v1/auth/profile — update own profile."""
    mobile_number: str | None = Field(None, max_length=20)
    country_phone_code: str | None = Field(None, max_length=10)
    email: str | None = Field(None, max_length=255)
    date_of_birth: str | None = Field(None)


class ForgotPasswordResponse(BaseModel):
    """POST /api/v1/auth/forgot-password — response."""
    message: str
    masked_contact: str | None = Field(
        None,
        description="Masked email or mobile where OTP would be sent (future).",
    )
    otp_debug: str | None = Field(
        None,
        description=(
            "OTP in plaintext — DEVELOPMENT ONLY. "
            "Will be removed when email/SMS service is integrated."
        ),
    )
