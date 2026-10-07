from pydantic import BaseModel


class RolePermissionsOut(BaseModel):
    modules: list[str]
    matrix: dict[str, list[str]]  # role -> module list, excludes admin (always all)


class RolePermissionsUpdate(BaseModel):
    matrix: dict[str, list[str]]
