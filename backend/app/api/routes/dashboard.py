from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.security import CurrentUser, require_module
from app.db.session import get_db
from app.models.invoice import Invoice, InvoiceStatus
from app.schemas.dashboard import DashboardMetricsOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_TOUCHLESS_STATUSES = {InvoiceStatus.MATCHED.value, InvoiceStatus.APPROVED.value, InvoiceStatus.POSTED.value}
_PENDING_APPROVAL_STATUSES = {InvoiceStatus.MATCHED.value, InvoiceStatus.MATCHED_TOLERANCE.value}


@router.get("/metrics", response_model=DashboardMetricsOut)
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_module("dashboard")),
) -> DashboardMetricsOut:
    """MVP analytics per PRD Section 28 — deliberately short list: every
    number here either proves the AI pipeline is working (touchless rate)
    or is the ROI evidence a renewal conversation depends on, not a
    vanity metric.
    """
    stmt = (
        select(Invoice)
        .where(Invoice.tenant_id == user.tenant_id)
        .options(selectinload(Invoice.match_records))
    )
    invoices = list(db.execute(stmt).scalars().all())

    processed = [i for i in invoices if i.status != InvoiceStatus.PROCESSING.value]
    needs_review = [i for i in invoices if i.status == InvoiceStatus.NEEDS_REVIEW.value]
    exceptions = [i for i in invoices if i.status == InvoiceStatus.EXCEPTION.value]
    pending_approval = [i for i in invoices if i.status in _PENDING_APPROVAL_STATUSES]

    touchless = [
        i
        for i in processed
        if i.status in _TOUCHLESS_STATUSES and not any(m.resolution_action for m in i.match_records)
    ]
    touchless_rate = (len(touchless) / len(processed) * 100) if processed else None

    now = datetime.now(timezone.utc)
    if exceptions:
        aging_days = [(now - i.created_at).total_seconds() / 86400 for i in exceptions]
        exception_aging_avg = sum(aging_days) / len(aging_days)
    else:
        exception_aging_avg = None

    return DashboardMetricsOut(
        invoices_processed=len(processed),
        needs_review=len(needs_review),
        touchless_rate=round(touchless_rate, 1) if touchless_rate is not None else None,
        avg_cost_per_invoice=None,  # requires customer-specific labor-cost input, not modeled yet
        exception_count=len(exceptions),
        exception_aging_days_avg=round(exception_aging_avg, 1) if exception_aging_avg is not None else None,
        pending_approval_count=len(pending_approval),
    )
