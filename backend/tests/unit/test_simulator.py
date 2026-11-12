"""The room simulator is a pure function."""

from app.services.twin.simulator import RoomState, step


def _state(**overrides: float) -> RoomState:
    base = {
        "temperature": 18.0,
        "setpoint": 21.0,
        "window": 0.0,
        "presence": 0.0,
        "valve": 0.0,
        "heat_meter": 0.0,
    }
    base.update(overrides)
    return RoomState(**base)


def test_heating_raises_the_temperature_towards_the_set_point() -> None:
    after = step(_state(), minutes=60, outdoor=5.0)
    assert after.valve > 0
    assert 18.0 < after.temperature < 21.0
    assert after.heat_meter > 0


def test_open_window_closes_the_valve_and_the_room_cools() -> None:
    after = step(_state(temperature=21.0, window=1.0), minutes=60, outdoor=5.0)
    assert after.valve == 0
    assert after.temperature < 21.0
    assert after.heat_meter == 0


def test_warm_room_does_not_heat() -> None:
    after = step(_state(temperature=22.0), minutes=15, outdoor=5.0)
    assert after.valve == 0
    assert after.heat_meter == 0


def test_same_inputs_same_outputs() -> None:
    assert step(_state(), minutes=15, outdoor=5.0) == step(_state(), minutes=15, outdoor=5.0)


def test_long_steps_are_split_and_stay_stable() -> None:
    after = step(_state(), minutes=24 * 60, outdoor=5.0)
    assert 20.0 < after.temperature < 21.5
