import enum
from datetime import date

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class InvoiceStatus(str, enum.Enum):
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    EXTRACTED = "extracted"
    MATCHED = "matched"
    MATCHED_TOLERANCE = "matched_tolerance"
    EXCEPTION = "exception"
    APPROVED = "approved"
    POSTED = "posted"
    REJECTED = "rejected"


class Invoice(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "invoices"

    id: Mapped[str] = uuid_pk()

    # Source document
    source_filename: Mapped[str]
    source_document_key: Mapped[str]  # MinIO object key: {tenant_id}/{invoice_id}/{filename}
    source: Mapped[str] = mapped_column(String(32), default="upload")  # upload | email

    # Extracted header fields (nullable until extraction completes)
    vendor_name: Mapped[str | None] = mapped_column(default=None)
    invoice_number: Mapped[str | None] = mapped_column(default=None)
    invoice_date: Mapped[date | None] = mapped_column(default=None)
    due_date: Mapped[date | None] = mapped_column(default=None)
    currency: Mapped[str | None] = mapped_column(String(8), default=None)
    subtotal: Mapped[float | None] = mapped_column(Numeric(14, 2), default=None)
    tax_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), default=None)
    total_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), default=None)
    po_number: Mapped[str | None] = mapped_column(default=None)

    status: Mapped[str] = mapped_column(String(32), default=InvoiceStatus.PROCESSING.value)
    needs_review_reason: Mapped[str | None] = mapped_column(Text, default=None)
    processing_error: Mapped[str | None] = mapped_column(Text, default=None)

    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )
    ai_outputs: Mapped[list["AiOutput"]] = relationship(
        order_by="AiOutput.created_at.desc()",
        primaryjoin="Invoice.id == AiOutput.invoice_id",
        viewonly=True,
    )
    match_records: Mapped[list["MatchRecord"]] = relationship(
        order_by="MatchRecord.created_at.desc()",
        primaryjoin="Invoice.id == MatchRecord.invoice_id",
        viewonly=True,
    )
    approval_records: Mapped[list["ApprovalRecord"]] = relationship(
        order_by="ApprovalRecord.created_at.desc()",
        primaryjoin="Invoice.id == ApprovalRecord.invoice_id",
        viewonly=True,
    )


class InvoiceLineItem(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "invoice_line_items"

    id: Mapped[str] = uuid_pk()
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), index=True)

    description: Mapped[str | None] = mapped_column(Text, default=None)
    quantity: Mapped[float | None] = mapped_column(Numeric(14, 4), default=None)
    unit_price: Mapped[float | None] = mapped_column(Numeric(14, 4), default=None)
    line_total: Mapped[float | None] = mapped_column(Numeric(14, 2), default=None)

    invoice: Mapped["Invoice"] = relationship(back_populates="line_items")
