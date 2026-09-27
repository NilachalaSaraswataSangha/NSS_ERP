"""
NSS ERP — Administration Pydantic schemas.

Request/response models for admin endpoints (Tier 5).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Request schemas ──────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    """POST /api/v1/admin/users"""
    person_pk: UUID = Field(
        ...,
        description="Person to create user account for (must exist in nss.person)",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Initial password (8–128 chars, 1 uppercase, 1 digit)",
    )
    force_password_change: bool = Field(
        default=True,
        description="Require password change on first login",
    )
    # Optional: also create sangha_sevi record
    create_sangha_sevi: bool = Field(
        default=False,
        description="If true, also create a Sangha Sevi (membership) record",
    )
    membership_type_pk: str | None = Field(
        None, description="UUID of membership_type master_data row (required if create_sangha_sevi)",
    )
    organization_pk: str | None = Field(
        None, description="UUID of organization/sakha (required if create_sangha_sevi)",
    )
    joining_date: str | None = Field(
        None, description="Joining date ISO (required if create_sangha_sevi)",
    )
    local_sakha_erp_id: str | None = Field(
        None, max_length=30,
        description="Local Sakha register number (raw, e.g. 1192). Backend composes <short_code><number>.",
    )


class ResetPasswordRequest(BaseModel):
    """POST /api/v1/admin/users/{user_account_pk}/reset-password"""
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="New password set by admin",
    )
    force_password_change: bool = Field(
        default=True,
        description="Require the user to change this password on next login",
    )


class UpdateStatusRequest(BaseModel):
    """PATCH /api/v1/admin/users/{user_account_pk}/status"""
    account_status: str = Field(
        ...,
        description="New status: ACTIVE, LOCKED, or INACTIVE",
        pattern="^(ACTIVE|LOCKED|INACTIVE)$",
    )


class AssignRoleRequest(BaseModel):
    """POST /api/v1/admin/users/{user_account_pk}/roles"""
    role_code: str = Field(
        ...,
        description="Role code from role_master (e.g., NSS_ERP_ADMIN)",
    )
    scope_level: str = Field(
        ...,
        description="Scope level: NSS-WIDE, KENDRA, ANCHALIKA, ZILLA, SAKHA, PATHA_CHAKRA",
        pattern="^(NSS-WIDE|KENDRA|ANCHALIKA|ZILLA|SAKHA|PATHA_CHAKRA)$",
    )
    organization_pk: UUID | None = Field(
        default=None,
        description="Organization PK (required unless scope_level is NSS-WIDE)",
    )


class CreateSanghaSeviRequest(BaseModel):
    """POST /api/v1/admin/sangha-sevi — standalone SS membership creation."""
    person_pk: UUID = Field(
        ..., description="Person to create Sangha Sevi record for",
    )
    membership_type_pk: str = Field(
        ..., description="UUID of membership_type master_data row",
    )
    organization_pk: str | None = Field(
        None,
        description=(
            "UUID of organization/sakha. Optional: a single-Sakha admin has "
            "it auto-resolved server-side; an NSS-wide or multi-Sakha admin "
            "must supply it."
        ),
    )
    joining_date: str = Field(
        ..., description="Joining date ISO (YYYY-MM-DD)",
    )
    local_sakha_erp_id: str | None = Field(
        None, max_length=30,
        description="Local Sakha register number (raw, e.g. 1192). Backend composes <short_code><number>.",
    )
    # Optional: also create a login (user account) for this person. Because
    # login is by sangha_sevi_id, an account is only usable once the person
    # is a Sangha Sevi — so the Sangha Sevi flow is the natural place to
    # offer account creation (rather than the person-anchored Create User
    # flow). The account branch itself requires ADMIN_USER_MANAGE.
    create_user_account: bool = Field(
        default=False,
        description="If true, also create a login/user account for this person.",
    )
    password: str | None = Field(
        None, min_length=8, max_length=128,
        description="Initial password (required if create_user_account; 8–128 chars, 1 uppercase, 1 digit).",
    )
    force_password_change: bool = Field(
        default=True,
        description="Require password change on first login (only used if create_user_account).",
    )


class UserAccountResponse(BaseModel):
    """Single user account in list and detail views."""
    user_account_pk: UUID
    person_pk: UUID
    person_id: str | None = None
    sangha_sevi_id: str | None = None
    sangha_sevi_id_generated: str | None = None  # Set only when SS was just created
    person_name: str | None = None
    organization_name: str | None = None
    local_sakha_erp_id: str | None = None
    darshak_local_number: str | None = None
    account_status: str
    force_password_change: bool
    last_login_at: datetime | None = None
    password_expires_at: datetime | None = None
    created_at: datetime
    is_active: bool


class UserListResponse(BaseModel):
    """GET /api/v1/admin/users — paginated list."""
    users: list[UserAccountResponse]
    total: int
    page: int
    page_size: int


class RoleAssignmentResponse(BaseModel):
    """A single role assignment with scope."""
    user_role_pk: UUID
    role_code: str
    role_name: str
    scope_level: str | None = None
    organization_pk: UUID | None = None
    organization_name: str | None = None
    assigned_at: datetime
    is_active: bool


class UserDetailResponse(BaseModel):
    """GET /api/v1/admin/users/{user_account_pk} — full detail."""
    user_account_pk: UUID
    person_pk: UUID
    person_id: str | None = None
    sangha_sevi_id: str | None = None
    person_name: str | None = None
    organization_name: str | None = None
    local_sakha_erp_id: str | None = None
    darshak_local_number: str | None = None
    account_status: str
    force_password_change: bool
    last_login_at: datetime | None = None
    password_expires_at: datetime | None = None
    failed_login_attempts: int
    locked_until: datetime | None = None
    created_at: datetime
    is_active: bool
    roles: list[RoleAssignmentResponse]


class CreateSanghaSeviResponse(BaseModel):
    """POST /api/v1/admin/sangha-sevi — response."""
    sangha_sevi_pk: UUID
    sangha_sevi_id: str
    person_pk: UUID
    person_name: str | None = None
    organization_name: str | None = None
    # Set only when a login account was bundled into this SS creation.
    user_account_pk: UUID | None = None
