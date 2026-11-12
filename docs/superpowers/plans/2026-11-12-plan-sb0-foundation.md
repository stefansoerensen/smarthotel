# Smart Building — Plan SB0: Foundation

> Steps use checkbox (`- [ ]`) syntax for tracking. Tick them in the same commit as the work.

**Goal:** A repository that can carry the Smart Building strand: working agreement, CI as the only
test loop, a Railway-deployable image, and the first slice of the cloud control plane — login,
tenant (Mandant), property (Haus) and a device registry.

**Hub:** b29 (stages SB0–SB4), d12 (safety systems are read only), d19/d36 (build only, accept
against simulators), d34 (own edge build on open protocol libraries), d35 (stack as pms-clone).

**Architecture:** Modular monolith in `backend/app/` with three modules for now:

```
platform → (nothing)                 users, login, tenants, domain events + outbox table
estate   → platform                  properties
devices  → estate, platform          gateways, devices (the registry)
```

`backend/tests/architecture/test_module_boundaries.py` enforces the direction. Edge code arrives
in SB2 under `edge/` as its own Python container and never imports `backend/`.

**Tech stack:** Python 3.11, FastAPI, SQLAlchemy 2 async + asyncpg, Pydantic v2, Alembic,
PostgreSQL 16; React 18, TypeScript strict, Vite, Tailwind, Vitest; GitHub Actions; Railway.

## Global constraints

- Every task ends green in CI on `main`; Conventional Commits with a scope.
- Test first. The verification step of every task is the Actions run for its push.
- Services never commit; the route handler does. Events are emitted inside the transaction
  that changed the data (`services/platform/events.emit`), into the `outbox_events` table.
- Every table lives in schema `smarthotel`: plural snake_case, UUID `id`, `created_at`/`updated_at`.
- Native API: `/api`, snake_case JSON, lists `{"items": [...], "total": n}` with `skip`/`limit`,
  errors `{"detail", "code", "details"}`, Bearer JWT.
- **Safety systems are read only (d12).** A device whose kind belongs to fire protection or
  life safety is registered with `controllable = false`, and the API refuses to change that.
- The reference PMS whose API pms-clone mirrors is never named in this repository.
- Nothing goes into hotel operation (d19). Demo data is generated and never seeded automatically.

---

### Task 1: Repository hygiene, working agreement, documentation skeleton

- [x] `.gitignore`, `.gitattributes`, `.dockerignore`, `.claude/settings.json`
- [x] `CLAUDE.md` (working agreement), `README.md`
- [x] `docs/README.md`, `docs/architecture.md`, `docs/code-map.md`, `docs/feature-status.md`,
  `docs/deployment.md`
- [x] ADR-0001 modular monolith + outbox, ADR-0002 deploy GitHub → Railway with CI as the only
  test loop, ADR-0003 safety systems are read only, ADR-0004 edge gateway as its own container

### Task 2: Backend core and health

- [x] Test: `GET /api/health` answers `{"status": "ok", "database": "ok"}`; unknown `/api/…`
  returns JSON 404
- [x] Test: settings normalise `postgresql://` URLs and refuse a weak `JWT_SECRET` in production
- [x] `app/core/{config,database,clock,errors,security}.py`, `app/api/{deps,errors}.py`, `app/main.py`
- [x] Alembic (async, schema-aware), `tests/migrations/test_migrations.py` (drift check)
- [x] `tests/architecture/test_module_boundaries.py`

### Task 3: Users and login

- [x] Test: `POST /api/auth/login` returns a token for valid credentials, 401 otherwise;
  `GET /api/auth/me` returns the user; ten failed logins a minute are rate limited
- [x] Model `users` (username, password hash, role `admin|operator`, optional `tenant_id`, active)
- [x] Bootstrap: administrator from `ADMIN_USERNAME`/`ADMIN_PASSWORD`; dev users only outside
  production

### Task 4: Tenants and properties (Mandant und Haus)

- [x] Test: admin creates a tenant and a property; codes are unique; an operator sees only the
  properties of their own tenant and cannot create tenants
- [x] Models `tenants` (platform), `properties` (estate) (code, name, time zone, address); events
  `tenant.created`, `property.created`, `property.changed`
- [x] `/api/tenants`, `/api/properties` (list, get, create, patch)

### Task 5: Device registry

- [x] Test: register a gateway and devices in a property; device codes are unique per property;
  a `fire_alarm`/`smoke_detector`/`emergency_light`/`sprinkler`/`evacuation` device is always
  `controllable = false` and a patch that sets it to `true` is rejected with
  `device.safety_read_only`; filter devices by kind, gateway and location
- [x] Models `gateways` (property, code, name, status, last_seen_at) and `devices` (property,
  optional gateway, code, name, kind, protocol, address, location, controllable, status)
- [x] Events `gateway.registered`, `device.registered`, `device.changed`, `device.retired`
- [x] `/api/properties/{code}/gateways`, `/api/properties/{code}/devices`

### Task 6: Frontend — login, properties, device registry

- [x] Login page, protected routes, token in Zustand
- [x] Properties page (list + create for admins), property page with the device registry
  (filter by kind, register a device, safety devices marked "read only")
- [x] Vitest component tests for login and the registry

### Task 7: Delivery pipeline

- [x] `.github/workflows/ci.yml`: backend (Black, isort, pytest, migration drift),
  frontend (ESLint, Vitest, build), image (build + smoke)
- [x] Multi-stage `Dockerfile` (Node builds the frontend, Python serves API + static build)
- [ ] Railway project with Postgres and the app service; pre-deploy
  `sh -lc 'python -m alembic upgrade head && python -m app.seed.bootstrap'` — **human step**
  (see `docs/deployment.md`)
- [ ] First green Actions run on `main` (done: run 43251629132) and the login checked on the
  deployed app

## Done when

All checkboxes are ticked, the Actions run is green and the device registry was used once on the
deployed app.
