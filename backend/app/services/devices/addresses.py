"""Bus addresses from a list: an own CSV (``code;address``) or an ETS group address export.

In an ETS export the group name is used as device code, so name the group addresses like the
devices (``101-VALVE``). Middle and main groups (``1/-/-``, ``1/2/-``) are skipped.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.devices import registry
from app.services.devices.catalogue import check_address

if TYPE_CHECKING:
    from app.models.estate.property import Property

_HEADER_WORDS = {"code", "address", "adresse", "group name", "gruppenname", "name"}


@dataclass(frozen=True)
class Row:
    """One usable line."""

    line: int
    code: str
    address: str


@dataclass(frozen=True)
class LineError:
    """A line that could not be used, and why (German, shown to the operator)."""

    line: int
    message: str


@dataclass(frozen=True)
class Change:
    """An address that would change."""

    line: int
    device_code: str
    old: str | None
    new: str


def parse_address_list(text: str) -> tuple[list[Row], list[LineError]]:
    """Read ``code;address`` lines (``;`` or ``,``, quoted or not, optional header)."""
    rows: list[Row] = []
    errors: list[LineError] = []
    first = text.lstrip("﻿").splitlines()[0] if text.strip() else ""
    delimiter = ";" if first.count(";") >= first.count(",") else ","
    reader = csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=delimiter)
    for number, fields in enumerate(reader, start=1):
        fields = [f.strip() for f in fields]
        if not any(fields):
            continue
        if number == 1 and fields[0].lower() in _HEADER_WORDS:
            continue
        if len(fields) < 2:
            errors.append(LineError(number, "Zwei Spalten erwartet: Code und Adresse"))
            continue
        code, address = fields[0], fields[1]
        if not code:
            errors.append(LineError(number, "Code fehlt"))
            continue
        if not address:
            errors.append(LineError(number, "Adresse fehlt"))
            continue
        if address.endswith("/-"):
            continue
        rows.append(Row(number, code, address))
    return rows, errors


async def import_addresses(
    session: AsyncSession, prop: Property, text: str, *, apply: bool
) -> tuple[list[Change], list[LineError]]:
    """Match lines to devices of ``prop``; with ``apply`` store the new addresses."""
    rows, errors = parse_address_list(text)
    changes: list[Change] = []
    for row in rows:
        device = await registry.find_device(session, prop, row.code)
        if device is None or device.status == "retired":
            errors.append(LineError(row.line, f"Gerät {row.code} gibt es in diesem Haus nicht"))
            continue
        problem = check_address(device.protocol, row.address)
        if problem:
            errors.append(LineError(row.line, problem))
            continue
        if device.address == row.address:
            continue
        changes.append(Change(row.line, device.code, device.address, row.address))
        if apply:
            await registry.update_device(session, prop, device, {"address": row.address})
    return changes, sorted(errors, key=lambda e: e.line)
