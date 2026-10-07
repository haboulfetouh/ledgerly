from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_role
from app.db.session import get_db
from app.models.erp_connection import ErpConnection
from app.models.invoice import Invoice, InvoiceStatus
from app.models.tenant import Tenant
from app.schemas.tenant import (
    AdminPasswordResetRequest,
    TenantAdminOut,
    TenantCreateRequest,
    TenantDetailOut,
    TenantPlanUpdate,
    TenantStatsOut,
)
from app.services.auth.keycloak_admin import KeycloakAdminClient
from app.services.tenants.onboarding import onboard_tenant

router = APIRouter(prefix="/platform/tenants", tags=["platform"])


@router.get("", response_model=list[TenantAdminOut])
def list_tenants(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("platform_admin")),
) -> list[Tenant]:
    return list(db.execute(select(Tenant).order_by(Tenant.created_at.desc())).scalars().all())


@router.post("", response_model=TenantAdminOut, status_code=status.HTTP_201_CREATED)
def create_tenant(
    payload: TenantCreateRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("platform_admin")),
) -> Tenant:
    try:
        return onboard_tenant(
            db,
            name=payload.name,
            slug=payload.slug,
            admin_email=payload.admin_email,
            admin_password=payload.admin_password,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, f"Slug '{payload.slug}' is already taken") from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc


def _get_tenant_or_404(db: Session, tenant_id: str) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant not found")
    return tenant


@router.get("/{tenant_id}", response_model=TenantDetailOut)
def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("platform_admin")),
) -> TenantDetailOut:
    tenant = _get_tenant_or_404(db, tenant_id)

    status_counts = dict(
        db.execute(
            select(Invoice.status, func.count())
            .where(Invoice.tenant_id == tenant_id)
            .group_by(Invoice.status)
        ).all()
    )
    invoices_total = sum(status_counts.values())
    invoices_processed = invoices_total - status_counts.get(InvoiceStatus.PROCESSING.value, 0)
    erp_connected = (
        db.execute(select(ErpConnection.id).where(ErpConnection.tenant_id == tenant_id).limit(1)).first()
        is not None
    )

    keycloak_users = KeycloakAdminClient().list_users(tenant_id)
    admin_user = next((u for u in keycloak_users if "admin" in u["roles"]), None)

    return TenantDetailOut(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan=tenant.plan,
        created_at=tenant.created_at,
        admin_email=admin_user["email"] if admin_user else None,
        stats=TenantStatsOut(
            invoices_total=invoices_total,
            invoices_processed=invoices_processed,
            invoices_needs_review=status_counts.get(InvoiceStatus.NEEDS_REVIEW.value, 0),
            invoices_exception=status_counts.get(InvoiceStatus.EXCEPTION.value, 0),
            invoices_posted=status_counts.get(InvoiceStatus.POSTED.value, 0),
            user_count=len(keycloak_users),
            erp_connected=erp_connected,
        ),
    )


@router.patch("/{tenant_id}", response_model=TenantAdminOut)
def update_tenant_plan(
    tenant_id: str,
    payload: TenantPlanUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("platform_admin")),
) -> Tenant:
    tenant = _get_tenant_or_404(db, tenant_id)
    tenant.plan = payload.plan
    db.commit()
    db.refresh(tenant)
    return tenant


@router.post("/{tenant_id}/reset-admin-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_tenant_admin_password(
    tenant_id: str,
    payload: AdminPasswordResetRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("platform_admin")),
) -> None:
    _get_tenant_or_404(db, tenant_id)

    keycloak = KeycloakAdminClient()
    admin_users = [u for u in keycloak.list_users(tenant_id) if "admin" in u["roles"]]
    if not admin_users:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This tenant has no admin user to reset")

    for admin_user in admin_users:
        keycloak.set_user_password(admin_user["id"], payload.password)
