# Smart Building — Plan SB1: Device model, room templates, digital twin, room simulator

> Steps use checkbox (`- [ ]`) syntax. Tick them in the same commit as the work.

**Goal:** A property can define room types (templates of data points), roll a room type out to many
rooms in one step — creating the rooms, their devices and their twin — and watch the rooms behave in
a deterministic simulator: heating towards the set point, cooling with an open window.

**Hub:** b29 (SB1), d12 (safety read only; deterministic before generative), d19/d36 (simulators only).

**New module:** `twin → devices, estate, platform` (ADR-0005).

## Data model (schema `smarthotel`)

| Table | Holds |
|---|---|
| `room_types` | property, code, name, description — the template |
| `room_type_points` | room type, key (`temperature`, `setpoint`, …), label, device kind, protocol, unit, writable, position |
| `rooms` | property, code (`101`), name, floor, room type, status — one digital twin each |
| `room_points` | room, key, label, kind, unit, writable, device, value, value_at, source |

A point is **writable** only if its kind can be controlled; sensor and safety kinds are always read
only (`twin.point_read_only`). Values are floats (booleans as 0/1). Value changes emit no events;
room types and rooms do.

## Standard room type

`temperature` (temperature_sensor, °C), `setpoint` (thermostat, °C, writable), `window`
(window_contact), `presence` (presence_sensor), `valve` (valve, %, writable), `light` (light,
writable), `heat_meter` (meter, kWh). A room type may start from it and add or drop points.

## Tasks

### Task 1: Room types
- [x] Tests: create a room type with the standard points or empty; add and remove a point; a point of
  a sensor or safety kind cannot be writable; codes unique per property; tenant scoping applies.
- [x] Models, Alembic revision, `services/twin/templates.py`, API under
  `/api/properties/{code}/room-types`.

### Task 2: Rooms, twin and rollout
- [x] Tests: rolling out a room type to `101`–`105` creates five rooms, one device per point
  (code `<room>-<KEY>`, location = room, name `<Label> <room>`), and a twin point per device;
  running it again changes nothing; a room of another type is reported, not changed; at most 500
  rooms per call; writing a writable point stores the value, writing a read-only point fails.
- [x] `services/twin/rooms.py`, `/api/properties/{code}/rooms`, `/rollout`,
  `PUT /rooms/{room}/points/{key}`.

### Task 3: Room simulator
- [x] Tests (pure function): heating with the valve open raises the temperature; an open window
  closes the valve and the room cools towards outside; the heat meter counts only while heating;
  the same inputs give the same outputs.
- [x] `services/twin/simulator.py`; `POST /api/properties/{code}/simulator/step` (minutes, outdoor
  temperature) and `POST /api/properties/{code}/simulator/rooms/{room}` (window, presence).

### Task 4: Frontend
- [x] Haus page with tabs **Zimmer**, **Raumtypen**, **Geräte**.
- [x] Raumtypen: create (with standard points), add/remove points, roll out to "101-120, 201-210".
- [x] Zimmer: one tile per room with temperature, set point (±0.5), window, presence, valve;
  simulator buttons "+15 min" and "+1 h"; window and presence toggles.
- [x] Vitest for rollout parsing, rollout form and the room tile.

### Task 5: Verification
- [ ] Green CI; on Railway: a room type rolled out to a handful of rooms and simulated once.
