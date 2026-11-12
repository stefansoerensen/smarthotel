"""Commands from the control plane to a gateway (ADR-0006)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, fk

COMMAND_STATUSES = ("pending", "sent", "done", "failed", "refused")


class Command(TimestampMixin, Base):
    """Set one device to one value; executed and acknowledged by the gateway."""

    __tablename__ = "commands"
    __table_args__ = (Index("ix_commands_gateway_status", "gateway_id", "status"),)

    property_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("properties")), nullable=False, index=True
    )
    gateway_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("gateways")), nullable=False
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("devices")), nullable=False
    )
    device_code: Mapped[str] = mapped_column(String(60), nullable=False)
    point_key: Mapped[str] = mapped_column(String(40), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="pending")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
