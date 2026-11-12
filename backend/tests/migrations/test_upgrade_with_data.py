"""Migrations must apply to a database that already holds rows (Railway does)."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND = Path(__file__).resolve().parents[2]


def _alembic(*args: str) -> None:
    subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND, check=True)


@pytest.mark.migrations
async def test_edge_columns_apply_to_existing_devices() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS smarthotel CASCADE"))
    _alembic("upgrade", "0002")
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO smarthotel.tenants (id, code, name, is_active, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'T', 'T', true, now(), now())"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO smarthotel.properties (id, tenant_id, code, name, time_zone, "
                "country_code, created_at, updated_at) SELECT gen_random_uuid(), id, 'P', 'P', "
                "'Europe/Berlin', 'DE', now(), now() FROM smarthotel.tenants"
            )
        )
        await conn.execute(
            text(
                "INSERT INTO smarthotel.devices (id, property_id, code, name, kind, protocol, "
                "controllable, status, created_at, updated_at) SELECT gen_random_uuid(), id, 'D', "
                "'D', 'light', 'knx', true, 'active', now(), now() FROM smarthotel.properties"
            )
        )
    _alembic("upgrade", "head")
    async with engine.begin() as conn:
        health = (await conn.execute(text("SELECT health FROM smarthotel.devices"))).scalar()
    await engine.dispose()
    assert health == "unknown"
