from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class GoodsReceipt(Base, TenantScopedMixin, TimestampMixin):
    """Read-only mirror of GRN data pulled from the tenant's ERP connector."""

    __tablename__ = "goods_receipts"

    id: Mapped[str] = uuid_pk()
    erp_connection_id: Mapped[str] = mapped_column(ForeignKey("erp_connections.id"), index=True)
    grn_number: Mapped[str] = mapped_column(String(64), index=True)
    po_number: Mapped[str] = mapped_column(String(64), index=True)
    received_quantities: Mapped[list | None] = mapped_column(JSON, default=None)
    synced_at: Mapped[datetime | None] = mapped_column(default=None)
