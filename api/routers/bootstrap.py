"""
NSS ERP — Bootstrap RBAC endpoints.

Tier 0 read-only API:
  GET /api/v1/bootstrap/health
  GET /api/v1/bootstrap/roles
  GET /api/v1/bootstrap/permissions
  GET /api/v1/bootstrap/roles/{role_pk}/permissions

No authentication. No CRUD. No speculative permissions.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from api.database import check_connection, get_connection
from api.helpers import rows_to_models
from api.schemas.bootstrap import (
    HealthResponse,
    PermissionResponse,
    RoleResponse,
)

router = APIRouter(prefix="/api/v1/bootstrap", tags=["bootstrap"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """
    Liveness/readiness probe.

    Returns database connectivity status.
    Never exposes connection details, credentials, or error messages.
    """
    db_ok = check_connection()
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        database="connected" if db_ok else "unreachable",
    )


@router.get("/roles", response_model=list[RoleResponse])
def list_roles(conn=Depends(get_connection)) -> list[RoleResponse]:
    """
    Return all active roles from nss.role_master.

    Tier 0 state: 8 frozen roles.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT role_master_pk,
                   role_code,
                   role_name,
                   role_class,
                   scope_level,
                   description,
                   display_order,
                   is_active
              FROM nss.role_master
             WHERE is_active = TRUE
             ORDER BY display_order
            """
        )
        return rows_to_models(cur, RoleResponse)


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(conn=Depends(get_connection)) -> list[PermissionResponse]:
    """
    Return all active permissions from nss.permission_master.

    Tier 0 state: empty by design — permissions are populated
    progressively with each module's vertical-slice implementation.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT permission_master_pk,
                   permission_code,
                   permission_name,
                   module_code,
                   description,
                   display_order,
                   is_active
              FROM nss.permission_master
             WHERE is_active = TRUE
             ORDER BY module_code, display_order
            """
        )
        return rows_to_models(cur, PermissionResponse)


@router.get(
    "/roles/{role_pk}/permissions",
    response_model=list[PermissionResponse],
)
def list_role_permissions(
    role_pk: UUID,
    conn=Depends(get_connection),
) -> list[PermissionResponse]:
    """
    Return permissions assigned to a specific role via nss.role_permission.

    Tier 0 state: empty — no role-permission mappings exist yet.
    Returns 404 if the role_pk does not exist.
    """
    # Verify the role exists
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1
              FROM nss.role_master
             WHERE role_master_pk = %s
               AND is_active = TRUE
            """,
            (str(role_pk),),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Role not found")

    # Fetch permissions via the junction table
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT pm.permission_master_pk,
                   pm.permission_code,
                   pm.permission_name,
                   pm.module_code,
                   pm.description,
                   pm.display_order,
                   pm.is_active
              FROM nss.role_permission rp
              JOIN nss.permission_master pm
                ON pm.permission_master_pk = rp.permission_master_pk
             WHERE rp.role_master_pk = %s
               AND rp.is_active = TRUE
               AND pm.is_active = TRUE
             ORDER BY pm.module_code, pm.display_order
            """,
            (str(role_pk),),
        )
        return rows_to_models(cur, PermissionResponse)
