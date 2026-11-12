"""Turning cumulative meter readings into consumption per interval."""

from datetime import UTC, datetime, timedelta

from app.services.energy.aggregate import Reading, consumption_by_bucket, day_edges, quarter_edges

T0 = datetime(2026, 11, 12, 8, 0, tzinfo=UTC)


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def test_deltas_go_to_the_bucket_of_the_later_reading() -> None:
    readings = [Reading(at(0), 10.0), Reading(at(10), 10.5), Reading(at(20), 11.5)]
    edges = quarter_edges(at(0), at(30))
    assert consumption_by_bucket(readings, edges) == [0.5, 1.0]


def test_a_counter_reset_counts_nothing() -> None:
    readings = [Reading(at(0), 100.0), Reading(at(5), 0.2), Reading(at(10), 0.7)]
    assert consumption_by_bucket(readings, quarter_edges(at(0), at(15))) == [0.5]


def test_readings_before_the_range_count_as_the_start_value() -> None:
    readings = [Reading(at(-60), 5.0), Reading(at(5), 6.0)]
    assert consumption_by_bucket(readings, quarter_edges(at(0), at(15))) == [1.0]


def test_local_days_follow_the_property_time_zone() -> None:
    edges = day_edges(datetime(2026, 11, 12).date(), datetime(2026, 11, 13).date(), "Europe/Berlin")
    assert [e.isoformat() for e in edges] == [
        "2026-11-11T23:00:00+00:00",
        "2026-11-12T23:00:00+00:00",
        "2026-11-13T23:00:00+00:00",
    ]
