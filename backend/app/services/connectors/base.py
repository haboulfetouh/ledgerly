"""ERP connector interface.

Every ERP integration (Dynamics, Oracle, Odoo, ERPNext, ...) implements this
same interface so the admin UI can render a generic "pick a connector type,
fill in its config, test the connection" flow without hardcoding per-ERP
logic anywhere except inside that connector's own module. See registry.py
for how a connector_type string maps to a class.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ConfigField:
    name: str
    label: str
    type: str = "text"  # text | password | url
    required: bool = True
    help_text: str | None = None


@dataclass
class ConnectionTestStep:
    name: str
    success: bool
    detail: str | None = None


@dataclass
class ConnectionTestResult:
    success: bool
    message: str
    steps: list[ConnectionTestStep] = field(default_factory=list)


@dataclass
class PoLineItemData:
    description: str | None = None
    quantity: float | None = None
    unit_price: float | None = None
    line_total: float | None = None


@dataclass
class PurchaseOrderData:
    po_number: str
    vendor_name: str | None = None
    total_amount: float | None = None
    line_items: list[PoLineItemData] = field(default_factory=list)


@dataclass
class GoodsReceiptData:
    grn_number: str
    po_number: str
    received_quantities: list[dict] = field(default_factory=list)


class ERPConnector(ABC):
    connector_type: str
    display_name: str
    implemented: bool = True
    config_schema: list[ConfigField] = []

    def __init__(self, config: dict):
        self.config = config

    @abstractmethod
    def test_connection(self) -> ConnectionTestResult: ...

    @abstractmethod
    def fetch_purchase_order(self, po_number: str) -> PurchaseOrderData | None: ...

    @abstractmethod
    def fetch_goods_receipt(self, po_number: str) -> GoodsReceiptData | None: ...

    @abstractmethod
    def write_approval_status(self, invoice_external_ref: str, status: str) -> bool: ...


class NotImplementedConnector(ERPConnector):
    """Placeholder for ERPs listed in the picker but not yet built — keeps
    the "choose from a wide list of ERPs" UX honest instead of hiding the
    roadmap, per the product's stated ERP-connector strategy.
    """

    implemented = False

    def test_connection(self) -> ConnectionTestResult:
        return ConnectionTestResult(
            success=False,
            message=f"{self.display_name} support is not built yet — coming soon.",
        )

    def fetch_purchase_order(self, po_number: str) -> PurchaseOrderData | None:
        raise NotImplementedError(f"{self.connector_type} connector is not implemented")

    def fetch_goods_receipt(self, po_number: str) -> GoodsReceiptData | None:
        raise NotImplementedError(f"{self.connector_type} connector is not implemented")

    def write_approval_status(self, invoice_external_ref: str, status: str) -> bool:
        raise NotImplementedError(f"{self.connector_type} connector is not implemented")
