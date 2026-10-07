from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.crypto import decrypt_json, encrypt_json
from app.core.security import CurrentUser, require_module, require_role
from app.db.session import get_db
from app.models.erp_connection import ErpConnection
from app.schemas.erp_connection import (
    ConfigFieldOut,
    ConnectionTestOut,
    ConnectionTestStepOut,
    ConnectorTypeOut,
    ErpConnectionConfigOut,
    ErpConnectionCreate,
    ErpConnectionOut,
    ErpConnectionUpdate,
)
from app.services.connectors.registry import build_connector, get_connector_class, list_connector_types

router = APIRouter(prefix="/admin/erp-connectors", tags=["admin-erp"])


@router.get("/types", response_model=list[ConnectorTypeOut])
def list_types(user: CurrentUser = Depends(require_role("admin"))) -> list[ConnectorTypeOut]:
    return [
        ConnectorTypeOut(
            connector_type=cls.connector_type,
            display_name=cls.display_name,
            implemented=cls.implemented,
            config_schema=[ConfigFieldOut.model_validate(f) for f in cls.config_schema],
        )
        for cls in list_connector_types()
    ]


def _get_connection_or_404(db: Session, tenant_id: str, connection_id: str) -> ErpConnection:
    stmt = select(ErpConnection).where(
        ErpConnection.id == connection_id, ErpConnection.tenant_id == tenant_id
    )
    connection = db.execute(stmt).scalar_one_or_none()
    if connection is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ERP connection not found")
    return connection


@router.post("", response_model=ErpConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connection(
    payload: ErpConnectionCreate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
) -> ErpConnection:
    try:
        get_connector_class(payload.connector_type)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    connection = ErpConnection(
        tenant_id=user.tenant_id,
        connector_type=payload.connector_type,
        display_name=payload.display_name,
        config_encrypted=encrypt_json(payload.config) if payload.config else None,
        status="not_configured",
    )
    db.add(connection)
    db.commit()
    db.refresh(connection)
    return connection


@router.get("", response_model=list[ErpConnectionOut])
def list_connections(
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_module("erp_connectors")),
) -> list[ErpConnection]:
    stmt = select(ErpConnection).where(ErpConnection.tenant_id == user.tenant_id)
    return list(db.execute(stmt).scalars().all())


@router.get("/{connection_id}/config", response_model=ErpConnectionConfigOut)
def get_connection_config(
    connection_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
) -> ErpConnectionConfigOut:
    """Decrypted config, for prefilling the edit form. Admin-only (never
    exposed on the list endpoint, which `erp_connectors`-module-only roles
    can also read) — this is the tenant's own stored credentials, not a
    secret being hidden from them, just from anyone without admin authority.
    """
    connection = _get_connection_or_404(db, user.tenant_id, connection_id)
    config = decrypt_json(connection.config_encrypted) if connection.config_encrypted else {}
    return ErpConnectionConfigOut(config=config)


@router.patch("/{connection_id}", response_model=ErpConnectionOut)
def update_connection(
    connection_id: str,
    payload: ErpConnectionUpdate,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
) -> ErpConnection:
    connection = _get_connection_or_404(db, user.tenant_id, connection_id)

    if payload.display_name is not None:
        connection.display_name = payload.display_name
    if payload.config is not None:
        connection.config_encrypted = encrypt_json(payload.config)
        connection.status = "not_configured"

    db.commit()
    db.refresh(connection)
    return connection


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
) -> None:
    connection = _get_connection_or_404(db, user.tenant_id, connection_id)
    db.delete(connection)
    db.commit()


@router.post("/{connection_id}/test", response_model=ConnectionTestOut)
def test_connection(
    connection_id: str,
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_role("admin")),
) -> ConnectionTestOut:
    connection = _get_connection_or_404(db, user.tenant_id, connection_id)

    config = decrypt_json(connection.config_encrypted) if connection.config_encrypted else {}
    connector = build_connector(connection.connector_type, config)

    try:
        result = connector.test_connection()
    except Exception as exc:  # connector bugs must not 500 the admin UI silently
        result_success, result_message, result_steps = False, f"Unexpected error: {exc}", []
    else:
        result_success, result_message, result_steps = result.success, result.message, result.steps

    connection.status = "connected" if result_success else "error"
    connection.last_tested_at = datetime.now(timezone.utc)
    connection.last_test_result = result_message
    db.commit()

    return ConnectionTestOut(
        success=result_success,
        message=result_message,
        steps=[ConnectionTestStepOut(name=s.name, success=s.success, detail=s.detail) for s in result_steps],
    )
