from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class InvoiceLineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    description: str | None
    quantity: float | None
    unit_price: float | None
    line_total: float | None


class AiOutputOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: str
    stage: str
    model_name: str
    confidence_overall: float | None
    field_confidences: dict | None
    created_at: datetime


class MatchRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    discrepancy_detail: str | None
    explanation: str | None
    resolved_by: str | None
    resolution_action: str | None
    resolution_reason: str | None
    resolved_at: datetime | None
    created_at: datetime


class ApprovalRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    approver_subject: str
    decision: str
    comment: str | None
    decided_at: datetime | None
    created_at: datetime


class InvoiceListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    vendor_name: str | None
    invoice_number: str | None
    invoice_date: date | None
    currency: str | None
    total_amount: float | None
    status: str
    created_at: datetime


class InvoiceDetailOut(InvoiceListItemOut):
    due_date: date | None
    subtotal: float | None
    tax_amount: float | None
    po_number: str | None
    source_filename: str
    needs_review_reason: str | None
    processing_error: str | None
    line_items: list[InvoiceLineItemOut] = []
    ai_outputs: list[AiOutputOut] = []
    match_records: list[MatchRecordOut] = []
    approval_records: list[ApprovalRecordOut] = []


class InvoiceUploadOut(BaseModel):
    id: str
    status: str


class ResolveExceptionRequest(BaseModel):
    action: Literal["accept", "override", "escalate"]
    reason: str | None = None


class ApprovalDecisionRequest(BaseModel):
    comment: str | None = None


class InvoiceFieldsUpdate(BaseModel):
    vendor_name: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency: str | None = None
    subtotal: float | None = None
    tax_amount: float | None = None
    total_amount: float | None = None
    po_number: str | None = None
