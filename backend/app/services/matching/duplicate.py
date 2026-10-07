"""Duplicate-invoice detection — deterministic, not AI (PRD Section 10:
similarity matching by vendor + amount + date proximity, not generative).
A duplicate invoice number for the same vendor is always treated as an
exception; a suspiciously similar amount+date on a different invoice
number is flagged as a possible duplicate for human confirmation.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.invoice import Invoice

_NEAR_DUPLICATE_DATE_WINDOW_DAYS = 5
_NEAR_DUPLICATE_AMOUNT_TOLERANCE_PCT = 0.5


@dataclass
class DuplicateMatch:
    existing_invoice_id: str
    reason: str


def find_duplicate(db: Session, tenant_id: str, invoice: Invoice) -> DuplicateMatch | None:
    if not invoice.vendor_name:
        return None

    candidates_stmt = (
        select(Invoice)
        .where(
            Invoice.tenant_id == tenant_id,
            Invoice.vendor_name == invoice.vendor_name,
            Invoice.id != invoice.id,
        )
    )
    candidates = list(db.execute(candidates_stmt).scalars().all())

    if invoice.invoice_number:
        exact = next((c for c in candidates if c.invoice_number == invoice.invoice_number), None)
        if exact:
            return DuplicateMatch(
                existing_invoice_id=exact.id,
                reason=(
                    f"Invoice number {invoice.invoice_number} already exists for vendor "
                    f"{invoice.vendor_name} (invoice {exact.id})."
                ),
            )

    if invoice.total_amount is not None and invoice.invoice_date is not None:
        for candidate in candidates:
            if candidate.total_amount is None or candidate.invoice_date is None:
                continue
            amount_diff_pct = (
                abs(float(candidate.total_amount) - float(invoice.total_amount))
                / float(invoice.total_amount)
                * 100
                if invoice.total_amount
                else 0
            )
            date_diff = abs((candidate.invoice_date - invoice.invoice_date).days)
            if (
                amount_diff_pct <= _NEAR_DUPLICATE_AMOUNT_TOLERANCE_PCT
                and date_diff <= _NEAR_DUPLICATE_DATE_WINDOW_DAYS
            ):
                return DuplicateMatch(
                    existing_invoice_id=candidate.id,
                    reason=(
                        f"Possible duplicate: same vendor, amount within "
                        f"{_NEAR_DUPLICATE_AMOUNT_TOLERANCE_PCT}% and date within "
                        f"{_NEAR_DUPLICATE_DATE_WINDOW_DAYS} days of invoice {candidate.id} "
                        f"(different invoice number)."
                    ),
                )

    return None
