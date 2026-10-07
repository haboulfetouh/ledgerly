import logging
import mimetypes
from datetime import date, datetime

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.ai_output import AiOutput
from app.models.audit_log_event import AuditLogEvent
from app.models.invoice import Invoice, InvoiceLineItem, InvoiceStatus
from app.services.extraction.claude_explainer import explain_exception
from app.services.extraction.claude_extractor import extract_invoice_fields
from app.services.matching.engine import run_matching
from app.services.ocr.engine import get_ocr_engine
from app.services.storage.minio_client import download_document
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _write_system_audit(db, invoice: Invoice, action: str, after: dict) -> None:
    db.add(
        AuditLogEvent(
            tenant_id=invoice.tenant_id,
            actor_subject=None,  # system-generated, not a human action
            action=action,
            entity_type="invoice",
            entity_id=invoice.id,
            after=after,
        )
    )


def _run_matching_and_explain(db, invoice: Invoice) -> None:
    match_record, fields = run_matching(db, invoice)
    _write_system_audit(
        db,
        invoice,
        "invoice_matched",
        after={"status": match_record.status, "discrepancy_detail": match_record.discrepancy_detail},
    )
    if match_record.status == InvoiceStatus.EXCEPTION.value and match_record.discrepancy_detail:
        explanation = explain_exception(match_record.discrepancy_detail, fields)
        if explanation:
            match_record.explanation = explanation
            db.add(
                AiOutput(
                    tenant_id=invoice.tenant_id,
                    invoice_id=invoice.id,
                    stage="explanation",
                    model_name=get_settings().anthropic_explanation_model,
                    raw_response={"explanation": explanation, "discrepancy_detail": match_record.discrepancy_detail},
                )
            )


@celery_app.task(name="app.workers.tasks.ocr_and_extract_invoice")
def ocr_and_extract_invoice(invoice_id: str, tenant_id: str) -> None:
    db = SessionLocal()
    try:
        invoice = (
            db.query(Invoice)
            .filter(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
            .one_or_none()
        )
        if invoice is None:
            logger.error("Invoice %s not found for tenant %s", invoice_id, tenant_id)
            return

        try:
            file_bytes = download_document(invoice.source_document_key)
        except Exception:
            logger.exception("Failed to download document for invoice %s", invoice_id)
            invoice.status = InvoiceStatus.NEEDS_REVIEW.value
            invoice.processing_error = "Could not retrieve the uploaded document from storage."
            db.commit()
            return

        content_type = mimetypes.guess_type(invoice.source_filename)[0] or "application/pdf"

        try:
            ocr_result = get_ocr_engine().extract_text(file_bytes, content_type)
        except Exception:
            logger.exception("OCR failed for invoice %s", invoice_id)
            invoice.status = InvoiceStatus.NEEDS_REVIEW.value
            invoice.processing_error = "OCR could not process this document — it may be corrupt or unreadable."
            db.commit()
            return

        if not ocr_result.text.strip():
            invoice.status = InvoiceStatus.NEEDS_REVIEW.value
            invoice.needs_review_reason = "No text could be read from the document (illegible or blank)."
            db.commit()
            return

        extraction = extract_invoice_fields(ocr_result.text)

        if extraction is None:
            invoice.status = InvoiceStatus.NEEDS_REVIEW.value
            invoice.needs_review_reason = (
                "AI extraction is not configured (missing ANTHROPIC_API_KEY) — "
                "please enter invoice details manually."
            )
            db.commit()
            return

        fields = extraction.fields
        invoice.vendor_name = fields.get("vendor_name")
        invoice.invoice_number = fields.get("invoice_number")
        invoice.invoice_date = _parse_date(fields.get("invoice_date"))
        invoice.due_date = _parse_date(fields.get("due_date"))
        invoice.currency = fields.get("currency")
        invoice.subtotal = fields.get("subtotal")
        invoice.tax_amount = fields.get("tax_amount")
        invoice.total_amount = fields.get("total_amount")
        invoice.po_number = fields.get("po_number")

        for item in fields.get("line_items") or []:
            db.add(
                InvoiceLineItem(
                    tenant_id=tenant_id,
                    invoice_id=invoice.id,
                    description=item.get("description"),
                    quantity=item.get("quantity"),
                    unit_price=item.get("unit_price"),
                    line_total=item.get("line_total"),
                )
            )

        db.add(
            AiOutput(
                tenant_id=tenant_id,
                invoice_id=invoice.id,
                stage="extraction",
                model_name=extraction.model_name,
                confidence_overall=extraction.overall_confidence,
                field_confidences=extraction.field_confidences,
                raw_response=extraction.raw_response,
            )
        )

        if extraction.low_confidence_fields:
            invoice.status = InvoiceStatus.NEEDS_REVIEW.value
            invoice.needs_review_reason = (
                "Low-confidence fields need manual confirmation: "
                + ", ".join(extraction.low_confidence_fields)
            )
            _write_system_audit(
                db, invoice, "invoice_extracted",
                after={"status": invoice.status, "confidence": extraction.overall_confidence, "low_confidence_fields": extraction.low_confidence_fields},
            )
            db.commit()
            return

        invoice.status = InvoiceStatus.EXTRACTED.value
        _write_system_audit(
            db, invoice, "invoice_extracted",
            after={"status": invoice.status, "confidence": extraction.overall_confidence},
        )
        db.flush()
        _run_matching_and_explain(db, invoice)
        db.commit()
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.run_matching_for_invoice")
def run_matching_for_invoice(invoice_id: str, tenant_id: str) -> None:
    """Manual re-entry point for invoices held in needs_review after a
    clerk has confirmed/corrected the extracted fields (PRD: fields below
    threshold must be confirmed before proceeding to matching).
    """
    db = SessionLocal()
    try:
        invoice = (
            db.query(Invoice)
            .filter(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
            .one_or_none()
        )
        if invoice is None:
            logger.error("Invoice %s not found for tenant %s", invoice_id, tenant_id)
            return
        _run_matching_and_explain(db, invoice)
        db.commit()
    finally:
        db.close()
