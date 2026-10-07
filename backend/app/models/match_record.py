from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class MatchRecord(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "match_records"

    id: Mapped[str] = uuid_pk()
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))  # matched | matched_tolerance | exception
    discrepancy_detail: Mapped[str | None] = mapped_column(Text, default=None)
    explanation: Mapped[str | None] = mapped_column(Text, default=None)

    resolved_by: Mapped[str | None] = mapped_column(default=None)  # keycloak subject
    resolution_action: Mapped[str | None] = mapped_column(default=None)  # accept|override|escalate
    resolution_reason: Mapped[str | None] = mapped_column(Text, default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(default=None)
