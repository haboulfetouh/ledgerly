from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class AuditLogEvent(Base, TenantScopedMixin, TimestampMixin):
    """Immutable activity trail. Never updated or deleted before retention
    expiry (PRD Section 12) — application code must only ever INSERT here.
    """

    __tablename__ = "audit_log_events"

    id: Mapped[str] = uuid_pk()
    actor_subject: Mapped[str | None] = mapped_column(String(64), default=None)  # null = system
    action: Mapped[str] = mapped_column(String(64))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(36))
    before: Mapped[dict | None] = mapped_column(JSON, default=None)
    after: Mapped[dict | None] = mapped_column(JSON, default=None)
