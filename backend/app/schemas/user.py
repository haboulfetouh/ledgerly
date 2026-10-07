from pydantic import BaseModel

TENANT_ROLES = ["bookkeeper", "accountant_manager", "admin", "auditor"]


class UserOut(BaseModel):
    id: str
    email: str | None
    full_name: str
    enabled: bool
    roles: list[str]


class UserInviteRequest(BaseModel):
    email: str
    password: str
    role: str
    full_name: str = ""


class UserUpdateRequest(BaseModel):
    role: str | None = None
    enabled: bool | None = None
