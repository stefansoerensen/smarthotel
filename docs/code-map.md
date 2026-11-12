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
| POST | `/properties/{code}/simulator/rooms/{room}` | signed in (scoped); window, presence |

## Tables (schema `smarthotel`)

`users`, `tenants`, `outbox_events`, `properties`, `gateways` (unique property+code),
`devices` (unique property+code), `room_types`, `room_type_points`, `rooms`, `room_points`.

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
| `utils/codes.ts` | Code suggestions (`suggestCode`, `suggestDeviceCode`) |
| `pages/LoginPage.tsx` | Anmeldung |
| `pages/PropertiesPage.tsx` | Häuser; Mandant und Haus anlegen (admin) |
| `pages/PropertyPage.tsx` | Haus (bearbeiten für Admins) with tabs Zimmer, Raumtypen, Geräte (`?tab=`) |
