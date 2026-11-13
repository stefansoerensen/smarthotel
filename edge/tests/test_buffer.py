import os
from pathlib import Path

import pytest

from edge_gateway.buffer import Buffer


def test_readings_survive_a_restart_in_order(tmp_path: Path) -> None:
    path = str(tmp_path / "edge.sqlite")
    first = Buffer(path)
    first.add([("A", 1.0, "2026-11-12T08:00:00+00:00"), ("B", 2.0, "2026-11-12T08:00:15+00:00")])
    second = Buffer(path)
    assert [r.device_code for r in second.peek()] == ["A", "B"]
    second.remove([second.peek()[0].id])
    assert [r.device_code for r in Buffer(path).peek()] == ["B"]
    assert Buffer(path).count() == 1


def test_configuration_is_kept(tmp_path: Path) -> None:
    path = str(tmp_path / "edge.sqlite")
    Buffer(path).save_config({"gateway_code": "GW", "devices": []})
    assert Buffer(path).load_config() == {"gateway_code": "GW", "devices": []}


@pytest.mark.skipif(os.geteuid() == 0, reason="root can write anywhere")
def test_unwritable_path_falls_back_to_a_temporary_file(tmp_path: Path) -> None:
    blocked = tmp_path / "ro"
    blocked.mkdir()
    blocked.chmod(0o500)
    buffer = Buffer(str(blocked / "sub" / "edge.sqlite"))
    buffer.add([("A", 1.0, "2026-11-12T08:00:00+00:00")])
    assert buffer.count() == 1
    assert buffer.path != str(blocked / "sub" / "edge.sqlite")
