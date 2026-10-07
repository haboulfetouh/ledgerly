"""Thin wrapper over the Keycloak Admin REST API.

Keycloak has no concept of a Ledgerly "tenant" — this glue is how a new
tenant's first admin user gets provisioned for MVP (PRD's onboarding is
sales-assisted/manual at this stage; see Section 29).
"""

from __future__ import annotations

import httpx

from app.core.config import get_settings


class KeycloakAdminClient:
    def __init__(self):
        self.settings = get_settings()
        self._token: str | None = None

    def _get_admin_token(self) -> str:
        if self._token:
            return self._token
        resp = httpx.post(
            f"{self.settings.keycloak_url}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "password",
                "client_id": "admin-cli",
                "username": self.settings.keycloak_admin,
                "password": self.settings.keycloak_admin_password,
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._get_admin_token()}"}

    def _ensure_tenant_id_attribute(self, base: str) -> None:
        """Keycloak's declarative User Profile silently drops any attribute
        that isn't declared in the realm's profile schema — tenant_id must
        be registered here once, or every created user ends up with no
        tenant_id claim at all (indistinguishable from a config bug at
        login time, since the request itself still succeeds with a 200).
        """
        profile_url = f"{base}/users/profile"
        profile = httpx.get(profile_url, headers=self._headers(), timeout=10.0).json()
        if any(attr["name"] == "tenant_id" for attr in profile["attributes"]):
            return

        profile["attributes"].append(
            {
                "name": "tenant_id",
                "displayName": "Tenant ID",
                "permissions": {"view": ["admin"], "edit": ["admin"]},
                "multivalued": False,
            }
        )
        resp = httpx.put(profile_url, headers=self._headers(), json=profile, timeout=10.0)
        resp.raise_for_status()

    def _create_user_raw(
        self, *, base: str, email: str, password: str, attributes: dict, full_name: str = ""
    ) -> str:
        first_name, _, last_name = (full_name or email.split("@")[0]).partition(" ")

        create_resp = httpx.post(
            f"{base}/users",
            headers=self._headers(),
            json={
                "username": email,
                "email": email,
                "enabled": True,
                "emailVerified": True,
                "firstName": first_name,
                "lastName": last_name or first_name,
                "attributes": attributes,
                "credentials": [
                    {"type": "password", "value": password, "temporary": False}
                ],
            },
            timeout=10.0,
        )
        if create_resp.status_code == 409:
            raise ValueError(f"A Keycloak user with email {email} already exists")
        create_resp.raise_for_status()

        location = create_resp.headers["Location"]
        return location.rstrip("/").split("/")[-1]

    def _assign_role(self, base: str, user_id: str, role: str) -> None:
        role_resp = httpx.get(f"{base}/roles/{role}", headers=self._headers(), timeout=10.0)
        role_resp.raise_for_status()
        role_repr = role_resp.json()

        assign_resp = httpx.post(
            f"{base}/users/{user_id}/role-mappings/realm",
            headers=self._headers(),
            json=[role_repr],
            timeout=10.0,
        )
        assign_resp.raise_for_status()

    def create_user(
        self, *, email: str, password: str, tenant_id: str, role: str, full_name: str = ""
    ) -> str:
        realm = self.settings.keycloak_realm
        base = f"{self.settings.keycloak_url}/admin/realms/{realm}"

        self._ensure_tenant_id_attribute(base)

        user_id = self._create_user_raw(
            base=base, email=email, password=password, attributes={"tenant_id": [tenant_id]}, full_name=full_name
        )
        self._assign_role(base, user_id, role)
        return user_id

    def create_platform_admin(self, *, email: str, password: str, full_name: str = "") -> str:
        """Platform admins aren't tied to any tenant — no tenant_id attribute
        at all (see core/security.py's carve-out for the platform_admin role).
        """
        realm = self.settings.keycloak_realm
        base = f"{self.settings.keycloak_url}/admin/realms/{realm}"

        user_id = self._create_user_raw(base=base, email=email, password=password, attributes={}, full_name=full_name)
        self._assign_role(base, user_id, "platform_admin")
        return user_id

    def _base(self) -> str:
        return f"{self.settings.keycloak_url}/admin/realms/{self.settings.keycloak_realm}"

    _TENANT_ROLES = ["bookkeeper", "accountant_manager", "admin", "auditor"]

    def list_users(self, tenant_id: str) -> list[dict]:
        """Keycloak supports searching custom attributes via `q=key:value`."""
        base = self._base()
        resp = httpx.get(
            f"{base}/users",
            headers=self._headers(),
            params={"q": f"tenant_id:{tenant_id}", "max": 200},
            timeout=10.0,
        )
        resp.raise_for_status()

        users = []
        for u in resp.json():
            roles_resp = httpx.get(f"{base}/users/{u['id']}/role-mappings/realm", headers=self._headers(), timeout=10.0)
            roles_resp.raise_for_status()
            user_roles = [r["name"] for r in roles_resp.json() if r["name"] in self._TENANT_ROLES]
            users.append(
                {
                    "id": u["id"],
                    "email": u.get("email"),
                    "full_name": " ".join(filter(None, [u.get("firstName"), u.get("lastName")])),
                    "enabled": u.get("enabled", True),
                    "roles": user_roles,
                }
            )
        return users

    def set_user_role(self, user_id: str, role: str) -> None:
        base = self._base()
        current_resp = httpx.get(f"{base}/users/{user_id}/role-mappings/realm", headers=self._headers(), timeout=10.0)
        current_resp.raise_for_status()
        to_remove = [r for r in current_resp.json() if r["name"] in self._TENANT_ROLES]
        if to_remove:
            httpx.request(
                "DELETE",
                f"{base}/users/{user_id}/role-mappings/realm",
                headers=self._headers(),
                json=to_remove,
                timeout=10.0,
            ).raise_for_status()
        self._assign_role(base, user_id, role)

    def set_user_enabled(self, user_id: str, enabled: bool) -> None:
        base = self._base()
        resp = httpx.put(
            f"{base}/users/{user_id}", headers=self._headers(), json={"enabled": enabled}, timeout=10.0
        )
        resp.raise_for_status()

    def delete_user(self, user_id: str) -> None:
        base = self._base()
        resp = httpx.delete(f"{base}/users/{user_id}", headers=self._headers(), timeout=10.0)
        resp.raise_for_status()

    def set_user_password(self, user_id: str, password: str) -> None:
        base = self._base()
        resp = httpx.put(
            f"{base}/users/{user_id}/reset-password",
            headers=self._headers(),
            json={"type": "password", "value": password, "temporary": False},
            timeout=10.0,
        )
        resp.raise_for_status()

    def list_emails_for_roles(self, tenant_id: str, roles: list[str]) -> list[str]:
        """Used for approval/escalation notifications — Keycloak has no
        native "users with role X in tenant Y" query, so this fetches by
        role then filters by the tenant_id attribute client-side.
        """
        realm = self.settings.keycloak_realm
        base = f"{self.settings.keycloak_url}/admin/realms/{realm}"

        emails: set[str] = set()
        for role in roles:
            resp = httpx.get(f"{base}/roles/{role}/users", headers=self._headers(), timeout=10.0)
            if resp.status_code != 200:
                continue
            for user in resp.json():
                user_tenant = (user.get("attributes") or {}).get("tenant_id", [None])[0]
                if user_tenant == tenant_id and user.get("email"):
                    emails.add(user["email"])
        return list(emails)
