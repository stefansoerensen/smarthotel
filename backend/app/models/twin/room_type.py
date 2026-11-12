"""Room types: templates of data points that rooms are rolled out from."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, fk


class RoomType(TimestampMixin, Base):
    """A template for rooms of one kind in a property (Standardzimmer, Suite, …)."""

    __tablename__ = "room_types"
    __table_args__ = (UniqueConstraint("property_id", "code"),)

    property_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("properties")), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RoomTypePoint(TimestampMixin, Base):
    """One data point of a room type; becomes one device and one twin point per room."""

    __tablename__ = "room_type_points"
    __table_args__ = (UniqueConstraint("room_type_id", "key"),)

    room_type_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("room_types")), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    writable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
