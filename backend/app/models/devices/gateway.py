"""An edge gateway: the box in the building that talks to the field buses."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, fk

GATEWAY_STATUSES = ("provisioned", "online", "offline", "retired")


class Gateway(TimestampMixin, Base):
    """One edge gateway in a property. Status is reported by the gateway itself from SB2 on."""

    __tablename__ = "gateways"
    __table_args__ = (UniqueConstraint("property_id", "code"),)

    property_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("properties")), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="provisioned")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # SHA-256 of the gateway's token (ADR-0006); the token itself is shown once and never stored.
    token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    provisioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
