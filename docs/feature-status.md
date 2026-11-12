# Feature status

**As of 2026-11-12: SB0 is built and passes its checks in an agent sandbox; it is not yet pushed,
so there is no Actions run and no deployment.** Push access for the repository is missing.

## 1. Snapshot

| Stage | Tasks done / total | State |
|---|---|---|
| SB0 — Foundation | 6 / 7 | Code complete. Unverified in CI; Railway not set up. |
| SB1 — Device model, templates, twin, room simulator | 0 | Open |
| SB2 — Edge gateway against the simulator | 0 | Open |
| SB3 — Coupling with the Hotel OS | 0 | Open |
| SB4 — Energy | 0 | Open |

Counts: 18 endpoints · 6 tables · 29 backend tests (+1 migration drift) · 4 frontend tests.

## 2. Features

Status: `Open` · `In progress` · `Done` (green in CI) · `Verified` (green and seen on the
deployed app) · `Unverified` (built, checks passed only outside CI).

| Feature | Area | Status | Plan·Task | Notes |
|---|---|---|---|---|
| Health check, JSON 404 under `/api` | Platform | Unverified | SB0·2 | |
| Settings: URL normalisation, production secret guard | Platform | Unverified | SB0·2 | |
| Login, current user, login rate limit | Platform | Unverified | SB0·3 | Roles `admin`, `operator`. |
| Tenants (Mandanten) | Platform | Unverified | SB0·4 | Admins create; operators see their own. |
| Properties (Häuser) | Estate | Unverified | SB0·4 | Unique code, time zone checked, tenant-scoped reads. |
| Gateways in the registry | Devices | Unverified | SB0·5 | Status `provisioned` until SB2 reports. |
| Device registry with catalogue and filters | Devices | Unverified | SB0·5 | Kinds, protocols, location, retire instead of delete. |
| Safety devices read only | Devices | Unverified | SB0·5 | ADR-0003. |
| Frontend: login, Häuser, Geräteregister | Frontend | Unverified | SB0·6 | |
| CI workflow, Dockerfile | Delivery | Unverified | SB0·7 | Image not built yet anywhere. |
| Railway deployment | Delivery | Open | SB0·7 | Human steps in deployment.md. |

## 3. Changelog

- 2026-11-12 — SB0 written: repository, working agreement, CI, image, login, tenants,
  properties, device registry, frontend. Sandbox: backend 29 + 1 passed, Black/isort clean,
  frontend lint, 4 tests and build passed. Image build not run (no Docker daemon in the sandbox).
