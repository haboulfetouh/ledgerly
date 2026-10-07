from datetime import datetime

from pydantic import BaseModel


class TenantPublicOut(BaseModel):
    name: str
    slug: str
    primary_color: str
    has_logo: bool


class TenantMeOut(TenantPublicOut):
    id: str
    plan: str


class TenantAdminOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    slug: str
    plan: str
    created_at: datetime


class TenantCreateRequest(BaseModel):
    name: str
    slug: str
    admin_email: str
    admin_password: str


class TenantStatsOut(BaseModel):
    invoices_total: int
    invoices_processed: int
    invoices_needs_review: int
    invoices_exception: int
    invoices_posted: int
    user_count: int
    erp_connected: bool


class TenantDetailOut(TenantAdminOut):
    admin_email: str | None
    stats: TenantStatsOut


class TenantPlanUpdate(BaseModel):
    plan: str


class AdminPasswordResetRequest(BaseModel):
    password: str
