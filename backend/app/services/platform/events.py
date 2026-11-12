"""Emit domain events into the transactional outbox."""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.models.platform.outbox_event import OutboxEvent

logger = logging.getLogger(__name__)


async def emit(
    session: AsyncSession,
    *,
    topic: str,
    event_type: str,
    entity_code: str,
    property_code: str | None,
    payload: dict[str, Any] | None = None,
) -> OutboxEvent:
    """Record an event in the current transaction; never call it after the commit."""
    event = OutboxEvent(
        topic=topic,
        event_type=event_type,
        entity_code=entity_code,
        property_code=property_code,
        payload=payload or {},
        occurred_at=utcnow(),
        processed_at=None,
        attempts=0,
    )
    session.add(event)
    await session.flush()
    logger.debug("event %s/%s %s", topic, event_type, entity_code)
    return event
