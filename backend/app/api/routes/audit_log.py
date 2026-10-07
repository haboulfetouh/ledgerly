import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import CurrentUser, require_module
from app.db.session import get_db
from app.models.audit_log_event import AuditLogEvent
from app.schemas.audit_log import AuditLogEventOut

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


def _filtered_query(user: CurrentUser, entity_id: str | None, action: str | None):
    stmt = select(AuditLogEvent).where(AuditLogEvent.tenant_id == user.tenant_id)
    if entity_id:
        stmt = stmt.where(AuditLogEvent.entity_id == entity_id)
    if action:
        stmt = stmt.where(AuditLogEvent.action == action)
    return stmt.order_by(AuditLogEvent.created_at.desc())


@router.get("", response_model=list[AuditLogEventOut])
def list_audit_events(
    entity_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_module("audit_log")),
) -> list[AuditLogEvent]:
    stmt = _filtered_query(user, entity_id, action)
    return list(db.execute(stmt).scalars().all())


@router.get("/export")
def export_audit_events(
    entity_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_module("audit_log")),
) -> StreamingResponse:
    """Immutable, exportable audit trail — PRD Section 12/19: every match,
    override, and approval event must be captured and exportable for audit.
    """
    stmt = _filtered_query(user, entity_id, action)
    events = db.execute(stmt).scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "created_at", "actor_subject", "action", "entity_type", "entity_id", "before", "after"])
    for event in events:
        writer.writerow(
            [
                event.id,
                event.created_at.isoformat(),
                event.actor_subject or "system",
                event.action,
                event.entity_type,
                event.entity_id,
                event.before or "",
                event.after or "",
            ]
        )
    buffer.seek(0)

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ledgerly-audit-log.csv"},
    )
