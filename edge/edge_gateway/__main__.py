"""Run the gateway: ``python -m edge_gateway``."""

import logging
import time
from datetime import UTC, datetime

from edge_gateway.buffer import Buffer
from edge_gateway.bus import BusDevice, SimulatedBus
from edge_gateway.cloud import Cloud, CloudUnavailable
from edge_gateway.config import Settings
from edge_gateway.gateway import Gateway


def main() -> None:
    """Start against the simulated bus and tick forever."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings.from_env()

    def bus_factory(devices: list[dict]) -> SimulatedBus:
        return SimulatedBus(
            [
                BusDevice(d["code"], d["room_code"], d["point_key"])
                for d in devices
                if d.get("room_code") and d.get("point_key")
            ],
            outdoor=settings.outdoor,
            scenario=settings.scenario,
            faulty=settings.faulty_devices,
        )

    gateway = Gateway(
        Cloud(settings.cloud_url, settings.token),
        bus_factory,
        Buffer(settings.buffer_path),
        lambda: datetime.now(UTC),
    )
    while True:
        try:
            gateway.start()
            break
        except CloudUnavailable as exc:
            logging.warning("waiting for the cloud: %s", exc)
            time.sleep(settings.tick_seconds)
    logging.info("gateway started with %d devices", len(gateway.devices))
    while True:
        gateway.tick(settings.simulated_minutes_per_tick)
        time.sleep(settings.tick_seconds)


if __name__ == "__main__":
    main()
