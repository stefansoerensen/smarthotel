"""Background jobs: periodic Hotel OS sync (ADR-0009)."""

from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.integration import occupancy
from app.services.integration.hotel_os import HotelOsUnavailable, Stay
from app.workers import jobs
from tests.factories import NOW, create_property


class FakeHotelOs:
    def __init__(self, failing: set[str] | None = None) -> None:
        self.failing = failing or set()
        self.calls: list[str] = []

    async def current_stays(self, property_code: str, today: date) -> list[Stay]:
        self.calls.append(property_code)
        if property_code in self.failing:
            raise HotelOsUnavailable("down")
        return []


async def _linked(db: AsyncSession, hotel_os_code: str, *, enabled: bool = True):
    prop = await create_property(db)
    link = await occupancy.save_link(
        db,
        prop,
        hotel_os_property_code=hotel_os_code,
        enabled=enabled,
        comfort_setpoint=21,
        eco_setpoint=17,
    )
    return prop, link


async def test_due_links_are_synced_and_failures_are_recorded(db: AsyncSession) -> None:
    ok_prop, ok_link = await _linked(db, "OK")
    bad_prop, bad_link = await _linked(db, "BAD")
    _, off_link = await _linked(db, "OFF", enabled=False)
    fake = FakeHotelOs(failing={"BAD"})

    synced = await jobs.sync_due_links(db, fake, now=NOW, interval=timedelta(minutes=10))
    assert sorted(synced) == sorted([ok_prop.code])
    assert sorted(fake.calls) == ["BAD", "OK"]
    assert ok_link.last_sync_at == NOW and ok_link.last_sync_error is None
    assert bad_link.last_sync_error == "down"
    assert off_link.last_sync_at is None


async def test_links_synced_recently_are_not_due(db: AsyncSession) -> None:
    _, link = await _linked(db, "RECENT")
    link.last_sync_at = NOW - timedelta(minutes=5)
    fake = FakeHotelOs()
    await jobs.sync_due_links(db, fake, now=NOW, interval=timedelta(minutes=10))
    assert "RECENT" not in fake.calls
    await jobs.sync_due_links(
        db, fake, now=NOW + timedelta(minutes=6), interval=timedelta(minutes=10)
    )
    assert "RECENT" in fake.calls


async def test_without_configuration_nothing_happens(
    db: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "hotel_os_url", "")
    assert jobs.hotel_os_client() is None


async def test_lock_lets_only_one_runner_through(db: AsyncSession, engine) -> None:
    async with engine.connect() as first, engine.connect() as second:
        assert await jobs.try_lock(first) is True
        assert await jobs.try_lock(second) is False
        await jobs.unlock(first)
        assert await jobs.try_lock(second) is True
        await jobs.unlock(second)


async def test_jobs_are_off_in_tests(client) -> None:
    assert client._transport.app.state.jobs is None  # type: ignore[attr-defined]
