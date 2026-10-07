from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.role_permission import MODULES, RoleModulePermission

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    if user.has_role("admin") or user.has_role("platform_admin"):
        modules = list(MODULES)
    else:
        rows = db.execute(
            select(RoleModulePermission.module).where(
                RoleModulePermission.tenant_id == user.tenant_id,
                RoleModulePermission.role.in_(user.roles),
            )
        ).scalars().all()
        modules = sorted(set(rows))

    return {
        "subject": user.subject,
        "tenant_id": user.tenant_id,
        "roles": user.roles,
        "email": user.email,
        "modules": modules,
    }
