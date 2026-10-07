"""Tenant-scoping helper.

Every query against a TenantScopedMixin table must go through here so that
"no customer can ever see another customer's data" (PRD Section 15) is
enforced in one place rather than repeated (and potentially forgotten) at
every call site. See tests/test_tenant_isolation.py for the automated proof.
"""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import TenantScopedMixin

ModelT = TypeVar("ModelT", bound=TenantScopedMixin)


class TenantScopedRepository:
    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id

    def query(self, model: type[ModelT]):
        return select(model).where(model.tenant_id == self.tenant_id)

    def get(self, model: type[ModelT], record_id: str) -> ModelT | None:
        stmt = self.query(model).where(model.id == record_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list(self, model: type[ModelT]) -> list[ModelT]:
        return list(self.db.execute(self.query(model)).scalars().all())

    def add(self, instance: ModelT) -> ModelT:
        instance.tenant_id = self.tenant_id
        self.db.add(instance)
        return instance
