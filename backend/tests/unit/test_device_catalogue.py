"""The device catalogue: which kinds exist and which are safety devices."""

from app.services.devices import catalogue


def test_safety_kinds_are_known_kinds() -> None:
    assert catalogue.SAFETY_KINDS <= set(catalogue.DEVICE_KINDS)


def test_fire_and_life_safety_are_safety_kinds() -> None:
    for kind in ("fire_alarm", "smoke_detector", "sprinkler", "emergency_light", "evacuation"):
        assert catalogue.is_safety(kind)
    assert not catalogue.is_safety("thermostat")


def test_room_template_datapoints_are_covered() -> None:
    # b29/SB1: room temperature, set point, window contact, presence, valve/fan coil, light, meter
    for kind in (
        "temperature_sensor",
        "thermostat",
        "window_contact",
        "presence_sensor",
        "valve",
        "fan_coil",
        "light",
        "meter",
    ):
        assert kind in catalogue.DEVICE_KINDS
