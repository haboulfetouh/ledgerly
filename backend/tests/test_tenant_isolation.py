"""Proves PRD Section 15's hard requirement: "no tenant can see another
tenant's data under any circumstance." Run before every release.
"""

from sqlalchemy.orm import Session

from app.db.tenancy import TenantScopedRepository
from app.models.invoice import Invoice, InvoiceStatus
from app.models.tenant import Tenant


def _make_tenant_with_invoice(db: Session, tenant_name: str, invoice_number: str) -> Tenant:
    tenant = Tenant(name=tenant_name, slug=tenant_name.lower().replace(" ", "-"))
    db.add(tenant)
    db.flush()

    db.add(
        Invoice(
            tenant_id=tenant.id,
            source_filename="invoice.pdf",
            source_document_key="key",
            invoice_number=invoice_number,
            status=InvoiceStatus.PROCESSING.value,
        )
    )
    db.commit()
    return tenant


def test_tenant_cannot_see_another_tenants_invoices(db_session: Session):
    tenant_a = _make_tenant_with_invoice(db_session, "Tenant A", "A-001")
    tenant_b = _make_tenant_with_invoice(db_session, "Tenant B", "B-001")

    repo_a = TenantScopedRepository(db_session, tenant_a.id)
    repo_b = TenantScopedRepository(db_session, tenant_b.id)

    invoices_visible_to_a = repo_a.list(Invoice)
    invoices_visible_to_b = repo_b.list(Invoice)

    assert [i.invoice_number for i in invoices_visible_to_a] == ["A-001"]
    assert [i.invoice_number for i in invoices_visible_to_b] == ["B-001"]


def test_get_by_id_across_tenants_returns_none(db_session: Session):
    tenant_a = _make_tenant_with_invoice(db_session, "Tenant A", "A-001")
    tenant_b = Tenant(name="Tenant B", slug="tenant-b")
    db_session.add(tenant_b)
    db_session.commit()

    invoice_a = TenantScopedRepository(db_session, tenant_a.id).list(Invoice)[0]

    repo_b = TenantScopedRepository(db_session, tenant_b.id)
    assert repo_b.get(Invoice, invoice_a.id) is None
