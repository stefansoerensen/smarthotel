# Deployment

The application is deployed to Railway from GitHub. Every deploy is gated on a green CI run on
`main`. Nothing is built, run or tested on a developer machine.

## Topology

Two Railway services in one project:

| Service | What it is |
|---|---|
| `Postgres` | Railway managed PostgreSQL 16 |
| `app` | the repository `Dockerfile`: FastAPI + the built frontend |

`app` talks to `Postgres` over the project's private network (`postgres.railway.internal`), so the
traffic is not billed as egress.

## One-time setup in the Railway dashboard

These steps are performed by a human in the browser; there is no infrastructure-as-code.

1. **Create the project.** Railway → *New Project* → *Empty Project*. Name it `smarthotel`.
2. **Add the database.** *New* → *Database* → *Add PostgreSQL*. Wait until it is healthy.
3. **Add the application service.** *New* → *GitHub Repo* → `stefansoerensen/smarthotel`, branch
   `main`. Railway detects the root `Dockerfile` and builds it; no Nixpacks configuration is needed.
4. **Set the variables** on the `app` service (*Variables* tab). `DATABASE_URL` is added with
   *New Variable* → *Add Reference* → the Postgres service's `DATABASE_URL`, which resolves to the
   internal hostname.

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | reference to the Postgres service (internal hostname) |
   | `ENVIRONMENT` | `production` |
   | `JWT_SECRET` | a fresh random string, at least 32 characters (`openssl rand -hex 32`) |
   | `ADMIN_USERNAME` | the real administrator's login name |
   | `ADMIN_PASSWORD` | a strong password for that account |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (optional; this is the default) |
   | `CORS_ORIGINS` | leave unset — the deployment is same-origin |

   The application rewrites `DATABASE_URL` from `postgresql://…` to `postgresql+asyncpg://…` and
   drops a `sslmode` parameter, so the reference value can be used unchanged. Startup fails with a
   clear message if `JWT_SECRET` is missing, shorter than 32 characters, or a known development
   value.
5. **Pre-deploy command** (*Settings* → *Deploy* → *Pre-deploy Command*):
   ```
   sh -lc 'python -m alembic upgrade head && python -m app.seed.bootstrap'
   ```
   The `sh -lc` wrapper is required. Without it the platform does not interpret `&&`: the first
   command runs, the second is skipped silently, and the release still succeeds — which is how a
   deployment ends up migrated but without an administrator account.
   It runs before the new container receives traffic. A failing migration aborts the deploy and the
   previous version keeps serving.
6. **Health check** (*Settings* → *Deploy*): path `/api/health`, timeout 30 s. The endpoint also
   executes `SELECT 1`, so it fails when the database is unreachable.
7. **Wait for CI** (*Settings* → *Source* → *Wait for CI*): enable it. Railway then deploys a commit
   only after all GitHub checks for it are green.
8. **Generate a public domain** (*Settings* → *Networking* → *Generate Domain*). Railway injects
   `PORT`; the start command is `exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` and
   is baked into the image.
9. **Replicas**: one. The login rate limiter is per process.
10. **Region**: put `app` and `Postgres` in the same region (lesson from pms-clone, hub b52).

## Demo data

There is no demo seed yet; SB1 brings the room simulator and generated demo properties.

## Generating a migration

Model changes need an Alembic revision in the same commit. Write it by hand or generate it against
a throwaway database; the `backend` job's *Migration drift* step proves it matches the models.

## Operating

- Logs and metrics: the Railway dashboard, or `railway logs --service app`.
- Database backups: Railway's managed Postgres backups. **Verify the retention offered by the active
  plan before this deployment holds anything that matters** — no independent dump is taken.
- Expected cost for two always-on services is roughly $8–12 per month (RAM $10/GB, vCPU $20/vCPU,
  volume $0.15/GB).
- There is no staging environment: `main` is production.
- **A forgotten administrator password** takes three steps, because bootstrap only *creates* a
  missing administrator and never resets an existing one. Dev users do not exist in production, so
  there is no second way in.
  1. Set the new `ADMIN_PASSWORD` on the `app` service.
  2. Delete the row: `railway connect Postgres`, then
     `DELETE FROM smarthotel.users WHERE username = '<ADMIN_USERNAME>';`
  3. Recreate it: `railway run --service app python -m app.seed.bootstrap`.
- Nothing is ever patched inside a running container. Runtime problems are diagnosed from the logs
  and fixed by another push.

## Edge gateway (optional, simulated rooms)

The edge gateway is a second image (`edge/Dockerfile`). To watch a property run on its gateway:

1. In the app: Haus → Geräte → register a gateway, then "Token erzeugen" (shown once).
2. Raumtypen → Ausrollen with that gateway selected.
3. Railway: *New* → *GitHub Repo* → same repository, **Root Directory** `edge`, variables
   `EDGE_CLOUD_URL` (the app's public URL), `EDGE_TOKEN`, optionally `EDGE_SIM_MINUTES_PER_TICK=5`
   to make simulated time run faster, and a volume mounted at `/data` for the buffer.
4. The gateway appears as "online" within one tick; readings arrive in the Zimmer tab.

Without a volume the buffer is lost on redeploy — acceptable for the simulator, not for a hotel.

## Hotel OS coupling (ADR-0007)

Variables on the `app` service:

| Variable | Value |
|---|---|
| `HOTEL_OS_URL` | Public URL of the pms-clone app |
| `HOTEL_OS_USERNAME`, `HOTEL_OS_PASSWORD` | A service user in pms-clone that may read properties and reservations |
| `HOTEL_OS_WEBHOOK_TOKEN` | A fresh random string (`openssl rand -hex 24`) |
| `HOTEL_OS_INBOX_KEY` | Another fresh random string; pms-clone sends it as `X-Api-Key` |

In pms-clone: a webhook subscription to
`https://<smarthotel app>/api/integrations/hotel-os/webhook?token=<HOTEL_OS_WEBHOOK_TOKEN>` with topic
`Reservation`, and the inbox source calling
`https://<smarthotel app>/api/integrations/hotel-os/v1/faults?property_code=<code>` with the key.
In Smart Building: Haus → Hotel OS → Hauscode of the pms-clone property → Speichern → Jetzt abgleichen.
