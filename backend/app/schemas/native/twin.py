"""Room types, rooms, rollout and simulator schemas."""

from datetime import datetime

from pydantic import BaseModel, Field

_CODE = r"^[A-Za-z0-9_-]+$"


class RoomTypeIn(BaseModel):
    """A new room type."""

    code: str = Field(min_length=1, max_length=20, pattern=_CODE)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    standard_points: bool = False


class RoomTypePatch(BaseModel):
    """Changes to a room type."""

    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class PointIn(BaseModel):
    """A new template point."""

    key: str = Field(min_length=1, max_length=40, pattern=r"^[a-z][a-z0-9_]*$")
    label: str = Field(min_length=1, max_length=100)
    kind: str
    protocol: str = "knx"
    unit: str | None = Field(default=None, max_length=20)
    writable: bool = False


class TemplatePointOut(BaseModel):
    """A template point."""

    key: str
    label: str
    kind: str
    protocol: str
    unit: str | None
    writable: bool


class RoomTypeOut(BaseModel):
    """A room type with its points."""

    code: str
    name: str
    description: str | None
    points: list[TemplatePointOut]


class RolloutIn(BaseModel):
    """Roll a room type out to rooms."""

    room_type_code: str
    room_codes: list[str] = Field(min_length=1, max_length=500)
    floor: str | None = Field(default=None, max_length=20)
    gateway_code: str | None = None


class RolloutOut(BaseModel):
    """What a rollout did."""

    rooms_created: int
    rooms_unchanged: int
    devices_created: int
    conflicts: list[str]


class RoomPointOut(BaseModel):
    """One twin point."""

    key: str
    label: str
    kind: str
    unit: str | None
    writable: bool
    device_code: str | None
    value: float | None
    value_at: datetime | None
    source: str | None
    desired: float | None
    desired_at: datetime | None


class RoomOut(BaseModel):
    """A room with its twin."""

    code: str
    name: str
    floor: str | None
    room_type_code: str | None
    gateway_code: str | None
    points: list[RoomPointOut]


class PointValueIn(BaseModel):
    """A value for a writable point."""

    value: float


class SimulatorStepIn(BaseModel):
    """Advance the simulation of a property."""

    minutes: float = Field(gt=0, le=24 * 60)
    outdoor: float = Field(default=5.0, ge=-30, le=45)


class SimulatorStepOut(BaseModel):
    """How many rooms were simulated."""

    rooms: int
    minutes: float
    outdoor: float


class SimulatorRoomIn(BaseModel):
    """Simulated inputs of a room."""

    window: bool | None = None
    presence: bool | None = None
