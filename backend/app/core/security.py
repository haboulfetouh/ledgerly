"""JWT validation against Keycloak's JWKS endpoint, and tenant/role extraction.

Tokens are issued by Keycloak (see infra/keycloak/realm-export.json) to the
`ledgerly-frontend` client. Every tenant-scoped table/query relies on the
`tenant_id` claim extracted here — see db/tenancy.py.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwk, jwt
from jose.exceptions import JWTError
from jose.utils import base64url_decode
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

_bearer_scheme = HTTPBearer(auto_error=True)

_JWKS_CACHE: dict = {"keys": {}, "fetched_at": 0.0}
_JWKS_TTL_SECONDS = 300


@dataclass
class CurrentUser:
    subject: str
    tenant_id: str | None
    roles: list[str] = field(default_factory=list)
    email: str | None = None

    def has_role(self, role: str) -> bool:
        return role in self.roles


def _get_jwks() -> dict:
    now = time.time()
    if now - _JWKS_CACHE["fetched_at"] > _JWKS_TTL_SECONDS or not _JWKS_CACHE["keys"]:
        settings = get_settings()
        resp = httpx.get(settings.keycloak_jwks_url, timeout=5.0)
        resp.raise_for_status()
        data = resp.json()
        _JWKS_CACHE["keys"] = {key["kid"]: key for key in data["keys"]}
        _JWKS_CACHE["fetched_at"] = now
    return _JWKS_CACHE["keys"]


def _decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token header") from exc

    kid = unverified_header.get("kid")
    keys = _get_jwks()
    key_data = keys.get(kid)
    if key_data is None:
        # kid rotated on the Keycloak side — force one refetch before giving up.
        _JWKS_CACHE["fetched_at"] = 0.0
        keys = _get_jwks()
        key_data = keys.get(kid)
    if key_data is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown signing key")

    public_key = jwk.construct(key_data)
    message, encoded_sig = token.rsplit(".", 1)
    decoded_sig = base64url_decode(encoded_sig.encode())
    if not public_key.verify(message.encode(), decoded_sig):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Signature verification failed")

    try:
        claims = jwt.get_unverified_claims(token)
    except JWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token claims") from exc

    if claims.get("iss") != settings.keycloak_issuer:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unexpected token issuer")

    if claims.get("exp", 0) < time.time():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")

    return claims


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> CurrentUser:
    claims = _decode_token(credentials.credentials)

    tenant_id = claims.get("tenant_id")
    roles = claims.get("realm_access", {}).get("roles", [])

    # platform_admin users manage tenants, not data within one — they're
    # deliberately not provisioned with a tenant_id at all.
    if not tenant_id and "platform_admin" not in roles:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Token has no tenant_id claim — user is not provisioned for any tenant",
        )

    return CurrentUser(
        subject=claims["sub"],
        tenant_id=tenant_id,
        roles=roles,
        email=claims.get("email"),
    )


def require_role(*allowed_roles: str):
    def _dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not any(user.has_role(role) for role in allowed_roles):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return user

    return _dependency


def require_module(*any_of_modules: str):
    """Gates page-level visibility per the tenant's RoleModulePermission
    matrix (admin-configurable — see api/routes/admin_role_permissions.py).
    `admin` always passes, regardless of the matrix — the matrix can
    restrict everyone else, never the tenant's own admin. `platform_admin`
    is deliberately NOT bypassed here: it has no tenant_id, so a tenant-
    scoped query keyed on it would silently run against `tenant_id=None`
    instead of erroring — platform_admin has no legitimate reason to hit
    tenant module endpoints at all (it operates exclusively via
    api/routes/platform.py). Passing multiple modules is an OR: any one
    grants access, for the rare endpoint that serves more than one nav item
    (e.g. the shared invoices list backing Invoices/Exceptions/Approvals).
    """

    def _dependency(
        user: CurrentUser = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> CurrentUser:
        if user.has_role("admin"):
            return user

        from app.models.role_permission import RoleModulePermission

        stmt = select(RoleModulePermission).where(
            RoleModulePermission.tenant_id == user.tenant_id,
            RoleModulePermission.role.in_(user.roles),
            RoleModulePermission.module.in_(any_of_modules),
        )
        if db.execute(stmt).first() is None:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Your role doesn't have access to: {', '.join(any_of_modules)}",
            )
        return user

    return _dependency
