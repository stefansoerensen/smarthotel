"""History the twin keeps: meter readings and occupancy periods (SB4)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, fk


class MeterReading(TimestampMixin, Base):
    """A cumulative meter value (kWh) at a point in time."""

    __tablename__ = "meter_readings"
    __table_args__ = (Index("ix_meter_readings_point_time", "room_point_id", "measured_at"),)

    room_point_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("room_points")), nullable=False
    )
    room_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("rooms")), nullable=False, index=True
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)


class OccupancyPeriod(TimestampMixin, Base):
    """A stretch of time a room was occupied by one reservation, from the Hotel OS sync."""

    __tablename__ = "occupancy_periods"
    __table_args__ = (Index("ix_occupancy_periods_room_time", "room_id", "started_at"),)

    room_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("rooms")), nullable=False
    )
    reservation_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
