# ADR-0007: Coupling with the Hotel OS — occupancy pulled on webhook, faults pulled by the inbox

Status: Accepted (2026-11-12). SB3, hub b29. The Hotel OS (pms-clone) keeps the same ADR.

## Context
Rooms should save energy when empty and be warm when a guest arrives; the front desk should learn
about a cold room or a dead gateway in the place it already works — the Hotel OS exception inbox.
The Hotel OS sends unsigned webhooks with only an entity code, and its inbox is a read model built
from its own data.

## Decision
- **Occupancy is reconciled, not replayed.** Smart Building reads the current reservations of the
  linked property (in house; confirmed and arriving today) through the Hotel OS native API with a
  service user, and sets every room's occupancy and mode from that picture. A `Reservation` webhook
  only triggers the sync; lost or repeated webhooks change nothing. A manual sync does the same.
- **Mode → set point:** occupied → comfort (default 21 °C), arriving today → preheat (comfort set
  point), vacant → eco (default 17 °C). The set point is written only when the mode changes, so a
  guest's own adjustment stays until checkout. Rooms behind a gateway get a command (ADR-0006).
- **Webhook authentication:** a shared secret in the subscription URL (`?token=`), compared in
  constant time. Signing can replace it when the Hotel OS signs webhooks.
- **Faults are pulled.** The Hotel OS inbox calls
  `GET /api/integrations/hotel-os/v1/faults?property_code=…` with `X-Api-Key`; Smart Building
  answers with items in the inbox's severities (`Blocker`, `Today`, `Attention`). Nothing is pushed,
  so the inbox stays a read model and Smart Building needs no write access to the Hotel OS.
- **Mapping:** room code = unit name; one Hotel OS property code per Smart Building property.
- Credentials (`HOTEL_OS_URL`, `HOTEL_OS_USERNAME`, `HOTEL_OS_PASSWORD`, `HOTEL_OS_WEBHOOK_TOKEN`,
  `HOTEL_OS_INBOX_KEY`) are Railway variables only.
- Module `integration` depends on every other module; nothing depends on it.

## Consequences
+ Either side can be down; the next sync or inbox refresh catches up.
+ The Hotel OS needs only a webhook subscription and one more source in its inbox.
− Occupancy lags by one sync when a webhook is lost; the manual sync is the fallback (a periodic
  sync can follow).
− Units must be named like rooms; a mapping table can follow if a hotel needs it.
