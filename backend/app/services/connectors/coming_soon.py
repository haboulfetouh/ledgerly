"""ERPs on the roadmap but not yet built. Kept as real registry entries
(rather than a hardcoded frontend list) so the admin picker UI and the
backend agree on exactly one source of truth for what's available.
"""

from app.services.connectors.base import ConfigField, NotImplementedConnector


class OracleFusionConnector(NotImplementedConnector):
    connector_type = "oracle_fusion"
    display_name = "Oracle Fusion Cloud ERP"
    config_schema: list[ConfigField] = []


class ErpNextConnector(NotImplementedConnector):
    connector_type = "erpnext"
    display_name = "ERPNext"
    config_schema: list[ConfigField] = []


class SapConnector(NotImplementedConnector):
    connector_type = "sap"
    display_name = "SAP"
    config_schema: list[ConfigField] = []


class NetSuiteConnector(NotImplementedConnector):
    connector_type = "netsuite"
    display_name = "Oracle NetSuite"
    config_schema: list[ConfigField] = []
