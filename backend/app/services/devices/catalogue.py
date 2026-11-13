"""Which device kinds and bus protocols the registry knows, and which kinds are safety devices.

The kinds cover the data points of a guest-room template (b29/SB1) plus the building devices the
platform must be able to see. Safety kinds are read by the platform and never controlled by it
(d12, ADR-0003): fire protection, smoke extraction, sprinklers, emergency lighting, evacuation.
"""

import re

DEVICE_KINDS: dict[str, str] = {
    "temperature_sensor": "Raumtemperatur",
    "thermostat": "Sollwertgeber / Raumbediengerät",
    "window_contact": "Fensterkontakt",
    "door_contact": "Türkontakt",
    "presence_sensor": "Präsenzmelder",
    "humidity_sensor": "Luftfeuchte",
    "co2_sensor": "CO2",
    "valve": "Heizventil",
    "fan_coil": "Fan-Coil",
    "light": "Licht",
    "blind": "Jalousie",
    "meter": "Zähler",
    "lock": "Türschloss",
    "fire_alarm": "Brandmeldeanlage",
    "smoke_detector": "Rauchmelder",
    "smoke_extraction": "Rauch- und Wärmeabzug",
    "sprinkler": "Sprinkler",
    "emergency_light": "Sicherheitsbeleuchtung",
    "evacuation": "Evakuierung / Sprachalarm",
    "other": "Sonstiges",
}

SAFETY_KINDS: frozenset[str] = frozenset(
    {
        "fire_alarm",
        "smoke_detector",
        "smoke_extraction",
        "sprinkler",
        "emergency_light",
        "evacuation",
    }
)

PROTOCOLS: dict[str, str] = {
    "knx": "KNX/IP",
    "bacnet": "BACnet/IP",
    "modbus": "Modbus TCP/RTU",
    "mqtt": "MQTT",
    "simulator": "Simulator",
    "vendor_api": "Hersteller-API",
}


def is_safety(kind: str) -> bool:
    """True for kinds the platform may read but never control."""
    return kind in SAFETY_KINDS


# Kinds whose value is measured, never set by the platform. Safety kinds are read only as well.
SENSOR_KINDS: frozenset[str] = frozenset(
    {
        "temperature_sensor",
        "window_contact",
        "door_contact",
        "presence_sensor",
        "humidity_sensor",
        "co2_sensor",
        "meter",
    }
)


def can_write(kind: str) -> bool:
    """True for kinds the platform may set (set points, valves, lights, blinds, locks …)."""
    return kind not in SENSOR_KINDS and kind not in SAFETY_KINDS


_KNX = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{1,3})$")


def valid_knx(address: str) -> bool:
    """A three-level KNX group address: main 0–31, middle 0–7, sub 0–255."""
    match = _KNX.match(address)
    if not match:
        return False
    main, middle, sub = (int(part) for part in match.groups())
    return main <= 31 and middle <= 7 and sub <= 255


def check_address(protocol: str, address: str) -> str | None:
    """A German error message when ``address`` is invalid for ``protocol``, else None."""
    if protocol == "knx" and not valid_knx(address):
        return f"Keine gültige KNX-Gruppenadresse: {address}"
    return None
