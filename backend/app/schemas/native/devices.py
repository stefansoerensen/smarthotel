"""Gateway, device and catalogue schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

_CODE = r"^[A-Za-z0-9_./-]+$"


class GatewayIn(BaseModel):
    """A new gateway."""

    code: str = Field(min_length=1, max_length=40, pattern=_CODE)
    name: str = Field(min_length=1, max_length=200)


class GatewayOut(BaseModel):
    """A gateway."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    status: str
    last_seen_at: datetime | None


class DeviceIn(BaseModel):
    """A new device. ``controllable`` defaults by kind: safety kinds are never controllable."""

    code: str = Field(min_length=1, max_length=60, pattern=_CODE)
    name: str = Field(min_length=1, max_length=200)
    kind: str
    protocol: str
    address: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=100)
    gateway_code: str | None = None
    controllable: bool | None = None


class DevicePatch(BaseModel):
    """Changes to a device; omitted fields stay as they are."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    kind: str | None = None
    protocol: str | None = None
    address: str | None = None
    location: str | None = None
    gateway_code: str | None = None
    controllable: bool | None = None


class DeviceOut(BaseModel):
    """A device in the registry."""

    code: str
    name: str
    kind: str
    protocol: str
    address: str | None
    location: str | None
    gateway_code: str | None
    controllable: bool
    safety: bool
    status: str


class KindOut(BaseModel):
    """One device kind of the catalogue."""

    kind: str
    label: str
    safety: bool


class CatalogueOut(BaseModel):
    """Device kinds and protocols the registry accepts."""

    kinds: list[KindOut]
    protocols: dict[str, str]
