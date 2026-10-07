from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class User(Base, TenantScopedMixin, TimestampMixin):
    """Local cache of Keycloak-provisioned users, for display/admin listing.

    Keycloak remains the source of truth for credentials and role
    assignment; this row is denormalized for fast tenant-scoped listing.
    """

    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("keycloak_subject", name="uq_users_keycloak_subject"),)

    id: Mapped[str] = uuid_pk()
    keycloak_subject: Mapped[str] = mapped_column(String(64), index=True)
    email: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(default=None)
    role: Mapped[str] = mapped_column(String(32))
