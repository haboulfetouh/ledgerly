from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import (
    admin_branding,
    admin_erp,
    admin_role_permissions,
    admin_users,
    audit_log,
    auth,
    dashboard,
    health,
    invoices,
    platform,
    public,
    tenants,
)

app = FastAPI(title="Ledgerly AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(admin_erp.router)
app.include_router(audit_log.router)
app.include_router(dashboard.router)
app.include_router(public.router)
app.include_router(tenants.router)
app.include_router(platform.router)
app.include_router(admin_role_permissions.router)
app.include_router(admin_users.router)
app.include_router(admin_branding.router)
