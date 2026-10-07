from datetime import datetime

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class ApprovalRecord(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "approval_records"

    id: Mapped[str] = uuid_pk()
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    approver_subject: Mapped[str] = mapped_column(String(64))
    decision: Mapped[str] = mapped_column(String(16))  # approved | rejected
    comment: Mapped[str | None] = mapped_column(Text, default=None)
    decided_at: Mapped[datetime | None] = mapped_column(default=None)
