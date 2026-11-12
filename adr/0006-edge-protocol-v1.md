# ADR-0006: Edge protocol v1 — HTTPS polling with gateway tokens

Status: Accepted (2026-11-12). SB2; refines ADR-0004.

## Context
The gateway must work behind a hotel firewall that allows only outbound connections, keep rooms
running offline, and never let the cloud write to a device that is not controllable.

## Decision
- **Transport:** HTTPS from the gateway to `/edge/v1` on the control plane. The gateway polls for
  commands every tick (default 15 s). MQTT stays an option for v2 when latency matters; polling is
  enough for room climate and needs no broker in the cloud.
- **Identity:** one token per gateway, created by an operator ("Token erzeugen"), shown once, stored
  as SHA-256 hash. A new token replaces the old one.
- **Readings:** the gateway sends `device_code`, `value`, `measured_at`. The cloud applies a
  reading only if it is newer than the stored value, so buffered, repeated or late deliveries are
  harmless. The gateway keeps readings in a SQLite queue until the cloud has accepted them.
- **Commands:** a write to a point whose device sits behind a gateway becomes a command with an id;
  the twin keeps it as *desired* until a reading confirms it. The gateway executes and acknowledges
  (`done`, `failed`, `refused`). Commands are created only for controllable devices, and the gateway
  refuses commands for devices it knows as not controllable — two independent checks (ADR-0003).
- **Local rules** (room controller, window open → heating off, frost protection) run on the
  gateway every tick, with or without the cloud.
- **Contract:** example messages in `contracts/edge-v1/` are used by both test suites.

## Consequences
+ Works through any firewall that allows HTTPS out; no inbound port, no broker to run.
+ Outages lose nothing; duplicates do nothing.
− Command latency is up to one poll interval.
− A stolen token can report readings for its gateway's devices only; it cannot reach other
  gateways or any user API.
