"""Commands to gateways: create for controllable devices, hand out once, acknowledge (ADR-0006)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError, NotFoundError
from app.core.query import paginate
from app.models.edge.command import Command

if TYPE_CHECKING:
    from app.models.devices.device import Device
    from app.models.devices.gateway import Gateway
    from app.models.estate.property import Property

ACK_STATUSES = ("done", "failed", "refused")


async def create(
    session: AsyncSession,
    prop: Property,
    device: Device,
    *,
    key: str,
    value: float,
    now: datetime,
) -> Command:
    """Queue ``value`` for ``device``. Refused for devices that are not controllable (ADR-0003)."""
    if not device.controllable or device.status == "retired":
        raise DomainError(
            "device.not_controllable", f"Device '{device.code}' cannot receive commands"
        )
    if device.gateway_id is None:
        raise DomainError("device.no_gateway", f"Device '{device.code}' has no gateway")
    command = Command(
        property_id=prop.id,
        gateway_id=device.gateway_id,
        device_id=device.id,
        device_code=device.code,
        point_key=key,
        value=value,
        status="pending",
    )
    command.created_at = now
    session.add(command)
    await session.flush()
    return command


async def take_pending(session: AsyncSession, gateway: Gateway, *, now: datetime) -> list[Command]:
    """Hand out the gateway's pending commands, oldest first, and mark them sent."""
    result = await session.execute(
        select(Command)
        .where(Command.gateway_id == gateway.id, Command.status == "pending")
        .order_by(Command.created_at)
        .with_for_update(skip_locked=True)
    )
    taken = list(result.scalars())
    for command in taken:
        command.status = "sent"
        command.sent_at = now
    await session.flush()
    return taken


async def acknowledge(
    session: AsyncSession,
    gateway: Gateway,
    command_id: uuid.UUID,
    *,
    status: str,
    detail: str | None,
    now: datetime,
) -> Command:
    """Record the gateway's answer to one of its commands."""
    if status not in ACK_STATUSES:
        raise DomainError("command.unknown_status", f"Unknown status '{status}'")
    command = await session.get(Command, command_id)
    if command is None or command.gateway_id != gateway.id:
        raise NotFoundError("command", command_id)
    command.status = status
    command.detail = detail
    command.acked_at = now
    await session.flush()
    return command


async def list_for_property(
    session: AsyncSession, prop: Property, *, skip: int, limit: int
) -> tuple[list[Command], int]:
    """Commands of a property, newest first."""
    stmt = select(Command).where(Command.property_id == prop.id).order_by(Command.created_at.desc())
    return await paginate(session, stmt, skip=skip, limit=limit)
