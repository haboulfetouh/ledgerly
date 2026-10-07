from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_subject: str | None
    action: str
    entity_type: str
    entity_id: str
    before: dict | None
    after: dict | None
    created_at: datetime
