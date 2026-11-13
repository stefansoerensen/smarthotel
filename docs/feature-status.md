# Feature status

**As of 2026-11-12: SB0–SB4 are built, green in CI and deployed on Railway (05cd509). On Railway
every new endpoint was checked read only (no data created by the agent). Open: a rollout and a
simulator run on Railway (needs a person, writes data), the pms-clone side of the coupling (hub
b57), Railway variables for the coupling and an edge container (hub b58).**

## 1. Snapshot

| Stage | Tasks done / total | State |
|---|---|---|
| SB0 — Foundation | 7 / 7 | Done and verified on the deployed app. |
| SB1 — Device model, templates, twin, room simulator | 4 / 5 | Green in CI, deployed. Rollout on Railway still to be done once by Stefan. |
| SB2 — Edge gateway against the simulator | 4 / 4 | Green in CI, deployed; edge API answers 401 without token. No gateway container runs yet (b58). |
| SB3 — Coupling with the Hotel OS | 5 / 5 | Green in CI, deployed; webhook and inbox endpoint answer 401 without secret. Not linked to pms-clone yet (b57, b58). |
| SB4 — Energy | 5 / 5 | Green in CI (05cd509), deployed; energy endpoints answer on Railway. |

Counts: 46 endpoints · 14 tables · 71 backend tests (+2 migration) · 14 edge tests · 50 frontend tests.

## 2. Features

Status: `Open` · `In progress` · `Done` (green in CI) · `Verified` (green and seen on the
deployed app) · `Unverified` (built, checks passed only outside CI).

| Feature | Area | Status | Plan·Task | Notes |
|---|---|---|---|---|
| Health check, JSON 404 under `/api` | Platform | Verified | SB0·2 | |
| Settings: URL normalisation, production secret guard | Platform | Done | SB0·2 | |
| Login, current user, login rate limit | Platform | Verified | SB0·3 | Roles `admin`, `operator`. |
| Tenants (Mandanten) | Platform | Verified | SB0·4 | Admins create; operators see their own. |
| Properties (Häuser) | Estate | Verified | SB0·4 | Unique code, time zone checked, tenant-scoped reads. |
| Gateways in the registry | Devices | Done | SB0·5 | Status `provisioned` until SB2 reports. |
| Device registry with catalogue and filters | Devices | Verified | SB0·5 | Kinds, protocols, location, retire instead of delete. |
| Safety devices read only | Devices | Verified | SB0·5 | ADR-0003. |
| Frontend: login, Häuser, Geräteregister | Frontend | Verified | SB0·6 | |
| Frontend: code suggestions for Mandant, Haus, Gerät | Frontend | Verified | SB0·6 | CI run 43260549510 green; 7cd6a54 deployed; tenant suggestion seen there (not submitted). |
| Frontend: device form — Art, Ort, Protokoll, Code; name is "<Art> <Ort>" | Frontend | Verified | SB0·6 | a4dee3e deployed and seen there. Bus address only through the API until the import in SB2. |
| Editing: rename Mandant, edit Haus (admin), edit and retire Geräte in the registry | Backend + Frontend | Verified | SB0·6 | 98c9f42 green and deployed; edit row and "Haus bearbeiten" seen there, nothing saved by the agent. Codes stay fixed. |
| Room types with standard points | Twin | Done | SB1·1 | CI green (b69fa6b). |
| Rollout, rooms, twin points, point writes | Twin | Done | SB1·2 | CI green (b69fa6b). |
| Room simulator | Twin | Done | SB1·3 | CI green (b69fa6b). |
| Frontend: Haus tabs Zimmer / Raumtypen / Geräte, rollout, room tiles, simulator | Frontend | Done | SB1·4 | CI green (710d84d), deployed; endpoints and UI seen on Railway (read only, nothing created by the agent). |
| Edge API: tokens, hello, readings, heartbeat, commands, ack | Edge | Done | SB2·1 | CI green (43c9ac0). |
| Edge gateway container (rules, buffer, commands, simulated bus) | Edge | Done | SB2·2 | CI green (43c9ac0). Not running anywhere yet. |
| Frontend: gateways, tokens, device health, pending set points, rollout behind a gateway | Frontend | Done | SB2·3 | CI green (43c9ac0). |
| Hotel OS link, occupancy sync, room modes and set points | Integration | Done | SB3·1 | CI green (461c90f). Needs Railway variables and a pms-clone service user. |
| Hotel OS webhook | Integration | Done | SB3·2 | CI green (461c90f). |
| Faults for the Hotel OS inbox | Integration | Done | SB3·3 | CI green (461c90f). pms-clone does not read it yet. |
| Frontend: Hotel OS tab, occupancy on room tiles | Frontend | Done | SB3·4 | CI green (461c90f). |
| Meter history, occupancy periods, energy per 15 min / day / night | Energy | Done | SB4·1–3 | CI green (05cd509), deployed. |
| Energy for the Hotel OS live P&L | Integration | Done | SB4·3 | CI green (05cd509), deployed. pms-clone does not read it yet. |
| Frontend: Energie tab, price per kWh | Frontend | Done | SB4·4 | CI green (05cd509), deployed. |
| Frontend: Mandant anlegen (admin) | Frontend | Done | SB0·6 | CI run 43259030276 green; 6d9d6fa deployed, form shown to the admin there. Not yet submitted. |
| CI workflow, Dockerfile | Delivery | Done | SB0·7 | Image built and smoke-tested in CI. |
| Railway deployment | Delivery | Verified | SB0·7 | Commit 39ab656 deployed; `/api/health` reports the database. |

## 3. Changelog

- 2026-11-12 — SB0 written: repository, working agreement, CI, image, login, tenants,
  properties, device registry, frontend. Sandbox: backend 29 + 1 passed, Black/isort clean,
  frontend lint, 4 tests and build passed. Image build not run (no Docker daemon in the sandbox).
- 2026-11-12 — CI: naming guard removed; the naming rule stays a writing rule (CLAUDE.md §6).
- 2026-11-12 — First push. Actions run 43251629132 green: backend 29 + 1 migration drift, frontend
  lint, 4 tests and build, image build and smoke.
- 2026-11-12 — Railway: 39ab656 deployed. Checked on the app: health ok with database, unknown
  `/api` path JSON 404, `/api/auth/me` and `/api/properties` 401 without token, wrong login 401
  with `auth.invalid_credentials`, `/properties` serves the SPA, login page renders.
- 2026-11-12 — Frontend: tenant form on the Häuser page for admins; the property form appears
  once a tenant exists.
- 2026-11-12 — Frontend: codes are suggested from the name (Mandant, Haus) or from location and
  kind (Gerät), umlauts spelled out, `-2`, `-3` … against codes already listed; editable.
- 2026-11-12 — Frontend: device form reordered (Art, Ort, Protokoll, then Name, Code, Busadresse);
  name suggested as "<Art> <Ort>"; "Adresse" renamed "Busadresse (optional)" with a format hint
  per protocol (640485c).
- 2026-11-12 — Frontend: device form reduced to Art, Ort ("Zimmernummer, Flur o. ä."), Protokoll and
  Code; the name is always "<Art> <Ort>"; no address fields, the postal address belongs to the Haus
  and the bus address comes with the import from the building (SB2).
- 2026-11-12 — SB0 accepted on the deployed app: tenant, property and two devices registered by
  Stefan; the smoke detector shows "nur lesen". Device names typed before a4dee3e keep their
  free-text names.
- 2026-11-12 — Editing: `PATCH /api/tenants/{code}` (rename, admin); Häuser page lists Mandanten
  with Umbenennen; Haus page has "Haus bearbeiten" (name, street, postcode, city) for admins;
  each device row can be edited (Art, Ort, Protokoll; name follows "Art Ort") and taken out of
  service after a confirmation. Codes cannot be changed.
- 2026-11-12 — SB1 backend: room types, rollout, twin, simulator; ADR-0005.
- 2026-11-12 — SB1 frontend: Haus page tabs; Raumtypen with points and rollout ("101-120, 201-210");
  Zimmer tiles with temperature, set point ±0.5, window and presence toggles, valve, heat meter;
  simulator +15 min / +1 h with outdoor temperature. Catalogue kinds now carry `writable`.
- 2026-11-12 — SB2: edge API, gateway container, frontend for gateways; migration 0003 with a
  server default for device health so existing devices on Railway migrate.
- 2026-11-12 — SB3: Hotel OS link, occupancy sync, webhook, faults endpoint, Hotel OS tab;
  ADR-0007 and `contracts/hotel-os-v1/`. Presence toggle relabelled anwesend/abwesend.
- 2026-11-12 — SB4: meter history, occupancy periods, energy series and nights, Hotel OS energy
  endpoint, Energie tab; ADR-0008.
- 2026-11-12 — Railway (05cd509): health, gateways, commands, hotel-os, faults, energy, nights answer
  200; `/edge/v1/hello`, webhook and inbox faults answer 401 without secret; unknown `/edge` path is JSON
  404; the new tabs are in the served bundle.
- 2026-11-13 — Edge on Railway crashed (reported by Stefan). Fixed: no `VOLUME` in the Dockerfile
  (Railway refuses it); runs as root so a Railway volume at /data is writable, with a fallback to a
  temporary buffer; missing variables are named; a refused token or request is logged and retried
  instead of ending the process; `edge/railway.json`. The actual Railway log was not seen; unverified
  until the service runs.
