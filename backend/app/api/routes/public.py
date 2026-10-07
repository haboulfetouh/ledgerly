"""Unauthenticated endpoints — must exist for the pre-login, tenant-branded
login page (see plan G3/G4). Never return anything beyond cosmetic branding
here; no tenant data of any real sensitivity belongs on this router.
"""

import mimetypes

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.tenant import Tenant
from app.schemas.tenant import TenantPublicOut
from app.services.storage.minio_client import download_document

router = APIRouter(prefix="/public/tenants", tags=["public"])


def _get_tenant_by_slug_or_404(db: Session, slug: str) -> Tenant:
    tenant = db.execute(select(Tenant).where(Tenant.slug == slug)).scalar_one_or_none()
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such workspace")
    return tenant


@router.get("/{slug}", response_model=TenantPublicOut)
def get_public_tenant(slug: str, db: Session = Depends(get_db)) -> TenantPublicOut:
    tenant = _get_tenant_by_slug_or_404(db, slug)
    return TenantPublicOut(
        name=tenant.name,
        slug=tenant.slug,
        primary_color=tenant.primary_color,
        has_logo=bool(tenant.logo_object_key),
    )


@router.get("/{slug}/logo")
def get_public_tenant_logo(slug: str, db: Session = Depends(get_db)) -> Response:
    tenant = _get_tenant_by_slug_or_404(db, slug)
    if not tenant.logo_object_key:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This workspace has no logo set")

    content = download_document(tenant.logo_object_key)
    content_type = mimetypes.guess_type(tenant.logo_object_key)[0] or "application/octet-stream"
    return Response(content=content, media_type=content_type)
