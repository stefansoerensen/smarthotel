"""Transactional outbox for domain events."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, utcnow


class OutboxEvent(TimestampMixin, Base):
    """A domain event recorded in the transaction that changed the data.

    SB0 only records events. Delivery (webhooks, the Hotel OS coupling) starts with SB3, through a
    worker that reads unprocessed rows in ``occurred_at`` order.
    """

    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_events_unprocessed", "processed_at", "occurred_at"),)

    topic: Mapped[str] = mapped_column(String(50), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_code: Mapped[str] = mapped_column(String(100), nullable=False)
    property_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
