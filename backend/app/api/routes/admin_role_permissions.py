from fastapi import APIRouter, Depends
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_role
from app.db.session import get_db
from app.models.role_permission import MODULES, RoleModulePermission
from app.schemas.role_permission import RolePermissionsOut, RolePermissionsUpdate

router = APIRouter(prefix="/admin/role-permissions", tags=["admin-role-permissions"])

# admin is intentionally excluded — it always has every module (see
# core/security.py require_module) and is not itself configurable, so a
# tenant admin can never accidentally lock themselves out.
_CONFIGURABLE_ROLES = ["bookkeeper", "accountant_manager", "auditor"]


@router.get("", response_model=RolePermissionsOut)
def get_role_permissions(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
) -> RolePermissionsOut:
    rows = db.execute(
        select(RoleModulePermission).where(RoleModulePermission.tenant_id == user.tenant_id)
    ).scalars().all()

    matrix: dict[str, list[str]] = {role: [] for role in _CONFIGURABLE_ROLES}
    for row in rows:
        if row.role in matrix:
            matrix[row.role].append(row.module)

    return RolePermissionsOut(modules=MODULES, matrix=matrix)


@router.put("", response_model=RolePermissionsOut)
def update_role_permissions(
    payload: RolePermissionsUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
) -> RolePermissionsOut:
    db.execute(
        delete(RoleModulePermission).where(
            RoleModulePermission.tenant_id == user.tenant_id,
            RoleModulePermission.role.in_(_CONFIGURABLE_ROLES),
        )
    )
    for role, modules in payload.matrix.items():
        if role not in _CONFIGURABLE_ROLES:
            continue
        for module in modules:
            if module not in MODULES:
                continue
            db.add(RoleModulePermission(tenant_id=user.tenant_id, role=role, module=module))
    db.commit()

    return get_role_permissions(db=db, user=user)
