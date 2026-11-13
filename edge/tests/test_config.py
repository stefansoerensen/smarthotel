import pytest

from edge_gateway.config import ConfigError, Settings


def test_missing_variables_are_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EDGE_CLOUD_URL", raising=False)
    monkeypatch.delenv("EDGE_TOKEN", raising=False)
    with pytest.raises(ConfigError, match="EDGE_CLOUD_URL, EDGE_TOKEN"):
        Settings.from_env()


def test_url_without_scheme_gets_https(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDGE_CLOUD_URL", "app.up.railway.app/")
    monkeypatch.setenv("EDGE_TOKEN", "t")
    assert Settings.from_env().cloud_url == "https://app.up.railway.app"


def test_bad_number_is_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EDGE_CLOUD_URL", "https://x")
    monkeypatch.setenv("EDGE_TOKEN", "t")
    monkeypatch.setenv("EDGE_TICK_SECONDS", "fast")
    with pytest.raises(ConfigError, match="EDGE_TICK_SECONDS"):
        Settings.from_env()
