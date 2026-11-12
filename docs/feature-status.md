# Feature status

**As of 2026-11-12: SB0 is done — green in CI, deployed on Railway, and used there: a tenant, a
property and two devices registered, the smoke detector shown as read only.**

## 1. Snapshot

| Stage | Tasks done / total | State |
|---|---|---|
| SB0 — Foundation | 7 / 7 | Done and verified on the deployed app. |
| SB1 — Device model, templates, twin, room simulator | 4 / 5 | Backend green in CI (b69fa6b); frontend pushed. |
| SB2 — Edge gateway against the simulator | 0 | Open |
| SB3 — Coupling with the Hotel OS | 0 | Open |
| SB4 — Energy | 0 | Open |

Counts: 30 endpoints · 10 tables · 46 backend tests (+1 migration drift) · 37 frontend tests.

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
| Frontend: Haus tabs Zimmer / Raumtypen / Geräte, rollout, room tiles, simulator | Frontend | In progress | SB1·4 | Pushed; CI and deployed app not checked yet. |
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
