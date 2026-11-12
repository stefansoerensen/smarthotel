# Architecture

## Two runtimes

```
          Hotel OS (pms-clone)                      Railway
        ┌───────────────────────┐  webhooks / API  ┌──────────────────────────────┐
        │ reservations, inbox   │◀───────────────▶│ Smart Building control plane │
        └───────────────────────┘     (SB3)        │ FastAPI + React + Postgres   │
                                                   └──────────────▲───────────────┘
                                                                  │ MQTT/HTTPS, outbound
                                                                  │ from the building (SB2)
                                                   ┌──────────────┴───────────────┐
                                                   │ Edge gateway (one per Haus)  │
                                                   │ local rules, buffer, commands│
                                                   └──┬──────────┬──────────┬─────┘
                                                      │ KNX/IP   │ BACnet   │ Modbus
                                                   room automation, HVAC, meters
                                                   (simulators until b32/a16/b08)
```

- The **cloud** owns configuration: tenants, properties, the device registry, room-type templates
  and twins (SB1), rules, energy data (SB4). It is the only place users and the Hotel OS talk to.
- The **edge** owns the field buses and the safety of the room in an outage: local rules keep
  working without the cloud, readings are buffered and delivered later, commands are acknowledged.
  Connections always go out from the building; nothing on the hotel network is exposed (ADR-0004).

## Modules of the control plane

```
platform → (nothing)            users, tenants (Mandanten), events + outbox
estate   → platform             properties (Häuser)
devices  → estate, platform     gateways, devices, device catalogue
twin     → devices, estate, platform   room types, rooms, twin points, rollout, simulator
edge     → twin, devices, estate, platform   commands to gateways
integration → edge, twin, devices, estate, platform   Hotel OS link, occupancy sync, faults
```

Enforced by `backend/tests/architecture/test_module_boundaries.py`. Nothing depends on
`integration`. Planned addition: `energy` (SB4).

## Digital twin (SB1, ADR-0005)

A room type is a template of data points. Rolling it out to rooms creates, per room, one device in
the registry (`<room>-<KEY>`, location = room) and one twin point linked to it. Twin points hold the
last value, its time and its source (`manual`, `simulator`, later `edge`). Writable points are set
points, valves, lights and other actuators; sensors and safety kinds are read only. The simulator
(`services/twin/simulator.py`) is a pure function advanced by `POST …/simulator/step`.

## Request flow

Route handler → service functions (never commit) → `session.commit()` in the handler. Services
raise `DomainError`/`NotFoundError`/`ConflictError`/`AuthError`; `api/errors.py` maps them to
`{"detail", "code", "details"}`.

Tenancy: `api/deps.get_scoped_property` loads the property in the path with the user's tenant
scope; an operator asking for another tenant's property gets 404.

## Events

Every state change emits an event into `outbox_events` in the same transaction:

| Topic | Types | Entity code |
|---|---|---|
| `tenant` | `created`, `changed` | tenant code |
| `property` | `created`, `changed` | property code |
| `gateway` | `registered` | `<property>/<gateway>` |
| `device` | `registered`, `changed`, `retired` | `<property>/<device>` |
| `room_type` | `created`, `changed` | `<property>/<room type>` |
| `room` | `created`, `mode_changed` | `<property>/<room>` |

SB0 records events only. A worker delivering them (webhooks, the Hotel OS) arrives with SB3.

## Safety systems

Device kinds of fire protection and life safety (`fire_alarm`, `smoke_detector`,
`smoke_extraction`, `sprinkler`, `emergency_light`, `evacuation`) are always registered with
`controllable = false`. Registering or patching them as controllable fails with
`device.safety_read_only`; changing a device's kind to a safety kind drops control. ADR-0003.

## Edge gateway (SB2, ADR-0004, ADR-0006)

```
gateway (edge/)                                    control plane (/edge/v1, gateway token)
  every tick:                                         hello      → devices, rooms, points
    bus.advance → rules (controller, window, frost)   readings   → twin points, newer only
    read devices → SQLite buffer                      heartbeat  → gateway online, device health
    flush buffer ─────────────────────────────────▶   commands   → pending, handed out once
    heartbeat, commands, ack ◀──────────────────────  ack        → done / failed / refused
```

- A write to a point whose device sits behind a gateway becomes a **command** and a **desired**
  value; the reading that confirms it clears the desired value.
- Rooms behind a gateway are not advanced by the cloud simulator and their window/presence cannot
  be toggled there; the edge owns them.
- Commands exist only for controllable devices; the gateway refuses others again (ADR-0003).
- Gateway status: `provisioned` before the first heartbeat, then `online` / `offline` (no contact for
  two minutes).

## Hotel OS coupling (SB3, ADR-0007)

```
Hotel OS (pms-clone)                         Smart Building
  webhook Reservation ──── ?token= ─────▶   sync property: read InHouse + arrivals today
  GET /api/reservations ◀─── service user    → room occupancy (vacant / arriving / occupied)
                                             → mode (eco / preheat / comfort) → set point on change
  inbox ──── X-Api-Key ─────────────────▶   GET /api/integrations/hotel-os/v1/faults
```

A mode change emits `room/mode_changed` and writes the mode's set point (a command behind a
gateway). Faults: occupied or arriving room 2 K below its set point (`Today`), gateway offline
(`Today`), device fault (`Attention`).
