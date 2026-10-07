from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk
from datetime import datetime


class ErpConnection(Base, TenantScopedMixin, TimestampMixin):
    """A tenant's configured ERP connector instance.

    `config_encrypted` holds a Fernet-encrypted JSON blob of whatever
    fields that connector type's config_schema requires (see
    services/connectors/base.py) — credentials are never stored in
    plaintext (PRD backlog LED-030).
    """

    __tablename__ = "erp_connections"

    id: Mapped[str] = uuid_pk()
    connector_type: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str] = mapped_column(String(128))
    config_encrypted: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[str] = mapped_column(String(32), default="not_configured")
    last_tested_at: Mapped[datetime | None] = mapped_column(default=None)
    last_test_result: Mapped[str | None] = mapped_column(Text, default=None)
