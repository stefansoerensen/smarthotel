from edge_gateway.rules import room_writes, valve_for


def test_window_open_turns_the_heating_off() -> None:
    assert valve_for(18.0, 21.0, 1.0) == 0.0
    assert valve_for(18.0, 21.0, 0.0) == 100.0


def test_frost_protection_wins_even_with_an_open_window() -> None:
    assert valve_for(6.5, 21.0, 1.0) == 100.0


def test_proportional_valve() -> None:
    assert valve_for(20.5, 21.0, 0.0) == 30.0
    assert valve_for(22.0, 21.0, 0.0) == 0.0


def test_rules_only_write_controllable_points() -> None:
    values = {"temperature": 18.0, "setpoint": 21.0, "window": 0.0, "valve": 0.0}
    assert room_writes(values, {"valve", "setpoint"}) == {"valve": 100.0}
    assert room_writes(values, {"setpoint"}) == {}
