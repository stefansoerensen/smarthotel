# ADR-0004: Edge gateway as its own Python container, outbound only

Status: Accepted (2026-11-12). Follows hub d34 and d35; implemented from SB2.

## Context
Room automation must keep working when the internet connection of a hotel fails. Field buses
(KNX/IP, BACnet/IP, Modbus) live on the building network, which must stay closed. Hub d34 rules
out a home-automation platform as the base; the edge is built on open protocol libraries (xknx,
BACpypes, pymodbus) and Mosquitto, licences checked before use (b36).

## Decision
- The edge gateway is a separate Python 3.11 container under `edge/`, one per property. It never
  imports `backend/`; the contract between them is a versioned message format.
- The gateway opens all connections outward (MQTT over TLS or HTTPS) to the control plane. Nothing on
  the hotel network accepts connections from the internet.
- Local rules that protect comfort and energy (window open → heating off) run on the edge, so they
  work offline. The cloud distributes them.
- Readings are buffered on the edge during an outage and delivered later with their original
  timestamps.
- Commands carry an id, are acknowledged by the edge, and are refused for devices that are not
  controllable (ADR-0003). Desired state is reconciled, as in pms-clone ADR-0013, not replayed.
- Until real hardware is allowed (hub b32, a16, b08), the edge runs only against simulators, in CI
  and on Railway.

## Consequences
+ Rooms keep working offline; the building network stays closed.
+ The edge can be tested without hardware.
− Two images to build and version; the message format needs its own compatibility tests.
