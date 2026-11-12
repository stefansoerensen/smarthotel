# ADR-0003: Safety systems are read only

Status: Accepted (2026-11-12). Implements hub d12 for Smart Building.

## Context
Hub d12: deterministic before generative, and safety and evacuation stay with people. A hotel's
building also contains fire alarm systems, smoke extraction, sprinklers, emergency lighting and
voice evacuation. These are regulated systems with their own certified controllers. The platform
benefits from seeing their state (a fault, an alarm in a room) but must never be a path to
switching them.

## Decision
The device catalogue names the safety kinds (`fire_alarm`, `smoke_detector`, `smoke_extraction`,
`sprinkler`, `emergency_light`, `evacuation`). A device of such a kind is always stored with
`controllable = false`:

- registering it as controllable fails with `device.safety_read_only`;
- patching it to controllable fails the same way;
- changing a device's kind to a safety kind drops control.

The rule lives in the service layer, so no API, import or future agent can bypass it. Every later
command path (SB2) must refuse devices with `controllable = false` before anything reaches the edge,
and the edge must refuse them again.

## Consequences
+ The platform can show safety states and raise faults without ever writing to those systems.
+ The rule is testable and tested.
− A legitimate need to write to such a system (none known) would need a new ADR, not a flag.
