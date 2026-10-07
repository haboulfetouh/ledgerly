from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, get_current_user
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantMeOut

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("/me", response_model=TenantMeOut)
def get_my_tenant(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> TenantMeOut:
    tenant = db.execute(select(Tenant).where(Tenant.id == user.tenant_id)).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return TenantMeOut(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        primary_color=tenant.primary_color,
        has_logo=bool(tenant.logo_object_key),
        plan=tenant.plan,
    )
