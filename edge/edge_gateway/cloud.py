"""HTTP client for the control plane's edge API (ADR-0006)."""

from typing import Any

import httpx


class CloudUnavailable(Exception):
    """The control plane could not be reached, answered with a server error or refused the token."""


class CloudRejected(Exception):
    """The control plane refused one request (4xx other than 401); retrying it will not help."""


class Cloud:
    """Calls ``/edge/v1`` with the gateway token."""

    def __init__(self, base_url: str, token: str, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(timeout=10.0)
        self.base = base_url.rstrip("/") + "/edge/v1"
        self.headers = {"Authorization": f"Bearer {token}"}

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            response = self.client.request(
                method, self.base + path, json=body, headers=self.headers
            )
        except httpx.TransportError as exc:
            raise CloudUnavailable(str(exc)) from exc
        if response.status_code >= 500:
            raise CloudUnavailable(f"HTTP {response.status_code}")
        if response.status_code in (401, 403):
            raise CloudUnavailable(
                "token refused (HTTP 401): create a new token in Geräte → Gateway and set EDGE_TOKEN"
            )
        if response.status_code >= 400:
            raise CloudRejected(f"HTTP {response.status_code} for {path}: {response.text[:200]}")
        return response.json()

    def hello(self) -> dict[str, Any]:
        """The gateway's devices."""
        return self._call("POST", "/hello")

    def send_readings(self, readings: list[dict[str, Any]]) -> dict[str, Any]:
        """Deliver readings."""
        return self._call("POST", "/readings", {"readings": readings})

    def heartbeat(self, body: dict[str, Any]) -> dict[str, Any]:
        """Report health."""
        return self._call("POST", "/heartbeat", body)

    def commands(self) -> list[dict[str, Any]]:
        """Pending commands."""
        return self._call("GET", "/commands")["commands"]

    def ack(self, command_id: str, status: str, detail: str | None = None) -> dict[str, Any]:
        """Answer a command."""
        return self._call(
            "POST", f"/commands/{command_id}/ack", {"status": status, "detail": detail}
        )
