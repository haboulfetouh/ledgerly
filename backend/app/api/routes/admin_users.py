from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import CurrentUser, require_module, require_role
from app.schemas.user import TENANT_ROLES, UserInviteRequest, UserOut, UserUpdateRequest
from app.services.auth.keycloak_admin import KeycloakAdminClient

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def _require_user_in_tenant(keycloak: KeycloakAdminClient, tenant_id: str, user_id: str) -> dict:
    """set_user_role/set_user_enabled/delete_user act on a raw Keycloak user
    id with no inherent tenant check — without this, a tenant admin could
    mutate or delete a user belonging to a different tenant entirely.
    """
    match = next((u for u in keycloak.list_users(tenant_id) if u["id"] == user_id), None)
    if match is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return match


@router.get("", response_model=list[UserOut])
def list_users(user: CurrentUser = Depends(require_module("users"))) -> list[UserOut]:
    return [UserOut(**u) for u in KeycloakAdminClient().list_users(user.tenant_id)]


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: UserInviteRequest,
    user: CurrentUser = Depends(require_role("admin")),
) -> UserOut:
    if payload.role not in TENANT_ROLES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Role must be one of: {', '.join(TENANT_ROLES)}")

    keycloak = KeycloakAdminClient()
    try:
        user_id = keycloak.create_user(
            email=payload.email,
            password=payload.password,
            tenant_id=user.tenant_id,
            role=payload.role,
            full_name=payload.full_name,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    return UserOut(id=user_id, email=payload.email, full_name=payload.full_name, enabled=True, roles=[payload.role])


@router.patch("/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    user: CurrentUser = Depends(require_role("admin")),
) -> UserOut:
    keycloak = KeycloakAdminClient()
    _require_user_in_tenant(keycloak, user.tenant_id, user_id)

    if payload.role is not None:
        if payload.role not in TENANT_ROLES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Role must be one of: {', '.join(TENANT_ROLES)}")
        keycloak.set_user_role(user_id, payload.role)

    if payload.enabled is not None:
        keycloak.set_user_enabled(user_id, payload.enabled)

    updated = next((u for u in keycloak.list_users(user.tenant_id) if u["id"] == user_id), None)
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserOut(**updated)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    user: CurrentUser = Depends(require_role("admin")),
) -> None:
    keycloak = KeycloakAdminClient()
    _require_user_in_tenant(keycloak, user.tenant_id, user_id)
    keycloak.delete_user(user_id)
