from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TenantScopedMixin, TimestampMixin, uuid_pk


class MatchingRule(Base, TenantScopedMixin, TimestampMixin):
    __tablename__ = "matching_rules"

    id: Mapped[str] = uuid_pk()
    rule_type: Mapped[str] = mapped_column(String(32))  # price_variance | quantity_variance
    tolerance_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=2.0)
    override_approval_value_threshold: Mapped[float | None] = mapped_column(
        Numeric(14, 2), default=None
    )
