"""A tenant (Mandant): the hotel company or group that owns properties."""

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class Tenant(TimestampMixin, Base):
    """A customer of the platform; every property and operator belongs to exactly one."""

    __tablename__ = "tenants"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
