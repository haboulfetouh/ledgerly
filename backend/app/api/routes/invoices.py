from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.crypto import decrypt_json
from app.core.security import CurrentUser, get_current_user, require_module, require_role
from app.db.session import get_db
from app.models.approval_record import ApprovalRecord
from app.models.audit_log_event import AuditLogEvent
from app.models.erp_connection import ErpConnection
from app.models.invoice import Invoice, InvoiceStatus
from app.models.match_record import MatchRecord
from app.models.matching_rule import MatchingRule
from app.schemas.invoice import (
    ApprovalDecisionRequest,
    InvoiceDetailOut,
    InvoiceFieldsUpdate,
    InvoiceListItemOut,
    InvoiceUploadOut,
    ResolveExceptionRequest,
)
from app.services.auth.keycloak_admin import KeycloakAdminClient
from app.services.connectors.registry import build_connector
from app.services.notifications.email import send_email
from app.services.storage.minio_client import object_key, presigned_url, upload_document
from app.workers.tasks import ocr_and_extract_invoice, run_matching_for_invoice

router = APIRouter(prefix="/invoices", tags=["invoices"])


def _write_audit(
    db: Session,
    user: CurrentUser,
    action: str,
    entity_id: str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    db.add(
        AuditLogEvent(
            tenant_id=user.tenant_id,
            actor_subject=user.subject,
            action=action,
            entity_type="invoice",
            entity_id=entity_id,
            before=before,
            after=after,
        )
    )

_ALLOWED_CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg"}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


@router.post("", response_model=InvoiceUploadOut, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("bookkeeper", "accountant_manager", "admin")),
) -> InvoiceUploadOut:
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Unsupported file type '{file.content_type}'. Allowed: PDF, PNG, JPG.",
        )

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File exceeds 20 MB limit.")

    invoice = Invoice(
        tenant_id=user.tenant_id,
        source_filename=file.filename or "invoice",
        source_document_key="",
        status=InvoiceStatus.PROCESSING.value,
    )
    db.add(invoice)
    db.flush()  # assigns invoice.id

    key = object_key(user.tenant_id, invoice.id, invoice.source_filename)
    invoice.source_document_key = key
    db.commit()
    db.refresh(invoice)

    upload_document(key, content, file.content_type)

    ocr_and_extract_invoice.delay(invoice.id, user.tenant_id)

    return InvoiceUploadOut(id=invoice.id, status=invoice.status)


@router.get("", response_model=list[InvoiceListItemOut])
def list_invoices(
    status_in: list[str] | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_module("invoices", "exceptions", "approvals")),
) -> list[Invoice]:
    stmt = select(Invoice).where(Invoice.tenant_id == user.tenant_id)
    if status_in:
        stmt = stmt.where(Invoice.status.in_(status_in))
    stmt = stmt.order_by(Invoice.created_at.asc())
    return list(db.execute(stmt).scalars().all())


@router.get("/{invoice_id}", response_model=InvoiceDetailOut)
def get_invoice(
    invoice_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> Invoice:
    stmt = (
        select(Invoice)
        .where(Invoice.id == invoice_id, Invoice.tenant_id == user.tenant_id)
        .options(
            selectinload(Invoice.line_items),
            selectinload(Invoice.ai_outputs),
            selectinload(Invoice.match_records),
            selectinload(Invoice.approval_records),
        )
    )
    invoice = db.execute(stmt).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    return invoice


def _get_invoice_or_404(db: Session, tenant_id: str, invoice_id: str) -> Invoice:
    stmt = select(Invoice).where(Invoice.id == invoice_id, Invoice.tenant_id == tenant_id)
    invoice = db.execute(stmt).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invoice not found")
    return invoice


@router.get("/{invoice_id}/document-url")
def get_document_url(
    invoice_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """Short-lived link to the original uploaded file in MinIO — the
    source document is kept for the invoice's full retention period
    (PRD Section 12), this just makes that copy reachable from the UI.
    """
    invoice = _get_invoice_or_404(db, user.tenant_id, invoice_id)
    return {"url": presigned_url(invoice.source_document_key), "filename": invoice.source_filename}


@router.patch("/{invoice_id}", response_model=InvoiceDetailOut)
def update_invoice_fields(
    invoice_id: str,
    payload: InvoiceFieldsUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("bookkeeper", "accountant_manager", "admin")),
) -> Invoice:
    """Lets a clerk correct low-confidence extracted fields before matching
    runs — PRD: fields below threshold must be confirmed, never silently
    guessed or auto-proceeded on.
    """
    invoice = _get_invoice_or_404(db, user.tenant_id, invoice_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(invoice, field, value)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/run-matching", response_model=InvoiceUploadOut)
def trigger_matching(
    invoice_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("bookkeeper", "accountant_manager", "admin")),
) -> InvoiceUploadOut:
    invoice = _get_invoice_or_404(db, user.tenant_id, invoice_id)
    if invoice.status not in (InvoiceStatus.NEEDS_REVIEW.value, InvoiceStatus.EXTRACTED.value, InvoiceStatus.EXCEPTION.value):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot run matching from status '{invoice.status}'.",
        )
    run_matching_for_invoice.delay(invoice.id, user.tenant_id)
    return InvoiceUploadOut(id=invoice.id, status=invoice.status)


def _get_latest_match_record(db: Session, tenant_id: str, invoice_id: str) -> MatchRecord | None:
    stmt = (
        select(MatchRecord)
        .where(MatchRecord.tenant_id == tenant_id, MatchRecord.invoice_id == invoice_id)
        .order_by(MatchRecord.created_at.desc())
    )
    return db.execute(stmt).scalar_one_or_none()


def _get_override_threshold(db: Session, tenant_id: str) -> float | None:
    stmt = select(MatchingRule).where(
        MatchingRule.tenant_id == tenant_id, MatchingRule.rule_type == "price_variance"
    )
    rule = db.execute(stmt).scalar_one_or_none()
    return float(rule.override_approval_value_threshold) if rule and rule.override_approval_value_threshold else None


@router.post("/{invoice_id}/resolve", response_model=InvoiceDetailOut)
def resolve_exception(
    invoice_id: str,
    payload: ResolveExceptionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("bookkeeper", "accountant_manager", "admin")),
) -> Invoice:
    invoice = _get_invoice_or_404(db, user.tenant_id, invoice_id)
    if invoice.status != InvoiceStatus.EXCEPTION.value:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only invoices in Exception status can be resolved.")
    if payload.action in ("override", "escalate") and not payload.reason:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A reason is required for override or escalate.")

    match_record = _get_latest_match_record(db, user.tenant_id, invoice_id)
    if match_record is not None:
        match_record.resolved_by = user.subject
        match_record.resolution_action = payload.action
        match_record.resolution_reason = payload.reason
        match_record.resolved_at = datetime.now(timezone.utc)

    before_status = invoice.status

    if payload.action == "accept":
        # Clerk agrees the exception is genuine (e.g. a real duplicate) — invoice is rejected, not paid.
        invoice.status = InvoiceStatus.REJECTED.value
    elif payload.action == "override":
        threshold = _get_override_threshold(db, user.tenant_id)
        requires_accountant_manager = (
            threshold is not None
            and invoice.total_amount is not None
            and float(invoice.total_amount) > threshold
            and not (user.has_role("accountant_manager") or user.has_role("admin"))
        )
        if requires_accountant_manager:
            # Stays in Exception until an accountant manager approves the override — PRD:
            # "overrides above a configurable value threshold require supervisor approval."
            emails = KeycloakAdminClient().list_emails_for_roles(user.tenant_id, ["accountant_manager", "admin"])
            send_email(
                emails,
                subject=f"High-value override pending your approval: invoice {invoice.id}",
                body=f"{user.email} requested an override on invoice {invoice.id} (amount {invoice.total_amount}). Reason: {payload.reason}",
            )
        else:
            invoice.status = InvoiceStatus.MATCHED_TOLERANCE.value
    elif payload.action == "escalate":
        emails = KeycloakAdminClient().list_emails_for_roles(user.tenant_id, ["accountant_manager", "admin"])
        send_email(
            emails,
            subject=f"Invoice escalated for review: invoice {invoice.id}",
            body=f"{user.email} escalated invoice {invoice.id}. Reason: {payload.reason}",
        )

    _write_audit(
        db, user, f"exception_{payload.action}", invoice.id,
        before={"status": before_status}, after={"status": invoice.status, "reason": payload.reason},
    )

    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/approve", response_model=InvoiceDetailOut)
def approve_invoice(
    invoice_id: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("accountant_manager", "admin")),
) -> Invoice:
    invoice = _get_invoice_or_404(db, user.tenant_id, invoice_id)
    if invoice.status not in (InvoiceStatus.MATCHED.value, InvoiceStatus.MATCHED_TOLERANCE.value):
        raise HTTPException(status.HTTP_409_CONFLICT, "Only matched invoices can be approved.")

    db.add(
        ApprovalRecord(
            tenant_id=user.tenant_id,
            invoice_id=invoice.id,
            approver_subject=user.subject,
            decision="approved",
            comment=payload.comment,
            decided_at=datetime.now(timezone.utc),
        )
    )

    invoice.status = InvoiceStatus.APPROVED.value

    # Best-effort ERP write-back — never silently drop a failure (PRD Section 7),
    # but never let a write-back failure block the approval itself either.
    write_back_note = None
    stmt = (
        select(ErpConnection)
        .where(ErpConnection.tenant_id == user.tenant_id, ErpConnection.status == "connected")
        .order_by(ErpConnection.updated_at.desc())
    )
    connection = db.execute(stmt).scalar_one_or_none()
    if connection is not None:
        try:
            config = decrypt_json(connection.config_encrypted) if connection.config_encrypted else {}
            connector = build_connector(connection.connector_type, config)
            success = connector.write_approval_status(invoice.po_number or invoice.id, "approved")
            invoice.status = InvoiceStatus.POSTED.value if success else InvoiceStatus.APPROVED.value
            write_back_note = "posted to ERP" if success else "ERP write-back failed — held as Approved"
        except Exception as exc:
            write_back_note = f"ERP write-back failed — held as Approved ({exc})"

    _write_audit(
        db, user, "invoice_approved", invoice.id,
        after={"status": invoice.status, "write_back": write_back_note, "comment": payload.comment},
    )

    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/reject", response_model=InvoiceDetailOut)
def reject_invoice(
    invoice_id: str,
    payload: ApprovalDecisionRequest,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("accountant_manager", "admin")),
) -> Invoice:
    invoice = _get_invoice_or_404(db, user.tenant_id, invoice_id)
    if invoice.status not in (InvoiceStatus.MATCHED.value, InvoiceStatus.MATCHED_TOLERANCE.value):
        raise HTTPException(status.HTTP_409_CONFLICT, "Only matched invoices can be rejected.")

    db.add(
        ApprovalRecord(
            tenant_id=user.tenant_id,
            invoice_id=invoice.id,
            approver_subject=user.subject,
            decision="rejected",
            comment=payload.comment,
            decided_at=datetime.now(timezone.utc),
        )
    )
    invoice.status = InvoiceStatus.REJECTED.value

    _write_audit(
        db, user, "invoice_rejected", invoice.id,
        after={"status": invoice.status, "comment": payload.comment},
    )

    db.commit()
    db.refresh(invoice)
    return invoice
