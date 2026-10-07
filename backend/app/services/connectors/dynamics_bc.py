"""Microsoft Dynamics 365 Business Central connector.

Chosen as the first real ERP connector per the PRD's ideal-customer profile
(mid-market, single well-implemented ERP instance) — Business Central's
REST/OData v2.0 API is a materially smaller integration surface than
Dynamics 365 Finance & Operations.

Write-back note: Business Central's standard API does not expose a generic
"external approval status" field on purchaseOrders — real deployments
typically need a small customer-side extension exposing a custom field
(here assumed to be `ledgerlyApprovalStatus`) for write-back to land
anywhere. This mirrors the PRD's own flagged risk (Section 34): the first
ERP connector is the highest-uncertainty item in the roadmap, and the
exact write-back shape should be confirmed against the pilot customer's
actual BC instance before go-live.
"""

from __future__ import annotations

import httpx

from app.services.connectors.base import (
    ConfigField,
    ConnectionTestResult,
    ConnectionTestStep,
    ERPConnector,
    GoodsReceiptData,
    PoLineItemData,
    PurchaseOrderData,
)


class DynamicsBusinessCentralConnector(ERPConnector):
    connector_type = "dynamics_business_central"
    display_name = "Microsoft Dynamics 365 Business Central"
    implemented = True
    config_schema = [
        ConfigField("azure_tenant_id", "Azure AD Tenant ID"),
        ConfigField("client_id", "Application (client) ID"),
        ConfigField("client_secret", "Client secret", type="password"),
        ConfigField(
            "environment",
            "Business Central environment name",
            help_text="e.g. Production or Sandbox",
        ),
        ConfigField("company_id", "Company ID (GUID)"),
    ]

    _TOKEN_URL_TMPL = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
    _SCOPE = "https://api.businesscentral.dynamics.com/.default"

    def __init__(self, config: dict):
        super().__init__(config)
        self._token: str | None = None

    def _base_url(self) -> str:
        env = self.config["environment"]
        company_id = self.config["company_id"]
        return (
            f"https://api.businesscentral.dynamics.com/v2.0/{env}"
            f"/api/v2.0/companies({company_id})"
        )

    def _get_token(self) -> str:
        if self._token:
            return self._token
        resp = httpx.post(
            self._TOKEN_URL_TMPL.format(tenant=self.config["azure_tenant_id"]),
            data={
                "grant_type": "client_credentials",
                "client_id": self.config["client_id"],
                "client_secret": self.config["client_secret"],
                "scope": self._SCOPE,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def test_connection(self) -> ConnectionTestResult:
        steps: list[ConnectionTestStep] = []
        try:
            self._get_token()
        except KeyError as exc:
            steps.append(ConnectionTestStep("Authenticate with Azure AD", False, f"Missing required config field: {exc}"))
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        except httpx.HTTPStatusError as exc:
            steps.append(
                ConnectionTestStep(
                    "Authenticate with Azure AD", False, f"Azure AD rejected the request: {exc.response.status_code} {exc.response.text[:200]}"
                )
            )
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        except httpx.RequestError as exc:
            steps.append(ConnectionTestStep("Authenticate with Azure AD", False, f"Could not reach Azure AD: {exc}"))
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        steps.append(ConnectionTestStep("Authenticate with Azure AD", True))

        try:
            resp = httpx.get(
                f"{self._base_url()}/purchaseOrders",
                headers=self._headers(),
                params={"$top": 1},
                timeout=15.0,
            )
            resp.raise_for_status()
        except KeyError as exc:
            steps.append(ConnectionTestStep("Query Business Central purchase orders", False, f"Missing required config field: {exc}"))
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        except httpx.HTTPStatusError as exc:
            steps.append(
                ConnectionTestStep(
                    "Query Business Central purchase orders",
                    False,
                    f"Business Central rejected the request: {exc.response.status_code} {exc.response.text[:200]}",
                )
            )
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        except httpx.RequestError as exc:
            steps.append(ConnectionTestStep("Query Business Central purchase orders", False, f"Could not reach Business Central: {exc}"))
            return ConnectionTestResult(success=False, message=steps[-1].detail, steps=steps)
        steps.append(ConnectionTestStep("Query Business Central purchase orders", True))

        return ConnectionTestResult(success=True, message="Connected to Business Central successfully.", steps=steps)

    def fetch_purchase_order(self, po_number: str) -> PurchaseOrderData | None:
        resp = httpx.get(
            f"{self._base_url()}/purchaseOrders",
            headers=self._headers(),
            params={"$filter": f"number eq '{po_number}'", "$expand": "purchaseOrderLines"},
            timeout=15.0,
        )
        resp.raise_for_status()
        results = resp.json().get("value", [])
        if not results:
            return None

        po = results[0]
        line_items = [
            PoLineItemData(
                description=line.get("description"),
                quantity=line.get("quantity"),
                unit_price=line.get("unitPrice"),
                line_total=line.get("lineAmount") or line.get("amountIncludingTax"),
            )
            for line in po.get("purchaseOrderLines", [])
        ]
        return PurchaseOrderData(
            po_number=po.get("number", po_number),
            vendor_name=po.get("vendorName") or po.get("payToName"),
            total_amount=po.get("totalAmountIncludingTax") or po.get("totalAmountExcludingTax"),
            line_items=line_items,
        )

    def fetch_goods_receipt(self, po_number: str) -> GoodsReceiptData | None:
        resp = httpx.get(
            f"{self._base_url()}/purchaseReceipts",
            headers=self._headers(),
            params={"$filter": f"orderNumber eq '{po_number}'", "$expand": "purchaseReceiptLines"},
            timeout=15.0,
        )
        resp.raise_for_status()
        results = resp.json().get("value", [])
        if not results:
            return None

        receipt = results[0]
        received_quantities = [
            {
                "description": line.get("description"),
                "quantity": line.get("quantityReceived") or line.get("quantity"),
            }
            for line in receipt.get("purchaseReceiptLines", [])
        ]
        return GoodsReceiptData(
            grn_number=receipt.get("number", ""),
            po_number=po_number,
            received_quantities=received_quantities,
        )

    def write_approval_status(self, invoice_external_ref: str, status: str) -> bool:
        # See module docstring: this assumes a customer-side extension field.
        # Fails loudly rather than silently no-op'ing, per PRD's "never
        # silently fail an ERP write-back" requirement (Section 7/17).
        resp = httpx.patch(
            f"{self._base_url()}/purchaseOrders({invoice_external_ref})",
            headers={**self._headers(), "If-Match": "*"},
            json={"ledgerlyApprovalStatus": status},
            timeout=15.0,
        )
        return resp.status_code < 300
