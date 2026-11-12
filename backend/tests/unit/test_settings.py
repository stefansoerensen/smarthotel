"""Configuration rules."""

import pytest

from app.core.config import InsecureConfigurationError, Settings, normalize_database_url


def test_managed_postgres_url_is_made_async_and_drops_sslmode() -> None:
    raw = "postgresql://u:p@postgres.railway.internal:5432/railway?sslmode=require&x=1"
    assert normalize_database_url(raw) == (
        "postgresql+asyncpg://u:p@postgres.railway.internal:5432/railway?x=1"
    )
    assert normalize_database_url("postgres://u:p@h/db").startswith("postgresql+asyncpg://")


@pytest.mark.parametrize("secret", ["", "short", "ci-test-secret-not-for-production-0123456789"])
def test_production_refuses_a_weak_jwt_secret(secret: str) -> None:
    with pytest.raises(InsecureConfigurationError):
        Settings(environment="production", jwt_secret=secret)


def test_production_accepts_a_strong_secret() -> None:
    settings = Settings(environment="production", jwt_secret="a" * 16 + "b" * 16 + "c")
    assert settings.environment == "production"
