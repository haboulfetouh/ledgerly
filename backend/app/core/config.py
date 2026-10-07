from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://redis:6379/0"

    minio_endpoint: str = "minio:9000"
    # Browser-reachable address — presigned URLs are signed for this host,
    # since "minio" (the internal Docker hostname) doesn't resolve outside
    # the compose network. Same pattern as keycloak_public_url below.
    minio_public_endpoint: str = "localhost:9000"
    minio_root_user: str
    minio_root_password: str
    minio_bucket: str = "ledgerly-documents"
    minio_secure: bool = False

    # Internal, container-to-container address — used to fetch JWKS and call the Admin API.
    keycloak_url: str = "http://keycloak:8080"
    # Address the *browser* actually authenticates against — this is what ends up in every
    # token's `iss` claim, which will not match keycloak_url when the browser reaches
    # Keycloak via a different (host-mapped) hostname/port than the backend does.
    keycloak_public_url: str = "http://localhost:8081"
    keycloak_realm: str = "ledgerly"
    keycloak_backend_client_id: str = "ledgerly-backend"
    keycloak_backend_client_secret: str = ""
    keycloak_frontend_client_id: str = "ledgerly-frontend"
    keycloak_admin: str = "admin"
    keycloak_admin_password: str = ""

    secrets_encryption_key: str = ""

    anthropic_api_key: str = ""
    anthropic_extraction_model: str = "claude-sonnet-5"
    anthropic_explanation_model: str = "claude-haiku-4-5-20251001"

    smtp_host: str = "mailhog"
    smtp_port: int = 1025
    smtp_from: str = "noreply@ledgerly.local"

    # Comma-separated. Dev origins stay in the default so local dev keeps
    # working without a .env override; production adds its real origin here.
    cors_allow_origins: str = (
        "http://localhost:5173,http://localhost:5174,"
        "http://localhost:5175,http://127.0.0.1:5175"
    )

    @property
    def cors_allow_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @property
    def keycloak_issuer(self) -> str:
        return f"{self.keycloak_public_url}/realms/{self.keycloak_realm}"

    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}/protocol/openid-connect/certs"


@lru_cache
def get_settings() -> Settings:
    return Settings()
