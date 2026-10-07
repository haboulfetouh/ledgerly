from app.services.connectors.base import ERPConnector
from app.services.connectors.coming_soon import (
    ErpNextConnector,
    NetSuiteConnector,
    OracleFusionConnector,
    SapConnector,
)
from app.services.connectors.dynamics_bc import DynamicsBusinessCentralConnector
from app.services.connectors.mock import MockERPConnector
from app.services.connectors.odoo import OdooConnector

_REGISTRY: dict[str, type[ERPConnector]] = {
    cls.connector_type: cls
    for cls in [
        MockERPConnector,
        DynamicsBusinessCentralConnector,
        OracleFusionConnector,
        OdooConnector,
        ErpNextConnector,
        SapConnector,
        NetSuiteConnector,
    ]
}


def get_connector_class(connector_type: str) -> type[ERPConnector]:
    try:
        return _REGISTRY[connector_type]
    except KeyError:
        raise ValueError(f"Unknown connector type: {connector_type}") from None


def list_connector_types() -> list[type[ERPConnector]]:
    return list(_REGISTRY.values())


def build_connector(connector_type: str, config: dict) -> ERPConnector:
    return get_connector_class(connector_type)(config)
