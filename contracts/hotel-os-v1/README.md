# Hotel OS coupling v1 — message examples (ADR-0007)

| File | Direction |
|---|---|
| `webhook-request.json` | Hotel OS → Smart Building, `POST /api/integrations/hotel-os/webhook?token=<secret>` |
| `reservations-response.json` | Hotel OS → Smart Building, `GET /api/reservations` (fields used) |
| `energy-response.json` | Smart Building → Hotel OS, `GET /api/integrations/hotel-os/v1/energy?property_code=<code>&date=YYYY-MM-DD` with `X-Api-Key` (ADR-0008) |
| `faults-response.json` | Smart Building → Hotel OS, `GET /api/integrations/hotel-os/v1/faults?property_code=<code>` with `X-Api-Key` |

The Hotel OS repository keeps a copy of this folder; change both together.
