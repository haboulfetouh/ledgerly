"""Shared tenant-onboarding logic — used by both the `bootstrap-tenant` CLI
(for the very first tenant) and the platform portal's tenant-creation
endpoint (see api/routes/platform.py), so the two never drift apart.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models.role_permission import DEFAULT_ROLE_MODULES, RoleModulePermission
from app.models.tenant import Tenant
from app.services.auth.keycloak_admin import KeycloakAdminClient


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "tenant"


def onboard_tenant(
    db: Session,
    *,
    name: str,
    slug: str,
    admin_email: str,
    admin_password: str,
) -> Tenant:
    tenant = Tenant(name=name, slug=slug)
    db.add(tenant)
    db.flush()

    for role, modules in DEFAULT_ROLE_MODULES.items():
        for module in modules:
            db.add(RoleModulePermission(tenant_id=tenant.id, role=role, module=module))

    KeycloakAdminClient().create_user(
        email=admin_email,
        password=admin_password,
        tenant_id=tenant.id,
        role="admin",
    )

    db.commit()
    db.refresh(tenant)
    return tenant
