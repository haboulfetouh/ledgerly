from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class PurchaseOrder(Base, TenantScopedMixin, TimestampMixin):
    """Read-only mirror of PO data pulled from the tenant's ERP connector.

    Not the system of record (the ERP is) — purged on tenant offboarding,
    refreshed on the connector's sync cadence (PRD Section 12).
    """

    __tablename__ = "purchase_orders"

    id: Mapped[str] = uuid_pk()
    erp_connection_id: Mapped[str] = mapped_column(ForeignKey("erp_connections.id"), index=True)
    po_number: Mapped[str] = mapped_column(String(64), index=True)
    vendor_name: Mapped[str | None] = mapped_column(default=None)
    total_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), default=None)
    line_items: Mapped[list | None] = mapped_column(JSON, default=None)
    synced_at: Mapped[datetime | None] = mapped_column(default=None)
