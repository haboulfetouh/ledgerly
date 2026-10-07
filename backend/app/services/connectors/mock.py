"""In-memory fake ERP — lets every downstream module (matching, exceptions,
approvals) be built and demoed without a real ERP tenant. Data is keyed by
PO number so a demo/pilot script can set up predictable match/exception
scenarios.
"""

from __future__ import annotations

from app.services.connectors.base import (
    ConfigField,
    ConnectionTestResult,
    ConnectionTestStep,
    ERPConnector,
    GoodsReceiptData,
    PoLineItemData,
    PurchaseOrderData,
)

_FAKE_POS: dict[str, PurchaseOrderData] = {
    "PO-20561": PurchaseOrderData(
        po_number="PO-20561",
        vendor_name="Falcon IT Supplies LLC",
        total_amount=8295.00,
        line_items=[
            PoLineItemData("Server rack UPS unit", 2, 3500.00, 7000.00),
            PoLineItemData("Installation service", 1, 900.00, 900.00),
        ],
    ),
    "PO-20567": PurchaseOrderData(
        po_number="PO-20567",
        vendor_name="Gulf Print & Packaging LLC",
        total_amount=21870.00,
        line_items=[PoLineItemData("Retail shopping bags - kraft, branded run", 1, 21870.00, 21870.00)],
    ),
}

_FAKE_GRNS: dict[str, GoodsReceiptData] = {
    "PO-20561": GoodsReceiptData(
        grn_number="GRN-9001",
        po_number="PO-20561",
        received_quantities=[{"description": "Server rack UPS unit", "quantity": 2}],
    ),
    "PO-20567": GoodsReceiptData(
        grn_number="GRN-9002",
        po_number="PO-20567",
        received_quantities=[{"description": "Retail shopping bags - kraft, branded run", "quantity": 1}],
    ),
}


class MockERPConnector(ERPConnector):
    connector_type = "mock"
    display_name = "Demo / Mock ERP"
    implemented = True
    config_schema: list[ConfigField] = []  # no config needed

    def test_connection(self) -> ConnectionTestResult:
        return ConnectionTestResult(
            success=True,
            message="Connected to the demo ERP dataset.",
            steps=[ConnectionTestStep("Load in-memory demo dataset", True)],
        )

    def fetch_purchase_order(self, po_number: str) -> PurchaseOrderData | None:
        return _FAKE_POS.get(po_number)

    def fetch_goods_receipt(self, po_number: str) -> GoodsReceiptData | None:
        return _FAKE_GRNS.get(po_number)

    def write_approval_status(self, invoice_external_ref: str, status: str) -> bool:
        return True
