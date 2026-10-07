from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk

MODULES = ["dashboard", "invoices", "exceptions", "approvals", "audit_log", "erp_connectors", "users", "branding"]

DEFAULT_ROLE_MODULES: dict[str, list[str]] = {
    "bookkeeper": ["dashboard", "invoices", "exceptions"],
    "accountant_manager": ["dashboard", "invoices", "exceptions", "approvals", "erp_connectors"],
    "admin": list(MODULES),
    "auditor": ["dashboard", "audit_log"],
}


class RoleModulePermission(Base, TenantScopedMixin, TimestampMixin):
    """A row's presence means the role can see that module for this tenant.
    `admin` and `platform_admin` always bypass this check (see
    core/security.py require_module) — the matrix only controls page
    visibility for the other roles, never the admin's own access.
    """

    __tablename__ = "role_module_permissions"
    __table_args__ = (UniqueConstraint("tenant_id", "role", "module", name="uq_role_module_tenant"),)

    id: Mapped[str] = uuid_pk()
    role: Mapped[str] = mapped_column(String(32))
    module: Mapped[str] = mapped_column(String(32))
