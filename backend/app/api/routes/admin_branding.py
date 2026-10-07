from fastapi import APIRouter, Depends, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_module
from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantMeOut
from app.services.storage.minio_client import upload_document

router = APIRouter(prefix="/admin/branding", tags=["admin-branding"])

_ALLOWED_LOGO_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/svg+xml": "svg"}


@router.put("", response_model=TenantMeOut)
async def update_branding(
    primary_color: str = Form(...),
    logo: UploadFile | None = None,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_module("branding")),
) -> Tenant:
    tenant = db.execute(select(Tenant).where(Tenant.id == user.tenant_id)).scalar_one()

    tenant.primary_color = primary_color

    if logo is not None and logo.filename:
        ext = _ALLOWED_LOGO_TYPES.get(logo.content_type or "")
        if ext:
            key = f"branding/{tenant.id}/logo.{ext}"
            content = await logo.read()
            upload_document(key, content, logo.content_type or "application/octet-stream")
            tenant.logo_object_key = key

    db.commit()
    db.refresh(tenant)

    return TenantMeOut(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        primary_color=tenant.primary_color,
        has_logo=bool(tenant.logo_object_key),
        plan=tenant.plan,
    )
