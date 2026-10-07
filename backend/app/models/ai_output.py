from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class AiOutput(Base, TenantScopedMixin, TimestampMixin):
    """Every AI extraction/explanation call, kept for audit (PRD Section 12)."""

    __tablename__ = "ai_outputs"

    id: Mapped[str] = uuid_pk()
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)
    stage: Mapped[str] = mapped_column(String(32))  # extraction | explanation | duplicate_check
    model_name: Mapped[str] = mapped_column(String(64))
    confidence_overall: Mapped[float | None] = mapped_column(default=None)
    field_confidences: Mapped[dict | None] = mapped_column(JSON, default=None)
    raw_response: Mapped[dict | None] = mapped_column(JSON, default=None)
