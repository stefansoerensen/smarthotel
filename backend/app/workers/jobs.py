"""Background jobs in the API process, one runner at a time (ADR-0009)."""

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession

from app.core.clock import SystemClock
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.estate.property import Property
from app.models.integration.hotel_os_link import HotelOsLink
from app.services.integration import occupancy
from app.services.integration.hotel_os import HotelOs, HttpHotelOs, configured_client

logger = logging.getLogger(__name__)

LOCK_KEY = 4_711_001  # pg advisory lock id for the job runner
TICK_SECONDS = 60


def hotel_os_client() -> HttpHotelOs | None:
    """The configured client, or None when the coupling is not set up."""
    return configured_client()


async def try_lock(connection: AsyncConnection) -> bool:
    """Take the runner lock on ``connection`` if nobody holds it."""
    result = await connection.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": LOCK_KEY})
    return bool(result.scalar())


async def unlock(connection: AsyncConnection) -> None:
    """Release the runner lock."""
    await connection.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": LOCK_KEY})


async def sync_due_links(
    session: AsyncSession, hotel_os: HotelOs, *, now: datetime, interval: timedelta
) -> list[str]:
    """Sync every enabled link whose last sync is older than ``interval``; returns synced codes.

    Each property runs in its own savepoint; a failure is stored on its link and the next one runs.
    """
    result = await session.execute(select(HotelOsLink).where(HotelOsLink.enabled.is_(True)))
    synced: list[str] = []
    for link in result.scalars().all():
        if link.last_sync_at is not None and now - link.last_sync_at < interval:
            continue
        prop = await session.get(Property, link.property_id)
        if prop is None:
            continue
        today = now.astimezone(ZoneInfo(prop.time_zone)).date()
        try:
            async with session.begin_nested():
                await occupancy.sync_property(session, prop, link, hotel_os, today=today, now=now)
            synced.append(prop.code)
        except Exception as exc:  # noqa: BLE001 - one property must not stop the others
            await session.refresh(link)
            link.last_sync_at = now
            link.last_sync_error = (getattr(exc, "message", None) or str(exc))[:500]
            await session.flush()
            logger.warning("hotel os sync of %s failed: %s", prop.code, exc)
    return synced


async def run_once() -> None:
    """One round of all jobs, if this process gets the lock."""
    client = hotel_os_client()
    if client is None:
        return
    async with SessionLocal() as session:
        connection = await session.connection()
        if not await try_lock(connection):
            return
        try:
            synced = await sync_due_links(
                session,
                client,
                now=SystemClock().now(),
                interval=timedelta(minutes=settings.hotel_os_sync_minutes),
            )
            await session.commit()
            if synced:
                logger.info("hotel os sync: %s", ", ".join(synced))
        finally:
            await unlock(await session.connection())
            await session.commit()


async def run_forever() -> None:
    """Run the jobs every minute until cancelled."""
    while True:
        try:
            await run_once()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - keep the loop alive
            logger.exception("job round failed")
        await asyncio.sleep(TICK_SECONDS)
