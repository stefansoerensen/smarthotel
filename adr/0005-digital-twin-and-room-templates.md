# ADR-0005: Digital twin per room, room types as templates, simulator in the control plane

Status: Accepted (2026-11-12). SB1, hub b29.

## Context
A hotel has many rooms of few kinds. Configuring 150 rooms device by device is the work that makes
building automation expensive. Before real hardware is allowed (b32/a16/b08) the product still has to
show rooms that behave plausibly.

## Decision
- **Room types are templates** of data points, kept per property. Rolling a room type out to a list of
  rooms creates the room, one device per point in the registry, and one twin point per device. The
  rollout is idempotent and never changes a room that already has another type.
- **The twin is a table of points per room** with the last value, its time and its source
  (`manual`, `simulator`, later `edge`). Values are floats; booleans are 0/1. Value updates emit no
  domain events — they are state, not business facts; room types and rooms do emit events.
- **Writability is decided by the device kind**, not by the caller: sensors and safety kinds are
  read only (ADR-0003). Writing a set point in SB1 changes the twin only; commands to devices arrive
  with the edge (SB2).
- **The simulator is a pure function** in `services/twin/simulator.py`, advanced by an explicit API
  call with a number of minutes. It includes a simple proportional room controller as a stand-in for
  the room controller in the building; the edge's local rules (SB2) replace it for real rooms.
- Module `twin` depends on `devices`, `estate` and `platform`.

## Consequences
+ 150 rooms are one rollout; the registry stays the single list of devices.
+ Tests and demos are reproducible: no background randomness.
− Templates per property are copied, not shared across properties of a tenant; sharing can follow.
− Floats are fine for sensor data, not for money — money never lives here.
