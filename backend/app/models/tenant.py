from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class Tenant(Base, TimestampMixin):
    __tablename__ = "tenants"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str]
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    region: Mapped[str | None] = mapped_column(default=None)
    plan: Mapped[str] = mapped_column(default="starter")

    # Whitelabel branding
    primary_color: Mapped[str] = mapped_column(String(16), default="#059669")
    logo_object_key: Mapped[str | None] = mapped_column(default=None)
