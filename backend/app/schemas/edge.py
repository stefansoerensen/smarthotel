"""Edge protocol v1 messages (ADR-0006, contracts/edge-v1)."""

import uuid
from datetime import datetime

from pydantic import AwareDatetime, BaseModel, Field


class EdgeDevice(BaseModel):
    """A device the gateway is responsible for."""

    code: str
    kind: str
    protocol: str
    address: str | None
    controllable: bool
    room_code: str | None
    point_key: str | None


class HelloOut(BaseModel):
    """The gateway's configuration."""

    gateway_code: str
    property_code: str
    devices: list[EdgeDevice]


class Reading(BaseModel):
    """One measured value."""

    device_code: str
    value: float
    measured_at: AwareDatetime


class ReadingsIn(BaseModel):
    """A batch of readings, oldest first."""

    readings: list[Reading] = Field(max_length=5000)


class ReadingsOut(BaseModel):
    """How many readings were applied and how many were older or unknown."""

    accepted: int
    ignored: int


class DeviceHealth(BaseModel):
    """Health of one device as the gateway sees it."""

    device_code: str
    ok: bool


class HeartbeatIn(BaseModel):
    """Sign of life with device health."""

    sent_at: AwareDatetime
    buffered: int = 0
    health: list[DeviceHealth] = Field(default_factory=list)


class HeartbeatOut(BaseModel):
    """Acknowledged heartbeat."""

    status: str


class EdgeCommand(BaseModel):
    """A command for the gateway."""

    id: uuid.UUID
    device_code: str
    value: float
    created_at: datetime


class CommandsOut(BaseModel):
    """Commands handed out to the gateway."""

    commands: list[EdgeCommand]


class AckIn(BaseModel):
    """The gateway's answer to a command."""

    status: str
    detail: str | None = Field(default=None, max_length=500)


class AckOut(BaseModel):
    """The stored answer."""

    id: uuid.UUID
    status: str
