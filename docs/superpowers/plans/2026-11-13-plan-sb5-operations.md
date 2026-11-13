# Smart Building — Plan SB5: Operations

> Steps use checkbox (`- [ ]`) syntax. Tick them in the same commit as the work.

**Goal:** What a hotel group needs to run the product without the developer: its own users, bus
addresses imported from the building's planning tool, occupancy that follows the Hotel OS without
pressing a button, a view of what was sent to the devices, and an overview per property.

**Hub:** b29, d12, d19 (still simulators only), ADR-0009 (background jobs).

### Task 1: Users
- [x] Tests: an admin creates operators for a tenant and admins without one, lists users, resets a
  password, deactivates a user (who can no longer log in); an operator sees only the users of its
  tenant and cannot change them; the last active admin cannot be deactivated; a user changes their
  own password with the old one.
- [x] `/api/users` (list, create, patch), `/api/auth/password`; frontend page "Benutzer" for admins
  and "Passwort ändern" for everyone.

### Task 2: Bus address import
- [x] Tests: a CSV with `code;address` (or an ETS group address export: `"Group name";"Address"`)
  sets the bus addresses of existing devices; unknown codes and malformed lines are reported per
  line; a preview changes nothing; KNX addresses are checked (`main/middle/sub`).
- [x] `POST /api/properties/{code}/devices/addresses?apply=` (text body); frontend dialog in Geräte
  with preview and apply; the registry shows the address again.

### Task 3: Background jobs (ADR-0009)
- [x] Tests: the scheduler syncs every enabled Hotel OS link when it is due and records errors on the
  link; a sync of one property failing does not stop the others; due-ness respects the interval.
- [x] In-process loop started by the FastAPI lifespan, gated by `RUN_JOBS` (default `true`),
  `HOTEL_OS_SYNC_MINUTES` (default 10), a Postgres advisory lock so only one replica runs a job.

### Task 4: Commands and overview
- [x] Geräte tab: last commands with status (offen, gesendet, erledigt, abgelehnt, fehlgeschlagen).
- [x] `GET /api/properties/{code}/overview`: rooms by occupancy and mode, average temperature of
  occupied rooms, open faults, gateways online/offline, kWh yesterday; shown on the Häuser list and
  at the top of the Haus page.

### Task 5: Verification
- [ ] Green CI; on Railway the pages answer (read only).
