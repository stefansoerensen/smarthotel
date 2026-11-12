"""Which device kinds and bus protocols the registry knows, and which kinds are safety devices.

The kinds cover the data points of a guest-room template (b29/SB1) plus the building devices the
platform must be able to see. Safety kinds are read by the platform and never controlled by it
(d12, ADR-0003): fire protection, smoke extraction, sprinklers, emergency lighting, evacuation.
"""

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
