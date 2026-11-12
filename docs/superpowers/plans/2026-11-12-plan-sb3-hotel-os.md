# Smart Building — Plan SB3: Coupling with the Hotel OS

> Steps use checkbox (`- [ ]`) syntax. Tick them in the same commit as the work.

**Goal:** Occupancy from the Hotel OS (pms-clone) sets each room's mode — eco when vacant, preheat on
the day of arrival, comfort while the guest is in house — and building faults (room too cold, gateway
offline, device fault) appear in the Hotel OS inbox.

**Hub:** b29 (SB3), d12, ADR-0007 (contract). The pms-clone side is built by the pms-clone session
(hub task); this repository builds and documents its side and the contract.

## Contract (ADR-0007, `contracts/hotel-os-v1/`)

1. **Occupancy, pull with a push trigger.** Smart Building reads reservations through the Hotel OS
   native API with a service user: `InHouse`, and `Confirmed` arriving today. A Hotel OS webhook on
   topic `Reservation` (any type) triggers a sync for that property; a manual "Jetzt abgleichen" does
   the same. The webhook body is the Hotel OS's standard webhook payload; the URL carries a shared
   secret (`?token=`), because the Hotel OS does not sign webhooks.
2. **Faults, pulled by the Hotel OS.** `GET /api/integrations/hotel-os/v1/faults?property_code=<Hotel
   OS property code>` with header `X-Api-Key`. Items carry `kind`, `severity` (`Blocker`, `Today`,
   `Attention` — the inbox's own levels), `message`, `unit_name` and `since`.
3. **Mapping:** a Smart Building room matches a Hotel OS unit by name (`101` = `101`). A property is
   linked to one Hotel OS property code.

## Tasks

### Task 1: Link and occupancy sync
- [x] Tests (fake Hotel OS): in-house guest → comfort and set point 21; arrival today → preheat 21;
  everyone else → eco 17; a room behind a gateway gets a command instead of a direct value; a mode
  change emits `room/mode_changed`; units without a room are reported; nothing changes on a second
  sync; manual set point changes are kept until the next mode change.
- [x] `hotel_os_links`, room `occupancy`/`mode`, `services/integration/occupancy.py`,
  HTTP client, `/api/properties/{code}/hotel-os` (get, put, sync).

### Task 2: Webhook
- [x] Tests: wrong token 401; a `Reservation` event for a linked property syncs it; other topics and
  unknown properties are ignored with 200.

### Task 3: Faults
- [x] Tests: occupied or arriving room 2 K below its set point → `Today`; gateway offline → `Today`;
  device fault → `Attention`; the service endpoint needs the API key and the Hotel OS property code.

### Task 4: Frontend
- [x] Haus tab "Hotel OS": link (Hotel OS Hauscode, Komfort/Eco Sollwert, aktiv), Abgleich, Störungen.
- [x] Room tiles show occupancy and mode.

### Task 5: Verification
- [ ] Green CI; on Railway the faults endpoint answers 401 without key. Linking a real pms-clone
  deployment needs the Railway variables and the pms-clone side (hub task).
