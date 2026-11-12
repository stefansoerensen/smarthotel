"""The HTTP client reads the Hotel OS native API as the contract describes."""

import json
from datetime import date
from pathlib import Path

import httpx

from app.services.integration.hotel_os import HttpHotelOs, Stay

CONTRACTS = Path(__file__).resolve().parents[3] / "contracts" / "hotel-os-v1"


async def test_client_logs_in_finds_the_property_and_reads_stays() -> None:
    sample = json.loads((CONTRACTS / "reservations-response.json").read_text())
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(f"{request.method} {request.url.path}?{request.url.query.decode()}")
        if request.url.path == "/api/auth/login":
            assert json.loads(request.content) == {"username": "svc", "password": "pw"}
            return httpx.Response(200, json={"access_token": "jwt", "expires_in": 3600})
        assert request.headers["authorization"] == "Bearer jwt"
        if request.url.path == "/api/properties":
            return httpx.Response(200, json={"items": [{"id": "p-1", "code": "HAM"}], "total": 1})
        if request.url.path == "/api/reservations":
            statuses = request.url.params.get_list("status")
            if statuses == ["InHouse"]:
                return httpx.Response(200, json=sample)
            return httpx.Response(200, json={"items": [], "total": 0})
        return httpx.Response(404)

    client = HttpHotelOs(
        "https://pms.test", "svc", "pw", httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    stays = await client.current_stays("HAM", date(2026, 11, 12))
    assert stays == [Stay("ABCDEF-1", "101", "InHouse", date(2026, 11, 12), date(2026, 11, 14))]
    assert any(
        "status=Confirmed" in s and "date_filter=Arrival" in s and "from_date=2026-11-12" in s
        for s in seen
    )
    assert any("property_id=p-1" in s for s in seen)
