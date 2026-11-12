# Smart Building — Plan SB2: Edge gateway against the simulator

> Steps use checkbox (`- [ ]`) syntax. Tick them in the same commit as the work.

**Goal:** A gateway container per property that runs the rooms' local rules, survives network
outages, delivers buffered readings later, executes commands with acknowledgement and reports
device health — tested against a simulated bus, never against real hardware (b32/a16/b08 open).

**Hub:** b29 (SB2), d34 (own build on open libraries), d12 (safety read only), ADR-0003, ADR-0004.

## Cloud side (new module `edge → twin, devices, estate, platform`)

- Gateways get a provisioning token (stored as SHA-256 hash, shown once) and `last_seen_at`.
  Devices get `health` and `last_seen_at`.
- `commands`: one row per write to a point whose device sits behind a gateway — id, gateway,
  device, point key, value, status (`pending` → `sent` → `done`/`failed`/`refused`), timestamps.
  Commands are only created for controllable devices; the edge refuses others again.
- Twin points get `desired` / `desired_at`: a set point written for an edge room is desired until
  the edge reports the device's value. Rooms behind a gateway are not advanced by the cloud
  simulator; the edge owns them.
- Edge API `/edge/v1` with the gateway token: `hello`, `readings`, `heartbeat`, `commands`,
  `commands/{id}/ack`. Readings are applied when they are newer than the stored value
  (out-of-order and replayed deliveries are harmless).
- Message examples live in `contracts/edge-v1/`; both test suites check against them.

## Edge side (`edge/`, own image, never imports `backend/`)

- `bus.py`: bus interface and `SimulatedBus` (room physics without a controller).
- `rules.py`: room controller (proportional valve), "window open → heating off", frost protection
  at 7 °C, and the refusal of writes to non-controllable devices.
- `buffer.py`: SQLite queue of readings with their measurement time; delivered in order.
- `cloud.py`: HTTP client for `/edge/v1`.
- `gateway.py`: one tick = advance bus, apply rules, buffer readings, flush, heartbeat, fetch and
  execute commands, acknowledge.

## Tasks

### Task 1: Cloud edge API
- [x] Tests: provisioning returns a token once and only its hash is stored; a wrong token is 401;
  hello lists the gateway's devices and points; readings update the twin with source `edge` and
  ignore older readings; heartbeat sets gateway online and device health; writing a set point of an
  edge room creates a command and a desired value; commands are handed out once and acknowledged;
  a non-controllable device never gets a command; the cloud simulator skips edge rooms.
- [x] Migration, services, `/edge/v1`, gateway provisioning endpoint.

### Task 2: Edge gateway
- [x] Tests: window open closes the valve; frost protection; a reading measured during an outage is
  delivered after it with its original time; commands are executed and acknowledged; a command for a
  non-controllable device is refused; messages match `contracts/edge-v1`.
- [x] Package, Dockerfile, CI job.

### Task 3: Frontend
- [x] Geräte tab: gateways with status, register, create token (shown once, with the run command).
- [x] Zimmer tiles show "ausstehend" for desired set points and hide simulator toggles for edge rooms.

### Task 4: Verification
- [ ] Green CI; on Railway the edge API answers 401 without a token. Running an edge container
  against Railway is a human step (deployment.md).
