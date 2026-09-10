"""
NSS ERP — Pydantic response schemas for Bootstrap RBAC endpoints.

These schemas define the API contract. They deliberately exclude
audit columns (created_at, *_by_sangha_sevi_pk) — those are internal.

Raw psycopg2 returns dictionaries — no ORM objects — so
ConfigDict(from_attributes=True) is unnecessary.
"""

from uuid import UUID

from pydantic import BaseModel


class RoleResponse(BaseModel):
    """Single role from nss.role_master."""

    role_master_pk: UUID
    role_code: str
    role_name: str
    role_class: str
    scope_level: str | None
    description: str | None
    display_order: int
    is_active: bool


class PermissionResponse(BaseModel):
    """Single permission from nss.permission_master."""

    permission_master_pk: UUID
    permission_code: str
    permission_name: str
    module_code: str
    description: str | None
    display_order: int
    is_active: bool


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    database: str
