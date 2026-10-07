from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ConfigFieldOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    label: str
    type: str
    required: bool
    help_text: str | None = None


class ConnectorTypeOut(BaseModel):
    connector_type: str
    display_name: str
    implemented: bool
    config_schema: list[ConfigFieldOut]


class ErpConnectionCreate(BaseModel):
    connector_type: str
    display_name: str
    config: dict[str, str] = {}


class ErpConnectionUpdate(BaseModel):
    display_name: str | None = None
    config: dict[str, str] | None = None


class ErpConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    connector_type: str
    display_name: str
    status: str
    last_tested_at: datetime | None
    last_test_result: str | None
    created_at: datetime


class ConnectionTestStepOut(BaseModel):
    name: str
    success: bool
    detail: str | None = None


class ConnectionTestOut(BaseModel):
    success: bool
    message: str
    steps: list[ConnectionTestStepOut] = []


class ErpConnectionConfigOut(BaseModel):
    config: dict[str, str]
