# ADR-0001: Modular monolith with domain events and a transactional outbox

Status: Accepted (2026-11-12). Same pattern as pms-clone (hub d35).

## Context
The control plane will grow modules for the registry, room templates and twins, rules, energy data
and the coupling with the Hotel OS. Two people build it; the coupling (SB3) must not lose events
when a call to the other system fails.

## Decision
One FastAPI application with modules under `services/<module>/` and `models/<module>/`, a fixed
dependency direction checked by an AST import test, and services that never commit. Every state
change writes an event into `outbox_events` inside the same transaction. Delivery is a separate
worker (from SB3).

## Consequences
+ One deploy, one database, transactions across modules.
+ Events cannot be lost between "data changed" and "event published".
− Module discipline depends on the boundary test, not on the runtime.
− Event delivery is at-least-once; consumers must be idempotent.
