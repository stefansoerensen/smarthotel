# Code map

## Backend (`backend/app/`)

| Path | What |
|---|---|
| `main.py` | App factory, `/api/health`, JSON 404 for unknown `/api` paths, static SPA serving |
| `core/config.py` | Settings, `DATABASE_URL` normalisation, production `JWT_SECRET` guard |
| `core/database.py` | `Base` (schema `smarthotel`), `TimestampMixin`, engine, `SessionLocal` |
| `core/clock.py` | `Clock`, `SystemClock`, `FixedClock` |
| `core/errors.py` | `DomainError`, `NotFoundError`, `ConflictError`, `AuthError` |
| `core/security.py` | bcrypt, JWT |
| `core/query.py` | `paginate` |
| `core/ratelimit.py` | Login rate limiter |
| `api/deps.py` | `get_db`, `get_clock`, `get_current_user`, `require_admin`, `tenant_scope`, `get_scoped_property` |
| `api/errors.py` | Error → JSON mapping |
| `api/native/auth.py` | Login, me |
| `api/native/estate.py` | Tenants, properties |
| `api/native/devices.py` | Catalogue, gateways, devices |
| `models/platform/` | `users`, `tenants`, `outbox_events` |
| `models/estate/` | `properties` |
| `models/devices/` | `gateways`, `devices` |
| `services/platform/` | `users`, `tenants` (create, rename, list), `events.emit` |
| `services/estate/properties.py` | Create, get (tenant-scoped), list, update |
| `services/devices/catalogue.py` | Device kinds, safety kinds, protocols |
| `services/devices/registry.py` | Gateways and devices: register, find, list, update, retire |
| `models/twin/` | `room_types`, `room_type_points`, `rooms`, `room_points` |
| `services/twin/templates.py` | Room types, standard points, add/remove points |
| `services/twin/rooms.py` | Rooms, rollout, point writes, simulator applied to rooms |
| `services/twin/simulator.py` | Pure room simulator with a proportional controller |
| `api/native/twin.py` | Room types, rooms, rollout, simulator endpoints |
| `alembic/versions/0002_sb1_twin.py` | SB1 tables |
| `alembic/versions/0003_sb2_edge.py` | `commands`; gateway token hash; device health; desired values |
| `models/edge/command.py`, `services/edge/commands.py` | Commands: create, hand out, acknowledge |
| `api/edge/v1.py`, `schemas/edge.py` | Edge protocol v1 for gateways |
| `api/native/commands.py` | Commands of a property for operators |
| `alembic/versions/0004_sb3_hotel_os.py` | `hotel_os_links`; room occupancy and mode |
| `models/integration/hotel_os_link.py` | Link to the Hotel OS property, set points per mode |
| `services/integration/hotel_os.py` | `Stay`, `HttpHotelOs` client of the Hotel OS native API |
| `services/integration/occupancy.py` | Link, occupancy by unit, sync → room modes and set points |
| `services/integration/faults.py` | Faults for the inbox |
| `api/native/hotel_os.py` | Link, sync, faults, webhook, inbox and energy endpoints for the Hotel OS |
| `alembic/versions/0005_sb4_energy.py` | `meter_readings`, `occupancy_periods`, energy price on the link |
| `models/twin/history.py` | `MeterReading`, `OccupancyPeriod` |
| `services/energy/aggregate.py` | Buckets, local days, nights, cost |
| `api/native/energy.py` | Energy series and nights |
| `seed/bootstrap.py` | Pre-deploy: administrator from env, dev users outside production |
| `alembic/versions/0001_sb0_foundation.py` | All SB0 tables |

## Endpoints (`/api`)

| Method | Path | Who |
|---|---|---|
| GET | `/health` | anyone |
| POST | `/auth/login` | anyone (rate limited) |
| GET | `/auth/me` | signed in |
| GET | `/tenants` | signed in (scoped) |
| POST | `/tenants` | admin |
| PATCH | `/tenants/{code}` | admin; renames, the code stays |
| GET | `/properties` | signed in (scoped) |
| POST | `/properties` | admin |
| GET | `/properties/{code}` | signed in (scoped) |
| PATCH | `/properties/{code}` | admin |
| GET | `/device-catalogue` | signed in |
| GET | `/properties/{code}/gateways` | signed in (scoped) |
| POST | `/properties/{code}/gateways` | signed in (scoped) |
| GET | `/properties/{code}/devices` | signed in (scoped); filters `kind`, `gateway_code`, `location`, `include_retired` |
| POST | `/properties/{code}/devices` | signed in (scoped) |
| GET | `/properties/{code}/devices/{device}` | signed in (scoped) |
| PATCH | `/properties/{code}/devices/{device}` | signed in (scoped) |
| DELETE | `/properties/{code}/devices/{device}` | signed in (scoped); retires, does not delete |
| GET, POST | `/properties/{code}/room-types` | signed in (scoped) |
| PATCH | `/properties/{code}/room-types/{type}` | signed in (scoped) |
| POST | `/properties/{code}/room-types/{type}/points` | signed in (scoped) |
| DELETE | `/properties/{code}/room-types/{type}/points/{key}` | signed in (scoped); template only |
| POST | `/properties/{code}/rollout` | signed in (scoped); ≤ 500 rooms |
| GET | `/properties/{code}/rooms`, `/rooms/{room}` | signed in (scoped) |
| PUT | `/properties/{code}/rooms/{room}/points/{key}` | signed in (scoped); writable points only |
| POST | `/properties/{code}/simulator/step` | signed in (scoped) |
| POST | `/properties/{code}/simulator/rooms/{room}` | signed in (scoped); window, presence; not for edge rooms |
| POST | `/properties/{code}/gateways/{gateway}/token` | signed in (scoped); new token, shown once |
| GET | `/properties/{code}/commands` | signed in (scoped) |
| POST | `/edge/v1/hello`, `/readings`, `/heartbeat` | gateway token |
| GET | `/edge/v1/commands` | gateway token; hands out pending commands once |
| GET, PUT | `/properties/{code}/hotel-os` | signed in (scoped) |
| POST | `/properties/{code}/hotel-os/sync` | signed in (scoped) |
| GET | `/properties/{code}/faults` | signed in (scoped) |
| POST | `/integrations/hotel-os/webhook?token=` | Hotel OS, shared secret |
| GET | `/integrations/hotel-os/v1/faults?property_code=` | Hotel OS inbox, `X-Api-Key` |
| GET | `/integrations/hotel-os/v1/energy?property_code=&date=` | Hotel OS live P&L, `X-Api-Key` |
| GET | `/properties/{code}/energy?from&to&resolution&room` | signed in (scoped) |
| GET | `/properties/{code}/energy/nights?from&to` | signed in (scoped) |
| POST | `/edge/v1/commands/{id}/ack` | gateway token |

## Tables (schema `smarthotel`)

`users`, `tenants`, `outbox_events`, `properties`, `gateways` (unique property+code),
`devices` (unique property+code), `room_types`, `room_type_points`, `rooms`, `room_points`, `commands`, `hotel_os_links`, `meter_readings`, `occupancy_periods`.

## Frontend (`frontend/src/`)

| Path | What |
|---|---|
| `types/index.ts` | All types |
| `services/api.ts` | Axios instance, error mapping, auth hooks |
| `services/{auth,estate,devices}.ts` | Typed API calls |
| `hooks/useAuthStore.ts` | Token and user (Zustand) |
| `components/Layout.tsx`, `components/Field.tsx` | Shell, form field |
| `components/DeviceRow.tsx` | Registry row with in-place edit and retire |
| `components/TenantItem.tsx` | Tenant with in-place rename |
| `components/DeviceRegistry.tsx` | Geräte tab: list, filter, register |
| `components/RoomTypesTab.tsx` | Raumtypen tab: templates, points, rollout |
| `components/RoomsTab.tsx`, `components/RoomTile.tsx` | Zimmer tab: twin tiles and simulator |
| `services/twin.ts` | Room types, rooms, rollout, simulator calls |
| `utils/rooms.ts` | `parseRoomCodes` for "101-120, 201" |
| `components/GatewaysPanel.tsx` | Gateways: status, register, token shown once |
| `components/HotelOsTab.tsx`, `services/hotelOs.ts` | Hotel OS tab: link, price, sync, faults |
| `components/EnergyTab.tsx`, `services/energy.ts` | Energie tab: totals, per night, bars per day |

## Edge (`edge/edge_gateway/`)

| Path | What |
|---|---|
| `config.py` | `EDGE_*` settings, scenario parsing |
| `bus.py` | Bus interface, `SimulatedBus` (room physics, scenario, faulty devices) |
| `rules.py` | Room controller, window open → heating off, frost protection |
| `buffer.py` | SQLite reading queue and stored configuration |
| `cloud.py` | `/edge/v1` client |
| `gateway.py` | One tick: bus, rules, buffer, sync, commands |
| `__main__.py` | `python -m edge_gateway` |

Contract examples: `contracts/edge-v1/`.
| `utils/codes.ts` | Code suggestions (`suggestCode`, `suggestDeviceCode`) |
| `pages/LoginPage.tsx` | Anmeldung |
| `pages/PropertiesPage.tsx` | Häuser; Mandant und Haus anlegen (admin) |
| `pages/PropertyPage.tsx` | Haus (bearbeiten für Admins) with tabs Zimmer, Raumtypen, Geräte (`?tab=`) |
