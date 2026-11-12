"""Verify that ``alembic upgrade head`` produces exactly the schema the models describe.

Run separately: ``pytest -m migrations``. The test drops and recreates the schema, so it must not
run alongside the ordinary suite.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.core.config import settings
from app.core.database import Base

BACKEND = Path(__file__).resolve().parents[2]


def _include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Restrict the comparison to the application schema."""
    if type_ == "schema":
        return name == settings.db_schema
    return True


@pytest.mark.migrations
async def test_upgrade_head_matches_models() -> None:
    """A fresh ``upgrade head`` must leave no difference against the ORM metadata."""
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {settings.db_schema} CASCADE"))
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, check=True)

    def diff(sync_conn: Any) -> list[Any]:
        context = MigrationContext.configure(
            sync_conn,
            opts={
                "include_schemas": True,
                "include_name": _include_name,
                "compare_type": True,
                "version_table_schema": settings.db_schema,
            },
        )
        return compare_metadata(context, Base.metadata)

    async with engine.connect() as conn:
        differences = await conn.run_sync(diff)
    await engine.dispose()

    assert differences == [], f"migrations drifted from the models: {differences}"
