# CLAUDE.md — Smart Building

Working agreement for this repository. Read it before changing anything.

## 1. What this project is

The **Smart Building** strand of chAIn: a control plane that makes the building technology of a
hotel — room climate, windows, presence, light, meters, locks, and read-only views of safety
systems — manageable like home automation, for many rooms across many properties. It aggregates
device data and exchanges it with the Hotel OS (the sibling repository `pms-clone`) so occupancy
can drive rooms and faults reach the front desk.

Two runtimes, one repository:

- **Cloud control plane** (`backend/`, `frontend/`): registry, templates, digital twin, rules,
  energy data, API. Deployed to Railway like `pms-clone`.
- **Edge gateway** (`edge/`, from SB2): one Python container per property that talks KNX, BACnet,
  Modbus and MQTT, runs local rules and buffers during outages. Until real hardware is allowed
  (after hub b32/a16/b08), it runs against simulators only.

It is a prototype (hub d19/d36): built and accepted against simulators and constructed test
cases. **Nothing here goes into hotel operation**, and nothing is tested live.

## 2. Where to look

| Question | File |
|---|---|
| Documentation index | [docs/README.md](docs/README.md) |
| Modules, request and event flow, edge/cloud split | [docs/architecture.md](docs/architecture.md) |
| Which file, endpoint or table holds what | [docs/code-map.md](docs/code-map.md) |
| What is implemented, in progress or not started | [docs/feature-status.md](docs/feature-status.md) |
| Railway services, variables, release steps | [docs/deployment.md](docs/deployment.md) |
| Stage plans (SB0 …) with checkboxes | [docs/superpowers/plans/](docs/superpowers/plans/) |
| Why a decision was made | [adr/](adr/) |

Product decisions, backlog and assumptions live in the **hilbert Hub**, not here. Hub IDs
(`b29`, `d34`, …) are quoted where a rule comes from there.

## 3. How we work

Tests run **only** in GitHub Actions (`.github/workflows/ci.yml`); the user interface is only
visible on the deployed Railway app; the database is only reachable from Railway.

1. Implement one plan task. Write the test first and see it fail for the right reason.
2. Commit (Conventional Commits with a scope) and push to `main` — work lands directly on `main`.
3. Read the Actions result for that push; if red, fix forward with another commit.
4. Railway deploys once CI is green and runs
   `python -m alembic upgrade head && python -m app.seed.bootstrap` before the new container takes
   traffic.
5. For user-visible work, check the behaviour on the deployed app.

Never claim a test passed, a build worked or a migration applied without a run that says so.
Before the run, the honest wording is "this should pass in CI". A sandbox run during an agent
session counts as a hint, not as the verification.

## 4. Architecture rules that must hold

Modular monolith with domain events and a transactional outbox. Modules and the allowed
dependency direction, enforced by `backend/tests/architecture/test_module_boundaries.py`:

```
platform → (nothing)            users, tenants, events/outbox
estate   → platform             properties (Häuser)
devices  → estate, platform     gateways, devices, device catalogue
```

- A module never imports another module's `models` at runtime and never queries its tables; it
  calls that module's services. Imports under `if TYPE_CHECKING:` are exempt.
- **Services never commit.** The route handler (or worker, or seed script) commits after a
  successful use case.
- **Events are emitted inside the transaction that changed the data**, via
  `services/platform/events.emit(...)`. Entity codes of property-owned things are
  `<property code>/<code>`.
- **Safety systems are read only (hub d12, ADR-0003).** Fire alarm, smoke detection, smoke
  extraction, sprinklers, emergency lighting and evacuation are seen, never controlled. The rule
  lives in `services/devices/catalogue.py` and `services/devices/registry.py`; no caller may
  override it, and no command path may ever reach such a device.
- **Deterministic before generative (d12).** Rules decide; agents may explain and propose.
- **Tenancy:** admins see everything; an operator sees only their tenant. A property of another
  tenant answers 404, not 403, so its existence does not leak.
- **No ORM `relationship()`s.** Reference by id and load explicitly.
- **Nothing is deleted** from the registry: devices are retired (`status = retired`).
- **Edge code never imports `backend/`** and the cloud never assumes the edge is reachable
  (ADR-0004). Commands carry an id and are acknowledged; state is reconciled, not replayed.
- Every table lives in schema `smarthotel`: plural snake_case, UUID `id`, `created_at`/`updated_at`.

## 5. Conventions

**Backend** — Python 3.11, FastAPI, SQLAlchemy 2.0 async with asyncpg, Pydantic v2, Alembic,
PostgreSQL 16. Full type hints, docstrings on public functions, `logging.getLogger(__name__)`.
Black + isort, line length 100. Native API: `/api`, snake_case JSON, lists
`{"items": [...], "total": n}` with `skip`/`limit` (default 0/50, max 500), errors
`{"detail", "code", "details"}`, Bearer JWT. A model change ships with its Alembic revision in the
same commit; `pytest -m migrations` checks they agree. Tests in
`backend/tests/{unit,integration,architecture,migrations}`; builders in `backend/tests/factories.py`.
Time comes from the injectable `Clock`; tests use `FixedClock(2026-11-12T08:00Z)`.

**Frontend** — React 18, TypeScript `strict` (never `any`), Vite, Tailwind, React Router 6,
Axios, Zustand, lucide-react, Vitest + Testing Library. All types in `src/types/index.ts`; HTTP
only through `src/services/api.ts` and the typed modules beside it; relative base path `/api`.
Colours: bone `#F4F2F0`, ink `#0C0A08`, burgundy `#7B1F4B`. UI text is German.

**Commits** — Conventional Commits with a scope: `feat(backend): …`, `feat(frontend): …`,
`ci: …`, `docs: …`.

## 6. Naming rule

The reference PMS whose API `pms-clone` mirrors is **never named in this repository** — not in
code, comments, docs, ADRs, commit messages or PR descriptions. Write "the Hotel OS" or "the
reference PMS API". CI greps the tree for the repository variable `FORBIDDEN_VENDOR_NAME` and
fails the build if it appears.

## 7. Secrets and data

Secrets (`JWT_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `DATABASE_URL`) exist only as Railway
variables. `backend/.env.example` documents every variable and is never read in production.
`JWT_SECRET` is at least 32 characters; startup fails in production otherwise. No development
users in production. Never commit real guest, staff or building data; demo data is generated
and never created automatically. Building plans, bus addresses and network details of the real
beta hotel stay out of the repository.

## 8. Keeping track

When a task is finished, in the **same commit** as the code: update `docs/feature-status.md`,
`docs/code-map.md` when files, endpoints or tables change, `docs/architecture.md` when a rule or
diagram stops being true, tick the plan checkboxes, and add an ADR for a decision a future reader
would otherwise have to reverse-engineer. Supersede an ADR instead of rewriting it. A stale
status file is worse than none: if you cannot tell whether something works, write that it is
unverified.

## 9. Definition of done

1. The test was written first and failed for the right reason.
2. The Actions run for the pushed commit is **green** and you have read it.
3. Any model change ships with its Alembic revision.
4. Status, code map, architecture and ADRs are updated in the same commit; plan boxes ticked.
5. For user-visible work: Railway deployed that commit and the behaviour was checked there.

Anything short of that is reported as in progress, naming what is missing.
