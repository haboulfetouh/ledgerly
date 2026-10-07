"""Three-way match engine.

Deliberately deterministic/rule-based at its core (PRD Section 10 and 11):
the AI layer only ever explains an already-computed exception in plain
language (see extraction/claude_explainer.py) — it never itself decides
Matched vs. Exception. That is what stops an adversarial or malformed
document from talking its way into a false "Matched" status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_json
from app.models.erp_connection import ErpConnection
from app.models.goods_receipt import GoodsReceipt
from app.models.invoice import Invoice, InvoiceStatus
from app.models.match_record import MatchRecord
from app.models.matching_rule import MatchingRule
from app.models.purchase_order import PurchaseOrder
from app.services.connectors.base import GoodsReceiptData, PurchaseOrderData
from app.services.connectors.registry import build_connector
from app.services.matching.duplicate import find_duplicate

DEFAULT_PRICE_VARIANCE_TOLERANCE_PCT = 2.0
DEFAULT_QUANTITY_VARIANCE_TOLERANCE_PCT = 2.0


@dataclass
class MatchOutcome:
    status: str  # InvoiceStatus.MATCHED | MATCHED_TOLERANCE | EXCEPTION
    discrepancy_detail: str | None = None
    fields: dict = field(default_factory=dict)  # grounding data for the explanation step


def _get_tolerance(db: Session, tenant_id: str, rule_type: str, default: float) -> float:
    stmt = select(MatchingRule).where(
        MatchingRule.tenant_id == tenant_id, MatchingRule.rule_type == rule_type
    )
    rule = db.execute(stmt).scalar_one_or_none()
    return float(rule.tolerance_percent) if rule else default


def _get_active_connector(db: Session, tenant_id: str):
    stmt = (
        select(ErpConnection)
        .where(ErpConnection.tenant_id == tenant_id, ErpConnection.status == "connected")
        .order_by(ErpConnection.updated_at.desc())
    )
    connection = db.execute(stmt).scalar_one_or_none()
    if connection is None:
        return None
    config = decrypt_json(connection.config_encrypted) if connection.config_encrypted else {}
    return build_connector(connection.connector_type, config), connection


def _cache_purchase_order(db: Session, tenant_id: str, connection_id: str, po: PurchaseOrderData) -> None:
    stmt = select(PurchaseOrder).where(
        PurchaseOrder.tenant_id == tenant_id, PurchaseOrder.po_number == po.po_number
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        row = PurchaseOrder(tenant_id=tenant_id, erp_connection_id=connection_id, po_number=po.po_number)
        db.add(row)
    row.vendor_name = po.vendor_name
    row.total_amount = po.total_amount
    row.line_items = [li.__dict__ for li in po.line_items]
    row.synced_at = datetime.now(timezone.utc)


def _cache_goods_receipt(db: Session, tenant_id: str, connection_id: str, grn: GoodsReceiptData) -> None:
    stmt = select(GoodsReceipt).where(
        GoodsReceipt.tenant_id == tenant_id, GoodsReceipt.po_number == grn.po_number
    )
    row = db.execute(stmt).scalar_one_or_none()
    if row is None:
        row = GoodsReceipt(tenant_id=tenant_id, erp_connection_id=connection_id, po_number=grn.po_number, grn_number=grn.grn_number)
        db.add(row)
    row.received_quantities = grn.received_quantities
    row.synced_at = datetime.now(timezone.utc)


def _evaluate(db: Session, tenant_id: str, invoice: Invoice, po: PurchaseOrderData, grn: GoodsReceiptData) -> MatchOutcome:
    price_tolerance = _get_tolerance(db, tenant_id, "price_variance", DEFAULT_PRICE_VARIANCE_TOLERANCE_PCT)
    quantity_tolerance = _get_tolerance(db, tenant_id, "quantity_variance", DEFAULT_QUANTITY_VARIANCE_TOLERANCE_PCT)

    invoice_total = float(invoice.total_amount) if invoice.total_amount is not None else None
    po_total = po.total_amount

    price_variance_pct = 0.0
    if invoice_total is not None and po_total:
        price_variance_pct = abs(invoice_total - po_total) / po_total * 100

    invoiced_qty = sum(float(li.quantity or 0) for li in invoice.line_items) or None
    received_qty = sum(float(q.get("quantity") or 0) for q in grn.received_quantities) or None

    quantity_variance_pct = 0.0
    if invoiced_qty is not None and received_qty:
        quantity_variance_pct = abs(invoiced_qty - received_qty) / received_qty * 100

    fields = {
        "invoice_total": invoice_total,
        "po_total": po_total,
        "price_variance_pct": round(price_variance_pct, 2),
        "invoiced_qty": invoiced_qty,
        "received_qty": received_qty,
        "quantity_variance_pct": round(quantity_variance_pct, 2),
    }

    if invoiced_qty is not None and received_qty is not None and invoiced_qty > received_qty and quantity_variance_pct > quantity_tolerance:
        return MatchOutcome(
            status=InvoiceStatus.EXCEPTION.value,
            discrepancy_detail=(
                f"Invoiced quantity {invoiced_qty:g} exceeds GRN-received quantity "
                f"{received_qty:g} by {quantity_variance_pct:.1f}%."
            ),
            fields=fields,
        )

    if price_variance_pct > price_tolerance:
        return MatchOutcome(
            status=InvoiceStatus.EXCEPTION.value,
            discrepancy_detail=(
                f"Invoice total {invoice_total:,.2f} differs from PO total {po_total:,.2f} "
                f"by {price_variance_pct:.1f}%, exceeding the {price_tolerance:.1f}% tolerance."
            ),
            fields=fields,
        )

    if price_variance_pct > 0 or quantity_variance_pct > 0:
        return MatchOutcome(
            status=InvoiceStatus.MATCHED_TOLERANCE.value,
            discrepancy_detail=(
                f"Within tolerance: {price_variance_pct:.1f}% price variance, "
                f"{quantity_variance_pct:.1f}% quantity variance."
            ),
            fields=fields,
        )

    return MatchOutcome(status=InvoiceStatus.MATCHED.value, fields=fields)


def run_matching(db: Session, invoice: Invoice) -> tuple[MatchRecord, dict]:
    """Runs duplicate detection then three-way match for a single invoice,
    updates invoice.status, and returns the created MatchRecord plus the
    supporting numeric fields (for the explanation step to ground its
    output in, without re-deriving them). Never raises for expected
    "can't match yet" conditions — those become Exception records with a
    clear reason, per PRD's "ambiguous cases default to Exception, never
    default to Matched."
    """
    tenant_id = invoice.tenant_id

    duplicate = find_duplicate(db, tenant_id, invoice)
    if duplicate:
        outcome = MatchOutcome(
            status=InvoiceStatus.EXCEPTION.value,
            discrepancy_detail=duplicate.reason,
            fields={"duplicate_of_invoice_id": duplicate.existing_invoice_id},
        )
    elif not invoice.po_number:
        outcome = MatchOutcome(
            status=InvoiceStatus.EXCEPTION.value,
            discrepancy_detail="Invoice has no purchase order number — cannot be matched automatically.",
        )
    else:
        active = _get_active_connector(db, tenant_id)
        if active is None:
            outcome = MatchOutcome(
                status=InvoiceStatus.EXCEPTION.value,
                discrepancy_detail="No connected ERP is configured for this tenant — cannot verify against a purchase order.",
            )
        else:
            connector, connection = active
            po = connector.fetch_purchase_order(invoice.po_number)
            if po is None:
                outcome = MatchOutcome(
                    status=InvoiceStatus.EXCEPTION.value,
                    discrepancy_detail=f"Purchase order {invoice.po_number} was not found in the ERP.",
                )
            else:
                _cache_purchase_order(db, tenant_id, connection.id, po)
                grn = connector.fetch_goods_receipt(invoice.po_number)
                if grn is None:
                    outcome = MatchOutcome(
                        status=InvoiceStatus.EXCEPTION.value,
                        discrepancy_detail=f"No goods receipt found for purchase order {invoice.po_number} — goods may not have been received yet.",
                    )
                else:
                    _cache_goods_receipt(db, tenant_id, connection.id, grn)
                    outcome = _evaluate(db, tenant_id, invoice, po, grn)

    match_record = MatchRecord(
        tenant_id=tenant_id,
        invoice_id=invoice.id,
        status=outcome.status,
        discrepancy_detail=outcome.discrepancy_detail,
    )
    db.add(match_record)
    invoice.status = outcome.status
    db.flush()
    return match_record, outcome.fields
