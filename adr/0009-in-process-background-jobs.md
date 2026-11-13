# ADR-0009: Background jobs inside the API process, one runner at a time

Status: Accepted (2026-11-13). SB5. Same shape as pms-clone's in-process outbox worker.

## Context
Occupancy should follow the Hotel OS even when no webhook arrives (pms-clone does not send one yet,
hub b57) and nobody presses "Jetzt abgleichen". Railway runs one service; a second service only for
a timer would double the operating cost of the prototype.

## Decision
- The FastAPI lifespan starts an `asyncio` task that wakes every minute and runs the jobs that are
  due. Today one job: sync every enabled Hotel OS link whose last sync is older than
  `HOTEL_OS_SYNC_MINUTES` (default 10). Gated by `RUN_JOBS` (default `true`); tests switch it off.
- Each run takes a Postgres advisory lock (`pg_try_advisory_lock`), so with several replicas only
  one runs a job; the others skip that minute.
- Each property is synced in its own transaction; a failure is stored on its link
  (`last_sync_error`) and does not stop the others.
- Without the `HOTEL_OS_*` variables the job does nothing.

## Consequences
+ No extra service, no external scheduler.
+ A lost webhook costs at most one interval.
− Jobs share the API's event loop; a slow Hotel OS slows nothing else because calls are async, but
  a CPU-heavy job would. Move jobs to their own service when one becomes heavy.
