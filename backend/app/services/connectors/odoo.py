"""Odoo connector, via its stable XML-RPC external API (stdlib xmlrpc.client
— no extra dependency needed). Chosen as the first fully-local, self-hostable
ERP to validate the three-way-match flow end-to-end without a cloud tenant
(unlike Business Central, which has no real free local install).

Odoo has no generic "external approval status" field either (same gap noted
in dynamics_bc.py), so write-back posts a chatter message on the purchase
order via `message_post` — visible in the Odoo UI's log, no custom module
or schema change required on the Odoo side.
"""

from __future__ import annotations

import xmlrpc.client

from app.services.connectors.base import (
    ConfigField,
    ConnectionTestResult,
    ConnectionTestStep,
    ERPConnector,
    GoodsReceiptData,
    PoLineItemData,
    PurchaseOrderData,
)


class OdooConnector(ERPConnector):
    connector_type = "odoo"
    display_name = "Odoo"
    implemented = True
    config_schema = [
        ConfigField(
            "url",
            "Odoo URL",
            type="url",
            help_text="e.g. http://odoo:8069 (use the docker network hostname, not localhost)",
        ),
        ConfigField("db", "Database name"),
        ConfigField("username", "Username (email)"),
        ConfigField("password", "Password or API key", type="password"),
    ]

    def __init__(self, config: dict):
        super().__init__(config)
        self._uid: int | None = None

    def _common(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/common")

    def _models(self) -> xmlrpc.client.ServerProxy:
        return xmlrpc.client.ServerProxy(f"{self.config['url']}/xmlrpc/2/object")

    def _authenticate(self) -> int:
        if self._uid:
            return self._uid
        uid = self._common().authenticate(self.config["db"], self.config["username"], self.config["password"], {})
        if not uid:
            raise ValueError("Odoo authentication failed — check the URL, database, username, and password.")
        self._uid = uid
        return uid

    def _execute(self, model: str, method: str, args: list, kwargs: dict | None = None):
        uid = self._authenticate()
        return self._models().execute_kw(
            self.config["db"], uid, self.config["password"], model, method, args, kwargs or {}
        )

    def test_connection(self) -> ConnectionTestResult:
        steps: list[ConnectionTestStep] = []
        try:
            self._authenticate()
        except ValueError as exc:
            steps.append(ConnectionTestStep("Authenticate with Odoo", False, str(exc)))
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        except KeyError as exc:
            steps.append(ConnectionTestStep("Authenticate with Odoo", False, f"Missing required config field: {exc}"))
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError) as exc:
            steps.append(ConnectionTestStep("Authenticate with Odoo", False, f"Could not reach Odoo: {exc}"))
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        steps.append(ConnectionTestStep("Authenticate with Odoo", True))

        try:
            self._execute("purchase.order", "search_count", [[]])
        except (xmlrpc.client.Fault, xmlrpc.client.ProtocolError, OSError) as exc:
            steps.append(ConnectionTestStep("Verify access to Purchase Orders", False, f"Could not read purchase orders: {exc}"))
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        steps.append(ConnectionTestStep("Verify access to Purchase Orders", True))

        return ConnectionTestResult(success=True, message="Connected to Odoo successfully.", steps=steps)

    def fetch_purchase_order(self, po_number: str) -> PurchaseOrderData | None:
        orders = self._execute(
            "purchase.order",
            "search_read",
            [[["name", "=", po_number]]],
            {"fields": ["name", "partner_id", "amount_total", "order_line"], "limit": 1},
        )
        if not orders:
            return None

        po = orders[0]
        line_ids = po.get("order_line") or []
        lines = (
            self._execute(
                "purchase.order.line",
                "read",
                [line_ids],
                {"fields": ["name", "product_qty", "price_unit", "price_subtotal"]},
            )
            if line_ids
            else []
        )
        line_items = [
            PoLineItemData(
                description=line.get("name"),
                quantity=line.get("product_qty"),
                unit_price=line.get("price_unit"),
                line_total=line.get("price_subtotal"),
            )
            for line in lines
        ]
        partner = po.get("partner_id")  # Odoo many2one fields read back as [id, display_name]
        return PurchaseOrderData(
            po_number=po.get("name", po_number),
            vendor_name=partner[1] if partner else None,
            total_amount=po.get("amount_total"),
            line_items=line_items,
        )

    def fetch_goods_receipt(self, po_number: str) -> GoodsReceiptData | None:
        pickings = self._execute(
            "stock.picking",
            "search_read",
            [[["origin", "=", po_number], ["state", "=", "done"]]],
            {"fields": ["name", "move_line_ids"], "limit": 1},
        )
        if not pickings:
            return None

        picking = pickings[0]
        move_line_ids = picking.get("move_line_ids") or []
        move_lines = (
            self._execute("stock.move.line", "read", [move_line_ids], {"fields": ["product_id", "qty_done"]})
            if move_line_ids
            else []
        )
        received_quantities = [
            {
                "description": (line.get("product_id") or [None, None])[1],
                "quantity": line.get("qty_done"),
            }
            for line in move_lines
        ]
        return GoodsReceiptData(
            grn_number=picking.get("name", ""),
            po_number=po_number,
            received_quantities=received_quantities,
        )

    def write_approval_status(self, invoice_external_ref: str, status: str) -> bool:
        orders = self._execute(
            "purchase.order",
            "search_read",
            [[["name", "=", invoice_external_ref]]],
            {"fields": ["id"], "limit": 1},
        )
        if not orders:
            return False

        self._execute(
            "purchase.order",
            "message_post",
            [[orders[0]["id"]]],
            {"body": f"Ledgerly AI: invoice approval status → {status}"},
        )
        return True
