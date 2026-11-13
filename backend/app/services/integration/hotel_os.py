"""Reading occupancy from the Hotel OS native API (ADR-0007)."""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import httpx

from app.core.errors import AppError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Stay:
    """A reservation as far as the building cares."""

    reservation_code: str
    unit_name: str | None
    status: str
    arrival_date: date
    departure_date: date


class HotelOs(Protocol):
    """What the occupancy sync needs from the Hotel OS."""

    async def current_stays(self, property_code: str, today: date) -> list[Stay]:
        """Guests in house and confirmed arrivals of ``today``."""


class HotelOsUnavailable(AppError):
    """The Hotel OS could not be reached or refused the request."""

    status_code = 502

    def __init__(self, message: str) -> None:
        super().__init__("hotel_os.unavailable", message)


class HttpHotelOs:
    """The Hotel OS native API with a service user."""

    def __init__(
        self, base_url: str, username: str, password: str, client: httpx.AsyncClient | None = None
    ) -> None:
        self.base = base_url.rstrip("/") + "/api"
        self.username = username
        self.password = password
        self.client = client or httpx.AsyncClient(timeout=15.0)
        self._token: str | None = None

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            if self._token is None:
                login = await self.client.post(
                    f"{self.base}/auth/login",
                    json={"username": self.username, "password": self.password},
                )
                if login.status_code != 200:
                    raise HotelOsUnavailable(f"Login at the Hotel OS failed ({login.status_code})")
                self._token = login.json()["access_token"]
            response = await self.client.request(
                method,
                f"{self.base}{path}",
                headers={"Authorization": f"Bearer {self._token}"},
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise HotelOsUnavailable(f"Hotel OS unreachable: {exc}") from exc
        if response.status_code == 401:
            self._token = None
        if response.status_code != 200:
            raise HotelOsUnavailable(f"Hotel OS answered {response.status_code} for {path}")
        return response.json()

    async def _property_id(self, code: str) -> str:
        page = await self._request("GET", "/properties", params={"limit": 500})
        for item in page["items"]:
            if item["code"] == code:
                return str(item["id"])
        raise HotelOsUnavailable(f"No property '{code}' in the Hotel OS")

    async def current_stays(self, property_code: str, today: date) -> list[Stay]:
        """In-house guests plus confirmed arrivals of ``today``."""
        property_id = await self._property_id(property_code)
        in_house = await self._request(
            "GET",
            "/reservations",
            params={"property_id": property_id, "status": "InHouse", "limit": 500},
        )
        arriving = await self._request(
            "GET",
            "/reservations",
            params={
                "property_id": property_id,
                "status": "Confirmed",
                "date_filter": "Arrival",
                "from_date": today.isoformat(),
                "to_date": today.isoformat(),
                "limit": 500,
            },
        )
        return [
            Stay(
                reservation_code=item["code"],
                unit_name=item.get("unit_name"),
                status=item["status"],
                arrival_date=date.fromisoformat(item["arrival_date"]),
                departure_date=date.fromisoformat(item["departure_date"]),
            )
            for item in [*in_house["items"], *arriving["items"]]
        ]


_client: HttpHotelOs | None = None


def configured_client() -> HttpHotelOs | None:
    """The Hotel OS client from the ``HOTEL_OS_*`` settings, or None when they are not set."""
    from app.core.config import settings

    global _client
    if not (settings.hotel_os_url and settings.hotel_os_username and settings.hotel_os_password):
        return None
    if _client is None:
        _client = HttpHotelOs(
            settings.hotel_os_url, settings.hotel_os_username, settings.hotel_os_password
        )
    return _client
