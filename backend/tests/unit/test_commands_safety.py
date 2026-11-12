"""A command never targets a device that is not controllable (ADR-0003, ADR-0006)."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import FixedClock
from app.core.errors import DomainError
from app.services.devices import registry
from app.services.edge import commands
from tests.factories import NOW, create_property


async def test_command_for_a_read_only_device_is_refused(db: AsyncSession) -> None:
    prop = await create_property(db)
    gateway = await registry.register_gateway(db, prop, code="GW", name="GW")
    smoke = await registry.register_device(
        db,
        prop,
        code="S1",
        name="Rauchmelder",
        kind="smoke_detector",
        protocol="bacnet",
        gateway_code="GW",
    )
    assert gateway.id == smoke.gateway_id
    with pytest.raises(DomainError) as raised:
        await commands.create(db, prop, smoke, key="x", value=1.0, now=FixedClock(NOW).now())
    assert raised.value.code == "device.not_controllable"
