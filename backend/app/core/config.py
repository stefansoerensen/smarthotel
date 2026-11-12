"""Application settings loaded from environment variables."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ASYNC_SCHEME = "postgresql+asyncpg://"
_SYNC_SCHEMES = ("postgres://", "postgresql://")
_DROPPED_QUERY_PARAMS = frozenset({"sslmode"})

MIN_JWT_SECRET_LENGTH = 32
KNOWN_DEV_JWT_SECRETS = frozenset(
    {
        "dev-only-secret-change-me-0123456789abcdef",
        "test-secret-not-for-production-0123456789",
        "ci-test-secret-not-for-production-0123456789",
        "change-me",
        "changeme",
        "secret",
    }
)


def normalize_database_url(raw: str) -> str:
    """Return ``raw`` as a URL SQLAlchemy's asyncpg dialect accepts.

    Managed providers hand out ``postgresql://…`` (sometimes ``postgres://…``) and may append
    ``?sslmode=…``, which asyncpg rejects. An internal connection on a private network does not
    need it, so it is dropped; other query parameters are kept.
    """
    url = raw.strip()
    for scheme in _SYNC_SCHEMES:
        if url.startswith(scheme):
            url = _ASYNC_SCHEME + url[len(scheme) :]
            break
    parts = urlsplit(url)
    if parts.query:
        kept = [
            (key, value)
            for key, value in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in _DROPPED_QUERY_PARAMS
        ]
        url = urlunsplit(parts._replace(query=urlencode(kept)))
    return url


class InsecureConfigurationError(RuntimeError):
    """Raised at import time when production configuration would be unsafe.

    A ``RuntimeError`` rather than a ``ValueError``: pydantic would wrap a ``ValueError`` into a
    ``ValidationError`` whose message buries the reason, and this one must lead the deploy log.
    """


class Settings(BaseSettings):
    """Runtime configuration. All secrets come from the environment."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smarthotel"
    db_schema: str = "smarthotel"
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    cors_origins: list[str] = []
    admin_username: str = "admin"
    admin_password: str = ""
    static_dir: str = "static"
    # Coupling with the Hotel OS (ADR-0007); empty values switch the parts off.
    hotel_os_url: str = ""
    hotel_os_username: str = ""
    hotel_os_password: str = ""
    hotel_os_webhook_token: str = ""
    hotel_os_inbox_key: str = ""

    @field_validator("database_url", mode="after")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        """Accept a managed provider's URL verbatim and make it usable."""
        return normalize_database_url(value)

    @model_validator(mode="after")
    def _check_production_secrets(self) -> "Settings":
        """Refuse to start a production process with a guessable signing key."""
        if self.environment != "production":
            return self
        secret = self.jwt_secret.strip()
        if not secret:
            raise InsecureConfigurationError("JWT_SECRET must be set when ENVIRONMENT=production")
        if len(secret) < MIN_JWT_SECRET_LENGTH:
            raise InsecureConfigurationError(
                f"JWT_SECRET must be at least {MIN_JWT_SECRET_LENGTH} characters when "
                f"ENVIRONMENT=production (got {len(secret)})"
            )
        if secret in KNOWN_DEV_JWT_SECRETS:
            raise InsecureConfigurationError(
                "JWT_SECRET is a known development value; generate a fresh one "
                "(openssl rand -hex 32) and set it in the deployment's variables"
            )
        return self


settings = Settings()
