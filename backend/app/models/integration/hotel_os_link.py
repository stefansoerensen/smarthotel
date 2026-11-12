"""Link of a property to its property in the Hotel OS (ADR-0007)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin, fk


class HotelOsLink(TimestampMixin, Base):
    """Which Hotel OS property feeds a property's occupancy, and the set points per mode."""

    __tablename__ = "hotel_os_links"

    property_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey(fk("properties")), nullable=False, unique=True
    )
    hotel_os_property_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    comfort_setpoint: Mapped[float] = mapped_column(Float, nullable=False, default=21.0)
    eco_setpoint: Mapped[float] = mapped_column(Float, nullable=False, default=17.0)
    # Price per kWh of heat/electricity for the live P&L (d31); money is Decimal, never float.
    energy_price_eur_per_kwh: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
