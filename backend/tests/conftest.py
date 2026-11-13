"""Shared pytest fixtures: database engine, transactional session, API client."""

import os
from collections.abc import AsyncIterator

# The engine fixture DROPS AND RECREATES the schema. CI sets TEST_DATABASE_URL to a throwaway
# database. Never point it at a database whose contents matter.
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/sb_test"),
)
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production-0123456789")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("RUN_JOBS", "false")

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine  # noqa: E402

import app.models  # noqa: E402,F401  (registers all tables on Base.metadata)
from app.api.deps import get_clock, get_db  # noqa: E402
from app.core.clock import FixedClock  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.factories import auth_headers, make_clock  # noqa: E402


@pytest.fixture(scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    """Create a fresh schema for the whole test session."""
    eng = create_async_engine(settings.database_url)
    async with eng.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {settings.db_schema} CASCADE"))
        await conn.execute(text(f"CREATE SCHEMA {settings.db_schema}"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    """A session whose commits become savepoints inside a rolled-back outer transaction."""
    async with engine.connect() as conn:
        outer = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await outer.rollback()


@pytest.fixture
def clock() -> FixedClock:
    """Deterministic clock at 2026-11-12T08:00Z."""
    return make_clock()


@pytest.fixture
async def client(db: AsyncSession, clock: FixedClock) -> AsyncIterator[AsyncClient]:
    """HTTP client against a fresh app instance bound to the test session."""
    application = create_app()

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield db

    application.dependency_overrides[get_db] = _override_db
    application.dependency_overrides[get_clock] = lambda: clock
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as http:
        yield http


@pytest.fixture
async def admin_headers(db: AsyncSession) -> dict[str, str]:
    """Authorization headers for a platform administrator."""
    return await auth_headers(db, role="admin")
